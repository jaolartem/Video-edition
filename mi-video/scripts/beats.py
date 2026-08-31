"""Monta el reel **por beats del libreto**, no por calidad de enunciado.

Por qué se reescribió
---------------------
El montaje anterior elegía enunciados por densidad y fluidez hasta gastar el
presupuesto. Con eso, cuatro intentos de la misma idea puntúan alto los cuatro y
entran los cuatro: el reel 1 decía «la mayoría de los emprendedores asume que si
vende más le va a quedar más» y catorce segundos después «la mayoría de gente
piensa que si usted vende mucho más va a conseguir más plata». Misma idea, otras
palabras — el detector de repetición no la ve porque compara n-gramas, y el
espectador sí la ve porque compara sentido.

Jaime: *«el frame debe estar presente siempre, y debe mantener el orden del
libreto así no se diga igual»*. Eso es exactamente lo que hace este montaje:

1. La estructura se parte en **etapas** — cada una, una función en el argumento.
   Cuáles son y en qué orden lo declara `ads/frames.json`. El frame no se deduce
   aquí: se lee.
2. Para cada etapa se busca en la toma el enunciado que mejor la cumple.
3. **Una etapa, un enunciado.** Cumplida, su idea queda cerrada para toda la
   pieza: los demás intentos de decirla quedan fuera, estén donde estén.
4. Salen **en el orden de la estructura**, no en el de la grabación.

El resultado no es «las mejores frases»: es el argumento entero, una vez cada
cosa, en el orden en que convence.

**El libreto es accidental; el módulo es el copy.** Jaime: *«no es el libreto lo
importante, lo importante es el framework y el copy… los módulos son el copy»*.
El párrafo del libreto entra aquí sólo como **vocabulario de su etapa** —una
forma de decirla, no la forma—, así que un enunciado que cumple la etapa con
otras palabras vale igual. Lo que no se negocia es la secuencia de la estructura
y que cada etapa se cumpla **una vez**.

Y el orden de prioridad es el que fijó Jaime: *«lo más importante es el mensaje,
lo que se dice; luego cómo se dice; luego cómo se ve»*. Aquí eso es literal —
**el texto filtra y la voz decide**, en dos pasos, no en una suma ponderada:
sólo compiten los enunciados que dicen el beat, y entre ellos gana el más
expresivo. Con la suma, una toma apagada que cubría un poco más ganaba a una
viva; con el filtro, la apagada ni siquiera compite si no dice el beat.

Uso:
    python scripts/beats.py --reel 1
"""
import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata

import numpy as np

# **La velocidad del montaje, y vive aqui porque la usan cinco pasos.**
#
# 1, no 1,15. Jaime, al ver las duraciones reales: *«ninguno hay que acelerar la
# verdad, todos estan por debajo de los 120 y en el rango de los 90s»*. A
# velocidad natural el lote va de 47,6 a 118,5 s, con cuatro de seis entre 72 y
# 89 — formato corto sin forzar nada.
#
# Y quita de la cadena la resintesis mas grande: `rubberband` no es un filtro,
# reconstruye la senal. Con la voz limpiada fuera eran **dos resintesis
# encadenadas**, y ahi es donde empezo a sonar a papilla.
#
# Estaba repetido en seis ficheros, que es como se acaba teniendo dos
# velocidades distintas en el mismo montaje.
VELOCIDAD = 1.0

sys.path.insert(0, os.path.dirname(__file__))
import estado  # noqa: E402
import transcribir  # noqa: E402
import rutas  # noqa: E402

# **`libretos.md` es el documento que entrego Jaime, y no hay otro.**
#
# Estuvo siendo una reconstruccion, y eso no es cosmetica: `puntua()` busca el
# material en la cinta **comparando con las palabras del libreto**, asi que un
# texto distinto encuentra cosas distintas. De ahi salieron «el simil del
# odontologo se pierde», «no da la idea completa» y «se come la primera parte».
#
# El reconstruido queda en `libretos-reconstruido.md` marcado NO USAR, para
# poder ver que cambio. **Una sola fuente**: dos ficheros para el mismo dato se
# separan en cuanto uno cambia, y eso ya costo cuatro fallos en este proyecto.
LIBRETOS = os.path.join("..", "docs", "libretos.md")
FRAMES = os.path.join("ads", "frames.json")
# Palabras que no distinguen un beat de otro.
VACIAS = {
    "que", "de", "la", "el", "en", "los", "las", "un", "una", "por", "con",
    "para", "del", "se", "su", "sus", "lo", "le", "es", "no", "mas", "pero",
    "como", "esta", "este", "esto", "usted", "yo", "va", "ya", "si", "al",
    "y", "a", "o", "sin", "hay", "muy", "todo", "todos", "eso", "ese", "ahi",
    "tiene", "ser", "son", "esa", "cada", "porque", "cuando", "donde",
}


def palabras(t):
    """Las palabras tal cual, sin tildes ni puntuación. No filtra nada."""
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", t)


def norm(t):
    return [w for w in palabras(t) if len(w) > 2 and w not in VACIAS]


def beats_del_libreto(n):
    """Cada párrafo del libreto es un beat: una función en el argumento."""
    libro = open(LIBRETOS, encoding="utf-8").read()
    bloque = next(
        (b for b in libro.split("\n## ") if b.startswith(f"Reel {n} ")), None)
    if not bloque:
        raise SystemExit(f"sin libreto para el reel {n}")
    cuerpo = bloque.split("---")[0]
    out = []
    for p in cuerpo.split("\n\n"):
        p = " ".join(p.split())
        # Fuera el encabezado, el hook duplicado y las líneas de metadatos.
        if not p or p.startswith(("**Hook", "Reel ", "#")) or len(p) < 40:
            continue
        out.append(p)
    return out


def frame_del_reel(n, beats):
    """
    Qué estructura ejecuta el reel y qué función cumple cada beat dentro de ella.

    Sale de `ads/frames.json`, no de una etiqueta en el libreto: tres de las seis
    etiquetas que traían los libretos nombraban el **mecanismo conductual** y una
    nombraba una configuración orgánica de EDUCATE, que no es una estructura de
    pago. El mecanismo y la estructura son decisiones distintas y se declaran
    aparte.

    Si el libreto cambia de número de párrafos, esto **para**. Es el aprendizaje
    24 aplicado antes de que haga daño: un fichero declarado no se entera de que
    editaste su fuente, y un beat corrido de sitio reasigna todas las funciones
    a partir de ahí sin avisar de nada.
    """
    d = json.load(open(FRAMES, encoding="utf-8"))
    f = d["reels"].get(f"reel-{n:02d}")
    if not f:
        raise SystemExit(f"reel-{n:02d} sin estructura declarada en {FRAMES}")
    if len(f["beats"]) != len(beats):
        raise SystemExit(
            f"reel-{n:02d}: el libreto tiene {len(beats)} párrafos y "
            f"{FRAMES} declara {len(f['beats'])} beats. Uno de los dos cambió; "
            f"cuadrarlos antes de montar.")
    return f


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


def _en_run(t, runs):
    """El tramo de voz que contiene ese instante, o None."""
    for a, b in runs:
        if a <= t <= b:
            return (a, b)
    return None


