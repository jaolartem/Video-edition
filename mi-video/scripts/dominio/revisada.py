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

    def __init__(self, que: str, etapa=None, segundo=None, para: bool = True):
        self.que, self.etapa, self.segundo, self.para = que, etapa, segundo, para

    def __repr__(self):
        d = f" e{self.etapa}" if self.etapa is not None else ""
        s = f" s={self.segundo:.1f}" if self.segundo is not None else ""
        return f"{'✗' if self.para else '·'}{d}{s} {self.que}"


class Comprobacion:
    """Una cosa que mirar. No la mide: se la pide a quien ya sabe medirla."""

    nombre = "comprobacion"
    #: Si para la pieza o sólo se anota.
    para = True
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


class ElCC(Comprobacion):
    """El transcript de las cintas que usa la pieza: barrido y sin huecos."""

    nombre = "cc"

    def mirar(self, pieza) -> list:
        import consulta

        fuera = []
        try:
            for beat, cob in (consulta.cc_afinado(pieza.slug) or {}).items():
                if cob < 0.95:
                    fuera.append(Falta(
                        f"el CC de la etapa {beat} está al {cob:.0%}: el barrido"
                        f" caro no lo cubre, así que lo que se lee ahí puede no"
                        f" ser lo que se dijo", etapa=beat))
        except Exception as e:                     # noqa: BLE001
            fuera.append(Falta(f"no se pudo medir el CC: {type(e).__name__}"))
        return fuera


class LasDescripciones(Comprobacion):
    """Que cada escena siga hablando del texto que hoy se oye.

    **No pide redescribir.** Jaime: *«sólo hacemos una descripción y una sola
    composición gráfica; no se devuelve a hacer un reproceso por lo mismo»*. Si
    una descripción quedó hablando de otro texto, eso se anota y lo mira quien
    ve la pieza — no se paga otra vuelta de IA por ello.
    """

    nombre = "descripciones"
    para = False
    decide = "criterio"

    def mirar(self, pieza) -> list:
        import basedatos

        from .montaje import Montaje
        from .texto import dice_lo_mismo

        m = Montaje(pieza.slug)
        dice = {}
        for tr, d in m.tramos():
            b = d.get("beat")
            if b is not None:
                dice[b] = (dice.get(b, "") + " " + (m.texto(tr) or "")).strip()
        cx = basedatos.abrir()
        fuera = []
        for b, antes in cx.execute(
                "select etapa_orden, sobre_texto from escena_desc"
                " where video_slug = ? and sobre_texto is not null",
                (pieza.slug,)):
            if b in dice and not dice_lo_mismo(antes, dice[b]):
                fuera.append(Falta(
                    f"la escena de la etapa {b} se escribió sobre otro texto",
                    etapa=b, para=False))
        return fuera


class LosEmpalmes(Comprobacion):
    """Que ningún corte parta una palabra ni caiga en pleno sonido."""

    nombre = "empalmes"

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
                habla = sum(min(b, tr.hasta) - max(a, tr.desde)
                            for a, b in c.habla()
                            if b > tr.desde and a < tr.hasta)
            except Exception:                      # noqa: BLE001
                continue
            mudo = tr.dura - habla
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

    COMPROBACIONES = (ElCC(), LasDescripciones(), LosEmpalmes(),
                      SuenaLoQueDice(), SinRepetir())

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
                    fuera.append(f)
            except Exception as e:                 # noqa: BLE001
                fuera.append(Falta(f"la comprobación «{c.nombre}» reventó:"
                                   f" {type(e).__name__}: {e}"[:200]))
        return fuera

    def pasa(self) -> bool:
        """Sólo lo medible para la pieza. Lo demás se pregunta y viaja."""
        return not any(f.para for f in self.faltas())
