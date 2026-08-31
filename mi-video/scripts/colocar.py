"""El registro de renderizado: qué pieza va dónde, y de dónde sale.

Idea de Jaime: *«la tabla de renderizado tiene id de vídeo de entrada, id de
vídeo de salida (renderizado fragmento), id segmento de entrada, id segmento
esperado por libreto, posición en el vídeo de salida; las transiciones ocupan
una columna y lo que tenemos es un registro de renderizado»*.

Hasta ahora la línea de tiempo vivía en dos ficheros —`edl-sell.json` y
`plan-full.json`— que se derivan uno del otro y se separan en cuanto uno cambia.
Aquí queda en una tabla de conexiones, y con ella dos cosas que antes no se
podían:

- **Decir qué hay que rehacer.** La huella resume todo lo que decide cómo se ve
  una pieza; si no cambió, esa pieza no se vuelve a renderizar. Es el peldaño
  caro tocando sólo lo que cambió.
- **Corregir una pieza sin mover las demás**, que es la «semi aplicación» que
  Jaime pidió y que hasta ahora dependía de que nadie tocara el resto.

    python scripts/colocar.py 1 2 3     # vuelca el plan de esos reels
    python scripts/colocar.py --ver 1   # la tabla de conexiones del reel 1
"""
import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rutas  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")


def huella(e, fragmento_id, transicion):
    """Todo lo que decide cómo se ve esta pieza, resumido.

    Si cambia el trozo de cinta, el encuadre, el acercamiento o la transición
    que la abre, la huella cambia y hay que rehacerla. Si no, no.
    """
    crudo = json.dumps({
        "f": fragmento_id,
        "a": round(e.get("origen_desde", 0), 3),
        "b": round(e.get("origen_hasta", 0), 3),
        "crop": e.get("crop"),
        "zoom": (e.get("zoom") or {}).get("hasta"),
        "t": transicion,
    }, sort_keys=True)
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


