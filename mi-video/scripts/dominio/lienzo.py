"""El cuadro de una pieza: cuánto mide y con qué proporción se recorta.

**Por qué es un objeto.** La cadena de Python daba por hecho el vertical en
diez sitios: `scale=1080:1920` en `punch-ins.py` y `cortar.py`, el `9/16` del
recorte, los 950 px útiles de `subtitular.py`, el 216×384 de `trasfondo.py` y
`emision.py`, que rechaza todo lo que no mida 1080×1920. El CV de YBL es
horizontal y habría salido recortado a 9:16 sin que nada avisara (C-671).

Los números viven en `src/brand/lienzos.json` y **sólo ahí**: es el mismo
fichero que leen `src/brand/lienzo.ts` y `scripts/lienzo.mjs` (C-670). Una pieza
elige el suyo con `formato` en `ads/frames.json`; sin declararlo, vertical, y
lo de hoy no se entera.
"""
from __future__ import annotations

import dataclasses
import json
import math
import os
import re

#: Los lienzos de la línea, compartidos con el render.
LIENZOS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "src", "brand", "lienzos.json")
FRAMES = os.path.join("ads", "frames.json")
#: El de una pieza que no declara otro.
POR_DEFECTO = "vertical"
#: El nombre de pieza dentro de una ruta: `work/scenes/reel-23/plan-full.json`.
_PIEZA = re.compile(r"reel-\d+")


class FormatoDesconocido(ValueError):
    """Una pieza que pide un cuadro que no está declarado. No se adivina."""


@dataclasses.dataclass(frozen=True, slots=True)
class Lienzo:
    """Un cuadro de salida: su formato y sus píxeles."""

    formato: str
    ancho: int
    alto: int
    banda: int
    #: Lo que queda entre los márgenes seguros: donde cabe una línea de texto.
    util: int
    #: Desde abajo, en píxeles: donde se apoya el cc pegado a la barbilla y el
    #: borde inferior de la zona segura. De ahí salen las bandas del cc (C-692).
    cc_abajo: int
    seguro_abajo: int

    # ── cómo nace ────────────────────────────────────────────────────────────
    @classmethod
    def de(cls, formato: str = POR_DEFECTO) -> "Lienzo":
        with open(LIENZOS, encoding="utf-8") as f:
            todos = json.load(f)
        if formato not in todos or formato.startswith("_"):
            raise FormatoDesconocido(
                f"formato «{formato}»: no está en src/brand/lienzos.json")
        d = todos[formato]
        return cls(formato, int(d["width"]), int(d["height"]),
                   int(d["captionBand"]),
                   int(d["width"]) - int(d["safe"]["left"]) - int(d["safe"]["right"]),
                   int(d["captionBottom"]), int(d["safe"]["bottom"]))

    @classmethod
    def de_pieza(cls, slug: str) -> "Lienzo":
        """El que declara la pieza en `frames.json`; sin declarar, vertical."""
        try:
            with open(FRAMES, encoding="utf-8") as f:
                pedido = (json.load(f)["reels"].get(slug) or {}).get("formato")
        except (OSError, KeyError, ValueError):
            pedido = None
        return cls.de(pedido or POR_DEFECTO)

    @classmethod
    def de_ruta(cls, ruta: str) -> "Lienzo":
        """El de la pieza que nombra una ruta; sin pieza, vertical."""
        m = _PIEZA.search(str(ruta).replace("\\", "/"))
        return cls.de_pieza(m.group(0)) if m else cls.de()

    @classmethod
    def en_pedido(cls, slug: str) -> dict:
        """Lo que viaja en el pedido: nada si la pieza es vertical (C-671).

        Así un pedido vertical queda idéntico al de antes y no caduca ninguna
        respuesta en vuelo; los contratos dicen qué hacer con `formato`.
        """
        formato = cls.de_pieza(slug).formato
        return {} if formato == POR_DEFECTO else {"formato": formato}

    # ── lo que sabe ──────────────────────────────────────────────────────────
    @property
    def suelo_cc(self) -> float:
        """Suelo del cc pegado a la barbilla, en fracción de la altura: 1160/1920."""
        return (self.alto - self.cc_abajo) / self.alto

    @property
    def suelo_franja(self) -> float:
        """Suelo de la franja bajo un tablero: el borde de la zona segura, 1248/1920."""
        return (self.alto - self.seguro_abajo) / self.alto

    @property
    def vertical(self) -> bool:
        return self.alto > self.ancho

    @property
    def proporcion(self) -> tuple:
        """Ancho y alto reducidos: `(9, 16)` o `(16, 9)`. Para recortar exacto."""
        g = math.gcd(self.ancho, self.alto)
        return self.ancho // g, self.alto // g

    @property
    def escala(self) -> str:
        """El `scale` de ffmpeg que lleva un recorte al cuadro de salida."""
        return f"scale={self.ancho}:{self.alto}"

    def llenar(self) -> str:
        """Escalar y recortar al cuadro, sin deformar: lo que no tiene encuadre."""
        return (f"{self.escala}:force_original_aspect_ratio=increase,"
                f"crop={self.ancho}:{self.alto}")
