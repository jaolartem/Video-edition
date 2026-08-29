"""
Mide el foco a lo largo de una toma. Un plano desenfocado no se usa, se diga bien
o mal.

Como se mide
------------
Varianza del laplaciano sobre la region del sujeto. Es la medida estandar de
nitidez: una imagen enfocada tiene bordes marcados —transiciones bruscas de
intensidad— y una desenfocada los tiene suaves, asi que la segunda derivada se
aplana. Cuanto mayor la varianza, mas nitido.

Se mide **solo sobre el sujeto**, no sobre el cuadro entero: el fondo puede estar
desenfocado a proposito y arrastraria la media hacia abajo. La region se toma
alrededor del ancla de movimiento, igual que los encuadres.

Que significa el numero
-----------------------
El valor absoluto **no es comparable entre camaras ni entre iluminaciones**. Lo
que importa es la distribucion DENTRO de una misma toma: los momentos que caen
muy por debajo de la mediana son los que perdieron el foco.

Uso:
    python scripts/focus-check.py --source "G:/.../X.mp4" --desde 60 --hasta 560
    python scripts/focus-check.py --source "..." --edl ads/reel-01/edl-sell.json
"""
import argparse
import json
import subprocess

import numpy as np

W = 480


def frame(source, t):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", source,
         "-frames:v", "1", "-vf", f"scale={W}:-1,format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True).stdout
    if not raw:
        return None
    h = len(raw) // W
    if h < 10:
        return None
    return np.frombuffer(raw[:W * h], dtype=np.uint8).reshape(h, W).astype(float)


def sharpness(img, box=None):
    """Varianza del laplaciano. Mas alto, mas nitido."""
    if img is None:
        return None
    if box:
        y0, y1, x0, x1 = box
        img = img[y0:y1, x0:x1]
    if img.size < 400:
        return None
    lap = (-4 * img
           + np.roll(img, 1, 0) + np.roll(img, -1, 0)
           + np.roll(img, 1, 1) + np.roll(img, -1, 1))[1:-1, 1:-1]
    return float(lap.var())


def subject_box(img):
    """
    Region central-superior, donde vive la cara en un plano hablado.

    Recorte fijo y no deteccion: aqui solo hace falta excluir el fondo lejano y
    el suelo, no localizar con precision.
    """
    h, w = img.shape
    return (int(h * 0.15), int(h * 0.55), int(w * 0.10), int(w * 0.75))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--edl")
    ap.add_argument("--desde", type=float, default=0)
    ap.add_argument("--hasta", type=float)
    ap.add_argument("--paso", type=float, default=5.0)
    args = ap.parse_args()

    if args.edl:
        segs = json.load(open(args.edl, encoding="utf-8"))["segmentos"]
        tiempos = []
        for a, b in segs:
            n = max(1, int((b - a) / 1.5))
            tiempos += [a + (b - a) * (k + 0.5) / n for k in range(n)]
    else:
        hasta = args.hasta or (args.desde + 300)
        tiempos = list(np.arange(args.desde, hasta, args.paso))

    filas = []
    for t in tiempos:
        img = frame(args.source, float(t))
        if img is None:
            continue
        v = sharpness(img, subject_box(img))
        if v is not None:
            filas.append((float(t), v))

    if not filas:
        raise SystemExit("No se pudo medir.")

    vals = np.array([v for _, v in filas])
    med = float(np.median(vals))
    # Umbral relativo: la mitad de la mediana ya es blandura evidente.
    umbral = med * 0.55

    print(f"{len(filas)} muestras · nitidez mediana {med:.0f} "
          f"(min {vals.min():.0f}, max {vals.max():.0f})")
    print(f"umbral de desenfoque: {umbral:.0f}\n")

    malos = [(t, v) for t, v in filas if v < umbral]
    for t, v in filas:
        if v < umbral:
            print(f"  {t:7.1f}s  nitidez {v:7.0f}  <-- DESENFOCADO ({v/med:.0%} de la mediana)")

    print(f"\n{len(malos)} de {len(filas)} muestras por debajo del umbral")
    if not malos:
        print("Ningun tramo desenfocado detectado.")
