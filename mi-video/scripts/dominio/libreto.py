"""Qué dice una pieza y qué estructura ejecuta: el libreto y su frame.

Son dos datos y **dos fuentes distintas**, y por eso están juntos: la única regla
que los ata es que tienen que cuadrar en número, y esa comprobación no tenía
dueño.

## El libreto sale de la base, y de ningún otro sitio

Vivía en dos: la tabla `libreto` y `docs/libretos.md`. Quien corrige escribe en
uno; quien monta leía el otro. Es el patrón que costó el día entero — Jaime,
después de recibir tres veces la misma pieza: *«la decisión de componer está
escuchando las indicaciones viejas»*.

Y no era teórico: el parser del markdown **tiraba en silencio los párrafos de
menos de 40 caracteres**, un filtro puesto para saltarse encabezados. La séptima
pieza tiene ocho etapas en la base y el markdown devolvía siete: la que faltaba
era *«Le dejo el link abajo.»* — el registro, que es la etapa que pide la acción.

`docs/libretos.md` se queda como documento para leer y **no se lee desde aquí**;
si hace falta regenerarlo, se genera desde la base, nunca al revés. El
reconstruido vive en `docs/libretos-reconstruido.md` marcado NO USAR.

## La estructura sale de `ads/frames.json`, no de una etiqueta del libreto

Tres de las seis etiquetas que traían los libretos nombraban el **mecanismo
conductual** y una nombraba una configuración orgánica de EDUCATE, que no es una
estructura de pago. El mecanismo y la estructura son decisiones distintas y se
declaran aparte.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

#: Donde vive la base. La declara `basedatos`, que es su dueno; aqui solo se usa.
BASE = basedatos.BASE
#: El documento que entrego Jaime. Se lee con los ojos, no desde el codigo.
LIBRETOS = os.path.join("..", "docs", "libretos.md")
FRAMES = os.path.join("ads", "frames.json")


class Libreto:
    """Lo que la pieza `n` tiene que decir, y en qué orden."""

    __slots__ = ("n", "slug")

    def __init__(self, n: int):
        self.n = int(n)
        self.slug = f"reel-{self.n:02d}"

    @property
    def beats(self) -> list:
        """Los beats de la pieza, **desde la base**. Un párrafo, un beat."""
        con = basedatos.abrir(BASE)
        filas = con.execute(
            "select l.texto from libreto l join video v on v.id = l.video_id"
            " where v.slug = ? order by l.orden", (self.slug,)).fetchall()
        con.close()
        if not filas:
            raise SystemExit(
                f"sin libreto para el reel {self.n} — la tabla `libreto` no tiene"
                f" filas. El libreto se declara ahi, no en docs/libretos.md.")
        return [" ".join(str(f[0]).split()) for f in filas]

    def frame(self, beats=None) -> dict:
        """Qué estructura ejecuta el reel y qué función cumple cada beat.

        Si el libreto cambia de número de párrafos, esto **para**. Es el
        aprendizaje 24 aplicado antes de que haga daño: un fichero declarado no
        se entera de que editaste su fuente, y un beat corrido de sitio reasigna
        todas las funciones a partir de ahí sin avisar de nada.
        """
        if beats is None:
            beats = self.beats
        d = json.load(open(FRAMES, encoding="utf-8"))
        f = d["reels"].get(self.slug)
        if not f:
            raise SystemExit(f"{self.slug} sin estructura declarada en {FRAMES}")
        if len(f["beats"]) != len(beats):
            raise SystemExit(
                f"{self.slug}: el libreto tiene {len(beats)} párrafos y "
                f"{FRAMES} declara {len(f['beats'])} beats. Uno de los dos cambió; "
                f"cuadrarlos antes de montar.")
        return f

    def __str__(self) -> str:
        return self.slug
