"""Transcribe el reel YA MONTADO y genera sus subtítulos.

Por qué no vale el transcript del bruto
---------------------------------------
Los subtítulos salían de las palabras del bruto mapeadas a la línea de tiempo, y
eso hereda todos sus defectos: las palabras estiradas que cruzan silencios
eliminados, y los tramos donde el transcript se salta palabras enteras. En el
reel 6 el tramo 22,08-30,66 dice de oído «nadie le mandó una carta, el banco no
le dijo que no, el CRA no lo llamó…», y el transcript del bruto empieza en «el
CRA»: los subtítulos se comían la primera mitad.

Transcribir lo montado no tiene ese problema — **es literalmente lo que se oye**,
sin huecos que remapear. Y como el montaje ya viene sin silencios, whisper tiene
menos donde alucinar.

Se pide granularidad de palabra (`-ml 1 -sow`) para poder agrupar en frases
cortas con tiempos reales.
"""
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402
from dominio.texto import comparable as _comparable  # noqa: E402
from dominio.idioma import Idioma  # noqa: E402

W = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
FPS = 30
# Medido sobre render: la Montserrat 800 gasta ~0,70 em por caracter, así que a
# 62 px caben ~22 por línea en los 950 útiles. 36 da dos líneas con holgura.
TOPE = 36
# **Cuantas palabras seguidas se aceptan cambiar de una vez.** Un desajuste
# de una, dos o tres palabras es una mal oida; de cuatro para arriba ya no es
# eso, es que la cinta y el montaje no son del mismo corte, y ahi sustituir
# seria inventar la frase en vez de corregirla.
TRAMO = 3


#: Largo máximo de cada trozo que se transcribe, en segundos (C-472).
TROZO = 20


def trozos(wav):
    """Dónde partir el montaje para transcribirlo: en silencios, cada `TROZO` s.

    **De una pasada, whisper apelmaza los tiempos** (C-472). En reel-14 metió
    doce palabras —«para otros Canadá es la tierra de las oportunidades»— entre
    4,17 y 4,24 s, y el subtítulo del gancho se quedó congelado cuatro segundos
    y se saltó una línea. Los mismos diez segundos transcritos solos salen con
    cada palabra en su sitio, medidos contra los silencios del audio.

    **Y cada trozo empieza donde empieza su silencio, no en su medio** (C-486).
    Partido en el medio, el trozo de reel-12 arrancaba 0,4 s antes de «No
    excepcional» y whisper estiraba las primeras palabras: «más que nunca» salía
    a 24,46 s cuando la voz lo dice a 21,4, y la línea anterior se quedaba cinco
    segundos quieta. Con el silencio entero delante, cae a 21,38. El anterior
    sigue acabando en el medio, así que lo que comparten es silencio: ninguna
    palabra sale dos veces.
    """
    r = subprocess.run(["ffmpeg", "-v", "info", "-i", wav, "-af",
                        "silencedetect=noise=-35dB:d=0.3", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    ini = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    fin = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    dura = os.path.getsize(wav) / 32000        # 16 kHz, mono, 16 bit
    silencios = [(a, (a + b) / 2) for a, b in zip(ini, fin)]
    cortes, desde = [], 0.0
    while dura - desde > TROZO:
        dentro = [s for s in silencios if desde + 4 < s[1] <= desde + TROZO]
        entra, desde = dentro[-1] if dentro else (desde + TROZO, desde + TROZO)
        cortes.append((entra, desde))
    entradas = [0.0] + [e for e, _ in cortes]
    salidas = [m for _, m in cortes] + [dura]
    return list(zip(entradas, salidas))


def transcribir(mp4, wav, base, idioma):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp4,
                    "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
                   check=True)
    todas = []
    for k, (a, b) in enumerate(trozos(wav)):
        pieza = f"{base}.t{k}"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}",
                        "-t", f"{b - a:.3f}", "-i", wav, "-c:a", "pcm_s16le",
                        pieza + ".wav"], check=True)
        subprocess.run(gpu.whisper() + [
                        "-m", os.path.join(W, "ggml-medium.bin"),
                        *idioma.banderas, "-mc", "0", "-ml", "1", "-sow",
                        "-oj", "-of", pieza, "-f", pieza + ".wav"],
                       capture_output=True, check=True)
        with open(pieza + ".json", encoding="utf-8") as fh:
            for s in json.load(fh)["transcription"]:
                off = s["offsets"]
                todas.append({**s, "offsets": {"from": off["from"] + a * 1000,
                                               "to": off["to"] + a * 1000}})
        for ext in (".wav", ".json"):
            os.remove(pieza + ext)
    d = {"transcription": todas}
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(d, fh, ensure_ascii=False)
    out = []
    for s in d["transcription"]:
        t = s["text"].strip()
        if not t or t.startswith("["):
            continue
        # Whisper mete comillas donde no las hay: en el reel 1 salio
        # «le queda lo que deberia"» con una comilla suelta al final. En un
        # subtitulo quemado eso no se puede corregir despues.
        # «>>» es la marca de cambio de hablante de whisper, no texto (C-580):
        # reel-19 salio con «¿usted sabe>> ¿Cuánta plata…» en pantalla.
        t = t.replace('"', "").replace("“", "").replace("”", "")
        t = t.replace(">>", "").replace("<<", "").strip()
        if not t:
            continue
        off = s["offsets"]
        out.append({"start": off["from"] / 1000, "end": off["to"] / 1000, "text": t})
    return out


