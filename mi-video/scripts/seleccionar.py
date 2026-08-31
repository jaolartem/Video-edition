"""La sección la marca el guion; los extremos, la pausa medida.

Los pasos 2 y 3 del proceso de Jaime, después de los subtítulos: *«con los
subtítulos de todo el video contrastamos contra el guion, evitamos las
repeticiones y puntuamos por sección: la mejor puntuada en la sección queda»*.

## Por qué no se busca «la frase»

Porque la frase no existe en el dato. `whisper -ml 1 -sow` **borra toda la
puntuación** —86 palabras del reel 3, cero signos—, y con `--prompt` sí puntúa
pero se come la primera frase y se queda pegado repitiendo. Así que cortar la
cinta en oraciones era pedirle al modelo justo lo que no sabe hacer, y de ahí
salían las unidades de 98 segundos.

La pausa sí está medida: la mide el detector de habla, no el modelo. Pero la
pausa sola tampoco define la unidad —hay tramos continuos de 50 s sin un solo
hueco de un segundo— y además Jaime avisó de lo contrario: *«hay silencios entre
la misma frase; no significa que sea otra toma, sólo me quedé callado
pensando»*.

Entonces **la sección la marca el guion**: para cada etapa del frame se busca el
trozo de cinta que mejor la dice, con los extremos anclados a pausa medida para
que el corte caiga en silencio. Es lo que hace que no haga falta puntuación.

## Cómo se puntúa

Una ventana es cualquier trozo que **empieza donde arranca un tramo y acaba
donde acaba otro**. Se le mide:

- **cubre** — cuánto del mensaje de la etapa está dicho (`beats.puntua`).
- **dice** — si aparecen los términos que la etapa declara en `debe_decir`.
  Vale más que la cobertura: son los datos que la etapa existe para decir.
- **aire** — el silencio interno se descuenta, no se prohíbe. Una pausa de
  pensar es aceptable; treinta segundos de nada, no.
- **repite** — palabras de contenido repetidas seguidas: el intento fallido y
  su corrección dentro de la misma ventana.
- **costura** — si el extremo no cae en un hueco de verdad, está cortando dentro
  de una frase. El umbral sale de los 885 huecos medidos del lote: p70 = 1,29 s
  y p80 = 2,58 s, y entre esos dos valores está la frontera entre la pausa de
  pensar y el final.
- **sobra / trunca** — la pausa limpia no basta. Tras «...preguntado al contador
  **por**» hay 3,79 s de silencio, y lo que sigue es «al contador por qué y es
  que...»: Jaime se paró y **reempezó la frase**. La firma del reintento es que
  la cola de la ventana reaparece al principio del tramo siguiente, y al revés
  —«de más, usted ya lleva años pagando de más»— que el arranque repita la cola
  del anterior.
- **cuelga** — un extremo detrás de una palabra de función parte una unidad
  sintáctica. Es la regla de los subtítulos compuestos (C-23) aplicada al corte,
  con la misma lista y leída del mismo fichero.

## Cómo se reparte

En orden de cinta y sin solaparse, maximizando el total: es la programación
dinámica de `encadenar()`. Eso respeta *«casi siempre secuencial»* sin imponer
que lo sea —una etapa puede quedarse vacía si su mejor ventana vale menos que lo
que le quita a las demás—, y hace **imposible por construcción** que dos etapas
usen el mismo trozo de cinta, que es de donde salía «repites demasiadas veces 21
dólares».

Y lo que la programación dinámica no puede ver —la misma frase dicha en dos
puntos distintos de la cinta— lo quita `sin_repetir()`, que vuelve a repartir
prohibiendo la copia peor puntuada.

    python scripts/seleccionar.py 3          # el plan del reel 3
    python scripts/seleccionar.py 3 --todo   # con los finalistas de cada etapa
"""
import argparse
import datetime
import io
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import depurar  # noqa: E402
import dominio  # noqa: E402
import estado  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402
import trato as trato_mod  # noqa: E402
import transcribir  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")

MIN_VOZ = 1.8     # por debajo no hay enunciado, hay una palabra suelta
MAX_VOZ = 26.0    # por encima no es una etapa, son varias
PESO_DICE = 0.6   # el dato declarado pesa mas que el parecido con el parrafo
# **El mensaje manda sobre la ejecucion.** Los castigos de extremo —costura,
# cuelga, solape— suman hasta 1,5, y con la cobertura contando 1 borraban
# diferencias de mensaje enormes: en el reel 1 gano una ventana que cubre 0,22
# frente a otra de 0,51 porque entraba mas limpia. Un extremo sucio se recorta;
# lo que no se dice no se recupera con nada.
PESO_CUBRE = 2.0
PESO_AIRE = 0.03  # por segundo de silencio interno
PESO_REPE = 0.7
# Un extremo es limpio si detras hay un hueco de verdad. La frontera sale de los
# datos: de los 885 huecos medidos del lote, p70 = 1,29 s y p80 = 2,58 s — ahi
# estan las dos poblaciones, la pausa de pensar y el final. Por debajo de esto
# la ventana esta cortando dentro de una frase, que es de donde salio
# «...preguntado al contador por».
COSTURA = 1.3
# Por debajo de esto el hueco es respiracion, no frontera: la idea sigue del
# otro lado aunque el detector de silencio marque un tramo. Medido sobre las
# pausas de estas seis cintas.
PAUSA_IDEA = 0.55
PESO_COSTURA = 0.45
# Un hueco grande no garantiza que ahi acabe la idea. En el reel 3 hay 3,79 s de
# silencio tras «...preguntado al contador por» y lo que viene despues es «al
# contador por que y es que...»: Jaime se paro y **reempezo la frase**. Eso no lo
# ve la pausa; lo delata que la cola de la ventana reaparezca al principio del
# tramo siguiente. Lo mismo al reves — «de mas, usted ya lleva anos pagando de
# mas» empieza con la cola de la idea anterior.
PESO_SOLAPE = 0.55
COLA = 4          # palabras de contenido que se comparan en cada extremo
# **Un extremo roto cuesta mas que lo que cubrir puede pagar.** Este numero era
# 0,5 contra un `PESO_CUBRE` de 2,0, asi que una ventana que empezaba a mitad de
# frase perdia 0,2 y ganaba hasta 2,0 por cubrir: cubrir compraba el corte.
#
# El resultado se vio al revisar el lote entero contra el libreto — **trece de
# las dieciocho roturas de argumento eran extremos partidos**: «tiene dos
# tra...», «quedan con 67», «el bootcamp esta», «nunca le ha preguntado al
# contador por». No eran dieciocho defectos distintos, era este numero.
#
# A 2,6 una ventana rota por un extremo pierde 1,3 y solo gana si la
# alternativa cubre mucho peor — que es exactamente cuando se acepta un corte
# feo: cuando lo otro no dice lo que hay que decir.
PESO_CUELGA = 2.6
# Lo que cuesta comerse el arranque de la etapa siguiente. Va alto a proposito:
# una ventana larga gana cobertura para SU etapa y deja a la de al lado sin
# material — y una etapa obligatoria vacia rompe la estructura entera.
PESO_INVADE = 1.5
UMBRAL = 0.14     # cobertura minima para ser candidata; por debajo no dice la etapa
SUELO_DICE = 0.05 # y ni con el dato declarado se rescata a quien no dice nada
# Por encima de esto, la toma reproduce el libreto palabra por palabra: es
# lectura. No compite — la etapa busca otra toma, y si no hay, va a tablero.
LEIDA = 0.60
# Y la voz que la salva. La mediana de los 53 elegidos es 4,99 st y el cuartil
# bajo 4,73: por debajo de 4,3 la entrega es plana, y una lectura plana es
# exactamente lo que Jaime no quiere ver.
# **3,4 y no 4,3: cambió la unidad.** El umbral estaba calibrado sobre el
# recorrido de F0 en semitonos; ahora la medida es la intensidad —distancia a la
# neutralidad de la cinta, sin signo— y vive en otra escala. Dejar el numero
# viejo mando cuatro etapas a tablero por «lectura plana» que no eran planas,
# entre ellas los ganchos del reel 3 y del reel 6.
#
# Se recalibra al mismo percentil, no al mismo numero: 4,3 era el p15 de la
# escala vieja y 3,4 es el p15 de la nueva. La mediana casi no se mueve (4,9),
# pero el fondo baja de 3,1 a 1,5 — la medida nueva **separa lo tibio de lo
# grave**, que era justo el sesgo que venia a corregir.
VOZ_SALVA = 3.4
# **Dejar una etapa sin toma cuesta.** Sin esto, saltarsela valia cero y la
# cadena prefería vaciarla antes que aceptar una ventana floja que le limitara
# las siguientes: el reel 2 salia con 3 etapas de 10 teniendo candidatas en
# siete. Y no es una preferencia estetica — Jaime aparece minimo tres veces y
# cada etapa vacia es un tablero mas y una tirada suya menos.
# Y van a la MISMA escala que la cobertura: al subir `PESO_CUBRE` a 2, dejar
# una etapa vacia se abarato a la mitad y el reel 5 perdio una obligatoria —
# una ventana mas larga se comio el trozo que la otra necesitaba. Un premio que
# no escala con lo que compite no premia nada.
PREMIO = 1.2
PREMIO_OBLIG = 2.4

# Detras de una palabra de funcion la frase NO ha acabado. La lista es la misma
# que usan los subtitulos compuestos (C-23) y vive en un solo sitio: dos copias
# se separan en cuanto una cambia.
COLGANTE = set(json.load(open(os.path.join(os.path.dirname(__file__),
                                           "colgantes.json"),
                              encoding="utf-8"))["palabras"])


def _solapa(cola, cabeza):
    """¿Reaparece la cola de un trozo al principio del siguiente?

    Es la firma del reintento: Jaime se para, y al retomar **vuelve unas
    palabras atras**. Cortar ahi deja la version truncada y manda al espectador
    la frase a medias, aunque el silencio sea limpio.
    """
    a, b = beats.norm(cola)[-COLA:], beats.norm(cabeza)[:COLA]
    if not a or not b:
        return 0.0
    mejor = 0
    for n in range(1, min(len(a), len(b)) + 1):
        if a[-n:] == b[:n]:
            mejor = n
    return mejor / COLA


