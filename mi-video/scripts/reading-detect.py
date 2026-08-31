"""
Detecta los tramos en que Jaime está LEYENDO el libreto en vez de interpretar.

Hipotesis
---------
Al leer, la cabeza baja y se inclina hacia las hojas; al interpretar, se sostiene
alta y de frente a camara. Si es cierto, la **altura de la cabeza** separa los dos
estados sin necesidad de un modelo de pose ni de deteccion de mirada.

La altura se mide con la misma maquinaria del encuadre: el borde superior del
movimiento (percentil 15) es la coronilla. Cuanto mas abajo cae, mas inclinado
esta el sujeto.

Esto es una hipotesis medible, no un hecho. El script imprime la distribucion
completa para poder juzgar si el corte separa de verdad o si es ruido — si los
valores salen todos apelotonados, la hipotesis no se sostiene en este material y
hay que descartarla en vez de forzar un umbral.

Uso:
    python scripts/reading-detect.py --source "G:/.../X.mp4" --edl ads/reel-01/edl-sell.json
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


W = 270


def gray(source, t):
    raw = subprocess.run(
        ["ffmpeg", "-v", "error"] + gpu.decodifica() + ["-ss", str(t), "-i", source,
         "-frames:v", "1", "-vf", f"scale={W}:-1,format=gray",
         "-f", "rawvideo", "-"],
        capture_output=True).stdout
    if not raw:
        return None
    h = len(raw) // W
    if h < 10:
        return None
    return np.frombuffer(raw[:W * h], dtype=np.uint8).reshape(h, W).astype(float)


def head_y(source, t, dt=0.4):
    """Altura relativa de la coronilla: percentil 15 del movimiento."""
    a, b = gray(source, t), gray(source, t + dt)
    if a is None or b is None or a.shape != b.shape:
        return None
    d = uniform_filter(np.abs(b - a), size=9)
    mask = d >= np.percentile(d, 92)
    ys = np.nonzero(mask)[0]
    if ys.size < 20:
        return None
    return float(np.percentile(ys, 15) / d.shape[0])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--edl", required=True)
    ap.add_argument("--out")
    args = ap.parse_args()

    edl = json.load(open(args.edl, encoding="utf-8"))
    segs = edl["segmentos"]

    filas = []
    for i, (a, b) in enumerate(segs):
        # Tres muestras por segmento: una postura puntual no decide.
        ts = [a + (b - a) * f for f in (0.25, 0.5, 0.75)]
        vals = [v for v in (head_y(args.source, t) for t in ts) if v is not None]
        if not vals:
            continue
        filas.append({"i": i, "start": a, "end": b,
                      "head_y": round(float(np.median(vals)), 4),
                      "dispersion": round(float(np.std(vals)), 4)})

    if not filas:
        raise SystemExit("No se pudo medir ningun segmento.")

    ys = np.array([f["head_y"] for f in filas])
    q25, med, q75 = np.percentile(ys, [25, 50, 75])
    print(f"{len(filas)} segmentos medidos")
    print(f"altura de cabeza — min {ys.min():.3f}  q25 {q25:.3f}  "
          f"mediana {med:.3f}  q75 {q75:.3f}  max {ys.max():.3f}")
    print(f"recorrido: {ys.max()-ys.min():.3f}  (si es <0.05 la hipotesis no separa)\n")

    # Umbral relativo, no absoluto: cada rodaje tiene su encuadre.
    umbral = q75 + (q75 - q25) * 0.5
    for f in filas:
        f["leyendo"] = bool(f["head_y"] > umbral)
        marca = "  <-- LEYENDO" if f["leyendo"] else ""
        print(f"  {f['i']:3} [{f['start']:7.1f}-{f['end']:7.1f}] "
              f"cabeza {f['head_y']:.3f}{marca}")

    n = sum(1 for f in filas if f["leyendo"])
    print(f"\numbral {umbral:.3f} · {n} de {len(filas)} marcados como lectura")

    if args.out:
        json.dump({"umbral": umbral, "segmentos": filas},
                  open(args.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"→ {args.out}")