def costuras(slug):
    """Donde empieza cada etapa en el montaje, sacado del plan (C-578).

    **Un subtitulo no cruza de una etapa a otra.** reel-18, 18-10: el gancho
    enseñaba «Que si tengo miedo, / CUANDO YO LLEGUE», y «cuando yo llegue» es
    de la etapa 2 y no se oye hasta 5,34 s. El agrupador sólo miraba caracteres
    y pausas, y en una costura no hay pausa: el corte las quita.
    """
    try:
        esc = json.load(open(f"work/scenes/{slug}/plan-full.json",
                             encoding="utf-8"))["escenas"]
    except (OSError, ValueError, KeyError):
        return []
    return [b["montado_desde"] for a, b in zip(esc, esc[1:])
            if a.get("beat") != b.get("beat")]


def agrupar(words, cortes=()):
    caps, buf = [], None
    for w in words:
        cierra = w["text"][-1:] in ".?!"
        # La palabra es de la etapa donde ACABA: whisper adelanta los arranques
        # (en reel-18 «cuando» empezaba en 5,02 con la costura en 5,34).
        costura = next((c for c in cortes
                        if (buf["end"] if buf else -1) <= c < w["end"]), None)
        if buf and (len(buf["text"]) + 1 + len(w["text"]) > TOPE
                    or w["start"] - buf["end"] > 0.7 or costura is not None):
            caps.append(buf); buf = None
        if not buf:
            buf = {"start": w["start"], "end": w["end"], "text": w["text"]}
            if costura is not None:
                buf["start"], buf["costura"] = max(w["start"], costura), True
        else:
            buf["text"] += " " + w["text"]
            buf["end"] = w["end"]
        if cierra:
            caps.append(buf); buf = None
    if buf:
        caps.append(buf)
    # **Un subtitulo nunca es UNA palabra suelta.**
    #
    # Jaime, tres veces sobre reel-01: *«al final queda un "semanales"
    # huerfano; "le cuesta hasta ... semanales" va en una misma frase»*, y la
    # tercera: *«el semanales persiste»*.
    #
    # Las tres veces se arreglo **el corte**, y las tres veces volvio, porque el
    # corte no era el problema: el EDL ya trae la frase entera en UN segmento
    # —«...costando hasta 550 dolares semanales», cinta 562,85-571,05—. Quien la
    # partia es esto: whisper oye una micro-pausa antes de «semanales», escribe
    # «dolares. Semanales.», y aqui se cerraba el subtitulo en ese punto.
    #
    # **Es la averia que el nombro:** dos cosas decidiendo donde se parte la
    # frase —el corte y el agrupador— y el arreglo aplicandose siempre a una
    # sola. El corte sabe que es una frase; el agrupador no le preguntaba.
    #
    # La regla que lo cierra no necesita preguntar nada: una palabra sola no es
    # un subtitulo. Se pega a la anterior aunque pase de `TOPE` —una palabra de
    # mas se lee; una palabra huerfana se nota— y si venia detras de un punto
    # que whisper invento, ese punto se va con ella.
    #
    # **Y se va SIEMPRE, no solo si la palabra venia en mayuscula.** La mayuscula
    # era la prueba de que whisper habia cerrado frase ahi, y whisper no la pone
    # siempre: el 7-9-2026, con el corte nuevo, escribio «dolares.» y «semanales.»
    # —la segunda en minuscula— y el punto sobrevivio a la union. La linea quedo
    # «costando hasta 550 dolares. semanales.», o sea la misma frase partida por
    # un punto en medio, que es la cuarta forma que encuentra el mismo defecto
    # que Jaime lleva denunciando tres vueltas. Si la palabra no era un
    # subtitulo, tampoco era una frase: el punto de delante es invento.
    fuera = []
    for c in caps:
        if fuera and len(c["text"].split()) == 1 and not c.get("costura"):
            prev = fuera[-1]
            suelta = c["text"]
            if prev["text"].endswith("."):
                prev["text"] = prev["text"][:-1]
                suelta = suelta[:1].lower() + suelta[1:]
            prev["text"] += " " + suelta
            prev["end"] = c["end"]
            continue
        fuera.append(c)
    caps = fuera
    # **Sin huecos.** Cada subtitulo se estira hasta el siguiente: la mayoria ve
    # los reels sin audio, asi que un instante sin texto es un instante sin
    # argumento. Un hueco de medio segundo no descansa la vista, la corta.
    # La duracion se calcula EN FRAMES, restando los `at` ya redondeados. Al
    # redondear los segundos por separado —`round(inicio*30)` y
    # `round((fin-inicio)*30)`— quedaban huecos de un frame entre subtitulo y
    # subtitulo. Son 33 ms y no se ven, pero un detector de huecos que siempre
    # encuentra seis deja de servir para encontrar el que si importa.
    ats = [round(c["start"] * FPS) for c in caps]
    out = []
    for i, c in enumerate(caps):
        fin = ats[i + 1] if i + 1 < len(caps) else round((c["end"] + 0.4) * FPS)
        out.append({"at": ats[i],
                    "duration": max(8, fin - ats[i]),
                    "text": c["text"]})
    return out


