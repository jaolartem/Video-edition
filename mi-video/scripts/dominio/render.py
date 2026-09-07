"""Cuánto tardó un render, y con qué banderas. La puerta de la tabla `render`.

**Por qué existe.** La tabla estaba declarada en `esquema.sql` desde el
principio —`frames`, `segundos`, `config`— y tenía **cero filas**. Así que la
pregunta de Jaime, *«no es lógico que nos demoremos una hora con un vídeo de 50
segundos»*, sólo se podía contestar montando un banco de pruebas a mano: bundle
aparte, rangos de frames, cronómetro. Un día de trabajo para saber algo que la
línea ya sabía y tiraba.

Un número que se pierde al cerrar la terminal se vuelve a medir o, peor, se
supone. Es la misma regla que ya obligó a que `suena.py` escribiera en
`medicion`, aplicada al único paso caro que quedaba sin apuntar.

**Lo que se guarda es la configuración literal**, no un resumen: la concurrencia
y el resto de banderas son lo que se cambia cuando se busca velocidad, así que
sin ellas la fila dice cuánto tardó y no de qué dependía.

    python scripts/dominio/render.py reel-01 212.4 2974 1080 1920 "gl=angle c=8"
    python scripts/dominio/render.py --ver        # los últimos, con su ritmo
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

#: Para qué se hizo ese render. Lo fija el `CHECK` de la tabla.
PROPOSITOS = ("entrega", "revision", "banco")


def _con():
    c = basedatos.abrir()
    c.row_factory = sqlite3.Row
    return c


def apuntar(slug, segundos, frames, ancho, alto, config,
            proposito="entrega", nota=None):
    """Apunta un render. Devuelve el `id` de la fila, o `None` sin pieza.

    **No falla si la pieza no está en la base.** Esto es telemetría: que un
    render de prueba sobre una pieza sin registrar tumbe el montaje sería
    cambiar el precio de medir, y entonces se deja de medir.
    """
    if proposito not in PROPOSITOS:
        raise ValueError(f"proposito «{proposito}»: sólo {PROPOSITOS}")
    con = _con()
    # **Si la tabla no está, se dice y se sigue.** El esquema es código y lo pone
    # `modelo.py`; repetir aquí el `CREATE TABLE` sería la segunda copia de una
    # decisión que ya vive en `esquema.sql`, que es justo la avería que este
    # proyecto persigue. Una base sin migrar no puede costar un render.
    try:
        v = con.execute("select id from video where slug = ?",
                        (slug,)).fetchone()
        if not v:
            return None
        cur = con.execute(
            "insert into render (video_id, proposito, ancho, alto, frames,"
            " segundos, config, nota) values (?,?,?,?,?,?,?,?)",
            (v["id"], proposito, int(ancho), int(alto),
             int(frames) if frames else None, float(segundos), str(config),
             nota))
        con.commit()
    except sqlite3.OperationalError as e:
        print(f"render sin apuntar ({e}). Corre: python scripts/modelo.py")
        return None
    return cur.lastrowid


def ultimos(cuantos=12):
    """Los últimos renders, del más nuevo al más viejo."""
    con = _con()
    try:
        return [dict(r) for r in con.execute(
            "select r.*, v.slug from render r join video v on v.id = r.video_id"
            " order by r.fecha desc, r.id desc limit ?", (cuantos,))]
    except sqlite3.OperationalError:
        return []


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("slug", nargs="?")
    p.add_argument("segundos", nargs="?", type=float)
    p.add_argument("frames", nargs="?", type=int)
    p.add_argument("ancho", nargs="?", type=int)
    p.add_argument("alto", nargs="?", type=int)
    p.add_argument("config", nargs="?", default="")
    p.add_argument("--proposito", default="entrega", choices=PROPOSITOS)
    p.add_argument("--nota", default=None)
    p.add_argument("--ver", action="store_true", help="los últimos renders")
    a = p.parse_args()

    if a.ver or not a.slug:
        filas = ultimos()
        if not filas:
            print("render: ninguna corrida apuntada todavía.")
            return
        print(f"{'pieza':<9} {'fecha':<20} {'seg':>7} {'frames':>7} "
              f"{'fps':>5}  config")
        for r in filas:
            fps = (r["frames"] / r["segundos"]) if r["frames"] and r["segundos"] else 0
            print(f"{r['slug']:<9} {r['fecha']:<20} {r['segundos']:>7.1f} "
                  f"{r['frames'] or 0:>7} {fps:>5.1f}  {r['config']}")
        return

    i = apuntar(a.slug, a.segundos, a.frames, a.ancho, a.alto, a.config,
                a.proposito, a.nota)
    print(f"render #{i} apuntado" if i else
          f"render no apuntado: {a.slug} no está en la base")


if __name__ == "__main__":
    main()
