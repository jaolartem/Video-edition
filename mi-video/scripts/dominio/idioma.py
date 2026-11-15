"""La lengua en que habla una cinta, y lo que eso cambia de cómo se la lee.

**Por qué es un objeto.** El español estaba escrito en dos capas y ninguna lo
declaraba: `-l es` en ocho llamadas a whisper, y seis listas de palabras de
función repartidas por `habla.py`, `texto.py`, `redundancia.py`,
`repeticiones.py`, `colgantes.json` y `describir-pedido.mjs`. Una cinta en
inglés —el CV de YBL, C-665— habría pasado por todas sin que nadie avisara: el
modelo transcribe en español lo que oye en inglés, y las listas no filtran
ninguna palabra inglesa, así que «the» pesaría como contenido.

Aquí la lengua es **una propiedad de la cinta**. La declara `rutas.json` →
`idiomas` (toma → código), sin entrada es español, y lo de hoy no se entera.
Las listas viven en `scripts/idiomas/<código>.json`, una por regla.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rutas  # noqa: E402

#: Donde vive cada lengua. Una por fichero, con las mismas claves.
CARPETA = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "idiomas")
#: La de siempre. Una cinta sin entrada en `idiomas` habla esto.
POR_DEFECTO = "es"
#: El nombre de pieza dentro de una ruta: `out/reels/reel-23-final.mp4`.
_PIEZA = re.compile(r"reel-\d+")


class IdiomaDesconocido(ValueError):
    """Una cinta declarada en una lengua sin fichero. Se dice, no se adivina."""


@dataclasses.dataclass(frozen=True, slots=True)
class Idioma:
    """Una lengua: cómo se le pide a whisper y qué palabras no cuentan."""

    codigo: str
    colgantes: frozenset
    no_cierra: frozenset
    vacias: frozenset
    niegan: tuple
    claves_vacias: frozenset
    llanas: frozenset
    #: El modelo de whisper con que se oye bien esta lengua (fichero en
    #: `whisper.cpp/`). Sin declararlo, `medium`, el de siempre.
    modelo: str = "ggml-medium.bin"

    # ── cómo nace ────────────────────────────────────────────────────────────
    @classmethod
    def de(cls, codigo: str = POR_DEFECTO) -> "Idioma":
        """La lengua `codigo`, leída una vez por proceso."""
        if codigo not in _CARGADAS:
            ruta = os.path.join(CARPETA, f"{codigo}.json")
            if not os.path.exists(ruta):
                raise IdiomaDesconocido(
                    f"no hay {ruta}: declara la lengua o quita la entrada de"
                    f" `idiomas` en rutas.json")
            with open(ruta, encoding="utf-8") as f:
                d = json.load(f)
            _CARGADAS[codigo] = cls(
                codigo=d["whisper"],
                colgantes=frozenset(d["colgantes"]),
                no_cierra=frozenset(d["no_cierra"]),
                vacias=frozenset(d["vacias"]),
                niegan=tuple(d["niegan"]),
                claves_vacias=frozenset(d["claves_vacias"]),
                llanas=frozenset(d["llanas"]),
                modelo=d.get("modelo") or "ggml-medium.bin")
        return _CARGADAS[codigo]

    @classmethod
    def de_cinta(cls, toma: str) -> "Idioma":
        """La lengua de la grabación `toma`, como la declara `rutas.json`."""
        return cls.de(rutas.IDIOMAS.get(toma, POR_DEFECTO))

    @classmethod
    def de_pieza(cls, slug: str) -> "Idioma":
        """La lengua de una pieza es la de su cinta."""
        return cls.de_cinta(rutas.TOMAS.get(slug, slug))

    @classmethod
    def de_ruta(cls, ruta: str) -> "Idioma":
        """La de la pieza que nombra un fichero; sin pieza, la de siempre."""
        m = _PIEZA.search(os.path.basename(ruta))
        return cls.de_pieza(m.group(0)) if m else cls.de()

    @classmethod
    def en_pedido(cls, slug: str) -> dict:
        """Lo que viaja en el pedido: nada si la pieza habla español.

        Así un pedido en español queda idéntico al de antes y no caduca
        ninguna respuesta en vuelo; los contratos dicen qué hacer con ella.
        """
        codigo = cls.de_pieza(slug).codigo
        return {} if codigo == POR_DEFECTO else {"idioma": codigo}

    # ── lo que sabe ──────────────────────────────────────────────────────────
    @property
    def banderas(self) -> list:
        """Lo que se le pasa a whisper.cpp para que oiga esta lengua."""
        return ["-l", self.codigo]

    def colgante(self, txt: str) -> bool:
        """¿Deja esta palabra la idea a medias si la etapa acaba en ella?"""
        return txt.strip(".,¿?¡!;:").lower() in self.no_cierra


_CARGADAS: dict = {}

#: El español, que es lo que habla toda cinta sin declarar.
ES = Idioma.de()