def volcar(con, slug):
    plan_p = f"work/scenes/{slug}/plan-full.json"
    edl_p = os.path.join("ads", slug, "edl-sell.json")
    if not (os.path.exists(plan_p) and os.path.exists(edl_p)):
        return 0
    plan = json.load(open(plan_p, encoding="utf-8"))
    edl = json.load(open(edl_p, encoding="utf-8"))

    fila = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not fila:
        return 0
    video_id = fila[0]
    etapas = dict(con.execute(
        "select orden, id from etapa where video_id = ?", (video_id,)).fetchall())
    trans = dict(con.execute("select nombre, id from transicion").fetchall())

    # El fragmento del que nace cada escena: por su rango dentro de la toma.
    # **El fragmento se busca DENTRO de su cinta.** Sin filtrar por toma, la
    # busqueda por rango encontraba un fragmento de otra grabacion que caia en
    # los mismos segundos: la escena 11 del reel 3 salia atribuida a la cinta
    # del reel 2. El tiempo no identifica nada por si solo — hay seis cintas y
    # todas empiezan en cero.
    tomas_del_video = [r[0] for r in con.execute(
        "select distinct f.toma_id from eleccion el"
        " join etapa e on e.id = el.etapa_id"
        " join fragmento f on f.id = el.fragmento_id"
        " where e.video_id = ?", (video_id,))] or [
        con.execute("select toma_id from video where id = ?",
                    (video_id,)).fetchone()[0]]
    marcas = ",".join("?" * len(tomas_del_video))

    def frag_de(e):
        r = con.execute(
            "select f.id from fragmento f"
            f" where f.toma_id in ({marcas})"
            " and f.desde <= ? + 0.05 and f.hasta >= ? - 0.05"
            " order by f.hasta - f.desde limit 1",
            (*tomas_del_video, e.get("origen_desde", 0),
             e.get("origen_hasta", 0))).fetchone()
        return r[0] if r else None

    con.execute("delete from empalme where video_id = ?", (video_id,))
    con.execute("delete from colocacion where video_id = ?", (video_id,))
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    n, previo = 0, None
    for i, e in enumerate(plan.get("escenas", [])):
        fid = frag_de(e)
        # `modo` del plan: la primera escena de un corte entra con corte; las
        # que siguen encadenan dentro del mismo fragmento.
        t = "corte" if e.get("modo") == "cut" else "encadenado"
        if i == 0:
            t = "ninguna"
        cur = con.execute(
            "insert into colocacion (video_id, orden, desde_s, dura_s,"
            " fragmento_id, etapa_id, tipo, huella, fecha)"
            " values (?,?,?,?,?,?,?,?,?)",
            (video_id, i, round(e.get("montado_desde", 0), 3),
             round(e.get("duracion", 0), 3), fid,
             etapas.get(e.get("beat")), "toma", huella(e, fid, t), ahora))
        # El empalme es lo que pasa ENTRE dos piezas, asi que va aparte y con su
        # duracion: 5 frames el glitch, 0,7 s la cortinilla, 0 el corte seco.
        DURA = {"glitch": 5 / 30, "cortinilla": 0.7, "encadenado": 0.05}
        con.execute(
            "insert into empalme (video_id, antes_id, despues_id,"
            " transicion_id, dura_s) values (?,?,?,?,?)",
            (video_id, previo, cur.lastrowid, trans.get(t), DURA.get(t, 0.0)))
        previo = cur.lastrowid
        n += 1
    # Lo que el libreto espera y no salio de la cinta ocupa su sitio igual.
    for h in edl.get("sin_toma", []):
        con.execute(
            "insert into colocacion (video_id, orden, desde_s, dura_s,"
            " fragmento_id, etapa_id, tipo, huella, fecha)"
            " values (?,?,?,?,NULL,?,?,?,?)",
            (video_id, 1000 + h["beat"], 0.0, 0.0,
             etapas.get(h["beat"]), "tarjeta",
             f"sin-toma-{h['beat']}", ahora))
        n += 1
    return n


def ver(con, slug):
    q = """
      select c.orden, c.desde_s, c.dura_s, c.tipo,
             tr.nombre || (case when em.dura_s > 0
                                then ' ' || printf('%.2f', em.dura_s) || 's'
                                else '' end),
             t.nombre, f.desde, f.hasta, e.orden, ec.nombre, c.huella
      from colocacion c
      join video v on v.id = c.video_id
      left join empalme em on em.despues_id = c.id
      left join transicion tr on tr.id = em.transicion_id
      left join fragmento f on f.id = c.fragmento_id
      left join toma t on t.id = f.toma_id
      left join etapa e on e.id = c.etapa_id
      left join etapa_canonica ec
             on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
      where v.slug = ? order by c.orden
    """
    print(f"{slug}")
    print(f"  {'#':>3} {'sale en':>8} {'dura':>6}  {'entra con':<11}"
          f" {'cinta de entrada':<17} {'segmento entrada':<15}"
          f" {'etapa del libreto':<26} huella")
    for (o, d, du, tipo, tr, toma, fa, fb, eo, en, h) in con.execute(q, (slug,)):
        seg = f"{fa:.1f}-{fb:.1f}" if fa is not None else "—"
        print(f"  {o:>3} {d:>8.2f} {du:>6.2f}  {(tr or '—'):<11}"
              f" {(toma or '—'):<17} {seg:<15}"
              f" {(f'{eo}. ' + (en or '')) if eo else '—':<26} {h}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", type=int)
    a = ap.parse_args()
    con = sqlite3.connect(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    if a.ver:
        ver(con, f"reel-{a.ver:02d}")
    else:
        for n in (a.reels or rutas.piezas()):
            slug = f"reel-{n:02d}"
            print(f"{slug}: {volcar(con, slug)} colocaciones")
        con.commit()
    con.close()


if __name__ == "__main__":
    main()
