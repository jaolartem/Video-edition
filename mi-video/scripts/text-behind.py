"""
Compone texto DETRAS del sujeto: el rotulo pasa por delante del fondo y la
figura queda sobrepuesta encima.

Como funciona
-------------
Tres capas por fotograma:

    fondo (el propio video)  ->  rotulo  ->  sujeto recortado

El recorte del sujeto sale de la segmentacion de MediaPipe (`ImageSegmenter` con
el modelo `selfie_segmenter`), pensada justo para esto: una persona en primer
plano sobre fondo estatico.

Por que se reparte el trabajo asi
---------------------------------
La tipografia la rinde Remotion y llega aqui como PNG con alfa. Podria dibujarse
con PIL, pero entonces el sistema visual viviria en dos sitios —fuentes, tracking
negativo, colores— y acabarian divergiendo. Remotion es la unica fuente de
verdad tipografica; este script solo apila capas.

Cuidados que no son obvios
--------------------------
- **La mascara se suaviza y se contrae un pixel.** El borde crudo de la
  segmentacion deja un halo del fondo original alrededor de la silueta, que
  sobre un rotulo de color canta muchisimo.
- **Se estabiliza en el tiempo.** La segmentacion parpadea entre fotogramas; sin
  promediar con el anterior, el borde del hombro vibra.

Uso:
    python scripts/text-behind.py --video public/hook-zoom.mp4 \\
        --titulo out/titulo.png --desde 5.0 --hasta 6.8 --out public/hook-behind.mp4
"""
import argparse
import os
import subprocess
import sys

import numpy as np

MODEL = os.path.join("models", "selfie_segmenter.tflite")


def crear_segmentador():
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    base = mp_python.BaseOptions(model_asset_path=MODEL)
    opts = vision.ImageSegmenterOptions(
        base_options=base,
        running_mode=vision.RunningMode.VIDEO,
        output_category_mask=False,
        output_confidence_masks=True,
    )
    return vision.ImageSegmenter.create_from_options(opts), mp


def suavizar(mask, prev, radio=2, contraer=1.5):
    """
    Limpia el borde de la mascara.

    Se contrae un poco y se difumina: el borde crudo arrastra un halo del fondo
    original que sobre un rotulo de color se ve inmediatamente. Y se promedia
    con el fotograma anterior porque la segmentacion parpadea, y sin eso el
    hombro vibra.
    """
    from scipy.ndimage import gaussian_filter
    m = gaussian_filter(mask, sigma=radio)
    m = np.clip((m - contraer * 0.08) / max(1e-6, 1 - contraer * 0.08), 0, 1)
    if prev is not None:
        m = 0.65 * m + 0.35 * prev
    return m


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--titulo", required=True, help="PNG con alfa")
    ap.add_argument("--desde", type=float, default=0.0)
    ap.add_argument("--hasta", type=float)
    ap.add_argument("--fade", type=float, default=0.25, help="entrada del rotulo, s")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(MODEL):
        raise SystemExit(f"Falta el modelo: {MODEL}")

    from PIL import Image

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,r_frame_rate:format=duration",
         "-of", "default=nw=1:nk=1", args.video],
        capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.split()
    W, H = int(probe[0]), int(probe[1])
    num, den = probe[2].split("/")
    fps = float(num) / float(den)
    dur = float(probe[3])
    hasta = args.hasta if args.hasta is not None else dur

    titulo = Image.open(args.titulo).convert("RGBA").resize((W, H))
    t_rgb = np.asarray(titulo)[:, :, :3].astype(np.float32)
    t_a = np.asarray(titulo)[:, :, 3].astype(np.float32) / 255.0

    seg, mp = crear_segmentador()

    lector = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", args.video,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)
    escritor = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
         "-i", "-", "-i", args.video,
         "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "copy", "-pix_fmt", "yuv420p", args.out],
        stdin=subprocess.PIPE)

    prev = None
    n = 0
    tam = W * H * 3
    while True:
        raw = lector.stdout.read(tam)
        if len(raw) < tam:
            break
        frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)
        t = n / fps

        if args.desde <= t <= hasta:
            img = mp.Image(image_format=mp.ImageFormat.SRGB,
                           data=np.ascontiguousarray(frame.astype(np.uint8)))
            res = seg.segment_for_video(img, int(t * 1000))
            # COPIA obligatoria: `numpy_view()` devuelve una vista a memoria de
            # MediaPipe que se libera al soltar el resultado. Usarla despues es
            # un use-after-free y revienta el proceso con violacion de segmento.
            m = np.array(res.confidence_masks[0].numpy_view(),
                         dtype=np.float32, copy=True)
            m = np.squeeze(m)   # llega como (H,W,1); sin esto la difusion rompe
            m = suavizar(m, prev)
            prev = m

            # Entrada del rotulo: lineal, como el resto del sistema.
            k = min(max((t - args.desde) / max(args.fade, 1e-3), 0.0), 1.0)
            alpha = (t_a * k)[:, :, None]

            fondo = frame * (1 - alpha) + t_rgb * alpha
            salida = fondo * (1 - m[:, :, None]) + frame * m[:, :, None]
        else:
            prev = None
            salida = frame

        escritor.stdin.write(np.clip(salida, 0, 255).astype(np.uint8).tobytes())
        n += 1
        if n % 30 == 0:
            print(f"  {n} fotogramas", file=sys.stderr, end="\r")

    escritor.stdin.close()
    escritor.wait()
    lector.wait()
    seg.close()
    print(f"\n{n} fotogramas -> {args.out}", file=sys.stderr)
