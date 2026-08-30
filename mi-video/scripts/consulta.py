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


def escenas_por_describir(reels=None, rehacer=False):
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    donde = ""
    args = []
    if reels:
        donde = " and v.slug in (%s)" % ",".join("?" * len(reels))
        args = [f"reel-{int(r):02d}" for r in reels]
    if not rehacer:
        donde += (" and not exists (select 1 from escena_desc d"
                  " where d.video_slug = v.slug and d.etapa_orden = e.orden)")
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
    salida, textos, avisos = [], {}, {}
    for f in filas:
        d = dict(f)
        if d["slug"] not in textos:
            textos[d["slug"]] = _montaje(d["slug"])
            avisos[d["slug"]] = bordes_sucios(d["slug"])
        d["montaje"] = textos[d["slug"]].get(int(d["orden"]))
        # **Los bordes que hay que mirar van con la etapa**, para que quien
        # compone los resuelva con el texto delante en vez de dejarselos a un
        # umbral.
        d["bordes"] = avisos[d["slug"]].get(int(d["orden"])) or []
        d["repetido"] = [r for r in repetido(d["slug"])
                         if r["etapa"] == int(d["orden"])]
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
        "insert into escena_desc (video_slug, etapa_orden, que_pasa, emocion,"
        " componente, grafico, color, sonido, plano, trato, trato_porque,"
        " prioridad, integridad, remedio, corrige_dice, corrige_es,"
        " sobre_texto, quien, fecha)"
        " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " on conflict(video_slug, etapa_orden) do update set"
        " que_pasa=excluded.que_pasa, emocion=excluded.emocion,"
        " componente=excluded.componente, grafico=excluded.grafico,"
        " color=excluded.color, sonido=excluded.sonido, plano=excluded.plano,"
        " trato=excluded.trato, trato_porque=excluded.trato_porque,"
        " prioridad=excluded.prioridad,"
        " integridad=excluded.integridad, remedio=excluded.remedio,"
        " corrige_dice=excluded.corrige_dice, corrige_es=excluded.corrige_es,"
        " sobre_texto=excluded.sobre_texto,"
        " quien=excluded.quien, fecha=excluded.fecha",
        (slug, int(orden), d["que_pasa"], d.get("emocion"),
         None if d.get("componente") in (None, "ninguno") else d["componente"],
         d.get("grafico"), d.get("color"), d.get("sonido"), d.get("plano"),
         d.get("trato"), d.get("trato_porque"), d.get("prioridad"),
         d.get("integridad"), d.get("remedio"),
         (d.get("corrige") or {}).get("dice"), (d.get("corrige") or {}).get("es"),
         sobre,
         # `quien` decia «gemini» y esa via se descarto —*«no quiero a
         # Google»*—, asi que el campo mentia sobre quien decidio.
         d.get("quien", "cli"),
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    return {"ok": True}


if __name__ == "__main__":
    fn = {"escenas_por_describir": escenas_por_describir,
          "cc_afinado": cc_afinado,
          "bordes_sucios": bordes_sucios,
          "repetido": repetido,
          "abanico": abanico,
          "pausas": pausas,
          "precio_vigente": precio_vigente,
          "guardar_escena": guardar_escena}[sys.argv[1]]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    print(json.dumps(fn(*args), ensure_ascii=False))
