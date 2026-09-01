"""La voz de un tramo: si está viva, si se mueve, si transmite — y si se nota al
unirla con otra.

Orden de prioridad de Jaime: *«lo más importante es el mensaje, lo que se dice;
luego cómo se dice; luego cómo se ve»*. Esto es el segundo peldaño —**cómo se
dice**— y por eso no elige nada: mide, y quien elige decide qué hacer con la
medida.

## «No medido» no es «medido y bajo»

Es la avería que este objeto viene a cerrar. `expresividad` y `cambio_de_tono`
devolvían `0.0` tanto cuando la voz salía plana como cuando **no se pudo medir**
—ventana corta, poca energía sonora, el detector saltando de octava—, y los dos
casos son opuestos: uno dice «esta toma no transmite» y el otro dice «no lo sé».
Con el mismo número, un tramo sin medir entraba en las comparaciones como el
peor posible; en `costuras.py` arrastraba la media de una unión hacia abajo y
descartaba el empalme bueno.

Aquí **`None` es «no lo sé» y cualquier float es una medida de verdad.** Y la
regla vale hacia dentro: `expresividad` no puede devolver 0,0, porque un
recorrido por debajo de 0,2 st no es una voz plana, es el detector sin material.
"""
from __future__ import annotations

import dataclasses

import numpy as np

from . import f0 as _f0
from . import neutralidad as _cero
from .neutralidad import _hablado

# Lo que hace falta para que una union **se oiga**. Estaban en la prosa de
# `salto` —«por debajo de ~2 st y de ~1,5 pal/s pasa desapercibido»— y una cifra
# que solo vive en un comentario no la puede usar nadie: la segunda valoracion
# necesita descontar por costura audible, y para eso el umbral tiene que ser un
# dato del modulo, no una frase.
SALTO_TONO = 2.0        # semitonos de diferencia de altura media
SALTO_RITMO = 1.5       # palabras por segundo


