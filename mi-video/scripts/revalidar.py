"""Re-calificar lo elegido después del paso caro, y pasar a la siguiente si cae.

Es el bucle que Jaime describió entero:

    *«Seguimos calificando con entrega emocional, ése es nuestro criterio de
    selección. Si después de las cuatro pasadas baja su puntaje, o es demasiado
    fragmentado, si no hay ritmo y si no hay cambio de tono, entonces escogemos
    el siguiente»* — *«hasta encontrar el mejor costo/beneficio»*.

Y quién decide:

    *«Por eso es importante que el LLM sea el que lo revisa también, y por eso
    define si pasa o no basándose en los tres elementos pero sobre todo en la
    intención comunicativa: si el mensaje llega muy roto, pues no llegó.»*

## Los números no deciden, informan

Aquí se miden cuatro cosas sobre el tramo ya afinado, y **ninguna vota sola**:

    voz         recorrido de F0 en semitonos — la entrega emocional
    tono        cuánto se MUEVE la voz, st/s — leer plano da bajo aunque el
                recorrido sea ancho, que es la trampa que `voz` no ve
    ritmo       variación de la velocidad del habla — una lectura mantiene el
                mismo paso de principio a fin
    continuidad qué fracción de las costuras respeta una frontera de idea

El veredicto lo da el LLM leyendo **el texto** con esos números al lado, porque
la pregunta final no es numérica: *¿llega la intención?*. Un tramo con buenos
números y el mensaje partido no pasa, y uno con números mediocres que dice lo
que tiene que decir, sí.

## El coste manda cuándo parar

Cada intento cuesta un afinado con el modelo bueno. Así que no se busca «la que
pase», se busca **el mejor coste/beneficio**: se prueban como mucho `INTENTOS`
candidatas, se guarda siempre la mejor vista, y si una tanda no mejora a la
mejor, se para y se queda ésa. Seguir tirando candidatas dejó la etapa 2 del
reel 1 peor de lo que estaba — ya pasó una vez (C-65).

    python scripts/revalidar.py 1          # el dossier del reel 1
    python scripts/revalidar.py --json 1   # para el paso de IA
"""
import argparse
import json
import os
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import depurar  # noqa: E402
import transcribir  # noqa: E402
import rutas  # noqa: E402

# Cuántas candidatas se prueban por etapa antes de quedarse con la mejor vista.
# Tres es el punto donde el afinado deja de pagarse: la cuarta rara vez mejora y
# cuesta lo mismo que las tres primeras juntas.
INTENTOS = 3

# Suelos de referencia. **No son puertas** — son lo que el dossier marca para que
# el LLM sepa dónde mirar. Medidos sobre lo elegido de estas seis cintas.
#
# **El suelo de «plano» va sobre la intensidad, no sobre el recorrido de F0.**
# Regla de Jaime, y es la segunda vez que hace falta aplicarla: *«ojo, no hay
# emociones positivas o negativas: más emoción es más tristeza tanto como más
# rabia tanto como más alegría»*. El recorrido de F0 premia lo animado —la
# tristeza baja el tono, ralentiza y estrecha el rango—, así que un suelo puesto
# ahí marca como floja la entrega grave.
#
# `seleccionar.py` ya recalibró esto en su día —de 4,3 a 3,4, mismo percentil,
# otra escala— y aquí se quedó el número viejo. Medido sobre los 51 beats
# montados: con el suelo de `voz` a 4,3 se marcaban **19 de 51**, y los que se
# marcaban eran los graves —«eso suele ser una pérdida silenciosa» de reel-06,
# el arranque de reel-05— mientras los cinco tramos de verdad tibios (intensidad
# 0,37 a 1,04) pasaban limpios **porque tenían mucho recorrido de F0**. El suelo
# no estaba sesgado: estaba casi invertido.
#
# 1,2 es el p15 de la intensidad en esa población, el mismo percentil con el que
# se calibró `seleccionar`. Marca 7 de 51, y son los tibios.
SUELO = {"intensidad": 1.2, "ritmo": 0.30, "continuidad": 0.5}


