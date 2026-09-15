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

#: Las etapas de cierre: desde la primera, la pieza vende. Vivía en
#: `seleccion/edl.py`, que la usa para las zonas; aquí la usa también el corte
#: de una pieza que deriva de otra sin su CTA (C-388).
CIERRE = ("promesa", "urgencia", "registro", "aplicación", "aplicacion")

#: Lo que declara una pieza derivada. Lo demás se hereda de su origen.
#: `portada` está aquí porque **es suya y no de su origen**: lleva el fotograma
#: de SU corte. reel-13 y reel-06 dicen lo mismo y se ven distinto, así que
#: heredar la portada seria poner la cara de otro montaje en la miniatura.
DECLARA = ("_deriva", "deriva_de", "pilar", "cara", "lectura", "quita",
           "portada")

#: Lo del origen que una derivada NO hereda: todo es del cierre que se corta.
#: `debe_decir` de pieza lleva las cifras de ese cierre (reel-01: «550|576»).
NO_HEREDA = ("cierre", "_cierre", "nota_de_cierre", "debe_decir")


def derivada(origen: dict, decl: dict) -> dict:
    """La pieza que deriva de otra, **resuelta** (C-388).

    Jaime, 10-9-2026: *«toma los 7 videos y conviértelos en reels, es decir
    quítales el CTA comercial»*. La derivada hereda las etapas de su origen
    **hasta la primera de cierre**, menos las que declara en `quita`, y nada del
    CTA: ni `cierre` —la frase del link—, ni el `debe_decir` de pieza. Y lleva
    `de_origen`, qué etapa del origen es cada una de las suyas.
    """
    beats = origen["beats"]
    corte = next((i for i, b in enumerate(beats)
                  if any(c in (b.get("etapa") or "").lower() for c in CIERRE)),
                 len(beats))
    quita = set(decl.get("quita") or [])
    quedan = [i for i in range(corte) if i + 1 not in quita]
    f = {k: v for k, v in origen.items() if k not in NO_HEREDA}
    f["beats"] = [beats[i] for i in quedan]
    s = origen.get("senala")
    f["senala"] = ({**s, "beat": quedan.index(s["beat"] - 1) + 1}
                   if s and s.get("beat", 0) - 1 in quedan else None)
    f.update({k: decl[k] for k in DECLARA if k in decl})
    f["de_origen"] = [i + 1 for i in quedan]
    return f


def escribir_derivadas(ruta: str = FRAMES) -> list:
    """Expande en `frames.json` las piezas que derivan de otra. Devuelve cuáles.

    **La declaración es una línea**; lo demás se vuelve a generar desde su
    origen cada vez, igual que `estado.json` publica lo que dice la base. Así
    los quince sitios que leen `frames.json` ven una pieza entera sin que
    ninguno tenga que saber qué es derivar, y un cambio en el origen llega solo.
    Lo llama `db.migrar`, que corre al arrancar la línea.
    """
    texto = open(ruta, encoding="utf-8").read()
    d = json.loads(texto)
    cambian = []
    for slug, f in d["reels"].items():
        origen = d["reels"].get(f.get("deriva_de") or "")
        if not origen or origen.get("deriva_de"):
            continue
        nuevo = derivada(origen, f)
        if nuevo != f:
            d["reels"][slug] = nuevo
            cambian.append(slug)
    if cambian:
        with open(ruta, "w", encoding="utf-8", newline="\n") as h:
            h.write(json.dumps(d, ensure_ascii=False, indent=1)
                    + ("\n" if texto.endswith("\n") else ""))
    return cambian


def origen_de(slug: str) -> tuple:
    """`(origen, {etapa del origen: etapa suya})`, o `(None, {})` si no deriva."""
    try:
        f = json.load(open(FRAMES, encoding="utf-8"))["reels"].get(slug) or {}
    except (OSError, ValueError):
        return None, {}
    if not f.get("deriva_de"):
        return None, {}
    return f["deriva_de"], {o: j + 1 for j, o in enumerate(f.get("de_origen") or [])}


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
