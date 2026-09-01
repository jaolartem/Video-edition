"""El libreto de una pieza: lo que se escribió, etapa por etapa.

Es la mitad **teórica** de la unidad de análisis —*«la sección de frame sale de
la unión de lo teórico, el libreto, con lo práctico, la grabación»*— y vive en la
tabla `libreto` de la base, que es su única fuente (ver `verdad.py`).

Se pregunta desde dos sitios y por dos cosas distintas: si una repetición estaba
pedida por el guion, y si una etapa lleva declarada una pausa que hay que
conservar. Las dos leían la misma tabla con su propia consulta escrita a mano.

**Y esto cabe dentro de `dominio.libreto.Libreto`**, que lee la misma tabla para
otra pregunta —los párrafos en orden y su frame—. Están separados porque nacieron
a la vez y en dos manos, no porque sean dos cosas: `Libreto` indexa por posición
y aquí hace falta por `orden`, que es la única diferencia real. Se dice aquí para
que la unión sea un trabajo pendiente con nombre y no un descubrimiento.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

#: Cómo se declara una pausa que hay que conservar. Va **en el libreto**, que es
#: donde Jaime escribe: *«probablemente te deje aviso por libreto»*.
MARCA_PAUSA = ("[pausa]", "(pausa)", "[silencio]", "(silencio)")
#: Cuánto del texto se guarda como motivo de la pausa: lo justo para reconocerla.
MOTIVO = 90


class Guion:
    """Lo que el libreto de `slug` dice de cada etapa."""

    __slots__ = ("slug", "_textos")

    def __init__(self, slug: str):
        self.slug = str(slug)
        self._textos = None

    def textos(self) -> dict:
        """`{orden: texto}`. Una sola consulta, aunque se pregunten dos cosas."""
        if self._textos is None:
            con = basedatos.abrir()
            con.row_factory = sqlite3.Row
            self._textos = {
                r["orden"]: (r["texto"] or "") for r in con.execute(
                    "select l.orden, l.texto from libreto l"
                    " join video v on v.id = l.video_id"
                    " where v.slug = ? order by l.orden", (self.slug,))}
            con.close()
        return self._textos

    def texto(self, orden) -> str:
        return self.textos().get(orden, "")

    def pausas(self) -> dict:
        """Las etapas cuyo silencio de entrada **no se recorta**, con su motivo.

        Regla de Jaime, y cierra el tema del aire: *«lo de los silencios también
        puede ser aritmético, no hace falta criterio editorial — excepto cuando
        aporta: por ejemplo antes de una revelación o de una afirmación
        importante, siempre y cuando el silencio sea mirando a cámara»*.

        O sea: **quitar aire es aritmética y se hace sola**; conservar una pausa
        es una decisión, y las decisiones se declaran. Se declaran donde él las
        escribe —en el texto del libreto, con `[pausa]` delante de la frase que
        quiere que respire—, así no hace falta ni una tabla nueva ni acordarse de
        nada: la marca viaja con el guion.
        """
        fuera = {}
        for orden, t in self.textos().items():
            bajo = t.lower()
            for m in MARCA_PAUSA:
                if m in bajo:
                    i = bajo.index(m)
                    fuera[orden] = t[i:i + MOTIVO].strip()
                    break
        return fuera

    def __str__(self) -> str:
        return f"libreto de {self.slug} ({len(self.textos())} etapas)"