def _mide(v, dec):
    """Redondea una medida, y deja `None` cuando no la hubo.

    `expresividad`, `cambio_de_tono` y `ritmo` devuelven `None` para decir
    **no medido**. Antes devolvian `0.0`, que es indistinguible de «medido
    y plano» — y eso estaba en 18 sitios, cuatro de ellos comparaciones.

    Aqui no se convierte a cero: se guarda el `None`. Quien lo lea vera que
    no hay medida, que es la verdad, en vez de un cero que miente.
    """
    return None if v is None else round(float(v), dec)


def medir(toma, palabras, tramos):
    """Las cuatro medidas sobre los tramos ya afinados de una etapa."""
    a = min(x for x, _ in tramos)
    b = max(y for _, y in tramos)
    rotas, costuras, esquirlas = depurar.continuidad(palabras, sorted(tramos))
    # La intensidad se mide sobre lo que se conserva —ver `entrega`— y entra en
    # el dossier porque es la medida con la que se juzga si algo transmite. Sin
    # ella aquí, `flojo` no podía mirarla y `marca` la leía como cero.
    ent = entrega(toma, palabras, sorted(tramos))
    return {
        "desde": round(a, 2),
        "hasta": round(b, 2),
        "intensidad": ent["intensidad"],
        # **`None` es «no medido» y se guarda como tal.** Redondearlo
        # reventaba el paso entero; convertirlo en 0,0 seria peor, porque
        # «no lo oyo nadie» pasaria por «lo oi y esta plano».
        "voz": _mide(beats.expresividad(toma, a, b), 2),
        "tono": _mide(beats.cambio_de_tono(toma, a, b), 1),
        "ritmo": _mide(beats.ritmo(palabras, a, b), 2),
        "continuidad": (round(1 - rotas / costuras, 2) if costuras else 1.0),
        "trozos": len(tramos),
        "esquirlas": esquirlas,
    }


def saltos(toma, pal, tramos, antes=None):
    """Lo que se oye AL CRUZAR cada costura de la etapa: tono y ritmo.

    Jaime, definiendo esta segunda valoracion: *«cuando vemos si los cortes
    rompen los mensajes o si el cambio de ritmo hace el segmento contradictorio
    o poco armonico, pues revisa los candidatos con sus puntuaciones y ahi
    decide si cambia de candidato del segmento o si lo mantiene»*.

    `continuidad` ya decia si la costura cae entre ideas —eso es el mensaje—,
    pero no decia **como suena el cruce**. Y son cosas distintas: dos tramos
    pueden unirse en una frontera limpia de sentido y aun asi sonar a pegote
    porque uno acaba grave y despacio y el siguiente arranca agudo y disparado.

    `antes` es el final del beat anterior, para medir tambien la costura de
    entrada: la etapa no empieza en el vacio.
    """
    out = []
    ts = sorted(tramos)
    pares = []
    if antes:
        pares.append((antes[0], antes[1], toma, ts[0][0], "entrada"))
    for (x1, y1), (x2, _) in zip(ts, ts[1:]):
        pares.append((toma, y1, toma, x2, "interna"))
    for ta, fin, tb, ini, donde in pares:
        try:
            sa = beats.salto(ta, fin, tb, ini, pal)
        except Exception:                          # noqa: BLE001
            continue
        if sa.get("tono") is None and sa.get("ritmo") is None:
            continue
        out.append({"donde": donde, "en": round(ini, 2),
                    "tono": sa.get("tono"), "ritmo": sa.get("ritmo")})
    return out


def entrega(toma, pal, tramos):
    """Intensidad y recorrido de F0 **sobre lo que se conserva**.

    Dos arreglos, y los dos los encontro la revision adversarial:

    - **`medir` mide el SPAN**, de la primera marca a la ultima, asi que incluye
      lo que el montaje quito. En reel-05 e2 el span es de 39,3 s para 19,2 s
      conservados: el 51% de lo medido no esta en la pieza. Aqui se mide tramo a
      tramo y se pondera por duracion.
    - **`marca` creia leer `intensidad` de `medir`, que nunca la devuelve.** El
      `or 0.0` la dejaba en cero y la marca era solo el recorrido de F0 partido
      por cuatro — justo la vara que Jaime corrigio, porque premia lo animado y
      puntua la tristeza como plana. Aqui se calcula de verdad.
    """
    tot = sum(y - x for x, y in tramos)
    if tot <= 0:
        return {"intensidad": 0.0, "voz": 0.0}
    inten = exp = 0.0
    for x, y in tramos:
        peso = (y - x) / tot
        try:
            i = beats.intensidad(toma, x, y, pal) or {}
            inten += peso * float(i.get("intensidad") or 0.0)
        except Exception:                          # noqa: BLE001
            pass
        try:
            exp += peso * float(beats.expresividad(toma, x, y) or 0.0)
        except Exception:                          # noqa: BLE001
            pass
    return {"intensidad": round(inten, 3), "voz": round(exp, 2)}


