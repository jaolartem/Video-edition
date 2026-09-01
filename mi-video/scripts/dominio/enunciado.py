"""Cómo se parte una cinta en **unidades de sentido**, y no en trozos de tiempo.

Ésta es la corrección más importante que ha tenido el montaje, y viene de Jaime:
*«sólo una frase u oración equivalente, con la mayor continuidad posible; no
fragmentos, no secciones»*.

Antes los candidatos salían del detector de silencio, y un tramo de silencio **no
es una unidad de sentido**: empieza y acaba donde el hablante respira. De los 48
enunciados del lote anterior **sólo 5 eran frases completas** y 33 estaban rotos
por los dos extremos. Por eso el reel 1 quedó «supremamente roto» — no era el
orden ni el frame, era que cada pieza era media frase.

**Aquí sólo se parte; no se juzga.** Qué unidad cumple qué etapa lo decide
`dominio.candidata`, y qué se dice dos veces dentro de una, `dominio.poda`. Son
tres oficios y estaban en el mismo sitio.

## Lo que sale de aquí sigue siendo un `dict`

A propósito, y con fecha de caducidad. La unidad viaja a `catalogar.py`,
`candidatos.py` y `seleccionar.py`, y de ahí a un JSON: convertirla en objeto hoy
obliga a tocar los tres a la vez. Se declara la deuda en vez de esconderla —
`clave`, `pal`, `a`, `b` son las claves que esos tres esperan.
"""
from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import vocabulario as _voc  # noqa: E402

# Margen que el detector de silencio deja a cada lado del habla. Recortarlo
# quita el aire muerto que queda entre corte y corte: son decimas por escena,
# pero con veinte escenas son segundos, y Jaime lo describio como «poco
# dinamico». Se deja lo justo para no comerse la consonante inicial.
CENIDO = 0.09
# Hueco maximo DENTRO de una frase, medido entre tramos de voz. Por encima de
# esto no es una pausa: son dos intentos que whisper unio en una sola oracion,
# y al montarlos se oye el agujero.
# **Techo de aire interno.** Estuvo en 1,2 s y **descartaba la frase entera**:
# «por cada 100 dolares que el vende, se queda con 67» lleva 7,0 s de pausa
# dentro -Jaime pensando- y no existia como candidato, que es por lo que el reel
# 2 no daba ninguna de las dos cifras. A 12 s solo caza lo que de verdad son dos
# ideas distintas que whisper unio. El aire se reporta y lo quita el corte.
HUECO = 12.0
# Silencio que separa dos INTENTOS. No es la pausa de respirar: Jaime graba de
# una sola toma —*«pueden tener silencios intermedios pero fueron grabadas de
# una sola toma… puedes borrar silencios intermedios pero no puedes cambiar de
# toma o seleccionar varias»*—, asi que la unidad es el intento entero y sus
# pausas se quitan al cortar (`plan-reel.mjs` las interseca con el habla).
#
# Con 0,45 s se partia DENTRO de una frase: salian «mil dolares que no son por
# venta son por tener la estructura» como si fuera una unidad. Con 0,9 s las
# unidades son intentos.
# **PAUSA se retira, y se deja dicho por que.** Partia la unidad en cada silencio
# de 0,9 s, y eso contradice la regla de Jaime: *«hay silencios entre la misma
# frase; no significan que sean otra toma»*. Si alguien la vuelve a introducir,
# vuelve el reel 2 mutilado. Ver C-45.
# Por encima de esto, lo que whisper llama «oracion» no lo es: en el reel 1 hay
# una de 91 s. Son diez intentos sin puntuar y hay que partirlos.
# Con las pausas dentro, una frase real puede durar 15 s de reloj y 8 de voz.
# El troceo por pausa mayor es justo lo que Jaime rechaza, asi que solo debe
# saltar cuando whisper lleva mucho rato sin poner un punto.
MAX_ORACION = 35.0

# Signos con que whisper cierra una frase. Los abre `¿` y `¡`, que en español
# son parte del arranque y por eso cuentan como mayúscula.
FIN = ".?!…"


def _en_run(t, runs):
    """El tramo de voz que contiene ese instante, o None."""
    for a, b in runs:
        if a <= t <= b:
            return (a, b)
    return None


