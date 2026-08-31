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


def declarar(slug, beat, toma, tramos, por_que="", quien="servicio"):
    """Declara **cuáles son** los tramos de una etapa. Sustituye lo que hubiera.

    ## Por qué esta función existe y `fijar` es ahora una envoltura suya

    `corte_fijo` empezó con la clave en `(video, papel, orden)`: una etapa, un
    tramo. Declarar era **sustituir por construcción** — el `on conflict` pisaba
    lo anterior y no había forma de equivocarse.

    Luego la clave se amplió con `desde`, porque una etapa puede necesitar dos
    trozos de verdad: la idea de reel-01 e2 vive en 118 y su remate en 220. Eso
    era necesario, y a cambio —sin que nadie lo notara— **sacó una garantía del
    esquema y la metió en la memoria de quien llama**: a partir de ahí, «declara
    el tramo de esta etapa» eran dos operaciones, borrar y luego insertar, y
    sólo una de las dos estaba en la firma.

    Uno de los dos sitios que declaran lo hacía bien y el otro no. El que no,
    dejó reel-05 diciendo su cierre dos veces y la pieza pasó de 105 a 157
    segundos — y no fallo nada: un tramo de más no da error, alarga.

    Es la regla del proyecto aplicada al código: **un paso que depende de que
    alguien se acuerde no es un paso del proceso.** Así que la operación pasa a
    ser una sola y recibe **la lista entera**: no existe una manera de añadir un
    tramo sin sustituir, porque no hay función que lo haga.

    Devuelve lo que dice la medida sobre el conjunto propuesto.
    """
    import revalidar

    tramos = [(float(a), float(b)) for a, b in tramos if b > a]
    if not tramos:
        return {"error": f"{slug} e{beat}: no se declara una etapa sin tramos"}
    veredicto = revalidar.evaluar(slug, int(beat), tramos, toma=toma)
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    con = _con()
    vid = _vid(con, slug)
    # Lo que hubiera declarado para esta etapa se va, **venga de donde venga**.
    # `tramos` dice cuál ES la etapa, no qué se le suma.
    con.execute("delete from corte_fijo where video_id = ? and papel = 'etapa'"
                " and orden = ?", (vid, int(beat)))
    con.executemany(
        "insert into corte_fijo (video_id, papel, orden, desde, hasta, toma,"
        " por_que, quien, fecha) values (?,'etapa',?,?,?,?,?,?,?)",
        [(vid, int(beat), a, b, toma, por_que, quien, ahora) for a, b in tramos])
    con.commit()
    con.close()
    return veredicto


def fijar(slug, beat, toma, desde, hasta, por_que="", quien="servicio"):
    """Un solo tramo. Envoltura de `declarar` — y sustituye, como ella.

    Se conserva porque es lo que escribe la línea de comandos y lo que leen los
    dos servicios. Lo que **no** se conserva es la posibilidad de llamarla en
    bucle para declarar dos tramos: eso ahora deja sólo el último, a propósito,
    porque era justo el uso que rompía. Para dos tramos, `declarar`.
    """
    return declarar(slug, beat, toma, [(desde, hasta)], por_que, quien)


def solapes(slug):
    """Etapas cuyos tramos declarados se pisan entre sí. Es una contradicción.

    Una etapa de dos trozos dice «esto y luego esto». Dos trozos que se solapan
    dicen «esto, y otra vez esto», que no es una declaración: es el resto de una
    que no se retiró. Se mira aquí para que la puerta pueda mirarlo.
    """
    por_beat = {}
    for f in fijados(slug):
        por_beat.setdefault(f["beat"], []).append(f)
    malos = []
    for beat, fs in sorted(por_beat.items()):
        fs = sorted(fs, key=lambda x: x["desde"])
        for a, b in zip(fs, fs[1:]):
            if b["desde"] < a["hasta"] - 1e-3 and a["toma"] == b["toma"]:
                malos.append((beat, a, b))
    return malos


def rehacer(slug, beats=None):
    """Reconstruye esas etapas del EDL **desde su declaración**.

    `aplicar` es incremental a propósito: salta la etapa cuyas declaraciones ya
    están puestas, para no deshacer lo que otro paso recortó por dentro. El
    efecto colateral es que **no hay camino de vuelta**: si el EDL de una etapa
    quedó mal —duplicado, a medias, con un tramo que ya no se declara—, la
    declaración puede estar perfecta y `aplicar` no la toca, porque desde su
    punto de vista está hecha.

    Eso obligaba a repararlo a mano: borrar la marca `fijado` del JSON y volver
    a correr. Se hizo una vez, funcionó, y no quedó en ningún sitio — que es
    exactamente la forma de perder el estado que este proyecto persigue. Aquí
    está, con nombre y con argumentos.

    Sin `beats`, rehace **todas** las etapas declaradas de la pieza.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        raise SystemExit(f"{slug}: no hay EDL que rehacer")
    quiere = ({int(b) for b in beats} if beats is not None
              else {f["beat"] for f in fijados(slug)})
    if not quiere:
        return 0, []
    edl = json.load(open(ruta, encoding="utf-8"))
    for d in edl.get("detalle") or []:
        if d.get("beat") in quiere:
            d.pop("fijado", None)
    json.dump(edl, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return aplicar(slug)


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
    ap.add_argument("--rehacer", nargs="*", type=int, metavar="BEAT",
                    help="reconstruye esas etapas desde su declaracion"
                         " (sin numeros, todas las declaradas)")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()
    slug = f"reel-{a.reel:02d}" if a.reel else None
    if a.ver:
        for f in fijados(slug):
            print(f"  e{f['beat']:<3} {f['toma']} [{f['desde']}-{f['hasta']}]"
                  f"  {f['por_que'][:70]}")
        return
    if a.rehacer is not None:
        n, cuales = rehacer(slug, a.rehacer or None)
        print(f"{slug}: {n} etapa(s) rehechas desde su declaracion {cuales}")
        for beat, x, y in solapes(slug):
            print(f"  aviso e{beat}: los tramos declarados se pisan"
                  f" ({x['desde']}-{x['hasta']} y {y['desde']}-{y['hasta']})")
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