def esperadas(slug):
    """Las palabras que el montaje DEBERIA decir, tomadas de la cinta.

    El transcript de la cinta lleva cuatro pasadas y el del montaje una sola —y
    una sola pasada *«se come cosas, se queda pegado»* (C-54). Por eso el
    subtitulo decia «pierda la mitad en **puestos**» donde la cinta dice
    «impuestos», «al **cR**» donde dice «CRA», y «estar costando **esta casa**»
    donde dice «hasta 550 dolares».

    **La division correcta: el tiempo lo da el montaje, las palabras las da la
    cinta.** Transcribir el montaje sigue siendo lo correcto para los tiempos
    —ahi no hay huecos que remapear— pero sus palabras son las peores del
    sistema y son justo las que el espectador lee.
    """
    import sys as _s
    _s.path.insert(0, os.path.dirname(__file__))
    import transcribir as _tr, rutas as _ru
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache, out = {}, []
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        t = det.get("toma") or _ru.TOMAS.get(slug)
        if t not in cache:
            try:
                cache[t] = _tr.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        out += [w["text"] for w in cache[t]
                if rango[0] - 0.02 <= w["start"] and w["end"] <= rango[1] + 0.02]
    return out


# **Comparar dos palabras es `dominio.texto.comparable`**, y estaba escrito
# aquí otra vez. Es la vara con la que se decide si el subtítulo dice lo mismo
# que la cinta, así que tenerla en dos sitios es tener dos varas.
def _limpia(t):
    return _comparable(t).strip()


