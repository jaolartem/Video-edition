"""
Recorta al sujeto del plano para que algo pueda pasar POR DETRAS de el.

Dos salidas, el mismo recorte
-----------------------------
1. **El recorte solo, con alfa** (`--out ....webm`, sin `--titulo`). Es la que
   consume el render: una capa que Remotion apila encima de lo que quiera meter
   entre el plano y la figura. Ahi el elemento lo dibuja Remotion, que es donde
   vive el sistema visual, y este paso solo aporta la silueta.
2. **La composicion cerrada** (`--titulo`), que es como nacio esto: fondo,
   rotulo y sujeto apilados aqui y escritos a mp4.

La segunda **no es la que se usa** y conviene saber por que: componer fuera de
Remotion deja el rotulo escrito en el pixel, asi que no se puede mover, ni
sincronizar con la voz, ni cambiar sin volver a pasar MediaPipe por la pieza
entera. Y ademas Jaime ya puso el limite —*«el efecto se lucia a costa del
mensaje»*—: lo que cruza por detras es el ELEMENTO, no lo que hay que leer.
Queda porque sirve para probar la mascara de un vistazo.

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

El canto es de papel, no de tijera
----------------------------------
El recorte sale con el canto RASGADO. La receta —ruido de grano grueso sobre la
distancia al borde, orla clara de fibra de grosor variable, y **la semilla
constante en todos los fotogramas** o el canto hierve— vive en
[`dominio/papel.py`](dominio/papel.py), con el porque de cada numero. Aqui solo
se aplica por fotograma, que es lo que este fichero sabe hacer: apilar capas.

Cuidados que no son obvios
--------------------------
- **La mascara se suaviza y se contrae un pixel.** El borde crudo de la
  segmentacion deja un halo del fondo original alrededor de la silueta, que
  sobre un rotulo de color canta muchisimo.
- **Se estabiliza en el tiempo.** La segmentacion parpadea entre fotogramas; sin
  promediar con el anterior, el borde del hombro vibra.
- **Los doce escalones NO van aqui.** Los pone Remotion por fotograma
  (`src/components/Recorte.tsx`), que es donde el tratamiento —blanco y negro,
  color o sepia— se decide por etapa.

Uso:
    # el recorte del GANCHO: canto limpio, y deja su ficha con la coronilla
    python scripts/text-behind.py --video public/reel-01.mp4 --canto limpio \
        --desde 0 --hasta 5.2 --out public/recorte/reel-01-e1.webm

    # el recorte con alfa, que es lo que sirve el render
    python scripts/text-behind.py --video public/reel-05.mp4 \\
        --desde 0 --hasta 5 --out public/recorte/reel-05-e1.webm

    # la composicion cerrada, para mirar la mascara
    python scripts/text-behind.py --video public/hook-zoom.mp4 \\
        --titulo out/titulo.png --desde 5.0 --hasta 6.8 --out public/hook-behind.mp4
"""
import argparse
import os
import subprocess
import sys

import numpy as np

MODEL = os.path.join("models", "selfie_segmenter.tflite")

# La receta del canto de papel vive en su propio modulo: es una decision
# grafica aprobada con sus numeros, y aqui solo se aplica.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dominio.papel import (cabeza, coronilla, granos, estirar, limpiar,  # noqa: E402
                           mediana, nucleo, rango, rasgar, sobre_papel)


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


def _lector(video, desde, hasta, solo_ventana):
    """El video en crudo. En modo recorte se abre **solo la ventana**.

    La composicion tiene que escribir la pieza entera —lo de fuera de la ventana
    sale tal cual—, asi que ahi se lee todo. El recorte no: es una capa que
    empieza donde empieza y dura lo que dura, y decodificar noventa segundos
    para segmentar cinco es pagar dieciocho veces lo que cuesta.
    """
    corte = ["-ss", str(desde), "-to", str(hasta)] if solo_ventana else []
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", *corte, "-i", video,
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE)