def repite(texto):
    """Lo dicho dos veces dentro de la misma ventana.

    No basta con mirar repeticiones **seguidas**: en el reel 3 gano una ventana
    que decia «y no es porque no valga mas ... y no es porque no valga mas» con
    una frase entera en medio, y el detector de pares no la veia. Cuenta
    cualquier trigrama de contenido que aparezca dos veces.
    """
    ws = beats.norm(texto)
    if len(ws) < 4:
        return 0.0
    pares = sum(1 for i in range(len(ws) - 1) if ws[i] == ws[i + 1])
    vistos, tri = set(), 0
    for i in range(len(ws) - 2):
        g = tuple(ws[i:i + 3])
        if g in vistos:
            tri += 1
        vistos.add(g)
    return (pares + 2 * tri) / len(ws)


def cuelga(texto, entra=9.9, sale=9.9):
    """Cuánto rompe la ventana por sus extremos: 0 limpia, 1 rota por los dos.

    Detrás de «por», «que» o «de» la frase no ha acabado — es la regla de los
    subtítulos compuestos (C-23) aplicada al corte. Es lo que dejaba
    «...preguntado al contador **por**», que además es el trozo truncado de un
    reintento: la pausa de 3,79 s decía que ahí acababa algo, y lo que acababa
    era el intento, no la idea.

    **Y la palabra no basta.** «Tiene dos tra… un electricista en Brampton»
    empieza por un verbo cuyo sujeto se quedó en el tramo anterior, y ninguna
    lista de palabras colgantes atrapa eso. Lo que sí lo atrapa es el hueco: si
    antes de la ventana no hubo una pausa de verdad, la idea venía de antes.

    Así que un extremo está roto cuando **la palabra pide continuación o el
    hueco no llega a frontera**. Es la corrección de fondo de las dieciocho
    roturas de argumento del lote — trece eran exactamente esto.
    """
    ws = beats.palabras(texto)
    if not ws:
        return 1.0
    abre = (ws[0] in COLGANTE) or (entra < PAUSA_IDEA)
    cierra = (ws[-1] in COLGANTE) or (sale < PAUSA_IDEA)
    return 0.5 * float(abre) + 0.5 * float(cierra)


def ventanas(runs, palabras):
    """Todo trozo que empieza en el arranque de un tramo y acaba en el fin de otro."""
    # Las palabras de cada tramo, una sola vez: sin esto son cuatro mil barridos.
    por_tramo = [[] for _ in runs]
    k = 0
    for w in sorted(palabras, key=lambda w: w["start"]):
        c = (w["start"] + w["end"]) / 2
        while k + 1 < len(runs) and c >= runs[k][1]:
            k += 1
        if runs[k][0] - 0.25 <= c < runs[k][1] + 0.25:
            por_tramo[k].append(w)

    # El hueco antes de cada tramo y despues de cada tramo, medido.
    antes = [runs[0][0]] + [runs[k][0] - runs[k - 1][1] for k in range(1, len(runs))]
    despues = [runs[k + 1][0] - runs[k][1] for k in range(len(runs) - 1)] + [9.9]

    # **Un tramo sin palabras no es voz.** El detector de habla marca tramos por
    # nivel de senal —respiracion, ruido, un arranque que no llego a palabra— y
    # el transcript no saca nada de ellos. Contarlos como voz hacia que una
    # ventana pareciera llena estando vacia: el reel 1 abria con **22,6
    # segundos sin una sola palabra** entre 64,99 y 87,60, y eso salia al
    # montaje como el gancho.
    #
    # Es el aprendizaje 3 un nivel mas adentro: alli se intersecaba el EDL con
    # los tramos de habla; aqui hace falta intersecar con los tramos que
    # **produjeron texto**, que es lo unico que el espectador va a oir decir.
    con_voz = [bool(por_tramo[k]) for k in range(len(runs))]

    out = []
    for i in range(len(runs)):
        if not con_voz[i]:
            continue          # una ventana no puede ABRIR en un tramo mudo
        voz = 0.0
        ws = []
        for j in range(i, len(runs)):
            if con_voz[j]:
                voz += runs[j][1] - runs[j][0]
            ws = ws + por_tramo[j]
            if not con_voz[j]:
                continue      # ni CERRAR en uno
            if voz < MIN_VOZ:
                continue
            if voz > MAX_VOZ:
                break
            if not ws:
                continue
            a, b = runs[i][0], runs[j][1]
            texto = " ".join(w["text"] for w in ws).strip()
            if len(beats.norm(texto)) < 3:
                continue
            ant = " ".join(w["text"] for w in por_tramo[i - 1]) if i else ""
            sig = (" ".join(w["text"] for w in por_tramo[j + 1])
                   if j + 1 < len(runs) else "")
            # **Se construye por el tipo y se entrega como diccionario.**
            #
            # Los campos de una ventana no estaban declarados en ningun sitio:
            # eran las claves que este `append` ponia y que otras mil lineas
            # leian de memoria. Ahora los declara `dominio.Ventana`, y aqui se
            # devuelve `a_dict()` para que los consumidores no se enteren — que
            # es lo que permite tipar el productor sin reescribir a quien lee.
            #
            # Comprobado sobre las 1.823 ventanas del corpus: la ida y vuelta
            # devuelve los mismos campos con los mismos valores.
            out.append(dominio.Ventana(
                rango=dominio.Rango(round(a, 3), round(b, 3)),
                texto=texto, i=i, j=j,
                voz=round(voz, 2), aire=round((b - a) - voz, 2),
                entra=round(min(antes[i], 9.9), 2),
                sale=round(min(despues[j], 9.9), 2),
                # Sobra por delante si el arranque repite la cola del tramo
                # anterior; queda truncada por detras si su cola reaparece en el
                # siguiente.
                sobra=round(_solapa(ant, texto), 2),
                trunca=round(_solapa(texto, sig), 2),
            ).a_dict())
    return out


