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
from .texto import dice_lo_mismo  # noqa: E402
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
    # **«Nada que describir» y «esta pieza no está declarada» no son lo mismo.**
    #
    # reel-07 pasó por aquí con **cero etapas** —estaba en `ads/frames.json` con
    # sus ocho beats y la base no se había enterado— y esta consulta devolvió
    # una lista vacía, que el paso leyó como «ya está todo descrito» y dio por
    # bueno. La pieza siguió camino y sólo reventó tres fases más arriba, con un
    # mensaje que apuntaba a este paso: «sin descripción de escena, corre el
    # paso 4». Correrlo mil veces no habría arreglado nada.
    #
    # Una pieza sin etapas no es una pieza terminada: es una pieza sin declarar,
    # y decir «nada que hacer» es mentir en el único sitio donde alguien mira.
    for s in args:
        n = con.execute("select count(*) from etapa e join video v"
                        " on v.id = e.video_id where v.slug = ?", (s,)).fetchone()[0]
        if not n:
            con.close()
            raise ValueError(
                f"{s} no tiene ni una etapa declarada en la base. No es que no"
                f" haya nada que describir: es que no hay pieza. Corre"
                f" `python scripts/db.py migrar` para meter `ads/frames.json`.")
    filas = con.execute(ETAPAS.format(donde=donde), args).fetchall()
    # La caducidad se decide comparando textos, y en SQL no se puede porque el
    # montaje se calcula leyendo la cinta. Se trae lo escrito y se compara aquí.
    # **Y viaja la descripcion aprobada, no solo su fecha.** Jaime: *«lo que ya
    # se aprobo no se vuelve a discutir: se revisa que este como se dijo»*.
    # Trayendo unicamente `sobre_texto` sabiamos que estaba caducada y quien
    # contestaba la escribia **desde cero**, sin ver la que ya habia — asi que
    # dos vueltas seguidas podian describir la misma etapa de dos maneras sin
    # que nada hubiera cambiado salvo el enfoque de quien miraba.
    filas_desc = list(con.execute(
        "select video_slug, etapa_orden, sobre_texto, que_pasa, emocion,"
        # **Y el tablero, que es la mitad cara de la escena.** Se quedo
        # fuera de la primera version de `ya_dicho` y el efecto fue medio
        # arreglo: la descripcion llegaba aprobada y el tablero no, asi
        # que quien describe tenia que volver a inventarlo aunque la
        # escena no hubiera cambiado. Lo dijo el paso al contestar
        # reel-04: cinco etapas tipograficas rehechas por esto.
        " componente, grafico, color, sonido, plano, tablero"
        " from escena_desc"))
    guardado = {(r["video_slug"], r["etapa_orden"]): (r["sobre_texto"] or "")
                for r in filas_desc}
    aprobada = {(r["video_slug"], r["etapa_orden"]): dict(r) for r in filas_desc}
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
        # Lo aprobado y **sobre que texto se aprobo**, para poder comparar.
        ya = aprobada.get((slug, orden))
        if ya:
            d["ya_dicho"] = {k: v for k, v in ya.items()
                             if k not in ("video_slug", "etapa_orden")}
        # La clave de `bordes_sucios` es texto, siempre: viaja por JSON y ahi
        # deja de ser numero. Ver `Montaje.bordes_sucios`.
        d["bordes"] = p.bordes.get(str(orden)) or []
        d["repetido"] = [r for r in p.repetido if r["etapa"] == orden]
        if not rehacer:
            # **Se describe UNA vez.** Jaime, el 1 de septiembre: *«solo
            # hacemos una descripcion y una sola composicion grafica; revisar es
            # despues de eso»*, y *«no se devuelve a hacer un reproceso por lo
            # mismo»*.
            #
            # Esto comparo primero cadenas exactas —una muletilla tiraba la
            # descripcion entera— y luego, mejor, por sentido (`dice_lo_mismo`).
            # Las dos versiones compartian el error de fondo: **volver a pedir**.
            # Describir es criterio estetico, y la IA no es determinista: la
            # segunda descripcion no es mejor que la primera, es otra. Con eso la
            # pieza no cierra nunca.
            #
            # Que el texto se haya movido sigue siendo un dato, y no se pierde:
            # `verificar` lo anota como ticket puntual con su etapa, y lo mira
            # quien revisa la pieza montada. Lo que no hace es rehacer el
            # trabajo. `--rehacer` sigue existiendo para pedirlo a mano.
            if guardado.get((slug, orden)) is not None:
                continue                 # ya descrita: no se vuelve a pedir
        fuera.append(d)
    return fuera
