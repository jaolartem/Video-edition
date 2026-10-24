"""Cuánto costó cada vídeo y por qué: tiempo, vueltas, tiquets y agentes, medidos.

    python scripts/monitor.py                 # todas las piezas, una línea cada una
    python scripts/monitor.py reel-18         # una pieza: fases y agentes por paso
    python scripts/monitor.py --recoger       # antes, leer las transcripciones nuevas

Jaime, 23-10-2026: *«no quiero topes duros, quiero que las cosas se hagan bien,
pero sí quiero monitorización de cada vídeo, análisis de gasto… necesitamos ver
la eficiencia»*. No para nada: enseña. Lee la base y sólo la base; `--recoger`
es lo único que escribe, y sólo en la tabla `gasto` (ver `dominio/gasto.py`).

La eficiencia se cuenta contra lo que sale, no contra lo que se trabaja:
**tokens y minutos por segundo de vídeo final**, y agentes por tiquet resuelto.
Un lote se compara con otro con esas tres cifras.
"""
import argparse
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basedatos  # noqa: E402

#: Un hueco mayor entre dos anotaciones no es trabajo: es la noche, o esperar a Jaime.
ACTIVO = datetime.timedelta(minutes=15)


def _t(s):
    try:
        return datetime.datetime.fromisoformat(str(s)[:19])
    except (TypeError, ValueError):
        return None


def fases(cx, slug):
    """`(filas, cambios, atras, minutos_activos, {fase: minutos})` de su registro."""
    filas = cx.execute(
        "select f.nombre, f.orden, vf.entro from video_fase vf join fase f on f.id = vf.fase_id"
        " join video v on v.id = vf.video_id where v.slug = ? order by vf.id", (slug,)).fetchall()
    cambios = atras = 0
    activo, por = datetime.timedelta(), {}
    for (f0, o0, e0), (f1, o1, e1) in zip(filas, filas[1:]):
        if f1 != f0:
            cambios += 1
            atras += bool(o0 and o1 and o1 < o0)
        t0, t1 = _t(e0), _t(e1)
        if t0 and t1 and timedelta_ok(t1 - t0):
            activo += t1 - t0
            por[f0] = por.get(f0, 0) + (t1 - t0).total_seconds() / 60
    return len(filas), cambios, atras, activo.total_seconds() / 60, por


def timedelta_ok(d):
    return datetime.timedelta() <= d <= ACTIVO


def tiquets(cx, slug):
    """`(total, de_jaime, caducados, arreglados)`."""
    r = cx.execute(
        "select count(*),"
        " sum(t.autor_id = 1 or substr(t.dijo, 1, 40) like '%Jaime%'),"
        " sum(t.respuesta like 'Caducado%'), sum(t.estado = 'arreglado')"
        " from ticket t where t.pieza = ?", (slug,)).fetchone()
    return tuple(x or 0 for x in r)


def agentes(cx, slug):
    """Filas de `gasto` de la pieza, o `[]` si nunca se recogió."""
    try:
        return cx.execute("select paso, origen, llamadas, bash, entrada + cache_escritura"
                          " + cache_lectura, equivalente from gasto where pieza = ?",
                          (slug,)).fetchall()
    except sqlite3.OperationalError:
        return []


def pieza(cx, slug):
    """Todo lo de una pieza en un dict: lo que pinta la tabla y el detalle."""
    v = cx.execute("select count(*), count(distinct ve.huella), max(ve.duracion_s)"
                   " from version ve join video vi on vi.id = ve.video_id"
                   " where vi.slug = ?", (slug,)).fetchone()
    filas, cambios, atras, mins, por = fases(cx, slug)
    total, jaime, caducados, arreglados = tiquets(cx, slug)
    ag = agentes(cx, slug)
    dur = v[2] or 0
    equiv = sum(a[5] for a in ag)
    return {"pieza": slug, "dur": dur, "versiones": v[0], "cortes": v[1],
            "filas": filas, "cambios": cambios, "atras": atras, "minutos": mins,
            "por_fase": por, "tiquets": total, "jaime": jaime, "caducados": caducados,
            "arreglados": arreglados, "agentes": len(ag), "llamadas": sum(a[2] for a in ag),
            "bash": sum(a[3] for a in ag), "entrada": sum(a[4] for a in ag),
            "equiv": equiv, "por_paso": ag,
            "tok_s": equiv / dur if dur else 0, "min_s": mins / dur if dur else 0,
            "ag_tiq": len(ag) / arreglados if arreglados else 0}


