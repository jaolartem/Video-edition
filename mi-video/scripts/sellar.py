"""Sella una entrega: el montaje entero queda guardado y se puede rehacer.

Jaime, cuando le dije que la entrega que había aprobado no se podía volver a
producir: *«no se trata de commits, todo debía estar en base de datos, y nada se
borra de la base de datos; para eso está»*.

## Lo que costó no tenerlo

El 4 de septiembre a las 19:20 se le entregaron siete piezas. Las miró, levantó
trece correcciones sobre ellas, y **no había forma de rehacerlas**: los cortes
se habían movido esa misma noche y no quedaba de dónde sacar los de esa entrega.
La tabla `version` guardaba `huella`, `duracion_s` y `commit_git` — o sea, con
qué distinguir dos versiones, no con qué reconstruir una.

Pidió los vídeos de vuelta —*«no quiero otros videos, quiero esos que vi»*— y lo
único que quedaba eran los mp4 en Drive.

## Qué queda guardado

El **EDL** —qué tramo de qué cinta, en qué orden— y el **spec** —lo que el render
dibuja: tableros, subtítulos, CTA—. Con esos dos, una versión se vuelve a montar
sola. Más el sha del fichero entregado, para saber si lo que hay en disco sigue
siendo lo que se selló.

Y **nada se borra**: cada entrega es una fila nueva. Ese es el punto.

    python scripts/sellar.py 3                 # sella lo entregado de reel-03
    python scripts/sellar.py --de out/entregado-19h    # sella otra carpeta
    python scripts/sellar.py --ver 3           # qué versiones hay
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"
ENTREGA = "out/entrega"


def _sha(f, tope=64 * 1024 * 1024):
    """El sha del fichero. Los primeros 64 MB bastan para distinguir entregas."""
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        h.update(fh.read(tope))
    return h.hexdigest()[:32]


def _dura(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", f],
                       capture_output=True, text=True)
    try:
        return round(float(r.stdout.strip()), 3)
    except ValueError:
        return None


def _leer(ruta):
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def sellar(n, carpeta=ENTREGA):
    """Guarda una versión nueva de esa pieza. Devuelve (numero, motivo)."""
    slug = f"reel-{n:02d}"
    mp4 = os.path.join(carpeta, f"reel-R{n}.mp4")
    if not os.path.exists(mp4):
        return None, f"no esta {mp4}"
    edl = _leer(f"ads/{slug}/edl-sell.json")
    if edl is None:
        return None, f"no esta el EDL de {slug}"
    # Del spec sólo su pieza: guardar las siete en cada fila es guardar seis de
    # más y perder de vista cuál era la suya.
    spec = None
    todo = _leer("src/reels.json")
    if todo:
        suya = [p for p in json.loads(todo) if p.get("id") == f"Reel-R{n}"]
        spec = json.dumps(suya[0], ensure_ascii=False) if suya else None
    cx = basedatos.abrir(BASE)
    fila = cx.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not fila:
        cx.close()
        return None, f"{slug} no esta en la tabla video"
    vid = fila[0]
    ult = cx.execute("select max(n) from version where video_id = ?",
                     (vid,)).fetchone()[0] or 0
    sha = _sha(mp4)
    ya = cx.execute("select n from version where video_id = ? and"
                    " sha_entrega = ?", (vid, sha)).fetchone()
    if ya:
        # Sellada ya, pero su audio puede faltar: la fila de `audio_version` se
        # anadio despues. Se completa y no se duplica — idempotente a proposito,
        # que es lo que permite volver a pasar por aqui sin miedo.
        _audio(cx, cx.execute("select id from version where video_id = ? and"
                              " sha_entrega = ?", (vid, sha)).fetchone()[0],
               slug)
        cx.commit()
        cx.close()
        return ya[0], "ya estaba sellada, es el mismo fichero"
    cx.execute(
        "insert into version (video_id, n, huella, duracion_s, fichero,"
        " commit_git, fecha, edl, spec, sha_entrega)"
        " values (?,?,?,?,?,?,?,?,?,?)",
        (vid, ult + 1, hashlib.sha1(edl.encode()).hexdigest()[:12], _dura(mp4),
         mp4.replace("\\", "/"), _git(), datetime.datetime.now().isoformat(),
         edl, spec, sha))
    # **Y el audio de esa version, que es la otra mitad de poder rehacerla.**
    #
    # `audio_version` estaba declarada y vacia desde que existe. Se pago exacto:
    # al querer corregir el sonido de las piezas aprobadas, tres de siete tenian
    # stems de OTRO montaje —reel-02 sobraba 1,2 s, reel-07 eran 63 s contra 88—
    # y no habia forma de saber cual iba con cual salvo midiendo duraciones a
    # mano. Con esto, cada version dice de que voz salio.
    _audio(cx, cx.execute("select last_insert_rowid()").fetchone()[0], slug)
    cx.commit()
    cx.close()
    return ult + 1, None


def _audio(cx, version_id, slug):
    """La voz de la que salió esa versión. No se duplica si ya está."""
    if cx.execute("select 1 from audio_version where version_id = ?",
                  (version_id,)).fetchone():
        return
    virgen = f"out/audio-puro/{slug}-voz.wav"
    limpio = next(iter(_limpios(slug)), None)
    cx.execute(
        "insert into audio_version (version_id, virgen, virgen_s, limpio,"
        " limpio_s, integrado, fecha) values (?,?,?,?,?,?,?)",
        (version_id, virgen if os.path.exists(virgen) else None,
         _dura(virgen) if os.path.exists(virgen) else None,
         limpio, _dura(limpio) if limpio else None,
         1 if limpio else 0, datetime.datetime.now().isoformat()))


def _limpios(slug):
    """Las devoluciones de Adobe para esa pieza, de la mas reciente a la mas vieja."""
    import glob

    hay = [f for f in glob.glob(f"out/audio-puro/{slug}-voz-*.wav")
           if "-cola" not in f]
    return sorted(hay, key=os.path.getmtime, reverse=True)


def _git():
    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() or None


def versiones(n):
    cx = basedatos.abrir(BASE)
    filas = cx.execute(
        "select v.n, v.duracion_s, v.fecha, v.fichero,"
        " length(v.edl) le, length(v.spec) ls from version v"
        " join video vi on vi.id = v.video_id where vi.slug = ?"
        " order by v.n", (f"reel-{n:02d}",)).fetchall()
    cx.close()
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--de", default=ENTREGA, help="de qué carpeta se sella")
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()
    for n in (a.reels or range(1, 8)):
        if a.ver:
            for v in versiones(n):
                print(f"  R{n} v{v[0]}  {v[1]}s  {str(v[2])[:16]}"
                      f"  edl {v[4] or 0} B · spec {v[5] or 0} B")
            continue
        num, mal = sellar(n, a.de)
        print(f"  R{n}: {mal}" if mal and num is None
              else f"  R{n}: version {num}"
                   + (f" — {mal}" if mal else " sellada, se puede rehacer"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
