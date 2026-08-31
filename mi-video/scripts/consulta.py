"""Las consultas que necesita `describir.mjs`, en un solo sitio.

El paso de IA vive en JavaScript porque ahí está el `fetch`, pero la base es de
Python en todo el resto del proyecto. En vez de abrir la base desde los dos
lados —dos formas de escribir la misma tabla es de donde salen los fallos de
este proyecto— el lado JS pide por nombre y aquí está la única implementación.

    python scripts/consulta.py escenas_por_describir '[[], false]'
    python scripts/consulta.py guardar_escena '["reel-03", 2, {...}]'
"""
import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "ads/decisiones.db"


def _montaje(slug):
    """Lo que dice cada etapa en el montaje actual. Una sola fuente: `Pieza`.

    No se pregunta a la base: la base guarda **lo que se eligio**, y el montaje
    es lo que sobrevivio a los recortes posteriores. Describir lo elegido y
    verificar lo montado es como se llego a tener seis piezas descritas contra
    un texto que ya no existia.
    """
    from servicios import Pieza

    return Pieza(int(slug.split("-")[1])).texto


def _quitadas(slug):
    """Las etapas que una nota de corte saco de la pieza a proposito.

    Lo mismo que mira `verificar` para no contar como falta lo que alguien
    mando quitar (C-106). Vive aqui tambien porque las dos preguntas son la
    misma: **una etapa ausente por decision no es una etapa ausente por falta**.
    """
    import re as _re

    try:
        c = sqlite3.connect(BASE)
        filas = c.execute(
            "select que from revision where video_id = (select id from video where slug = ?) and accion='cortar'"
            " and estado='aplicada' and regla='seccion que sobra'", (slug,)).fetchall()
        c.close()
    except Exception:                              # noqa: BLE001
        return set()
    out = set()
    for (q,) in filas:
        for b in _re.findall(r"e(\d+)", q or ""):
            out.add(int(b))
    return out


