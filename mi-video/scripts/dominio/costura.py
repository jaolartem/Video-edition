"""Una costura: dos trozos que se tocan, y lo que salta la voz al cruzarlos.

**Por qué no existía y tenía que existir.** La costura es el sustantivo más
usado del cosido —el propio paso se llama así— y era lo único que no era nada:
veintitrés funciones pasándose `(edl, i, cache)` y devolviendo tuplas
`(b0, a1, salto)`. El índice `i` era la costura, y un índice no sabe nada de sí
mismo, así que cada función volvía a deducir lo mismo desde cero: de qué cinta
sale cada lado, si entre los dos se quitaron palabras, si el tramo venía
declarado.

De ahí salían dos averías que aquí son imposibles:

- **Medir y decidir estaban en la misma función.** `arreglar` preguntaba si la
  costura se oía, si estaba fijada y cuál era el mejor empalme, todo mezclado
  con escribir el fichero — así que no se podía preguntar por una costura sin
  arriesgarse a moverla.
- **«Aquí se quitaron palabras» se medía con la vara equivocada.** Se exigía la
  palabra entera dentro del hueco (`b0 <= start and end <= a1`), y una palabra
  que el corte parte por la mitad —el caso normal, porque el corte se pega a lo
  callado y no a la frontera del texto— no contaba: la costura no llegaba a
  medirse nunca. La vara del proyecto es `Palabra.suena_en` (C-84), y es la que
  se usa aquí.

Regla de Jaime, y trae las dos mitades: *«busca los mejores cortes posibles, y
si no, utiliza la transición del glitch, con ésa se disimula»*. Esta clase
contesta la primera mitad; la segunda la decide quien monta.
"""
from __future__ import annotations

from .tramo import Tramo

#: Por debajo de esto la costura no se oye. Medido sobre el lote, y son los
#: umbrales de percepción, no de manual.
#:
#: **Viven aquí porque son de la costura.** `suena.costuras` juzga lo mismo con
#: `beats.SALTO_TONO` (2,0) y `beats.SALTO_RITMO` (1,5), así que hoy el informe
#: denuncia uniones que el paso que las arregla considera limpias. Dos varas
#: para «se oye» son dos verdades; la de la costura es ésta.
TONO_OK = 2.5
RITMO_OK = 3.0
#: Cuánto se puede mover un extremo buscando un empalme mejor. Medio segundo es
#: una palabra corta: más allá se empieza a cambiar lo que se dice.
MARGEN = 0.6
#: Cuánta expresividad puede perder una alternativa antes de descartarla.
PIERDE_VOZ = 0.15


