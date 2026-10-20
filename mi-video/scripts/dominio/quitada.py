"""**Una etapa opcional que sale de la pieza, declarada.** C-609.

Jaime, 19-10, sobre reel-18: *«quita la firma de e9 y que el nombre vaya sobre
el final de e8»*. El compositor la cortó (`remedio: cortar`), el diseñador la
retiró, y e9 siguió sonando en el render: su tramo estaba en `corte_fijo`,
`fijar --aplicar` lo volvía a poner, y no había forma de decir «esta etapa no
va». Una decisión que la máquina no sabe guardar se pierde en cada vuelta.

Sólo sale una etapa **opcional**. Una obligatoria sin material sube a Jaime
(CLAUDE.md), no se quita por declaración.

    python scripts/dominio/quitada.py reel-18 9 "Jaime, 19-10 (#779): ..."
"""
from __future__ import annotations

import datetime
import json
import os
import sys

TABLA = "etapa_quitada"


def _con():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if raiz not in sys.path:
        sys.path.insert(0, raiz)
    import basedatos

    cx = basedatos.abrir()
    crea(cx)
    return cx


def crea(cx) -> bool:
    """La tabla. La crea quien abre, como `memoria`."""
    cx.execute(f"""
      CREATE TABLE IF NOT EXISTS {TABLA} (
        video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
        etapa    INTEGER NOT NULL,
        por_que  TEXT NOT NULL,
        quien    TEXT,
        cuando   TEXT NOT NULL,
        PRIMARY KEY (video_id, etapa)
      )""")
    return True


def declarar(slug, etapa, por_que, quien="servicio"):
    """La deja fuera y borra su tramo declarado. Devuelve el error, o `None`.

    El tramo se borra porque las dos declaraciones dicen lo contrario: una que
    la etapa suena ahí, la otra que no suena. Si se quedaran las dos, ganaría
    la que se aplica después.
    """
    if not (por_que or "").strip():
        return "una etapa no se quita sin decir por qué"
    cx = _con()
    v = cx.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        return f"{slug}: no está en la base"
    ob = cx.execute("select obligatorio from etapa where video_id = ? and orden = ?",
                    (v[0], int(etapa))).fetchone()
    if ob and ob[0]:
        return f"{slug} e{etapa} es obligatoria: sin material sube a Jaime"
    cx.execute("delete from corte_fijo where video_id = ? and papel = 'etapa'"
               " and orden = ?", (v[0], int(etapa)))
    cx.execute(f"insert or replace into {TABLA} values (?,?,?,?,?)",
               (v[0], int(etapa), por_que, quien,
                datetime.datetime.now().isoformat(timespec="seconds")))
    cx.commit()
    return None


def de(slug) -> dict:
    """`{etapa: por_que}` de las que salen de esa pieza."""
    cx = _con()
    return {int(e): p for e, p in cx.execute(
        f"select q.etapa, q.por_que from {TABLA} q join video v on v.id = q.video_id"
        " where v.slug = ?", (slug,))}


def aplicar(slug) -> list:
    """Las saca del EDL. Escribe sólo si había algo que sacar."""
    fuera = de(slug)
    ruta = f"ads/{slug}/edl-sell.json"
    if not fuera or not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    det = edl.get("detalle") or []
    if any(d.get("beat") in fuera and d.get("obligatorio") for d in det):
        raise SystemExit(f"{slug}: una etapa quitada figura como obligatoria"
                         " en el EDL — sube a Jaime")
    quedan = [i for i, d in enumerate(det) if d.get("beat") not in fuera]
    if len(quedan) == len(det):
        return []
    sale = sorted({d.get("beat") for d in det} & set(fuera))
    for k in ("segmentos", "fuentes", "detalle"):
        if isinstance(edl.get(k), list) and len(edl[k]) == len(det):
            edl[k] = [edl[k][i] for i in quedan]
    nuevo = {viejo: n for n, viejo in enumerate(quedan)}
    edl["costuras_duras"] = [nuevo[i] for i in edl.get("costuras_duras") or []
                             if i in nuevo]
    edl["sin_toma"] = [h for h in edl.get("sin_toma") or []
                       if h.get("beat") not in fuera]
    edl["duracion_s"] = edl["duracion_montada_s"] = round(
        sum(b - a for a, b in edl["segmentos"]), 2)
    json.dump(edl, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return sale


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("uso: quitada.py <pieza> <etapa> <por qué>")
    err = declarar(sys.argv[1], int(sys.argv[2]), sys.argv[3], quien="Jaime")
    print(f"{sys.argv[1]} e{sys.argv[2]}: "
          + (err or "quitada; sale del EDL en `fijar --aplicar`"))