def oraciones(toma):
    """
    Los candidatos son **oraciones completas**, no tramos de silencio.

    El transcript de whisper trae mayúsculas y puntuación, así que la oración se
    reconstruye: abre en mayúscula (o en `¿` `¡`) y cierra en `.` `?` `!`. Las
    palabras sueltas anteriores a la primera mayúscula se tiran — son la cola del
    intento anterior.

    ## Las palabras largas y los silencios: se cruzan dos fuentes, no se estima

    Jaime: *«asegúrate de resolver el problema de las palabras muy largas o de
    los silencios muy largos; a veces están enmarcados en errores del whisper»*.
    Y tiene razón en el diagnóstico: **la duración de una palabra no es un dato
    de audio**, es texto con un tiempo colgado. Whisper le atribuye a cada
    palabra el silencio que viene detrás, así que una pausa de respiración
    produce una «palabra de dos segundos» que no existe.

    Un umbral no resuelve eso — sólo elige a qué lado equivocarse. Con 1,5 s se
    caían todos los candidatos del reel 3; con 3 s pasaban huecos reales.

    Lo que sí es dato de audio son **los tramos con voz** que midió el detector
    de silencio (`work/cuts/`). Así que aquí se cruzan las dos fuentes:

    1. **El final de cada palabra se recorta al final de su tramo de voz.** Una
       palabra ya no puede «contener» un silencio, y las palabras largas
       desaparecen porque nunca fueron largas.
    2. **El aire se mide entre tramos**, que es donde el silencio está medido de
       verdad, no entre palabras.
    3. Si dentro de la frase hay un hueco de más de `HUECO`, no es una pausa:
       son dos intentos que whisper unió en una frase. Se descarta.

    El transcript dice **lo que se dijo**; los tramos, **dónde hubo voz**. Para
    juzgar tiempos manda el segundo — es el aprendizaje 19 aplicado a otra cosa.
    """
    import transcribir

    ws = transcribir.exigir(toma)["segmentos"]
    runs = json.load(open(f"work/cuts/{toma}.json",
                          encoding="utf-8"))["segmentos"]

    # Recorte de cada palabra a su tramo de voz.
    limpio = []
    for w in ws:
        r = _en_run(w["start"], runs)
        fin_real = min(w["end"], r[1]) if r else w["end"]
        limpio.append({**w, "end": max(w["start"], fin_real), "run": r})

    # **La unidad la cierra la PUNTUACION, no el silencio.**
    #
    # Regla de Jaime, y es la que este fichero llevaba escrita en el docstring y
    # contradicha en el codigo: *«hay silencios entre la misma frase; esto es
    # clave, no significan que sean otra toma. Solo me quede callado pensando o
    # validando la idea en mi cabeza, o como movimiento natural»*.
    #
    # Con `PAUSA` partiendo por silencio, una pausa de pensar cortaba la frase en
    # dos y ninguna de las dos mitades decia la idea entera. Es el origen de todo
    # lo que el paso 2 refuto en el reel 2: «corta en *vendiendo lo* sin llegar
    # al 67», «arranca sin sujeto», «cierra en coma». Las unidades estaban rotas,
    # no las frases.
    #
    # Una unidad va de un final de frase al siguiente. Las pausas de dentro
    # **se quedan dentro** y las quita el corte, que interseca con los tramos de
    # habla (`plan-reel.mjs`). El unico limite es `MAX_ORACION`, para el caso en
    # que whisper no ponga un punto en mucho rato.
    partidas, trozo = [], []
    for w in limpio:
        trozo.append(w)
        if re.search(r"[.!?]$", w["text"].strip()):
            partidas.append(trozo)
            trozo = []
    if trozo:
        partidas.append(trozo)

    # Un intento muy largo se parte por su pausa mayor hasta caber. Por encima
    # de MAX_ORACION ya no es un intento: es la toma entera sin cortar.
    def trocear(f):
        if f[-1]["end"] - f[0]["start"] <= MAX_ORACION or len(f) < 4:
            return [f]
        # **Se parte por la coma, no por la pausa.**
        #
        # Partir por el silencio mas largo es exactamente lo que Jaime rechaza:
        # esa pausa suele estar **dentro** de la frase -«se queda ... con 67»
        # lleva 7 s en medio- y cortar ahi deja las dos mitades sin sentido. La
        # coma la puso whisper donde la frase respira de verdad, que es una
        # juntura sintactica y no una de aliento.
        #
        # El silencio mayor queda como ultimo recurso, para cuando no hay ni una
        # coma en 35 segundos.
        medio = len(f) // 2
        comas = [i for i in range(1, len(f) - 1)
                 if f[i - 1]["text"].strip().endswith(",")]
        if comas:
            corte = min(comas, key=lambda i: abs(i - medio))
        else:
            mejor, corte = 0.0, None
            for i in range(1, len(f) - 1):
                r1, r2 = f[i - 1]["run"], f[i]["run"]
                h = (r2[0] - r1[1]) if (r1 and r2 and r1 != r2) else 0.0
                if h > mejor:
                    mejor, corte = h, i
            if corte is None:
                corte = medio
        return trocear(f[:corte]) + trocear(f[corte:])

    partidas = [t for f in partidas for t in trocear(f)]

    cands = []
    for f in partidas:
        a, b = f[0]["start"], f[-1]["end"]
        txt = " ".join(w["text"] for w in f).strip()
        if len(txt) < 25:
            continue
        if re.search(r"[\[\*]", txt):
            continue
        # Ninguna palabra sin tramo de voz: si whisper la situó en el silencio,
        # no la oyó ahí.
        if any(w["run"] is None for w in f):
            continue
        # Aire interno medido entre tramos de voz, no entre palabras.
        huecos = []
        for i in range(len(f) - 1):
            r1, r2 = f[i]["run"], f[i + 1]["run"]
            if r1 and r2 and r1 != r2:
                huecos.append(max(0.0, r2[0] - r1[1]))
        if any(h > HUECO for h in huecos):
            continue
        # **La duracion que cuenta es la de voz, no la de reloj.** Con las pausas
        # dentro, una frase de 8 s de habla puede ocupar 15 s de cinta; medir el
        # reloj descartaba justo las que Jaime dice que hay que conservar.
        voz = (b - a) - sum(huecos)
        if not (2.0 <= voz <= 22.0):
            continue
        cands.append({
            # Las palabras con sus tiempos: hacen falta para recortar la cola de
            # una unidad por donde empieza a repetir la siguiente.
            "pal": [[w["start"], w["end"], w["text"]] for w in f],
            "a": a - CENIDO * 0.5, "b": b + CENIDO * 0.5,
            "texto": txt, "clave": set(_voc.contenido(txt)),
            "aire": round(sum(huecos), 2),
            # **Se marca, no se descarta.** Un trozo salido de una oracion
            # partida no acaba en punto aunque sea una idea entera: la
            # puntuacion de whisper es justo lo que fallaba. Que se lea como
            # pensamiento completo lo juzga la IA — el codigo garantiza que
            # empieza y acaba en silencio, que es lo que si puede medir.
            "abre": bool(txt[:1].isupper() or txt[:1] in "¿¡"),
            "cierra": txt[-1:] in FIN,
        })
    return cands


