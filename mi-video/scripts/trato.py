"""Qué tratamiento lleva cada segmento, decidido y no declarado a mano.

Es el segundo de los dos pasos que Jaime señaló como fallidos: *«fallaron dos
pasos: el de escoger el vídeo dentro de los fragmentos posibles por variación de
tono y ritmo del habla, y dos, escoger qué tipo de renderizado tiene; habíamos
hablado de 3 opciones pero son más»*.

Hasta ahora el `trato` venía escrito a mano en `ads/frames.json`, así que no
respondía a lo que la toma es. Aquí se decide con lo que ya está medido: cuánto
reproduce el libreto (lectura), cuánta voz lleva, dónde cae en la pieza y qué
tipo de idea trae el párrafo.

## Los cinco tratamientos, y la regla de cada uno

**portada** — los primeros 5 segundos, y *«de los que el primero es clave»*.
Cara y máxima expresividad, mucho movimiento dentro de la toma, ganchos visuales
múltiples, sonido acompañando el título y los subtítulos animados. Maximalismo
coherente: romper el patrón y generar curiosidad antes de que el pulgar decida.

**tablero** — **leído**, o idea compleja. *«Los tableros son ideales para ideas
complejas.»* Y el copy sale de la propia lectura: por ser exacta dice lo que el
libreto quería, palabra por palabra.

**cercano** — idea densa **bien entregada**. Jaime: *«excepto si el delivery
emocional es especialmente bueno, en cuyo caso buscamos planos cercanos
enfatizando la emoción en la cara y animaciones que expliquen la idea»*.

Aquí llegaba también la toma **leída y bien entregada**, y eso se acabó con la
instrucción T-01: *«si en el audio se está leyendo, ese tramo va cubierto con
tablero: la cara no aparece en cámara limpia mientras se lee»*. La excepción del
delivery sigue valiendo para la idea densa —que es de lo que hablaba— pero no
para la lectura: leer bien es leer, y en R-04 se veía.

**metafora** — el párrafo trae un ejemplo concreto o una comparación obvia.
*«Cuando hablamos del dentista, una ilustración de un odontólogo puede ser útil;
o los símbolos de prohibido; o un camino que se divide en dos cuando decimos
usted no va a X.»* Metáforas visuales sencillas **con Jaime en cuadro**: no
sustituyen el plano, lo acompañan.

**diapositiva** — lo demás. CC animado que entra por un lado y sale por otro.

Y transversal a todos: **cada animación suena a lo que hace**. Si se pega como
pegatina suena a pegatina; si aparece letra a letra, suena el tecleo. Eso no es
un tratamiento, es una condición de todos.
"""
import re
import unicodedata

# El gancho son 5 s y el primero es el que decide. Antes se trataba como 1,3 s
# —lo que tarda el pulgar en irse— y eso es cuánto hay para enganchar, no cuánto
# dura el gancho.
GANCHO_S = 5.0
GANCHO_CLAVE_S = 1.0

# Umbrales, los mismos que usa la selección para que signifiquen lo mismo en los
# dos sitios: 0,60 de secuencia literal es lectura; 4,3 semitonos es entregarlo.
LEIDA = 0.60
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

# Una idea es compleja si encadena condiciones o cifras: eso es lo que un
# tablero resuelve y un plano hablado no.
COMPLEJA_PALABRAS = 40
# **Una cifra ya hace compleja la idea.** Estaba en dos y por eso casi nada
# llegaba a tablero: un calculo con un porcentaje es exactamente lo que un
# tablero resuelve y un plano hablado no — el espectador no puede rebobinar.
COMPLEJA_CIFRAS = 1

# Marcas de comparación y de ejemplo concreto. La lista es corta a propósito:
# lo que se busca es la figura que se puede DIBUJAR —dos caminos, una
# prohibición, un oficio— no cualquier símil.
COMPARA = ("como", "igual que", "en vez de", "mientras que", "frente a",
           "no va a", "no se queja", "por cada", "en cambio", "pero si")
CONCRETO = ("dentista", "odontologo", "medico", "doctor", "contador",
            "abogado", "electricista", "mecanico", "plomero", "vecino",
            "primo", "banco", "carta", "puerta", "muela", "yate", "mansion")


def _st(v):
    """Formatea una medida que puede no existir.

    Tercera vez que el mismo patron rompe algo: `voz_st` es None cuando la
    expresividad no se midio —solo se mide sobre los finalistas, que es el
    embudo— y formatearla como numero revienta. Antes paso con el acuerdo entre
    pasadas y con el NOT NULL de la tabla. **Hacer representable el «no medido»
    obliga a mirar todos los sitios que asumian un numero**, y este es el
    formateador para no volver a olvidarse.
    """
    return "sin medir" if v is None else f"{v:.1f} st"