class Costura:
    """La unión entre el tramo `antes` y el tramo `despues`.

    `fijada` dice que uno de los dos lados viene declarado por una decisión
    anterior: entonces la costura **no se mueve** aunque se oiga, porque moverla
    recorta una palabra a cada lado y eso deshace la decisión en silencio.
    Medido en reel-01 e2: la segunda valoración declaró 118,20-134,35 y
    220,35-224,85 justo para que entraran «estructura» al cerrar y «y los» al
    abrir; el optimizador los quitó buscando una costura más limpia y la pieza
    quedó diciendo «una cierta | que usan esa estructura». Para eso está el
    glitch: disimular no cuesta palabras.
    """

    __slots__ = ("antes", "despues", "fijada", "_habla", "_salto")

    def __init__(self, antes: Tramo, despues: Tramo, habla, fijada=False):
        self.antes = antes
        self.despues = despues
        self.fijada = bool(fijada)
        #: `habla(cinta) -> Habla`. Se recibe, no se carga: el dueño de las
        #: palabras es el montaje, y una segunda puerta a las palabras de una
        #: cinta es una segunda respuesta a qué se dice en ella.
        self._habla = habla
        self._salto = None

    # ── qué clase de unión es ───────────────────────────────────────────────
    @property
    def cambia_de_cinta(self) -> bool:
        """El plano cambia entero: no hay costura que disimular."""
        return self.antes.cinta != self.despues.cinta

    @property
    def hueco(self) -> Tramo | None:
        """Lo que se quitó entre los dos trozos, o `None` si se tocan."""
        if self.cambia_de_cinta or self.despues.desde <= self.antes.hasta:
            return None
        return Tramo(self.antes.hasta, self.despues.desde, self.antes.cinta)

    @property
    def es_empalme(self) -> bool:
        """¿Se quitaron palabras aquí?

        **Sólo cuenta donde se quitaron.** Si entre un trozo y el siguiente sólo
        se fue silencio, la voz continúa: el cambio de tono es prosodia, no
        empalme, y taparlo con un glitch sería poner el efecto donde no hay nada
        que tapar.
        """
        h = self.hueco
        return bool(h and h.palabras_de(self._palabras(h.cinta)))

    # ── cuánto salta la voz ─────────────────────────────────────────────────
    @property
    def salto(self) -> dict:
        """`{"tono": semitonos, "ritmo": palabras/s}` al cruzar la unión.

        **Cada lado con las palabras de su cinta.** `beats.salto` lo documenta:
        medir los dos lados con la transcripción de la primera daba 2,0 pal/s
        donde había 0,67 y denunciaba costuras que no existen. Aquí se le pasan
        las dos, aunque hoy sólo se midan uniones de la misma cinta — el día que
        se mida una de dos cintas no habrá que acordarse.
        """
        if self._salto is None:
            import beats

            self._salto = beats.salto(
                self.antes.cinta, self.antes.hasta,
                self.despues.cinta, self.despues.desde,
                self._crudas(self.antes.cinta),
                palabras_b=self._crudas(self.despues.cinta))
        return self._salto

    @property
    def tono(self) -> float:
        return float(self.salto.get("tono") or 0.0)

    @property
    def ritmo(self) -> float:
        return float(self.salto.get("ritmo") or 0.0)

    @property
    def audible(self) -> bool:
        """¿Se va a oír esta unión? La pregunta entera, en un sitio."""
        return self.tono > TONO_OK or self.ritmo > RITMO_OK

    @property
    def coste(self) -> float:
        """Lo audible en una sola cifra, para poder ordenar alternativas."""
        return self.tono / TONO_OK + self.ritmo / RITMO_OK

    # ── qué se puede hacer con ella ─────────────────────────────────────────
    def mejor(self) -> "Costura | None":
        """La misma costura movida a las fronteras de palabra que mejor empalman.

        Se prueban los finales de palabra dentro de `MARGEN` antes del corte y
        los comienzos dentro de `MARGEN` después. **No se inventa un corte a
        mitad de palabra**: sólo se eligen fronteras que ya existen.

        **Y mover el corte no puede costar voz.** Jaime, sobre el objetivo de
        todo esto: *«el punto es transmitir mas emocion»*. Un optimizador que
        sólo minimiza el salto acaba eligiendo el trozo más plano, porque lo
        plano empalma con todo — lo contrario de lo que la pieza necesita. Así
        que la entrega es una **restricción**, no un término más: una
        alternativa que baje la expresividad se descarta aunque empalme
        perfecto, y entonces la costura se disimula.

        Devuelve `None` cuando no hay nada que probar: costura declarada, cambio
        de cinta, o ninguna alternativa que respete la entrega.
        """
        if self.fijada or self.cambia_de_cinta:
            return None
        ws = self._palabras(self.antes.cinta)
        a0, b0 = self.antes.desde, self.antes.hasta
        a1, b1 = self.despues.desde, self.despues.hasta
        finales = {round(b0, 3)} | {round(p.acaba, 3) for p in ws
                                    if b0 - MARGEN <= p.acaba <= b0
                                    and p.acaba - a0 > 0.8}
        inicios = {round(a1, 3)} | {round(p.empieza, 3) for p in ws
                                    if a1 <= p.empieza <= a1 + MARGEN
                                    and b1 - p.empieza > 0.8}
        # **Y si no se pudo medir no hay suelo que defender.**
        #
        # `_voz` devuelve `None` cuando ningun lado se pudo medir —su ventana es
        # corta, que es el caso de 4 de 103 trozos—, y esta linea le restaba
        # `PIERDE_VOZ`: **TypeError**, la costura entera al suelo. Y la de abajo
        # comparaba `None <` con lo mismo. Con `None` la voz no opina: la
        # costura se elige por coste, que es lo que se hacia antes de que la voz
        # existiera, en vez de rechazar candidatas por una medida que no hay.
        base = self._voz(a0, b0, a1, b1)
        suelo = None if base is None else base - PIERDE_VOZ
        elegida = None
        for f in sorted(finales):
            for n in sorted(inicios):
                if n <= f:
                    continue
                if suelo is not None:
                    v = self._voz(a0, f, n, b1)
                    if v is not None and v < suelo:
                        continue
                cand = self._como(Tramo(a0, f, self.antes.cinta),
                                  Tramo(n, b1, self.despues.cinta))
                if elegida is None or cand.coste < elegida.coste:
                    elegida = cand
        return elegida

    # ── lo de dentro ────────────────────────────────────────────────────────
    def _como(self, antes: Tramo, despues: Tramo) -> "Costura":
        return Costura(antes, despues, self._habla, fijada=self.fijada)

    def _palabras(self, cinta) -> list:
        return self._habla(cinta).palabras

    def _crudas(self, cinta) -> list:
        return self._habla(cinta).dicts()

    def _voz(self, a0, b0, a1, b1) -> float:
        """La expresividad media de los dos trozos, que es lo que no se pierde."""
        import beats

        # **Lo no medido no cuenta; no suma cero.** Un lado sin medir con un
        # cero delante baja la media a la mitad y el resultado parece medido.
        # La regla vive en `voz.media`, que es de la medida y no de la costura:
        # aqui estaba escrita y los otros cuatro sitios que hacen lo mismo
        # ponian el cero.
        from .voz import media

        return media(beats.expresividad(self.antes.cinta, a0, b0),
                     beats.expresividad(self.despues.cinta, a1, b1))

    def __str__(self) -> str:
        return (f"costura {self.antes}|{self.despues}"
                f" tono {self.tono} · ritmo {self.ritmo}")
