"""En qué paso está cada escena, y no sólo la pieza (C-752).

Jaime, 17-11-2026: *«haz también los subtítulos y la fase por escena; todo por
escena»*, y *«que no la devuelva al inicio sino al punto que necesita ser
corregido»*.

La pieza seguía siendo la que tenía fase: un tiquet en e2 la devolvía entera, y
cada paso que venía detrás volvía a trabajar las escenas que no estaban
aprobadas todavía aunque ya hubieran pasado por él. Ahora cada escena lleva su
paso (`escena_fase`):
- cuando la pieza **avanza** a un paso, las escenas que estaban por debajo
  suben a él; las que ya iban por delante se quedan donde estaban;
- cuando un tiquet la **devuelve**, baja sólo su escena, al paso que la atiende;
- y un paso sólo trabaja las escenas que todavía no lo han pasado
  (`Alcance.editables`).

La fase de la pieza sigue existiendo y es lo que el motor recorre: es la de su
escena más atrasada.
"""
from __future__ import annotations

import datetime


def _con():
    from .fase import _con as c

    con = c()
    con.execute("CREATE TABLE IF NOT EXISTS escena_fase (video_slug TEXT NOT NULL,"
                " etapa INTEGER NOT NULL, fase TEXT NOT NULL, orden REAL NOT NULL,"
                " cuando TEXT NOT NULL, PRIMARY KEY (video_slug, etapa))")
    return con


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def de(slug) -> dict:
    """`{etapa: (fase, orden)}` de las escenas de la pieza que ya tienen paso."""
    con = _con()
    filas = con.execute("select etapa, fase, orden from escena_fase where video_slug = ?",
                        (slug,)).fetchall()
    con.close()
    return {int(r[0]): (r[1], float(r[2])) for r in filas}


def avanza(slug, etapas, fase, orden) -> None:
    """La pieza llegó a `fase`: sube las escenas que iban por detrás."""
    hay, ahora = de(slug), _ahora()
    con = _con()
    for e in etapas:
        if e not in hay or hay[e][1] < orden:
            con.execute("insert or replace into escena_fase values (?,?,?,?,?)",
                        (slug, int(e), fase, float(orden), ahora))
    con.commit()
    con.close()


def vuelve(slug, etapa, fase, orden) -> None:
    """Un tiquet devuelve **esa** escena al paso que la atiende."""
    con = _con()
    con.execute("insert or replace into escena_fase values (?,?,?,?,?)",
                (slug, int(etapa), fase, float(orden), _ahora()))
    con.commit()
    con.close()


def ya_paso(slug, fase) -> set:
    """Las escenas que ya pasaron por `fase` (su paso está en ella o más allá)."""
    from .fase import camino

    orden = next((f["orden"] for f in camino() if f["nombre"] == fase), None)
    if orden is None:
        return set()
    return {e for e, (_f, o) in de(slug).items() if o >= orden}