def glosario(caps):
    """Corrige lo que Whisper oye mal **siempre igual**. Ver `ads/glosario.json`.

    `reconciliar` compara el montaje contra la cinta y arregla lo que difiere.
    Pero hay errores que las dos pasadas cometen por igual —la cinta tambien dice
    «Electric System»— y ahi comparar no descubre nada: las dos se equivocan en
    lo mismo y quedan de acuerdo.

    Esta es la herramienta que le falta, y **estaba declarada en el docstring de
    `reconciliar` sin existir**: *«las siglas se arreglan con un glosario, que es
    la herramienta que les corresponde»*. Se escribio la frase y no el fichero,
    asi que el arranque de reel-02 llevaba dias presentando «Electric System
    Brampton», una empresa que no existe, en lugar de «un electricista en
    Brampton». Jaime lo dijo dos veces.

    Solo entran errores **vistos**, cada uno con su pieza en `visto_en`: una
    entrada inventada rompe una frase que estaba bien, que es exactamente lo que
    hacia la regla de parecido de letras que el glosario vino a sustituir.
    """
    ruta = os.path.join("ads", "glosario.json")
    try:
        terminos = json.load(open(ruta, encoding="utf-8"))["terminos"]
    except (OSError, ValueError, KeyError):
        return caps, 0
    # De mas largo a mas corto: «y que ya» tiene que probarse antes que «cr», o
    # una entrada corta parte la frase que la larga venia a arreglar.
    # **Una entrada mal escrita no puede tumbar el paso, y ya lo hizo dos veces.**
    #
    # Una vez con una cadena vacia —el glosario SUSTITUYE, no borra— y hoy con el
    # valor puesto como texto en vez de como objeto: `v["es"]` sobre una cadena
    # revienta con `TypeError` y se lleva por delante el montaje entero, despues
    # de haber cortado y renderizado. Este fichero se edita a mano por diseño,
    # asi que tiene que aguantar que se edite mal.
    #
    # Se salta la entrada rota **y se dice cual**: callarla la dejaria sin
    # efecto para siempre sin que nadie lo notara, que es peor que el error.
    pares, rotas = [], []
    for k, v in terminos.items():
        dice = v.get("es") if isinstance(v, dict) else v
        if not isinstance(k, str) or not isinstance(dice, str)                 or not k.strip() or not dice.strip():
            rotas.append(k)
            continue
        # La entrada se compara con la MISMA vara que el subtitulo (`_limpia`):
        # sin ella «Bultán» nunca casaba con «bultan» y su entrada no hacia nada
        # (C-433).
        pares.append(([_limpia(w) for w in k.split()], dice.split()))
    if rotas:
        print(f"    glosario: {len(rotas)} entrada(s) mal escritas, sin efecto:"
              f" {rotas}. El valor es un objeto con «es», y no puede ir vacio.")
    pares.sort(key=lambda x: -len(x[0]))

    # **Se busca sobre la secuencia de PALABRAS, no dentro de cada subtitulo.**
    #
    # Trabajando por subtitulo, una entrada de varias palabras no se encuentra si
    # cae en una costura — y caen: los subtitulos se cortan a 36 caracteres, sin
    # mirar la frase. «moldura de carne» quedaba partido entre «…es una moldura
    # de» y «carne, para otros…», asi que el arranque de reel-07 seguia diciendo
    # «moldura» con su entrada puesta en el glosario y funcionando.
    #
    # Aplanando a palabras con su subtitulo de origen, la costura deja de existir
    # para la busqueda y sigue existiendo para el dibujo.
    plano = [(i, w) for i, c in enumerate(caps) for w in c["text"].split()]
    n, j = 0, 0
    while j < len(plano):
        for mal, bien in pares:
            k = len(mal)
            if j + k > len(plano):
                continue
            trozo = [_limpia(w) for _, w in plano[j:j + k]]
            if trozo != mal:
                continue
            # La mayuscula de lo que habia manda sobre la de la correccion: si la
            # frase empezaba en mayuscula, la corregida tambien.
            arr = plano[j][1][:1].isupper()
            puesto = list(bien)
            if arr:
                puesto[0] = puesto[0].capitalize()
            # La puntuacion pegada a la ultima palabra se conserva: «carne,»
            # tiene que seguir llevando su coma.
            cola = re.sub(r"^[\wáéíóúüñÁÉÍÓÚÜÑ]+", "", plano[j + k - 1][1])
            puesto[-1] += cola
            # Todo lo corregido cae en el subtitulo de la PRIMERA palabra: mover
            # texto de un subtitulo a otro cambiaria cuando se lee.
            destino = plano[j][0]
            plano[j:j + k] = [(destino, w) for w in puesto]
            n += 1
            j += len(puesto) - 1
            break
        j += 1
    if n:
        rehecho = {}
        for i, w in plano:
            rehecho.setdefault(i, []).append(w)
        for i, c in enumerate(caps):
            c["text"] = " ".join(rehecho.get(i, [])) or c["text"]
    return caps, n


