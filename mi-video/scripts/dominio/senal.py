"""La señal de una cinta: dónde suena fuerte y **dónde calla**.

**Por qué es un objeto.** Un corte no se pone a mitad de vocal. Jaime, después
de verlo volver: *«los cortes siguen solapando palabras, no están limpios»*, y
acto seguido lo que lo cierra: *«pero si eso ya lo hemos pasado al menos unas 20
veces; eso debe estar en código»*.

Y no exige entender ninguna frase, que es lo que decide si algo puede ir en
código: un corte suena mal cuando cae donde el audio está fuerte —en medio de
una vocal— y limpio cuando cae en un mínimo de energía. Eso se mide en la onda.

**Por qué no basta con ir a la frontera de palabra** (C-135, C-137): esa
frontera la dice el transcript, y el transcript entra 0,25 s tarde de mediana y
sale 0,05-0,14 s pronto, con 0,7 s de dispersión entre p10 y p90 sobre las ocho
cintas. Donde el texto dice que acaba la palabra no es donde deja de sonar. Aquí
no se le pregunta al texto.

Es la vecina de `dominio.f0`, no su repetición: allí se mide **altura** sobre el
mp4 con ffmpeg, y aquí **energía** sobre el wav ya extraído. Dos preguntas
distintas sobre el mismo sonido.
"""
from __future__ import annotations

import math
import os

#: Cuánto se permite mover un corte buscando silencio: ±120 ms. No cambian lo
#: que se dice, sólo dónde se pega la tijera.
VENTANA = 0.12
#: Cada cuánto se prueba dentro de la ventana, y sobre cuánto se mide el RMS.
GRANO = 0.005
MEDIDA = 0.020
#: **Las dos barras, y son distintas a propósito.** `GANA` es cuándo MERECE LA
#: PENA mover: mejorar es gratis. `PUERTA` es cuándo el corte SE OYE sucio, y es
#: la que usa la verificación — exigirle el óptimo a una pieza es no dejarla
#: salir nunca.
GANA = 3.0
PUERTA = 12.0


class Senal:
    """La onda de la cinta `nombre`, entera y en memoria.

    Se lee **una vez por cinta**: son grabaciones de media hora y se pregunta
    por cada uno de los cortes de cada pieza.
    """

    __slots__ = ("nombre",)

    _CACHE: dict = {}

    def __init__(self, nombre) -> None:
        self.nombre = str(nombre or "")

    @property
    def muestras(self):
        """`(muestras, sr)`, o `(None, None)` si esta cinta no tiene audio."""
        if self.nombre not in Senal._CACHE:
            Senal._CACHE[self.nombre] = self._leer()
        return Senal._CACHE[self.nombre]

    def _leer(self):
        import wave

        try:
            import numpy as np
        except ImportError:                                # noqa: BLE001
            return None, None
        ruta = next((c for c in (f"work/audio/{self.nombre}_full.wav",
                                 f"work/audio/{self.nombre}.wav")
                     if os.path.exists(c)), None)
        if ruta is None:
            return None, None
        with wave.open(ruta, "rb") as f:
            sr = f.getframerate()
            x = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16)
            if f.getnchannels() > 1:
                x = x.reshape(-1, f.getnchannels()).mean(axis=1)
        return x.astype(np.float32) / 32768.0, sr

    def energia(self, t: float) -> float:
        """RMS sobre `MEDIDA` segundos centrados en `t`."""
        import numpy as np

        x, sr = self.muestras
        if x is None:
            return 0.0
        a = int(max(0, (t - MEDIDA / 2) * sr))
        b = int(min(len(x), (t + MEDIDA / 2) * sr))
        return float(np.sqrt(np.mean(x[a:b] ** 2))) if b > a else 0.0

    def mas_callado(self, t: float) -> tuple[float, float]:
        """El punto más callado a menos de `VENTANA` de `t`, y cuántos dB gana.

        **La ventana se ancla al corte que trae el montaje, no al ya movido.**
        Sin eso el paso no converge: cada movimiento arrastra la ventana con él,
        la nueva abre territorio que la vieja no cubría, y a la pasada siguiente
        vuelve a haber dónde bajar — 21 cortes movidos, luego 10, luego 6, cada
        vez la mitad y nunca cero.

        Anclada, la respuesta es un punto fijo: el mínimo de un intervalo que no
        se mueve. Correrlo dos veces da lo mismo, y **ése es el contrato entre el
        paso y la puerta**, que pregunta por este mismo código en seco.
        """
        x, sr = self.muestras
        if x is None:
            return t, 0.0
        aqui = self.energia(t)
        if aqui <= 1e-6:
            return t, 0.0
        fin, mejor, mejor_e, u = len(x) / sr, t, aqui, t - VENTANA
        while u <= t + VENTANA:
            if 0 < u < fin:
                e = self.energia(u)
                if e < mejor_e:
                    mejor, mejor_e = u, e
            u += GRANO
        if mejor_e <= 0 or aqui / max(mejor_e, 1e-9) < 10 ** (GANA / 20):
            return t, 0.0
        return round(mejor, 3), 20 * math.log10(aqui / max(mejor_e, 1e-9))

    def __str__(self) -> str:
        return f"señal de {self.nombre}"