def oraciones(toma):
    """
    Los candidatos son **oraciones completas**, no tramos de silencio.

    Esto es la corrección más importante que ha tenido el montaje, y viene de
    Jaime: *«sólo una frase u oración equivalente, con la mayor continuidad
    posible; no fragmentos, no secciones»*.

    Antes los candidatos salían del detector de silencio, y un tramo de silencio
    **no es una unidad de sentido**: empieza y acaba donde el hablante respira.
    De los 48 enunciados del lote anterior **sólo 5 eran frases completas** y 33
    estaban rotos por los dos extremos. Por eso el reel 1 quedó «supremamente
    roto» — no era el orden ni el frame, era que cada pieza era media frase.

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
            "texto": txt, "clave": set(norm(txt)),
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


def _octava(f, med):
    """Baja o sube la muestra hasta la octava de la mediana."""
    while f > 1.6 * med:
        f /= 2
    while f < 0.62 * med:
        f *= 2
    return f


def expresividad(toma, a, b):
    """
    Cuánta vida tiene la voz en ese tramo, en semitonos de recorrido de F0.

    **Se elige por voz, no por toma.** Jaime: *«en lugar de buscar tomas buenas,
    si hay un audio con calidad o con expresividad, con emoción, pero sin toma,
    entonces creamos una animación con ese audio»*. El plano se puede sustituir
    por una tarjeta; la voz no se puede sustituir por nada.

    Se aplica el filtro de plausibilidad de siempre: el habla expresiva se mueve
    entre 2 y 5 semitonos de recorrido. Por encima de 8 no es energía, es el
    detector saltando de octava.
    """
    f0 = contorno(toma, a, b)
    if f0 is None:
        return 0.0
    # Rango intercuartílico, no p90-p10: aguanta mejor los saltos que queden.
    st = 12 * np.log2(np.percentile(f0, 75) / max(1e-6, np.percentile(f0, 25)))
    return 0.0 if st > 8 or st < 0.2 else float(st)


def contorno(toma, a, b):
    """El contorno de F0 del tramo, en Hz y ya corregido de octava.

    Estaba dentro de `expresividad` y sale aqui porque **la altura y el
    movimiento son dos cosas distintas**: una lectura monotona puede tener un
    recorrido amplio si deriva despacio de grave a agudo, y sonar plana igual.
    Para saber si hay *cambio de tono* hace falta el contorno, no su rango.
    """
    # **Un fichero por llamada, no uno para todas.** Esto escribia siempre
    # `exp.wav`, y con dos procesos midiendo a la vez —la linea avanzando piezas
    # en segundo plano y una consulta a mano— uno lee lo que el otro esta
    # escribiendo: `EOFError` en mitad de una corrida, intermitente y sin decir
    # de donde viene. Aparecio tres veces esta sesion antes de que mirara el
    # nombre del fichero.
    #
    # El nombre lleva el proceso y el tramo, asi que dos medidas nunca compiten
    # y ademas se puede saber de quien es un temporal que quedo suelto.
    import wave

    wav = (f"{rutas.TEMPORAL}/f0-{os.getpid()}-"
           f"{abs(hash((toma, round(a, 2), round(b, 2)))) % 10**8}.wav")
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a), "-to", str(b),
                        "-i", f"{rutas.ORIGEN}/{toma}.mp4", "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", wav], check=True)
        with wave.open(wav) as w:
            x = np.frombuffer(w.readframes(w.getnframes()),
                              dtype=np.int16).astype(float)
    finally:
        # No se deja basura: son cientos de recortes por corrida.
        try:
            os.remove(wav)
        except OSError:
            pass
    if x.size < 16000:
        return None
    # F0 por autocorrelacion en ventanas de 40 ms.
    sr, n, f0 = 16000, 640, []
    for i in range(0, len(x) - n, n // 2):
        v = x[i:i + n] - x[i:i + n].mean()
        if np.sqrt((v ** 2).mean()) < 250:
            continue
        c = np.correlate(v, v, "full")[n - 1:]
        lo, hi = sr // 320, sr // 70          # 70-320 Hz, rango de voz
        if hi >= len(c):
            continue
        k = int(np.argmax(c[lo:hi])) + lo
        if c[k] > 0.3 * c[0]:
            f0.append(sr / k)
    if len(f0) < 8:
        return None
    f0 = np.array(f0)

    # **Doblado de octava.** El detector engancha a veces el primer armónico y
    # devuelve el doble: en una toma la mediana daba 117 Hz y el percentil 90
    # daba 208 — exactamente el doble del percentil 10. Sin corregirlo el
    # recorrido salía en 14 semitonos, el filtro de plausibilidad lo tiraba, y
    # TODAS las tomas puntuaban cero: la expresividad dejaba de decidir nada.
    #
    # Es el aprendizaje 15 otra vez, y por eso el filtro no basta: descarta el
    # número malo, pero si el error es sistemático descarta todos.
    med = np.median(f0)
    return np.array([_octava(f, med) for f in f0])


def cambio_de_tono(toma, a, b):
    """Cuánto se MUEVE la voz, en semitonos por segundo de recorrido.

    Jaime, fijando las cuatro condiciones del re-calificado: *«si después de las
    cuatro pasadas baja su puntaje, o es demasiado fragmentado, si no hay ritmo
    y si no hay cambio de tono, entonces escogemos el siguiente»*.

    **Y no es lo mismo que `expresividad`.** Aquella mide el rango —cuánto
    espacio ocupa la voz entre su grave y su agudo—, y una lectura monótona que
    deriva despacio de un extremo al otro puntúa alto sin haber cambiado de tono
    ni una vez. Esto mide el recorrido real: la suma de lo que sube y baja,
    dividida por el tiempo. Leer plano da un número bajo aunque el rango sea
    ancho.
    """
    f0 = contorno(toma, a, b)
    if f0 is None or len(f0) < 8:
        return 0.0
    st = 12 * np.log2(np.maximum(f0[1:], 1e-6) / np.maximum(f0[:-1], 1e-6))
    # Los saltos de octava que sobrevivan no son entonacion: se recortan.
    st = np.clip(st, -3.0, 3.0)
    return float(np.abs(st).sum() / max(b - a, 1e-6))


def ritmo(palabras, a, b, ventana=2.0):
    """Cuánto varía la velocidad del habla dentro del tramo. 0 = plano.

    La otra mitad de *«si no hay ritmo»*. Se cuentan palabras por segundo en
    ventanas de dos segundos y se devuelve el coeficiente de variación: una
    entrega con ritmo acelera y frena —remata una idea, deja aire, arranca la
    siguiente—, y una lectura mantiene la misma velocidad de principio a fin.

    Se mide sobre las palabras y no sobre la señal porque es lo que el
    espectador percibe como ritmo: cuándo llegan las palabras, no la energía.
    """
    ws = [w for w in palabras if a - 0.01 <= w["start"] and w["end"] <= b + 0.01]
    if len(ws) < 6 or b - a < 2 * ventana:
        return 0.0
    tasas = []
    t = a
    while t + ventana <= b:
        n = sum(1 for w in ws if t <= w["start"] < t + ventana)
        tasas.append(n / ventana)
        t += ventana / 2
    tasas = np.array([x for x in tasas if x > 0])
    if len(tasas) < 3 or tasas.mean() <= 0:
        return 0.0
    return float(tasas.std() / tasas.mean())


_BASE = {}


def _baseline(toma, palabras):
    """La neutralidad de ESTA cinta: su altura, su velocidad y su cuerpo medios.

    Se calcula una vez por cinta y se cachea: es el punto cero contra el que se
    mide la intensidad, y tiene que ser el suyo. La misma frase dicha por dos
    personas no compara; dicha por la misma persona en dos momentos, sí.
    """
    if toma in _BASE:
        return _BASE[toma]
    # **En disco, no solo en memoria.** Extraer el F0 de una cinta entera cuesta
    # medio minuto, y `seleccionar.py` corre una vez por reel: sin cachearlo se
    # pagan tres minutos por corrida para calcular seis veces lo mismo.
    cache = os.path.join("work", "baseline", f"{toma}.json")
    if os.path.exists(cache):
        _BASE[toma] = json.load(open(cache, encoding="utf-8"))
        return _BASE[toma]
    f0 = contorno(toma, 0, 9e9)
    alt = float(np.median(f0)) if f0 is not None and len(f0) else 0.0
    if palabras and len(palabras) > 20:
        dur = palabras[-1]["end"] - palabras[0]["start"]
        vel = len(palabras) / max(dur, 1e-6)
    else:
        vel = 0.0
    _BASE[toma] = {"altura": alt, "velocidad": vel}
    os.makedirs(os.path.dirname(cache), exist_ok=True)
    json.dump(_BASE[toma], open(cache, "w", encoding="utf-8"))
    return _BASE[toma]


def _hablado(toma, a, b):
    """Cuantos segundos de ese tramo son voz de verdad, segun el audio.

    Los tramos de `work/cuts/<toma>.json` los midio el detector de silencio
    sobre la onda, asi que dicen donde hay voz **independientemente de lo que
    el alineador haya hecho con las marcas de palabra**. Si no estan, se cae al
    span entero: peor medida, pero medida.
    """
    try:
        runs = json.load(open(f"work/cuts/{toma}.json",
                              encoding="utf-8"))["segmentos"]
    except Exception:                              # noqa: BLE001
        return max(b - a, 1e-6)
    t = sum(max(0.0, min(b, y) - max(a, x)) for x, y in runs)
    # Nunca cero: un tramo sin voz medida se trata como el span, y ya lo dira
    # la intensidad quedandose baja.
    return t if t > 0.2 else max(b - a, 1e-6)


def intensidad(toma, a, b, palabras=None):
    """Cuánta emoción lleva el tramo, **sin signo**.

    Correccion de Jaime, y desarma un sesgo que las otras medidas tenian dentro:
    *«ojo, no hay emociones positivas o negativas: mas emocion es mas tristeza
    tanto como mas rabia tanto como mas alegria»*.

    `expresividad` mide el recorrido de F0, y eso **premia lo animado**. La
    tristeza baja el tono, ralentiza y estrecha el rango: con esa vara puntua
    como plana, que es justo lo contrario de lo que es. La rabia, al reves, sube
    y acelera.

    Lo que las dos tienen en comun no es la direccion: es **estar lejos de la
    neutralidad del hablante**. Asi que esto mide la distancia al punto cero de
    esa misma cinta —su altura media y su velocidad media— y la devuelve sin
    signo. Grave y lento puntua igual que agudo y rapido; lo que puntua bajo es
    lo tibio, que es lo unico que de verdad no transmite.

    Devuelve `{altura, velocidad, intensidad}` en desviaciones relativas.
    """
    base = _baseline(toma, palabras)
    f0 = contorno(toma, a, b)
    out = {"altura": None, "velocidad": None, "intensidad": None}
    if f0 is not None and len(f0) and base["altura"] > 0:
        # En semitonos respecto a su propia altura media, con signo conservado
        # para poder informar de si va grave o agudo.
        out["altura"] = round(12 * np.log2(float(np.median(f0)) / base["altura"]), 2)
    if palabras and base["velocidad"] > 0 and b > a:
        n = sum(1 for w in palabras if a <= w["start"] < b)
        # **Se divide por lo que se HABLA, no por lo que dura el tramo.**
        #
        # Esto usaba el span entero, y un tramo con silencio dentro salia lento
        # aunque se hablara rapido: la velocidad quedaba diluida por el aire.
        # Medido en reel-06: la etapa 6 tiene 13,7 s mudos de 21,49 —el 64%— y
        # puntuaba 0,12 de intensidad; la 7 tenia 5,0 s de 9,50 y puntuaba 0,36.
        # Recortando solo el silencio, esa misma toma sube a 3,84.
        #
        # O sea que media tarde de «etapas tibias» no eran tomas flojas: eran
        # tomas bien dichas medidas sobre el aire que las rodea. Y la trampa es
        # doble, porque **el render ya quita ese silencio** —`plan-reel` corta
        # todo hueco de mas de 0,16 s— asi que se estaba puntuando un tramo que
        # el espectador nunca va a oir asi.
        #
        # El silencio se mide con el detector de voz, que mide el AUDIO, y no
        # con las marcas de palabra: el alineador pega el silencio a la palabra
        # anterior —en esa cinta «practicas.» dura 14,1 s y «ano» 7,1 con
        # energia cero— asi que por palabras es invisible. Es la leccion de
        # C-101 otra vez: cuando dos medidas del mismo hecho discrepan, gana la
        # que mide el hecho.
        util = _hablado(toma, a, b)
        out["velocidad"] = round((n / util) / base["velocidad"] - 1.0, 2)
    partes = [abs(out["altura"]) / 2.0 if out["altura"] is not None else None,
              abs(out["velocidad"]) / 0.35 if out["velocidad"] is not None else None]
    partes = [p for p in partes if p is not None]
    if partes:
        # La norma, no la suma: lejos en UNA dimension ya es intensidad, y no
        # hace falta estarlo en las dos. Un susurro lento y grave cuenta.
        out["intensidad"] = round(float(np.sqrt(sum(p * p for p in partes))), 2)
    return out


# Lo que hace falta para que una costura **se oiga**. Estaban en la prosa de
# `salto` —«por debajo de ~2 st y de ~1,5 pal/s pasa desapercibido»— y una cifra
# que solo vive en un comentario no la puede usar nadie: la segunda valoracion
# necesita descontar por costura audible, y para eso el umbral tiene que ser un
# dato del modulo, no una frase.
SALTO_TONO = 2.0        # semitonos de diferencia de altura media
SALTO_RITMO = 1.5       # palabras por segundo


def salto(toma_a, fin_a, toma_b, ini_b, palabras=None, ventana=1.5,
          palabras_b=None):
    """Cuánto salta la voz AL CRUZAR una costura. Es lo que se oye del corte.

    Jaime: *«si notas que los cortes de tono, o de ritmo, son muy profundos,
    sabes que se va a notar en video»* — *«por lo que puedes escoger o buscar
    otro fragmento que puntúe mejor»*.

    Y es una medida distinta de las que ya había, no una variante. `expresividad`
    y `cambio_de_tono` miran **dentro** de un trozo: dicen si esa toma está viva.
    Ésta mira **entre** dos: dice si la unión se va a notar. Dos fragmentos
    pueden puntuar de maravilla por separado y sonar a corte pegado cuando uno
    acaba grave y despacio y el siguiente arranca agudo y disparado.

    Se mide sobre `ventana` segundos a cada lado —lo que el oído usa para
    situarse— y devuelve:

        tono   diferencia de altura media, en semitonos
        ritmo  diferencia de velocidad del habla, en palabras por segundo

    Un salto de tono por debajo de ~2 st y de ritmo por debajo de ~1,5 pal/s pasa
    desapercibido; por encima, la costura se oye y **conviene buscar otro
    fragmento** antes que taparla con una transición.
    """
    fa = contorno(toma_a, max(0.0, fin_a - ventana), fin_a)
    fb = contorno(toma_b, ini_b, ini_b + ventana)
    out = {"tono": None, "ritmo": None}
    if fa is not None and fb is not None and len(fa) and len(fb):
        ma, mb = float(np.median(fa)), float(np.median(fb))
        if ma > 0 and mb > 0:
            # **La octava, otra vez.** `contorno` corrige cada tramo contra SU
            # mediana, asi que dos ventanas pueden quedar en octavas distintas y
            # el salto sale de 18 semitonos, que es imposible en una voz. Es el
            # aprendizaje 15 aplicado a la comparacion: el filtro de
            # plausibilidad no basta si el error es sistematico, hay que
            # corregirlo. Se lleva `mb` a la octava de `ma` antes de restar.
            while mb > ma * 1.6:
                mb /= 2.0
            while mb < ma / 1.6:
                mb *= 2.0
            out["tono"] = round(abs(12 * np.log2(mb / ma)), 2)
    if palabras:
        def tasa(ws, a, b):
            """Palabras por segundo en esa ventana, con SUS palabras.

            **Cada lado se mide con la transcripcion de su cinta.** Cuando la
            costura cruza de una toma a otra —el caso donde el salto mas se
            oye— medir los dos lados con las palabras de la primera daba 2,0
            pal/s donde habia 0,67: cruzaba el umbral por el lado equivocado
            y denunciaba costuras que no existen.
            """
            if not ws:
                return 0.0
            n = sum(1 for w in ws if a <= w["start"] < b)
            return n / max(b - a, 1e-6)

        pb = palabras_b if palabras_b is not None else palabras
        out["ritmo"] = round(
            abs(tasa(pb, ini_b, ini_b + ventana)
                - tasa(palabras, max(0.0, fin_a - ventana), fin_a)), 2)
    return out


def tartamudeo(texto):
    """
    Cuánto se repite el enunciado consigo mismo. 0 = limpio, 1 = todo repetido.

    Es la firma del intento fallido: «pasa sin cada semana que pasa sin saber
    sin saber cada semana que pasa cada». Sin esto, ese trozo ganaba su beat
    porque **repetir las palabras del libreto sube la cobertura** — el
    tartamudeo puntuaba como acierto.
    """
    ws = norm(texto)
    if len(ws) < 4:
        return 0.0
    return 1 - len(set(ws)) / len(ws)


# Signos con que whisper cierra una frase. Los abre `¿` y `¡`, que en español
# son parte del arranque y por eso cuentan como mayúscula.
FIN = ".?!…"


def integridad(texto):
    """
    Cuántos extremos de la frase están enteros: 0, 1 ó 2.

    El transcript conserva mayúsculas y puntuación, así que un enunciado que
    empieza en minúscula **empieza a mitad de frase** y uno que no acaba en
    punto **se corta a mitad de idea**. Es el aprendizaje 36 hecho criterio:
    entrar en frontera de tramo no garantiza entrar en la frase.

    Va por encima de la voz a propósito. Una frase rota es un defecto de
    mensaje, y el mensaje manda sobre cómo se dice.
    """
    ws = texto.split()
    if not ws:
        return 0
    abre = ws[0][:1].isupper() or ws[0][:1] in "¿¡"
    return int(abre) + int(ws[-1][-1:] in FIN)


def trabado(texto):
    """
    Palabras pegadas repetidas: «usted usted», «no no», «su negocio su».

    Es exactamente lo que Jaime oyó en el reel 3 —*«el tercero se traba, usted
    usted tiene un contador»*— y lo que `tartamudeo` no ve: aquel mide repetición
    en todo el enunciado y se diluye con la longitud; esto mira sólo el pegado,
    que es lo que se nota al oído.
    """
    ws = palabras(texto)
    return sum(1 for a, b in zip(ws, ws[1:]) if a == b)


def parecido(u, v):
    """
    Cuánto dicen lo mismo dos enunciados. 0 = nada, 1 = idénticos.

    Es lo que distingue **dos intentos de una idea** de dos ideas distintas, y
    hacía falta porque el descarte por solape de tiempo no los ve: los cuatro
    intentos de «la mayoría de los emprendedores asume…» están en instantes
    distintos de la toma, así que ninguno solapa con otro y los cuatro podían
    entrar bajo etapas distintas. En el reel 1 entraron.

    Jaime: *«que no se repita lo que ya se dijo y se cumplió de acuerdo al
    copy»*. Una etapa cumplida cierra su idea para toda la pieza, no sólo para
    su propio hueco.
    """
    a, b = u["clave"], v["clave"]
    return len(a & b) / max(1, len(a | b))


# Por encima de esto, dos enunciados son el mismo intento y sólo entra uno.
# Medido sobre los intentos repetidos del reel 1: los duplicados reales caen
# entre 0,55 y 0,8; dos beats distintos del mismo libreto rara vez pasan de 0,35.
IGUAL = 0.5


def puntua(beat, u):
    """
    Cuánto dice este enunciado el beat, y cómo de bien lo dice.

    Cobertura del beat, no parecido general: importa **cuánto del beat está
    dicho**, no cuánto del enunciado sobra. Un enunciado largo que dice el beat
    entero vale más que uno corto que dice la mitad.

    Y la fluidez pesa: entre dos tomas que dicen lo mismo gana la que no
    tropieza. Sin ese término, la que tropieza gana — porque repite palabras del
    beat y eso subía la cobertura.
    """
    pedidas = set(norm(beat))
    if not pedidas:
        return 0.0
    cubre = len(pedidas & u["clave"]) / len(pedidas)
    # Penaliza el relleno: mucho texto que no es del beat es divagación.
    sobra = len(u["clave"] - pedidas) / max(1, len(u["clave"]))
    return cubre - 0.25 * sobra - 0.8 * tartamudeo(u["texto"])


# Suelo absoluto de cobertura: por debajo, el enunciado no dice el beat.
UMBRAL = 0.18
# Y suelo relativo: sólo compite quien se acerca al que mejor lo dice. Es lo que
# impide que la voz rescate a uno que dice la mitad — el mensaje filtra primero.
RELATIVO = 0.80
# Finalistas por beat. Antes eran 3; con la voz decidiendo de verdad conviene
# mirar algunos más, porque el mejor de texto y el mejor de voz rara vez son el
# mismo enunciado.
FINALISTAS = 5
# Escalón con que se comparan dos expresividades. Por debajo de un cuarto de
# semitono la diferencia es ruido del detector, no de la voz, y en ese caso
# vuelve a mandar la cobertura en vez de decidir el azar de la medición.
PASO_VOZ = 0.25


def podar(u, exige=()):
    """Quita las repeticiones de DENTRO de una unidad.

    Regla de Jaime: *«correctivos para la redundancia, y mas cuando lo que se
    dice es directamente contradictorio»*.

    ## Que cuenta como repeticion

    Una racha de tres palabras o mas que vuelve a aparecer mas adelante en la
    misma unidad. Vale igual si **una palabra cambia** -«se queda con 64» y «se
    queda con 67»-, que es el caso peor: dos cifras para el mismo hueco es
    informacion contradictoria en pantalla.

    ## Cual se queda: la que sigue diciendo algo

    La primera version miraba solo repeticiones **pegadas**, y el habla real no
    repite asi: en el reel 3, «usted tiene un contador y se queja de que paga
    mucho impuesto» vuelve **diez palabras despues**, con la frase clave del beat
    en medio. Pegado no habia nada, asi que no podaba nada y la pieza decia la
    tesis tres veces.

    Y no vale quedarse siempre con la ultima. Aqui la buena es la PRIMERA,
    porque detras lleva *«pero nunca le ha preguntado al contador por que»* —el
    giro que hace la tesis— y la ultima no lleva nada detras: es un rearranque.

    Asi que la regla es: **se queda la aparicion que va seguida de mas material
    nuevo**, y las otras se van con lo que arrastran hasta la siguiente. Cubre
    los dos casos con el mismo criterio -en «64 / 67» gana la segunda, porque es
    la que continua la frase- y no depende de adivinar cual quiso decir.
    """
    # **Solo lo que de verdad queda de la unidad.** `pal` son las palabras de la
    # frase entera, y para entonces ya se le pudo aplicar un recorte declarado
    # (`entra_en` / `sale_en`). Sin acotar, la poda proponia tramos fuera del
    # recorte y **deshacia una decision de oido** — en el reel 3 devolvia el
    # precio que se acababa de recortar a proposito.
    pal = [w for w in (u.get("pal") or [])
           if w[0] >= u["a"] - 0.05 and w[1] <= u["b"] + 0.05]
    if len(pal) < 8:
        return None
    tok = []
    for w in pal:
        t = norm(w[2])
        tok.append(t[0] if t else "")
    esnum = [bool(re.search(r"\d", w[2])) for w in pal]

    def igual2(vivos, x, y, n):
        """Igual que `igual`, pero sobre las posiciones que siguen vivas."""
        return igual(vivos[x], vivos[y], n, [vivos[x + k] for k in range(n)],
                     [vivos[y + k] for k in range(n)])

    def igual(i, j, n, ii=None, jj=None):
        # **La racha tiene que decir algo.** Con puras palabras de funcion
        # -«es para usted»- cualquier frase repite: en el reel 3 eso se llevo
        # por delante el remate del registro. Se exigen dos palabras de
        # contenido dentro de la racha.
        ii = ii or [i + k for k in range(n)]
        jj = jj or [j + k for k in range(n)]
        # **Si la racha lleva una cifra, con dos palabras basta.**
        #
        # Jaime: *«repites demasiadas veces 21 dolares... lo mismo con 189.000...
        # el libreto marca una sola, no dos»*. «21 dolares, 21 dolares» son dos
        # palabras y el suelo general son cuatro, asi que pasaba entera. Una
        # cifra repetida no es enfasis: es el hablante afianzandose, y en
        # pantalla queda como tartamudeo.
        #
        # El suelo alto sigue para lo demas, que es lo que evita que «es para
        # usted» se lea como repeticion.
        concifra = any(esnum[k] for k in ii)
        if not concifra and sum(1 for k in ii if len(tok[k]) > 3) < 2:
            return False
        # **La cifra distinta solo vale como autocorreccion inmediata.**
        #
        # Con tolerancia numerica libre, «se queda con 44» y «se queda con 67»
        # cuentan como la misma racha — y son **las dos caras de la
        # comparacion**, no una repeticion. La poda se llevaba 18 s del reel 2 y
        # con ellos el 67.
        #
        # Una autocorreccion se dice pegada («con 64, el se queda con 67»); dos
        # datos distintos van separados y con material en medio. Asi que el
        # numero distinto solo se admite si las dos rachas estan a menos de su
        # propio largo de distancia, y en rachas de cuatro palabras o mas.
        pegadas = (jj[0] - ii[0]) <= max(n, 4)
        distinto = 0
        for ka, kb in zip(ii, jj):
            if tok[ka] == tok[kb]:
                continue
            if esnum[ka] and esnum[kb] and n >= 4 and pegadas:
                distinto += 1
                continue
            return False
        return distinto <= 1

    # **Se poda hasta que no quede ninguna, no una y a otra cosa.**
    #
    # La primera version quitaba **la repeticion mas larga** y paraba. Y una
    # unidad real trae varias: en el reel 2, *«esa diferencia, esta diferencia,
    # 21 dolares, 21 dolares cada 100 dolares que recibe, cinco anos son 189 mil
    # dolares, 189 mil dolares, 189 mil dolares que el electricista trabajo»*
    # lleva tres. Jaime: *«repites demasiadas veces 21 dolares... lo mismo con
    # 189.000... repeticion redundante e inoficiosa»*.
    vivos = list(range(len(pal)))
    fuera = []
    for _ in range(8):
        mejor = None
        m = len(vivos)
        for n in range(min(12, m // 2), 1, -1):
            for x in range(m - 2 * n + 1):
                for y in range(x + n, m - n + 1):
                    if igual2(vivos, x, y, n):
                        mejor = (x, y, n)
                        break
                if mejor:
                    break
            if mejor:
                break
        if not mejor:
            break
        x, y, n = mejor

        def nuevas(desde, hasta):
            vistas = {tok[vivos[k]] for k in range(desde) if len(tok[vivos[k]]) > 3}
            return len({tok[vivos[k]] for k in range(desde, hasta)
                        if len(tok[vivos[k]]) > 3} - vistas)

        # Se queda la aparicion que va seguida de mas material nuevo.
        if nuevas(x + n, y) >= nuevas(y + n, m):
            quita = list(range(y, m))
        else:
            quita = list(range(x, y))
        # **Nunca se poda lo que la etapa tiene que decir.** Si el trozo que
        # tocaria quitar lleva la cifra declarada, se prueba con la otra
        # aparicion; y si tampoco, esta repeticion se deja estar. Limpiar no es
        # elegir: entre quitar una repeticion y quitar el dato, se queda el dato.
        def sobrevive(ks):
            """Lo que la etapa debe decir sigue estando despues de quitar `ks`."""
            fuera_ = set(ks)
            queda = " ".join(pal[vivos[k]][2] for k in range(m) if k not in fuera_)
            return all(dice(queda, e) for e in exige)
        # **Se poda si lo declarado SOBREVIVE, no si el trozo lo contiene.**
        #
        # La version anterior rechazaba quitar el trozo en cuanto llevaba la
        # palabra declarada — y eso es justo lo que pasa al quitar una
        # repeticion: las dos copias la llevan. Resultado: «y si usted no sabe
        # que pedir, pues nadie se lo va a ofrecer solo» se decia dos veces
        # seguidas en el reel 3 porque la etapa declaraba «pedir».
        #
        # Lo que hay que garantizar es que **quede dicho**, no que no se toque.
        if exige and not sobrevive(quita):
            otro = list(range(x, y)) if quita[0] == y else list(range(y, m))
            if not sobrevive(otro):
                break
            quita = otro
        fuera.append((vivos[quita[0]], vivos[quita[-1]] + 1))
        vivos = [v for k, v in enumerate(vivos) if k not in set(quita)]
    if not fuera:
        return None
    fuera.sort()
    # Se funden los tramos que se tocan, para no partir de mas.
    unidos = [list(fuera[0])]
    for a_, b_ in fuera[1:]:
        if a_ <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], b_)
        else:
            unidos.append([a_, b_])
    fuera = [tuple(t) for t in unidos]

    tramos, ini = [], 0
    for a_, b_ in fuera:
        if a_ > ini:
            tramos.append([round(pal[ini][0], 3), round(pal[a_ - 1][1], 3)])
        ini = b_
    if ini < len(pal):
        tramos.append([round(pal[ini][0], 3), round(u["b"], 3)])
    if not tramos:
        return None
    quitado = sum(pal[min(b_, len(pal)) - 1][1] - pal[a_][0] for a_, b_ in fuera)
    return tramos, round(quitado, 2), " ".join(
        " ".join(w[2] for w in pal[a_:b_]) for a_, b_ in fuera)


def unir(u1, u2):
    """Dos frases seguidas de la misma toma, como una sola unidad.

    Regla de Jaime: *«a la frase 5 quitale "por cada 100 dolares" en adelante,
    es completamente redundante con la frase 6; la redundancia hay que
    evitarla»*.

    Y no hace falta escribir donde cortar: **se deriva**. Se recorre la cola de
    la primera de atras adelante y se corta en la ultima palabra cuyo contenido
    ya no este en la segunda. En el reel 2 eso deja la [5] en «...y que tiene
    yate en el lago Muscoca,» y tira «por 100 dolares, por cada 100 dolares que
    el recibe,», que es exactamente lo que la [6] vuelve a decir.

    El corte es por palabra y con su tiempo, asi que la union sigue siendo un
    tramo continuo de la misma toma: no se cose nada.
    """
    wb = set(norm(u2["texto"]))
    pal = u1["pal"]
    corte = len(pal)
    for i in range(len(pal) - 1, 3, -1):
        toks = norm(pal[i][2])
        if toks and not set(toks) <= wb:
            break
        corte = i
    fin = pal[corte - 1][1] if corte < len(pal) else u1["b"]
    txt = " ".join(w[2] for w in pal[:corte]).strip() + " " + u2["texto"]
    # **Dos tramos, no uno continuo.** El hueco entre el corte y el arranque de
    # la segunda es justo lo redundante, asi que tiene que quedarse fuera del
    # montaje: si se emite el tramo entero, la cola repetida vuelve a sonar y no
    # habriamos quitado nada.
    return {**u2, "a": u1["a"], "b": u2["b"], "corte_uno": round(fin, 3),
            "tramos": [[round(u1["a"], 3), round(fin, 3)],
                       [round(u2["a"], 3), round(u2["b"], 3)]],
            "texto": txt.strip(), "clave": set(norm(txt)),
            "aire": round(u1.get("aire", 0) + u2.get("aire", 0), 2)}


def dice(texto, termino):
    """Si un enunciado dice de verdad un termino, con la ortografia que sea.

    Los numeros se escriben de tres maneras en el mismo transcript -«30.000»,
    «30,000», «30000»- asi que se comparan sin separadores. Y sin tildes, que es
    lo que ya hace el resto del fichero.
    """
    def limpio(t):
        t = unicodedata.normalize("NFKD", str(t).lower())
        t = "".join(c for c in t if not unicodedata.combining(c))
        return re.sub(r"(?<=\d)[.,](?=\d)", "", t)
    # **La intencion, no la letra.** Jaime: *«la idea no es tomar el libreto
    # literal, es tomar la intencion comunicativa de cada parte, respetando su
    # funcion»*. Una cifra se puede decir de varias maneras y un desliz de dos
    # dolares no cambia el mensaje ni la estructura, asi que el termino admite
    # alternativas con `|`: «44|46» se cumple con cualquiera de las dos.
    return any(limpio(t) in limpio(texto) for t in str(termino).split("|"))


def montar(n, budget):
    toma = rutas.TOMAS[f"reel-{n:02d}"]
    beats = beats_del_libreto(n)
    frame = frame_del_reel(n, beats)
    _ws = transcribir.exigir(toma)["segmentos"]

    _runs = json.load(open(f"work/cuts/{toma}.json",
                           encoding="utf-8"))["segmentos"]

    def _hueco(x):
        """El silencio real entre dos palabras, medido con los tramos de voz.

        Los tiempos de whisper no dejan hueco entre palabras -el final de una es
        el principio de la siguiente- asi que restarlos siempre da cero y el
        corte no encontraba donde parar: devolvia 98 s de una tirada. El
        silencio esta en `work/cuts/`, que es donde se midio de verdad. Es el
        aprendizaje 19: el transcript dice lo que se dijo, los tramos dicen
        donde hubo voz, y para tiempos manda el segundo.
        """
        r1 = _en_run(_ws[x]["start"], _runs)
        r2 = _en_run(_ws[x + 1]["start"], _runs)
        return (r2[0] - r1[1]) if (r1 and r2 and r1 != r2) else 0.0

    def frase_con(termino):
        """El tramo de cinta donde se dice un termino, acotado por las pausas.

        Antes devolvia «la frase» entre puntos, y whisper deja tramos enteros
        sin puntuar: en el reel 3 eso daba **98 segundos** para una etapa. La
        frase es la unidad, pero cuando la puntuacion no esta, quien delimita es
        el silencio medido — que es lo unico que hay.

        Se abre desde la palabra hacia los dos lados y se para en lo primero que
        aparezca: un final de frase, o una pausa de mas de 1,2 s.
        """
        # **Se catalogan TODAS las veces que se dice, no la primera.**
        #
        # Jaime: *«buscas pero no catalogas todo lo que hay en el video... si no
        # encuentras nada es porque honestamente ni has mirado»*. Devolver la
        # primera aparicion es dejar de mirar en cuanto algo encaja, y el
        # material bueno suele estar mas adelante: **repite hasta que sale**.
        #
        # Se recorren todas y se devuelve **la ultima**, que por como graba es
        # la version ajustada.
        hallados = []
        for k, w in enumerate(_ws):
            if not dice(w["text"], termino):
                continue
            ini = k
            for x in range(k - 1, 0, -1):
                if re.search(r"[.!?]$", _ws[x]["text"].strip()):
                    ini = x + 1
                    break
                if _hueco(x) > 1.2:
                    ini = x + 1
                    break
                ini = x
            fin = k
            for x in range(k, len(_ws) - 1):
                fin = x
                if re.search(r"[.!?]$", _ws[x]["text"].strip()):
                    break
                if _hueco(x) > 1.2:
                    break
            hallados.append((round(_ws[ini]["start"], 3), round(_ws[fin]["end"], 3)))
        if not hallados:
            return None
        print(f"    {termino}: {len(hallados)} apariciones en la cinta "
              f"({', '.join('%.1f' % h[0] for h in hallados)}) — se toma la ultima",
              file=sys.stderr)
        return hallados[-1]

    def texto_en(rango):
        """Lo que se dice en un tramo de la cinta, **palabra a palabra**.

        Se lee del transcript y no de los candidatos: la apertura y el cierre se
        eligen de oido sobre la cinta entera, y su tramo puede no coincidir con
        ninguna unidad -en el reel 3 no lo hacia, asi que la comprobacion no
        tenia texto que comparar y no saltaba nunca.
        """
        a_, b_ = rango
        return " ".join(w["text"] for w in _ws if a_ <= w["start"] <= b_)

    cands = oraciones(toma)
    usados = []
    elegidos = []

    # **Lo aprobado no se re-elige.** Idea de Jaime: una base de datos que
    # registre qué segmento está bien y cuál no, para que al corregir uno no se
    # muevan los demás. Es el aprendizaje 13 resuelto de forma estructural — ya
    # no depende de que alguien recuerde re-imponer lo elegido de oído.
    fijados = estado.del_reel(n)

    # **La asignación del paso 2 manda sobre la puntuación de texto.**
    #
    # Faltaba esto y era el hueco del proceso: la IA elegía por sentido y
    # `beats.py` seguía eligiendo por su cuenta con solapamiento de palabras, que
    # es justo el criterio que fallaba. Si existe la asignación, el texto ya no
    # elige — sólo desempata cuando no hay asignación para esa etapa.
    fasig = f"work/asignacion/reel-{n:02d}.json"
    asignado, propuesto, refutado, tramos_decl = {}, {}, set(), {}
    if os.path.exists(fasig):
        for a in json.load(open(fasig, encoding="utf-8"))["asignaciones"]:
            if a.get("unidad_id") is None:
                continue
            propuesto[a["etapa_n"]] = a["unidad_id"]
            if a.get("sostiene"):
                asignado[a["etapa_n"]] = a["unidad_id"]
            elif a.get("tramos"):
                tramos_decl[a["etapa_n"]] = a["tramos"]
            else:
                refutado.add(a["etapa_n"])
        # **Un `null` sostenido tambien es una decision.** El paso 2 puede decir
        # «ninguna unidad sirve» y la refutacion darle la razon; eso es tan
        # vinculante como una asignacion. Sin esto la etapa caia al concurso de
        # texto y salia elegida justo la unidad que el refutador habia
        # descartado por su nombre — pasaba en la urgencia del reel 3.
        for a in json.load(open(fasig, encoding="utf-8"))["asignaciones"]:
            if a.get("unidad_id") is None and a.get("sostiene"):
                refutado.add(a["etapa_n"])
        print(f"  paso 2: {len(asignado)} etapas asignadas por sentido",
              file=sys.stderr)

    for i, beat in enumerate(beats):
        etapa = frame["beats"][i]
        guardado = fijados.get(str(i + 1), {})
        if guardado.get("estado") == "aprobado":
            u = {"a": guardado["desde"], "b": guardado["hasta"],
                 "texto": guardado.get("texto", ""),
                 "clave": set(norm(guardado.get("texto", "")))}
            usados.append(u)
            elegidos.append({**u, "beat": i + 1, "etapa": etapa["etapa"],
                             "obligatorio": bool(etapa.get("obligatorio")),
                             "score": 1.0, "voz": 0.0})
            print(f"  beat {i + 1} ({etapa['etapa']}): APROBADO, se conserva",
                  file=sys.stderr)
            continue
        if guardado.get("estado") == "rechazado":
            print(f"  beat {i + 1} ({etapa['etapa']}): RECHAZADO, va con "
                  f"tarjeta — {guardado.get('por_que', '')}", file=sys.stderr)
            continue
        # **Una etapa cumplida cierra su idea.** Dos filtros, y hacen falta los
        # dos: el de tiempo quita el mismo trozo de cinta, el de contenido quita
        # el mismo intento dicho en otro momento. Sin el segundo, cuatro
        # intentos de una idea entraban bajo cuatro etapas distintas — es
        # literalmente lo que pasó en el reel 1.
        libres = [u for u in cands
                  if not any(min(u["b"], v["b"]) - max(u["a"], v["a"]) > 0.2
                             for v in usados)
                  and not any(parecido(u, v) > IGUAL for v in usados)]
        # **`recortar` conserva la unidad.** Cuando Jaime dice que un segmento
        # no sirve por dónde entra, la respuesta es recortarlo, no tirarlo — así
        # que se toma la unidad que el paso 2 propuso aunque la refutación la
        # tumbara, y el recorte la arregla. Tumbar y recortar son respuestas a
        # problemas distintos: una frase que no dice el beat se tira; una que lo
        # dice pero arranca mal, se recorta.
        if guardado.get("estado") == "recortar" and (i + 1) in propuesto:
            asignado[i + 1] = propuesto[i + 1]

        # **Si a la etapa le falta lo que tiene que decir, se extiende a la
        # frase siguiente.**
        #
        # No es coser tomas ni usar fragmentos: son **dos oraciones enteras y
        # seguidas** de la misma toma —en el reel 2 la [3] empieza a nueve
        # centesimas del final de la [2]—, que es hablar seguido. La regla de
        # una frase por etapa protegia contra el fragmento, no contra la idea
        # completa.
        #
        # Se activa solo cuando la etapa declara `debe_decir` y la unidad
        # elegida no lo dice: la extension la pide la intencion comunicativa, no
        # el gusto. Y al unir se quita la redundancia (ver `unir`).
        def completar(u):
            """Sigue leyendo hacia delante hasta que la etapa este dicha.

            **Protocolo de Jaime**, y es el que manda sobre todo lo demas:

            > *«Siempre va a estar. Puede estar fragmentado o cortado, pero
            > esta. Revisa el texto de la parte siguiente a la que ya esta;
            > luego para de revisar el texto si aparece lo del siguiente
            > segmento. Repites el proceso con cada segmento.»*

            Sale de como graba: en orden, y sin pasar a la frase siguiente hasta
            tener una toma ajustada. Asi que el material de una etapa esta
            **despues** del de la anterior y **antes** del de la siguiente, y
            buscarlo es un barrido hacia delante con dos frenos:

            1. **Se para cuando la etapa ya esta dicha.**
            2. **Se para si aparece lo del segmento siguiente** — se mide con la
               misma puntuacion de cobertura: si una unidad se parece mas al
               beat de al lado que a este, ya no es de este.

            La version anterior solo miraba **la frase inmediatamente pegada**
            (1,5 s), y por eso el reel 1 se quedaba sin sus tres cifras: estaban
            dos o tres frases mas alla, con un intento fallido en medio.
            """
            exige_ = etapa.get("debe_decir") or []
            if not exige_ or all(dice(u["texto"], t) for t in exige_):
                return u
            siguiente = beats[i + 1] if i + 1 < len(beats) else None
            adelante = sorted((c for c in cands if c["a"] > u["a"] + 0.2),
                              key=lambda c: c["a"])
            junto = u
            for c in adelante[:6]:
                # **Freno de contiguidad.** Jaime: *«no siempre secuencial, pero
                # siempre por etapas completas; casi siempre secuencial»*. El
                # material de una etapa es un bloque seguido: si hay que saltar
                # mas de ocho segundos para encontrar la continuacion, lo de en
                # medio es de otra etapa y esto ya no es la misma.
                #
                # Sin este freno el barrido se llevaba 113 s del reel 1 -de
                # 215 a 328- cosiendo tres etapas en una.
                if c["a"] - junto["b"] > 8.0:
                    break
                # Freno 2: esto ya es del segmento siguiente.
                if siguiente and puntua(siguiente, c) > puntua(beat, c) + 0.05:
                    break
                junto = unir(junto, c)
                # Freno 1: la etapa ya esta dicha.
                if all(dice(junto["texto"], t) for t in exige_):
                    print(f"  beat {i + 1}: barrido hacia delante hasta decir "
                          f"{exige_} ({u['a']:.2f}-{c['b']:.2f})", file=sys.stderr)
                    return junto
            return u

        # **Tramos declarados.** Cuando la frase que la etapa necesita esta
        # partida en la cinta por un intento fallido en medio, no hay heuristica
        # que lo resuelva: la eleccion es de oido y se declara.
        #
        # El caso: *«no siempre el que paga MAS impuestos es el que menos
        # trabaja, es el que menos sabe»*. Entre las dos mitades hay una
        # autocorreccion que **invierte el sentido** -repite la frase con «menos
        # impuestos»- y dos «muy regularmente». La regla de quedarse con la
        # ultima (aprendizaje 25) elegiria justo la equivocada, asi que aqui
        # decide el oido y el codigo lo ejecuta igual siempre.
        if (i + 1) in tramos_decl:
            tr = tramos_decl[i + 1]
            u = {"a": tr[0][0], "b": tr[-1][1], "tramos": [list(x) for x in tr],
                 "texto": "", "clave": set(), "pal": []}
            usados.append(u)
            elegidos.append({**u, "beat": i + 1, "etapa": etapa["etapa"],
                             "obligatorio": bool(etapa.get("obligatorio")),
                             "score": 1.0, "voz": expresividad(toma, tr[0][0], tr[-1][1])})
            print(f"  beat {i + 1} ({etapa['etapa']}): tramos declarados "
                  f"{', '.join('%.2f-%.2f' % (x[0], x[1]) for x in tr)}",
                  file=sys.stderr)
            continue

        # **Una etapa refutada va con tarjeta, no vuelve a concurso.**
        #
        # El paso 2 la tumba por una razon escrita y sin esto la etapa caia al
        # concurso de texto, que **volvia a elegir la misma unidad** — justo el
        # criterio que la refutacion venia a corregir. La excepcion es
        # `recortar`: ahi la frase si sirve y lo que falla es por donde entra.
        #
        # (Esta guarda se perdio al reordenar el fichero y volvio a pasar en el
        # reel 4: tres etapas refutadas salieron montadas.)
        if (i + 1) in refutado and (i + 1) not in asignado:
            print(f"  beat {i + 1} ({etapa['etapa']}): refutada por el paso 2 — "
                  f"va con tarjeta", file=sys.stderr)
            continue

        # Si el paso 2 asignó una unidad a esta etapa, es ésa y no se discute.
        #
        # **Salvo que no diga lo que la etapa tiene que decir.** La asignacion
        # puede ser de una pasada anterior, con otras unidades y otro criterio;
        # la intencion comunicativa esta declarada en el frame y es lo que no
        # cambia. Si ni la unidad asignada ni el barrido hacia delante llegan a
        # decirlo, la asignacion esta vieja y se vuelve al concurso, que **si**
        # filtra por `debe_decir`.
        if (i + 1) in asignado:
            u = completar(cands[asignado[i + 1]])
            exige0 = etapa.get("debe_decir") or []
            if exige0 and not all(dice(u["texto"], t) for t in exige0):
                print(f"  beat {i + 1} ({etapa['etapa']}): la asignacion del paso 2 "
                      f"no dice {exige0} ni barriendo — se vuelve a elegir",
                      file=sys.stderr)
                asignado.pop(i + 1, None)
                u = None
        if (i + 1) in asignado:
            u = completar(cands[asignado[i + 1]])
            usados.append(u)
            elegidos.append({**u, "beat": i + 1, "etapa": etapa["etapa"],
                             "obligatorio": bool(etapa.get("obligatorio")),
                             "score": 1.0,
                             "voz": expresividad(toma, u["a"], u["b"])})
            continue

        puntuados = [(puntua(beat, u), u) for u in libres]
        techo = max((p for p, _ in puntuados), default=0.0)
        # **La intencion comunicativa filtra antes que la puntuacion.**
        #
        # Jaime, del reel 2: *«el guion deja de lado los puntos comparativos;
        # eso debe quedar claro en el proceso, no es solo el guion, es la
        # intencion comunicativa: si es comparar, entonces las comparaciones
        # deben ser claras»*. Y era literal: el montaje cortaba justo antes de
        # las dos cifras -acababa en «de cada 100 dolares que el»- asi que la
        # pieza planteaba una comparacion y no daba ninguno de los dos numeros.
        #
        # La puntuacion de cobertura no lo podia ver: mide cuanto del beat dice
        # la unidad, y un trozo sin la cifra puede cubrir mucho vocabulario. Lo
        # que hace falta es una condicion **dura**, declarada en el frame: si la
        # etapa dice que tiene que sonar un numero, quien no lo diga no compite.
        exige = etapa.get("debe_decir") or []
        if exige:
            antes = len(puntuados)
            puntuados = [x for x in puntuados
                         if all(dice(x[1]["texto"], t) for t in exige)]
            if not puntuados:
                # **Ultima puerta del protocolo: buscarlo en la cinta.**
                #
                # Jaime: *«siempre va a estar; puede estar fragmentado o cortado,
                # pero esta»*. Y aqui estaba: la frase de los 30.000 del reel 1
                # vive en un tramo tan repetido que pasa de los 22 s de voz y el
                # filtro de candidatos la tira entera. Que una unidad no sea
                # publicable **no significa que el dato no este**.
                #
                # Se busca la palabra en el transcript y se toma la frase que la
                # contiene, de punto a punto. Sale larga y con repeticiones; de
                # eso se encarga la poda despues.
                hallado = None
                for t in exige:
                    r = frase_con(t)
                    if r:
                        hallado = r
                        break
                if hallado:
                    a_, b_ = hallado
                    txt = texto_en(hallado)
                    print(f"  beat {i + 1} ({etapa['etapa']}): {exige} no estaba en "
                          f"ninguna unidad; encontrado en la cinta "
                          f"({a_:.2f}-{b_:.2f})", file=sys.stderr)
                    u = {"a": a_, "b": b_, "texto": txt, "clave": set(norm(txt)),
                         "aire": 0.0, "pal": [[w["start"], w["end"], w["text"]]
                                              for w in _ws if a_ <= w["start"] <= b_]}
                    usados.append(u)
                    elegidos.append({**u, "beat": i + 1, "etapa": etapa["etapa"],
                                     "obligatorio": bool(etapa.get("obligatorio")),
                                     "score": 1.0,
                                     "voz": expresividad(toma, a_, b_)})
                    continue
                print(f"  beat {i + 1} ({etapa['etapa']}): ninguna unidad dice "
                      f"{exige} — de {antes} candidatas. La etapa se queda sin "
                      f"material antes que decirlo a medias.", file=sys.stderr)
                continue
        techo = max(p for p, _ in puntuados)
        # **Con `debe_decir` cumplido, el umbral absoluto sobra.** Ese umbral
        # mide parecido de vocabulario con el libreto, y ya no hace falta para
        # decidir si la unidad viene al caso: **dice la cifra que la etapa exige**,
        # que es una prueba mas fuerte. Dejandolo, el reel 1 tiraba la unica
        # unidad que decia los 30.000 por no parecerse bastante al parrafo.
        suelo = RELATIVO * techo if exige else max(UMBRAL, RELATIVO * techo)
        finalistas = sorted((x for x in puntuados if x[0] >= suelo),
                            key=lambda x: -x[0])[:FINALISTAS]
        if not finalistas:
            print(f"  beat {i + 1} ({etapa['etapa']}): SIN MATERIAL — "
                  f"«{beat[:60]}…»", file=sys.stderr)
            continue

        # Tres criterios, en el orden que fijó Jaime: **el mensaje, luego cómo
        # se dice, luego cómo se ve**.
        #
        # 1. La cobertura ya filtró quién compite — eso es el mensaje.
        # 2. Entre los que lo dicen, primero la frase entera y sin trabarse: una
        #    frase rota o un «usted usted» siguen siendo defectos de mensaje.
        # 3. Y sólo entonces decide la voz, que es lo que se oye.
        #
        # Sin el paso 2, la voz rescataba tomas trabadas: el arranque fallido
        # tiene saltos de tono, así que **puntúa alto justamente por tropezar**.
        #
        # Si la toma de ese audio no sirve visualmente, se pone una tarjeta — el
        # plano se sustituye, la voz no.
        medidos = [(expresividad(toma, u["a"], u["b"]), p, u)
                   for p, u in finalistas]
        # **Casi siempre secuencial.** Entre dos candidatas que dicen lo mismo,
        # gana la que va **despues de la etapa anterior**: Jaime graba en orden.
        # Es desempate y no filtro, porque el mismo dijo *«no siempre»* — un
        # filtro duro tiraria la buena las veces que se sale del orden.
        ultimo = max((u["b"] for u in elegidos), default=0.0)
        mejore, mejorp, mejor = max(
            medidos,
            key=lambda t: (-trabado(t[2]["texto"]), integridad(t[2]["texto"]),
                           int(t[0] / PASO_VOZ), t[2]["a"] >= ultimo, t[1]))
        mejor = completar(mejor)
        usados.append(mejor)
        elegidos.append({**mejor, "beat": i + 1, "etapa": etapa["etapa"],
                         "obligatorio": bool(etapa.get("obligatorio")),
                         "score": round(mejorp, 3), "voz": round(mejore, 2)})

    # El orden es el del LIBRETO, no el de la grabación.
    #
    # **El presupuesto ya no recorta.** Jaime: *«respeta el guion; si hay
    # necesidad de recortar lo definimos al final»* y *«el ajuste de tiempo lo
    # hacemos al final con el reel montado»*.
    #
    # Antes, al pasarse de presupuesto, caía el beat peor cubierto — y eso es
    # una decisión de montaje tomada por una resta. Un beat que sobra por
    # duración no sobra por argumento: qué se va se mira con la pieza delante,
    # no con una cuenta.
    #
    # Se avisa con la cifra, que es lo que hace falta para decidir después.
    total = sum(u["b"] - u["a"] for u in elegidos)
    if budget and total > budget:
        print(f"  ojo: {total:.1f}s sobre la indicación de {budget:.0f}s "
              f"(+{total - budget:.1f}s). NO se recorta: el ajuste se decide "
              f"al final, sobre el montaje.", file=sys.stderr)

    # **Ajustes finos de entrada o salida por etapa.**
    #
    # Una unidad puede arrancar con el intento fallido que la precede — el reel
    # 1 empieza su etapa 7 con un «hasta 500» suelto antes de la frase buena.
    # Recortar eso es ejecución, no mensaje, así que no se consulta: se declara
    # en `frames.json` y se aplica.
    ajustes = dict(frame.get("ajustes", {}))
    # Los recortes que Jaime marcó en la base de datos entran por la misma
    # puerta que los declarados en el frame.
    for k, v in fijados.items():
        if v.get("estado") == "recortar":
            if v.get("entra_en"):
                ajustes[f"beat_{k}_entra_en"] = v["entra_en"]
            if v.get("sale_en"):
                ajustes[f"beat_{k}_sale_en"] = v["sale_en"]
    for u in elegidos:
        d = ajustes.get(f"beat_{u['beat']}_entra_en")
        if d is not None and u["a"] < d < u["b"]:
            u["a"] = d
        h = ajustes.get(f"beat_{u['beat']}_sale_en")
        if h is not None and u["a"] < h < u["b"]:
            u["b"] = h

    # **Las decisiones de oido se re-imponen.** `apertura` y `cierre` salen de
    # `frames.json` y mandan sobre lo que eligio el montaje: es el aprendizaje
    # 13 convertido en dato — las heuristicas limpian, no eligen.
    def fuera(segs, rangos):
        """Quita por INTERSECCION, no por igualdad: el tramo a sustituir suele
        estar partido en varios despues de quitar silencios."""
        return [t for t in segs
                if not any(min(t[1], y) - max(t[0], x) > 0.05
                           for x, y in rangos)]


    def repetido_por(rangos):
        """Las unidades elegidas que un tramo declarado vuelve a decir.

        **Jaime graba en orden y repite hasta que sale**: *«no paso a la
        siguiente frase sin tener al menos una toma o serie de tomas
        ajustada»*. De ahi que entre dos versiones de la misma idea **la buena
        sea la ultima**, y que las anteriores sean intentos, no material.

        La apertura y el cierre se eligen de oido y casi siempre son una toma
        POSTERIOR y mejor del mismo beat. Sin esto el montaje emitia las dos: en
        el reel 3 la pieza decia la tesis dos veces seguidas, primero en su
        version floja y luego en la buena, que es lo que Jaime llamo *«mutilado,
        repetitivo»*.
        """
        dicho = {r: set(norm(texto_en(r))) for r in map(tuple, rangos)}
        malos = []
        for u in elegidos:
            k = set(norm(u.get("texto", "")))
            if not k:
                continue
            for r, palabras in dicho.items():
                if not palabras:
                    continue
                comun = len(k & palabras) / max(1, len(k))
                # Que el tramo declarado diga casi todo lo que dice la unidad.
                if comun > 0.7 and u["a"] < r[0]:
                    malos.append((u, r, round(comun, 2)))
                    break
        return malos

    apertura = frame.get("apertura")
    cierre = frame.get("cierre")
    # Una unidad puede traer dos tramos: son dos frases seguidas de la misma
    # toma con la cola redundante de la primera fuera. Ver `unir`.
    # **La poda va aqui, sobre lo ya elegido.** Cada unidad pierde sus
    # repeticiones internas -y sobre todo sus autocorrecciones, que son
    # informacion contradictoria en pantalla- y se queda con la ultima version.
    for u in elegidos:
        exige_ = (frame["beats"][u["beat"] - 1].get("debe_decir") or []
                  if u["beat"] - 1 < len(frame["beats"]) else [])
        r = podar(u, exige_)
        if not r:
            continue
        tramos, quitado, que = r
        u["tramos"] = (u["tramos"][:-1] + tramos) if u.get("tramos") else tramos
        print(f"  beat {u['beat']}: podadas repeticiones ({quitado}s) — "
              f"«{que[:70]}»", file=sys.stderr)

    segs = [t for u in elegidos
            for t in (u.get("tramos") or [[round(u["a"], 3), round(u["b"], 3)]])]
    if apertura:
        # **La apertura RECORTA la unidad, no la sustituye.**
        #
        # Es la distincion de `estado.py` entre `recortar` y `rechazado`, que ya
        # costo un fallo una vez: una frase que **si dice** la etapa pero entra
        # mal se recorta; sustituirla entera tira la frase buena. El reel 2 lo
        # enseno crudo — la apertura declarada (97,20-99,98) vive DENTRO de la
        # unidad que el paso 2 eligio para el beat 1 (81,39-105,11), asi que
        # sustituirla dejaba la etapa en «en Brampton, tiene dos contratos,» y
        # la pieza empezaba por un fragmento de dos segundos.
        #
        # Si la apertura cae dentro de una unidad elegida, se conserva **desde
        # donde Jaime dijo hasta donde acaba la frase**. Si no toca ninguna, se
        # impone tal cual, que es el caso para el que se penso.
        dentro = next((u for u in elegidos
                       if u["a"] <= apertura[0] + 0.05 and apertura[1] <= u["b"] + 0.05),
                      None)
        trozo = [apertura[0], round(dentro["b"], 3)] if dentro else apertura
        segs = [trozo] + fuera(segs, [trozo])
        # Y lo que la apertura ya dice, no se dice otra vez antes.
        # La unidad de la que sale el propio recorte no cuenta: el tramo no la
        # repite, **es ella**. Sin esto la regla se comia el beat que acababa de
        # conservar (C-47).
        for u, _, cuanto in [x for x in repetido_por([trozo]) if x[0] is not dentro]:
            print(f"  beat {u['beat']}: la apertura dice lo mismo "
                  f"({int(cuanto * 100)}% de las palabras) y es posterior. "
                  f"Grabas en orden y repites hasta que sale: **la buena es la "
                  f"ultima**, asi que el beat se queda con la apertura.",
                  file=sys.stderr)
            segs = [t for t in segs
                    if not (min(t[1], u["b"]) - max(t[0], u["a"]) > 0.05)]
            # **El beat no se pierde: cambia de toma.** Borrarlo de `elegidos`
            # lo dejaba contado como SIN MATERIAL teniendo su frase en pantalla,
            # que es el defecto de C-27 por otra puerta.
            u["a"], u["b"] = trozo[0], trozo[1]
            u["tramos"] = [list(trozo)]

    # **La apertura declarada ES el primer beat.** Si no se elige unidad para
    # el, el beat sale contado como SIN MATERIAL y se le fabrica una tarjeta que
    # tapa justo la apertura. Es el mismo agujero que ya tenia el cierre (C-27)
    # por el otro extremo de la pieza.
    if apertura and not any(u["beat"] == 1 for u in elegidos):
        elegidos.insert(0, {"a": trozo[0], "b": trozo[1], "beat": 1,
                            "etapa": frame["beats"][0]["etapa"],
                            "obligatorio": bool(frame["beats"][0].get("obligatorio")),
                            "score": 1.0, "voz": expresividad(toma, trozo[0], trozo[1]),
                            "texto": texto_en(trozo), "clave": set(norm(texto_en(trozo))),
                            "pal": []})
        print("  beat 1: lo cumple la apertura declarada.", file=sys.stderr)

    if cierre:
        segs = fuera(segs, cierre) + cierre
        # El cierre declarado ES la etapa de registro. Sin esto la comprobación
        # de obligatorios la da por vacía y avisa de un agujero que no existe.
        ultima = len(frame["beats"])
        if not any(u["beat"] == ultima for u in elegidos):
            a0, b0 = cierre[0][0], cierre[-1][1]
            elegidos.append({"a": a0, "b": b0, "beat": ultima,
                             "etapa": frame["beats"][ultima - 1]["etapa"],
                             "obligatorio": True, "score": 1.0, "voz": 0.0,
                             "texto": "(cierre declarado)",
                             "clave": set()})
    total = sum(b - x for x, b in segs)
    return frame, beats, elegidos, total, fijados, segs


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reel", type=int, required=True)
    # **Indicación, no tope.** Ad 120 s, reel 90 s, y varía según lo que la
    # pieza tenga que decir. Sólo avisa: el ajuste se decide al final, sobre el
    # montaje. Ver «Duración» en CLAUDE.md.
    ap.add_argument("--budget", type=float, default=120.0)
    ap.add_argument("--escribir", action="store_true")
    a = ap.parse_args()

    frame, beats, elegidos, total, fijados, segs = montar(a.reel, a.budget)

    print(f"\n=== reel-{a.reel:02d} · {frame['estructura']} · "
          f"{len(elegidos)}/{len(beats)} beats · {total:.1f}s ===")
    print(f"    mecanismo: {frame['mecanismo']['primario']} "
          f"(secundario: {frame['mecanismo']['secundario']})")
    puestos = {u["beat"] for u in elegidos}
    # Se imprime DESPUES de aplicar recortes, apertura y cierre: antes el
    # listado ensenaba tiempos que el EDL ya no tenia.
    porBeat = {u["beat"]: u for u in elegidos}
    for i, b in enumerate(frame["beats"], 1):
        u = porBeat.get(i)
        marca = "!" if b.get("obligatorio") else " "
        if u:
            print(f" {marca}{i:2} {b['etapa']:34} {u['a']:7.2f}-{u['b']:7.2f} "
                  f"({u['b']-u['a']:4.1f}s, voz {u['voz']:.1f}st)  "
                  f"{u['texto'][:58]}")
        else:
            print(f" {marca}{i:2} {b['etapa']:34} — SIN TOMA: va con tarjeta")
    faltan = [b["etapa"] for i, b in enumerate(frame["beats"], 1)
              if i not in puestos and b.get("obligatorio")]
    if faltan:
        print(f"\n  OBLIGATORIOS SIN TOMA: {', '.join(faltan)}", file=sys.stderr)

    if a.escribir:
        # **Biblioteca de partes: lo que QUEDO, no lo que se cayo.**
        #
        # Jaime: *«lo descartado se tira; lo que no se tira es lo que quedo, eso
        # es lo que puede reutilizarse en otro video que hable del mismo tema»*.
        # Un descarte se descarto por algo; un enunciado elegido ya paso por
        # todo — cubre su etapa, esta entero y es el mas expresivo de sus
        # rivales. Se indexa por etapa, que es lo que lo hace buscable.
        toma = rutas.TOMAS[f"reel-{a.reel:02d}"]
        os.makedirs("work/biblioteca", exist_ok=True)
        bf = f"work/biblioteca/reel-{a.reel:02d}.json"
        json.dump({"toma": toma, "estructura": frame["estructura"],
                   "mecanismo": frame["mecanismo"],
                   "partes": [{"etapa": u["etapa"],
                               "start": round(u["a"], 3),
                               "end": round(u["b"], 3),
                               "dur": round(u["b"] - u["a"], 2),
                               "voz_st": u["voz"],
                               "texto": u["texto"]}
                              for u in elegidos]},
                  open(bf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"biblioteca -> {bf} ({len(elegidos)} partes reutilizables)")

        f = f"ads/reel-{a.reel:02d}/edl-sell.json"
        d = json.load(open(f, encoding="utf-8"))
        d["segmentos"] = segs
        # **`detalle` se deriva de `segs`, no de `elegidos`.**
        #
        # Eran dos fuentes para el mismo dato y se separaban en cuanto la
        # apertura o el cierre declarados sustituian algo: en el reel 5 los
        # `segmentos` ya no llevaban el precio y el `detalle` seguia
        # ensenandolo. Es el aprendizaje 33 otra vez.
        porTiempo = {(round(u["a"], 3), round(u["b"], 3)): u for u in elegidos}

        def deBeat(a_, b_):
            """El beat de un corte, aunque sea la apertura o el cierre.

            La apertura declarada es un RECORTE de la unidad que el montaje
            eligio para ese beat, asi que comparten tiempo pero no extremos. Sin
            esto salia con `beat: null` y todo lo que se ancla al beat —la idea
            fuerza, la placa, el tratamiento— se lo saltaba en silencio.
            """
            exacto = porTiempo.get((round(a_, 3), round(b_, 3)))
            if exacto:
                return exacto
            for u in elegidos:
                if min(u["b"], b_) - max(u["a"], a_) > 0.2:
                    return u
            return None
        d["detalle"] = []
        for a_, b_ in segs:
            u = deBeat(a_, b_)
            d["detalle"].append(
                {"start": a_, "end": b_, "beat": u["beat"] if u else None,
                 "etapa": u["etapa"] if u else "apertura o cierre declarado",
                 "obligatorio": bool(u["obligatorio"]) if u else True,
                 "cobertura": u["score"] if u else None,
                 "voz_st": u["voz"] if u else None,
                 "texto": u["texto"] if u else ""})
        d["estructura"] = frame["estructura"]
        d["mecanismo"] = frame["mecanismo"]
        # **Un corte sin beat es una etapa perdida, y hay que gritarlo.**
        #
        # Un corte declarado a mano que no recorta ninguna unidad elegida sale
        # con `beat: None`, y entonces todo lo que se ancla al beat -idea
        # fuerza, placa, tratamiento, panel- se lo salta en silencio. Peor: la
        # etapa que ese corte cumple sigue contandose como SIN MATERIAL aunque
        # su frase este en pantalla. Paso en las dos primeras piezas: el reel 1
        # cerraba sin registro teniendo la frase a veinte segundos, y el reel 2
        # daba el beat 10 por vacio con «el link esta abajo» ya montado.
        #
        # No se adivina a que etapa pertenece -eso seria inventar-, se avisa con
        # el tiempo exacto para poder declararlo.
        huerfanos = [x for x in d["detalle"] if x["beat"] is None]
        if huerfanos:
            donde = ", ".join("%.2fs" % x["start"] for x in huerfanos)
            print(
                "  ojo: %s tiene %d corte(s) sin beat (%s). Lo que se ancle al "
                "beat se lo salta, y su etapa cuenta como sin material aunque "
                "suene. Hay que declararles el beat a mano."
                % (f"reel-{a.reel:02d}", len(huerfanos), donde),
                file=sys.stderr,
            )

        d["sin_toma"] = [{"beat": i, "etapa": b["etapa"],
                          "obligatorio": bool(b.get("obligatorio")),
                          "libreto": beats[i - 1]}
                         for i, b in enumerate(frame["beats"], 1)
                         if i not in puestos]
        d["duracion_montada_s"] = round(total, 2)
        # **Un diccionario, y luego sus claves.** Antes se escribia
        # `revision["apertura_y_cierre"]` y la linea siguiente reasignaba
        # `revision = {...}` entero: la nota se perdia en silencio.
        d["revision"] = {
            "montaje": "Por beats del libreto: un beat, un enunciado, en el "
                       "orden del libreto. La estructura y la funcion de cada "
                       "beat salen de ads/frames.json. Ver scripts/beats.py.",
            "apertura_y_cierre": "La apertura y el cierre salen de "
                                 "ads/frames.json y se re-imponen sobre lo que "
                                 "eligio el montaje: son decisiones de oido, y "
                                 "las heuristicas limpian pero no eligen.",
            "duracion": "Nada se recorta por duracion durante el montaje. El "
                        "ajuste se decide al final, sobre la pieza montada.",
        }
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\nescrito -> {f}")
