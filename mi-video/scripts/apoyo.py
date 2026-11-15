"""La ingesta de la biblioteca de apoyo: un tramo de una cinta pasa a ser un clip.

    python scripts/apoyo.py giro-al-pc --cinta 20261113_204403 --desde 5.5 --hasta 12.8 \\
        --muestra "Jaime se gira a cámara desde la silla y vuelve al monitor" \\
        --monitor 0.379,0.407,0.236,0.275 --delante

**Por qué existe** (C-704). La biblioteca (`src/brand/apoyo.json`, C-673) es
«la voz sigue y la imagen es otra», y hasta hoy sus clips se cortaban a mano.
Jaime, 15-11-2026, sobre la apertura de reel-23: la toma 8K en que se gira a
cámara y mira al computador **no tiene voz** —whisper oye «Hi»—, así que
`abanico` no la ve y ningún paso podía ponerla bajo la voz de la otra cinta.
Jaime: *«sí, por apoyo»*. Un clip de apoyo es exactamente eso, y declararlo es
una ingesta, no una edición a mano del JSON (el hook lo para).

Lo que deja:
- `public/apoyo/<id>.mp4`, 1920×1080 y mudo, cortado del ángulo de la cinta;
- con `--delante`, `public/recorte/apoyo-<id>.webm`: su silueta con alfa, por
  `text-behind.py`, para que lo que se amplíe desde el monitor no le tape;
- la entrada en `apoyo.json`, con `muestra`, `derechos` (la toma y los
  segundos), y si se dan, `monitor` (fracciones del clip) y `recorte`.

`--solo-ficheros` corta y recorta sin tocar el JSON: es lo que se corre en la
línea, cuyo `public/` es dato y cuyo `apoyo.json` llega por despliegue.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rutas  # noqa: E402

BIBLIOTECA = os.path.join("src", "brand", "apoyo.json")


def _angulo(cinta, nombre):
    for a in rutas.angulos(cinta):
        if os.path.splitext(os.path.basename(a))[0] == nombre:
            return a
    raise SystemExit(f"la grabación {cinta} no tiene el ángulo «{nombre}»")


def cortar(origen, desde, hasta, salida):
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{desde:.3f}", "-to", f"{hasta:.3f}", "-i", origen, "-an",
                    "-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-crf", "18",
                    "-preset", "medium", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    salida], check=True)


def recortar(clip, dura, salida):
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    subprocess.run([sys.executable, os.path.join("scripts", "text-behind.py"), "--video", clip,
                    "--canto", "limpio", "--desde", "0", "--hasta", f"{dura:.3f}",
                    "--out", salida], check=True)


def declarar(id_, entrada):
    d = json.load(open(BIBLIOTECA, encoding="utf-8"))
    d["clips"][id_] = entrada
    with open(BIBLIOTECA, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("id", help="nombre del clip, en minúsculas y con guiones")
    ap.add_argument("--cinta", required=True)
    ap.add_argument("--angulo", default="camA")
    ap.add_argument("--desde", type=float, required=True)
    ap.add_argument("--hasta", type=float, required=True)
    ap.add_argument("--muestra", help="qué se ve, en una línea")
    ap.add_argument("--monitor", help="x,y,w,h del monitor, fracciones del clip")
    ap.add_argument("--insignia", default=None)
    ap.add_argument("--delante", action="store_true", help="saca su silueta con alfa")
    ap.add_argument("--solo-ficheros", action="store_true", help="no toca apoyo.json")
    a = ap.parse_args()
    if a.hasta <= a.desde:
        raise SystemExit("--hasta tiene que ir después de --desde")
    if not a.solo_ficheros and not a.muestra:
        raise SystemExit("un clip se declara con --muestra: qué enseña")

    origen = _angulo(a.cinta, a.angulo)
    fichero = f"apoyo/{a.id}.mp4"
    cortar(origen, a.desde, a.hasta, os.path.join(rutas.PUBLICO, fichero))
    print(f"  {fichero}: {a.hasta - a.desde:.1f} s de {a.cinta}/{a.angulo}")
    recorte = None
    if a.delante:
        recorte = f"recorte/apoyo-{a.id}.webm"
        recortar(os.path.join(rutas.PUBLICO, fichero), a.hasta - a.desde,
                 os.path.join(rutas.PUBLICO, recorte))
        print(f"  {recorte}: su silueta, para que nada le tape")
    if a.solo_ficheros:
        return
    entrada = {
        "fichero": fichero, "muestra": a.muestra, "orientacion": "horizontal",
        "insignia": a.insignia,
        "derechos": f"propio: toma {a.cinta}/{a.angulo}, {a.desde:.1f}–{a.hasta:.1f} s"
                    f" ({datetime.date.today():%d-%m-%Y})",
    }
    if a.monitor:
        x, y, w, h = (float(v) for v in a.monitor.split(","))
        entrada["monitor"] = {"x": x, "y": y, "w": w, "h": h}
    if recorte:
        entrada["recorte"] = recorte
    declarar(a.id, entrada)
    print(f"  apoyo.json: «{a.id}» declarado")


if __name__ == "__main__":
    main()
