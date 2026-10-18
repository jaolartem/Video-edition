"""Los OJOS de quien compone sobre una repeticion. **No decide: mide.**

Jaime, cuando esto empezaba a convertirse en una regla de codigo:

> *«La redundancia es editorial y la repeticion es una excepcion: tiene que ser
> algo muy esporadico y completamente intencional, y se debe notar intencional;
> de lo contrario la repeticion es ruido. Eso no debe ir en codigo, debe ir en
> composicion. Nosotros pusimos ojos y oidos al LLM, pero nada de eso se puede
> utilizar sin criterio editorial.»*

Asi que este modulo **no corta nada y no bloquea nada**. Contesta una pregunta
que el oido no puede contestar con precision —cuanto sube el tono y cuanto el
volumen entre la primera entrega y la segunda— y devuelve los numeros. Quien
compone mira eso y decide; si decide que la repeticion se queda, se queda.

## La vara editorial, que es de Jaime y no de aqui

Una repeticion vale cuando **se nota intencional**. Sus condiciones: siempre
dentro de una misma toma —quitar el hueco entre las dos vale—, y ademas o esta
en el libreto o la segunda golpea mas fuerte: sube el tono y sube el volumen.

Lo que este modulo aporta a esa vara es el «cuanto». El «si» es de quien compone.

## Y por que los ojos tienen que ser sencillos

Jaime: *«mientras mas sencillos y elegantes y sobre todo eficaces sean los ojos
y los oidos del LLM, mejor»*. Aqui eso son dos medidas y nada mas — dBFS medio y
mediana de F0— sobre los dos tramos. Sin umbrales que decidan, sin veredicto
escondido en un booleano.
"""
from __future__ import annotations

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import f0  # noqa: E402

#: Cuánto tiene que subir el tono para contar como que golpea más fuerte, en
#: semitonos. Medio semitono es la variación normal entre dos frases seguidas;
#: por debajo de eso no hay intención, hay ruido de medida.
SUBE_TONO = 0.5

#: Y cuánto el volumen, en dB. Un decibelio es el umbral por debajo del cual el
#: oído no distingue dos frases de la misma voz.
SUBE_VOLUMEN = 1.0


def _volumen(toma: str, a: float, b: float):
    """dBFS medio del tramo. `None` si no se pudo medir."""
    if b - a < 0.05:
        return None
    import rutas  # la cinta se le pregunta a `rutas`, no se escribe (C-548)
    ruta = (rutas.angulos(toma) or [""])[0]
    if not ruta or not os.path.exists(ruta):
        return None
    try:
        salida = subprocess.run(
            ["ffmpeg", "-hide_banner", "-nostats", "-ss", f"{a:.3f}",
             "-to", f"{b:.3f}", "-i", ruta, "-af", "volumedetect",
             "-f", "null", "-"],
            capture_output=True, text=True).stderr
    except OSError:
        return None
    for linea in salida.splitlines():
        if "mean_volume:" in linea:
            try:
                return float(linea.split("mean_volume:")[1].split("dB")[0])
            except ValueError:
                return None
    return None


def _tono(toma: str, a: float, b: float):
    """Mediana de F0 del tramo, en Hz. `None` si no se pudo medir."""
    try:
        c = f0.contorno(toma, a, b)
    except Exception:                              # noqa: BLE001
        return None
    # **`None` es «no se pudo medir», y no se aplana a cero.** `contorno`
    # devuelve `None` cuando el tramo no llega a su ventana —una frase de 0,8 s
    # no da para medir F0— y eso NO es lo mismo que un tono que no sube. Si se
    # confundieran, toda repeticion corta se declararia error de edicion sin
    # haberla medido.
    if c is None:
        return None
    # Es un array de numpy: `if not c` revienta con «truth value is ambiguous».
    # `contorno` devuelve un array de numpy: `if not c` sobre eso revienta con
    # «truth value is ambiguous». Se recorre y se filtran los ceros a mano.
    vals = sorted(float(v) for v in c if v and float(v) > 0)
    return vals[len(vals) // 2] if vals else None


def medir(toma: str, primera: tuple, segunda: tuple):
    """Cuanto sube la segunda entrega respecto a la primera. Nada mas.

    `primera` y `segunda` son `(desde, hasta)` en segundos de la cinta.

    Devuelve los numeros y la vara contra la que se leen — **no un veredicto**.
    Antes devolvia `vale: True/False` y un `por_que` que decia «error de
    edicion», y eso es decidir: el criterio es editorial y lo pone quien compone.

    `None` en tono significa que el tramo no llega a la ventana de F0 (1 s), no
    que el tono no suba. Son cosas distintas y se dicen distinto.
    """
    import math

    v1, v2 = _volumen(toma, *primera), _volumen(toma, *segunda)
    t1, t2 = _tono(toma, *primera), _tono(toma, *segunda)
    return {
        "volumen_1": v1, "volumen_2": v2,
        "sube_dB": None if v1 is None or v2 is None else round(v2 - v1, 1),
        "tono_1": t1, "tono_2": t2,
        "sube_semitonos": (round(12 * math.log2(t2 / t1), 1)
                           if t1 and t2 else None),
        "dura_1": round(primera[1] - primera[0], 2),
        "dura_2": round(segunda[1] - segunda[0], 2),
        "la_vara": "Una repeticion vale si se NOTA intencional: misma toma, y ademas o esta en el libreto o la segunda golpea mas fuerte —sube tono Y volumen—. El cuanto lo dan estos numeros; el si es tuyo.",
    }
