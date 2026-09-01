"""Lo que Jaime observa de UNA pieza, con su segundo y su respuesta.

**Por qué es distinto de `instruccion.py`.** Aquello guarda criterios que valen
para todo el lote —«C: no se toca», «máximo 300 líneas»—. Esto guarda lo otro,
que él precisó así: *«mis consideraciones con cada video… como el vídeo X tiene
problemas en el segundo Y y no me gusta X; una línea de tickets y de respuestas a
objeciones»*.

Son dos cosas de naturaleza distinta y por eso no comparten tabla: un criterio se
cumple siempre; una objeción se contesta una vez, sobre una pieza y casi siempre
sobre un instante concreto.

## El segundo es el dato que lo hace utilizable

*«En el segundo 30 el tablero se queda sin sonido»* no se puede atender sin saber
qué etapa cae en el segundo 30. Por eso el ticket guarda `segundo` y sabe
traducirlo a beat con el EDL de la pieza: así el paso que decide recibe **la
objeción colocada en su etapa**, no una frase suelta que alguien tendría que
volver a situar.

Y guarda el segundo **de la pieza montada**, no de la cinta: es lo que Jaime ve
cuando mira el vídeo, y traducirlo es trabajo de la máquina, no suyo.

## Una objeción sin respuesta es una objeción perdida

El estado por defecto es `abierto`, y `contestar()` exige texto. Un ticket que se
cierra sin decir qué se hizo deja a Jaime sin saber si se atendió o se ignoró —
que es exactamente lo que pasa hoy cuando una observación vive sólo en el chat.

**Y `descartado` es una respuesta legítima**, con su porqué: «no se puede, la toma
no existe» es información. Lo que no vale es que desaparezca.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ticket (
  id        INTEGER PRIMARY KEY,
  cuando    TEXT NOT NULL,
  pieza     TEXT NOT NULL,
  segundo   REAL,                    -- en la pieza montada, no en la cinta
  beat      INTEGER,                 -- se deriva del segundo, si se puede
  dijo      TEXT NOT NULL,           -- sus palabras, sin resumir
  tipo      TEXT NOT NULL DEFAULT 'objecion'
            CHECK (tipo IN ('objecion','falta','sobra','suena','dato','gusto')),
  estado    TEXT NOT NULL DEFAULT 'abierto'
            CHECK (estado IN ('abierto','contestado','arreglado','descartado')),
  respuesta TEXT,
  quien     TEXT,
  cerrado   TEXT
)
"""


def _con():
    cx = basedatos.abrir()
    cx.row_factory = sqlite3.Row
    basedatos.esquema(cx, ESQUEMA)
    return cx


def beat_en(pieza, segundo):
    """Qué etapa cae en ese segundo de la pieza montada.

    Se recorre el EDL sumando duraciones: el segundo que Jaime ve es tiempo de
    montaje, no de cinta. Devuelve `None` si no hay EDL o el segundo se sale —
    y `None` es honesto: colocarlo a ojo sería peor que no colocarlo.
    """
    if segundo is None:
        return None
    ruta = os.path.join("ads", pieza, "edl-sell.json")
    if not os.path.exists(ruta):
        return None
    try:
        edl = json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return None
    t = 0.0
    for (a, b), det in zip(edl.get("segmentos", []), edl.get("detalle", [])):
        dur = float(b) - float(a)
        if t <= segundo < t + dur:
            return det.get("beat")
        t += dur
    return None


def abrir(pieza, dijo, segundo=None, tipo="objecion"):
    """Apunta una observación suya. Devuelve el id, para poder contestarla."""
    cx = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    cur = cx.execute(
        "insert into ticket (cuando, pieza, segundo, beat, dijo, tipo)"
        " values (?,?,?,?,?,?)",
        (ahora, pieza, segundo, beat_en(pieza, segundo), dijo, tipo))
    cx.commit()
    return cur.lastrowid


