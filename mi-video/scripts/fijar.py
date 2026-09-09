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
import basedatos
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "ads/decisiones.db"

#: La medida que cierra el tiquet de una prueba que se movio. Lo abre `fijar`
#: y lo cierra el compositor con su respuesta, por el conducto de siempre: no
#: hay atajo que lo cierre desde dentro de la linea.
MOVIDA = "prueba movida"


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def _vid(con, slug):
    r = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not r:
        raise SystemExit(f"{slug}: no está en la base")
    return r["id"]


def huella(toma, a, b):
    """Que se oye dentro de ese tramo, reducido a doce caracteres.

    Es la prueba contra la que se declaro. Se lee por `exigir()` —la puerta—,
    no del fichero, para que sea el mismo texto que ve quien monta.

    Se compara texto y no segundos a proposito: la linea reescribe los
    transcripts en su paso `afinado` y los tiempos se mueven unas milesimas sin
    que cambie una palabra. Lo que invalida una declaracion no es que el fichero
    sea mas nuevo: es que **ahi ahora se dice otra cosa**.
    """
    import hashlib
    import unicodedata

    import transcribir as _tr

    try:
        pal = _tr.exigir(toma)["segmentos"]
    except (SystemExit, Exception):                # noqa: BLE001
        return None
    dentro = [w["text"] for w in pal if _tr.suena(w, a, b)]
    if not dentro:
        return None
    t = unicodedata.normalize("NFD", " ".join(dentro).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn"
                and (c.isalnum() or c == " "))
    return hashlib.sha1(" ".join(t.split()).encode("utf-8")).hexdigest()[:12]


def fijados(slug):
    """Los tramos declarados de una pieza, por beat."""
    con = _con()
    filas = con.execute(
        "select cf.id, cf.orden beat, cf.desde, cf.hasta, cf.toma, cf.por_que,"
        " cf.huella"
        "  from corte_fijo cf join video v on v.id = cf.video_id"
        " where v.slug = ? and cf.papel = 'etapa' order by cf.orden, cf.desde",
        (slug,)).fetchall()
    con.close()
    return [dict(f) for f in filas]


