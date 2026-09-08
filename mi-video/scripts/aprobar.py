"""Aprobar una versión, que es lo único que el motor no puede hacer solo.

Regla de Jaime: *«sale el vídeo renderizado, se aprueba uno por uno, y de cada
versión aprobada me das el audio virgen»*. Y sobre la máquina: *«las fases y los
estados son etiquetas que llaman servicios»* — pero `aprobado` **no tiene
servicio**, porque no hay nada que ejecutar. La mueve él.

## Qué desencadena aprobar

No es una anotación: es lo que abre la segunda mitad del ciclo.

    aprobada  ->  el motor sigue: voz limpia, masterizado, publicacion
              ->  la pieza pasa a montarse CON musica y efectos
              ->  el audio virgen de ESA version queda atado a ella

Lo último importa más de lo que parece. El audio limpio de una versión no vale
para otra: el corte es distinto y reintegrarlo desincroniza la pieza entera, y
eso no se ve hasta el render. Por eso `audio_version` cuelga de la versión y no
del vídeo.

## Y rechazar también avanza

`rehacer` no es «no hacer nada»: deja la pieza en su fase con el motivo escrito,
y ese motivo es lo que se convierte en nota de revisión. Una pieza rechazada sin
motivo es una pieza que se va a rehacer igual de mal.

    python scripts/aprobar.py 4                     # aprueba el reel 4
    python scripts/aprobar.py 2 --rehacer "el audio"  # lo devuelve con motivo
    python scripts/aprobar.py --ver                 # que hay aprobado
"""
import argparse
import datetime
import os
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def _cerrar_lo_abierto(slug, quien):
    """**Aprobar cierra todo lo que quedaba abierto de esa pieza.**

    Jaime, 7-9-2026: *«aprobado cierra todos los tikets abiertos siempre»*, y
    antes, viendo tres piezas firmadas dando vueltas por la linea: *«de aprobado
    no sale nada, a menos que yo lo diga»*, *«porque gastan tiempo valioso, mi
    tiempo en algo que ya esta aprobado»*.

    Sin esto, aprobar dejaba la pieza firmada **y con sus tiquets vivos**, asi
    que cada mecanismo que mira pendientes la volvia a encontrar: la puerta la
    devolvia a su paso, una respuesta tardia la sacaba de `aprobado`, y el
    enrutador la listaba como bloqueada en cada vuelta. Tres formas distintas de
    lo mismo, y las tres se arreglan aqui — en el origen — y no poniendo un
    guarda en cada una.

    Y es correcto, no una limpieza: **su firma es la respuesta**. Aprobar
    viendo la pieza es decir que lo que quedaba abierto ya no importa o ya esta;
    seguir tratandolo como pendiente es no creerle.

    Cierra los tiquets y da por aplicadas sus correcciones. Queda escrito quien
    y por que, que es lo que distingue cerrar de borrar.
    """
    por_que = f"cerrado por la aprobacion de {quien}: la pieza se firmo asi"
    n = 0
    try:
        from dominio import ticket as _t
        for t in _t.abiertos(slug):
            _t.contestar(t["id"], por_que, "arreglado", quien)
            n += 1
    except Exception:                              # noqa: BLE001
        pass
    try:
        import basedatos as _b
        cx = _b.abrir("ads/decisiones.db")
        cx.execute("update revision set estado = 'aplicada', regla = ?"
                   " where video_slug = ? and estado = 'pendiente'",
                   (por_que[:400], slug))
        cx.commit()
        cx.close()
    except Exception:                              # noqa: BLE001
        pass
    if n:
        print(f"  {slug}: {n} tiquet(s) cerrados por la aprobacion")
    return n


def veredicto(n, aprobada=True, notas=None, quien="jaime"):
    slug = f"reel-{n:02d}"
    con = _con()
    v = con.execute(
        "select ve.id, ve.n from version ve join video vi on vi.id = ve.video_id"
        " where vi.slug = ? order by ve.n desc limit 1", (slug,)).fetchone()
    if not v:
        con.close()
        return None, "sin version registrada — corre la linea primero"
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    con.execute(
        "insert or replace into aprobacion (version_id, veredicto, quien,"
        " notas, fecha) values (?,?,?,?,?)",
        (v["id"], "aprobada" if aprobada else "rehacer", quien, notas, ahora))
    if aprobada:
        # La etiqueta se mueve: a partir de aqui el motor sigue solo.
        f = con.execute("select id from fase where nombre = 'aprobado'").fetchone()
        vid = con.execute("select id from video where slug = ?",
                          (slug,)).fetchone()
        if f and vid:
            con.execute("insert into video_fase (video_id, fase_id, entro)"
                        " values (?,?,?)", (vid["id"], f["id"], ahora))
    con.commit()
    con.close()
    if aprobada:
        _cerrar_lo_abierto(slug, quien)
    registro.nota("aprobar", "veredicto sobre una version",
                  detalle=f"{slug} v{v['n']}: "
                          f"{'aprobada' if aprobada else 'rehacer'}"
                          f"{' — ' + notas if notas else ''}")
    return v["n"], None


def ver():
    con = _con()
    filas = con.execute(
        "select vi.slug, ve.n, ve.duracion_s, a.veredicto, a.quien, a.notas,"
        " a.fecha from version ve join video vi on vi.id = ve.video_id"
        " left join aprobacion a on a.version_id = ve.id"
        " order by vi.slug, ve.n").fetchall()
    con.close()
    for r in filas:
        d = f"{r['duracion_s']:.0f}s" if r["duracion_s"] else "—"
        print(f"{r['slug']}  v{r['n']}  {d:>6}  "
              f"{r['veredicto'] or 'sin veredicto':<14}"
              f"{'  ' + (r['notas'] or '') if r['veredicto'] else ''}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--rehacer", metavar="MOTIVO",
                    help="devuelve la pieza, con el motivo")
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()
    if a.ver or not a.reels:
        ver()
        return
    for n in a.reels:
        v, err = veredicto(n, aprobada=not a.rehacer, notas=a.rehacer)
        if err:
            print(f"reel-{n:02d}: {err}")
        else:
            print(f"reel-{n:02d} v{v}: "
                  + ("aprobada — el motor sigue: voz limpia, masterizado,"
                     " publicacion" if not a.rehacer
                     else f"a rehacer — {a.rehacer}"))


if __name__ == "__main__":
    main()
