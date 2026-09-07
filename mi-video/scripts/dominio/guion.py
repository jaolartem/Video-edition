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
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

#: Cómo se declara una pausa que hay que conservar. Va **en el libreto**, que es
#: donde Jaime escribe: *«probablemente te deje aviso por libreto»*.
#:
#: **Y dice de qué lado.** `[pausa]` a secas conserva la etapa entera, y eso era
#: todo lo que se podía decir: en reel-01 el beat 7 tiene el silencio que Jaime
#: quiere —el de después de «semanales»— y otro de 1,0 s dentro de la frase que
#: mandó quitar, así que declarar la etapa devolvía los dos. Un lado no es un
#: matiz del otro: son dos decisiones distintas sobre el mismo trozo.
MARCA_PAUSA = re.compile(
    r"[\[(]\s*(?:pausa|silencio)(?:\s+(entrada|salida|ambas))?\s*[\])]", re.I)
#: Dónde se conserva el silencio, y qué se entiende por una marca sin lado.
LADOS = ("entrada", "salida", "ambas")
POR_DEFECTO = "ambas"
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
        """Las etapas cuyo silencio **no se recorta**, con su lado y su motivo.

        Regla de Jaime, y cierra el tema del aire: *«lo de los silencios también
        puede ser aritmético, no hace falta criterio editorial — excepto cuando
        aporta: por ejemplo antes de una revelación o de una afirmación
        importante, siempre y cuando el silencio sea mirando a cámara»*.

        O sea: **quitar aire es aritmética y se hace sola**; conservar una pausa
        es una decisión, y las decisiones se declaran. Se declaran donde él las
        escribe —en el texto del libreto, con `[pausa]` delante de la frase que
        quiere que respire—, así no hace falta ni una tabla nueva ni acordarse de
        nada: la marca viaja con el guion.

        **`donde` dice de qué lado**: `entrada`, `salida` o `ambas`. Una marca
        sin lado vale por las dos, que es lo que significaba antes.
        """
        fuera = {}
        for orden, t in self.textos().items():
            m = MARCA_PAUSA.search(t)
            if m:
                fuera[orden] = {"donde": (m.group(1) or POR_DEFECTO).lower(),
                                "motivo": t[m.start():m.start() + MOTIVO].strip()}
        return fuera

    def declarar_pausa(self, orden, donde=POR_DEFECTO, por_que="") -> str:
        """Escribe la marca en el libreto de esa etapa. Sustituye la que hubiera.

        Existe para que declarar una pausa **no sea editar la base a mano**, que
        es por donde este proyecto pierde el estado: la decisión vive en la única
        fuente del libreto (`verdad.py`) y la escribe quien la lee.

        La marca va al final para `salida` —el silencio viene detrás de lo que
        se dice— y delante en los otros dos casos.
        """
        donde = str(donde).lower()
        if donde not in LADOS:
            raise ValueError(f"pausa de lado desconocido: {donde!r}, no {LADOS}")
        limpio = MARCA_PAUSA.sub("", self.texto(orden)).strip()
        if not limpio:
            raise ValueError(f"{self.slug} e{orden}: no hay libreto que marcar")
        marca = " ".join(x for x in (f"[pausa {donde}]", por_que.strip()) if x)
        nuevo = f"{limpio} {marca}" if donde == "salida" else f"{marca} {limpio}"
        con = basedatos.abrir()
        con.execute("update libreto set texto = ? where orden = ? and video_id ="
                    " (select id from video where slug = ?)",
                    (nuevo, orden, self.slug))
        con.commit()
        con.close()
        self._textos = None
        return nuevo

    def __str__(self) -> str:
        return f"libreto de {self.slug} ({len(self.textos())} etapas)"