# Igual que en `redundancia.py`: el dueño de esto es `dominio.texto`.
from dominio.texto import _sin_tildes as _limpio  # noqa: E402


def densidad(slug, orden, base="ads/decisiones.db"):
    """La densidad **la juzga la IA leyendo**, y aquí sólo se consulta.

    Correccion de Jaime: *«apenas tenemos los libretos o los segmentos podemos
    identificar la densidad; eso lo tienes que hacer tu como IA, no se si sea
    buena idea delegarlo a un Python»*. No lo es, y el primer intento lo
    demostro: contaba cifras y palabras, asi que «53,53% de impuesto marginal
    sobre un salario» y «cuesta 20 dolares» pesaban igual.

    Lo que un contador no puede ver, y esta en la tabla:

    - «lucir irrelevante y peligroso al mismo tiempo» es **alta** sin una sola
      cifra: es una paradoja con dos resultados simultaneos.
    - «el que paga mas no es el que menos trabaja» es **baja** aunque sea larga:
      es una tesis, no hay nada que sostener.

    Si no esta juzgada, **se dice** en vez de adivinar: un valor por defecto
    aqui es volver al contador de digitos por la puerta de atras.
    """
    import sqlite3
    import basedatos
    con = basedatos.abrir(base)
    r = con.execute("select nivel, figura, por_que from densidad"
                    " where video_slug = ? and etapa_orden = ?",
                    (slug, orden)).fetchone()
    con.close()
    return r if r else (None, None, "sin juzgar")


def decidido(slug, orden, base="ads/decisiones.db"):
    """El tratamiento que decidio el LLM mirando **la pieza entera**.

    Correccion de Jaime, y cambia el reparto de responsabilidades: *«el tablero
    no exige una lectura plana, la tolera, la permite; es alternativa cuando no
    hay una opcion mejor. La decision se da en funcion de dos variables,
    complejidad y necesidad del video, y por eso la debe tomar un LLM, porque el
    contexto es el video en general; la idea es que el LLM construya un video
    coherente con lo que hay»*.

    **La segunda variable no existe a nivel de segmento.** Un umbral solo ve la
    etapa que tiene delante: no sabe que la pieza ya lleva dos tableros cerca ni
    que vienen seis planos hablados seguidos, asi que no puede alternar. Por eso
    esto se consulta y no se calcula, igual que `densidad()`.

    Y por eso el umbral de abajo dejaba el lote **sin un solo tablero**: exigia
    entrega plana, pero el embudo escoge la toma mas expresiva, asi que nada de
    lo elegido bajaba del suelo. La lectura plana era un requisito y **tenia que
    ser una tolerancia**.

    Si nadie lo ha decidido devuelve `(None, None)` y manda la heuristica, que
    sigue sirviendo de red mientras el paso de descripcion no ha corrido.
    """
    import basedatos

    import sqlite3
    con = basedatos.abrir(base)
    try:
        r = con.execute("select trato, trato_porque from escena_desc"
                        " where video_slug = ? and etapa_orden = ?",
                        (slug, orden)).fetchone()
    except sqlite3.OperationalError:      # base vieja, sin la columna
        r = None
    con.close()
    return (r[0], r[1]) if r and r[0] else (None, None)


def dibujable(parrafo, texto):
    """¿Hay una comparación o un ejemplo concreto que se pueda dibujar?"""
    t = _limpio(parrafo) + " " + _limpio(texto)
    return (any(c in t for c in COMPARA) and any(c in t for c in CONCRETO))


def completa(slug, detalle):
    """El `trato` de cada etapa del detalle: lo que decidió quien describe, si
    falta, y **la portada en la etapa que abre el montaje, y sólo en ésa** (C-590).

    `decidir` ya lo dice —«la portada es mecánica y no se renegocia»—, pero el
    `trato` del JSON sólo se rellenaba si faltaba, así que una portada de otro
    corte se quedaba: reel-21, 19-10, la llevaba en e2. El gancho entraba a los
    5,03 s, en el tercio de Meta, y e1 iba como diapositiva. Se corrige en el
    sitio, sobre el detalle ya ordenado.
    """
    abre = (detalle[0] if detalle else {}).get("beat")
    for d in detalle:
        if d.get("beat") is not None and not d.get("trato"):
            t, porque = decidido(slug, d["beat"])
            if t:
                d["trato"], d["trato_porque"] = t, porque
        if d.get("beat") == abre:
            d["trato"] = "portada"
        elif d.get("trato") == "portada":
            t, _ = decidido(slug, d.get("beat"))
            d["trato"] = t if t and t != "portada" else "diapositiva"


