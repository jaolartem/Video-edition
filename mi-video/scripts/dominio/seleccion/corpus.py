"""Las ventanas de TODAS las grabaciones, y las palabras de cada una.

Corrección de Jaime, y reordena el modelo entero: *«típicamente se asume que un
video un libreto, pero no siempre es así. A veces se regraban los videos, otras
veces se graba la última parte de un video anterior… ¿Cuál es nuestra unidad
básica? No es el guion, no es el video y no es el frame. Es la sección de frame,
y eso sale de la unión de la teórica (libreto) con la práctica (grabación)»*.

La consecuencia es directa: una etapa puede cumplirse con material de
**cualquier** cinta.

**Por qué es un objeto y no tres diccionarios paralelos.** `corpus()` devolvía
`(ventanas, datos)` y quien llamaba desarmaba `datos` en `palabras_de` y
`runs_de` — dos diccionarios más que viajan juntos y se pasan a mano a cinco
funciones. Cuando una de ellas recibía la cinta equivocada nadie se enteraba:
`limpieza()` medía los tropiezos de una grabación sobre las palabras de otra.
Aquí se pregunta al corpus por la cinta de la ventana, y no hay forma de
equivocarse.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402
import registro  # noqa: E402

from . import pesos  # noqa: E402
from ..cinta import Cinta, CintaIncompleta  # noqa: E402
from ..tramo import Tramo  # noqa: E402
from .ventana import Ventana, reaparece  # noqa: E402


def ventanas(habla, palabras, toma: str = "") -> list[Ventana]:
    """Todo trozo que empieza en el arranque de un tramo y acaba en el fin de otro.

    **Un tramo sin palabras no es voz.** El detector de habla marca tramos por
    nivel de señal —respiración, ruido, un arranque que no llegó a palabra— y el
    transcript no saca nada de ellos. Contarlos como voz hacía que una ventana
    pareciera llena estando vacía: el reel 1 abría con **22,6 segundos sin una
    sola palabra** entre 64,99 y 87,60, y eso salía al montaje como el gancho.

    Es el aprendizaje 3 un nivel más adentro: allí se intersecaba el EDL con los
    tramos de habla; aquí hace falta intersecar con los tramos que
    **produjeron texto**, que es lo único que el espectador va a oír decir.
    """
    # Las palabras de cada tramo, una sola vez: sin esto son cuatro mil barridos.
    por_tramo: list[list] = [[] for _ in habla]
    k = 0
    for w in sorted(palabras, key=lambda w: w.empieza):
        c = (w.empieza + w.acaba) / 2
        while k + 1 < len(habla) and c >= habla[k][1]:
            k += 1
        if habla[k][0] - pesos.ROCE <= c < habla[k][1] + pesos.ROCE:
            por_tramo[k].append(w)

    # El hueco antes de cada tramo y después de cada tramo, medido sobre la onda.
    antes = [habla[0][0]] + [habla[k][0] - habla[k - 1][1]
                             for k in range(1, len(habla))]
    despues = ([habla[k + 1][0] - habla[k][1] for k in range(len(habla) - 1)]
               + [pesos.LEJOS])
    con_voz = [bool(p) for p in por_tramo]
    dicho = [" ".join(w.texto for w in p) for p in por_tramo]

    out: list[Ventana] = []
    for i in range(len(habla)):
        if not con_voz[i]:
            continue          # una ventana no puede ABRIR en un tramo mudo
        voz, ws = 0.0, []
        for j in range(i, len(habla)):
            ws += por_tramo[j]
            if not con_voz[j]:
                continue      # ni CERRAR en uno
            voz += habla[j][1] - habla[j][0]
            if voz < pesos.MIN_VOZ:
                continue
            if voz > pesos.MAX_VOZ:
                break
            texto = " ".join(w.texto for w in ws).strip()
            if len(beats.norm(texto)) < pesos.CONTENIDO_MIN:
                continue
            a, b = habla[i][0], habla[j][1]
            out.append(Ventana(
                tramo=Tramo(round(a, 3), round(b, 3), toma), texto=texto,
                voz=round(voz, 2), aire=round((b - a) - voz, 2),
                entra=round(min(antes[i], pesos.LEJOS), 2),
                sale=round(min(despues[j], pesos.LEJOS), 2),
                # Sobra por delante si el arranque repite la cola del tramo
                # anterior; queda truncada por detrás si su cola reaparece en el
                # siguiente.
                sobra=round(reaparece(dicho[i - 1] if i else "", texto), 2),
                trunca=round(reaparece(
                    texto, dicho[j + 1] if j + 1 < len(habla) else ""), 2)))
    return out


class Corpus:
    """Todo el material del que se puede sacar una etapa, cinta por cinta."""

    def __init__(self, tomas):
        self.ventanas: list[Ventana] = []
        self._palabras: dict[str, list] = {}
        self._dichos: dict[str, list] = {}
        self._habla: dict[str, list] = {}
        for t in tomas:
            self._sumar(t)

    def _sumar(self, toma: str) -> None:
        """Una cinta que no se puede sostener no entra, **y no para la corrida**.

        Se cazaban sólo los `SystemExit`, así que una cinta con habla sin texto
        —que lanza `CintaIncompleta`, no `SystemExit`— tumbaba la selección
        entera del reel por un defecto de OTRA grabación. La búsqueda amplia de
        C-74 convirtió eso en una avería garantizada: basta con que una de las
        ocho cintas del material esté a medio transcribir.
        """
        c = Cinta(toma)
        try:
            c.exigir()
        except (SystemExit, CintaIncompleta) as e:
            registro.aviso("seleccionar", "cinta fuera del corpus", toma=toma,
                           detalle=str(e)[:120], eco=False)
            return
        habla = c.habla()
        if not habla:
            registro.aviso("seleccionar", "cinta sin tramos de habla medidos",
                           toma=toma, detalle=c.cortes, eco=False)
            return
        self._palabras[toma] = c.palabras()
        self._habla[toma] = habla
        self.ventanas += ventanas(habla, self._palabras[toma], toma)

    # ── lo que se le pregunta ────────────────────────────────────────────────
    @property
    def tomas(self) -> list[str]:
        return list(self._palabras)

    def palabras(self, toma: str) -> list:
        """Las `Palabra` de esa cinta, pegadas al habla y con sitio."""
        return self._palabras.get(toma, [])

    def dichos(self, toma: str) -> list[dict]:
        """Las mismas, en el formato que esperan `depurar` y `beats`."""
        if toma not in self._dichos:
            self._dichos[toma] = [w.a_dict() for w in self.palabras(toma)]
        return self._dichos[toma]

    def habla(self, toma: str) -> list:
        return self._habla.get(toma, [])

    # ── el peldaño caro del embudo ───────────────────────────────────────────
    def a_afinar(self, marcas, toma: str, cuantos: int = 4) -> list[tuple]:
        """Los tramos que merecen el modelo bueno: la lista corta de TODAS las etapas.

        Corrección de Jaime, y es la que salva el peldaño: *«si esto es así hay
        que revalidar a los candidatos ganadores con el buen sistema, porque
        puede no coincidir para ese segmento pero ser los mejores para otro»*.

        O sea: afinar y confirmar en el sitio **no vale**. El barrido barato
        acierta el sitio en 7 de 9 etapas del reel 6, y las dos que falla las
        pone en otra etapa — así que confirmar cada ganador donde el barato lo
        dejó hereda exactamente su error. Se afina la lista corta de todas las
        etapas juntas y se reparte de cero sobre el material afinado.
        """
        quiero = []
        for fila in marcas:
            top = sorted((k for k in range(len(fila)) if fila[k] is not None),
                         key=lambda k: -fila[k])[:cuantos]
            quiero += [(round(self.ventanas[k].a, 2), round(self.ventanas[k].b, 2))
                       for k in top if self.ventanas[k].toma == toma]
        # Se funden los solapados: afinar dos veces el mismo trozo es pagar dos veces.
        fundidos: list[list] = []
        for a, b in sorted(quiero):
            if fundidos and a <= fundidos[-1][1] + 0.5:
                fundidos[-1][1] = max(fundidos[-1][1], b)
            else:
                fundidos.append([a, b])
        return [tuple(x) for x in fundidos]