def escenas_por_describir(reels=None, rehacer=False):
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    donde = ""
    args = []
    if reels:
        donde = " and v.slug in (%s)" % ",".join("?" * len(reels))
        args = [f"reel-{int(r):02d}" for r in reels]
    # **Sin filtro en SQL.** Antes se excluia aqui toda etapa ya descrita, y por
    # eso una descripcion caducada no se volvia a pedir: el paso decia «nada que
    # describir» y la puerta paraba la pieza sin que nadie supiera que faltaba.
    # Ahora se traen todas y se descartan abajo las que siguen hablando de su
    # texto — que es una comparacion de textos y no cabe en el WHERE.
    filas = con.execute(f"""
        select v.slug, e.orden, ec.nombre as etapa, es.nombre as estructura,
               e.mensaje_esperado as mensaje, l.texto as libreto,
               (select group_concat(u.texto, ' ') from eleccion el
                  join fragmento f on f.id = el.fragmento_id
                  join fragmento_unidad fu on fu.fragmento_id = f.id
                  join unidad u on u.id = fu.unidad_id
                 where el.etapa_id = e.id) as dicho
          from etapa e
          join video v on v.id = e.video_id
          join estructura es on es.id = e.estructura_id
          left join etapa_canonica ec
                 on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
          left join libreto l on l.video_id = v.id and l.orden = e.orden
         where l.texto is not null {donde}
         order by v.slug, e.orden
    """, args).fetchall()
    con.close()
    # **Lo que se dijo es lo que dice el montaje, no lo que se eligio.** El
    # `dicho` de la base queda como respaldo para la etapa que no tiene toma
    # —la que va a tablero—, porque ahi no hay montaje del que leer.
    # La caducidad se decide comparando textos, que es lo que sabe hacer
    # `sobre_texto`; en SQL no se puede porque el montaje se calcula leyendo la
    # cinta. Se filtra aqui, despues de traer las filas.
    con2 = sqlite3.connect(BASE)
    con2.row_factory = sqlite3.Row
    guardado = {(r["video_slug"], r["etapa_orden"]): (r["sobre_texto"] or "")
                for r in con2.execute(
                    "select v.slug as video_slug, e.etapa_orden, e.sobre_texto"
                    " from escena_desc e join video v on v.id = e.video_id")}
    con2.close()

    salida, textos, avisos = [], {}, {}
    for f in filas:
        d = dict(f)
        if d["slug"] not in textos:
            textos[d["slug"]] = _montaje(d["slug"])
            avisos[d["slug"]] = bordes_sucios(d["slug"])
        d["montaje"] = textos[d["slug"]].get(int(d["orden"]))
        # **Una etapa que no esta en la pieza no se describe.** El listado sale
        # de la estructura —las etapas que el frame define— y no del montaje, y
        # eso es correcto mientras todas esten. Cuando una se corta entera, sin
        # embargo, seguia pidiendose: la puerta de composicion reclamaba una
        # descripcion de la etapa 5 del reel-01 despues de que Jaime la mandara
        # sacar, y la pieza no podia avanzar por describir algo que ya no suena.
        #
        # **Y la diferencia es por que no esta, no que no este.**
        #
        # Una etapa fuera del montaje puede serlo por dos razones opuestas, y
        # solo una de ellas significa «no la describas»:
        #
        # - **Se corto por decision.** Hay una nota de seccion que lo dice. Esa
        #   etapa ya no existe en la pieza y describirla es trabajo perdido.
        # - **Nunca tuvo material.** La frase no esta grabada —reel-04 e5, «el
        #   CRA no ve a un empresario», tiene cero candidatas—. Esa **si** hay
        #   que describirla, porque el frame la necesita y va a tablero: es
        #   justo el caso que `verificar` contempla cuando acepta una etapa «con
        #   toma o con tablero».
        #
        # La primera version miraba si habia `dicho`, y eso mezclaba las dos:
        # dejaba sin describir la etapa que mas lo necesita, la que solo puede
        # existir como tablero.
        if not (d["montaje"] or "").strip() and int(d["orden"]) in _quitadas(d["slug"]):
            continue
        # **Los bordes que hay que mirar van con la etapa**, para que quien
        # compone los resuelva con el texto delante en vez de dejarselos a un
        # umbral.
        d["bordes"] = avisos[d["slug"]].get(int(d["orden"])) or []
        d["repetido"] = [r for r in repetido(d["slug"])
                         if r["etapa"] == int(d["orden"])]
        if not rehacer:
            g = guardado.get((d["slug"], int(d["orden"])))
            if g is not None and " ".join(g.split()) == " ".join(
                    (d["montaje"] or "").split()):
                continue                 # descrita y sigue hablando de este texto
        salida.append(d)
    return salida


def cc_afinado(slug):
    """Cuanto del montaje de esta pieza pasó por el barrido de cuatro pasadas.

    Jaime, sobre para qué existe ese barrido: *«la idea del barrido caro es que
    el agente de IA tenga el CC correcto, y pueda tomar decisiones sobre él,
    eliminar redundancia y componer las escenas»*.

    O sea que **no es un paso de acabado: es la entrada de los pasos de IA**. Un
    agente que compone la escena sobre el CC barato decide sobre un texto que no
    es el que se dijo — y eso ya pasó: cuatro de las seis piezas llegaron a
    montarse con el 0% del montaje afinado, y la revisión leyó «le que» donde la
    cinta dice otra cosa.

    Devuelve, por etapa, la fracción de sus segundos que cae dentro de un tramo
    afinado. 1.0 es entero; 0.0 es que ese trozo nunca se transcribió bien.
    """
    edl_p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(edl_p):
        return {}
    import transcribir

    edl = json.load(open(edl_p, encoding="utf-8"))
    cinta, por = {}, {}
    for (a, b), det in zip(edl["segmentos"], edl["detalle"]):
        t = det.get("toma")
        if t not in cinta:
            ruta = f"work/transcripts/{t}.json"
            try:
                d = json.load(open(ruta, encoding="utf-8"))
                cinta[t] = (d.get("afinado") or [], d.get("segmentos") or [])
            except Exception:                              # noqa: BLE001
                cinta[t] = ([], [])
        af, pal = cinta[t]
        # **Se cuentan PALABRAS, no segundos.** Un tramo con medio segundo de
        # silencio en el borde no llega nunca al 95% por tiempo —ahi no hay nada
        # que afinar— y el paso se quedaba bloqueado pidiendo un barrido que ya
        # habia corrido. Lo que la comprobacion quiere saber es si el texto que
        # el agente va a leer es el bueno, y eso son las palabras.
        dentro = fuera = 0
        for w in pal:
            if not transcribir.suena(w, a, b):
                continue
            if any(w["start"] >= x - 0.001 and w["end"] <= y + 0.001
                   for x, y in af):
                dentro += 1
            else:
                fuera += 1
        d0, t0 = por.get(det.get("beat"), (0, 0))
        por[det.get("beat")] = (d0 + dentro, t0 + dentro + fuera)
    return {b: round(d / t, 3) if t else 1.0 for b, (d, t) in por.items()}


