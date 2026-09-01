"""Qué etapas hay que describir, y con qué delante.

El listado sale de la **estructura** —las etapas que el frame define— y no del
montaje, porque el montaje es justo lo que puede haber perdido una. Pero lo que
se describe es el montaje, así que cada fila viaja con las dos mitades: la
función que la etapa cumple y lo que de verdad se dice ahí hoy.

**Sin filtro en SQL.** Antes se excluía aquí toda etapa ya descrita, y por eso una
descripción caducada no se volvía a pedir: el paso decía «nada que describir» y
la puerta paraba la pieza sin que nadie supiera qué faltaba. Ahora se traen todas
y se descartan abajo las que siguen hablando de su texto — que es una comparación
de textos y no cabe en el WHERE.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from .montaje import Montaje  # noqa: E402
from .pieza import Pieza  # noqa: E402
from .repetido import repetido  # noqa: E402

ETAPAS = """
    select v.slug, e.orden, ec.nombre as etapa, es.nombre as estructura,
           e.mensaje_esperado as mensaje, l.texto as libreto,
           (select group_concat(u.texto, ' ') from eleccion el
              join fragmento f on f.id = el.fragmento_id
              join fragmento_unidad fu on fu.fragmento_id = f.id
              join unidad u on u.id = fu.unidad_id
             where el.etapa_id = e.id) as dicho
      from etapa e
      join video v on v.id = e.video_id
      join estructura es on es.id = e.estructura_id
      left join etapa_canonica ec
             on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
      left join libreto l on l.video_id = v.id and l.orden = e.orden
     where l.texto is not null {donde}
     order by v.slug, e.orden
"""


def quitadas(slug: str) -> set:
    """Las etapas que una nota de corte sacó de la pieza **a propósito**.

    Lo mismo que mira `verificar` para no contar como falta lo que alguien mandó
    quitar (C-106). Las dos preguntas son la misma: **una etapa ausente por
    decisión no es una etapa ausente por falta**.
    """
    try:
        con = basedatos.abrir()
        filas = con.execute(
            "select que from revision where video_slug = ? and accion='cortar'"
            " and estado='aplicada' and regla='seccion que sobra'",
            (slug,)).fetchall()
        con.close()
    except Exception:                              # noqa: BLE001
        return set()
    return {int(b) for (q,) in filas for b in re.findall(r"e(\d+)", q or "")}


class _DeLaPieza:
    """Lo que hay que calcular una vez por pieza, no una vez por etapa.

    `repetido` mide la entrega de cada aparición con el detector de F0: llamarlo
    dentro del bucle de filas lo repetía una vez por etapa —nueve veces la misma
    cuenta en reel-05— para tirar ocho de los nueve resultados.
    """

    def __init__(self, slug: str):
        m = Montaje(slug)
        self.texto = Pieza(int(slug.split("-")[1])).texto
        self.bordes = m.bordes_sucios()
        self.repetido = repetido(m)
        self.quitadas = quitadas(slug)


def por_describir(reels=None, rehacer: bool = False) -> list:
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    donde, args = "", []
    if reels:
        donde = " and v.slug in (%s)" % ",".join("?" * len(reels))
        args = [f"reel-{int(r):02d}" for r in reels]
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    filas = con.execute(ETAPAS.format(donde=donde), args).fetchall()
    # La caducidad se decide comparando textos, y en SQL no se puede porque el
    # montaje se calcula leyendo la cinta. Se trae lo escrito y se compara aquí.
    guardado = {(r["video_slug"], r["etapa_orden"]): (r["sobre_texto"] or "")
                for r in con.execute("select video_slug, etapa_orden,"
                                     " sobre_texto from escena_desc")}
    con.close()

    fuera, piezas = [], {}
    for f in filas:
        d = dict(f)
        slug, orden = d["slug"], int(d["orden"])
        if slug not in piezas:
            piezas[slug] = _DeLaPieza(slug)
        p = piezas[slug]
        # **Lo que se dijo es lo que dice el montaje, no lo que se eligió.** El
        # `dicho` de la base queda como respaldo para la etapa que no tiene toma
        # —la que va a tablero—, porque ahí no hay montaje del que leer.
        d["montaje"] = p.texto.get(orden)
        # **Una etapa que no esta en la pieza no se describe.** Cuando una se
        # corta entera seguía pidiéndose: la puerta de composición reclamaba una
        # descripción de la etapa 5 del reel-01 después de que Jaime la mandara
        # sacar, y la pieza no podía avanzar por describir algo que ya no suena.
        #
        # **Y la diferencia es por qué no está, no que no esté.** Se cortó por
        # decisión —hay nota, y describirla es trabajo perdido— o nunca tuvo
        # material —reel-04 e5 tiene cero candidatas—, y ésa **sí** hay que
        # describirla, porque el frame la necesita y va a tablero. La primera
        # versión miraba si había `dicho`, y eso mezclaba las dos: dejaba sin
        # describir la etapa que más lo necesita.
        if not (d["montaje"] or "").strip() and orden in p.quitadas:
            continue
        # Los bordes y lo repetido van **con la etapa**, para que quien compone
        # los resuelva con el texto delante en vez de dejárselos a un umbral.
        d["bordes"] = p.bordes.get(orden) or []
        d["repetido"] = [r for r in p.repetido if r["etapa"] == orden]
        if not rehacer:
            g = guardado.get((slug, orden))
            if g is not None and " ".join(g.split()) == " ".join(
                    (d["montaje"] or "").split()):
                continue                 # descrita y sigue hablando de este texto
        fuera.append(d)
    return fuera
