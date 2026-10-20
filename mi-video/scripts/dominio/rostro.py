"""La cara: dónde caen los ojos, la boca y la barbilla, escena por escena.

`sujeto` sabe dónde está él —su silueta, la coronilla— y no dónde acaba su
cara. La barbilla se suponía: coronilla + 0,22 del cuadro, la altura de una cara
en un plano sentado (`punch-ins.ALTO_CARA`). Y la coronilla era una sola para
toda la pieza, la mediana de cuatro fotogramas. En el selfi de reel-19 la cara
ocupa el doble y la boca cae entre 0,56 y 0,74 del cuadro, así que el subtítulo
«pegado a la barbilla» —apoyado en 0,604— le tapaba la boca en las seis escenas,
y la hoja de contacto le decía al revisor que no (C-624). Jaime: *«los subtítulos
me tapan la cara»*, *«la hoja de contactos no está siendo efectiva»*.

Así que se mide, con el detector de caras de MediaPipe —el mismo origen que el
segmentador de `sujeto`—, **sobre el corte**, que es el cuadro que ve el
espectador, y **por escena**: ojos y boca son puntos del modelo, y la barbilla se
saca de ellos, porque de los ojos a la boca hay lo mismo, poco más o menos, que
de la boca a la barbilla. Lo guarda `sujeto.de_la_pieza` en el mismo
`cara.json`, con el mismo dueño y la misma frescura.
"""
from __future__ import annotations

import os

MODELO = os.path.join("models", "blaze_face_short_range.tflite")
#: Cuánto baja la barbilla por debajo de la boca, en múltiplos de ojos→boca.
#: Medido sobre cuatro fotogramas de reel-18 y reel-19, sentado, de perfil y en
#: selfi: con 0,9 la línea cae al final de la barba.
BARBILLA = 0.9
#: Por debajo de esto la detección no se cuenta.
CONFIANZA = 0.5


def en(video, momentos) -> dict | None:
    """`{ojos, boca, menton}` en fracción del alto del fotograma, o `None`.

    La mediana de los momentos donde se ve una cara; si no se ve en ninguno,
    `None`, y quien pregunta sigue con lo que tenía: no medir no es medir cero.
    """
    import numpy as np
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    from .sujeto import _fotograma

    if not os.path.exists(MODELO):
        return None
    opts = vision.FaceDetectorOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODELO),
        min_detection_confidence=CONFIANZA)
    ojos, bocas = [], []
    with vision.FaceDetector.create_from_options(opts) as det:
        for t in momentos:
            img = _fotograma(video, t, ancho=480)
            if img is None:
                continue
            r = det.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                    data=np.ascontiguousarray(img)))
            if not r.detections:
                continue
            d = max(r.detections,
                    key=lambda x: x.bounding_box.width * x.bounding_box.height)
            kp = d.keypoints
            ojos.append((kp[0].y + kp[1].y) / 2)
            bocas.append(kp[3].y)
    if not ojos:
        return None
    o, b = float(np.median(ojos)), float(np.median(bocas))
    return {"ojos": round(o, 3), "boca": round(b, 3),
            "menton": round(b + (b - o) * BARBILLA, 3), "visto": len(ojos)}


def por_escena(n, video, muestras=3) -> list:
    """`[{escena, beat, desde, hasta, coronilla, ojos, boca, menton}]` del corte.

    Las escenas son las de `trasfondo`, en la línea montada, para que la cara y
    el fondo de una escena se pregunten por el mismo número. Una escena donde no
    se ve nada no sale: quien la busque usa la medida de la pieza.
    """
    from .sujeto import donde_esta
    from .trasfondo import _escenas

    fuera = []
    for t in _escenas(n):
        largo = t["hasta"] - t["desde"]
        ts = [t["desde"] + largo * (k + 1) / (muestras + 1) for k in range(muestras)]
        cara, cuerpo = en(video, ts), donde_esta(video, ts)
        if cara or cuerpo:
            fuera.append({**t, **({"coronilla": cuerpo["coronilla"]} if cuerpo else {}),
                          **{k: v for k, v in (cara or {}).items() if k != "visto"}})
    return fuera
