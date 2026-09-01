"""Una etapa del frame: qué función cumple, qué la dice y qué **tiene** que decir.

**Por qué es un objeto.** Era `frame["beats"][i]` más `beats[i]` más `i + 1`,
tres datos sueltos que viajaban juntos por seis sitios y que cada sitio volvía a
desempaquetar a su manera. De ahí salía el mismo `all(dice(texto, t) for t in
etapa.get("debe_decir") or [])` escrito cuatro veces — y escrito cuatro veces es
cuatro reglas en cuanto alguien toca una.

La etapa sabe una sola cosa que nadie más puede saber: **si un texto la cumple**.
Y la cumple o no la cumple por lo que el frame declara en `debe_decir`, no por
parecerse al párrafo del libreto. Jaime: *«la idea no es tomar el libreto
literal, es tomar la intención comunicativa de cada parte, respetando su
función»*.
"""
from __future__ import annotations

import dataclasses

from .candidata import dice


@dataclasses.dataclass(frozen=True, slots=True)
class Etapa:
    """La etapa número `n` de la pieza, tal y como la declara el frame."""

    #: 1-based, como se cuenta en los avisos y como se guarda en el EDL.
    n: int
    #: La entrada de `frame["beats"][n - 1]`: nombre, obligatorio, debe_decir.
    declarada: dict
    #: El párrafo del libreto que la dice. **Vocabulario, no texto a copiar.**
    parrafo: str
    #: El párrafo de la etapa siguiente, o `None` si ésta es la última. Hace
    #: falta para saber cuándo un barrido hacia delante se ha pasado de etapa.
    siguiente: str | None = None

    @classmethod
    def de(cls, frame, parrafos, i: int) -> "Etapa":
        """La etapa `i` (0-based) de un frame ya cuadrado con su libreto."""
        return cls(i + 1, frame["beats"][i], parrafos[i],
                   parrafos[i + 1] if i + 1 < len(parrafos) else None)

    @classmethod
    def todas(cls, frame, parrafos) -> list:
        return [cls.de(frame, parrafos, i) for i in range(len(parrafos))]

    # ── lo que la etapa es ───────────────────────────────────────────────────
    @property
    def nombre(self) -> str:
        return self.declarada["etapa"]

    @property
    def obligatoria(self) -> bool:
        return bool(self.declarada.get("obligatorio"))

    @property
    def debe_decir(self) -> list:
        """Lo que tiene que sonar sí o sí. Condición **dura**, no puntuación.

        Jaime, del reel 2: *«el guion deja de lado los puntos comparativos; eso
        debe quedar claro en el proceso, no es solo el guion, es la intención
        comunicativa: si es comparar, entonces las comparaciones deben ser
        claras»*. La cobertura no lo puede ver —un trozo sin la cifra cubre
        mucho vocabulario— así que quien no lo diga no compite.
        """
        return self.declarada.get("debe_decir") or []

    # ── lo único que sólo ella puede contestar ───────────────────────────────
    def cumplida_por(self, texto: str) -> bool:
        """¿Este texto dice lo que la etapa exige? Sin `debe_decir`, siempre sí."""
        return all(dice(texto or "", t) for t in self.debe_decir)

    def __str__(self) -> str:
        marca = "!" if self.obligatoria else " "
        return f"{marca}{self.n:2} {self.nombre}"
