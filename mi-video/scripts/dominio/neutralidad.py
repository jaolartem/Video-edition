"""El punto cero de una cinta: cómo suena esa persona cuando no está transmitiendo.

**Por qué no vive dentro de `Voz`.** La neutralidad no es de un tramo, es de la
grabación entera: su altura media y su velocidad media. Medirla por tramo sería
medir cada trozo contra sí mismo, que es no medir nada. La misma frase dicha por
dos personas no compara; dicha por la misma persona en dos momentos, sí — y eso
es exactamente lo que `Voz.intensidad` necesita para poder decir «esto está lejos
de su tibio».
"""
from __future__ import annotations

import json
import os

import numpy as np

from . import f0 as _f0

#: La neutralidad de cada cinta, calculada una vez por proceso.
_BASE = {}


def de(toma, palabras):
    """La neutralidad de ESTA cinta: su altura y su velocidad medias.

    Se calcula una vez por cinta y se cachea: es el punto cero contra el que se
    mide la intensidad, y tiene que ser el suyo.

    **En disco, no solo en memoria.** Extraer el F0 de una cinta entera cuesta
    medio minuto, y `seleccionar.py` corre una vez por reel: sin cachearlo se
    pagan tres minutos por corrida para calcular seis veces lo mismo.
    """
    if toma in _BASE:
        return _BASE[toma]
    cache = os.path.join("work", "baseline", f"{toma}.json")
    if os.path.exists(cache):
        _BASE[toma] = json.load(open(cache, encoding="utf-8"))
        return _BASE[toma]
    f0 = _f0.contorno(toma, 0, 9e9)
    alt = float(np.median(f0)) if f0 is not None and len(f0) else 0.0
    if palabras and len(palabras) > 20:
        dur = palabras[-1]["end"] - palabras[0]["start"]
        vel = len(palabras) / max(dur, 1e-6)
    else:
        vel = 0.0
    _BASE[toma] = {"altura": alt, "velocidad": vel}
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(_BASE[toma], open(cache, "w", encoding="utf-8"))
    return _BASE[toma]


def _hablado(toma, a, b):
    """Cuantos segundos de ese tramo son voz de verdad, segun el audio.

    Privada del paquete: la usa `voz.intensidad`, que es la unica pregunta para
    la que existe. El guion delante no es un descuido — dice que no es una
    puerta publica, y por eso `voz` la importa por su nombre y no la reexpone.

    Los tramos de `work/cuts/<toma>.json` los midio el detector de silencio
    sobre la onda, asi que dicen donde hay voz **independientemente de lo que
    el alineador haya hecho con las marcas de palabra**. Si no estan, se cae al
    span entero: peor medida, pero medida.
    """
    try:
        runs = json.load(open(f"work/cuts/{toma}.json",
                              encoding="utf-8"))["segmentos"]
    except Exception:                              # noqa: BLE001
        return max(b - a, 1e-6)
    t = sum(max(0.0, min(b, y) - max(a, x)) for x, y in runs)
    # Nunca cero: un tramo sin voz medida se trata como el span, y ya lo dira
    # la intensidad quedandose baja.
    return t if t > 0.2 else max(b - a, 1e-6)