def marca(m, sal=None):
    """**La marca de un segmento: una sola cifra, para poder compararla.**

    Jaime: *«la IA debe tener una funcion que re evalue el segmento montado por
    la IA, luego compare las marcas con las de los demas, y si es muy cercana o
    menor que vuelva a evaluar otro segmento»*. Comparar exige un numero, y
    hasta ahora habia cinco medidas sueltas: se podia describir un segmento,
    no ordenarlo frente a otro.

    Se construye con lo que ya decidio el proyecto, sin inventar pesos nuevos:

    - **La entrega**, que es el criterio: `intensidad` —la distancia a la
      neutralidad de esa cinta, sin signo— mas un cuarto del recorrido de F0.
      Es exactamente lo que ya guarda `candidato.voz_st`, asi que la marca de un
      montaje y la de una candidata **se miden con la misma vara**.
    - **Menos lo que se oye del corte.** Una costura que cruza con mas de
      `beats.SALTO_TONO` semitonos o `beats.SALTO_RITMO` palabras por segundo se
      nota; cada una descuenta un escalon de voz (`beats.PASO_VOZ`), que es la
      unidad con la que este proyecto mide «diferencia que se nota».

    No entra `continuidad` aqui: eso es sentido, no sonido, y lo juzga el LLM
    leyendo el texto. Mezclarlo en el numero seria decidir por el.
    """
    base = float(m.get("intensidad") or 0.0) + float(m.get("voz") or 0.0) / 4.0
    duras = 0
    for x in (sal or []):
        t, r = x.get("tono"), x.get("ritmo")
        if (t is not None and abs(t) > beats.SALTO_TONO) or \
           (r is not None and abs(r) > beats.SALTO_RITMO):
            duras += 1
    return round(base - duras * beats.PASO_VOZ, 3)