MESES = ("ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic")


def precio_vigente(fecha=None):
    """El escalon de hoy y como se rotula. `None` si ya cerro todo.

    C-28 pedia que el precio saliera **con su fecha de cierre**, y eso se
    cumplia con una cadena escrita a mano que dejo de ser verdad sola. Aqui el
    rotulo se deriva: mientras haya escalon vigente hay precio, y cuando no lo
    hay **no se imprime nada**, que es lo unico honesto una vez cerrada la
    inscripcion.

    Devuelve `vale` ya redactado —«$20 hasta el 4 sep · luego $30 y $40»— porque
    el siguiente escalon es la mitad del argumento: sin el, un precio es una
    tarifa; con el, es una ventana que se cierra.
    """
    hoy = (fecha or datetime.datetime.now().isoformat(timespec="seconds"))
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    filas = [dict(r) for r in con.execute(
        "select * from precio where ancla = 0 order by hasta")]
    con.close()
    if not filas:
        return None
    def _abierta(f):
        # **El ultimo dia cuenta entero.** «hasta el 4 sep» sin hora significa
        # hasta que acabe el 4, no hasta que empiece: comparando cadenas,
        # «2026-09-04T10:00» > «2026-09-04» y la ventana se cerraba un dia
        # antes de lo dicho. Con hora —el cierre del evento— se compara tal cual.
        tope = f["hasta"] if "T" in f["hasta"] else f["hasta"] + "T23:59:59"
        return (not f["desde"] or f["desde"] <= hoy) and hoy <= tope

    vigente = next((f for f in filas if _abierta(f)), None)
    if not vigente:
        return None
    luego = [f["importe"] for f in filas if f["hasta"] > vigente["hasta"]]
    d = vigente["hasta"][:10].split("-")
    cierra = f"{int(d[2])} {MESES[int(d[1]) - 1]}"
    vale = f"${vigente['importe']} hasta el {cierra}"
    if luego:
        vale += " · luego " + " y ".join(f"${x}" for x in luego)
    return {"importe": vigente["importe"], "hasta": vigente["hasta"],
            "vale": vale, "luego": luego}


# Como se declara una pausa que hay que conservar. Va **en el libreto**, que es
# donde Jaime escribe: *«probablemente te deje aviso por libreto»*.
MARCA_PAUSA = ("[pausa]", "(pausa)", "[silencio]", "(silencio)")


def pausas(slug):
    """Las etapas cuyo silencio de entrada **no se recorta**.

    Regla de Jaime, y cierra el tema del aire: *«lo de los silencios tambien
    puede ser aritmetico, no hace falta criterio editorial — excepto cuando
    aporta: por ejemplo antes de una revelacion o de una afirmacion importante,
    siempre y cuando el silencio sea mirando a camara»*.

    O sea: **quitar aire es aritmetica y se hace sola**; conservar una pausa es
    una decision, y las decisiones se declaran. Se declaran donde el las
    escribe, en el texto del libreto, con `[pausa]` delante de la frase que
    quiere que respire. Asi no hace falta ni una tabla nueva ni acordarse de
    nada: la marca viaja con el guion.

    Devuelve `{etapa: motivo}` para las etapas marcadas.
    """
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    filas = con.execute(
        "select l.orden, l.texto from libreto l join video v on v.id = l.video_id"
        " where v.slug = ? order by l.orden", (slug,)).fetchall()
    con.close()
    out = {}
    for f in filas:
        t = (f["texto"] or "")
        for m in MARCA_PAUSA:
            if m in t.lower():
                i = t.lower().index(m)
                out[f["orden"]] = t[i:i + 90].strip()
                break
    return out