def frase_con(ws, runs, termino, dice):
    """El tramo de cinta donde se dice un termino, acotado por las pausas.

    Antes devolvia «la frase» entre puntos, y whisper deja tramos enteros sin
    puntuar: en el reel 3 eso daba **98 segundos** para una etapa. La frase es la
    unidad, pero cuando la puntuacion no esta, quien delimita es el silencio
    medido — que es lo unico que hay.

    Se abre desde la palabra hacia los dos lados y se para en lo primero que
    aparezca: un final de frase, o una pausa de mas de 1,2 s.

    **Se catalogan TODAS las veces que se dice, no la primera.** Jaime: *«buscas
    pero no catalogas todo lo que hay en el video... si no encuentras nada es
    porque honestamente ni has mirado»*. Devolver la primera aparicion es dejar
    de mirar en cuanto algo encaja, y el material bueno suele estar mas
    adelante: **repite hasta que sale**. Se recorren todas y se devuelven en
    orden; **la ultima** es, por como graba, la version ajustada.
    """
    def hueco(x):
        """El silencio real entre dos palabras, medido con los tramos de voz.

        Los tiempos de whisper no dejan hueco entre palabras -el final de una es
        el principio de la siguiente- asi que restarlos siempre da cero y el
        corte no encontraba donde parar: devolvia 98 s de una tirada. El
        silencio esta en `work/cuts/`, que es donde se midio de verdad. Es el
        aprendizaje 19: el transcript dice lo que se dijo, los tramos dicen
        donde hubo voz, y para tiempos manda el segundo.
        """
        r1 = _en_run(ws[x]["start"], runs)
        r2 = _en_run(ws[x + 1]["start"], runs)
        return (r2[0] - r1[1]) if (r1 and r2 and r1 != r2) else 0.0

    hallados = []
    for k, w in enumerate(ws):
        if not dice(w["text"], termino):
            continue
        ini = k
        for x in range(k - 1, 0, -1):
            if re.search(r"[.!?]$", ws[x]["text"].strip()):
                ini = x + 1
                break
            if hueco(x) > 1.2:
                ini = x + 1
                break
            ini = x
        fin = k
        for x in range(k, len(ws) - 1):
            fin = x
            if re.search(r"[.!?]$", ws[x]["text"].strip()):
                break
            if hueco(x) > 1.2:
                break
        hallados.append((round(ws[ini]["start"], 3), round(ws[fin]["end"], 3)))
    return hallados


def texto_en(ws, rango):
    """Lo que se dice en un tramo de la cinta, **palabra a palabra**.

    Se lee del transcript y no de los candidatos: la apertura y el cierre se
    eligen de oido sobre la cinta entera, y su tramo puede no coincidir con
    ninguna unidad -en el reel 3 no lo hacia, asi que la comprobacion no tenia
    texto que comparar y no saltaba nunca.
    """
    a_, b_ = rango
    return " ".join(w["text"] for w in ws if a_ <= w["start"] <= b_)