def _toma_montada(slug, beat):
    """De que cinta es esa etapa **en el montaje**, segun el EDL.

    Es la fuente de la verdad para medir: el EDL es lo que se oye. Devuelve
    `None` si la etapa no esta en el corte, y ahi si toca preguntar a la base.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return None
    try:
        edl = json.load(open(ruta, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for d in edl.get("detalle") or []:
        if d.get("beat") == beat and d.get("toma"):
            return d["toma"]
    return None


def evaluar(slug, beat, tramos, toma=None, excluir=None, contra=None):
    """Re-evalua **el segmento que monto la IA** y lo pone frente a las demas.

    Esta es la funcion que pidio Jaime. Recibe un montaje —una o varias tramos,
    que es lo que la IA propone cuando mueve una costura o cambia de candidata—
    y devuelve sus marcas y su veredicto contra las candidatas de esa etapa.

    El veredicto usa el suelo de ruido del propio detector: por debajo de
    `beats.PASO_VOZ` —un cuarto de semitono— la diferencia **no es una
    diferencia**, es el error de medida. De ahi salen los tres casos que el
    describio:

        mejor    gana por encima del ruido: se queda
        cercana  la diferencia cabe en el ruido: hay que evaluar otra
        peor     pierde: hay que evaluar otra

    Y «cercana» cuenta como no-gana **a proposito**: si dos opciones empatan
    dentro del error, quedarse con la que ya estaba es quedarse por inercia, no
    por criterio.
    """
    # **La cinta del montaje la dice el EDL, no `eleccion`.** Son dos cosas
    # distintas en cuanto `fijar` cambia una etapa: `eleccion` guarda lo que se
    # eligio, el EDL lo que suena. Medir los segundos del montaje contra las
    # palabras de otra cinta no devuelve un numero peor: devuelve el numero de
    # otra frase, y el veredicto que sale de ahi no es utilizable — ni siquiera
    # se nota, porque llega con la misma pinta que uno bueno.
    #
    # Medido en las seis: reel-01 b3 y b8, reel-03 b2, b6 y b7, reel-06 b7 y b9
    # se evaluaban contra la cinta que no era. `dossier()` ya la tomaba del EDL;
    # esto es la otra mitad del mismo dato, que se habia quedado atras.
    toma = toma or _toma_montada(slug, beat)
    if not toma:
        con = basedatos.abrir("ads/decisiones.db")
        con.row_factory = sqlite3.Row
        r = con.execute(
            "select t.nombre from etapa e join video v on v.id = e.video_id"
            " join eleccion el on el.etapa_id = e.id"
            " join fragmento f on f.id = el.fragmento_id"
            " join toma t on t.id = f.toma_id"
            " where v.slug = ? and e.orden = ?", (slug, beat)).fetchone()
        con.close()
        toma = r["nombre"] if r else None
    if not toma:
        return {"error": f"{slug} e{beat}: no se sabe de que toma es"}
    try:
        pal = transcribir.exigir(toma)["segmentos"]
    except SystemExit as e:
        return {"error": str(e)}
    tramos = [tuple(map(float, t)) for t in tramos]
    m = medir(toma, pal, tramos)
    sal = saltos(toma, pal, tramos)
    mia = marca(entrega(toma, pal, tramos), sal)
    # **Cada candidata se mide con SU cinta**, y el conjunto contra el que se
    # compara es el mismo para todos menos uno mismo. Antes el montaje se
    # excluia del conjunto de las candidatas pero las candidatas no se excluian
    # del suyo: una candidata podia salir «mejor» siendo peor que el montaje al
    # que sustituia. Reproducido: montaje 2,0 -> candidata 1,9 declarada mejor.
    cache = {toma: pal}
    otras = []
    for c in candidatas(slug, beat):
        if excluir is not None and c["puesto"] == excluir:
            continue
        tc = c.get("toma") or toma
        if tc not in cache:
            try:
                cache[tc] = transcribir.exigir(tc)["segmentos"]
            except SystemExit:
                cache[tc] = []
        mo = entrega(tc, cache[tc], [(c["desde"], c["hasta"])])
        otras.append({**c, "marca": marca(mo)})
    if contra is not None:
        # **Y contra el montaje al que sustituiria.** Se pasa ya medido porque
        # el montaje puede ser de otra cinta que la candidata, y medirlo aqui
        # con las palabras equivocadas es el mismo fallo por otra puerta.
        otras.append({"puesto": 0, "quien": "montaje actual", "marca": contra})
    mejor = max((o["marca"] for o in otras), default=None)
    if mejor is None:
        # **Sin nada con que comparar no hay veredicto.** Devolvia «mejor» y eso
        # adoptaba sola cualquier etapa con una unica candidata, despues de
        # pagarle el barrido caro.
        veredicto, margen = "unica", None
    else:
        margen = round(mia - mejor, 3)
        veredicto = ("mejor" if margen > beats.PASO_VOZ
                     else "peor" if margen < -beats.PASO_VOZ else "cercana")
    return {"beat": beat, "tramos": [list(t) for t in tramos],
            "marcas": m, "saltos": sal, "marca": mia,
            "texto": " ".join(w["text"] for x, y in sorted(tramos)
                              for w in pal if transcribir.suena(w, x, y)),
            "frente_a": otras, "veredicto": veredicto, "margen": margen}


def flojo(m):
    """Qué medidas quedan por debajo de su suelo. Informa, no descalifica.

    **Lo que no se midió no está flojo: está sin medir.** El `m.get(k, 0)` daba
    por floja cualquier medida ausente, y desde que «no medido» es `None` en vez
    de `0.0` ni siquiera comparaba: reventaba el paso entero. Las dos formas del
    mismo error — tratar la falta de dato como un dato malo.

    Quien no se midió no aparece en la lista, y eso es lo honesto: decir que una
    etapa va floja de tono cuando nadie le midió el tono es inventarse un
    diagnóstico.
    """
    return [k for k, v in SUELO.items()
            if m.get(k) is not None and m[k] < v]


def candidatas(slug, beat, cuantas=3):
    """Las otras opciones de esa etapa, con su texto y su puntuacion.

    Jaime, definiendo el contrato: *«por contrato recibes la informacion de cada
    escena y el contexto de las otras candidatas, para saber cual escoges»*.
    Elegir sin ver las alternativas no es elegir — y hasta ahora el dossier
    mandaba la elegida sola, asi que lo unico que se podia contestar era «esta
    vale o no vale», nunca «esta otra vale mas».

    Tres, que es el tope del embudo: *«si ninguna de las tres candidatas es, pues
    la que mejor puntaje tenga»*.
    """
    con = basedatos.abrir("ads/decisiones.db")
    con.row_factory = sqlite3.Row
    filas = con.execute(
        "select c.puesto, c.puntuacion, c.voz_st, f.desde, f.hasta,"
        "       f.id fragmento_id, t.nombre toma"
        " from candidato c join etapa e on e.id = c.etapa_id"
        " join video v on v.id = e.video_id"
        " join fragmento f on f.id = c.fragmento_id"
        " join toma t on t.id = f.toma_id"
        " where v.slug = ? and e.orden = ? order by c.puesto limit ?",
        (slug, beat, cuantas)).fetchall()
    con.close()
    out = []
    for r in filas:
        try:
            pal = transcribir.exigir(r["toma"])["segmentos"]
        except SystemExit:
            pal = []
        txt = " ".join(w["text"] for w in pal
                       if transcribir.suena(w, r["desde"], r["hasta"]))
        out.append({"puesto": r["puesto"],
                    # **Cada candidata trae SU cinta.** Sin esto, `evaluar`
                    # medía a todas con las palabras y el audio del montaje: en
                    # 14 de 53 etapas hay candidatas de mas de una cinta, y el
                    # error medido llegaba a 0,38 — mas que el escalon con el
                    # que se decide (0,25), o sea que cambiaba veredictos.
                    "toma": r["toma"],
                    "fragmento_id": r["fragmento_id"],
                    # **La puntuación puede no estar, y eso no es cero.** Es la
                    # cuarta vez que este patrón rompe algo: hacer representable
                    # el «no medido» obliga a mirar todos los sitios que asumían
                    # un número (C-63 y las dos de hoy).
                    "puntuacion": (round(r["puntuacion"], 3)
                                   if r["puntuacion"] is not None else None),
                    "desde": round(r["desde"], 2), "hasta": round(r["hasta"], 2),
                    "dura": round(r["hasta"] - r["desde"], 1),
                    # **Y hacia donde va, no solo cuanto.** Sin esto la eleccion
                    # entre candidatas era ciega a lo unico que Jaime pide aqui:
                    # *«si hablo de muerte no quiero estar cagado de la risa; si
                    # hablo de futuro no quiero sonar como un desesperado»*.
                    # `intensidad` dice cuanta emocion hay —sin signo, a
                    # proposito—; `altura` y `velocidad` dicen cual es.
                    **_direccion(r["toma"], r["desde"], r["hasta"], pal),
                    "texto": txt[:400]})
    return out


def _direccion(toma, a, b, pal):
    """Altura y velocidad **con signo**, y la intensidad al lado.

    Grave y lento es una emocion; agudo y rapido es otra; y las dos pueden ser
    fuertes. Por eso la magnitud no basta para elegir: hay que saber si el tramo
    va donde el momento del libreto pide que vaya.
    """
    try:
        i = beats.intensidad(toma, a, b, pal) or {}
    except Exception:                              # noqa: BLE001
        return {}
    return {"intensidad": i.get("intensidad"),
            "altura": i.get("altura"),
            "velocidad": i.get("velocidad")}


def afinada(toma, a, b):
    """¿Ese tramo ya paso por el barrido de cuatro pasadas?"""
    try:
        d = transcribir.exigir(toma)
    except SystemExit:
        return False
    dentro = sum(max(0.0, min(b, y) - max(a, x))
                 for x, y in (d.get("afinado") or []))
    return (b - a) <= 0 or dentro / (b - a) >= 0.95


def rondas(slug, beat, tramos=None, limite=INTENTOS, afinar_ok=True):
    """El bucle de Jaime, entero, para una etapa.

    > *«La IA debe tener una funcion que re evalue el segmento montado por la
    > IA, luego compare las marcas con las de los demas, y si es muy cercana o
    > menor que vuelva a evaluar otro segmento, desde la revision con 4
    > pasadas.»*

    Asi que: se mide lo que hay montado; si gana por encima del ruido, se queda.
    Si no, entra la siguiente candidata —**y entra por el barrido caro**, porque
    medir sobre el texto barato es medir otra cosa— y se vuelve a comparar.

    El orden de entrada es por marca, no por puesto: el puesto lo dio la
    seleccion con informacion incompleta, y esta pasada existe justamente porque
    esa informacion cambio.

    Devuelve el historial completo. **No decide**: propone y deja las marcas
    puestas para que el LLM elija con ellas delante, que es la ronda siguiente.
    """
    hist = []
    if tramos is None:
        edl = json.load(open(f"ads/{slug}/edl-sell.json", encoding="utf-8"))
        tramos = [tuple(r) for r, d in zip(edl["segmentos"], edl["detalle"])
                  if d.get("beat") == beat]
    if not tramos:
        return hist
    primera = evaluar(slug, beat, tramos)
    primera["quien"] = "montaje actual"
    hist.append(primera)
    if primera.get("veredicto") == "mejor" or primera.get("error"):
        return hist
    # Las otras, de mejor a peor marca. Se prueban de una en una y se para en
    # cuanto una gana: el embudo tambien manda aqui — afinar cuesta minutos.
    for c in sorted(primera.get("frente_a") or [],
                    key=lambda x: -(x.get("marca") or 0))[:limite]:
        toma = None
        con = basedatos.abrir("ads/decisiones.db")
        con.row_factory = sqlite3.Row
        r = con.execute(
            "select t.nombre from candidato c join etapa e on e.id = c.etapa_id"
            " join video v on v.id = e.video_id"
            " join fragmento f on f.id = c.fragmento_id"
            " join toma t on t.id = f.toma_id"
            " where v.slug = ? and e.orden = ? and c.puesto = ?",
            (slug, beat, c["puesto"])).fetchone()
        con.close()
        toma = r["nombre"] if r else None
        if not toma:
            continue
        if afinar_ok and not afinada(toma, c["desde"], c["hasta"]):
            transcribir.afinar(toma, [(c["desde"], c["hasta"])])
        x = evaluar(slug, beat, [(c["desde"], c["hasta"])], toma=toma,
                    excluir=c["puesto"], contra=primera.get("marca"))
        x["quien"] = f"candidata {c['puesto']}"
        hist.append(x)
        if x.get("veredicto") == "mejor":
            break
    return hist


def _alrededor(pal, tramos, margen=12.0):
    """Las palabras de ±12 s alrededor de la etapa, `palabra[desde-hasta]`."""
    a = min(x for x, _ in tramos) - margen
    b = max(y for _, y in tramos) + margen
    return " ".join(f'{w["text"]}[{w["start"]:.2f}-{w["end"]:.2f}]'
                    for w in pal if a <= w.get("start", -1) <= b)


def dossier(slug):
    """Lo que el LLM necesita para decidir: el texto, sus números y las otras."""
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache = {}
    por_beat = {}
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        por_beat.setdefault(det["beat"], {"tramos": [], "det": det})
        por_beat[det["beat"]]["tramos"].append(tuple(rango))
    # **Lo que la etapa TENIA que decir, al lado de lo que dice.**
    #
    # El contrato lo declaraba `EXIGIDO Y NO ENVIADO`: *«es la definicion misma
    # de congruencia… no hay contra que comparar»*. Y el prompt de este paso
    # promete comparar *«del libreto y del texto»*, o sea que pedia una
    # congruencia sin darle uno de los dos lados.
    #
    # Jaime, sobre reel-03: *«parece que el libreto y la intencion comunicativa
    # del libreto no se respeto; si el objetivo es comparar A con B, no puedes
    # entregarme B roto o solo el final de A»*. No es que el paso ignorara el
    # libreto: es que no lo veia.
    #
    # Va **la intencion de su beat y nada mas** —1,2-1,7 KB por pieza—, no el
    # corpus: los 118 KB se quitaron de `repaso` a proposito, y devolverlos
    # seria invitar a recomponer la pieza en vez de juzgar el corte.
    try:
        from dominio.libreto import Libreto
        _lib = Libreto(int(slug[-2:])).beats
    except Exception:                              # noqa: BLE001
        _lib = []
    out = []
    ultimo = None
    for beat, d in sorted(por_beat.items()):
        toma = d["det"].get("toma") or rutas.TOMAS[slug]
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        pal = cache[toma]
        m = medir(toma, pal, d["tramos"])
        texto = " ".join(
            w["text"] for x, y in sorted(d["tramos"])
            for w in pal if transcribir.suena(w, x, y))
        try:
            inten = beats.intensidad(toma, m["desde"], m["hasta"], pal)
        except Exception:                          # noqa: BLE001
            inten = {}
        out.append({
            "beat": beat,
            "etapa": d["det"].get("etapa"),
            #: Lo que el libreto pedia para esta etapa. `None` si no hay.
            "libreto": _lib[beat - 1] if 1 <= beat <= len(_lib) else None,
            "trato": d["det"].get("trato"),
            **m,
            "intensidad": inten.get("intensidad"),
            # **Con signo, y por eso hacen falta las dos.** `intensidad` mide
            # cuanta emocion hay y es sin signo a proposito —Jaime: *«no hay
            # emociones positivas o negativas»*—, pero eso deja fuera la otra
            # mitad de la pregunta, que el nombro asi: *«si hablo de muerte no
            # quiero estar cagado de la risa; si hablo de futuro no quiero sonar
            # como un desesperado»*.
            #
            # O sea: cuanta emocion lo dice `intensidad`, y **cual** lo dicen la
            # altura y la velocidad. Se medían las dos y se tiraban antes de
            # llegar al contrato, asi que quien elige no podia ver si un tramo
            # iba grave o iba arriba — y con esa ceguera el reel-01 salio con
            # siete de ocho etapas en tono grave, el mecanismo incluido, que es
            # justo la etapa que promete la salida.
            "altura": inten.get("altura"),
            "velocidad": inten.get("velocidad"),
            "flojo": flojo(m),
            # **Como suena cada costura**, que es lo que decide si el segmento
            # queda armonico o pegado. Ver `saltos`.
            "saltos": saltos(toma, pal, d["tramos"], ultimo),
            "texto": texto,
            # **Y lo que se dice alrededor, con sus segundos.** Sin esto no se
            # puede mover un borde fuera del tramo: el 12-9 tres compositores
            # dejaron tiquets abiertos («falta "por qué"», «entra sin "el
            # contador es"») por no tener dónde ubicar la palabra.
            "alrededor": _alrededor(pal, d["tramos"]),
            # **Y las otras candidatas.** Sin esto solo se puede contestar «vale
            # o no vale»; con esto se puede elegir.
            "candidatas": candidatas(slug, beat),
        })
        ultimo = (toma, max(y for _, y in d["tramos"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--json", action="store_true",
                    help="para el paso de IA, que es quien decide")
    ap.add_argument("--bucle", type=int, metavar="BEAT",
                    help="re-evalua ESA etapa y prueba candidatas si no gana")
    ap.add_argument("--sin-afinar", action="store_true",
                    help="no llama al barrido caro (para probar sin esperar)")
    a = ap.parse_args()
    if a.bucle is not None:
        for n in (a.reels or [1]):
            slug = f"reel-{n:02d}"
            for h in rondas(slug, a.bucle, afinar_ok=not a.sin_afinar):
                if h.get("error"):
                    print(f"  {h['error']}")
                    continue
                print(f"  {h['quien']:<18} marca {h['marca']:>6}"
                      f"  {h['veredicto']:<8} margen {h.get('margen')}"
                      f"  costuras {len(h['saltos'])}")
                print(f"      {h['texto'][:110]}")
        return
    todo = {}
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        filas = dossier(slug)
        if not filas:
            continue
        todo[slug] = filas
        if a.json:
            continue
        print(f"\n{slug}")
        for f in filas:
            marca = (" ← " + ",".join(f["flojo"])) if f["flojo"] else ""
            print(f"  e{f['beat']:<2} voz {f['voz']:>4.1f}  tono {f['tono']:>5.1f}"
                  f"  ritmo {f['ritmo']:>4.2f}  cont {f['continuidad']:>4.2f}"
                  f"  {f['trozos']:>2} trozo(s){marca}")
            print(f"      {f['texto'][:100]}")
    if a.json:
        print(json.dumps(todo, ensure_ascii=False, indent=1))
    else:
        print("\nLos numeros informan; **quien decide si pasa es el LLM**, y decide"
              "\nsobre la intencion comunicativa: si el mensaje llega muy roto, no llego.")


if __name__ == "__main__":
    main()