def onda(slug):
    """La curva emocional de la pieza, etapa por etapa. **No decide: dibuja.**

    Regla de Jaime, y es la que ordena la seleccion entera:

    > *«El efecto que buscamos es mas parecido a una onda: arriba, luego abajo,
    > luego arriba otra vez. En la seleccion hay una narrativa emocional, y es la
    > que nos dice cual fragmento es el mejor.»* Y la vara de si va o no va:
    > *«si hablo de muerte no quiero estar cagado de la risa; si hablo de futuro
    > no quiero sonar como un desesperado»*.

    Devuelve por etapa la `intensidad` —cuanta emocion, sin signo—, la `altura`
    —hacia donde, en semitonos: negativo grave, positivo arriba—, la
    `velocidad`, y el texto. Con eso se ve de un vistazo si la pieza hace una
    onda o si baja y se queda abajo.

    **Lo que no hace es decir cual deberia ser la altura de cada etapa.** Eso
    depende de que se este diciendo ahi, y saberlo es leer la frase — no es
    aritmetica. El detector apunta; quien monta decide.

        python scripts/consulta.py onda '["reel-01"]'
    """
    import beats
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    porb, cache = {}, {}
    for (a, b), d in zip(edl["segmentos"], edl["detalle"]):
        porb.setdefault(d.get("beat"), {"tramos": [], "etapa": d.get("etapa"),
                                        "toma": d.get("toma")})
        porb[d.get("beat")]["tramos"].append((a, b))
    out = []
    for beat in sorted(x for x in porb if x is not None):
        v = porb[beat]
        toma = v["toma"]
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        pal = cache[toma]
        tot = sum(y - x for x, y in v["tramos"]) or 1.0
        acc = {"intensidad": 0.0, "altura": 0.0, "velocidad": 0.0}
        for x, y in v["tramos"]:
            m = beats.intensidad(toma, x, y, pal) or {}
            peso = (y - x) / tot
            for k in acc:
                acc[k] += peso * float(m.get(k) or 0.0)
        out.append({
            "etapa": beat, "titulo": v["etapa"],
            "intensidad": round(acc["intensidad"], 2),
            "altura": round(acc["altura"], 2),
            "velocidad": round(acc["velocidad"], 2),
            "tibio": acc["intensidad"] < 1.2,
            "texto": " ".join(w["text"] for x, y in v["tramos"] for w in pal
                              if transcribir.suena(w, x, y))[:120],
        })
    return out


def cruces(slug):
    """Lo que se repite **a los dos lados de una costura**, sin cortarlo.

    Tercer sitio de la regla que el proyecto tiene escrita —dentro de la
    ventana, cruzando el corte, y el mismo dato en dos etapas— y el unico donde
    la aritmetica no llega. `depurar` lo cortaba solo, hasta la palabra repetida
    incluida, y esa palabra puede ser la unidad de dos cifras distintas: en
    reel-01 e7 la cola decia «550 dolares, semanales» y la cabeza «Esta semana
    el bootcamp esta en 20 dolares», y el paso se llevo el precio de la oferta.

    Saber si eso es redundancia o son dos datos exige entender la frase. Asi que
    aqui **se apunta**: la etapa, lo que se oye a cada lado, y hasta donde
    cortaria la regla si se aplicara. Lo resuelve quien compone, que tiene el
    texto de las dos etapas delante.

        python scripts/consulta.py cruces '["reel-01"]'
    """
    import depurar
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    out = []
    pares = list(zip(edl["segmentos"], edl["detalle"]))
    for ((a0, b0), d0), ((a1, b1), d1) in zip(pares, pares[1:]):
        toma = d1.get("toma") or d0.get("toma")
        try:
            pal = transcribir.exigir(toma)["segmentos"]
        except SystemExit:
            continue
        nuevo = depurar.cruza_el_corte(pal, (a0, b0), (a1, b1))
        if nuevo is None:
            continue
        out.append({
            "etapa": d1.get("beat"),
            "cola": " ".join(w["text"] for w in pal
                             if transcribir.suena(w, a0, b0))[-70:],
            "repite": " ".join(w["text"] for w in pal
                               if transcribir.suena(w, a1, nuevo)),
            "cortaria_hasta": nuevo,
        })
    return out


