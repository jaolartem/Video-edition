"""Una ventana: el trozo de cinta que se propone para decir una etapa.

**Por qué es un objeto.** Era un `dict` de trece claves que catorce sitios
mutaban por su cuenta, y las tres averías que salieron de ahí son la misma:

- `a`, `b` y `toma` son un `Tramo` y no lo eran, así que cada sitio volvía a
  escribir «se pisan» a su manera. `encadenar` lo escribía con `i`/`j`,
  `sin_repetir` con `i`/`j` al revés y `manda_la_voz` con una tercera copia —y
  las ventanas que añade `manda_jaime` entraban con `i = j = 0`, o sea pisando
  el primer tramo de la cinta por definición.
- `voz` y `aire` se quedaban mintiendo en cuanto alguien movía un extremo: la
  etapa 6 del reel 3 declaraba 9,3 s de voz sobre una ventana de 4,15 s.
- las marcas de diagnóstico —`recortado`, `podado`, `costura`— se escribían y no
  las leía nadie.

Aquí la ventana es dueña de su tramo y de lo que se mide sobre ella, y lo que
devuelve al cambiar es **otra ventana**, no la misma mutada.
"""
from __future__ import annotations

import dataclasses
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402

from . import pesos  # noqa: E402
from ..palabra import Palabra  # noqa: E402
from ..tramo import Tramo  # noqa: E402


def literal(parrafo: str, texto: str, n: int = 4) -> float:
    """Cuánta secuencia EXACTA del libreto reproduce un texto. El detector de lectura.

    Vivía dentro de `Ventana.lee`, y `fijar` —que aplica tramos declarados sin
    pasar por la selección— no tenía con qué medir: heredaba el `literal` de la
    ventana vieja con `{**d}`, así que un tramo leído y fijado sobrevivía a
    cualquier regla de lectura. Una sola medida para los dos (C-382).
    """
    a, b = beats.palabras(parrafo), beats.palabras(texto)
    if len(a) < n:
        return 0.0
    ga = {tuple(a[i:i + n]) for i in range(len(a) - n + 1)}
    gb = {tuple(b[i:i + n]) for i in range(len(b) - n + 1)}
    return len(ga & gb) / max(1, len(ga))


def reaparece(cola: str, cabeza: str) -> float:
    """¿Reaparece el final de un trozo al principio del siguiente?

    Es la firma del reintento: Jaime se para, y al retomar **vuelve unas
    palabras atrás**. Cortar ahí deja la versión truncada y manda al espectador
    la frase a medias, aunque el silencio sea limpio.
    """
    a, b = beats.norm(cola)[-pesos.COLA:], beats.norm(cabeza)[:pesos.COLA]
    if not a or not b:
        return 0.0
    mejor = 0
    for n in range(1, min(len(a), len(b)) + 1):
        if a[-n:] == b[:n]:
            mejor = n
    return mejor / pesos.COLA


