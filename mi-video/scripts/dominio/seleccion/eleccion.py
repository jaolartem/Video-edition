"""La decisión, escrita en el modelo. No en una tabla plana.

Sustituye a `propuesta`, que guardaba `desde`, `hasta` y `texto` dentro de la
fila de la elección: el fragmento no existía como cosa, era un atributo de la
decisión. Jaime: *«no creo que esté al tercer grado si cada uno de estos
elementos no tiene su propia instancia»*, y *«el punto es dejar de depender de
tu memoria y construir un modelo coherente»*.

Aquí cada cosa va a su sitio y una sola vez: el párrafo a `libreto`, el trozo de
cinta a `fragmento`, las unidades que abarca a `fragmento_unidad`, y la decisión
—sólo la decisión— a `eleccion`.
"""
from __future__ import annotations

import datetime
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import basedatos  # noqa: E402
import registro  # noqa: E402

#: Dónde vive la base. La declara `basedatos`, que es su dueño; aquí sólo se
#: usa. Estaba escrita a mano —`os.path.join("ads", "decisiones.db")`— y ésa es
#: la avería de siempre en pequeño: dos sitios diciendo dónde está una cosa.
BASE = basedatos.BASE


def guardar(slug: str, toma: str, plan, ventanas, libreto,
            marcas=None, finalistas: int = 5) -> int:
    """Deja el reparto en el modelo. Devuelve cuántas elecciones llevan fragmento."""
    con = basedatos.abrir(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(io.open("scripts/esquema.sql", encoding="utf-8").read())

    vid = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not vid:
        registro.error("seleccionar", "el video no esta en la base",
                       detalle=f"{slug}: corre python scripts/db.py migrar")
        con.close()
        return 0
    video_id = vid[0]

    # El libreto: la intención comunicativa, una fila por etapa.
    for i, parr in enumerate(libreto):
        con.execute("insert into libreto (video_id, orden, texto) values (?,?,?)"
                    " on conflict(video_id, orden) do update set"
                    " texto = excluded.texto", (video_id, i + 1, parr))

    etapas = dict(con.execute(
        "select orden, id from etapa where video_id = ?", (video_id,)).fetchall())
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    puestos = _elecciones(con, etapas, plan, ventanas, toma, ahora)
    if marcas:
        _candidatas(con, video_id, etapas, plan, ventanas, marcas, toma, finalistas)

    # `propuesta` era el atajo denormalizado. Se va: dos sitios diciendo lo
    # mismo es de donde salen los fallos de este proyecto.
    con.execute("drop table if exists propuesta")
    con.commit()
    con.close()
    return puestos


def _fragmento(con, v, toma: str, origen: str, declara_toma: bool = False):
    """El trozo de cinta como cosa, con su cinta. Devuelve `(toma_id, id)`.

    La elegida **declara su cinta** si no estaba: es la que se va a montar. Una
    candidata que viene de una cinta que la base no conoce se salta — apuntarla
    inventaría una grabación por una que ni siquiera ganó.
    """
    t_v = v.toma or toma
    ft = con.execute("select id from toma where nombre = ?", (t_v,)).fetchone()
    if ft is None:
        if not declara_toma:
            return None, None
        ft = (con.execute("insert into toma (nombre) values (?)",
                          (t_v,)).lastrowid,)
    con.execute("insert or ignore into fragmento (toma_id, desde, hasta, origen)"
                " values (?,?,?,?)", (ft[0], v.a, v.b, origen))
    fid = con.execute("select id from fragmento where toma_id=? and desde=?"
                      " and hasta=?", (ft[0], v.a, v.b)).fetchone()[0]
    return ft[0], fid


def _elecciones(con, etapas, plan, ventanas, toma, ahora) -> int:
    puestos = 0
    for s0, k in enumerate(plan):
        eid = etapas.get(s0 + 1)
        if eid is None:
            continue
        if k is None:
            con.execute("insert into eleccion (etapa_id, fragmento_id, quien,"
                        " fecha) values (?,NULL,?,?) on conflict(etapa_id) do"
                        " update set fragmento_id = NULL, quien = excluded.quien,"
                        " fecha = excluded.fecha", (eid, "seleccionar", ahora))
            continue
        v = ventanas[k]
        ft, fid = _fragmento(con, v, toma, v.de_jaime or "reparto",
                             declara_toma=True)
        # Las unidades que abarca: el texto vive ahí, no aquí.
        con.execute("delete from fragmento_unidad where fragmento_id = ?", (fid,))
        con.executemany(
            "insert or ignore into fragmento_unidad (fragmento_id, unidad_id)"
            " values (?,?)",
            [(fid, r[0]) for r in con.execute(
                "select id from unidad where toma_id=? and hasta>? and desde<?",
                (ft, v.a, v.b))])
        cubre, dice = v.det.get(s0, (None, 0))
        con.execute("insert into eleccion (etapa_id, fragmento_id, cubre, dice,"
                    " quien, fecha) values (?,?,?,?,?,?) on conflict(etapa_id)"
                    " do update set fragmento_id=excluded.fragmento_id,"
                    " cubre=excluded.cubre, dice=excluded.dice,"
                    " quien=excluded.quien, fecha=excluded.fecha",
                    (eid, fid, cubre, int(dice),
                     "jaime" if v.de_jaime else "seleccionar", ahora))
        puestos += 1
    return puestos


def _candidatas(con, video_id, etapas, plan, ventanas, marcas, toma, finalistas):
    """**Las OTRAS tomas de cada etapa.**

    La relación no es 1:1: Jaime graba varias veces lo mismo y por eso se escoge
    la mejor. Sin guardarlas, decir «ésta no sirve, usa la siguiente» obliga a
    repetir la selección entera y a confiar en que dé lo mismo; y además no se ve
    **por qué** ganó una, porque una puntuación sin las otras al lado es un
    número suelto.
    """
    con.execute("delete from candidato where etapa_id in"
                " (select id from etapa where video_id = ?)", (video_id,))
    for s0, eid in etapas.items():
        fila = marcas[s0 - 1] if s0 - 1 < len(marcas) else None
        if not fila:
            continue
        top = sorted((k for k in range(len(fila)) if fila[k] is not None),
                     key=lambda k: -fila[k])[:finalistas]
        elegido = plan[s0 - 1] if s0 - 1 < len(plan) else None
        # La elegida va la primera aunque el recorte le haya bajado la nota:
        # `puesto` es el orden en que quedaron, no una nota.
        orden = (([elegido] if elegido is not None else [])
                 + [k for k in top if k != elegido])
        for puesto, k in enumerate(orden, 1):
            v = ventanas[k]
            _ft, fid = _fragmento(con, v, toma, "candidata")
            if fid is None:
                continue
            cu, di = v.det.get(s0 - 1, (None, 0))
            # `ventanas` crece con las que añade `manda_jaime`, así que un índice
            # puede caer fuera de `marcas`: ésas no tienen puntuación porque no
            # compitieron — las puso Jaime.
            pun = (round(fila[k], 4)
                   if k < len(fila) and fila[k] is not None else None)
            con.execute(
                "insert into candidato (etapa_id, fragmento_id, puesto,"
                " puntuacion, cubre, dice, voz_st, descartada_por)"
                " values (?,?,?,?,?,?,?,?)"
                " on conflict(etapa_id, fragmento_id) do update set"
                " puesto=excluded.puesto, puntuacion=excluded.puntuacion,"
                " cubre=excluded.cubre, dice=excluded.dice,"
                " voz_st=coalesce(excluded.voz_st, candidato.voz_st)",
                (eid, fid, puesto, pun, cu, int(di), v.voz_st,
                 None if pun is not None else "elegida por Jaime"))