def huerfanas(slug):
    """Las marcas `fijado` del EDL que ya **no tienen declaracion** en la tabla.

    Es la misma pregunta que `fijados`, hecha en la otra direccion, y hace falta
    justo por eso: preguntando «¿esta en el corte lo que la tabla declara?» una
    tabla vacia no acusa a nadie —recorre cero filas y da luz verde—, que es
    como `verificar.py 5` respondia «reel-05: OK» con sus 27 declaraciones
    destruidas y sus 27 marcas huerfanas en el propio EDL.

    La marca la escribe `aplicar` con el id de la declaracion de la que sale, o
    sea que **es un recibo**: si esta en el EDL, alguien declaro. Que la fila ya
    no exista solo puede significar que se borro.

    Devuelve `(id, beat, desde, hasta, toma, por_que)`, que es lo que hace falta
    para reponerla — la lee `db.recuperar`.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    hay = {f["id"] for f in fijados(slug)}
    return [(d["fijado"], d["beat"], round(float(a), 3), round(float(b), 3),
             d.get("toma") or "", d.get("por_que") or "")
            for (a, b), d in zip(edl["segmentos"], edl["detalle"])
            if d.get("fijado") and d["fijado"] not in hay
            and d.get("beat") is not None]


# Las dos medidas que ajustan un tramo a la cinta viven en `dominio.ajuste`:
# no escriben nada y `costuras.py` tambien las necesita. Se conservan los
# nombres privados porque son los que ya se llaman desde fuera.
from dominio.ajuste import HUECO, RETROCESO  # noqa: F401
from dominio.ajuste import a_la_palabra as _a_la_palabra  # noqa: F401
from dominio.ajuste import a_la_voz as _a_la_voz  # noqa: F401


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

    # **Cada tramo puede traer su cinta.** `[desde, hasta]` usa la de la etapa;
    # `[desde, hasta, toma]` dice la suya. La columna `corte_fijo.toma` es por
    # fila desde siempre y `aplicar` ya la respeta fila a fila: lo unico que lo
    # impedia era esta firma, que aplicaba una sola cinta a toda la lista.
    #
    # Y no es un capricho de esquema: es lo que bloqueaba el piso. reel-05 y
    # reel-06 no podian meter el escalon del precio —«luego sube», que esta en
    # otra cinta— sin tirar la promesa entera de esa etapa, y sin escalon la
    # pieza no sale. C-110 ya decia que una etapa puede llevar tramos de dos
    # cintas; faltaba poder decirlo.
    puestos = []
    for t in tramos:
        a, b = float(t[0]), float(t[1])
        tk = t[2] if len(t) > 2 and t[2] else toma
        if b > a:
            puestos.append((a, b, tk))
    if not puestos:
        return {"error": f"{slug} e{beat}: no se declara una etapa sin tramos"}
    # `_a_la_voz` puede devolver VARIOS tramos: si el propuesto llevaba un
    # silencio largo dentro, sale partido en los trozos que si tienen voz.
    tramos = []
    for a, b, tk in puestos:
        for x, y in (_a_la_voz(tk, a, b) or []):
            tramos.append((x, y, tk))
    # **Y sin repetidos.** Al partir por los huecos, dos tramos propuestos que
    # se solapaban pueden acabar empezando en el mismo segundo, y la clave de
    # `corte_fijo` es `(video, papel, orden, desde)`: el segundo no entra, hace
    # saltar la insercion entera y con ella la etapa. Se quedan una vez, y el
    # mas largo de los que empiecen igual.
    #
    # **Y quitar repetidos no es ordenar.** Esto ordenaba por `desde` de paso, y
    # con eso una etapa no podia decir «esta frase va PRIMERO aunque en la cinta
    # este despues» — que es justo lo que pidio Jaime para el gancho de reel-03.
    # El orden es el que se declara; aqui solo se cae lo repetido.
    vistos, orden = {}, []
    for x, y, tk in tramos:
        if x in vistos:
            if y - x > vistos[x][1] - vistos[x][0]:
                vistos[x] = (x, y, tk)
            continue
        vistos[x] = (x, y, tk)
        orden.append(x)
    tramos = [vistos[k] for k in orden]
    if not tramos:
        return {"error": f"{slug} e{beat}: los tramos propuestos no tienen voz"}
    # La medida se hace sobre la cinta principal —la que mas segundos aporta—,
    # que es la que define el timbre de la etapa.
    _por_cinta = {}
    for a, b, tk in tramos:
        _por_cinta[tk] = _por_cinta.get(tk, 0.0) + (b - a)
    principal = max(_por_cinta, key=_por_cinta.get)
    veredicto = revalidar.evaluar(slug, int(beat), [(a, b) for a, b, tk in tramos
                                                   if tk == principal],
                                  toma=principal)
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    con = _con()
    vid = _vid(con, slug)
    # Lo que hubiera declarado para esta etapa se va, **venga de donde venga**.
    # `tramos` dice cuál ES la etapa, no qué se le suma.
    con.execute("delete from corte_fijo where video_id = ? and papel = 'etapa'"
                " and orden = ?", (vid, int(beat)))
    con.executemany(
        "insert into corte_fijo (video_id, papel, orden, desde, hasta, toma,"
        " por_que, quien, fecha, huella) values (?,'etapa',?,?,?,?,?,?,?,?)",
        [(vid, int(beat), a, b, tk, por_que, quien, ahora, huella(tk, a, b))
         for a, b, tk in tramos])
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

    **Y rehace ESAS y no las demás.** Decía «esas etapas» y hacía otra cosa:
    quitaba la marca de las pedidas y luego llamaba a `aplicar` entero, así que
    toda declaración pendiente de la pieza —una que nadie pidió tocar hoy— se
    colaba en el mismo movimiento. Pedir el beat 7 del reel-01 rehacía también
    el 3, que tenía una declaración sin aplicar de un ticket viejo: la etapa
    pasaba de 20,2 s a 15,5 s y se llevaba «30 mil dólares, no de ventas — de
    estructura», que es el remate de la comparación. Nada fallaba; la pieza
    salía más corta y peor.

    Es la regla del proyecto otra vez: **una corrección de una tuerca no
    regenera la pieza entera.** El argumento acota lo que se rehace, no sólo lo
    que se desmarca.
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
    return aplicar(slug, solo=quiere)


def _con_prueba_viva(slug, fjs):
    """Deja fuera la declaracion cuya prueba ya no casa, **y la manda**.

    La regla en si estaba bien: si el texto que se oye ahi no es el que se
    declaro, no se aplica a ciegas. Lo que faltaba era la otra mitad — nadie
    volvia nunca. El aviso se escribia en `stdout`, la linea seguia, y por ahi
    reel-03 se entrego sin el adelanto de los tiquets #276, #277 y #279:
    43,8 s, `desatura: []` y con el gancho de siempre. reel-02 estaba igual.

    Ahora la etapa se queda fuera —`verificar` para la pieza por el tramo que
    no dejo rastro— y **su encargo va al compositor por tiquet**, acotado a esa
    etapa. Jaime, 9-9-2026: *«se envia al compositor que es el que arregla
    todo, y continua por la linea de produccion»*.

    **Y salta mas de lo que parece**, que es lo que hay que tener presente al
    leer un aviso de estos: `afinado` (fase 3) vuelve a transcribir los tramos
    elegidos justo despues de `fijado` (fase 2.5), que es donde se estampa la
    prueba. Medido el 9-9-2026 en reel-03: cinco de catorce declaraciones no
    casaban, y ninguna aparece desplazada en ±1,5 s — no era desfase, era otra
    segmentacion de las mismas palabras.

    Las que no tienen huella son las de antes de que esto existiera: se
    estampan con la de ahora y se aplican, pero se cuenta cuantas, porque adoptar una
    prueba no es haberla comprobado.
    """
    vivas, movidas, adoptadas = [], {}, 0
    con = _con()
    for f in fjs:
        if not f.get("toma"):
            vivas.append(f)
            continue
        h = huella(f["toma"], f["desde"], f["hasta"])
        if f.get("huella") and h and h != f["huella"]:
            movidas.setdefault(f["beat"], 0)
            movidas[f["beat"]] += 1
            continue
        if not f.get("huella") and h:
            con.execute("update corte_fijo set huella = ? where id = ?",
                        (h, f["id"]))
            adoptadas += 1
        vivas.append(f)
    con.commit()
    con.close()
    if adoptadas:
        print(f"  {slug}: {adoptadas} declaracion(es) sin prueba estampada —"
              f" se adopta la de hoy; no es lo mismo que comprobada")
    if movidas:
        fuera = set(movidas)
        vivas = [f for f in vivas if f["beat"] not in fuera]
        _al_compositor(slug, movidas)
    return vivas


def _prueba_casa(slug):
    """Cierra el tiquet de la prueba movida cuando vuelve a casar entera."""
    from dominio import ticket as _t

    for t in _t.abiertos(slug):
        if (t["cierra_con"] or "") == MOVIDA:
            _t.contestar(t["id"], f"{slug}: las declaraciones vuelven a casar"
                         f" con el transcript de hoy, una por una.",
                         "arreglado", "la linea", MOVIDA)


def _al_compositor(slug, movidas):
    """La etapa se queda sin su declaracion y va al compositor por tiquet.

    **El seguro para, y la pieza entra por donde entra todo: el tiquet.**
    Jaime, 9-9-2026: *«no se envia por secciones, se envia al compositor que es el que
    arregla todo, y continua por la linea de produccion; por supuesto que los
    seguros van a saltar si no se sigue la linea, porque para eso son»*.

    Lo que faltaba no era aflojar el seguro: era la otra mitad, que nadie
    volviera nunca. El aviso se escribia en `stdout` y la linea seguia — asi
    perdio reel-03 el adelanto de los tiquets #276, #277 y #279. Ahora la etapa
    no se aplica, `verificar` para la pieza por el tramo que no dejo rastro, y
    el compositor recibe el encargo acotado a esa etapa.

    Uno por etapa y no uno por vuelta: la condicion es de la etapa.
    """
    from dominio import ticket as _t

    print(f"  {slug}: etapa(s) {sorted(movidas)} declaradas contra un texto"
          f" que ya no esta ahi — NO se aplican. Van al compositor por"
          f" tiquet.")
    ya = {t["beat"] for t in _t.abiertos(slug)
          if (t["cierra_con"] or "") == MOVIDA}
    for beat, cuantos in sorted(movidas.items()):
        if beat in ya:
            continue
        _t.abrir(slug, (
            f"e{beat} — sus {cuantos} tramo(s) declarados llevan una prueba"
            f" que"
            f" ya no casa con el transcript de hoy, asi que `fijar --aplicar`"
            f" NO los pone y la etapa sale con la seleccion automatica. La"
            f" decision sigue entera en `corte_fijo`, con su autor y su"
            f" porque:"
            f" lo que caduco es la prueba, no la decision. ACOTADO A ESTA"
            f" ETAPA: mira el tramo con la cinta de hoy delante y vuelve a"
            f" declararlo, o di por que ya no procede."),
            tipo="falta", vuelve_a="descrito", cierra_con=MOVIDA)


def aplicar(slug, solo=None):
    """Mete los tramos fijados en el EDL, sustituyendo los de esa etapa.

    **Se rehace el detalle de la etapa entera**, no se añade un trozo: un fijado
    dice cuál es el tramo de esa etapa, así que los que hubiera se van. Lo demás
    del EDL —las otras etapas, la oferta, la estructura— no se toca.

    `solo` acota a esos beats. Sin él entran todas las declaraciones vivas de la
    pieza, que es lo que quiere una corrida de línea; con él, lo que quiere una
    corrección concreta — ver `rehacer`.
    """
    import transcribir

    fjs = fijados(slug)
    if solo is not None:
        fjs = [f for f in fjs if f["beat"] in solo]
    if not fjs:
        return 0, []
    fjs = _con_prueba_viva(slug, fjs)
    if not fjs:
        return 0, []
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        raise SystemExit(f"{slug}: no hay EDL que tocar")
    edl = json.load(open(ruta, encoding="utf-8"))
    por_beat = {}
    for f in fjs:
        por_beat.setdefault(f["beat"], []).append(f)
    # **En el orden en que se DECLARARON, no en el de la cinta.**
    #
    # Ordenar por `desde` daba por hecho que el montaje sigue a la grabacion, y
    # eso hace imposible lo unico que un editor pide a veces: traerse una frase
    # de mas adelante al principio. Jaime, 7-9-2026, sobre reel-03: *«le
    # cambiamos el gancho por la frase mas fuerte, sin quitar el gancho y
    # repitiendo la frase en donde originalmente va»* — la frase esta en el
    # segundo 337 de la cinta y tiene que sonar antes que el segundo 28.
    #
    # No cambia nada de lo que ya hay: comprobados los 27 grupos de mas de un
    # tramo del proyecto, en los 27 el orden de declaracion y el de cinta son el
    # mismo. Lo unico que cambia es que ahora se puede decir otra cosa.
    for v in por_beat.values():
        v.sort(key=lambda x: x["id"])
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
    # **Una etapa que vuelve al EDL vuelve con su camino.**
    #
    # La rama de arriba conserva el detalle entero con `{**d}`; la de abajo
    # —la que mete una etapa que no estaba— construye un dict pelado, sin
    # `etapa` ni `trato`. Y sin `trato` el render **para**: «el beat 2 pide el
    # camino "undefined", que no existe». Paso con reel-04 b2.
    #
    # No se inventa aqui: se pregunta a quien lo decidio. `trato.decidido` lee
    # lo que el paso de descripcion resolvio mirando la pieza entera, y el
    # nombre de la etapa sale de `etapa`, que es donde vive el frame. Si nadie
    # lo ha decidido todavia se queda sin poner, que es distinto de ponerlo mal.
    import trato as _tr

    # El nombre de la etapa vive en el frame y lo pone `beats`; aqui basta con
    # que no se pierda el que ya trae el detalle. Lo que el render exige y se
    # perdia es el `trato`.
    for d in det:
        b = d.get("beat")
        if b is None:
            continue
        if not d.get("trato"):
            t, porque = _tr.decidido(slug, b)
            if t:
                d["trato"], d["trato_porque"] = t, porque

    # **Por etapa, y DENTRO de la etapa como se construyo.**
    #
    # La segunda clave era `segs[i][0]`, o sea el segundo de la cinta, y eso
    # daba por hecho que dentro de una etapa el montaje sigue a la grabacion.
    # Es el tercer sitio donde se colaba la misma suposicion —los otros dos son
    # `declarar` y el reparto por beat de aqui arriba—, y entre los tres hacian
    # imposible traerse una frase de mas adelante al principio: la de reel-03,
    # que Jaime pidio como gancho. `sorted` es estable, asi que quitando la
    # segunda clave el orden de dentro es el que trajo cada rama: el declarado
    # para las etapas fijadas, el que ya tenia el EDL para las demas.
    orden = sorted(range(len(det)), key=lambda i: det[i].get("beat") or 0)
    edl["segmentos"] = [segs[i] for i in orden]
    edl["detalle"] = [det[i] for i in orden]
    edl["duracion_s"] = round(sum(b - a for a, b in edl["segmentos"]), 2)
    # **Y el otro sitio donde vive la misma cifra.** El EDL lleva la duracion
    # dos veces —`duracion_s` y `duracion_montada_s`— y este paso solo tocaba
    # una: despues de fijar una etapa el fichero decia 93,92 y 93,36 a la vez.
    # `depurar` y `revision` ya escriben las dos; aqui faltaba, y una cifra que
    # solo se actualiza en dos de los tres caminos es una cifra en la que no se
    # puede confiar (es lo que `registrar_version` guarda como duracion de la
    # version).
    edl["duracion_montada_s"] = edl["duracion_s"]
    # Y la lista de cintas, que es paralela a `detalle` y aqui se quedaba con la
    # longitud de antes: 24 entradas para 23 segmentos. Hoy no rompe porque la
    # pieza sale de una sola cinta, pero una lista paralela descuadrada es la
    # averia del indice re-usado esperando a que haya dos.
    edl["fuentes"] = [d.get("toma") or "" for d in edl["detalle"]]
    json.dump(edl, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return len(hechos), sorted(set(hechos))


def _trozo(txt):
    """`desde:hasta` o `desde:hasta:toma`, tal como los toma `declarar`."""
    desde, hasta, *toma = txt.split(":")
    return [float(desde), float(hasta)] + toma


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
    #: **Una etapa de dos trozos, desde la linea.** `declarar` sustituye la
    #: lista entera —esa es su garantia, ver su docstring— y la linea solo sabia
    #: pasarle UN tramo, asi que corregir el borde de un trozo de reel-05 e2
    #: —«lo digo porque un realtor que vende…»— por la linea se llevaba por
    #: delante el otro, el del retail. La unica salida era llamar a `declarar`
    #: desde Python, o sea hacer a mano el trabajo de la maquina: una decision
    #: que no se puede repetir desde la linea no es un paso del proceso.
    ap.add_argument("--tramo", action="append", type=_trozo,
                    help="trozo desde:hasta[:toma]; repetible, declara la etapa"
                         " entera y sustituye a los posicionales")
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
    v = (declarar(slug, a.beat, a.toma, a.tramo, a.por_que) if a.tramo
         else fijar(slug, a.beat, a.toma, a.desde, a.hasta, a.por_que))
    print(f"{slug} e{a.beat}: fijado. marca {v.get('marca')}"
          f" · {v.get('veredicto')} · margen {v.get('margen')}")
    print(f"    {(v.get('texto') or '')[:120]}")


if __name__ == "__main__":
    main()
