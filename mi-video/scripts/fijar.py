"""Fija el tramo de una etapa: la decisión declarada gana sobre la automática.

Este paso faltaba, y era el que dejaba el resto en el aire. La composición sabe
decir *«esta etapa no entrega su mensaje y la toma buena está en la cinta, en el
segundo 516»* — y hasta ahora **no había forma de aplicarlo por la línea**:
`corte_fijo` sólo admitía `apertura` y `cierre`, y ningún script lo leía. Sin
esto, ejecutar esa decisión era editar el EDL a mano, que es exactamente por
donde el proyecto pierde el estado.

## Qué es un tramo fijado

Una **decisión declarada** sobre una etapa: este trozo de esta cinta, y no el que
elija la selección. Se guarda en `corte_fijo` con `papel='etapa'` y el número de
beat en `orden`, así que:

- **queda registrada** —quién, cuándo y por qué—, que es la diferencia entre una
  decisión y un apaño;
- **sobrevive a rehacer la selección**, porque se vuelve a aplicar sobre el EDL
  nuevo en vez de perderse;
- **se puede comprobar**: la puerta mira que cada fijado esté de verdad en el
  EDL, así que un fijado que no llegó al corte no pasa desapercibido.

## Y no se fija a ciegas: se mide

Jaime: *«la IA debe tener una función que re-evalúe el segmento montado por la
IA, luego compare las marcas con las de los demás»*. Así que antes de fijar nada
se mide el tramo propuesto con la misma vara que las candidatas
—`revalidar.evaluar`— y se dice si gana, empata o pierde. Fijar un tramo peor que
el que había es cambiar por cambiar.

    python scripts/fijar.py --ver 1                       # los fijados del reel 1
    python scripts/fijar.py 1 6 20260825_135637 517 529.2 --por-que "..."
    python scripts/fijar.py --aplicar 1                   # los mete en el EDL
"""
import argparse
import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "ads/decisiones.db"


def _con():
    c = sqlite3.connect(BASE)
    c.row_factory = sqlite3.Row
    return c


def _vid(con, slug):
    r = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not r:
        raise SystemExit(f"{slug}: no está en la base")
    return r["id"]


def fijados(slug):
    """Los tramos declarados de una pieza, por beat."""
    con = _con()
    filas = con.execute(
        "select cf.id, cf.orden beat, cf.desde, cf.hasta, cf.toma, cf.por_que"
        "  from corte_fijo cf join video v on v.id = cf.video_id"
        " where v.slug = ? and cf.papel = 'etapa' order by cf.orden, cf.desde",
        (slug,)).fetchall()
    con.close()
    return [dict(f) for f in filas]