@dataclasses.dataclass
class Ventana:
    """Lo que se oye entre `tramo.desde` y `tramo.hasta` de `tramo.cinta`."""

    tramo: Tramo
    texto: str
    #: Voz medida dentro y silencio interno. Se rehacen con `remedida()`.
    voz: float = 0.0
    aire: float = 0.0
    #: El hueco que hay antes de entrar y después de salir, medido sobre la onda.
    entra: float = pesos.LEJOS
    sale: float = pesos.LEJOS
    #: Cuánto repite del tramo anterior y cuánto reaparece en el siguiente: la
    #: firma del reintento.
    sobra: float = 0.0
    trunca: float = 0.0
    #: etapa -> (cubre, dice). Lo que esta ventana dice de cada etapa.
    det: dict = dataclasses.field(default_factory=dict)
    #: Puesta a mano por Jaime: `aprobado` o `recortar`.
    de_jaime: str = ""
    #: Lo caro, medido sólo sobre finalistas.
    voz_st: float | None = None
    intensidad: float | None = None
    altura_st: float | None = None
    limpieza: float | None = None
    #: Cuánto del libreto reproduce literalmente, y si por eso va a tablero.
    lectura: float | None = None
    a_tablero: bool = False

    # ── atajos al tramo ──────────────────────────────────────────────────────
    @property
    def a(self) -> float:
        return self.tramo.desde

    @property
    def b(self) -> float:
        return self.tramo.hasta

    @property
    def toma(self) -> str:
        return self.tramo.cinta

    @property
    def dura(self) -> float:
        return self.tramo.dura

    def movida(self, desde=None, hasta=None, **campos) -> "Ventana":
        """La misma ventana con otros extremos y/o otro texto. No se muta."""
        t = Tramo(round(desde if desde is not None else self.a, 3),
                  round(hasta if hasta is not None else self.b, 3), self.toma)
        return dataclasses.replace(self, tramo=t, **campos)

    def solapa(self, otra: "Ventana") -> bool:
        """¿Se pisan? Sólo dentro de la misma cinta: son grabaciones separadas.

        La regla es la del `Tramo`, que es de quien es. Antes se escribía con los
        índices de tramo de habla —`i`/`j`— en tres sitios distintos, y las
        ventanas de Jaime, que no tienen índice, entraban con `0` y salían
        pisando el arranque de la cinta.
        """
        return self.tramo.solapa(otra.tramo)

    # ── las palabras que caen dentro ─────────────────────────────────────────
    def dentro(self, palabras) -> list[Palabra]:
        """Las que caben **enteras**, que es la vara del recorte.

        No es `Tramo.palabras_de`, que usa la vara del oído —media palabra
        cuenta— y es la correcta para decidir qué se oye. Aquí se decide qué
        texto queda escrito, y media palabra no es texto que quede.
        """
        return [w for w in palabras
                if self.a - pesos.HOLGURA <= w.empieza
                and w.acaba <= self.b + pesos.HOLGURA]

    # ── lo que se mide sobre ella ────────────────────────────────────────────
    def cuelga(self) -> float:
        """Cuánto rompe por sus extremos: 0 limpia, 1 rota por los dos.

        Detrás de «por», «que» o «de» la frase no ha acabado — es la regla de
        los subtítulos compuestos (C-23) aplicada al corte. Es lo que dejaba
        «...preguntado al contador **por**».

        **Y la palabra no basta.** «Tiene dos tra… un electricista en Brampton»
        empieza por un verbo cuyo sujeto se quedó en el tramo anterior, y
        ninguna lista de palabras colgantes atrapa eso. Lo que sí lo atrapa es
        el hueco: si antes de la ventana no hubo una pausa de verdad, la idea
        venía de antes.
        """
        ws = beats.palabras(self.texto)
        if not ws:
            return 1.0
        abre = (ws[0] in pesos.COLGANTE) or (self.entra < pesos.PAUSA_IDEA)
        cierra = (ws[-1] in pesos.COLGANTE) or (self.sale < pesos.PAUSA_IDEA)
        return 0.5 * float(abre) + 0.5 * float(cierra)

    def invade(self, siguiente: str) -> float:
        """¿Se está comiendo el arranque de la etapa siguiente?

        No es repetición —la poda de dentro no lo ve—: es una ventana que sigue
        hablando después de cumplir lo suyo. En el reel 5 la etapa 3 acababa
        diciendo el arranque literal de la etapa 4, y por eso la 4 se quedaba
        sin material: sus cinco candidatas vivían dentro de esa ventana.

        Se mide sobre el ÚLTIMO TERCIO, que es donde ocurre.
        """
        if not siguiente:
            return 0.0
        ws = beats.palabras(self.texto)
        if len(ws) < 9:
            return 0.0
        pedidas = set(beats.norm(siguiente))
        if not pedidas:
            return 0.0
        cola = " ".join(ws[-len(ws) // 3:])
        return len(pedidas & set(beats.norm(cola))) / len(pedidas)

    def lee(self, parrafo: str, n: int = 4) -> float:
        """Cuánta secuencia EXACTA del libreto reproduce. El detector de lectura.

        Regla de Jaime: *«no es aceptado leer; para leer prefiero el tablero»*, y
        la clave que lo hace medible: *«la lectura es exacta»*.

        **Y esto invierte lo que la puntuación premiaba.** La cobertura mide
        cuántas palabras del libreto aparecen, así que cuanto más literal es una
        toma más puntúa — o sea que el selector estaba **eligiendo las tomas
        leídas por construcción**.

        Se miden secuencias de cuatro palabras y no palabras sueltas: decir las
        mismas palabras en otro orden es hablar; decirlas en el mismo orden es
        leer. El umbral (`pesos.LEIDA`) sale de un salto de 0,17 en la
        distribución de los 53 fragmentos elegidos.
        """
        return literal(parrafo, self.texto, n)

    def puntua(self, parrafo: str, exige=(), siguiente: str = "") -> tuple:
        """Lo que vale para esta etapa: `(puntuación, cubre, dice)`.

        **La redundancia NO decide cuál se elige.** Regla de Jaime: *«a la mejor
        toma, y sólo a la mejor, le hacemos la revisión estricta de
        redundancia»*, y la elección es *«por entrega emocional»*. Penalizarla
        aquí la metía en las 5.319 candidatas y hacía que un tropiezo descartara
        la toma con mejor voz — que es justo al revés. La poda va después, sobre
        la ganadora.
        """
        cubre = float(beats.puntua(
            parrafo, {"texto": self.texto, "clave": set(beats.norm(self.texto))}))
        dice = bool(exige) and all(beats.dice(self.texto, t) for t in exige)
        # Cortar dentro de una frase se paga. Jaime lo dijo por su nombre: *«hay
        # silencios entre la misma frase; no significa que sea otra toma, sólo
        # me quedé callado pensando»*. Un extremo en una pausa de pensar no es
        # un extremo, es un corte a mitad de idea.
        costura = ((max(0.0, pesos.COSTURA - self.entra)
                    + max(0.0, pesos.COSTURA - self.sale)) / (2 * pesos.COSTURA))
        p = (pesos.PESO_CUBRE * cubre
             + pesos.PESO_DICE * float(dice)
             - pesos.PESO_AIRE * self.aire
             - pesos.PESO_COSTURA * costura
             - pesos.PESO_SOLAPE * (self.sobra + self.trunca) / 2
             - pesos.PESO_CUELGA * self.cuelga()
             - pesos.PESO_INVADE * self.invade(siguiente))
        return round(p, 4), round(cubre, 4), int(dice)

    def compite(self, cubre: float, dice: int) -> bool:
        """¿Llega a candidata? **El umbral va sobre el mensaje, no sobre la nota.**

        Con el castigo dentro, una ventana que dice justo lo que la etapa
        necesita se caía por tener un extremo sucio — y el extremo sucio se
        recorta. Así la etapa se quedaba sin toma teniendo material.
        """
        return cubre >= pesos.UMBRAL or (bool(dice) and cubre >= pesos.SUELO_DICE)

    # ── lo que hay que rehacer cuando se mueve un extremo ────────────────────
    def remedida(self, habla) -> "Ventana":
        """Vuelve a medir voz y aire. **Un recorte deja los dos mintiendo.**

        Aguas abajo eso es una duración de escena equivocada, que es el
        aprendizaje 43 —el render pidiendo un frame que no existe— por otro
        camino.
        """
        voz = sum(max(0.0, min(self.b, y) - max(self.a, x)) for x, y in habla)
        return dataclasses.replace(
            self, voz=round(voz, 2), aire=round(max(0.0, self.dura - voz), 2))

    def __str__(self) -> str:
        return f"{self.tramo} «{self.texto[:60]}»"