def _escritor(video, out, W, H, fps, alfa):
    """A donde van los fotogramas.

    Con alfa es **VP9 en WebM** y sin audio: es el unico formato con canal alfa
    que Chromium reproduce, y Chromium es quien dibuja el render.

    Tres banderas que no son de gusto y cada una costo un render:

    - `-auto-alt-ref 0` y `-lag-in-frames 0`: con cuadros de referencia
      alternativos el plano alfa se pierde en los fotogramas que no son clave, y
      la capa sale **transparente a ratos** — el sujeto aparecia sobre el
      elemento en el fotograma 40 y desaparecia en el 60, sin error ninguno.
    - `-g 30`: un fotograma clave por segundo. El render extrae por tiempo, no
      reproduce, asi que un GOP largo obliga a decodificar desde muy atras.
    """
    if alfa:
        return subprocess.Popen(
            ["ffmpeg", "-v", "error", "-y",
             "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}",
             "-r", str(fps), "-i", "-",
             "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
             "-lag-in-frames", "0", "-g", "30",
             "-b:v", "0", "-crf", "30", "-row-mt", "1", "-an", out],
            stdin=subprocess.PIPE)
    return subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps),
         "-i", "-", "-i", video,
         "-map", "0:v", "-map", "1:a?",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-c:a", "copy", "-pix_fmt", "yuv420p", out],
        stdin=subprocess.PIPE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--titulo", help="PNG con alfa; sin el sale SOLO el recorte")
    ap.add_argument("--desde", type=float, default=0.0)
    ap.add_argument("--hasta", type=float)
    ap.add_argument("--fade", type=float, default=0.25, help="entrada del rotulo, s")
    #: **Dos cantos, y el sitio donde se compone decide cual.** `papel` es el
    #: del collage: orla de fibra clara, para un recorte que aterriza sobre una
    #: placa. `limpio` es el del GANCHO, que se compone sobre el mismo plano del
    #: que salio - ahi la orla dibuja una silueta blanca sobre su propia foto y
    #: se lee como pegatina. Ver `dominio/papel.py :: limpiar`.
    ap.add_argument("--canto", choices=("papel", "limpio"), default="papel")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(MODEL):
        raise SystemExit(f"Falta el modelo: {MODEL}")

    #: Sin titulo la salida es la silueta con alfa: el elemento lo pone Remotion.
    ALFA = not args.titulo

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

    if not ALFA:
        from PIL import Image

        titulo = Image.open(args.titulo).convert("RGBA").resize((W, H))
        t_rgb = np.asarray(titulo)[:, :, :3].astype(np.float32)
        t_a = np.asarray(titulo)[:, :, 3].astype(np.float32) / 255.0
    if ALFA:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    seg, mp = crear_segmentador()

    lector = _lector(args.video, args.desde, hasta, ALFA)
    escritor = _escritor(args.video, args.out, W, H, fps, ALFA)

    # Los dos campos de ruido se generan UNA vez para toda la pasada. Ver
    # `granos`: es lo que hace que el canto sea de papel y no hierva.
    grano, fibra = granos(H, W)
    # El tramo util se mide en el primer fotograma con mascara y se queda:
    # ver `rango`. Medirlo en cada uno movería los escalones de sitio.
    tramo = None

    prev = None
    #: Donde empieza su pelo en cada fotograma. Lo consume el gancho para
    #: saber hasta donde puede bajar el rotulo; ver la ficha del final.
    altas = []
    #: Y que columnas ocupa su cabeza, que es lo que decide de que lado del
    #: cuadro cae el bloque. Misma pasada, misma mascara.
    anchas = []
    n = 0
    tam = W * H * 3
    while True:
        raw = lector.stdout.read(tam)
        if len(raw) < tam:
            break
        frame = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32)
        # En modo recorte el lector ya viene cortado, asi que el fotograma 0 es
        # el segundo `--desde` y no el 0 de la pieza.
        t = n / fps + (args.desde if ALFA else 0.0)

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
            # El rasgado sale de la mascara de ESTE fotograma —una fija
            # recortaria en cuanto el se mueve— y del ruido de siempre.
            dentro = nucleo(m)
            alfa, orla = rasgar(dentro, grano, fibra)
            if tramo is None:
                tramo = rango(frame, dentro)

            if ALFA and args.canto == "limpio":
                # **El plano tal cual, con la silueta por alfa.** Ni mediana ni
                # estirado: el gancho apila esto ENCIMA del mismo fotograma, asi
                # que cualquier retoque de niveles partiria la cara en dos
                # versiones de si misma, una recortada sobre la otra. Lo unico
                # que cambia respecto al plano es que aqui hay alfa.
                salida = np.dstack([frame, limpiar(dentro) * 255.0])
                y = coronilla(dentro)
                if y is not None:
                    altas.append(y)
                x = cabeza(dentro)
                if x is not None:
                    anchas.append(x)
            elif ALFA:
                # El color es el del plano y el alfa es el canto rasgado:
                # apilado sobre el mismo fotograma, el sujeto queda exactamente
                # donde estaba. La mediana va antes de escribir porque lo que
                # sale de aqui es lo que Remotion escalona.
                salida = sobre_papel(estirar(mediana(frame), tramo),
                                     alfa, orla)
            else:
                # Entrada del rotulo: lineal, como el resto del sistema.
                k = min(max((t - args.desde) / max(args.fade, 1e-3), 0.0), 1.0)
                alpha = (t_a * k)[:, :, None]

                fondo = frame * (1 - alpha) + t_rgb * alpha
                a = np.clip(alfa + orla, 0.0, 1.0)[:, :, None]
                salida = fondo * (1 - a) + frame * a
        else:
            prev = None
            # Fuera de la ventana no hay sujeto que recortar: la capa es
            # transparente entera, que es lo que deja ver el plano de debajo.
            salida = np.dstack([frame, np.zeros((H, W), np.float32)]) if ALFA \
                else frame

        escritor.stdin.write(np.clip(salida, 0, 255).astype(np.uint8).tobytes())
        n += 1
        if n % 30 == 0:
            print(f"  {n} fotogramas", file=sys.stderr, end="\r")

    escritor.stdin.close()
    escritor.wait()
    lector.wait()
    seg.close()

    # **La ficha del recorte, al lado del recorte.**
    #
    # El gancho pone el rotulo DETRAS de su cabeza, asi que donde acaba el
    # bloque lo decide donde empieza su pelo - y eso cambia de pieza a pieza y
    # dentro de la misma toma. Aqui esta medido sobre la mascara de la ventana
    # entera, que es el unico sitio donde ese dato existe; deducirlo en el
    # render seria adivinarlo.
    #
    # Se guarda la coronilla MAS ALTA de la ventana y no la media: con la media
    # el rotulo se come la cara justo en el fotograma en que el se inclina, que
    # es lo que se vio al mirar el primer still de reel-01.
    if ALFA and altas:
        import json

        ficha = os.path.splitext(args.out)[0] + ".json"
        datos = {"coronilla": round(min(altas), 4),
                 "canto": args.canto,
                 "fotogramas": n}
        # **La cabeza va por la MEDIANA y la coronilla por el extremo**, y no es
        # descuido: la coronilla decide hasta donde puede bajar el bloque, asi
        # que el fotograma en que el se inclina manda. El lado no se decide
        # fotograma a fotograma —el bloque no salta de lado a mitad de gancho—,
        # asi que lo que hace falta es donde esta la cabeza en la ventana.
        if anchas:
            datos["cabeza"] = [round(float(np.median([a[0] for a in anchas])), 4),
                               round(float(np.median([a[1] for a in anchas])), 4)]
        with open(ficha, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, indent=1)
        print(f"coronilla {min(altas):.3f} cabeza {datos.get('cabeza')}"
              f" -> {ficha}", file=sys.stderr)
    print(f"\n{n} fotogramas -> {args.out}", file=sys.stderr)
