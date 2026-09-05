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
#: **Cuando el corte cae con la voz sonando.** No es lo mismo que «se puede
#: mejorar»: es que la palabra se parte y se oye. Medido sobre las siete piezas
#: —30 de 132 salidas—, los bordes que Jaime señaló como *«el corte se come el
#: final de las palabras»* estaban entre -7 y -14 dB; los limpios, por debajo
#: de -40. El suelo va en medio y con margen.
SUENA = -35.0
#: Cuánto se puede alargar un corte para que la palabra termine. Medio segundo
#: es una sílaba larga con su cola; más que eso ya no es cerrar la palabra, es
#: traerse la siguiente. **1,2 s y no 0,5**: medido, los bordes que quedaban
#: sucios necesitaban entre 700 y 1.255 ms, y si el audio sigue fuerte todo ese
#: rato es que la frase no ha terminado — que es exactamente lo que Jaime pide
#: Cuanto se puede alargar una salida para cerrar la palabra. **0,35 s: una
#: silaba larga, no una frase.**
#:
#: Estuvo en 1,2 s porque los bordes que quedaban sucios pedian entre 700 y
#: 1.255 ms — pero eso no era una palabra sin cerrar: era un corte a mitad de
#: habla continua, que es lo que un montaje hace. Con 1,2 s este paso **deshizo
#: un corte editorial**: Jaime quito la primera de las dos veces que dice «eso no
#: es mala suerte» en el gancho de reel-01, y la pasada siguiente la resucito
#: entera alargando el borde hasta el silencio de despues.
#:
#: Cerrar una palabra son decimas. Todo lo que pase de ahi es material, y el
#: material lo decide el corte, no un paso de limpieza.
ALARGA = 0.35


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

    def suena(self, t: float) -> float:
        """dBFS justo DESPUES de `t`. Por encima de `SUENA`, la voz sigue.

        **Y se mira despues, no antes.** Medirlo antes contaba como sucio todo
        corte que cierra una frase —que suene justo antes es lo normal, es la
        ultima silaba— y daba seis falsos positivos que pedian «+5 ms». Lo que
        parte una palabra no es que suene antes: es que **siga sonando
        despues**.
        """
        e = self.energia(t + 0.04)
        return 20 * math.log10(max(e, 1e-9))

    def donde_calla(self, t: float, maximo: float = ALARGA):
        """Hasta dónde estirar el corte para que la palabra acabe. `None` si ya.

        **Es la otra mitad de `mas_callado`, y hacía falta.** Aquélla busca el
        mínimo de una ventana de ±120 ms y se conforma con él: si dentro de esa
        ventana no hay silencio —porque la sílaba dura más— devuelve el punto
        menos malo y da el corte por bueno. Medido: 30 de 132 salidas quedaban
        así, cortando a -10 dB, o sea a pleno volumen.

        Aquí no se busca el mínimo: se avanza hasta que **deja de sonar**, que
        es lo que pidió Jaime —*«hay que dejar terminar la frase y ahí sí
        cortar, no por whisper, por sonido»*—. Y se avanza poco: `ALARGA` es
        medio segundo, lo que cierra una sílaba y no lo que trae la siguiente.
        """
        x, sr = self.muestras
        if x is None or self.suena(t) <= SUENA:
            return None
        fin, u = len(x) / sr, t
        while u <= t + maximo:
            if u >= fin:
                return None
            if 20 * math.log10(max(self.energia(u), 1e-9)) <= SUENA:
                return round(u + GRANO, 3)
            u += GRANO
        return None

    def __str__(self) -> str:
        return f"señal de {self.nombre}"
