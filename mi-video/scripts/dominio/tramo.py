"""Un trozo de una cinta: desde, hasta y **de cuál**.

**Por qué es un objeto.** Era una lista: `[desde, hasta]` unas veces y
`[desde, hasta, cinta]` otras. Quien la recibía decidía por su cuenta cuál de
las dos formas aceptaba, y las dos mitades de la misma decisión acabaron
discrepando: `repaso` aceptaba tres elementos y `revalidar` filtraba por
`len(t) == 2`, **tirando en silencio justo el trozo que viene de otra
grabación** — que es donde vive el escalón del precio de dos piezas, y sin
escalón la pieza no sale por cumplimiento (C-151).

Con la lista, esa divergencia era invisible. Con el objeto es imposible: un
`Tramo` siempre sabe de qué cinta es.
"""
from __future__ import annotations

import dataclasses
import hashlib


class TramoInvalido(ValueError):
    """Un tramo que no se puede sostener. Se dice, no se corrige por lo bajo."""


@dataclasses.dataclass(frozen=True, slots=True)
class Tramo:
    """De `desde` a `hasta`, en tiempo de la cinta `cinta`."""

    desde: float
    hasta: float
    cinta: str = ""

    def __post_init__(self) -> None:
        if self.hasta <= self.desde:
            raise TramoInvalido(
                f"un tramo no puede acabar antes de empezar: {self.desde}-{self.hasta}")

    # ── cómo nace ────────────────────────────────────────────────────────────
    @classmethod
    def de_lista(cls, t, cinta: str = "") -> "Tramo":
        """De `[desde, hasta]` o `[desde, hasta, cinta]`. Las dos, siempre.

        La forma corta hereda la cinta que le pase quien llama —normalmente la
        del beat—; la larga manda sobre ella, porque decir la cinta es
        exactamente lo que significa el tercer elemento.
        """
        if isinstance(t, Tramo):
            return t
        try:
            a, b = float(t[0]), float(t[1])
        except (TypeError, ValueError, IndexError) as e:
            raise TramoInvalido(f"no es un tramo: {t!r}") from e
        propia = str(t[2]) if len(t) > 2 and t[2] else ""
        return cls(round(a, 3), round(b, 3), propia or cinta)

    def a_lista(self) -> list:
        """De vuelta a lista, mientras queden consumidores que la esperan."""
        return [self.desde, self.hasta, self.cinta] if self.cinta \
            else [self.desde, self.hasta]

    # ── lo que sabe de sí mismo ──────────────────────────────────────────────
    @property
    def dura(self) -> float:
        return self.hasta - self.desde

    def solapa(self, otro: "Tramo") -> bool:
        """¿Se pisan? Sólo tiene sentido dentro de la misma cinta."""
        return (self.cinta == otro.cinta
                and self.hasta > otro.desde and otro.hasta > self.desde)

    def palabras_de(self, palabras) -> list:
        """Las que se oyen aquí dentro, con la vara del oído."""
        return [p for p in palabras if p.suena_en(self.desde, self.hasta)]

    def texto_de(self, palabras) -> str:
        return " ".join(p.texto for p in self.palabras_de(palabras)).strip()

    def huella_de(self, palabras) -> str | None:
        """La prueba contra la que se declaró algo aquí.

        Doce caracteres del texto que suena dentro. Es lo que permite saber que
        una declaración vieja habla de otras palabras cuando la cinta cambia —
        sin esto, una decisión sobrevive a la prueba que la justificaba (C-149).
        """
        from . import texto as _tx

        dentro = _tx.comparable(self.texto_de(palabras))
        if not dentro.strip():
            return None
        return hashlib.sha1(" ".join(dentro.split()).encode("utf-8")).hexdigest()[:12]

    def __str__(self) -> str:
        c = f" @{self.cinta}" if self.cinta else ""
        return f"[{self.desde:.3f}-{self.hasta:.3f}{c}]"