def invade(v, siguiente):
    """¿Se está comiendo el arranque de la etapa siguiente?

    No es repetición —`podar_dentro` no lo ve— es una ventana que sigue
    hablando después de cumplir lo suyo y entra en el material de la etapa que
    viene. En el reel 5 la etapa 3 acababa diciendo «el contador lo revisó todo
    y estaba bien declarado», que es el arranque literal de la etapa 4, y por
    eso la 4 se quedaba sin material: sus cinco candidatas vivían dentro de esa
    ventana.

    Se mide sobre el ÚLTIMO TERCIO, que es donde ocurre: si esa cola dice más
    de la etapa siguiente que del resto, la ventana se pasó de larga.
    """
    if not siguiente:
        return 0.0
    ws = beats.palabras(v["texto"])
    if len(ws) < 9:
        return 0.0
    cola = " ".join(ws[-len(ws) // 3:])
    pedidas = set(beats.norm(siguiente))
    if not pedidas:
        return 0.0
    return len(pedidas & set(beats.norm(cola))) / len(pedidas)


def literal(texto, parrafo, n=4):
    """Cuánta secuencia EXACTA del libreto reproduce. Es el detector de lectura.

    Regla de Jaime: *«no es aceptado leer; para leer prefiero el tablero»*, y la
    clave que lo hace medible: *«la lectura es exacta; sin lectura no hay una
    correspondencia exacta, hay errores, matices, y esa es la idea»*.

    **Y esto invierte lo que la puntuación premiaba.** La cobertura mide cuántas
    palabras del libreto aparecen, así que cuanto más literal es una toma más
    puntúa — o sea que el selector estaba **eligiendo las tomas leídas por
    construcción**. Por eso Jaime salía leyendo en varias.

    Se miden secuencias de cuatro palabras, no palabras sueltas: decir las
    mismas palabras en otro orden es hablar; decirlas en el mismo orden es leer.

    El umbral sale de los datos, no del ojo: sobre los 53 fragmentos elegidos la
    distribución tiene un **salto de 0,17** entre 0,684 y 0,519, y por encima se
    agrupan doce — seis de ellos del reel 4, que es justo donde Jaime lo noto.
    """
    a, b = beats.palabras(parrafo), beats.palabras(texto)
    if len(a) < n:
        return 0.0
    ga = {tuple(a[i:i + n]) for i in range(len(a) - n + 1)}
    gb = {tuple(b[i:i + n]) for i in range(len(b) - n + 1)}
    return len(ga & gb) / max(1, len(ga))


def puntuar(parrafo, exige, v, siguiente=""):
    u = {"a": v["a"], "b": v["b"], "texto": v["texto"],
         "clave": set(beats.norm(v["texto"]))}
    cubre = float(beats.puntua(parrafo, u))
    dice = (all(beats.dice(v["texto"], t) for t in exige) if exige else False)
    # Cortar dentro de una frase se paga. Jaime lo dijo por su nombre: *«hay
    # silencios entre la misma frase; no significa que sea otra toma, solo me
    # quede callado pensando»*. Un extremo en una pausa de pensar no es un
    # extremo, es un corte a mitad de idea.
    costura = ((max(0.0, COSTURA - v["entra"]) + max(0.0, COSTURA - v["sale"]))
               / (2 * COSTURA))
    p = (PESO_CUBRE * cubre
         + PESO_DICE * (1.0 if dice else 0.0)
         - PESO_AIRE * v["aire"]
         # **La redundancia NO decide cual se elige.** Regla de Jaime: *«a la
         # mejor toma, y solo a la mejor, le hacemos la revision estricta de
         # redundancia»*, y la eleccion es *«por entrega emocional»*. Penalizarla
         # aqui la metia en las 5.319 candidatas y hacia que un tropiezo
         # descartara la toma con mejor voz — que es justo al reves. La poda va
         # despues, sobre la ganadora: `podar_dentro`, `limpiar_costura` y
         # `depurar.py`.
         - PESO_COSTURA * costura
         - PESO_SOLAPE * (v["sobra"] + v["trunca"]) / 2
         - PESO_CUELGA * cuelga(v["texto"], v["entra"], v["sale"])
         - PESO_INVADE * invade(v, siguiente))
    return round(p, 4), round(cubre, 4), int(dice)


def encadenar(marcas, vs, prohibidas=(), premio=None):
    """Reparte las etapas en orden de cinta y sin solaparse, al mayor total.

    `marcas[s][k]` es lo que vale la ventana k para la etapa s. La recurrencia
    es la de siempre —o se salta la ventana, o se toma y se sigue por la primera
    que empieza después de que ésta acabe— y su efecto de fondo es el que
    importa: **dos etapas no pueden usar el mismo trozo de cinta.**
    """
    S, K = len(marcas), len(vs)
    # Para cada ventana, la primera que empieza cuando ésta ya acabó.
    sig = [K] * K
    for k in range(K):
        for m in range(k + 1, K):
            if vs[m].get("toma") != vs[k].get("toma") or vs[m]["i"] > vs[k]["j"]:
                sig[k] = m
                break
    NADA = float("-inf")
    dp = [[NADA] * (K + 1) for _ in range(S + 1)]
    de = [[None] * (K + 1) for _ in range(S + 1)]
    for k in range(K + 1):
        dp[S][k] = 0.0
    for s in range(S - 1, -1, -1):
        dp[s][K] = dp[s + 1][K]          # sin ventana: la etapa va con tarjeta
        de[s][K] = ("salta", None)
        for k in range(K - 1, -1, -1):
            mejor, arg = dp[s][k + 1], ("otra", None)
            if dp[s + 1][K] > mejor:
                mejor, arg = dp[s + 1][K], ("salta", None)
            if k not in prohibidas and marcas[s][k] is not None:
                cand = (marcas[s][k] + (premio[s] if premio else PREMIO)
                        + dp[s + 1][sig[k]])
                if cand > mejor:
                    mejor, arg = cand, ("toma", k)
            dp[s][k], de[s][k] = mejor, arg
    plan, s, k = [], 0, 0
    while s < S:
        que, dato = de[s][k]
        if que == "otra":
            k += 1
            continue
        plan.append(dato)
        s += 1
        k = sig[dato] if dato is not None else K
    return plan, dp[0][0]


def sin_repetir(marcas, vs, plan, premio=None):
    """Quita la copia peor puntuada cuando dos etapas dicen lo mismo.

    La cadena impide usar el mismo trozo dos veces, pero no que Jaime diga la
    misma frase en dos puntos de la cinta y caigan las dos. Eso era «repites
    demasiadas veces 21 dolares», y es la parte del proceso que Jaime nombra
    aparte: *«evitamos las repeticiones»*.
    """
    for _ in range(4):
        malas, elegidas = set(), [(s, k) for s, k in enumerate(plan)
                                  if k is not None]
        for x in range(len(elegidas)):
            for y in range(x + 1, len(elegidas)):
                (s1, k1), (s2, k2) = elegidas[x], elegidas[y]
                a, b = set(beats.norm(vs[k1]["texto"])), set(beats.norm(vs[k2]["texto"]))
                if not a or not b:
                    continue
                if len(a & b) / min(len(a), len(b)) > 0.72:
                    # **Se prohibe la REGION de cinta, no la ventana.** Con 876
                    # ventanas, muchas solapadas, tumbar un indice deja a la
                    # cadena elegir la de al lado, que dice exactamente lo
                    # mismo: por eso las etapas 6 y 7 del reel 1 repetian las
                    # dos «este 21 de septiembre voy a hacer un bootcamp» ronda
                    # tras ronda. Prohibir el trozo si converge.
                    peor = k1 if marcas[s1][k1] < marcas[s2][k2] else k2
                    # `z`, no `x`: reusar el nombre del bucle de fuera lo dejaba
                    # apuntando al final de `vs` y la vuelta siguiente indexaba
                    # `elegidas` fuera de rango. Reventaba solo cuando habia una
                    # repeticion que quitar, o sea justo cuando hacia falta.
                    # Se prohibe la region **y ademas** que diga lo mismo: con
                    # solo la region, en el reel 2 —donde Jaime repite mucho— la
                    # veda arrasaba candidatas y el reparto caia de 10 etapas a
                    # 3. Lo que sobra es la copia, no el trozo de cinta.
                    pal = set(beats.norm(vs[peor]["texto"]))
                    for z, w in enumerate(vs):
                        if (w.get("toma") != vs[peor].get("toma")
                                or w["j"] < vs[peor]["i"] or w["i"] > vs[peor]["j"]):
                            continue
                        c = set(beats.norm(w["texto"]))
                        if c and len(c & pal) / min(len(c), len(pal)) > 0.72:
                            malas.add(z)
        if not malas:
            return plan
        nuevo, _ = encadenar(marcas, vs, prohibidas=malas, premio=premio)
        # **Quitar una repeticion no puede costar una etapa.** Si el reparto
        # nuevo cubre menos, la veda se paso de ancha y vale mas la pieza
        # completa: se avisa y se deja como estaba.
        if segs_ok(nuevo).__len__() < segs_ok(plan).__len__():
            registro.aviso("seleccionar", "veda de repeticion descartada",
                           detalle=f"habria dejado {len(segs_ok(nuevo))} etapas"
                                   f" de {len(segs_ok(plan))}", eco=False)
            return plan
        plan = nuevo
    return plan


def recortar(v, palabras):
    """Quita del extremo lo que cuelga, con los tiempos de palabra.

    Un extremo que parte una unidad sintáctica no descalifica la ventana: se
    recorta, que es lo que haría un montador. «...preguntado al contador **por**»
    cierra en «contador»; «**una...** el contador es como un médico» abre en «el
    contador».

    Se recorta por palabra y no por tramo a propósito: el tramo es la pausa
    medida y aquí hay que entrar por dentro. El corte cae en silencio de todos
    modos porque el montaje funde 50 ms por escena.
    """
    ws = [w for w in palabras if v["a"] - 0.01 <= w["start"] and w["end"] <= v["b"] + 0.01]
    if len(ws) < 4:
        return v
    pal = lambda w: (beats.palabras(w["text"]) or [""])[0]

    # **La cola sí, la cabeza casi no.** Detras de una palabra de funcion la
    # frase no ha acabado, siempre. Pero una frase **puede empezar** por «y»,
    # «si», «no» o «usted»: recortando la cabeza por la misma regla, «y si usted
    # no sabe que pedir» se quedo en «sabe que pedir» y perdio la condicion
    # entera. Asi que por delante solo se quita el resto de la idea anterior —el
    # fragmento cortado, o lo que repite el final del tramo de antes.
    ini, fin = 0, len(ws)
    while fin - ini > 3 and pal(ws[fin - 1]) in COLGANTE:
        fin -= 1
    while fin - ini > 3 and (not pal(ws[ini])
                             or ws[ini]["text"].strip().endswith("...")):
        ini += 1
    if ini == 0 and fin == len(ws):
        return v
    v = dict(v)
    v["a"] = round(max(v["a"], ws[ini]["start"] - 0.06), 3)
    v["b"] = round(min(v["b"], ws[fin - 1]["end"] + 0.10), 3)
    v["texto"] = " ".join(w["text"] for w in ws[ini:fin]).strip()
    v["recortado"] = len(ws) - (fin - ini)
    return v


def _mejora(nuevo, viejo, parrafo, exige):
    """¿Sigue diciendo la etapa despues de podar?"""
    def val(v):
        u = {"a": v["a"], "b": v["b"], "texto": v["texto"],
             "clave": set(beats.norm(v["texto"]))}
        c = float(beats.puntua(parrafo, u))
        d = all(beats.dice(v["texto"], t) for t in exige) if exige else True
        return (1 if d else 0, c)
    return val(nuevo) >= val(viejo)


def podar_dentro(v, palabras, parrafo="", exige=()):
    """Lo dicho dos veces dentro de la ventana: se queda la ULTIMA.

    Regla de Jaime, dicha varias veces y siempre igual: *«repites demasiadas
    veces 21 dolares»*, *«lo mismo con 1890000»*, *«el libreto marca una sola no
    dos»*, *«correctivos para la redundancia»*. Y la razon de quedarse con la
    ultima es como graba: repite hasta que sale, asi que **la buena suele ser la
    de despues** (aprendizaje 25) — la de antes es el intento.

    Se corta solo cuando el trigrama de contenido es **identico**. Eso es un
    reintento, no una figura: la anafora que si vale —«de cada 100 dolares que
    el recibe... de cada 100 dolares que usted recibe»— cambia una palabra de
    contenido, y por eso no la toca. Es lo que impide repetir el error de
    quitar la frase buena (aprendizaje 13).
    """
    ws = [w for w in palabras
          if v["a"] - 0.01 <= w["start"] and w["end"] <= v["b"] + 0.01]
    if len(ws) < 8:
        return v
    cont = [(i, n[0]) for i, n in
            ((i, beats.norm(w["text"])) for i, w in enumerate(ws)) if n]
    for n in (4, 3):
        for x in range(len(cont) - 2 * n + 1):
            g1 = [c[1] for c in cont[x:x + n]]
            for y in range(x + n, len(cont) - n + 1):
                if [c[1] for c in cont[y:y + n]] != g1:
                    continue
                corte = cont[y][0]
                if corte < 2 or len(ws) - corte < 4:
                    continue
                nuevo = dict(v)
                nuevo["a"] = round(ws[corte]["start"] - 0.06, 3)
                nuevo["texto"] = " ".join(w["text"] for w in ws[corte:]).strip()
                nuevo["podado"] = corte
                # **La poda limpia, no elige** (aprendizaje 13). Jaime dice
                # «30.000 dolares» siete veces seguidas dentro de una misma
                # tirada, asi que quedarse con la ultima aparicion tiraba «gana
                # 180 mil al ano, sin estructura puede estar pagando 30 mil
                # dolares mas» y dejaba el tropiezo «estructura. 30.000 dolares
                # no de ventas de estructura.» — que en el montaje sono como
                # «el gobierno de Canada rentas de estructura».
                #
                # La diferencia entre el reintento y la insistencia no esta en
                # el trigrama: esta en si lo que queda **sigue diciendo la
                # etapa**. Si podar empeora eso, no era un reintento.
                # Dos formas de quitar la repeticion: **quedarse con la
                # ultima** —el reintento, que es lo normal— o **quedarse con la
                # primera** y tirar la cola, que es lo que toca cuando insiste
                # dentro de una misma tirada. Se prueban las dos y gana la que
                # no empeore la etapa; si ninguna vale, no se toca.
                cola = dict(v)
                cola["b"] = round(ws[cont[y - 1][0]]["end"] + 0.10, 3)
                cola["texto"] = " ".join(
                    w["text"] for w in ws[:cont[y - 1][0] + 1]).strip()
                cola["podado_cola"] = len(ws) - cont[y - 1][0] - 1
                for cand in (nuevo, cola):
                    if not parrafo or _mejora(cand, v, parrafo, exige):
                        return podar_dentro(cand, palabras, parrafo, exige)
                continue
    return v


def limpiar_costura(plan, vs, palabras_de):
    """La repeticion que cruza el corte: cola de una, cabeza de la siguiente.

    Es el aprendizaje 31 —*«las repeticiones que sobreviven cruzan el corte»*—:
    cada ventana esta limpia por su cuenta y juntas dicen «eso no es mala
    suerte, eso no es mala suerte». Trece casos en los seis reels montados. Se
    quita de la SEGUNDA, que es donde sobra: la primera ya cerro su idea.
    """
    ult = None
    for k in plan:
        if k is None:
            continue
        if ult is not None:
            cola = beats.norm(vs[ult]["texto"])[-COLA:]
            ws = [w for w in palabras_de[vs[k]["toma"]]
                  if vs[k]["a"] - 0.01 <= w["start"] and w["end"] <= vs[k]["b"] + 0.01]
            cabeza = [(i, beats.norm(w["text"])[0]) for i, w in enumerate(ws)
                      if beats.norm(w["text"])][:COLA]
            corte = 0
            for n in range(min(len(cola), len(cabeza)), 0, -1):
                if cola[-n:] == [c[1] for c in cabeza[:n]]:
                    corte = cabeza[n - 1][0] + 1
                    break
            if corte and len(ws) - corte >= 4:
                v = dict(vs[k])
                v["a"] = round(ws[corte]["start"] - 0.06, 3)
                v["texto"] = " ".join(w["text"] for w in ws[corte:]).strip()
                v["costura"] = corte
                vs[k] = {**v, "det": vs[k].get("det", {}), "toma": vs[k]["toma"]}
        ult = k
    return plan


def una_sola_vez(plan, vs, frame):
    """Cada dato declarado se dice UNA vez en la pieza.

    *«El libreto marca una sola no dos.»* La cadena impide que dos etapas usen
    el mismo trozo de cinta, pero no que el mismo dato —21 dolares, 1.890.000—
    aparezca en dos trozos distintos. Esto no recorta: **avisa con el sitio**,
    porque cual de las dos sobra depende del argumento y esa no es una decision
    del script (aprendizaje 13).
    """
    fuera = []
    for s, k in enumerate(plan):
        exige = (frame["beats"][s].get("debe_decir") or []
                 if s < len(frame["beats"]) else [])
        for t in exige or []:
            donde = [(o + 1, vs[j]["a"]) for o, j in enumerate(plan)
                     if j is not None and beats.dice(vs[j]["texto"], t)]
            if len(donde) > 1 and not any(t == x[0] for x in fuera):
                fuera.append((t, s + 1, donde))
    return fuera


def remedir(v, runs):
    """Vuelve a medir voz y aire despues de recortar.

    Un recorte mueve `a` o `b` y **deja los dos numeros mintiendo**: la etapa 6
    del reel 3 declaraba 9,3 s de voz sobre una ventana de 4,15 s. Aguas abajo
    eso es una duracion de escena equivocada, que es el aprendizaje 43 —el
    render pidiendo un frame que no existe— por otro camino.
    """
    voz = sum(max(0.0, min(v["b"], b) - max(v["a"], a)) for a, b in runs)
    v = dict(v)
    v["voz"] = round(voz, 2)
    v["aire"] = round(max(0.0, (v["b"] - v["a"]) - voz), 2)
    return v


def manda_jaime(plan, vs, slug, palabras, runs, marcas, toma_propia):
    """Lo que Jaime ya juzgo **no se vuelve a elegir**.

    Es el aprendizaje 13 —*«las heuristicas limpian, no eligen»*— y ya se
    incumplio tres veces en una sesion: un automatismo sustituyo el arranque
    elegido de oido y hubo que re-imponerlo a mano en cada montaje. Con la
    seleccion nueva volveria a pasar, porque busca de cero.

    Los cuatro estados de `ads/estado.json`, y cada uno hace algo distinto:

    - `aprobado`  — se usa **el rango declarado**, tal cual. No se busca.
    - `recortar`  — se conserva lo elegido y se aplica `entra_en`/`sale_en`.
    - `rechazado` — la etapa va con tarjeta y **no se busca sustituto**.
    - lo demas    — lo elige el reparto.
    """
    est = estado.cargar().get("reels", {}).get(slug, {})
    if not est:
        return plan
    for clave, dec in est.items():
        try:
            s0 = int(clave) - 1
        except ValueError:
            continue
        if not (0 <= s0 < len(plan)):
            continue
        e = dec.get("estado") if isinstance(dec, dict) else dec
        if e == "rechazado":
            plan[s0] = None
            registro.nota("seleccionar", "etapa rechazada por Jaime",
                          detalle=f"{slug} etapa {clave}")
            continue
        k = plan[s0]
        if e == "aprobado" and dec.get("desde") is not None:
            a, b = float(dec["desde"]), float(dec["hasta"])
        elif e == "recortar":
            a = float(dec.get("entra_en", vs[k]["a"] if k is not None else 0))
            b = float(dec.get("sale_en", vs[k]["b"] if k is not None else 0))
            # **Un punto de entrada puede apuntar a otra unidad.** El
            # `entra_en` del reel 1 etapa 7 es 563,3 y la ventana que eligio el
            # reparto acaba en 539: aplicarlo tal cual daba el rango invertido
            # `563,30-539,03`, o sea cero segundos de voz y ningun aviso.
            # Lo que Jaime decidio ahi es **donde entra**; hasta donde llega lo
            # decide el reparto, asi que se busca la mejor candidata que empiece
            # en ese punto.
            if b <= a or k is None or not (vs[k]["a"] <= a <= vs[k]["b"]):
                # Solo las candidatas originales tienen marca: `vs` crece
                # con las ventanas que se anaden aqui.
                cerca = [(marcas[s0][x], x) for x in range(len(marcas[s0]))
                         if marcas[s0][x] is not None
                         and abs(vs[x]["a"] - a) < 2.0
                         and (not dec.get("sale_en") or vs[x]["b"] <= b + 0.3)]
                if not cerca:
                    registro.error("seleccionar", "recorte que no cuadra",
                                   detalle=f"{slug} etapa {clave}: entra_en {a}"
                                           f" no cae en ninguna candidata")
                    continue
                k = max(cerca)[1]
                a, b = vs[k]["a"], vs[k]["b"]
        else:
            continue
        ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
        v = {"i": 0, "j": 0, "a": round(a, 3), "b": round(b, 3),
             "entra": 9.9, "sale": 9.9, "sobra": 0.0, "trunca": 0.0,
             "texto": (dec.get("texto")
                       or " ".join(w["text"] for w in ws).strip()),
             "det": {}, "de_jaime": e, "toma": toma_propia}
        vs.append(remedir(v, runs))
        plan[s0] = len(vs) - 1
        registro.nota("seleccionar", f"etapa {e} por Jaime",
                      detalle=f"{slug} etapa {clave}: {a:.2f}-{b:.2f}")
    return plan


def segs_ok(plan):
    return [k for k in plan if k is not None]


def escribir_edl(slug, plan, vs, libreto, frame, runs):
    """Escribe `ads/<slug>/edl-sell.json` desde el reparto.

    Se **conserva** del EDL anterior todo lo que no sale de la seleccion —pilar,
    estructura, mecanismo, la fecha declarada de la oferta— y se rehace lo que
    si: los cortes, el detalle por etapa y las duraciones. Asi cambiar de
    seleccion no borra un dato de la oferta que nadie ha vuelto a decidir.
    """
    ruta = os.path.join("ads", slug, "edl-sell.json")
    base = {}
    if os.path.exists(ruta):
        base = json.load(open(ruta, encoding="utf-8"))

    segs, det, sin_toma, fuentes = [], [], [], []
    # Segundo en que empieza cada segmento en la SALIDA, para saber si cae en el
    # gancho. En una lista para poder acumular dentro del bucle.
    voz_acum = [0.0]
    for s0, k in enumerate(plan):
        etapa = (frame["beats"][s0].get("etapa") if s0 < len(frame["beats"]) else "") or ""
        oblig = bool(frame["beats"][s0].get("obligatorio")) if s0 < len(frame["beats"]) else False
        if k is None:
            sin_toma.append({"beat": s0 + 1, "etapa": etapa, "obligatorio": oblig,
                             "libreto": (libreto[s0] if s0 < len(libreto) else "")[:400]})
            continue
        if vs[k].get("a_tablero"):
            # Lectura plana: la etapa va con tablero y **el copy es lo leido**,
            # que por ser exacto dice lo que el libreto queria decir.
            sin_toma.append({"beat": s0 + 1, "etapa": etapa, "obligatorio": oblig,
                             "motivo": "lectura plana",
                             "literal": vs[k].get("literal"),
                             "voz_st": vs[k].get("voz_st"),
                             "copy": vs[k]["texto"][:400],
                             "libreto": (libreto[s0] if s0 < len(libreto) else "")[:400]})
            continue
        v = vs[k]
        cubre, dice = v["det"].get(s0, (0.0, 0))
        lit = literal(v["texto"], libreto[s0] if s0 < len(libreto) else "")
        # **Cuanto se podia cubrir de esta etapa como mucho.** Sin este numero,
        # la cobertura sola mide LITERALIDAD contra el parrafo del libreto: si
        # el parrafo es largo —el del reel 2 habla de la mansion, el yate y
        # Muskoka antes de llegar a la cifra— decir solo lo esencial puntua
        # bajo aunque cumpla la etapa. Jaime: *«la idea no es tomar el libreto
        # literal, es tomar la intencion comunicativa de cada parte»*.
        mejor = max((vs[k2]["det"].get(s0, (0.0, 0))[0]
                     for k2 in range(len(vs)) if s0 in vs[k2].get("det", {})),
                    default=cubre)
        # El tratamiento se DECIDE con lo medido, no se declara a mano.
        niv, fig, _pq = trato_mod.densidad(slug, s0 + 1)
        tr, porque = trato_mod.decidir(
            desde_s=round(voz_acum[0], 2), dura_s=v["b"] - v["a"],
            parrafo=libreto[s0] if s0 < len(libreto) else "",
            texto=v["texto"], literal=lit, voz_st=v.get("voz_st"),
            nivel=niv, figura=fig,
            # Lo que el LLM decidio mirando la pieza entera manda sobre la
            # heuristica: la necesidad del video no se ve desde un segmento.
            decidido=trato_mod.decidido(slug, s0 + 1))
        voz_acum[0] += (v["b"] - v["a"]) / beats.VELOCIDAD
        segs.append([v["a"], v["b"]])
        fuentes.append(v.get("toma", ""))
        det.append({"start": v["a"], "end": v["b"], "beat": s0 + 1,
                    "etapa": etapa, "obligatorio": oblig,
                    "cobertura": round(float(cubre), 3), "dice": int(dice),
                    "cubre_max": round(float(mejor), 3),
                    "de_jaime": v.get("de_jaime"), "toma": v.get("toma"),
                    "literal": round(lit, 3), "voz_st": v.get("voz_st"),
                    "trato": tr, "trato_porque": porque,
                    "densidad": niv, "figura": fig,
                    "texto": v["texto"]})

    voz = sum(v[1] - v[0] for v in segs)
    aire = sum(vs[k]["aire"] for k in plan if k is not None)
    # Las zonas, por funcion de la etapa y no por reloj: el gancho es el primer
    # beat y el CTA son las etapas de cierre que declara el frame.
    CIERRE = ("promesa", "urgencia", "registro", "aplicación", "aplicacion")
    cta_i = [i for i, d in enumerate(det)
             if any(c in (d["etapa"] or "").lower() for c in CIERRE)]
    corte = min(cta_i) if cta_i else len(det)
    zonas = dict(base.get("zonas") or {})
    zonas.update({
        "gancho_s": round(det[0]["end"] - det[0]["start"], 2) if det else 0,
        "cuerpo_s": round(sum(d["end"] - d["start"] for d in det[1:corte]), 2),
        "cta_s": round(sum(d["end"] - d["start"] for d in det[corte:]), 2),
    })

    out = dict(base)
    out.update({
        "pilar": base.get("pilar", "SELL"),
        "estructura": frame.get("estructura", base.get("estructura")),
        "mecanismo": frame.get("mecanismo", base.get("mecanismo")),
        "zonas": zonas,
        "enunciados": len(segs),
        "duracion_montada_s": round(voz, 2),
        "aire_muerto_eliminado_s": round(aire, 2),
        "segmentos": segs,
        # **De que grabacion sale cada corte.** Un video no tiene por que salir
        # de una sola cinta: Jaime regraba, y a veces graba la ultima parte de
        # un video en otra sesion. Si todos coinciden esto es redundante y no
        # estorba; si no, es lo unico que permite cortar.
        "fuentes": fuentes,
        "detalle": det,
        "sin_toma": sin_toma,
    })
    rev = dict(out.get("revision") or {})
    # **Las marcas de operacion NO se heredan.** `depurado_n` y
    # `notas_aplicadas` describen lo que se le hizo a UN EDL concreto, y aqui se
    # esta escribiendo otro. Arrastrarlas hacia que `depurar` se saltara una
    # seleccion recien hecha y que `revision` se saltara todos los cortes de
    # Jaime creyendolos ya aplicados: la correccion se perdia en silencio, que
    # es la peor forma de perderse.
    for _marca in ("depurado", "depurado_n", "notas_aplicadas", "revision_final"):
        rev.pop(_marca, None)
    # **Las marcas de operacion NO se heredan.** `depurado_n` y
    # `notas_aplicadas` describen lo que se le hizo a UN EDL concreto, y aqui se
    # esta escribiendo otro. Arrastrarlas hacia que `depurar` se saltara una
    # seleccion recien hecha y que `revision` se saltara todos los cortes de
    # Jaime creyendolos ya aplicados — la correccion se perdia en silencio, que
    # es la peor forma de perderse.
    for marca in ("depurado", "depurado_n", "notas_aplicadas", "revision_final"):
        rev.pop(marca, None)
    rev["montaje"] = ("Por etapas del frame: la seccion la marca el guion y los "
                      "extremos la pausa medida. Ver scripts/seleccionar.py "
                      "(C-55) sobre el transcript de varias pasadas (C-54).")
    if segs != sorted(segs):
        # Aprendizaje 35: **cronologico no es montado**. Ya rompio tres
        # herramientas distintas que asumian orden de cinta, asi que el dato lo
        # dice por si mismo en vez de esperar a que cada una se entere.
        rev["orden"] = ("Los segmentos van en orden de MONTAJE, no de cinta:"
                        " este reparto usa tomas fuera de orden porque en la"
                        " cinta las etapas finales se grabaron antes.")
    rev["no_redundante"] = ("podar_dentro + limpiar_costura + una_sola_vez "
                            "(C-58): nada se dice dos veces.")
    out["revision"] = rev
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(out, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return ruta, voz


def repartir_libre(marcas, vs, premio, prohibidas=()):
    """Reparte sin exigir orden de cinta, cuando el orden no da.

    Jaime lo dijo con todas las letras: *«no siempre secuencial pero siempre por
    etapas completas»*, *«casi siempre secuencial»*. La cadena de `encadenar()`
    impone el orden, y en el reel 2 —donde regrabo el argumento entero y las
    tomas buenas de las etapas finales estan ANTES en la cinta que las de las
    primeras— eso dejaba **3 etapas de 10 teniendo candidatas en siete**.

    Aqui se toma el mejor par (etapa, ventana) que quede, se tachan la etapa y
    todo lo que solape, y se repite. No es optimo y no hace falta: lo que hace
    es no perder una etapa entera por un requisito de orden que Jaime nunca
    puso.
    """
    libres = set(range(len(marcas)))
    pares = sorted(((marcas[s][k] + premio[s], s, k)
                    for s in range(len(marcas))
                    for k in range(len(vs))
                    if marcas[s][k] is not None and k not in prohibidas),
                   reverse=True)
    # **Las obligatorias se sirven primero.**
    #
    # Tomando siempre el mejor par, una etapa larga se come el trozo donde vive
    # el material de la siguiente y esta se queda sin nada — el reel 5 perdio su
    # etapa 4 asi: la 3 ocupo 302,3-332,1 y las cinco candidatas de la 4 estaban
    # dentro. El voraz no reconsidera, asi que la unica forma de que no pase es
    # el orden: una etapa obligatoria sin material rompe la estructura, y eso
    # vale mas que cualquier ganancia de cobertura en su vecina.
    obl = {s for s in range(len(marcas)) if premio[s] >= max(premio)}
    orden = ([x for x in pares if x[1] in obl] +
             [x for x in pares if x[1] not in obl])
    plan = [None] * len(marcas)
    usados = []
    for _, s, k in orden:
        if s not in libres:
            continue
        # Dos ventanas de cintas distintas no pueden pisarse: son grabaciones
        # separadas. El solape solo existe dentro de la misma toma.
        if any(vs[k].get("toma") == vs[u].get("toma")
               and not (vs[k]["j"] < vs[u]["i"] or vs[k]["i"] > vs[u]["j"])
               for u in usados):
            continue
        plan[s] = k
        usados.append(k)
        libres.discard(s)
    total = sum(marcas[s][k] + premio[s]
                for s, k in enumerate(plan) if k is not None)
    return plan, total


def corpus(tomas):
    """Las ventanas de TODAS las grabaciones, no solo la del reel.

    Correccion de Jaime, y reordena el modelo entero: *«tipicamente se asume que
    un video un libreto, pero no siempre es asi. A veces se regraban los videos,
    otras veces se graba la ultima parte de un video anterior, otras veces se
    graban videos sin guion. ¿Cual es nuestra unidad basica? No es el guion, no
    es el video y no es el frame. Es la seccion de frame, y eso sale de la union
    de la teorica (libreto) con la practica (grabacion)»*.

    La consecuencia es directa: una etapa puede cumplirse con material de
    **cualquier** cinta. El modelo ya lo permitia —`fragmento` cuelga de `toma`,
    no de `video`— pero la busqueda no: hacia `rutas.TOMAS[slug]` y no salia de
    ahi. Por eso los 22 fragmentos elegidos eran cada uno de su propia toma, que
    parecia correcto y era el limite de la busqueda.

    Y cada ventana se lleva **de que cinta sale**: dos ventanas de tomas
    distintas no pueden solaparse por definicion, y el corte necesita saber que
    fichero abrir.
    """
    todo, datos = [], {}
    for t in tomas:
        try:
            d = transcribir.exigir(t)
        except SystemExit as e:
            registro.aviso("seleccionar", "cinta fuera del corpus",
                           toma=t, detalle=str(e)[:120], eco=False)
            continue
        runs = json.load(open(f"work/cuts/{t}.json", encoding="utf-8"))["segmentos"]
        datos[t] = (d, runs)
        for v in ventanas(runs, d["segmentos"]):
            v["toma"] = t
            todo.append(v)
    return todo, datos


def escalera(slug, toma, marcas, vs, cuantos=4):
    """Preselecciona barato, afina lo preseleccionado, y **vuelve a elegir todo**.

    Correccion de Jaime, y es la que salva el peldaño: *«si esto es asi hay que
    revalidar a los candidatos ganadores con el buen sistema, porque puede no
    coincidir para ese segmento pero ser los mejores para otro»*.

    O sea: afinar y confirmar en el sitio **no vale**. El barrido barato acierta
    el sitio en 7 de 9 etapas del reel 6, y las dos que falla las pone en otra
    etapa — asi que confirmar cada ganador donde el barato lo dejo hereda
    exactamente su error. Lo que hay que hacer es afinar la lista corta **de
    todas las etapas juntas** y **repartir de cero** sobre el material afinado.

    Devuelve los tramos a afinar; el reparto nuevo lo hace `main` volviendo a
    puntuar, que es lo mismo que hace siempre y por eso no hay un segundo
    camino que mantener.
    """
    quiero = []
    for s0 in range(len(marcas)):
        top = sorted((k for k in range(len(marcas[s0]))
                      if marcas[s0][k] is not None),
                     key=lambda k: -marcas[s0][k])[:cuantos]
        for k in top:
            if vs[k].get("toma") == toma:
                quiero.append((round(vs[k]["a"], 2), round(vs[k]["b"], 2)))
    # Se funden los solapados: afinar dos veces el mismo trozo es pagar dos veces.
    quiero.sort()
    fundidos = []
    for a, b in quiero:
        if fundidos and a <= fundidos[-1][1] + 0.5:
            fundidos[-1] = (fundidos[-1][0], max(fundidos[-1][1], b))
        else:
            fundidos.append((a, b))
    return fundidos


def limpieza(palabras, a, b):
    """Cuánto de lo dicho sobrevive a quitarle los tropiezos. 1,0 es limpia.

    Jaime: *«para la intención comunicativa a veces es mejor una toma limpia y
    sin errores, pero no es en todos los casos»*. Como **no es en todos los
    casos**, esto no decide nada por sí solo: es una medida, y quién la usa es
    la prioridad que el paso de descripción fijó para esa etapa.

    Se mide con la misma maquinaria que `depurar.py` usa después —repetición
    dentro del trozo y tartamudeo— porque tiene que predecir exactamente lo que
    ese paso va a recortar. Y se mide **sobre los finalistas**, no sobre las
    5.325 ventanas: es el mismo peldaño caro donde ya vive la expresividad.
    """
    trozos = depurar.trozos_con_voz(palabras, a, b)
    util = sum(y - x for x, y in trozos)
    if util <= 0:
        return 0.0
    t2 = [list(depurar.podar_dentro(palabras, x, y)) for x, y in trozos]
    t2 = [t for x, y in t2 for t in depurar.sin_tartamudeo(palabras, x, y)]
    return sum(y - x for x, y in t2) / util


def manda_la_voz(plan, vs, marcas, toma, rotas=(), prioridades=None,
                 verbose=True):
    """Entre las que dicen lo mismo, gana la que lo dice con más voz.

    Es el paso 3 de Jaime —*«se busca la frase exacta que cumpla la función y
    comunique lo que debe; entre las que dicen lo mismo manda la emoción»*— y
    estaba desconectado desde que la seleccion se rehizo: el texto decidia y la
    voz no votaba.

    Y va **aqui y no antes** por el embudo: medir el recorrido de F0 sobre las
    876 ventanas de un reel es carisimo y sobre los cinco finalistas de cada
    etapa es gratis. El recurso caro solo sobre lo que ya paso el filtro barato.

    Solo compiten las que estan **cerca en mensaje** (`beats.RELATIVO`): la voz
    no rescata a una que dice la mitad — el mensaje filtra primero, que es la
    regla que evito que una toma con 18,33 de F0 IQR se presentara como la mejor
    (aprendizaje 15). Y el escalon es `beats.PASO_VOZ`: por debajo de un cuarto
    de semitono la diferencia es ruido del detector, y entonces manda el texto.

    `prioridades` dice, por etapa, si ahí manda la **entrega** o la **limpieza**.
    Lo decide el paso de descripción mirando la pieza entera, no un umbral: la
    pregunta que resuelve es *si esta frase sale con un tartamudeo, ¿pierdo
    emoción o pierdo el argumento?*. Donde manda la limpieza, la voz sigue
    contando —pero desempata en vez de decidir.

    `rotas` son las que `depurar.py` marco porque su mensaje se parte al quitar
    lo que no aporta. **No compiten menos: compiten con un escalon menos.** Es
    el sitio exacto donde cabe, porque aqui la moneda ya es la entrega — y la
    regla es que la fragmentacion solo pesa cuando el mensaje se rompe, nunca
    por contar cortes.
    """
    cambios = []
    # Las palabras de la cinta, una vez: `limpieza()` las necesita y cargarlas
    # por finalista serian cientos de lecturas del mismo fichero.
    try:
        pal = transcribir.exigir(toma)["segmentos"]
    except Exception:                             # noqa: BLE001
        pal = []
    for s0, k in enumerate(plan):
        if k is None or s0 >= len(marcas):
            continue
        fila = marcas[s0]
        cerca = [x for x in range(len(fila))
                 if fila[x] is not None and fila[x] >= fila[k] * beats.RELATIVO
                 and vs[x].get("toma") == toma]
        cerca = sorted(cerca, key=lambda x: -fila[x])[:beats.FINALISTAS]
        if len(cerca) < 2:
            continue
        medidas = {}
        for x in cerca:
            try:
                # **La emocion no tiene signo.** Jaime: *«ojo, no hay emociones
                # positivas o negativas: mas emocion es mas tristeza tanto como
                # mas rabia tanto como mas alegria»*.
                #
                # `expresividad` mide el recorrido de F0 y eso **premia lo
                # animado**: la tristeza baja el tono, ralentiza y estrecha el
                # rango, asi que puntuaba como plana. Medido en reel-06, «eso
                # suele ser una perdida silenciosa» —el momento mas grave de la
                # pieza— salia 3,11, el peor de su tramo; con la intensidad sale
                # 3,01, el mejor. Grave no es plano.
                #
                # `intensidad` mide la distancia a la neutralidad de ESA cinta
                # —su altura y su velocidad medias— y la devuelve sin signo.
                # Grave y lento puntua igual que agudo y rapido; lo unico que
                # puntua bajo es lo tibio, que es lo unico que no transmite.
                #
                # El recorrido se conserva como segundo termino, con un cuarto
                # del peso: dice si dentro del tramo la voz se mueve, que es
                # otra cosa distinta de estar lejos del punto cero.
                _i = beats.intensidad(toma, vs[x]["a"], vs[x]["b"], pal)
                medidas[x] = (
                    float(_i.get("intensidad") or 0.0)
                    + float(beats.expresividad(toma, vs[x]["a"], vs[x]["b"])) / 4.0)
                vs[x]["intensidad"] = _i.get("intensidad")
                vs[x]["altura_st"] = _i.get("altura")
            except Exception:                     # noqa: BLE001
                medidas[x] = 0.0
            vs[x]["voz_st"] = round(medidas[x], 2)
        # El handicap NO toca `voz_st`: lo medido se guarda como se midio y solo
        # la comparacion lo descuenta. Si se guardara descontado, el informe
        # diria que la toma tiene menos voz de la que tiene.
        # La limpieza se mide aquí, junto a la voz: mismo peldaño del embudo,
        # mismos cinco finalistas.
        limpias = {}
        for x in cerca:
            try:
                limpias[x] = limpieza(pal, vs[x]["a"], vs[x]["b"])
            except Exception:                     # noqa: BLE001
                limpias[x] = 1.0
            vs[x]["limpieza"] = round(limpias[x], 3)
        manda_limpieza = (prioridades or {}).get(s0 + 1) == "limpieza"

        def _vale(x):
            v = medidas[x] - (beats.PASO_VOZ if x in rotas else 0.0)
            # Donde la etapa pide limpieza, la limpieza es la escala y la voz
            # desempata; donde pide entrega, al revés. Nunca se anula ninguna:
            # una toma limpia que no comunica no sirve, y una que comunica pero
            # se cae a pedazos tampoco.
            return (limpias[x] * 10 + v) if manda_limpieza else (v + limpias[x])
        mejor = max(medidas, key=_vale)
        # No se pisa con lo que ya ocupa otra etapa.
        choca = any(o is not None and o != k and vs[mejor].get("toma") == vs[o].get("toma")
                    and not (vs[mejor]["j"] < vs[o]["i"] or vs[mejor]["i"] > vs[o]["j"])
                    for o in plan)
        if (mejor != k and not choca
                and _vale(mejor) - _vale(k) > beats.PASO_VOZ):
            cambios.append((s0 + 1, medidas.get(k, 0.0), medidas[mejor]))
            plan[s0] = mejor
    if verbose and cambios:
        for etapa, antes, ahora in cambios:
            print(f"  la voz cambia la etapa {etapa}: {antes:.2f} -> {ahora:.2f} st")
    return plan


def a_tablero(plan, vs, libreto, frame, toma_por_k):
    """La toma leída y plana se va a tablero — **y ella misma es el copy**.

    Correccion de Jaime, en dos partes y las dos importan:

    - *«La toma leida compite si es entregada con expresividad.»* O sea que leer
      no descalifica: descalifica leer **sin voz**. Excluirla de entrada, como
      hice primero, tiraba tomas buenas por parecerse al libreto.
    - *«La toma leida es la ideal para generar tableros»*, y *«los tableros son
      ideales para ideas complejas»*. Ahi esta lo que no se me habia ocurrido:
      justo porque leer es exacto, **su texto es copy fiable** — dice lo que el
      libreto queria decir, palabra por palabra, sin tener que reescribir nada.

    Asi que esto no descarta: **traslada**. La etapa deja de ir con toma y pasa
    a tablero, con el texto de la propia lectura como contenido.

    Va al final y sobre la elegida, no sobre las mil candidatas, porque medir el
    recorrido de F0 es lo caro del proceso: es el embudo otra vez.
    """
    movidas = []
    for s0, k in enumerate(plan):
        if k is None or s0 >= len(libreto):
            continue
        # **La primera etapa no se va nunca a tablero: es el gancho.**
        #
        # Choque de reglas, y gana esta. `a_tablero` traslada lo leido y plano,
        # y en reel-03 se llevo la etapa 1 — asi que la pieza abria con un
        # cartel en vez de con su cara. Pero el gancho es *«cara y maxima
        # expresividad, mucho movimiento dentro de la toma»*: un tablero ahi
        # contradice el camino `portada` entero.
        #
        # Y ademas rompio el argumento: al irse la etapa 1, la tesis —«el
        # contador no es su estratega»— desaparecio del habla, y la etapa 2
        # arrancaba por la conclusion sin premisa. Jaime: *«el 3 esta mal de
        # logica y de respeto por la intencion comunicativa»*.
        #
        # Si la apertura lee y viene plana, el remedio no es taparla con un
        # cartel: es elegir otra apertura.
        if s0 == 0:
            continue
        lit = literal(vs[k]["texto"], libreto[s0])
        # **La voz se mide en TODAS las elegidas, no solo en las literales.**
        #
        # Se medía solo si leía, así que las demás llegaban como «no medida» —y
        # `plana` leía eso como «no plana», o sea como entregada. Resultado:
        # **cero tableros en los seis reels**, porque una idea densa con voz
        # desconocida se iba a plano cercano. Es la misma trampa de siempre: un
        # valor ausente interpretado como el valor bueno.
        #
        # Son 54 medidas —una por etapa elegida—, no mil: sigue siendo el
        # embudo, el recurso caro sobre lo que ya gano.
        if vs[k].get("voz_st") is None:
            try:
                vs[k]["voz_st"] = round(
                    float(beats.expresividad(toma_por_k(k), vs[k]["a"], vs[k]["b"])), 2)
            except Exception:                      # noqa: BLE001
                vs[k]["voz_st"] = None
        voz = vs[k].get("voz_st")
        vs[k]["literal"] = round(lit, 3)
        if lit < LEIDA:
            continue
        if voz is None:
            continue
        if voz >= VOZ_SALVA:
            continue          # lee, pero lo entrega: se queda
        movidas.append((s0 + 1, lit, voz, vs[k]["texto"]))
        vs[k]["a_tablero"] = True
    return movidas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reel", type=int)
    ap.add_argument("--todo", action="store_true", help="los finalistas de cada etapa")
    ap.add_argument("--sin-voz", action="store_true",
                    help="no mide expresividad (mas rapido, decide solo el texto)")
    ap.add_argument("--finalistas", type=int, default=5,
                    help="cuantas tomas por etapa se guardan en la base")
    ap.add_argument("--escalera", action="store_true",
                    help="afina con el modelo bueno la lista corta de TODAS las"
                         " etapas y vuelve a repartir de cero")
    ap.add_argument("--propia", action="store_true",
                    help="busca solo en la cinta del reel (el corte aun no sabe"
                         " abrir dos ficheros: ver `fuentes` en el EDL)")
    ap.add_argument("--edl", action="store_true",
                    help="escribe ads/<slug>/edl-sell.json con este reparto")
    a = ap.parse_args()

    n = a.reel
    slug = f"reel-{n:02d}"
    toma = rutas.TOMAS[slug]
    d = transcribir.exigir(toma)
    runs = json.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
    libreto = beats.beats_del_libreto(n)
    frame = beats.frame_del_reel(n, libreto)

    # La cinta propia primero —para que la cadena secuencial siga teniendo
    # sentido— y detras el resto del corpus.
    # **El corpus se descubre, no se lee del mapa.** Esto decia
    # `rutas.TOMAS.values()`, que es el mapa reel -> cinta escrito a mano, y por
    # eso la busqueda no salia de lo que alguien se habia acordado de apuntar.
    # `rutas.material()` existe justo para esto desde C-74 y no estaba
    # enchufada aqui, que es el unico sitio donde decide algo: una cinta que la
    # busqueda no mira no tiene candidatas, y entonces «esa frase no esta
    # grabada» es una afirmacion sobre el mapa, no sobre el material.
    otras = ([] if a.propia
             else [t for t in rutas.material() if t != toma])
    vs, datos = corpus([toma] + otras)
    palabras_de = {t: datos[t][0]["segmentos"] for t in datos}
    runs_de = {t: datos[t][1] for t in datos}
    print(f"{slug} · {toma}: {len(runs)} tramos → {len(vs)} ventanas candidatas")

    marcas = []
    for s, parr in enumerate(libreto):
        exige = (frame["beats"][s].get("debe_decir") or []
                 if s < len(frame["beats"]) else [])
        fila = []
        sig = libreto[s + 1] if s + 1 < len(libreto) else ""
        for v in vs:
            p, cubre, dice = puntuar(parr, exige, v, sig)
            v.setdefault("det", {})[s] = (cubre, dice)
            # **El umbral va sobre el mensaje, no sobre la puntuacion final.**
            # Con el castigo dentro, una ventana que dice justo lo que la etapa
            # necesita se caia por tener un extremo sucio — y el extremo sucio
            # se recorta, que es lo que hace `recortar()`. Asi la etapa se
            # quedaba sin toma teniendo material: paso en la 6 y la 7.
            # **Contener la cifra no es decir la etapa.** El reel 1 eligio
            # «estructura. 30.000 dolares no de ventas de estructura.» —cuatro
            # segundos de un tropiezo, cobertura **-0,07**— porque llevaba el
            # «30» que la etapa exige, y dejo fuera la tirada entera: «gana 180
            # mil al ano, sin estructura puede estar pagando 30 mil dolares mas
            # que uno que vende exactamente lo mismo». En el montaje eso salio
            # como «el gobierno de Canada rentas de estructura».
            #
            # Ganaba por ser corta: `puntua` descuenta lo que sobra del parrafo,
            # y un fragmento de cuatro palabras no tiene de donde sobrar. Asi
            # que `dice` deja de rescatar a cualquiera: rescata a quien ademas
            # **diga algo de la etapa**. Con el suelo, gana la tirada completa,
            # que encima trae las dos cifras que la pieza declara.
            fila.append(p if (cubre >= UMBRAL or (dice and cubre >= SUELO_DICE))
                        else None)
        marcas.append(fila)

    if a.escalera:
        tramos = escalera(slug, toma, marcas, vs)
        largo = sum(b - x for x, b in tramos)
        print(f"escalera: {len(tramos)} tramos ({largo:.0f}s de cinta) a afinar"
              f" con el modelo bueno, de {len(vs)} ventanas")
        d2, n = transcribir.afinar(toma, tramos)
        registro.nota("seleccionar", "escalera", detalle=f"{slug}: {n} tramos afinados")
        # **Y se reparte de cero**, no se confirma en el sitio: un tramo afinado
        # puede ser ahora el mejor de OTRA etapa.
        print(f"  {n} tramos afinados -> vuelvo a repartir de cero")
        vs, datos = corpus([toma] + otras)
        palabras_de = {t: datos[t][0]["segmentos"] for t in datos}
        runs_de = {t: datos[t][1] for t in datos}
        marcas = []
        for s0, parr in enumerate(libreto):
            ex = (frame["beats"][s0].get("debe_decir") or []
                  if s0 < len(frame["beats"]) else [])
            fila = []
            sig = libreto[s0 + 1] if s0 + 1 < len(libreto) else ""
            for v in vs:
                p, cubre, dice = puntuar(parr, ex, v, sig)
                v.setdefault("det", {})[s0] = (cubre, dice)
                fila.append(p if (cubre >= UMBRAL or (dice and cubre >= SUELO_DICE))
                            else None)
            marcas.append(fila)

    # **La que queda rota compite con handicap, no queda fuera.** `depurar.py`
    # anota cuando las costuras saltan idea y ademas queda todo en esquirlas;
    # aqui eso pesa, pero no elimina.
    #
    # Antes esto ponia `marcas[etapa][k] = None` y la toma desaparecia del
    # tablero. Jaime lo corto: *«el criterio no es temporal, el criterio es
    # emocional; la mejor es la que mas comunique, no la que menos cortes
    # tenga»*, y emocional en el sentido de *«la entrega emocional de un
    # mensaje»*. Eliminar por numero de costuras descarta justo a la que mas
    # comunica, porque la entrega viva trae falsos arranques.
    #
    # Asi que la rotura se paga en la **misma moneda que la entrega** —un escalon
    # de voz, `beats.PASO_VOZ`— y se cobra en `manda_la_voz`. Una toma rota que
    # dice el mensaje con medio semitono mas de recorrido se queda; una que
    # empata, pierde.
    _con = sqlite3.connect(BASE)
    fuera_pic = _con.execute(
        "select etapa_orden, desde, hasta from descartado where video_id = (select id from video where slug = ?)",
        (slug,)).fetchall()
    _con.close()
    rotas = set()
    for s0, dd, hh in fuera_pic:
        for k2 in range(len(vs)):
            if abs(vs[k2]["a"] - dd) < 0.3 and abs(vs[k2]["b"] - hh) < 0.3:
                rotas.add(k2)
    if rotas:
        print(f"  {len(rotas)} toma(s) con handicap por mensaje roto"
              f" (-{beats.PASO_VOZ} st, no eliminadas)")

    premio = [(PREMIO_OBLIG if (b.get("obligatorio") if i < len(frame["beats"]) else False)
               else PREMIO) for i, b in enumerate(frame["beats"])]
    premio += [PREMIO] * max(0, len(libreto) - len(premio))
    plan, total = encadenar(marcas, vs, premio=premio)
    # El orden de cinta es la preferencia, no la ley. Si soltarlo cubre mas
    # etapas, gana cubrir: una etapa vacia es un tablero mas y una tirada de
    # Jaime menos, y el orden nunca fue un requisito suyo.
    suelto, total_s = repartir_libre(marcas, vs, premio)
    if len(segs_ok(suelto)) > len(segs_ok(plan)):
        registro.nota("seleccionar", "reparto fuera de orden",
                      detalle=f"{slug}: {len(segs_ok(suelto))} etapas frente a"
                              f" {len(segs_ok(plan))} en orden de cinta")
        plan, total = suelto, total_s
    plan = sin_repetir(marcas, vs, plan, premio)
    if not a.sin_voz:
        # Qué prioriza cada etapa lo decidió el paso de descripción viendo la
        # pieza entera. Sin él, manda la entrega, que es el caso normal.
        _con = sqlite3.connect(BASE)
        try:
            prioridades = dict(_con.execute(
                "select etapa_orden, prioridad from escena_desc"
                " where video_id = (select id from video where slug = ?) and prioridad is not null", (slug,)))
        except sqlite3.OperationalError:
            prioridades = {}
        _con.close()
        plan = manda_la_voz(plan, vs, marcas, toma, rotas=rotas,
                            prioridades=prioridades)
    # **Las tres reglas de no-redundancia**, en este orden y por un motivo: se
    # poda dentro antes de mirar la costura, porque podar cambia donde empieza
    # la ventana; y los extremos se recortan al final, cuando ya no se mueven.
    for k in plan:
        if k is not None:
            ex_k = (frame["beats"][plan.index(k)].get("debe_decir") or []
                    if plan.index(k) < len(frame["beats"]) else [])
            pa_k = libreto[plan.index(k)] if plan.index(k) < len(libreto) else ""
            vs[k] = {**podar_dentro(vs[k], palabras_de[vs[k]["toma"]], pa_k, ex_k),
                     "det": vs[k].get("det", {}), "toma": vs[k]["toma"]}
    plan = limpiar_costura(plan, vs, palabras_de)
    for k in plan:
        if k is not None:
            t_k = vs[k]["toma"]
            antes = vs[k]
            despues = remedir(recortar(antes, palabras_de[t_k]), runs_de[t_k])
            # **El suelo se comprueba DESPUES de recortar, no solo antes.**
            #
            # `MIN_VOZ` filtra al construir las ventanas, pero el recorte de
            # extremos y la poda de repeticiones se aplican despues y pueden
            # dejarla en nada: el reel 5 salio con una etapa de **0,16
            # segundos** —«un trimestre un ano normal»— que no es un enunciado,
            # es un resto. Si recortar la deja por debajo del suelo, el recorte
            # era el error: se vuelve a la ventana entera.
            if despues["voz"] < MIN_VOZ <= antes.get("voz", 0):
                registro.aviso("seleccionar", "el recorte dejaba la etapa en nada",
                               detalle=f"{slug} {despues['voz']:.2f}s de"
                                       f" {antes['voz']:.2f}s — se deja entera",
                               eco=False)
                despues = remedir(antes, runs_de[t_k])
            vs[k] = {**despues, "det": vs[k].get("det", {}), "toma": t_k}
    # **Recortar puede llevarse el dato declarado.** `dice` y `cubre` se
    # calcularon sobre la ventana entera, y despues se le quitaron extremos: la
    # etapa 7 del reel 1 salia marcada DICE con un texto donde la cifra ya no
    # estaba. Se vuelve a puntuar sobre lo que de verdad queda, y si el dato se
    # perdio se avisa — es exactamente el fallo silencioso de C-19.
    # Lo que Jaime ya juzgo entra aqui, DESPUES de repartir y ANTES de puntuar
    # otra vez: asi su rango se mide igual que los demas y sale en el informe.
    plan = manda_jaime(plan, vs, slug, d["segmentos"], runs, marcas, toma)
    perdidos = []
    for s2, k in enumerate(plan):
        if k is None:
            continue
        exige = (frame["beats"][s2].get("debe_decir") or []
                 if s2 < len(frame["beats"]) else [])
        parr = libreto[s2] if s2 < len(libreto) else ""
        _, cubre2, dice2 = puntuar(parr, exige, vs[k])
        antes = vs[k]["det"].get(s2, (0, 0))[1]
        vs[k]["det"][s2] = (cubre2, dice2)
        if antes and not dice2:
            perdidos.append((s2 + 1, exige))
    # La lectura plana se traslada a tablero, con su propio texto de copy.
    a_tab = a_tablero(plan, vs, libreto, frame,
                      lambda k: vs[k].get("toma") or toma)
    repes = una_sola_vez(plan, vs, frame)

    print(f"reparto: {sum(1 for k in plan if k is not None)}/{len(libreto)}"
          f" etapas con toma · puntuacion {total:.2f}")
    for etapa, lit, voz, txt in a_tab:
        print(f"  A TABLERO: etapa {etapa} — lee el libreto al {lit:.0%} y lo"
              f" entrega plano ({voz:.1f} st). Su texto es el copy del tablero.")
        print(f"      «{txt[:110]}»")
        registro.nota("seleccionar", "lectura plana a tablero",
                      detalle=f"{slug} etapa {etapa}: literal {lit:.2f}, voz {voz:.1f}")
    for etapa, exige in perdidos:
        print(f"  OJO: la etapa {etapa} exige {exige} y el recorte se lo llevo")
        registro.aviso("seleccionar", "el recorte se llevo el dato exigido",
                       detalle=f"{slug} etapa {etapa}: {exige}", eco=False)
    for t, _etapa, donde in repes:
        sitios = ", ".join(f"etapa {o} ({a:.1f}s)" for o, a in donde)
        print(f"  REDUNDANTE: «{t}» se dice en {len(donde)} sitios — {sitios}")
        registro.aviso("seleccionar", "dato repetido en la pieza",
                       detalle=f"{slug} «{t}»: {sitios}", eco=False)
    print()
    for s, k in enumerate(plan):
        etapa = (frame["beats"][s].get("etapa") if s < len(frame["beats"]) else "") or ""
        exige = (frame["beats"][s].get("debe_decir") or []
                 if s < len(frame["beats"]) else [])
        cab = f"{s + 1}. {etapa}" + (f"  [exige {', '.join(exige)}]" if exige else "")
        if k is None:
            print(f"{cab}\n    SIN TOMA → tarjeta\n")
            continue
        v = vs[k]
        cubre, dice = v["det"][s]
        print(f"{cab}\n    {v['a']:7.2f}-{v['b']:7.2f}  voz {v['voz']:5.1f}s"
              f"  aire {v['aire']:4.1f}s  cubre {cubre:.2f}"
              f"{'  DICE' if dice else ''}")
        print(f"    {v['texto'][:220]}\n")
        if a.todo:
            top = sorted((x for x in range(len(marcas[s])) if marcas[s][x] is not None),
                         key=lambda x: -marcas[s][x])[:5]
            for x in top:
                w = vs[x]
                print(f"      {marcas[s][x]:+.2f}  {w['a']:7.2f}-{w['b']:7.2f}"
                      f"  {w['texto'][:110]}")
            print()

    if a.edl:
        ruta, voz = escribir_edl(slug, plan, vs, libreto, frame, runs)
        print(f"-> {ruta}  ({len(segs_ok(plan))} cortes, {voz:.1f}s de voz)")

    guardar(slug, toma, plan, vs, libreto, frame, marcas, a.finalistas)


def guardar(slug, toma, plan, vs, libreto, frame, marcas=None, finalistas=5):
    """Deja el reparto en el modelo, no en una tabla plana.

    Sustituye a `propuesta`, que guardaba `desde`, `hasta` y `texto` dentro de
    la fila de la eleccion: el fragmento no existia como cosa, era un atributo
    de la decision. Jaime: *«no creo que este al tercer grado si cada uno de
    estos elementos no tiene su propia instancia»*, y *«el punto es dejar de
    depender de tu memoria y construir un modelo coherente»*.

    Aqui cada cosa va a su sitio y una sola vez: el parrafo a `libreto`, el
    trozo de cinta a `fragmento`, las unidades que abarca a `fragmento_unidad`,
    y la decision —solo la decision— a `eleccion`.
    """
    con = sqlite3.connect(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(io.open("scripts/esquema.sql", encoding="utf-8").read())

    vid = con.execute("select id, toma_id from video where slug = ?", (slug,)).fetchone()
    if not vid:
        registro.error("seleccionar", "el video no esta en la base",
                       detalle=f"{slug}: corre python scripts/db.py migrar")
        con.close()
        return
    video_id, toma_id = vid

    # El libreto: la intencion comunicativa, una fila por etapa.
    for i, parr in enumerate(libreto):
        con.execute("insert into libreto (video_id, orden, texto) values (?,?,?)"
                    " on conflict(video_id, orden) do update set texto = excluded.texto",
                    (video_id, i + 1, parr))

    etapas = dict(con.execute(
        "select orden, id from etapa where video_id = ?", (video_id,)).fetchall())
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    puestos = 0
    for s0, k in enumerate(plan):
        eid = etapas.get(s0 + 1)
        if eid is None:
            continue
        if k is None:
            con.execute("insert into eleccion (etapa_id, fragmento_id, quien, fecha)"
                        " values (?,NULL,?,?) on conflict(etapa_id) do update set"
                        " fragmento_id = NULL, quien = excluded.quien,"
                        " fecha = excluded.fecha", (eid, "seleccionar", ahora))
            continue
        v = vs[k]
        t_v = v.get("toma") or toma
        ft = con.execute("select id from toma where nombre = ?", (t_v,)).fetchone()
        ft = ft[0] if ft else con.execute(
            "insert into toma (nombre) values (?)", (t_v,)).lastrowid
        con.execute("insert or ignore into fragmento (toma_id, desde, hasta, origen)"
                    " values (?,?,?,?)",
                    (ft, v["a"], v["b"], v.get("de_jaime") or "reparto"))
        fid = con.execute("select id from fragmento where toma_id=? and desde=? and hasta=?",
                          (ft, v["a"], v["b"])).fetchone()[0]
        # Las unidades que abarca: el texto vive ahi, no aqui.
        con.execute("delete from fragmento_unidad where fragmento_id = ?", (fid,))
        con.executemany(
            "insert or ignore into fragmento_unidad (fragmento_id, unidad_id) values (?,?)",
            [(fid, r[0]) for r in con.execute(
                "select id from unidad where toma_id=? and hasta>? and desde<?",
                (ft, v["a"], v["b"]))])
        cubre, dice = v["det"].get(s0, (None, 0))
        con.execute("insert into eleccion (etapa_id, fragmento_id, cubre, dice, quien, fecha)"
                    " values (?,?,?,?,?,?) on conflict(etapa_id) do update set"
                    " fragmento_id=excluded.fragmento_id, cubre=excluded.cubre,"
                    " dice=excluded.dice, quien=excluded.quien, fecha=excluded.fecha",
                    (eid, fid, cubre, int(dice),
                     "jaime" if v.get("de_jaime") else "seleccionar", ahora))
        puestos += 1
    # **Las OTRAS tomas de cada etapa.** La relacion no es 1:1: Jaime graba
    # varias veces lo mismo y por eso se escoge la mejor. Sin guardarlas, decir
    # «esta no sirve, usa la siguiente» obliga a repetir la seleccion entera y
    # a confiar en que de lo mismo; y ademas no se ve **por que** gano una,
    # porque una puntuacion sin las otras al lado es un numero suelto.
    if marcas:
        con.execute(
            "delete from candidato where etapa_id in"
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
            orden = ([elegido] if elegido is not None else []) +                     [k for k in top if k != elegido]
            for puesto, k in enumerate(orden, 1):
                v = vs[k]
                t_v = v.get("toma") or toma
                ft = con.execute("select id from toma where nombre = ?",
                                 (t_v,)).fetchone()
                if not ft:
                    continue
                con.execute("insert or ignore into fragmento"
                            " (toma_id, desde, hasta, origen) values (?,?,?,?)",
                            (ft[0], v["a"], v["b"], "candidata"))
                fid2 = con.execute(
                    "select id from fragmento where toma_id=? and desde=? and hasta=?",
                    (ft[0], v["a"], v["b"])).fetchone()[0]
                cu, di = v.get("det", {}).get(s0 - 1, (None, 0))
                # `vs` crece con las ventanas que anade `manda_jaime`, asi
                # que un indice puede caer fuera de `marcas`: esas no tienen
                # puntuacion porque no compitieron — las puso Jaime.
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
                    (eid, fid2, puesto, pun, cu, int(di), v.get("voz_st"),
                     None if pun is not None else "elegida por Jaime"))

    # `propuesta` era el atajo denormalizado. Se va: dos sitios diciendo lo
    # mismo es de donde salen los fallos de este proyecto.
    con.execute("drop table if exists propuesta")
    con.commit()
    con.close()
    print(f"modelo: {puestos} elecciones con fragmento, {len(libreto)} parrafos de libreto")


if __name__ == "__main__":
    main()