def brolls(minimo=2.0, maximo=8.0, cintas=None):
    """Los tramos donde el esta en cuadro y **no habla**. Material de transicion.

    Regla de Jaime, y anade un recurso que ya estaba grabado y no se usaba:

    > *«Otra forma de hacer transiciones es hacer B-rolls con pedazos del video
    > donde yo salgo en silencio, leyendo o haciendo algo; mostrar un poco el
    > proceso, durante un par de segundos, luego continuar. Dar espacio
    > intencional a dos secciones diferentes, o dar el espacio para pensar
    > cuando algo importante se dijo.»*

    Son los huecos del transcript: si entre dos palabras hay dos segundos, ahi
    la camara siguio grabando y el seguia delante. No hace falta grabar nada
    nuevo — hay 149 huecos de dos segundos o mas en las siete cintas.

    Dos usos, y los dos son de ritmo, no de relleno:

    - **Entre dos secciones**, para que no se pisen.
    - **Despues de algo importante**, para dejarlo caer.

    Un B-roll que no hace ninguna de las dos cosas es tiempo muerto, y esta
    pieza vive de que no sobre nada.
    """
    import glob

    rutas = ([f"work/transcripts/{c}.json" for c in cintas] if cintas
             else sorted(glob.glob("work/transcripts/*.json")))
    out = []
    for r in rutas:
        if not os.path.exists(r):
            continue
        d = json.load(open(r, encoding="utf-8"))
        ws = d.get("segmentos") or []
        for a, b in zip(ws, ws[1:]):
            hueco = b["start"] - a["end"]
            if hueco < minimo:
                continue
            # Se corta a `maximo`: un plano mudo largo deja de ser transicion.
            out.append({"toma": d["toma"],
                        "desde": round(a["end"] + 0.15, 2),
                        "hasta": round(min(b["start"] - 0.15,
                                           a["end"] + maximo), 2),
                        "dura": round(min(hueco, maximo) - 0.3, 2),
                        "antes": a["text"], "despues": b["text"]})
    return sorted(out, key=lambda x: -x["dura"])


def abanico(frase, cintas=None, tope=12):
    """Dónde está dicha esa frase **en todo el material**, y cómo de bien.

    Regla de Jaime, y ensancha el abanico que ya usábamos: *«usualmente se
    repite más de dos veces… incluso a veces se repite en otro video»*. Así que
    la mejor toma de una frase **no tiene por qué estar en la cinta de esa
    pieza**: puede estar en la de otra, dicha entera y con más entrega.

    Ya pasó y se resolvió a mano: el «virtual» que le faltaba al reel 1 estaba
    en la cinta del reel 2. Esto lo convierte en una consulta.

    Devuelve cada aparición con su cinta, sus segundos, lo que se oye alrededor
    y su intensidad —la entrega, sin signo—, **ordenadas de mejor a peor**. No
    decide: da material para decidir.

        python scripts/consulta.py abanico '["el 21 de septiembre"]'
    """
    import glob
    import re
    import unicodedata

    import transcribir

    def norm(t):
        t = unicodedata.normalize("NFD", (t or "").lower())
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        return re.findall(r"[a-z0-9]+", t)

    buscada = norm(frase)
    if not buscada:
        return []
    rutas = ([f"work/transcripts/{c}.json" for c in cintas] if cintas
             else sorted(glob.glob("work/transcripts/*.json")))
    out = []
    for r in rutas:
        if not os.path.exists(r):
            continue
        d = json.load(open(r, encoding="utf-8"))
        ws = d.get("segmentos") or []
        pal = [(p, w) for w in ws for p in norm(w["text"])]
        for i in range(len(pal) - len(buscada) + 1):
            if [p for p, _ in pal[i:i + len(buscada)]] != buscada:
                continue
            a0 = pal[i][1]["start"]
            b0 = pal[i + len(buscada) - 1][1]["end"]
            ctx = " ".join(w["text"] for _, w in pal[max(0, i - 6):i + len(buscada) + 6])
            out.append({"toma": d["toma"], "desde": round(a0, 2),
                        "hasta": round(b0, 2), "contexto": ctx,
                        "intensidad": None})
    # La entrega solo de las que hay, y con tope: medir es lo caro.
    try:
        import beats

        for x in out[:tope]:
            m = beats.intensidad(x["toma"], x["desde"], x["hasta"]) or {}
            if m.get("intensidad") is not None:
                x["intensidad"] = round(float(m["intensidad"]), 2)
    except Exception:                              # noqa: BLE001
        pass
    return sorted(out, key=lambda x: -(x["intensidad"] or -1))


