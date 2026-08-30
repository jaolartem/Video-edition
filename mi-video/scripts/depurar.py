"""Borra los segundos que no aportan. Después de elegir la escena, no antes.

Regla de Jaime, y señala un paso que faltaba: *«el filtro de la redundancia se
aplica después de escoger la escena; lo que no aporte, o los segundos que no
aporten, se deben borrar»*. Y el diagnóstico: *«noto con el primero que el
filtro contra redundancia no se aplicó — ese paso no está en código dentro del
pipeline»*.

Tenía razón. `seleccionar.py` poda **la selección**: quita repeticiones dentro
de la ventana, en la costura y el mismo dato en dos etapas. Pero eso decide qué
trozo se usa, no cómo se corta por dentro — así que lo que llegaba al montaje
seguía trayendo el aire y los intentos fallidos. El reel 1 abría con **ocho
segundos para decir cuatro palabras**.

## Los dos criterios, y por qué son distintos

**El aire.** Un hueco sin una sola palabra no aporta nada, y esto es formato
corto: poca repetición, velocidad y movimiento. Se corta por encima de
`AIRE_MAX`, no por debajo — las pausas cortas son el ritmo del habla, y Jaime ya
avisó de que un silencio dentro de una frase es él pensando, no otra toma.

Y el hueco se mide contra **las palabras**, no contra los tramos de habla. Ésa
es la lección cara del reel 1: el detector marca tramos por nivel de señal
—respiración, ruido, un arranque que no llegó a palabra— y ahí había 21,5
segundos de «habla» con dos palabras dentro. Es el aprendizaje 3 un nivel más
adentro: hay que intersecar con lo que **produjo texto**, que es lo único que el
espectador va a oír decir.

**La repetición.** Un trigrama de contenido que vuelve dentro del mismo corte es
un intento y su corrección. Se queda **el último**, porque así graba Jaime
—repite hasta que sale— y el de antes es el ensayo.

## Lo que ya NO hace, y es deliberado

**La redundancia de sentido no vive aqui.** Jaime, despues de ver tres intentos
algoritmicos fallar: *«la redundancia no es algo que se pueda inferir con codigo
facilmente; necesitariamos un modelo probabilistico de prediccion de lenguaje,
que es exactamente lo que tenemos contigo — no esta en la capacidad de Python ni
de ninguna de sus dependencias»*.

Esta comprobado. Un trigrama **no ve** que «de cada 100 dolares que el» y «100
dolares que el recibe el» son la misma frase empezada dos veces: no comparten
ninguno. Ni que «pero que el sistema se quedo» y «pero que el sistema capturo»
dicen lo mismo con otro verbo. El ultimo intento dejo la pieza mas larga que
antes.

Eso vive en `redundancia.py`, que es un paso de IA. Aqui se queda lo que se
mide: **el aire** y **el tartamudeo**.

## Lo que NO hace

No decide qué se dice: eso ya está decidido y no se toca. No quita pausas
retóricas ni junta frases que Jaime separó a propósito. Y **no recorta por
duración**: *«respeta el guion; si hay necesidad de recortar lo definimos al
final»*. Aquí sólo se va lo que no aporta nada — silencio y repetición.

    python scripts/depurar.py 1        # depura el EDL del reel 1
    python scripts/depurar.py --ver 1  # dice qué quitaría y no toca nada
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

# Por encima de esto, el hueco no es ritmo: es tiempo muerto. En formato corto
# medio segundo mirando una cara que no habla ya es una invitacion a deslizar.
AIRE_MAX = 0.5
# Y el margen que se deja alrededor de cada palabra para no comerse el ataque
# ni el final de la consonante.
MARGEN = 0.12
# **La fragmentacion no es un criterio: es una consecuencia.** Regla de Jaime:
# *«el criterio no es temporal, el criterio es emocional; la mejor es la que mas
# comunique, no la que menos cortes tenga — pero si los cortes rompen la
# continuidad del mensaje y queda todo fraccionado, la fuerza comunicativa se
# pierde»*. Y emocional en su sentido exacto: *«la entrega emocional de un
# mensaje»*, que son dos mitades — que llegue entero y que llegue con voz.
#
# Antes esto media un corte cada seis segundos y descartaba por ahi, y eso
# premia a la toma tibia: la entregada con mas voz trae mas falsos arranques y
# por tanto mas costuras, asi que **contar cortes descartaba justo lo que hay
# que quedarse**. Se comprobo en reel-01: descartar las dos mejores dejo la
# etapa 2 peor de lo que estaba (7 trozos/24 s -> 8 trozos/25 s).
#
# Lo que si rompe son dos cosas **a la vez**, tal y como el las dijo:
#   - la costura salta idea — se lleva palabras y mas de SALTO_MAX segundos, con
#     lo que el que escucha aterriza en otro sitio del mensaje;
#   - lo que queda son esquirlas — trozos por debajo de TROZO_IDEA, que no dan
#     para una idea.
# Quitar aire entre dos frases no rompe nada: ahi ya habia una frontera y el
# corte solo la usa. Por eso el aire no cuenta como costura rota.
SALTO_MAX = 0.8
TROZO_IDEA = 1.2
# Y por encima de que fraccion de cada cosa se declara fracturada. La mitad, en
# las dos: menos que eso es una toma con una costura fea, no un mensaje roto.
FRACTURA = 0.5


def trozos_con_voz(palabras, a, b):
    """Parte [a,b] en los tramos donde de verdad se dice algo."""
    ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
    if not ws:
        return []
    trozos = []
    ini = max(a, ws[0]["start"] - MARGEN)
    fin = ws[0]["end"]
    for w in ws[1:]:
        if w["start"] - fin > AIRE_MAX:
            trozos.append([round(ini, 3), round(min(b, fin + MARGEN), 3)])
            ini = w["start"] - MARGEN
        fin = w["end"]
    trozos.append([round(ini, 3), round(min(b, fin + MARGEN), 3)])
    return [t for t in trozos if t[1] - t[0] > 0.25]


def podar_dentro(palabras, a, b):
    """Corta la repeticion que ocurre DENTRO de un mismo trozo.

    Es la que se veia y la que no se estaba quitando: comparar trozos enteros no
    ve «eso eso no es mala suerte. Eso no es mala suerte. Eso no es...», que
    cabe entera en uno solo. Se busca el trigrama de contenido repetido y se
    entra en la ULTIMA aparicion — Jaime repite hasta que sale, asi que lo de
    antes es el ensayo.
    """
    ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
    cont = [(i, beats.norm(w["text"])[0]) for i, w in enumerate(ws)
            if beats.norm(w["text"])]
    for n in (4, 3):
        for x in range(len(cont) - 2 * n + 1):
            g = [c[1] for c in cont[x:x + n]]
            for y in range(x + n, len(cont) - n + 1):
                if [c[1] for c in cont[y:y + n]] != g:
                    continue
                # **Y lo de antes es el ensayo solo si lo de antes ES la
                # cabeza.** Esto entraba en la ultima aparicion y tiraba todo lo
                # anterior, repitiera o no. En reel-01 e2 el tramo declarado
                # empieza en «y los que usan esa estructura terminan ganando
                # mucho mas, terminan ganando mucho mas vendiendo…»: el trigrama
                # repetido es «terminan ganando mucho», y al entrar en el
                # segundo se llevo por delante **el puente**. La pieza pasaba de
                # «espera que usted tenga una cierta estructura y» a «terminan
                # ganando mucho», que no se sigue de nada.
                #
                # Jaime lo nombro por su nombre: *«se recortaron pasos
                # intermedios entre secciones y no secciones completas»*, y
                # *«pasar de ahi a "y cuando" rompe con la logica del video»*.
                #
                # Si antes de la primera aparicion hay texto que no repite, eso
                # no es un ensayo: es lo que hace que la frase siga. La
                # repeticion de en medio no se pierde — la quita
                # `sin_tartamudeo`, que corta el tramo duplicado y **conserva
                # los dos lados**, que es lo que habia que hacer desde el
                # principio.
                cabeza = ws[cont[x][0]]["start"] - a
                if cabeza > 0.4:
                    continue
                corte = ws[cont[y][0]]["start"] - MARGEN
                if corte - a < 0.2 or b - corte < 0.8:
                    continue
                return round(corte, 3), b
    return a, b


def partir_por_repeticion(palabras, a, b, n=3):
    """Parte un trozo alli donde una frase vuelve a empezar.

    `podar_dentro` encontraba UNA repeticion y recortaba la cabeza. Pero asi
    graba Jaime —*«se grabo asi para poder escoger una buena entre estas»*— y en
    un mismo trozo caben tres versiones seguidas de la misma frase: «el se queda
    con 64. el se queda con 67, por cada 100 dolares que el vende, se queda con
    67». Recortar la cabeza deja las otras dos.

    Aqui no se recorta nada: se **parte** en las versiones que hay, y quien
    elige es `sin_repetir`, que se queda con la mejor entregada. Partir y elegir
    son dos trabajos distintos y estaban mezclados en uno.
    """
    ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
    cont = [(i, beats.norm(w["text"])[0]) for i, w in enumerate(ws)
            if beats.norm(w["text"])]
    if len(cont) < 2 * n:
        return [[a, b]]
    vistos = {}
    cortes = []
    for x in range(len(cont) - n + 1):
        g = tuple(c[1] for c in cont[x:x + n])
        if g in vistos and x - vistos[g] >= n:
            t = ws[cont[x][0]]["start"] - MARGEN
            if (not cortes or t - cortes[-1] > 0.6) and t - a > 0.6 and b - t > 0.6:
                cortes.append(t)
        vistos.setdefault(g, x)
    if not cortes:
        return [[a, b]]
    out, ini = [], a
    for t in cortes:
        out.append([round(ini, 3), round(t, 3)])
        ini = t
    out.append([round(ini, 3), round(b, 3)])
    return out


def sin_tartamudeo(palabras, a, b):
    """Quita la palabra repetida de seguido: «el el», «y es y es», «que uno que uno».

    Es lo que queda cuando ya se fue la repeticion de frase, y es lo que se lee
    como error — Jaime: *«no se cortaron las partes redundantes o de error»*.

    Se corta la PRIMERA aparicion y se deja la segunda, que es la que sigue la
    frase. El trozo se parte en dos y se salta el tramo duplicado; los 50 ms de
    fundido por escena que ya aplica el corte tapan la costura.

    No toca la repeticion con intencion: «de cada 100 dolares que EL recibe... de
    cada 100 que USTED recibe» no es de seguido, asi que no entra aqui.
    """
    ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
    cont = [(i, beats.palabras(w["text"])[0]) for i, w in enumerate(ws)
            if beats.palabras(w["text"])]
    cortes = []
    k = 0
    while k < len(cont) - 1:
        # Una palabra repetida, o un par repetido: «y es y es».
        largo = 0
        # **Dos palabras iguales que se pisan en el tiempo no son un
        # tartamudeo: son la misma palabra contada dos veces.**
        #
        # Es el cinturon de C-64 aplicado aqui, que faltaba. El transcript sale
        # de varias pasadas y a veces deja la misma palabra duplicada con
        # tiempos solapados; tratarla como repeticion corta el audio donde solo
        # habia UNA palabra, y la palabra desaparece. Asi se fue el «20 dolares»
        # que cerraba la urgencia del reel 1 — el «dolares. dolares» del
        # transcript era uno solo.
        pisadas = (k + 1 < len(cont)
                   and ws[cont[k + 1][0]]["start"] < ws[cont[k][0]]["end"] - 0.01)
        if pisadas:
            k += 1
            continue
        if cont[k][1] == cont[k + 1][1]:
            largo = 1
        elif (k + 3 < len(cont) and cont[k][1] == cont[k + 2][1]
              and cont[k + 1][1] == cont[k + 3][1]):
            largo = 2
        if largo:
            # **El margen no puede comerse la palabra anterior.**
            #
            # `MARGEN` existe para no cortar el ataque de la consonante, pero
            # restado a secas mete el corte dentro de la palabra de antes — y en
            # habla rapida esa palabra dura menos de 0,12 s. Asi desaparecieron
            # tres palabras portantes del lote: «CRA» delante de «56 56», el
            # «mas» delante de «que uno que uno», y «20 dolares» delante de
            # «luego sube luego sube».
            #
            # El corte arranca, como mucho, donde acabo la palabra anterior. Si
            # no hay palabra anterior, el margen entero; si la hay, ella manda.
            ini = ws[cont[k][0]]["start"] - MARGEN
            if k:
                fin_previa = ws[cont[k - 1][0]]["end"]
                ini = max(ini, fin_previa + 0.01)
            fin = ws[cont[k + largo - 1][0]]["end"]
            cortes.append((max(a, ini), min(b, fin + 0.02)))
            k += largo
        k += 1
    if not cortes:
        return [[a, b]]

    def con_palabra(x, y):
        """¿Sobrevive alguna palabra en este trozo?"""
        return any(x - 0.01 <= w["start"] and w["end"] <= y + 0.01 for w in ws)

    # **Un trozo con una palabra dentro no se tira, dure lo que dure.**
    #
    # Esto descartaba todo lo que quedara por debajo de 0,25 s, y ahi caben
    # palabras cortas que llevan TODO el peso de la frase. Costo tres roturas de
    # argumento en el lote, y las tres del mismo modo:
    #
    #   «pagando 30 mil dolares MAS que uno que uno»  ->  se fue «mas»
    #   «dar al CRA 56 56»                            ->  se fue «CRA»
    #   «el bootcamp esta en 20 dolares»              ->  se fueron «20 dolares»
    #
    # Sin el «mas» la comparacion se invierte; sin «CRA» la cifra no tiene quien
    # la cobre; sin «20 dolares» la urgencia no cierra. La poda puede quitar
    # repeticion — nunca informacion. Ese es el limite, y el umbral de duracion
    # solo vale para lo que de verdad esta vacio.
    trozos, cursor = [], a
    for x, y in cortes:
        if con_palabra(cursor, x) or x - cursor > 0.25:
            trozos.append([round(cursor, 3), round(x, 3)])
        cursor = max(cursor, y)
    if con_palabra(cursor, b) or b - cursor > 0.25:
        trozos.append([round(cursor, 3), round(b, 3)])
    return trozos or [[a, b]]


def sin_repetir(palabras, trozos, toma=None):
    """Quita el intento cuando la misma idea vuelve: se queda la última.

    Se compara por trigramas de contenido, no por palabras sueltas: repetir
    «que» no es repetir, y repetir «no es mala suerte» sí.
    """
    fuera = []
    for k, (a, b) in enumerate(trozos):
        ws = [w for w in palabras if a <= w["start"] and w["end"] <= b]
        txt = " ".join(w["text"] for w in ws)
        fuera.append((k, txt, set(_trigramas(txt))))
    # **Cuando la misma idea vuelve, se ELIGE la que mejor la dice.**
    #
    # Antes se quedaba la ultima, por regla. Jaime lo corto: *«se escoge la que
    # mas comunique»*, *«pareciera que no hay criterio de seleccion»* — y no lo
    # habia. La razon de fondo la dio el mismo: *«se grabo asi para poder
    # escoger una buena entre estas»*. Las repeticiones del bruto no son basura
    # que recortar: son **un abanico donde hay que elegir**, y quedarse con la
    # ultima es tan arbitrario como quedarse con la primera.
    #
    # Y por que importa que sobre una sola: *«una herramienta de enfasis como la
    # repeticion deja de ser util cuando la utilizas todo el tiempo»*.
    familias = {}
    for i in range(len(fuera)):
        for j in range(i + 1, len(fuera)):
            gi, gj = fuera[i][2], fuera[j][2]
            if not gi or not gj:
                continue
            if len(gi & gj) / min(len(gi), len(gj)) > 0.6:
                raiz = familias.get(i, familias.get(j, i))
                familias[i] = familias[j] = raiz

    def entrega(k):
        """Lo que comunica ese trozo. Mismo criterio con el que se eligio la toma.

        Medir cuatro trozos de dos segundos es gratis y aqui ya estamos en el
        peldano caro, asi que la eleccion se paga con lo que decide de verdad.
        Sin toma no hay como medir y manda el ultimo, que es el comportamiento
        de antes.
        """
        if not toma:
            return float(k)
        a, b = trozos[k]
        if b - a < 0.6:
            return -1.0
        try:
            return (float(beats.expresividad(toma, a, b))
                    + beats.cambio_de_tono(toma, a, b) / 10.0)
        except Exception:                          # noqa: BLE001
            return float(k)

    grupos = {}
    for k, raiz in familias.items():
        grupos.setdefault(raiz, set()).add(k)
    quitar = set()
    for miembros in grupos.values():
        if len(miembros) > 1:
            quitar |= miembros - {max(miembros, key=entrega)}
    return [t for k, t in enumerate(trozos) if k not in quitar], quitar


def _trigramas(t):
    w = beats.norm(t)
    return [tuple(w[i:i + 3]) for i in range(len(w) - 2)]


# Una palabra de contenido: lo bastante larga como para que repetirla signifique
# algo. «diferente» si; «es», «no», «que» no. Cinco letras es donde cae la raya
# en castellano sin necesitar lista de vacias.
CONTENIDO = 5
# Cuantas palabras se miran a cada lado de la costura. Diez es una frase corta:
# mas alla, repetir una palabra ya no se oye como repeticion.
BORDE = 10


def cruza_el_corte(palabras, cola, cabeza):
    """La repeticion que ocurre ENTRE dos etapas, no dentro de una.

    Es el tercer sitio de la regla que el proyecto ya tenia escrita —*«dentro de
    la ventana, cruzando el corte, y el mismo dato en dos etapas»*— y era el
    unico sin implementar: `podar_dentro` y `sin_repetir` comparan trozos de la
    MISMA etapa, asi que el final de una contra el principio de la siguiente no
    lo miraba nadie.

    Jaime lo cazo dos veces en la misma pieza: *«en el segundo 55 "esto es
    diferente" sobra, acabas de decir "yo soy diferente aca no hacemos eso",
    redundancia de nuevo»*.

    Y no busca trigramas: «yo soy diferente» y «esto es diferente» no comparten
    ninguno. Busca **una palabra de contenido repetida cerca de la costura**, que
    es lo que se oye como repeticion aunque la frase sea otra.

    Devuelve el nuevo arranque de `cabeza`, o `None` si no hay que tocar nada.
    """
    a0, b0 = cola
    a1, b1 = cabeza
    fin = [w for w in palabras if a0 - 0.01 <= w["start"] and w["end"] <= b0 + 0.01]
    ini = [w for w in palabras if a1 - 0.01 <= w["start"] and w["end"] <= b1 + 0.01]
    if not fin or not ini:
        return None
    antes = {beats.norm(w["text"])[0] for w in fin[-BORDE:]
             if beats.norm(w["text"]) and len(beats.norm(w["text"])[0]) >= CONTENIDO}
    if not antes:
        return None
    for w in ini[:BORDE]:
        n = beats.norm(w["text"])
        if n and n[0] in antes:
            # Se corta HASTA esa palabra incluida: lo que repite se va y la
            # frase arranca en lo que aporta.
            nuevo = w["end"] + MARGEN
            # Y solo si queda pieza suficiente al otro lado.
            return round(nuevo, 3) if b1 - nuevo > 0.8 else None
    return None


def continuidad(palabras, trozos):
    """Cuanto de lo que se corto respeta la frontera que ya habia.

    Devuelve `(rotas, costuras, esquirlas)`. Una costura es **limpia** cuando lo
    que se llevo era silencio: ahi el hablante ya habia cerrado y el corte solo
    usa esa frontera. Es **rota** cuando se llevo palabras y mas de `SALTO_MAX`
    segundos — entonces el mensaje salta y el que escucha se cae.
    """
    rotas = costuras = 0
    for (_, y0), (x1, _) in zip(trozos, trozos[1:]):
        costuras += 1
        dentro = [w for w in palabras if y0 <= w["start"] and w["end"] <= x1]
        if dentro and (x1 - y0) > SALTO_MAX:
            rotas += 1
    esquirlas = sum(1 for x, y in trozos if y - x < TROZO_IDEA)
    return rotas, costuras, esquirlas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true", help="dice que quitaria")
    a = ap.parse_args()

    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        slug = f"reel-{n:02d}"
        ruta = os.path.join("ads", slug, "edl-sell.json")
        if not os.path.exists(ruta):
            continue
        edl = json.load(open(ruta, encoding="utf-8"))
        # **Depurar dos veces no depura mejor: depura de mas.** Este paso quita
        # el aire midiendo contra las palabras, y sobre su propia salida vuelve
        # a encontrar «aire» en los margenes que dejo — en reel-01, una segunda
        # pasada se llevo 48,3 s mas de una pieza ya limpia.
        #
        # En el camino canonico no pasa porque `seleccionar` regenera el EDL
        # antes; pasa cuando alguien corre el paso suelto. Se para, no se avisa:
        # un aviso sobre un EDL ya recortado llega tarde.
        # Se compara el NUMERO de segmentos, no la marca: `seleccionar` escribe
        # un EDL nuevo pero arrastra el bloque `revision`, asi que la marca sola
        # decia «ya depurado» sobre una seleccion recien hecha.
        if (edl.get("revision") or {}).get("depurado_n") == len(edl["segmentos"]):
            print(f"{slug}: ya depurado — se salta (corre seleccionar antes"
                  f" para rehacerlo)")
            continue
        fuentes = edl.get("fuentes") or []
        cache = {}

        segs, det, quitado, aire = [], [], 0.0, 0.0
        fragmentadas = []
        # Lo que la costura repite, para que lo resuelva quien compone.
        cruces = []
        brutos = {}
        for i, (rango, d) in enumerate(zip(edl["segmentos"], edl["detalle"])):
            toma = fuentes[i] if i < len(fuentes) else rutas.TOMAS[slug]
            if toma not in cache:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            pal = cache[toma]
            bruto = rango[1] - rango[0]
            brutos[d["beat"]] = (rango[0], rango[1])
            trozos = trozos_con_voz(pal, rango[0], rango[1])
            util = sum(y - x for x, y in trozos)
            aire += bruto - util
            # Primero dentro de cada trozo, luego entre trozos: son dos
            # repeticiones distintas y la de dentro no la ve la de fuera.
            # **Partir por repeticion NO se usa, y esta a proposito.**
            #
            # Se probo (`partir_por_repeticion`) y no converge: el trigrama no ve
            # que «de cada 100 dolares que el» y «100 dolares que el recibe el»
            # son la misma frase dicha dos veces, que es como se repite de
            # verdad. Partia donde no tocaba y la pieza salia mas larga.
            #
            # Jaime ya habia dado la respuesta antes de que yo lo intentara:
            # *«la IA debe leer los libretos producidos por la herramienta de
            # lectura cara para identificar estos patrones»*. Reconocer «esto es
            # la misma idea dicha tres veces» es comprension, no coincidencia de
            # n-gramas, y por eso vive en el paso de IA — igual que la densidad y
            # el tratamiento. Aqui se queda lo mecanico: aire y tartamudeo.
            trozos = [list(podar_dentro(pal, x, y)) for x, y in trozos]
            # Y el tartamudeo, que es lo que queda cuando ya se fue la
            # repeticion de frase y es lo que se lee como error.
            trozos = [t for x, y in trozos for t in sin_tartamudeo(pal, x, y)]
            trozos, tirados = sin_repetir(pal, trozos, toma)
            quitado += util - sum(y - x for x, y in trozos)
            if not trozos:
                trozos = [rango]        # antes dejarlo entero que dejarlo vacio
            # **Y la costura contra la etapa anterior.** Se mira aqui porque es
            # donde estan los dos lados a la vez: lo ultimo que quedo de la
            # etapa de antes y lo primero de esta. Ver `cruza_el_corte`.
            # **Y ya no corta: apunta.** Regla de Jaime, la misma de C-88:
            # *«la solucion es que el detector apunte y tu decidas caso a caso,
            # sin degradar el esfuerzo que haces»*.
            #
            # Cortaba hasta la palabra repetida incluida, y la palabra repetida
            # puede ser la unidad de dos cifras distintas. Medido en reel-01 e7:
            # la cola decia «550 dolares, semanales» y la cabeza «Esta semana el
            # bootcamp esta en 20 dolares»; la regla vio «dolares» a los dos
            # lados y se llevo **el precio de la oferta**, que es lo unico que la
            # pieza vende. El corte cayo en 584,78, que es el final de «dolares»
            # mas el margen: exacto y exactamente equivocado.
            #
            # Saber si «dolares» repetido es redundancia o son dos cifras exige
            # entender la frase, y eso no es aritmetica. Se anota y lo resuelve
            # quien compone, que para entonces tiene el texto de las dos etapas
            # delante.
            if segs and trozos:
                nuevo = cruza_el_corte(pal, segs[-1], trozos[0])
                if nuevo is not None:
                    cruces.append({"etapa": d.get("beat"),
                                   "corta_hasta": nuevo,
                                   "cola": " ".join(
                                       w["text"] for w in pal
                                       if segs[-1][0] <= w["start"] <= segs[-1][1])[-70:],
                                   "cabeza": " ".join(
                                       w["text"] for w in pal
                                       if trozos[0][0] <= w["start"] <= nuevo)})
            for t in trozos:
                segs.append(t)
                det.append({**d, "start": t[0], "end": t[1]})
            util2 = sum(y - x for x, y in trozos)
            rotas, costuras, esquirlas = continuidad(pal, trozos)
            # Las dos condiciones juntas, que es como el las dijo: que los
            # cortes rompan la continuidad **y** que quede todo fraccionado.
            picado = (costuras and rotas / costuras > FRACTURA
                      and esquirlas / len(trozos) > FRACTURA)
            if picado:
                fragmentadas.append((d["beat"], len(trozos), util2,
                                     rotas, costuras, esquirlas))
            if a.ver:
                print(f"  etapa {d['beat']:>2}: {bruto:5.1f}s -> {util2:5.1f}s"
                      f"  ({len(trozos)} trozo(s)"
                      f"{', ' + str(len(tirados)) + ' repetido(s) fuera' if tirados else ''})"
                      f"{f'   <-- FRACTURADA: {rotas}/{costuras} costuras saltan idea' if picado else ''}")

        print(f"{slug}: {len(edl['segmentos'])} cortes -> {len(segs)} · "
              f"{aire:.1f}s de aire y {quitado:.1f}s de repeticion fuera")
        for c in cruces:
            print(f"  costura e{c['etapa']}: se repite cerca del corte —"
                  f" «…{c['cola'].strip()}» / «{c['cabeza'].strip()}» —"
                  f" NO se corta: lo resuelve quien compone")
        # **El descarte se registra, si no el aviso es papel.** Sin esto,
        # `depurar` decia «esta queda picada» y la siguiente corrida volvia a
        # elegirla porque nada recordaba el descarte.
        import datetime
        import sqlite3
        con = sqlite3.connect("ads/decisiones.db")
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        for beat, k, dur, rotas, costuras, esquirlas in fragmentadas:
            r = [x for x in edl["detalle"] if x["beat"] == beat]
            orig = next((z for z in zip(edl.get("_antes", []), []) ), None)
            print(f"  etapa {beat}: {rotas}/{costuras} costuras saltan idea y"
                  f" {esquirlas}/{k} trozos no llegan a idea — el mensaje queda"
                  f" roto; compite con handicap, no queda fuera")
            # **Se anota hasta DOS veces por etapa, no indefinidamente.**
            # Si la tercera tambien queda rota, es que la cinta es asi ahi y
            # seguir anotando no cambia nada: el handicap ya esta puesto y la
            # que mas comunique se queda igual.
            ya = con.execute(
                "select count(*) from descartado where video_slug=? and etapa_orden=?",
                (slug, beat)).fetchone()[0]
            if ya >= 2:
                print(f"    (ya se descartaron {ya} para esta etapa: se queda"
                      f" esta, la cinta no da mas)")
                continue
            if r:
                con.execute(
                    "insert or replace into descartado (video_slug, etapa_orden,"
                    " desde, hasta, motivo, fecha) values (?,?,?,?,?,?)",
                    (slug, beat, brutos.get(beat, (0, 0))[0],
                     brutos.get(beat, (0, 0))[1],
                     f"mensaje roto: {rotas}/{costuras} costuras saltan idea,"
                     f" {esquirlas}/{k} trozos por debajo de {TROZO_IDEA}s", ahora))
            registro.aviso("depurar", "el mensaje queda roto",
                           detalle=f"{slug} etapa {beat}: {rotas}/{costuras}"
                                   f" costuras saltan idea",
                           eco=False)
        con.commit()
        con.close()
        if a.ver:
            continue
        edl["segmentos"] = segs
        edl["detalle"] = det
# **`fuentes` se deriva de `detalle`, no se re-indexa.** Al partir un corte en
        # varios trozos el indice deja de significar lo mismo, y `fuentes[min(i,
        # n-1)]` acababa diciendo una cinta y `detalle[i].toma` otra para el
        # mismo segmento — en reel-01, cinco segmentos apuntaban a una cinta que
        # ni siquiera llega a ese segundo.
        #
        # No rompio ningun render porque **nadie lee `fuentes`**: el corte usa
        # `detalle.toma`. Y eso es lo peligroso — un campo que existe, miente y
        # parece autoridad. Es el patron de `db.py`: dos fuentes para el mismo
        # dato se separan en cuanto una cambia, asi que solo puede haber una.
        edl["fuentes"] = [d.get("toma") or "" for d in det]
        edl["duracion_montada_s"] = round(sum(b - x for x, b in segs), 2)
        rev = dict(edl.get("revision") or {})
        rev["depurado_n"] = len(segs)
        rev["depurado"] = (f"Se quitaron {aire:.1f}s sin una sola palabra y "
                           f"{quitado:.1f}s de repeticion, midiendo contra las "
                           f"PALABRAS y no contra los tramos de habla. Ver "
                           f"scripts/depurar.py.")
        edl["revision"] = rev
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        registro.nota("depurar", "aire y repeticion fuera",
                      detalle=f"{slug}: {aire:.1f}s + {quitado:.1f}s")


if __name__ == "__main__":
    main()