def contestar(id_, respuesta, estado="contestado", quien="la linea"):
    """Cierra un ticket **diciendo qué se hizo**. Sin texto no se cierra."""
    if not (respuesta or "").strip():
        raise ValueError("un ticket no se cierra sin decir que se hizo")
    cx = _con()
    cx.execute("update ticket set respuesta = ?, estado = ?, quien = ?,"
               " cerrado = ? where id = ?",
               (respuesta, estado, quien,
                datetime.datetime.now().isoformat(timespec="seconds"), id_))
    cx.commit()


def abiertos(pieza=None):
    """Los que siguen sin contestar, ya colocados en su etapa."""
    cx = _con()
    if pieza:
        filas = cx.execute(
            "select * from ticket where estado = 'abierto' and pieza = ?"
            " order by segundo, id", (pieza,)).fetchall()
    else:
        filas = cx.execute(
            "select * from ticket where estado = 'abierto'"
            " order by pieza, segundo, id").fetchall()
    cx.close()
    return [dict(f) for f in filas]


def recolocar(pieza):
    """Vuelve a traducir el segundo a etapa. **El corte cambia; el segundo no.**

    Un ticket apunta al segundo 30 de lo que Jaime vio. Si la pieza se recorta,
    ese segundo cae en otra etapa — y atender la objeción en la etapa equivocada
    es peor que no atenderla. Se recoloca en cada corrida.
    """
    cx = _con()
    n = 0
    for f in cx.execute("select id, segundo from ticket where pieza = ?"
                        " and estado = 'abierto'", (pieza,)).fetchall():
        b = beat_en(pieza, f["segundo"])
        cx.execute("update ticket set beat = ? where id = ?", (b, f["id"]))
        n += 1
    cx.commit()
    return n


def historia(pieza):
    """Todo lo que ha dicho de esa pieza, contestado o no."""
    cx = _con()
    filas = [dict(f) for f in cx.execute(
        "select * from ticket where pieza = ? order by id", (pieza,))]
    cx.close()
    return filas


def _texto(t):
    """Una línea legible, con el segundo y la etapa donde cae hoy."""
    donde = ""
    if t.get("segundo") is not None:
        donde = f" s={t['segundo']:.0f}"
        donde += f" (b{t['beat']})" if t.get("beat") is not None else " (sin etapa)"
    marca = {"abierto": "·", "contestado": ">", "arreglado": "+",
             "descartado": "-"}.get(t["estado"], "?")
    linea = f"  {marca} #{t['id']:<3} {t['pieza']}{donde}  {t['dijo']}"
    if t.get("respuesta"):
        linea += f"\n        -> {t['respuesta']}"
    return linea


def main():
    """Para que Jaime abra y cierre tickets sin pasar por nadie.

        python scripts/dominio/ticket.py reel-03 30 "el tablero no suena"
        python scripts/dominio/ticket.py --ver reel-03
        python scripts/dominio/ticket.py --cerrar 4 "movido el borde a 31,2"
    """
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", nargs="?")
    ap.add_argument("segundo", nargs="?")
    ap.add_argument("dijo", nargs="?")
    ap.add_argument("--tipo", default="objecion")
    ap.add_argument("--ver", metavar="PIEZA", nargs="?", const="", default=None)
    ap.add_argument("--cerrar", nargs=2, metavar=("ID", "RESPUESTA"))
    ap.add_argument("--estado", default="arreglado")
    a = ap.parse_args()

    if a.cerrar:
        contestar(int(a.cerrar[0]), a.cerrar[1], estado=a.estado, quien="Jaime")
        print(f"ticket #{a.cerrar[0]}: {a.estado}")
        return
    if a.ver is not None:
        filas = historia(a.ver) if a.ver else abiertos()
        if not filas:
            print("sin tickets")
            return
        for t in filas:
            print(_texto(t))
        return
    if not (a.pieza and a.dijo):
        # **El segundo es opcional, el texto no.** Un ticket sin sus palabras no
        # es un ticket: es una marca que nadie sabe atender.
        ap.error("hace falta la pieza y lo que dice; el segundo es opcional")
    seg = float(str(a.segundo).replace(",", ".")) if a.segundo else None
    i = abrir(a.pieza, a.dijo, seg, a.tipo)
    t = [x for x in historia(a.pieza) if x["id"] == i][0]
    print("apuntado:")
    print(_texto(t))


if __name__ == "__main__":
    main()
