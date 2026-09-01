"""Una palabra dicha: cuándo empieza, cuándo acaba y qué se oye.

**Por qué es un objeto y no un `dict`.** Era un `dict` con `start`, `end` y
`text`, y cada sitio que lo recibía volvía a decidir qué significaba. De ahí
salieron tres fallos en un solo día:

- una palabra estirada sobre 5 s de silencio hacía que un beat pareciera hablado
  entero (C-147);
- una palabra de ancho cero se la llevaba por delante un corte que empezaba en
  su mismo instante, sin que nadie lo contara — así desapareció «por esta
  semana» de una pieza de precio;
- seis palabras de ancho cero apiladas en el mismo instante salían dos veces en
  el subtítulo, porque nada las ordenaba.

Los tres son la misma avería: **el dato no sabía nada de sí mismo.** Aquí sí.
"""
from __future__ import annotations

import dataclasses

from . import texto as _tx

#: Lo que dura una palabra que el modelo estampó sin duración. No se inventa:
#: es el suelo por debajo del cual dos palabras no se pueden ordenar en el
#: tiempo, y sin orden el subtítulo las repite.
MINIMA = 0.04


@dataclasses.dataclass(frozen=True, slots=True)
class Palabra:
    """Lo que se oye entre `empieza` y `acaba`, en tiempo de cinta."""

    texto: str
    empieza: float
    acaba: float

    # ── cómo nace ────────────────────────────────────────────────────────────
    @classmethod
    def de_dict(cls, d: dict) -> "Palabra":
        """Del formato que guarda el transcript. La única puerta de entrada."""
        return cls(str(d.get("text", "")),
                   float(d.get("start", 0.0)),
                   float(d.get("end", 0.0)))

    def a_dict(self) -> dict:
        """De vuelta al formato del fichero, mientras queden consumidores."""
        return {"text": self.texto, "start": self.empieza, "end": self.acaba}

    # ── lo que sabe de sí misma ──────────────────────────────────────────────
    @property
    def dura(self) -> float:
        return self.acaba - self.empieza

    @property
    def sin_duracion(self) -> bool:
        """El modelo la estampó con principio y final iguales.

        **Existe y se oye.** Whisper devuelve marcas iguales cuando dos palabras
        caen en el mismo frame: hay 236 en las ocho cintas de este proyecto. Que
        no dure no significa que no suene — significa que no sabemos cuánto.
        """
        return self.dura <= 0.0

    def suena_en(self, a: float, b: float) -> bool:
        """¿Se oye dentro del corte `[a, b]`?

        **La vara es la del oído, no la del filtro.** Exigir la palabra entera
        dentro se come una en cada borde de cada segmento. El espectador oye lo
        que suena, así que la palabra está si **más de la mitad** de su duración
        cae dentro. Para la que no dura, la vara es estar dentro.
        """
        if self.sin_duracion:
            return a <= self.empieza <= b
        return (min(b, self.acaba) - max(a, self.empieza)) > self.dura / 2

    # ── lo que se puede afirmar de ella ──────────────────────────────────────
    def pegada_a(self, fin_del_habla: float) -> "Palabra":
        """Recortada al tramo de voz donde empieza. **No inventa.**

        Los tramos los midió el detector de silencio sobre la onda; que la
        palabra acabó antes de que empezara ese silencio es lo único que se
        puede sostener.
        """
        if self.acaba <= fin_del_habla + 0.02:
            return self
        return dataclasses.replace(
            self, acaba=round(max(fin_del_habla, self.empieza), 3))

    def en_el_hueco(self, desde: float, hasta: float) -> "Palabra":
        """La coloca dentro del hueco que le toca, sin pisar a nadie.

        Una palabra sin duración no se puede ordenar contra sus vecinas: el
        subtítulo la repite y un corte que empiece en su instante se la lleva
        sin que nadie lo cuente. Se le da el trozo que le corresponde del hueco
        libre — es el mínimo para existir y poder ordenarla, **no** una
        estimación de lo que tardó en decirse.
        """
        if not self.sin_duracion:
            return self
        return dataclasses.replace(self, empieza=round(desde, 3),
                                   acaba=round(max(hasta, desde), 3))

    @property
    def sin_sitio(self) -> bool:
        """No cabe ni el mínimo: el modelo no supo dónde ponerla.

        Pasa cuando varias palabras salen estampadas en el mismo instante y el
        audio de ahí no da para todas — siete palabras en 0,04 s. No es una
        palabra corta: es texto que **no se puede afirmar que suene ahí**, y
        casi siempre es el modelo repitiendo algo que ya dijo. Se marca en vez
        de borrarse, porque borrar texto del transcript es decisión de quien
        monta, no del que mide.
        """
        return self.dura < MINIMA / 2

    # ── cómo se compara ──────────────────────────────────────────────────────
    @property
    def comparable(self) -> str:
        """Para buscarla en un ancla. Ver `dominio.texto.comparable`."""
        return _tx.comparable(self.texto)

    def __str__(self) -> str:
        return f"{self.texto}[{self.empieza:.3f}-{self.acaba:.3f}]"
