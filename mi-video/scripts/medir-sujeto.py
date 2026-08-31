"""Mide DONDE y CUANTO ocupa el sujeto en cada toma, para poder igualar encuadres.

Por que hace falta
------------------
`punch-ins.py` define `completo` como 1.00 — el sensor entero. Eso no es un
encuadre, es la ausencia de uno: lo que se ve depende de a que distancia se
sento el sujeto ese dia. En la sesion de tarde queda plano medio; en la de
noche, reclinado y mas lejos, queda plano general con sofa y perro. Los seis
dejan de parecer la misma serie.

Para igualarlos hace falta un numero: **que fraccion de la altura del cuadro
ocupa el sujeto**. Con eso, `completo` se normaliza por toma en vez de heredar
la distancia de camara.

Y el ancla en X
---------------
El docstring de `punch-ins.py` ya avisa: el centroide del movimiento se equivoca
"si hay algo moviendose de fondo". En la sesion de noche hay **un husky** — y un
perro grande moviendose en el suelo es muchisimo movimiento. En `reel-03` el
recorte `medio` salio pegado al borde izquierdo (x=0, clamped), que es la firma
de un ancla arrastrada.

Aqui la X se calcula **solo sobre la banda de la cabeza y los hombros**, no
sobre todo el movimiento. El perro esta en el suelo, muy por debajo de la
coronilla, asi que queda fuera por construccion.
"""
import argparse
import json
import subprocess

import numpy as np
from scipy.ndimage import uniform_filter
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402



def sample(source, t0, t1, n=14, w=270):
    times = np.linspace(t0, t1, n)
    out = []
    for t in times:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error"] + gpu.decodifica() + ["-ss", f"{t}", "-i", source,
             "-frames:v", "1", "-vf", f"scale={w}:-1,format=gray",
             "-f", "rawvideo", "-"], capture_output=True).stdout
        if not raw:
            continue
        h = len(raw) // w
        if h < 10:
            continue
        out.append(np.frombuffer(raw[:w * h], dtype=np.uint8)
                   .reshape(h, w).astype(float))
    return out


def medir(frames):
    acc = None
    for a, b in zip(frames, frames[1:]):
        if a.shape != b.shape:
            continue
        d = np.abs(b - a)
        acc = d if acc is None else acc + d
    if acc is None:
        return None
    acc = uniform_filter(acc, size=9)
    h, w = acc.shape
    mask = acc >= np.percentile(acc, 92)
    ys, xs = np.nonzero(mask)
    if ys.size < 20:
        return None

    coronilla = float(np.percentile(ys, 15))
    # Banda cabeza+hombros: desde la coronilla, un 18% de la altura del cuadro.
    # Es la zona donde el sujeto esta y el perro no.
    banda = (ys >= coronilla) & (ys <= coronilla + 0.18 * h)
    ax_cabeza = float(xs[banda].mean() / w) if banda.sum() > 10 else float(xs.mean() / w)

    return {
        "ancla_x_todo": round(float(xs.mean() / w), 4),
        "ancla_x_cabeza": round(ax_cabeza, 4),
        "coronilla_y": round(coronilla / h, 4),
        # Extension vertical del movimiento: p15 a p95. Aproxima "cuanto cuadro
        # ocupa el sujeto" — con el perro dentro se dispara, que es la senal.
        "extension_y": round(float(np.percentile(ys, 95) - coronilla) / h, 4),
        "ancho_cabeza": round(float(np.percentile(xs[banda], 90)
                                    - np.percentile(xs[banda], 10)) / w, 4)
        if banda.sum() > 10 else None,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    a = ap.parse_args()
    plan = json.load(open(a.plan, encoding="utf-8"))
    # Se muestrea CADA escena en su propio rango, no el intervalo que va de la
    # primera a la ultima. En el reel 5 la escena 0 es una apertura en frio
    # tomada del minuto 682 y la ultima cierra en el 186: el "rango global"
    # sale invertido y el muestreo cae en un trozo que no esta en la pieza.
    frames = []
    rangos = []
    for e in plan["escenas"]:
        t0, t1 = e["origen_desde"], e["origen_hasta"]
        rangos.append([round(t0, 2), round(t1, 2)])
        frames += sample(plan["source"], t0, t1, n=8)
    m = medir(frames)
    print(json.dumps({"plan": a.plan, "rangos": rangos, **(m or {})},
                     ensure_ascii=False))
