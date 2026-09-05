"""Dónde está cada pieza. Lo primero que se corre en una sesión nueva.

Regla de Jaime, dicha como comprobación: *«si ya estamos, nunca se va a perder el
estado de un vídeo así limpie completamente el contexto»*.

Eso sólo es cierto si el estado **se puede reconstruir sin preguntarle a nadie**.
Y hasta ahora no del todo: había estado por fragmento (`fase`/`paso`) y ninguna
vista que dijera en qué punto está cada vídeo. Una sesión nueva tenía que
deducirlo mirando ficheros y fechas — que es exactamente como se pierde.

Esto lo lee todo de la base y del disco, y no de la memoria de nadie:

    version      qué corte es el vigente y si cambió desde el último registrado
    aprobación   si está aprobado, por quién y cuándo
    audio        si salió el virgen, si volvió el limpio, si está integrado
    publicación  si se subió y dónde
    pendiente    cortes suyos sin aplicar y pedidos de IA sin contestar
    puerta       si pasaría la verificación ahora mismo

Si esto se ejecuta y contesta, el contexto es prescindible. Ése es el criterio.

    python scripts/donde.py
"""
import argparse
import json
import os
import sqlite3
import basedatos
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import modelo  # noqa: E402
import servicio  # noqa: E402
import rutas  # noqa: E402

BASE = "ads/decisiones.db"


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, encoding="utf-8", errors="replace",
                              cwd="..").stdout.strip()
    except Exception:                              # noqa: BLE001
        return "?"


def estado(slug):
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row
    v = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        con.close()
        return None
    ult = con.execute(
        "select * from version where video_id = ? order by n desc limit 1",
        (v["id"],)).fetchone()
    ap = con.execute(
        "select * from aprobacion where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    au = con.execute(
        "select * from audio_version where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    pu = con.execute(
        "select * from publicacion where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    pend = con.execute(
        "select count(*) from revision where video_slug = ? and accion='cortar'"
        " and estado='pendiente'", (slug,)).fetchone()[0]
    con.close()
    # **La huella dice si el corte se movió desde la versión registrada.** Es la
    # diferencia entre «hay una versión» y «la versión es ésta»: sin esto, una
    # sesión nueva creería que lo registrado corresponde al EDL de ahora.
    h = modelo.huella_edl(slug)
    return {
        "version": ult["n"] if ult else None,
        "huella_reg": ult["huella"] if ult else None,
        "huella_hoy": h,
        "al_dia": bool(ult and ult["huella"] == h),
        "duracion": ult["duracion_s"] if ult else None,
        "aprobada": ap["veredicto"] if ap else None,
        "audio_virgen": bool(au and au["virgen"]),
        "audio_limpio": bool(au and au["limpio"]),
        "audio_integrado": bool(au and au["integrado"]),
        "publicada": pu["destino"] if pu else None,
        "cortes_pendientes": pend,
        "pedidos_ia": [p for p, sl, _ in servicio.pendientes() if sl == slug],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    print(f"commit {_commit()}\n")
    print(f"{'pieza':<9} {'ver':>3} {'corte':>7} {'dur':>7}  "
          f"{'aprobada':<9} {'audio':<22} {'pendiente'}")
    for n in rutas.piezas():
        slug = f"reel-{n:02d}"
        e = estado(slug)
        if not e:
            continue
        corte = "al dia" if e["al_dia"] else "CAMBIO"
        audio = ("integrado" if e["audio_integrado"]
                 else "limpio, sin integrar" if e["audio_limpio"]
                 else "virgen entregado" if e["audio_virgen"]
                 else "—")
        pend = []
        if e["cortes_pendientes"]:
            pend.append(f"{e['cortes_pendientes']} corte(s)")
        if e["pedidos_ia"]:
            pend.append("IA: " + ",".join(e["pedidos_ia"]))
        dur = f"{e['duracion']:.0f}s" if e["duracion"] else "—"
        print(f"{slug:<9} {str(e['version'] or '-'):>3} {corte:>7} {dur:>7}"
              f"  {(e['aprobada'] or '-'):<9} {audio:<22}"
              f" {'; '.join(pend) or '-'}")
    # **Y el material que todavia no es pieza.** Esto es lo que hacia que la
    # septima grabacion fuera invisible: la tabla recorre piezas, asi que una
    # cinta sin pieza no salia ni como pendiente ni como nada. No es que
    # estuviera mal contada — es que **no se podia echar de menos**, que es la
    # unica averia que este comando existe para no tener.
    #
    # Se dice en que punto esta, porque lo que le falta a cada una es distinto:
    # una sin copiar se pide, una sin transcribir se transcribe, y una
    # transcrita y sin libreto **espera a Jaime**, no a la maquina.
    huerfanas = []
    for t in rutas.material():
        if t in set(rutas.TOMAS.values()):
            continue
        hay_mp4 = os.path.exists(f"{rutas.ORIGEN}/{t}.mp4")
        hay_tr = os.path.exists(f"{rutas.TRABAJO}/transcripts/{t}.json")
        falta = ("sin copiar de origen" if not hay_mp4
                 else "sin transcribir — corre transcribir.py" if not hay_tr
                 else "transcrita y sin libreto: la construye Jaime")
        huerfanas.append((t, falta))
    if huerfanas:
        print()
        print(f"Y {len(huerfanas)} grabacion(es) que todavia no son pieza:")
        for t, falta in huerfanas:
            print(f"    · {t}: {falta}")

    print("\nY lo que dice la puerta ahora mismo:")
    subprocess.run([sys.executable, "scripts/verificar.py", "--avisa"])
    # **Y si el sistema esta conectado, que es lo primero que hay que saber.**
    #
    # Jaime, despues de una noche de correcciones suyas que no llegaban: *«tu
    # objetivo no es editar videos, es vigilar que el sistema funcione y este
    # todo conectado; aca no esta conectado»*.
    #
    # Va aqui y no en `montar.sh` a proposito: un cable suelto no tiene por que
    # parar una entrega —Jaime quiere ver la pieza—, pero **no puede pasar
    # inadvertido al empezar**. Un productor sin consumidor no da error nunca;
    # sale cuando el mira la entrega y echa en falta lo que pidio.
    print()
    subprocess.run([sys.executable, "scripts/conectado.py"])


if __name__ == "__main__":
    main()