def tabla(cx):
    slugs = [r[0] for r in cx.execute("select slug from video order by slug")]
    print(f"{'pieza':8} {'dur':>5} {'ver':>4} {'cort':>4} {'vuelt':>5} {'atrás':>5}"
          f" {'min':>6} {'tiq':>4} {'Jai':>4} {'cad':>4} {'agen':>4} {'llam':>5}"
          f" {'M ent':>6} {'M eq':>6} {'K eq/s':>7} {'min/s':>6}")
    for s in slugs:
        p = pieza(cx, s)
        if not p["filas"]:
            continue
        print(f"{s:8} {p['dur']:5.0f} {p['versiones']:4} {p['cortes']:4} {p['cambios']:5}"
              f" {p['atras']:5} {p['minutos']:6.0f} {p['tiquets']:4} {p['jaime']:4}"
              f" {p['caducados']:4} {p['agentes']:4} {p['llamadas']:5}"
              f" {p['entrada'] / 1e6:6.1f} {p['equiv'] / 1e6:6.2f} {p['tok_s'] / 1e3:7.0f}"
              f" {p['min_s']:6.1f}")
    print("\nvuelt = cambios de fase · atrás = vueltas hacia atrás · min = minutos activos"
          "\nM ent = tokens de entrada con caché · M eq = equivalente (ver dominio/gasto.PESO)"
          "\nK eq/s y min/s = por segundo de vídeo final: la eficiencia.")


def detalle(cx, slug):
    p = pieza(cx, slug)
    print(f"{slug}: {p['dur']:.0f} s · {p['versiones']} versiones, {p['cortes']} cortes"
          f" · {p['minutos']:.0f} min activos · {p['cambios']} cambios de fase,"
          f" {p['atras']} hacia atrás ({p['filas']} anotaciones)")
    print(f"  tiquets: {p['tiquets']} ({p['jaime']} de Jaime), {p['caducados']} caducados,"
          f" {p['arreglados']} arreglados")
    print("  tiempo por fase (min): " + ", ".join(
        f"{f} {m:.0f}" for f, m in sorted(p["por_fase"].items(), key=lambda x: -x[1])[:8]))
    pasos = {}
    for paso, origen, llam, bash, ent, eq in p["por_paso"]:
        q = pasos.setdefault((paso, origen), [0, 0, 0, 0])
        q[0] += 1
        q[1] += llam
        q[2] += bash
        q[3] += eq
    print("  agentes por paso:")
    for (paso, origen), (n, llam, bash, eq) in sorted(pasos.items(), key=lambda x: -x[1][3]):
        print(f"    {paso:12} {origen:7} {n:3} agentes · {llam:4} llamadas · {bash:3} Bash"
              f" · {eq / 1e6:6.2f} M eq")
    print(f"  eficiencia: {p['tok_s'] / 1e3:.0f} K eq por segundo de vídeo,"
          f" {p['min_s']:.1f} min por segundo, {p['ag_tiq']:.1f} agentes por tiquet arreglado")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", nargs="?")
    ap.add_argument("--recoger", action="store_true")
    a = ap.parse_args()
    if a.recoger:
        from dominio import gasto

        cx = basedatos.abrir(basedatos.BASE)
        print(f"monitor: {gasto.recoger(cx)} agentes recogidos de las transcripciones")
    cx = sqlite3.connect(f"file:{basedatos.BASE}?mode=ro", uri=True)
    if a.pieza:
        detalle(cx, a.pieza if a.pieza.startswith("reel-") else f"reel-{int(a.pieza):02d}")
    else:
        tabla(cx)


if __name__ == "__main__":
    main()