def reconciliar(caps, esperado, ventana=6):
    """Sustituye las palabras del montaje por las de la cinta cuando difieren.

    **El tiempo lo da el montaje; las palabras las da la cinta** (C-80). La
    cinta lleva cuatro pasadas y el montaje una sola, asi que donde discrepan
    manda la cinta.

    Las dos secuencias dicen lo mismo y en el mismo orden, asi que se alinean
    con `difflib` y se mira **donde no coinciden**. No es parecido de letras
    —esa regla hacia mas dano que bien y esta fuera desde C-80—: es alineacion
    exacta, y solo se toca lo que cae entre dos trozos que si coinciden.

    ## Por que no bastaba sustituir palabra a palabra

    La version anterior recorria las dos listas con un puntero y solo sabia
    cambiar **una palabra por una**, cuando la de la cinta contenia a la del
    montaje por el final («impuestos» contra «puestos»). Un desajuste de
    **dos palabras por una** le era invisible, y ahi se colo el peor error del
    lote: reel-01 decia en pantalla *«de manera legal y no las reglas»* donde la
    cinta dice *«de manera legal siguiendo las reglas»*. Las dos palabras
    sobrantes eran de dos y tres letras, por debajo del minimo de la regla, asi
    que pasaron enteras y **el subtitulo afirmaba lo contrario de lo que el
    dice**. Jaime: *«eso es peligrosisimo»*, y lo es: es cumplimiento, no estilo.

    ## Los limites, y por que hay limites

    Se sustituye un tramo por otro solo si **los dos son cortos** (`TRAMO`) y
    ninguna linea se queda vacia. Un desajuste largo no es una palabra mal oida:
    es que la cinta y el montaje son de cortes distintos, y ahi reescribir seria
    inventar. Eso **no se calla** — se cuenta al final, porque un subtitulo que
    discrepa de la cinta y nadie mira es como salio «y no las reglas».
    """
    if not esperado:
        return caps, 0
    # **La cinta pasa primero por el glosario.** No es autoridad absoluta: hay
    # errores que las cuatro pasadas cometen igual —lo dice el propio glosario,
    # «la cinta tambien dice Electric System»—. Sin esto, cuadrar contra ella
    # ROMPIA palabras que estaban bien: «su contador» pasaba a «su contado» en
    # reel-02 y reel-03, porque asi lo escribe la cinta y el glosario lo
    # arreglaba despues... sobre el subtitulo, cuando ya se habia estropeado.
    esperado = glosario([{"text": " ".join(esperado)}])[0][0]["text"].split()
    plano = [(i, w) for i, c in enumerate(caps) for w in c["text"].split()]
    dicho = [_limpia(w) for _, w in plano]
    cinta = [_limpia(x) for x in esperado]
    nuevas = [[] for _ in caps]
    cambios, sin_resolver = 0, []

    def tal_cual(i1, i2):
        for k in range(i1, i2):
            nuevas[plano[k][0]].append(plano[k][1])

    ops = difflib.SequenceMatcher(None, dicho, cinta,
                                 autojunk=False).get_opcodes()

    def anclado(t):
        """¿El tramo `t` tiene a los lados trozos que SI coinciden?

        Es el limite que faltaba, y lo enseño reel-01: sin el, «Es un negocio
        que esta vendiendo» se convertia en «Su negocio QUE esta vendiendo»
        —la cinta dice «Su negocio esta vendiendo», y el «que» sobrante caia en
        otro tramo, asi que se cambiaba medio desajuste y quedaba peor que
        antes—. Un cambio solo es seguro cuando lo que hay pegado a los dos
        lados coincide palabra por palabra: entonces se sabe que el desajuste
        empieza y acaba donde parece.
        """
        i = ops.index(t)

        def basta(j):
            # Fuera de la lista no hay nada que desalinear: el borde ancla.
            if j < 0 or j >= len(ops):
                return True
            o = ops[j]
            if o[0] != "equal":
                return False
            # Dos palabras iguales bastan para saber que el desajuste empieza y
            # acaba donde parece. **Y una tambien, si detras no queda nada**:
            # «pierda la mitad en puestos de» contra «...impuestos de» tiene un
            # solo «de» al final y es el caso de C-80, el que este paso existe
            # para arreglar. Pidiendo dos se rechazaba a si mismo.
            return o[2] - o[1] >= 2 or j in (0, len(ops) - 1)

        return basta(i - 1) and basta(i + 1)

    for t in ops:
        op, i1, i2, j1, j2 = t
        # `equal` no toca nada, y `delete` —el montaje dice algo que la cinta no
        # tiene— se respeta: borrar palabras deja la linea sin el tiempo que
        # ocupa. `insert` tampoco entra: una palabra de la cinta que el montaje
        # no dice no tiene sitio en ningun subtitulo.
        if op in ("equal", "delete"):
            tal_cual(i1, i2)
            continue
        if op == "insert":
            sin_resolver.append("+ " + " ".join(esperado[j1:j2]))
            continue
        # **Las cifras no las arregla la cinta.** El montaje escribe «180.000»
        # y la cinta «180 mil»: las dos dicen lo mismo y la del montaje se lee
        # mejor en pantalla. Lo que va rotulado lo gobiernan el copy y su
        # `fuente`, no el transcript, asi que aqui no se toca.
        if any(any(ch.isdigit() for ch in w) for w in
               [w for _, w in plano[i1:i2]] + list(esperado[j1:j2])):
            tal_cual(i1, i2)
            continue
        # **Y dos formas de que la cinta este PEOR que el montaje, medidas en
        # el lote.** La primera: la cinta se come una letra del final —escribe
        # «contado» por «contador», «lastre» por «elastre»—, o sea que el
        # montaje trae la palabra mas completa. Es la regla de C-80 al reves, y
        # al reves no vale. La segunda: la cinta ofrece solo palabras cortas
        # —«le» por «la», «porque» por «o que»—, que es ruido de funcion y no
        # una palabra mal oida. Las de verdad son largas: «siguiendo»,
        # «palancarse», «moledora», «bootcamp».
        corta = max((len(x) for x in cinta[j1:j2]), default=0) < 4
        recorta = (i2 - i1 == 1 and j2 - j1 == 1
                   and dicho[i1].endswith(cinta[j1])
                   and len(dicho[i1]) > len(cinta[j1]))
        if corta or recorta:
            tal_cual(i1, i2)
            continue
        if i2 - i1 > TRAMO or j2 - j1 > TRAMO or not anclado(t):
            sin_resolver.append(f"{' '.join(w for _, w in plano[i1:i2])}"
                                f" -> {' '.join(esperado[j1:j2])}")
            tal_cual(i1, i2)
            continue
        # **La linea de destino se mantiene**: cada palabra de la cinta va a la
        # linea de la palabra del montaje que ocupa su sitio, y la ultima se
        # lleva las que sobren. Asi un tramo que cruza una costura no vacia la
        # linea siguiente, que la dejaria sin nada que dibujar.
        destino = [plano[min(i1 + k, i2 - 1)][0] for k in range(j2 - j1)]
        if any(d not in destino for d in {plano[k][0] for k in range(i1, i2)}):
            sin_resolver.append(f"{' '.join(w for _, w in plano[i1:i2])}"
                                f" -> {' '.join(esperado[j1:j2])} (vaciaria una"
                                " linea)")
            tal_cual(i1, i2)
            continue
        # La mayuscula inicial y la puntuacion final son del montaje: la cinta
        # trae la palabra, no la forma en que estaba escrita en la frase.
        trozo = list(esperado[j1:j2])
        if plano[i1][1][:1].isupper():
            trozo[0] = trozo[0][:1].upper() + trozo[0][1:]
        # **Y no se apila puntuacion.** La palabra de la cinta suele traer ya la
        # suya: «saberlo,» del montaje contra «saberlo.» de la cinta daba
        # «saberlo,.» — y salio en el rotulo grande del gancho de reel-03, que
        # es donde mas se ve. Solo se hereda la del montaje si la de la cinta
        # acaba en letra.
        if trozo[-1][-1:].isalnum():
            trozo[-1] += "".join(c for c in plano[i2 - 1][1] if not c.isalnum())
        for d, w in zip(destino, trozo):
            nuevas[d].append(w)
        cambios += 1

    for c, ws in zip(caps, nuevas):
        c["text"] = " ".join(ws)
    if sin_resolver:
        print(f"    contra la cinta: {len(sin_resolver)} tramo(s) que NO se"
              f" pudieron cuadrar — {sin_resolver[:6]}")
    return caps, cambios


