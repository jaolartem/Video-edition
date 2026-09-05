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


# Cuanto se puede retroceder para no entrar a mitad de frase. Mas que esto y
# lo que se recupera ya no es la cabeza de lo que se dice: es lo anterior.
RETROCESO = 1.5
# Por encima de esto un silencio deja de ser una pausa del hablante y pasa a ser
# aire muerto: se parte el tramo y se deja fuera.
HUECO = 1.2


def _a_la_palabra(toma, ini, fin, cerca=0.45, voz=None):
    """Mueve los bordes a la frontera de palabra mas cercana.

    Solo si esta a menos de `cerca`: por encima de eso el borde no parte una
    silaba, esta donde alguien lo puso a proposito, y moverlo seria decidir por
    el. Devuelve `(ini, fin)` tal cual si no hay transcript.
    """
    import transcribir as _tr

    try:
        pal = _tr.exigir(toma)["segmentos"]
    except SystemExit:
        return ini, fin
    # Al entrar: si el borde cae dentro de una palabra, o justo despues de que
    # empiece, se entra donde empieza. Si esa palabra ya va por la mitad, se
    # entra cuando acaba.
    for w in pal:
        x, y = w["start"], w["end"]
        if x < ini < y and y - x < 2.0:
            ini = x if (ini - x) < (y - ini) and (ini - x) <= cerca else (
                y if (y - ini) <= cerca else ini)
            break
    for w in pal:
        x, y = w["start"], w["end"]
        if not (x < fin < y):
            continue
        # **El final de la palabra puede tragarse la pausa siguiente.** El
        # alineador estira la ultima palabra de una frase sobre el silencio, asi
        # que su `end` no es donde deja de sonar. Si se ajustara ahi entrarian
        # segundos mudos, y por eso el filtro de `cerca` lo descartaba y el
        # borde se quedaba partido: «al» sin «año», «en» sin «Ontario».
        #
        # La salida no es rendirse: es **acotar**. La palabra acaba, de verdad,
        # donde acaba el tramo de habla que la contiene. Lo dijo el paso que lo
        # sufrio dos vueltas seguidas: «cuando el acaba de la palabra absorbe
        # una pausa, acotar en vez de rendirse».
        real = y
        for a2, b2 in (voz or []):
            if a2 <= x < b2:
                real = min(y, b2)
                break
        if (real - fin) <= cerca:
            fin = real
        elif (fin - x) <= cerca:
            fin = x
        break
    return ini, fin