def repetido(slug, n=3):
    """Lo que la pieza dice **dos veces**, y no deberia.

    Regla de Jaime, que es la que separa el enfasis del ruido:

    > *«La redundancia o es explicita en el libreto, o es continua en la
    > grabacion; pero dejar enfasis cada corte no es enfasis sino ruido.»*

    Asi que una repeticion vale cuando el guion la pide —esta dos veces en el
    libreto— y no vale cuando la produjo el montaje. Lo que aparece aqui es lo
    segundo: n-gramas que suenan dos veces en la pieza y una sola vez en el
    libreto.

    Existia `repeticiones.py` y hacia justo esto, pero **no lo llamaba nadie**:
    un paso que depende de que alguien se acuerde no es un paso. Por eso vive
    aqui, lo mira la puerta y lo lee el que compone.
    """
    import re
    import unicodedata

    def norm(t):
        t = unicodedata.normalize("NFD", (t or "").lower())
        t = "".join(c for c in t if unicodedata.category(c) != "Mn")
        return re.findall(r"[a-z0-9]+", t)

    import transcribir

    edl_p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(edl_p):
        return []
    edl = json.load(open(edl_p, encoding="utf-8"))
    cache = {}
    # Las palabras de la pieza, en orden de montaje, cada una con **de que
    # trozo viene**. Ese indice es lo que decide: si las dos veces caen en el
    # mismo trozo, el hablante lo dijo asi de seguido.
    seq = []
    for k, ((a, b), d) in enumerate(zip(edl["segmentos"], edl["detalle"])):
        t = d.get("toma")
        if t not in cache:
            try:
                cache[t] = transcribir.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        for w in cache[t]:
            if transcribir.suena(w, a, b):
                for p in norm(w["text"]):
                    seq.append((p, k, d.get("beat"), w["start"], w["end"], t))
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    lib = {r["orden"]: r["texto"] for r in con.execute(
        "select l.orden, l.texto from libreto l join video v on v.id = l.video_id"
        " where v.slug = ?", (slug,))}
    con.close()
    fuera, gramas = [], {}
    for i in range(len(seq) - n + 1):
        g = " ".join(x[0] for x in seq[i:i + n])
        gramas.setdefault(g, []).append(i)
    for g, sitios in gramas.items():
        if len(sitios) < 2:
            continue
        # **Se repite mas de dos veces, y por eso no se comparan dos: se
        # miden todas.** Jaime: *«usualmente se repite mas de dos veces»*, y esa
        # es la razon de que la cinta sea un abanico — *«se grabo asi para poder
        # escoger una buena entre estas»* (C-81). Elegir «la segunda» seria tan
        # arbitrario como elegir la ultima.
        veces = []
        for k0 in sitios:
            tramo = seq[k0:k0 + n]
            veces.append({
                "empieza": round(tramo[0][3], 2),
                "acaba": round(tramo[-1][4], 2),
                "trozo": tramo[0][1],
                "toma": tramo[0][5],
                "intensidad": None,
            })
        try:
            import beats

            for v in veces:
                m = beats.intensidad(v["toma"], v["empieza"], v["acaba"]) or {}
                v["intensidad"] = (round(float(m["intensidad"]), 2)
                                   if m.get("intensidad") is not None else None)
        except Exception:                          # noqa: BLE001
            pass
        medidas = [v for v in veces if v["intensidad"] is not None]
        beat = seq[sitios[0]][2]
        una_toma = len({v["trozo"] for v in veces}) == 1
        en_libreto = " ".join(norm(lib.get(beat, ""))).count(g) >= len(sitios)

        # **La mejor es la que mas comunica**, que es la vara del proyecto: la
        # entrega, sin signo. Si no se pudo medir ninguna, no se decide aqui.
        mejor = max(medidas, key=lambda v: v["intensidad"]) if medidas else None
        if mejor is not None and len(medidas) > 1:
            segunda = sorted(v["intensidad"] for v in medidas)[-2]
            destaca = (mejor["intensidad"] - segunda) > beats.PASO_VOZ
        else:
            destaca = False

        # Una obligatoria y dos de tres: la toma manda, y ademas o lo pide el
        # libreto o la repeticion sube de verdad la entrega.
        cumple = sum([una_toma, en_libreto, destaca])
        if una_toma and cumple >= 2:
            continue
        if not una_toma:
            motivo = f"se dice {len(sitios)} veces cruzando cortes"
        elif not medidas:
            motivo = f"se dice {len(sitios)} veces y no se pudo medir la entrega"
        elif not destaca:
            motivo = (f"se dice {len(sitios)} veces y ninguna destaca"
                      f" (intensidades {[v['intensidad'] for v in medidas]}):"
                      f" es repetir, no enfatizar")
        else:
            motivo = f"se dice {len(sitios)} veces y el libreto solo la pide una"
        fuera.append({"etapa": beat, "dice": g, "veces": len(sitios),
                      "separadas_por": sitios[1] - sitios[0] - n,
                      "trozos": sorted({v["trozo"] for v in veces}),
                      "motivo": motivo, "en_libreto": en_libreto,
                      "una_toma": una_toma, "tomas": veces,
                      "decide_quien_compone": not medidas,
                      # Cual se queda: la que mas comunica de las medidas.
                      "se_queda": (None if mejor is None else
                                   {"empieza": mejor["empieza"],
                                    "acaba": mejor["acaba"],
                                    "intensidad": mejor["intensidad"]})})
    return fuera