def sin_cambios(slug, edl, ruta):
    """Sin tramos que poner, la portada se corrige igual (C-590), y sólo se
    escribe si algo cambió: lo que `fijar.aplicar` devuelve cuando no hay nada."""
    import json

    antes = [d.get("trato") for d in edl.get("detalle", [])]
    completa(slug, edl.get("detalle", []))
    if [d.get("trato") for d in edl.get("detalle", [])] != antes:
        json.dump(edl, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0, []


def decidir(*, desde_s, dura_s, parrafo, texto, literal, voz_st,
            nivel=None, figura=None, es_cta=False, decidido=None):
    """El tratamiento de un segmento, con el porqué.

    Devuelve `(trato, motivo)`. El motivo se guarda: un tratamiento sin razón
    escrita es un tratamiento que nadie puede discutir después.
    """
    if es_cta:
        return "cta", "es el registro"
    # **El gancho es UNO.** Jaime: *«definitivamente el gancho es uno de ellos
    # porque es diferente»* — en singular. Esto marcaba portada a todo segmento
    # que empezara dentro de los 5 s, asi que reel-04 y reel-05 llevaban dos
    # ganchos compitiendo por la atencion en los primeros segundos.
    #
    # El gancho es el segmento que **abre**, el que contiene el primer segundo,
    # que es el que decide. Los demas caen dentro de la ventana pero no son el
    # gancho: llevan su tratamiento normal, y las capas del gancho se estiran
    # sobre ellos porque el gancho dura 5 s aunque el segmento dure 2.
    if desde_s < GANCHO_CLAVE_S:
        return "portada", "el primer segundo, que es el que decide"
    leida = literal is not None and literal >= LEIDA
    plana = voz_st is not None and voz_st < VOZ_SALVA
    # **T-01 · Un tramo leido va cubierto, y eso no se delega.**
    #
    # Instruccion de Jaime, tras verse leyendo en camara limpia en R-04: *«si en
    # el audio se esta leyendo, ese tramo va cubierto con tablero: la cara no
    # aparece en camara limpia mientras se lee. El disparador es el audio, no el
    # frame. El tablero deja de ser un parche y pasa a ser lo que corresponde a
    # esos tramos por diseno»*.
    #
    # Va **antes** de `decidido` a proposito, con la portada y el CTA. Lo que se
    # le delega al LLM es el criterio —que necesita el contexto del video— y
    # esto no es criterio: es una condicion de la toma, medida, igual de
    # mecanica que saber cual es la etapa que abre. Debajo estaba, y por eso el
    # lote llego con ocho tramos leidos en camara limpia: dos que la heuristica
    # mandaba a `cercano` por venir bien entregados, y seis que el paso de
    # descripcion coloco en `metafora` o `diapositiva` sin saber que se leian.
    #
    # Y ya no exige que ademas venga plana. Esa condicion es la que cerro el
    # mecanismo entero una vez (C-68): pedia lo que el embudo elimina.
    if leida:
        return "tablero", (f"lee el libreto al {literal:.0%}: va cubierto con"
                           f" tablero, no en camara limpia ({_st(voz_st)})")
    # **Si el LLM ya lo decidio viendo la pieza entera, manda el LLM.**
    # La portada va antes porque es mecanica —es la etapa que abre— y no se
    # renegocia; el resto es criterio, y el criterio necesita el contexto del
    # video completo. Lo de abajo queda de red para cuando el paso de
    # descripcion no ha corrido todavia.
    if decidido and decidido[0] and decidido[0] != "portada":
        return decidido[0], (decidido[1] or "lo decidio el paso de descripcion")
    # **La complejidad basta para pedir tablero.** Jaime: *«los reels leidos o
    # con demasiada densidad y complejidad, en estos casos conviene un tablero,
    # excepto si el delivery emocional es especialmente bueno»*. Exigir ademas
    # que viniera plana dejaba casi todo en diapositiva — que es justo la queja
    # de que hay pocos tableros.
    if nivel == "alta":
        if plana:
            return "tablero", "idea densa y entrega plana"
        return "cercano", (f"idea densa pero entregada ({_st(voz_st)}):"
                           f" plano cerrado y animacion que la explique")
    if figura:
        return "metafora", f"se puede dibujar: {figura}"
    if nivel == "media":
        return "diapositiva", "densidad media sin figura: el CC lleva la idea"
    if nivel is None:
        return "diapositiva", "SIN JUZGAR la densidad — corre el paso de IA"
    return "diapositiva", "idea ligera: el CC basta"