if __name__ == "__main__":
    os.makedirs("work/subs", exist_ok=True)
    todo = {}
    # **El numero se rellena a dos digitos, y esto costo el dia entero.**
    #
    # Los ficheros son `public/reel-01.mp4`, y el resto de pasos aceptan `1`:
    # `plan-reel.mjs --reel 1`, `depurar.py 1`, `render.mjs 1`. Aqui el argumento
    # se pegaba tal cual, asi que `subtitular.py 1` buscaba `public/reel-1.mp4`,
    # no lo encontraba, imprimia una linea y **terminaba con exito**.
    #
    # Encadenado detras de los otros pasos con `| tail -1`, esa linea se perdio
    # en todas las pasadas del dia: los subtitulos se quedaron en los de trece
    # horas antes, `reels-spec` los metio en el spec, y yo confirme «seis piezas
    # sin repeticiones» contando sobre un corte que ya no existia.
    #
    # Por eso ahora **faltar un corte es un fallo**, no un aviso. Un paso que no
    # hizo su trabajo y devuelve exito manda el error mas lejos de donde se ve.
    faltan = []
    for r in sys.argv[1:] or ["01", "02", "03", "04", "05", "06"]:
        r = f"{int(r):02d}" if r.isdigit() else r
        mp4 = f"public/reel-{r}.mp4"
        if not os.path.exists(mp4):
            print(f"reel-{r}: falta {mp4}", file=sys.stderr)
            faltan.append(r)
            continue
        base = f"work/subs/reel-{r}"
        caps = agrupar(transcribir(mp4, base + ".wav", base,
                                   Idioma.de_pieza(f"reel-{r}")),
                       costuras(f"reel-{r}"))
        caps, n = reconciliar(caps, esperadas(f"reel-{r}"))
        caps, g = glosario(caps)
        todo[f"reel-{r}"] = caps
        print(f"reel-{r}: {len(caps)} subtitulos"
              + (f" · {n} contra la cinta" if n else "")
              + (f" · {g} del glosario" if g else ""))
    if todo:
        prev = {}
        if os.path.exists("work/subs/todos.json"):
            prev = json.load(open("work/subs/todos.json", encoding="utf-8"))
        prev.update(todo)
        json.dump(prev, open("work/subs/todos.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    if faltan:
        raise SystemExit(
            f"\nPARA: sin corte para {', '.join('reel-' + f for f in faltan)}."
            " Hay que cortar antes de subtitular — y esto es un fallo y no un"
            " aviso a proposito: subtitulos viejos en el spec son un corte que"
            " nadie ha medido.")
