"""El tono de la señal: F0 medido sobre la onda, antes de que signifique nada.

**Por qué está separado de `voz`.** Aquí no se juzga nada — se extrae un
contorno de frecuencia fundamental de un trozo de cinta. Que ese contorno
signifique «viva», «plana» o «tibia» es de `dominio.voz`, y son dos oficios
distintos: éste falla por ffmpeg y por falta de audio, aquél por lo que la
medida quiere decir. Mezclados, un tramo que no se pudo medir salía indistinguible
de uno medido y apagado.

**Y «no medido» se dice con `None`, siempre.** Un tramo de cero segundos hacía
abortar a ffmpeg —«-to value smaller than -ss»— y `check=True` lo convertía en
excepción; el mismo hecho —«no se puede medir»— salía unas veces como `None` y
otras como una excepción, y quien llamaba tenía que acertar con cuál. Dos
representaciones de un mismo hecho es la familia de C-63.
"""
from __future__ import annotations

import os
import subprocess
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rutas  # noqa: E402

#: Lo que la medida de F0 necesita para existir, en segundos.
#:
#: **Es la precondicion de la medida, y por eso es un dato publico.** Estaba
#: escondida como `x.size < 16000` despues de haber gastado un ffmpeg, asi que
#: la unica forma de saber que una ventana no se podia medir era pedirla y
#: recibir `None`. Quien pregunta no distingue eso de «se midio y salio bajo».
#:
#: Sale de la autocorrelacion: ventanas de 40 ms con salto de 20 ms y un minimo
#: de 8 ventanas con voz. Un segundo de audio es el suelo por debajo del cual
#: no hay F0 que promediar, se haga como se haga.
VENTANA_MIN = 1.0


def cabe(a, b):
    """Si ese tramo da para medir. La precondicion, preguntable antes de gastar."""
    return (b - a) >= VENTANA_MIN


def _octava(f, med):
    """Baja o sube la muestra hasta la octava de la mediana."""
    while f > 1.6 * med:
        f /= 2
    while f < 0.62 * med:
        f *= 2
    return f


def a_la_octava(hz, referencia):
    """Lleva una altura a la octava de otra, para poder restarlas.

    `contorno` corrige cada tramo contra SU mediana, asi que dos ventanas
    distintas pueden quedar en octavas distintas y la diferencia sale de 18
    semitonos, que es imposible en una voz. Es el aprendizaje 15 aplicado a la
    comparacion: el filtro de plausibilidad no basta si el error es
    sistematico, hay que corregirlo.
    """
    while hz > referencia * 1.6:
        hz /= 2.0
    while hz < referencia / 1.6:
        hz *= 2.0
    return hz


def contorno(toma, a, b):
    """El contorno de F0 del tramo, en Hz y ya corregido de octava.

    Estaba dentro de `expresividad` y sale aqui porque **la altura y el
    movimiento son dos cosas distintas**: una lectura monotona puede tener un
    recorrido amplio si deriva despacio de grave a agudo, y sonar plana igual.
    Para saber si hay *cambio de tono* hace falta el contorno, no su rango.

    **Una ventana que no llega al minimo se contesta aqui, no en ffmpeg.** Ver
    la cabecera del modulo: `None` es «no se pudo medir», y es la unica forma
    que tiene de decirlo.
    """
    if not cabe(a, b):
        return None
    # **Un fichero por llamada, no uno para todas.** Esto escribia siempre
    # `exp.wav`, y con dos procesos midiendo a la vez —la linea avanzando piezas
    # en segundo plano y una consulta a mano— uno lee lo que el otro esta
    # escribiendo: `EOFError` en mitad de una corrida, intermitente y sin decir
    # de donde viene. Aparecio tres veces esta sesion antes de que mirara el
    # nombre del fichero.
    #
    # El nombre lleva el proceso y el tramo, asi que dos medidas nunca compiten
    # y ademas se puede saber de quien es un temporal que quedo suelto.
    wav = (f"{rutas.TEMPORAL}/f0-{os.getpid()}-"
           f"{abs(hash((toma, round(a, 2), round(b, 2)))) % 10**8}.wav")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-to", str(b),
                        "-i", f"{rutas.ORIGEN}/{toma}.mp4", "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", wav], check=True)
        with wave.open(wav) as w:
            x = np.frombuffer(w.readframes(w.getnframes()),
                              dtype=np.int16).astype(float)
    finally:
        # No se deja basura: son cientos de recortes por corrida.
        try:
            os.remove(wav)
        except OSError:
            pass
    # El mismo suelo que `cabe`, ahora sobre lo que ffmpeg devolvio de verdad:
    # un tramo puede pedirse largo y salir corto si cae al final de la cinta.
    if x.size < 16000 * VENTANA_MIN:
        return None
    # F0 por autocorrelacion en ventanas de 40 ms.
    sr, n, f0 = 16000, 640, []
    for i in range(0, len(x) - n, n // 2):
        v = x[i:i + n] - x[i:i + n].mean()
        if np.sqrt((v ** 2).mean()) < 250:
            continue
        c = np.correlate(v, v, "full")[n - 1:]
        lo, hi = sr // 320, sr // 70          # 70-320 Hz, rango de voz
        if hi >= len(c):
            continue
        k = int(np.argmax(c[lo:hi])) + lo
        if c[k] > 0.3 * c[0]:
            f0.append(sr / k)
    if len(f0) < 8:
        return None
    f0 = np.array(f0)

    # **Doblado de octava.** El detector engancha a veces el primer armónico y
    # devuelve el doble: en una toma la mediana daba 117 Hz y el percentil 90
    # daba 208 — exactamente el doble del percentil 10. Sin corregirlo el
    # recorrido salía en 14 semitonos, el filtro de plausibilidad lo tiraba, y
    # TODAS las tomas puntuaban cero: la expresividad dejaba de decidir nada.
    #
    # Es el aprendizaje 15 otra vez, y por eso el filtro no basta: descarta el
    # número malo, pero si el error es sistemático descarta todos.
    med = np.median(f0)
    return np.array([_octava(f, med) for f in f0])
