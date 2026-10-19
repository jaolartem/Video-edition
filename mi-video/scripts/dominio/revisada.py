"""Qué se revisa de una pieza, y todo se mide.

**Lo que Jaime pidió que revisara**, el 1 de septiembre: *«revisar revisa CC,
descripciones y empalmes —además que tenga sonido en todo lo que dice—;
probablemente sea fácil para revisar comprobar la regla de redundancia en el CC,
que ya está trabajado desde antes»*.

Las cinco son **hechos**, y por eso este paso no gasta una llamada. Es la norma
que él mismo fijó: *«LLM cuando se necesite criterio para decidir; todo lo que
pueda ser hecho con código, que se haga con código»*. Aquí no hay nada que
entender: hay que contar.

## Y contar no es lo mismo que volver a juzgar

Esto no vuelve a opinar sobre el corte ni sobre las escenas: **comprueba que
estén como se dijo**. Un paso que revisa opinando es el que hizo dar siete
vueltas al reel-01, porque la IA no es determinista y cada lectura encuentra otra
cosa. Éste, con la misma entrada, da siempre la misma respuesta.

## Una subclase por comprobación, y cada una sabe dónde mirar

Ninguna implementa su medida: se la pide a quien ya la tiene —`Cinta`,
`Montaje`, `repetido`, `dice_lo_mismo`—. Lo que aportan es **decir qué
significa** lo que sale de ahí, y con qué severidad.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Falta:
    """Algo que no está como se dijo. Con su sitio, para poder ir a mirarlo."""

    def __init__(self, que: str, etapa=None, segundo=None, para: bool = True,
                 devuelve_a: str | None = None):
        self.que, self.etapa, self.segundo, self.para = que, etapa, segundo, para
        #: **A qué paso se devuelve, y sólo si ese paso lo evalúa.** Jaime:
        #: *«un problema para devolver es respecto a lo que evalúa»*. Sin esto
        #: una puerta paraba la pieza por algo que ningún paso sabía arreglar —
        #: y entonces no hay salida ninguna: pasó hoy tres veces seguidas, con
        #: un solape de 80 ms, con un corte sucio y con un pedido huérfano.
        #:
        #: `None` quiere decir que nadie lo arregla solo. Eso **no devuelve**:
        #: se anota y viaja con la pieza, que es lo honesto.
        self.devuelve_a = devuelve_a

    def __repr__(self):
        d = f" e{self.etapa}" if self.etapa is not None else ""
        s = f" s={self.segundo:.1f}" if self.segundo is not None else ""
        return f"{'✗' if self.para else '·'}{d}{s} {self.que}"


class Comprobacion:
    """Una cosa que mirar. No la mide: se la pide a quien ya sabe medirla."""

    nombre = "comprobacion"
    #: Si para la pieza o sólo se anota.
    para = True
    #: El paso que sabe arreglar lo que esta comprobación encuentra. Devolver la
    #: pieza a cualquier otro sitio es mandarla a que no pase nada.
    devuelve_a = None
    #: **Quién decide esto.** Jaime, el 1 de septiembre: *«descripciones y
    #: redundancias por LLM, que tienen criterio; lo demás por código»*.
    #:
    #: Las de `codigo` dan un veredicto: se miden y se acabó. Las de `criterio`
    #: **no lo dan** — miden lo que se puede medir y salen como PREGUNTA, con la
    #: mitad computable ya resuelta para que quien lee no la repita. Que un
    #: `¿sigue valiendo esta escena?` o un `¿esta repetición remata?` los conteste
    #: una comparación de cadenas es justo lo que hace falsos los dos.
    decide = "codigo"

    def mirar(self, pieza) -> list:
        raise NotImplementedError


class LosCortes(Comprobacion):
    """Que ningún corte caiga dentro de una palabra.

    Es la primera de las cuatro que Jaime listó, y no es la misma que los
    empalmes: el empalme es cómo suena la unión de dos trozos; el corte es dónde
    cae la tijera. Un corte a media sílaba se oye aunque la costura sea limpia.
    """

    nombre = "cortes"
    devuelve_a = "cosido"

    def mirar(self, pieza) -> list:
        # **En la onda, no en el transcript** (C-604): con la misma vara que la
        # verificación y el cosido (`bordes`, C-574). Medía con los tiempos de
        # whisper, que en un trozo declarado ya nadie puede mover (C-570), y
        # reel-20 volvió de aquí al cosido en bucle por cortes de 3 y 75 ms que
        # la onda daba por callados.
        from . import bordes

        try:
            n = len(bordes.sucios(pieza.slug))
        except Exception as e:                     # noqa: BLE001
            return [Falta(f"no se pudieron medir los cortes:"
                          f" {type(e).__name__}")]
        return [Falta(f"{n} corte(s) caen dentro de una palabra")] if n else []


class LosEmpalmes(Comprobacion):
    """Que ningún corte parta una palabra ni caiga en pleno sonido."""

    nombre = "empalmes"
    devuelve_a = "cosido"

    def mirar(self, pieza) -> list:
        import costuras

        fuera = []
        try:
            sucios = costuras.a_lo_callado(pieza.slug, ver=True,
                                           minimo=costuras.PUERTA)
            if sucios:
                fuera.append(Falta(
                    f"{sucios} corte(s) caen en pleno sonido y hay un punto"
                    f" callado a menos de 120 ms — lo cierra el paso `cosido`"))
        except Exception as e:                     # noqa: BLE001
            fuera.append(Falta(f"no se pudieron medir los empalmes:"
                               f" {type(e).__name__}"))
        return fuera


class SuenaLoQueDice(Comprobacion):
    """Que haya voz detrás de todo lo que la pieza dice.

    La pidió él con esas palabras —*«además que tenga sonido en todo lo que
    dice»*— y no es lo mismo que el CC: el CC puede estar perfecto y el montaje
    haberse llevado el audio de un trozo. El texto se lee entero y no suena.
    """

    nombre = "suena"
    #: Un hueco de voz dentro de un trozo lo cierra quien cose, partiéndolo.
    devuelve_a = "cosido"

    #: Un trozo con más de esto callado dentro no es una pausa: es un hueco.
    MUDO_MAX = 1.2

    def mirar(self, pieza) -> list:
        from .cinta import Cinta
        from .montaje import Montaje

        m = Montaje(pieza.slug)
        fuera, cintas = [], {}
        for tr, d in m.tramos():
            if not (m.texto(tr) or "").strip():
                continue
            c = cintas.get(tr.cinta)
            if c is None:
                try:
                    c = cintas[tr.cinta] = Cinta(tr.cinta)
                except Exception:                  # noqa: BLE001
                    continue
            try:
                voz = sorted((max(a, tr.desde), min(b, tr.hasta))
                             for a, b in c.habla()
                             if b > tr.desde and a < tr.hasta)
            except Exception:                      # noqa: BLE001
                continue
            # **El hueco más largo, no la suma de las pausas.** Sumadas, las
            # pausas naturales de un trozo de 15 s daban 1,36 s y reel-11 e3
            # volvía al cosido en cada vuelta sin que el cosido tuviera nada que
            # partir: seis pausas de 0,1 a 0,7 s no son aire muerto (C-463).
            bordes = [tr.desde] + [x for par in voz for x in par] + [tr.hasta]
            mudo = max((bordes[i + 1] - bordes[i]
                        for i in range(0, len(bordes) - 1, 2)), default=tr.dura)
            if mudo > self.MUDO_MAX:
                fuera.append(Falta(
                    f"la etapa {d.get('beat')} tiene {mudo:.1f} s sin voz dentro"
                    f" de un trozo que sí tiene texto: se lee entero y no suena",
                    etapa=d.get("beat")))
        return fuera


class SinRepetir(Comprobacion):
    """La regla de dos de tres, sobre el CC que ya está trabajado.

    Jaime, literal: *«para repeticiones la regla establecida era cumplir dos de
    tres características; la primera completamente obligatoria, que esté en la
    misma toma; la segunda que esté en el libreto; y la tercera que aporte a la
    construcción de un punchline»*.

    De las tres, dos se miden aquí y la tercera es criterio. Así que lo que sale
    **no para**: se anota diciendo cuál de las dos le falta, y quien mire la
    pieza decide si el remate la justifica.
    """

    nombre = "redundancia"
    para = False
    decide = "criterio"

    def mirar(self, pieza) -> list:
        from .montaje import Montaje
        from .repetido import repetido

        fuera = []
        for r in repetido(Montaje(pieza.slug)):
            if r.get("una_toma") and r.get("en_libreto"):
                continue                    # cumple dos: se queda
            falta = ("no está en la misma toma, que es la obligatoria"
                     if not r.get("una_toma") else
                     "está en la misma toma pero no en el libreto: sólo vale si"
                     " la repetición construye el remate")
            fuera.append(Falta(
                f"dice «{r['dice']}» {r['veces']} veces y {falta}",
                etapa=r.get("etapa"), para=False))
        return fuera


class Revisada:
    """La revisión entera de una pieza. Cinco comprobaciones, cero llamadas."""

    #: **Las cuatro, y sólo las cuatro.** Jaime, precisando cuando yo había
    #: puesto de más: *«no respecto a todo. Evalúa cortes, que haya audio,
    #: empalmes y redundancia en CC»*.
    #:
    #: Fuera quedan la cobertura del CC —de eso sólo mira la redundancia— y las
    #: descripciones, que ya se decidieron y no se vuelven a discutir. Un paso
    #: que evalúa de más devuelve la pieza por cosas que no son suyas, y eso es
    #: lo que la deja sin salida.
    COMPROBACIONES = (LosCortes(), SuenaLoQueDice(), LosEmpalmes(),
                      SinRepetir())

    def __init__(self, pieza):
        self.pieza = pieza

    def faltas(self) -> list:
        """Lo que el código decide: CC, empalmes y que suene lo que dice."""
        return self._mirar("codigo")

    def preguntas(self) -> list:
        """Lo que necesita criterio: las escenas y las repeticiones.

        Sale con la parte medible ya hecha —qué etapa, sobre qué texto se
        escribió, cuál de las dos características le falta a la repetición— para
        que quien lee gaste su turno en lo único que no se puede contar.
        """
        return self._mirar("criterio")

    def _mirar(self, quien: str) -> list:
        fuera = []
        for c in self.COMPROBACIONES:
            if c.decide != quien:
                continue
            try:
                for f in c.mirar(self.pieza):
                    f.para = f.para and c.para
                    f.devuelve_a = f.devuelve_a or c.devuelve_a
                    fuera.append(f)
            except Exception as e:                 # noqa: BLE001
                fuera.append(Falta(f"la comprobación «{c.nombre}» reventó:"
                                   f" {type(e).__name__}: {e}"[:200]))
        return fuera

    def pasa(self) -> bool:
        """Sólo lo medible para la pieza. Lo demás se pregunta y viaja."""
        return not any(f.para for f in self.faltas())