@dataclasses.dataclass(frozen=True, slots=True)
class Voz:
    """Lo que se oye entre `desde` y `hasta` de la cinta `cinta`.

    Mismo orden de campos que `Tramo` a proposito: es el mismo trozo de cinta
    visto por otra vara. `ritmo` es la unica medida que no necesita el audio —se
    cuenta sobre las palabras—, y por eso `cinta` puede ir vacia.
    """

    desde: float
    hasta: float
    cinta: str = ""

    # ── lo que se extrae de la señal ─────────────────────────────────────────
    @property
    def contorno(self):
        """El contorno de F0, o `None` si no se pudo medir. Ver `dominio.f0`."""
        return _f0.contorno(self.cinta, self.desde, self.hasta)

    @property
    def medible(self) -> bool:
        """Si el tramo da para medir F0, **antes** de gastar un ffmpeg."""
        return _f0.cabe(self.desde, self.hasta)

    @property
    def altura(self):
        """La altura media del tramo en Hz, o `None`. Lo que se compara al cruzar."""
        f0 = self.contorno
        if f0 is None or not len(f0):
            return None
        m = float(np.median(f0))
        return m if m > 0 else None

    # ── lo que dice esa señal de la entrega ──────────────────────────────────
    @property
    def expresividad(self):
        """Cuánta vida tiene la voz, en semitonos de recorrido de F0. `None` si
        no se pudo medir.

        **Se elige por voz, no por toma.** Jaime: *«en lugar de buscar tomas
        buenas, si hay un audio con calidad o con expresividad, con emoción,
        pero sin toma, entonces creamos una animación con ese audio»*. El plano
        se puede sustituir por una tarjeta; la voz no se puede sustituir por
        nada.

        Se aplica el filtro de plausibilidad de siempre: el habla expresiva se
        mueve entre 2 y 5 semitonos de recorrido. Por encima de 8 no es energía,
        es el detector saltando de octava; por debajo de 0,2 no es una voz plana,
        es el detector sin material. **Los dos casos son `None`, no cero** — un
        cero decía «esta toma no transmite» de un tramo que nadie llegó a oír, y
        así entraba en su beat como la peor.
        """
        f0 = self.contorno
        if f0 is None:
            return None
        # Rango intercuartílico, no p90-p10: aguanta mejor los saltos que queden.
        st = 12 * np.log2(np.percentile(f0, 75) / max(1e-6, np.percentile(f0, 25)))
        return None if st > 8 or st < 0.2 else float(st)

    @property
    def cambio_de_tono(self):
        """Cuánto se MUEVE la voz, en semitonos por segundo. `None` si no se midió.

        Jaime, fijando las cuatro condiciones del re-calificado: *«si después de
        las cuatro pasadas baja su puntaje, o es demasiado fragmentado, si no hay
        ritmo y si no hay cambio de tono, entonces escogemos el siguiente»*.

        **Y no es lo mismo que `expresividad`.** Aquella mide el rango —cuánto
        espacio ocupa la voz entre su grave y su agudo—, y una lectura monótona
        que deriva despacio de un extremo al otro puntúa alto sin haber cambiado
        de tono ni una vez. Esto mide el recorrido real: la suma de lo que sube y
        baja, dividida por el tiempo. Leer plano da un número bajo aunque el
        rango sea ancho — **bajo, que aquí sí es un número medido.**
        """
        f0 = self.contorno
        if f0 is None or len(f0) < 8:
            return None
        st = 12 * np.log2(np.maximum(f0[1:], 1e-6) / np.maximum(f0[:-1], 1e-6))
        # Los saltos de octava que sobrevivan no son entonacion: se recortan.
        st = np.clip(st, -3.0, 3.0)
        return float(np.abs(st).sum() / max(self.hasta - self.desde, 1e-6))

    def ritmo(self, palabras, ventana=2.0):
        """Cuánto varía la velocidad del habla dentro del tramo. `None` si no se
        pudo medir; 0 = medido y plano.

        La otra mitad de *«si no hay ritmo»*. Se cuentan palabras por segundo en
        ventanas de dos segundos y se devuelve el coeficiente de variación: una
        entrega con ritmo acelera y frena —remata una idea, deja aire, arranca la
        siguiente—, y una lectura mantiene la misma velocidad de principio a fin.

        Se mide sobre las palabras y no sobre la señal porque es lo que el
        espectador percibe como ritmo: cuándo llegan las palabras, no la energía.
        """
        a, b = self.desde, self.hasta
        ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
        if len(ws) < 6 or b - a < 2 * ventana:
            return None
        tasas = []
        t = a
        while t + ventana <= b:
            n = sum(1 for w in ws if t <= w["start"] < t + ventana)
            tasas.append(n / ventana)
            t += ventana / 2
        tasas = np.array([x for x in tasas if x > 0])
        if len(tasas) < 3 or tasas.mean() <= 0:
            return None
        return float(tasas.std() / tasas.mean())

    def tasa(self, palabras):
        """Palabras por segundo en este tramo, con SUS palabras.

        **Cada lado se mide con la transcripcion de su cinta.** Cuando una union
        cruza de una toma a otra —el caso donde el salto mas se oye— medir los
        dos lados con las palabras de la primera daba 2,0 pal/s donde habia
        0,67: cruzaba el umbral por el lado equivocado y denunciaba costuras que
        no existen.
        """
        if not palabras:
            return 0.0
        n = sum(1 for w in palabras if self.desde <= w["start"] < self.hasta)
        return n / max(self.hasta - self.desde, 1e-6)

    def intensidad(self, palabras=None) -> dict:
        """Cuánta emoción lleva el tramo, **sin signo**.

        Correccion de Jaime, y desarma un sesgo que las otras medidas tenian
        dentro: *«ojo, no hay emociones positivas o negativas: mas emocion es mas
        tristeza tanto como mas rabia tanto como mas alegria»*.

        `expresividad` mide el recorrido de F0, y eso **premia lo animado**. La
        tristeza baja el tono, ralentiza y estrecha el rango: con esa vara puntua
        como plana, que es justo lo contrario de lo que es. La rabia, al reves,
        sube y acelera.

        Lo que las dos tienen en comun no es la direccion: es **estar lejos de la
        neutralidad del hablante** (`dominio.neutralidad`). Grave y lento puntua
        igual que agudo y rapido; lo que puntua bajo es lo tibio, que es lo unico
        que de verdad no transmite.

        Devuelve `{altura, velocidad, intensidad}` en desviaciones relativas, y
        cada clave puede ser `None`: misma regla del modulo — lo que no se pudo
        medir se dice, no se rellena con un cero.
        """
        toma, a, b = self.cinta, self.desde, self.hasta
        base = _cero.de(toma, palabras)
        f0 = self.contorno
        out = {"altura": None, "velocidad": None, "intensidad": None}
        if f0 is not None and len(f0) and base["altura"] > 0:
            # En semitonos respecto a su propia altura media, con signo conservado
            # para poder informar de si va grave o agudo.
            out["altura"] = round(12 * np.log2(float(np.median(f0)) / base["altura"]), 2)
        if palabras and base["velocidad"] > 0 and b > a:
            n = sum(1 for w in palabras if a <= w["start"] < b)
            # **Se divide por lo que se HABLA, no por lo que dura el tramo.**
            #
            # Esto usaba el span entero, y un tramo con silencio dentro salia lento
            # aunque se hablara rapido: la velocidad quedaba diluida por el aire.
            # Medido en reel-06: la etapa 6 tiene 13,7 s mudos de 21,49 —el 64%— y
            # puntuaba 0,12 de intensidad; la 7 tenia 5,0 s de 9,50 y puntuaba 0,36.
            # Recortando solo el silencio, esa misma toma sube a 3,84. O sea que
            # media tarde de «etapas tibias» no eran tomas flojas: eran tomas bien
            # dichas medidas sobre el aire que las rodea. Y la trampa es doble,
            # porque **el render ya quita ese silencio** —`plan-reel` corta todo
            # hueco de mas de 0,16 s— asi que se estaba puntuando un tramo que el
            # espectador nunca va a oir asi.
            #
            # El silencio se mide con el detector de voz, que mide el AUDIO, y no
            # con las marcas de palabra: el alineador pega el silencio a la palabra
            # anterior —en esa cinta «practicas.» dura 14,1 s y «ano» 7,1 con
            # energia cero— asi que por palabras es invisible. Es la leccion de
            # C-101 otra vez: cuando dos medidas del mismo hecho discrepan, gana la
            # que mide el hecho.
            util = _hablado(toma, a, b)
            out["velocidad"] = round((n / util) / base["velocidad"] - 1.0, 2)
        partes = [abs(out["altura"]) / 2.0 if out["altura"] is not None else None,
                  abs(out["velocidad"]) / 0.35 if out["velocidad"] is not None else None]
        partes = [p for p in partes if p is not None]
        if partes:
            # La norma, no la suma: lejos en UNA dimension ya es intensidad, y no
            # hace falta estarlo en las dos. Un susurro lento y grave cuenta.
            out["intensidad"] = round(float(np.sqrt(sum(p * p for p in partes))), 2)
        return out

    # ── y lo que se oye al unirla con otra ───────────────────────────────────
    def salta_a(self, otra: "Voz", palabras=None, palabras_b=None) -> dict:
        """Cuánto salta la voz AL CRUZAR de este tramo al de `otra`.

        Jaime: *«si notas que los cortes de tono, o de ritmo, son muy profundos,
        sabes que se va a notar en video»* — *«por lo que puedes escoger o buscar
        otro fragmento que puntúe mejor»*.

        Es una medida distinta de las de arriba, no una variante: aquéllas miran
        **dentro** de un trozo y dicen si esa toma está viva; ésta mira **entre**
        dos y dice si la unión se va a notar. Dos fragmentos pueden puntuar de
        maravilla por separado y sonar a corte pegado cuando uno acaba grave y
        despacio y el siguiente arranca agudo y disparado.

            tono   diferencia de altura media, en semitonos
            ritmo  diferencia de velocidad del habla, en palabras por segundo

        Cada clave es `None` cuando ese lado no se pudo medir — nunca cero: un
        cero diría «no se nota», que es lo contrario de «no sé si se nota». Por
        debajo de `SALTO_TONO` y `SALTO_RITMO` la unión pasa desapercibida.
        """
        ma, mb = self.altura, otra.altura
        out = {"tono": None, "ritmo": None}
        if ma is not None and mb is not None:
            # **La octava, otra vez.** `contorno` corrige cada tramo contra SU
            # mediana, asi que dos ventanas pueden quedar en octavas distintas
            # y el salto sale de 18 semitonos, que es imposible en una voz.
            out["tono"] = round(abs(12 * np.log2(_f0.a_la_octava(mb, ma) / ma)), 2)
        if palabras:
            pb = palabras_b if palabras_b is not None else palabras
            out["ritmo"] = round(abs(otra.tasa(pb) - self.tasa(palabras)), 2)
        return out

    def __str__(self) -> str:
        c = f" @{self.cinta}" if self.cinta else ""
        return f"voz[{self.desde:.3f}-{self.hasta:.3f}{c}]"