def fijar(slug, beat, toma, desde, hasta, por_que="", quien="servicio"):
    """Declara el tramo de una etapa. Devuelve lo que dice la medida."""
    import revalidar

    veredicto = revalidar.evaluar(slug, int(beat), [(float(desde), float(hasta))],
                                  toma=toma)
    con = _con()
    con.execute(
        "insert into corte_fijo (video_id, papel, orden, desde, hasta, toma,"
        " por_que, quien, fecha) values (?,'etapa',?,?,?,?,?,?,?)"
        " on conflict(video_id, papel, orden, desde) do update set"
        " hasta=excluded.hasta, toma=excluded.toma,"
        " por_que=excluded.por_que, quien=excluded.quien, fecha=excluded.fecha",
        (_vid(con, slug), int(beat), float(desde), float(hasta), toma, por_que,
         quien, datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    return veredicto


def aplicar(slug):
    """Mete los tramos fijados en el EDL, sustituyendo los de esa etapa.

    **Se rehace el detalle de la etapa entera**, no se añade un trozo: un fijado
    dice cuál es el tramo de esa etapa, así que los que hubiera se van. Lo demás
    del EDL —las otras etapas, la oferta, la estructura— no se toca.
    """
    import transcribir

    fjs = fijados(slug)
    if not fjs:
        return 0, []
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        raise SystemExit(f"{slug}: no hay EDL que tocar")
    edl = json.load(open(ruta, encoding="utf-8"))
    por_beat = {}
    for f in fjs:
        por_beat.setdefault(f["beat"], []).append(f)
    for v in por_beat.values():
        v.sort(key=lambda x: x["desde"])
    # **Un fijado ya aplicado no se vuelve a aplicar.** `aplicar` rehace la etapa
    # entera, asi que corriendolo dos veces borraba lo que hubiera pasado por
    # encima despues —los recortes de redundancia, sobre todo— y la pieza se
    # volvia a alargar sola. Se comprueba por contenido: si lo que hay en el EDL
    # ya cae dentro de lo declarado, esa etapa esta hecha y no se toca.
    #
    # **Y «cae dentro» no es «se aplico».** Esto preguntaba si los trozos que hay
    # caben dentro de lo declarado, y con eso una etapa recortada por otro paso
    # parecia hecha: reel-01 e2 esta declarada en dos tramos —16,2 s y 11 s— y
    # tenia un solo trozo de 6,2 s dentro del primero. La comprobacion dijo «ya
    # esta», el segundo tramo no se puso nunca, y la etapa perdio la mitad que
    # la convierte en hueco de conocimiento: «los que usan esa estructura
    # terminan ganando mucho mas vendiendo exactamente lo mismo».
    #
    # La marca `fijado` es la señal honesta, porque la pone este paso al aplicar.
    # La aritmetica solo sabe que un trozo cabe; la marca sabe quien lo puso.
    #
    # **Y la marca dice de QUE declaracion viene, no solo que hubo una.**
    # Con un `True` a secas la etapa quedaba cerrada para siempre: la segunda
    # valoracion declaraba un tramo nuevo para el reel-01 e4 —343,16 a 366,65,
    # para dejar de cortar dentro de «Usted» y de «eso»— y `aplicar` lo saltaba
    # porque la etapa «ya estaba fijada». La decision se guardaba en
    # `corte_fijo` y no llegaba al montaje, que es el mismo fallo de C-93 por la
    # puerta de al lado.
    #
    # Con el id se distinguen los dos casos que hay que distinguir: si en el EDL
    # estan todas las declaraciones de hoy, la etapa esta hecha —y lo que otro
    # paso haya recortado por dentro se respeta—; si falta una, es nueva y entra.
    ya = set()
    for b_, fs in por_beat.items():
        suyos = [d for d in edl["detalle"] if d.get("beat") == b_]
        puestas = {d.get("fijado") for d in suyos}
        if suyos and {f["id"] for f in fs} <= puestas:
            ya.add(b_)
    for b_ in ya:
        por_beat.pop(b_, None)
    if not por_beat:
        return 0, []

    segs, det, hechos = [], [], []
    puestos = set()
    for rango, d in zip(edl["segmentos"], edl["detalle"]):
        b = d.get("beat")
        if b not in por_beat:
            segs.append(rango)
            det.append(d)
            continue
        if b in puestos:
            continue                       # el resto de trozos de esa etapa se van
        for f in por_beat[b]:
            toma = f["toma"] or d.get("toma")
            try:
                pal = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                pal = []
            texto = " ".join(w["text"] for w in pal
                             if transcribir.suena(w, f["desde"], f["hasta"]))
            segs.append([round(f["desde"], 3), round(f["hasta"], 3)])
            det.append({**d, "toma": toma, "texto": texto,
                        "fijado": f["id"], "por_que": f["por_que"]})
        puestos.add(b)
        hechos.append(b)
    # Las etapas fijadas que no estaban en el EDL —las que se habían quedado sin
    # material— entran ahora: es justo para lo que sirve fijar.
    for b, fs in sorted(por_beat.items()):
        if b in puestos:
            continue
        for f in fs:
            toma = f["toma"]
            try:
                pal = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                pal = []
            texto = " ".join(w["text"] for w in pal
                             if transcribir.suena(w, f["desde"], f["hasta"]))
            segs.append([round(f["desde"], 3), round(f["hasta"], 3)])
            det.append({"beat": b, "toma": toma, "texto": texto, "fijado": f["id"],
                        "por_que": f["por_que"]})
        hechos.append(b)
    orden = sorted(range(len(det)), key=lambda i: (det[i].get("beat") or 0,
                                                  segs[i][0]))
    edl["segmentos"] = [segs[i] for i in orden]
    edl["detalle"] = [det[i] for i in orden]
    edl["duracion_s"] = round(sum(b - a for a, b in edl["segmentos"]), 2)
    json.dump(edl, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(hechos), sorted(set(hechos))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel", nargs="?", type=int)
    ap.add_argument("beat", nargs="?", type=int)
    ap.add_argument("toma", nargs="?")
    ap.add_argument("desde", nargs="?", type=float)
    ap.add_argument("hasta", nargs="?", type=float)
    ap.add_argument("--por-que", default="")
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    slug = f"reel-{a.reel:02d}" if a.reel else None
    if a.ver:
        for f in fijados(slug):
            print(f"  e{f['beat']:<3} {f['toma']} [{f['desde']}-{f['hasta']}]"
                  f"  {f['por_que'][:70]}")
        return
    if a.aplicar:
        n, cuales = aplicar(slug)
        print(f"{slug}: {n} etapa(s) fijadas en el EDL {cuales}")
        return
    v = fijar(slug, a.beat, a.toma, a.desde, a.hasta, a.por_que)
    print(f"{slug} e{a.beat}: fijado. marca {v.get('marca')}"
          f" · {v.get('veredicto')} · margen {v.get('margen')}")
    print(f"    {(v.get('texto') or '')[:120]}")


if __name__ == "__main__":
    main()