def _a_la_voz(toma, a, b, margen=0.12):
    """Recorta los bordes de un tramo hasta donde de verdad se habla.

    ## Por que esto no puede ser responsabilidad de quien propone

    Un borde se propone copiando los segundos de una palabra del transcript, y
    **ese final esta inflado**: el alineador estira la ultima palabra de cada
    frase sobre el silencio que viene detras. Medido en la cinta de reel-06,
    `ano` dura de 319,14 a 326,20 —siete segundos para una palabra— y `Ontario.`
    de 417,89 a 424,20. Copiar ese final es tragarse la pausa entera.

    El resultado no es un corte peor: es una pieza que **se queda muda**. reel-06
    llevaba 15 s de silencio dentro, dos de ellos con un tablero encima, o sea
    con el espectador mirando algo que nadie le explica. Y no se ve leyendo el
    texto, porque por texto la frase esta completa.

    Asi que no se le pide a quien propone que lo tenga en cuenta —eso es un paso
    que depende de que alguien se acuerde—: se recorta aqui, que es por donde
    pasan todos los caminos que declaran una etapa. Es C-101 otra vez: cuando
    dos medidas del mismo hecho discrepan, gana la que mide el hecho. El
    transcript mide texto y **rellena** los tiempos que no sabe; el detector de
    voz mide la onda.

    **Solo los bordes.** Un silencio en medio es una pausa del hablante y es
    suya; quitarla es otra decision y la toma otro paso.

    Devuelve `None` si en ese tramo no se habla en absoluto.
    """
    import rutas as _ru

    f = os.path.join(_ru.TRABAJO, "cuts", f"{toma}.json")
    if not os.path.exists(f):
        return (a, b)
    try:
        voz = json.load(open(f, encoding="utf-8"))["segmentos"]
    except (OSError, KeyError, json.JSONDecodeError):
        return (a, b)
    dentro = [(max(a, x), min(b, y)) for x, y in voz if min(b, y) - max(a, x) > 0.01]
    if not dentro:
        return None
    # **Y no se entra a mitad de una frase.** Si el borde cae DENTRO de un
    # tramo de habla, lo que se corta no es silencio: es el principio de lo que
    # se esta diciendo. Se retrocede hasta donde ese tramo empieza.
    #
    # Es la otra cara de lo mismo que C-129, y la mas cara: el alineador estira
    # una palabra sobre el silencio que la precede igual que sobre el que la
    # sigue. En la cinta de reel-05 la palabra «14» figura de 519,62 a 532,38
    # —doce segundos— y el corte entraba en 532,3, dentro de ella. Resultado: la
    # pieza decia «mil dolares de impuesto adicional» y **la cifra no aparecia
    # ni en el trozo ni en `antes`**, porque por texto la palabra cruzaba el
    # borde. Tres pasadas la dieron por no grabada. La cinta dice «14 mil».
    #
    # El limite existe para no arrastrar la frase anterior: si el tramo empezo
    # mucho antes, el borde se puso ahi por una razon y no se toca.
    ini = max(a, min(x for x, _ in dentro) - margen)
    fin = min(b, max(y for _, y in dentro) + margen)
    # **Y no se entra ni se sale a mitad de palabra.**
    #
    # El recorte a la voz deja el borde donde hay sonido, pero el sonido de una
    # palabra empieza antes de que la palabra se entienda: entrar en mitad de
    # «estratega» deja «tratega», y salir en mitad de «Ontario» deja «Onta».
    # Los agentes lo han devuelto vuelta tras vuelta —«estratega», «mas», «año»,
    # «Ontario», «20»— y siempre es lo mismo: un corte que cae dentro del tramo
    # de una palabra.
    #
    # Se ajusta a la frontera mas cercana **dentro de un margen corto**: si la
    # palabra que cruza el borde apenas ha empezado, se entra despues de ella;
    # si ya casi ha acabado, se entra antes. Mas lejos que eso no se toca — ahi
    # ya no es una silaba partida, es contenido, y eso lo decide el paso.
    ini, fin = _a_la_palabra(toma, ini, fin, voz=voz)
    for x, y in voz:
        if x < a < y and a - x <= RETROCESO:
            ini = min(ini, max(0.0, x - margen))
            break
        # **Y lo que queda fuera del techo se dice, no se acepta callando.**
        #
        # El tope existe para no arrastrar la frase anterior, y esta bien que
        # exista; lo que estaba mal es que por encima de el este paso no
        # distinguia «el borde se puso ahi a proposito» de «el borde cayo a
        # mitad de frase y nadie lo vio». Los dos salian iguales: en silencio.
        #
        # reel-05 e2 entraba 3,12 s dentro de un bloque de voz de 5,755 s
        # —cinco veces RETROCESO— y por eso la pieza empezaba el caso en «...
        # tres casas en un mismo trimestre», sin nombrar al realtor que su
        # propio tablero rotula. Jaime lo pidio dos veces. No se mueve el borde
        # —eso seria decidir por quien lo puso— pero se cuenta cuanta frase se
        # queda fuera, que es lo unico que hacia falta para verlo antes de
        # montar.
        if x < a < y:
            print(f"  aviso {toma} [{a:.3f}]: entra {a - x:.2f} s en el bloque"
                  f" de voz de {x:.3f} y RETROCESO son {RETROCESO} s")
            break
    if fin - ini <= 0.2:
        return None
    # **Y un silencio largo DENTRO tampoco es una pausa: es aire muerto.**
    #
    # Esto solo recortaba los bordes, con el argumento de que un hueco en medio
    # es una pausa del hablante y es suya. Cierto hasta cierta duracion: siete
    # segundos no son una pausa. reel-04 llevaba 18,3 s mudos sobre 83, dos de
    # ellos con un tablero encima, y **cuatro vueltas de revision no lo vieron**
    # porque por texto el trozo parece una frase entera — el `hasta` estaba
    # clavado en la marca de la palabra siguiente.
    #
    # Se agrupan los tramos de voz que estan a menos de `HUECO` unos de otros;
    # cada grupo sale como un tramo. Deja de ser trabajo que alguien tiene que
    # ver y repetir en cada vuelta.
    grupos, act = [], []
    for x, y in dentro:
        if act and x - act[-1][1] > HUECO:
            grupos.append(act)
            act = []
        act.append((x, y))
    if act:
        grupos.append(act)
    trozos = []
    for g in grupos:
        x = max(ini, g[0][0] - margen)
        y = min(fin, g[-1][1] + margen)
        if y - x > 0.25:
            # **El ajuste a la palabra va AQUI, sobre el tramo que sale.**
            #
            # Estaba arriba, y despues de el pasaban dos cosas que lo deshacian:
            # el `RETROCESO` tira `ini` hacia el arranque del tramo de voz, y
            # estas dos lineas construyen el borde definitivo desde los tramos
            # de voz —`g[0][0] - margen`— en vez de desde el borde ya ajustado.
            # O sea que el ajuste solo sobrevivia cuando era el que mandaba.
            #
            # C-135 lo dejo escrito y el codigo hacia lo contrario: «primero se
            # recorta a la voz medida sobre la onda, LUEGO se ajusta a la
            # palabra». Aqui hacia voz, palabra, y voz otra vez.
            #
            # Medido sobre las seis piezas: 28 bordes a menos de 0,45 s de una
            # frontera —o sea, dentro del margen que este paso si toca— seguian
            # cayendo dentro de una palabra, y casi todos de entrada, que es el
            # lado que el `RETROCESO` mueve.
            x, y = _a_la_palabra(toma, x, y, voz=voz)
            trozos.append((round(x, 3), round(y, 3)))
    return trozos or None


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
    vistos = {}
    for x, y, tk in sorted(tramos, key=lambda t: (t[0], -(t[1] - t[0]))):
        if x not in vistos:
            vistos[x] = (x, y, tk)
    tramos = [vistos[k] for k in sorted(vistos)]
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
    """Deja fuera las declaraciones que hablan de un texto que ya no esta ahi.

    **Por etapa entera y no por tramo**: `aplicar` rehace la etapa con los
    tramos que le llegan, asi que colar la mitad de una declaracion vieja deja
    la etapa peor que no tocarla.

    Lo que NO hace es borrarlas. Una declaracion es una decision con autor y
    porque; lo que caduca es su prueba, no la decision. Se queda en la tabla,
    no se aplica, y se dice en voz alta — para que el paso que la puso la vuelva
    a mirar con la cinta de hoy delante.

    Las que no tienen huella son las de antes de que esto existiera: se estampan
    con la de ahora y se aplican, pero se cuenta cuantas, porque adoptar una
    prueba no es haberla comprobado.
    """
    vivas, viejas, adoptadas = [], {}, 0
    con = _con()
    for f in fjs:
        if not f.get("toma"):
            vivas.append(f)
            continue
        h = huella(f["toma"], f["desde"], f["hasta"])
        if f.get("huella") and h and h != f["huella"]:
            viejas.setdefault(f["beat"], 0)
            viejas[f["beat"]] += 1
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
    if viejas:
        fuera = set(viejas)
        vivas = [f for f in vivas if f["beat"] not in fuera]
        print(f"  {slug}: etapa(s) {sorted(fuera)} declaradas contra un texto"
              f" que ya no esta ahi — NO se aplican. Manda la seleccion de hoy"
              f" hasta que el paso que las puso las vuelva a mirar.")
    return vivas


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

    orden = sorted(range(len(det)), key=lambda i: (det[i].get("beat") or 0,
                                                  segs[i][0]))
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
