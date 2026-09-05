"""Donde esta EL SUJETO en un fotograma, recortandolo del fondo.

Jaime, al ver su cara debajo de los titulos: *«¿y esas guardas de que protegen,
si lo que hacen es poner mi cara debajo de los titulos?»*. Y la respuesta,
despues de mirarlo: de nada, porque median mal.

## Por que no vale el movimiento

`punch-ins.py` localiza al sujeto por el **centroide del movimiento**: en camara
fija, lo que se mueve es la persona. Es barato y funciona en la mesa de trabajo.

En el sofa no. En la sesion de noche tambien se mueven **la cortina y la
lampara**, y el percentil 15 de la mascara de movimiento sube con ellas. Medido
contra el render de reel-06: el ancla decia que su coronilla caia en **0,318** del
cuadro y esta en **0,435**. Doscientos veinticinco pixeles, y con ese numero se
coloca la banda de subtitulos, la ventana de las placas y los paneles.

Su propio docstring ya avisaba —*«sigue siendo heuristica: si hay algo moviendose
de fondo, se equivoca»*— y nadie comprobo nunca cuanto.

## Que hace esto en su lugar

Segmenta a la persona con MediaPipe —el mismo `selfie_segmenter` que ya usa
`text-behind.py` para pasar el rotulo por detras de el— y devuelve el borde
superior de la silueta. Una cortina no es una persona, asi que no entra en la
mascara por mucho que se mueva.

No sustituye al ancla de `punch-ins`: **la comprueba**. El recorte se sigue
calculando igual; lo que cambia es que ahora se sabe si salio donde decia.

    python scripts/dominio/sujeto.py --video public/reel-06.mp4 --en 6.5
"""
import os
import subprocess
import sys

MODELO = os.path.join("models", "selfie_segmenter.tflite")
#: Por debajo de esto la mascara no es una persona: es ruido con forma. La
#: segmentacion devuelve confianza por pixel, y el fondo de una habitacion en
#: penumbra puntua bajo pero no cero.
SEGURO = 0.6
#: Cuantas filas seguidas tienen que dar sujeto para llamarlo coronilla. Un pixel
#: suelto en el techo es un artefacto; doce filas son una cabeza.
FILAS = 12


def _fotograma(video, t, ancho=270):
    """Un fotograma en RGB, pequeno. La silueta no necesita resolucion."""
    import numpy as np

    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
         "-vf", f"scale={ancho}:-1,format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    if not crudo:
        return None
    alto = len(crudo) // (ancho * 3)
    if alto < 10:
        return None
    return np.frombuffer(crudo[:ancho * alto * 3],
                         dtype=np.uint8).reshape(alto, ancho, 3)


def donde_esta(video, momentos):
    """La franja que ocupa el sujeto, en fracciones del cuadro.

    Devuelve `{coronilla, pies, visto}` promediado sobre los momentos que se
    pidan, o `None` si no se pudo segmentar ninguno. `visto` dice en cuantos
    salio, que es lo que distingue una medida de una casualidad.
    """
    import numpy as np

    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError:
        return None
    if not os.path.exists(MODELO):
        return None

    opts = vision.ImageSegmenterOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODELO),
        running_mode=vision.RunningMode.IMAGE,
        output_confidence_masks=True)
    arriba, abajo = [], []
    with vision.ImageSegmenter.create_from_options(opts) as seg:
        for t in momentos:
            img = _fotograma(video, t)
            if img is None:
                continue
            m = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                                     data=np.ascontiguousarray(img)))
            mask = m.confidence_masks[0].numpy_view()
            filas = (mask >= SEGURO).sum(axis=1)
            # Una fila cuenta como sujeto si al menos el 2% de su ancho lo es:
            # asi un borde de cortina mal segmentado no arrastra la coronilla.
            hay = filas >= max(3, mask.shape[1] * 0.02)
            if hay.sum() < FILAS:
                continue
            ys = np.nonzero(hay)[0]
            # La coronilla es la primera fila con FILAS seguidas por debajo.
            for i in range(len(ys) - FILAS):
                if ys[i + FILAS - 1] - ys[i] == FILAS - 1:
                    arriba.append(ys[i] / mask.shape[0])
                    abajo.append(ys[-1] / mask.shape[0])
                    break
    if not arriba:
        return None
    return {"coronilla": round(float(np.median(arriba)), 3),
            "pies": round(float(np.median(abajo)), 3),
            "visto": len(arriba)}


def de_la_pieza(n, muestras=4):
    """Mide la pieza YA CORTADA y guarda el resultado donde el spec lo lee.

    Se mide sobre `public/reel-NN.mp4` y no sobre la cinta a proposito: ahi ya
    estan aplicados el recorte, el encuadre y el acercamiento, asi que lo que
    sale es **donde queda su cara en el cuadro que ve el espectador** — que es la
    unica pregunta que importaba y la que el ancla de movimiento contestaba mal.

    Se guarda en `work/scenes/reel-NN/cara.json` porque cuesta unos segundos por
    pieza y el spec se arma muchas veces. Se rehace cuando se rehace el corte.
    """
    import json

    video = f"public/reel-{n:02d}.mp4"
    if not os.path.exists(video):
        return None
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip())
    ts = [dur * (i + 1) / (muestras + 1) for i in range(muestras)]
    m = donde_esta(video, ts)
    if not m:
        return None
    d = os.path.join("work", "scenes", f"reel-{n:02d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cara.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    return m


def main():
    import argparse
    import json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video")
    p.add_argument("--en", type=float, nargs="+", help="segundos donde mirar")
    p.add_argument("piezas", nargs="*", type=int,
                   help="numeros de pieza: mide el corte y guarda")
    a = p.parse_args()
    if a.video and a.en:
        print(json.dumps(donde_esta(a.video, a.en), ensure_ascii=False))
        return
    for n in a.piezas or range(1, 8):
        m = de_la_pieza(n)
        print(f"R{n}: {json.dumps(m, ensure_ascii=False) if m else 'sin corte'}")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