def bordes_sucios(slug):
    """Los bordes que **hay que mirar**, sin decidir nada sobre ellos.

    Regla de Jaime, y corrige lo que yo estaba haciendo: *«la solucion es que el
    detector apunte y tu decidas caso a caso, sin degradar el esfuerzo que
    haces; eso se logra con una revision del guion despues de correr las cuatro
    pasadas, es decir, tu compones despues de que este paso se dio»*.

    Lo que se arregla solo es **aritmetica** y se queda en `costuras.py`: un
    corte no puede caer dentro de una palabra, y dos trozos de la misma cinta no
    pueden pisarse. Eso no exige entender una frase.

    Lo que exige entenderla —si la palabra pegada delante es la cabeza que falta
    o la cola de otra idea, si el conector del final sobra o le falta el objeto—
    **no se decide con un umbral**. Se apunta aqui y lo resuelve quien compone,
    que para entonces ya tiene el CC de las cuatro pasadas delante.

    Devuelve, por etapa, la lista de avisos con lo que se oye a cada lado.
    """
    import transcribir

    edl_p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(edl_p):
        return {}
    edl = json.load(open(edl_p, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    cache, por = {}, {}
    colgantes = {"y", "o", "pero", "porque", "que", "de", "del", "la", "el",
                 "los", "las", "un", "una", "en", "a", "al", "con", "para",
                 "por", "su", "se", "le", "lo", "es", "sin"}
    for i, ((a, b), d) in enumerate(zip(segs, det)):
        t = d.get("toma")
        if t not in cache:
            try:
                cache[t] = transcribir.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        ws = cache[t]
        if not ws:
            continue
        dentro = [w for w in ws if transcribir.suena(w, a, b)]
        antes = [w for w in ws if w["end"] <= a + 0.001]
        avisos = []
        if antes and dentro and a - antes[-1]["end"] < 0.20:
            # ¿esa palabra esta en la pieza? si no, la entrada se le pega
            suya = any(det[j].get("toma") == t
                       and transcribir.suena(antes[-1], segs[j][0], segs[j][1])
                       for j in range(len(segs)))
            if not suya:
                avisos.append(
                    {"donde": "entrada", "en": round(a, 2),
                     "pegada_a": " ".join(w["text"] for w in antes[-4:]),
                     "entra": " ".join(w["text"] for w in dentro[:6])})
        if dentro and dentro[-1]["text"].strip(".,¿?¡!").lower() in colgantes:
            sigue = [w for w in ws if w["start"] >= b - 0.001][:5]
            avisos.append(
                {"donde": "salida", "en": round(b, 2),
                 "acaba_en": " ".join(w["text"] for w in dentro[-5:]),
                 "seguia": " ".join(w["text"] for w in sigue)})
        if avisos:
            por.setdefault(d.get("beat"), []).extend(avisos)
    return por


def guardar_escena(slug, orden, d):
    """Guarda la descripción. `ninguno` se guarda como NULL, no como texto.

    **Y guarda el texto que la descripción describe**, que es lo que permite
    saber después si caducó. Lo deriva aquí y no lo recibe: un campo que el
    llamador puede olvidar es un campo que se olvida — `sobre_texto` llevaba
    54 filas escritas a mano y ninguna línea de código que lo mantuviera, así
    que la puerta comparaba contra lo que alguien tecleó una vez.
    """
    sobre = (_montaje(slug) or {}).get(int(orden))
    con = sqlite3.connect(BASE)
    con.execute(
        "insert into escena_desc (video_id, etapa_orden, que_pasa, emocion,"
        " componente, grafico, color, sonido, plano, trato, trato_porque,"
        " prioridad, integridad, remedio,"
        " sobre_texto, quien, fecha)"
        " values ((select id from video where slug = ?),?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " on conflict(video_id, etapa_orden) do update set"
        " que_pasa=excluded.que_pasa, emocion=excluded.emocion,"
        " componente=excluded.componente, grafico=excluded.grafico,"
        " color=excluded.color, sonido=excluded.sonido, plano=excluded.plano,"
        " trato=excluded.trato, trato_porque=excluded.trato_porque,"
        " prioridad=excluded.prioridad,"
        " integridad=excluded.integridad, remedio=excluded.remedio,"
        " sobre_texto=excluded.sobre_texto,"
        " quien=excluded.quien, fecha=excluded.fecha",
        (slug, int(orden), d["que_pasa"], d.get("emocion"),
         None if d.get("componente") in (None, "ninguno") else d["componente"],
         d.get("grafico"), d.get("color"), d.get("sonido"), d.get("plano"),
         d.get("trato"), d.get("trato_porque"), d.get("prioridad"),
         d.get("integridad"), d.get("remedio"),
         sobre,
         # `quien` decia «gemini» y esa via se descarto —*«no quiero a
         # Google»*—, asi que el campo mentia sobre quien decidio.
         d.get("quien", "cli"),
         datetime.datetime.now().isoformat(timespec="seconds")))
    # **La enmienda es otra tabla, y se retira si deja de venir.** Vive aparte
    # porque no describe la escena: corrige un dato que se dice —«dice comercio,
    # es Finanzas»— y solo aparece en el 11% de las etapas. Y el `delete`
    # importa tanto como el `insert`: una descripcion nueva sin `corrige` que
    # dejara la vieja seguiria pintando en pantalla una correccion que el paso
    # anterior ya desecho.
    c = d.get("corrige") or {}
    if c.get("dice") and c.get("es"):
        con.execute(
            "insert into enmienda (video_id, etapa_orden, dice, es, fecha)"
            " values ((select id from video where slug = ?),?,?,?,?)"
            " on conflict(video_id, etapa_orden) do update set"
            " dice=excluded.dice, es=excluded.es, fecha=excluded.fecha",
            (slug, int(orden), c["dice"], c["es"],
             datetime.datetime.now().isoformat(timespec="seconds")))
    else:
        con.execute("delete from enmienda where etapa_orden = ? and video_id ="
                    " (select id from video where slug = ?)", (int(orden), slug))
    con.commit()
    con.close()
    return {"ok": True}


if __name__ == "__main__":
    fn = {"escenas_por_describir": escenas_por_describir,
          "cc_afinado": cc_afinado,
          "bordes_sucios": bordes_sucios,
          "repetido": repetido,
          "abanico": abanico,
          "brolls": brolls,
          "cruces": cruces,
          "onda": onda,
          "pausas": pausas,
          "precio_vigente": precio_vigente,
          "guardar_escena": guardar_escena}[sys.argv[1]]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    print(json.dumps(fn(*args), ensure_ascii=False))
