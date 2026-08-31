"""Los subtítulos de la cinta ENTERA, con varias pasadas por tramo.

Regla de Jaime, y es el paso que faltaba delante de todo lo demás: *«tienes que
pasar el whisper varias veces por tramo, porque ya lo sabes, se come cosas, se
queda pegado, toma silencios y palabras largas. El punto es que lo primero que
necesitamos es los subtítulos; con los subtítulos de todo el video contrastamos
contra el guion, evitamos las repeticiones y puntuamos por sección: la mejor
puntuada en la sección queda»*.

El orden importa y es el que se incumplía: **primero los subtítulos de todo,
después la comparación contra el libreto.** El montaje venía trabajando sobre
*una* pasada de whisper y la trataba como verdad; de ahí salían las unidades de
98 segundos —el modelo no puntúa esas tomas— y con ellas una selección que se
quedaba con lo primero que encajaba.

## Por qué ventanas solapadas y no tramo a tramo

El tramo medido es la unidad correcta —la pausa la mide el detector, no el
modelo— pero **la mediana son 2,2 s y por debajo de ~2,2 s whisper devuelve
vacío**, que es el aprendizaje 18: *una herramienta que devuelve vacío no dice
«no hay nada», dice «no sé»*. Transcribir cada tramo por separado devolvería
silencio en la mitad de la cinta.

Así que la ventana es de `VENTANA` segundos y avanza `PASO`, sobre el audio
**sin silencios**: cada tramo cae dentro de dos o tres ventanas distintas y en
al menos una queda lejos del borde. Eso es «varias veces por tramo» y además
sale más barato que rellenar cada tramo con contexto.

Sobre audio sin silencios porque es lo que impide alucinar (aprendizaje 1) y
porque quita 1.349 s de reloj que no son voz. La correspondencia con la cinta es
exacta: se construye copiando muestras, no estimando.

## Cómo se elige entre pasadas

Cada tramo acaba con tres transcripciones distintas, y la comparación entre
ellas es **asimétrica** a propósito: gana la que **recoge lo que oyeron las
demás sin inventar lo que no oyó ninguna**. El parecido simétrico no vale y
costó una palabra real — entre «porque le duele una muela no» y «porque le duele
no» las dos se parecen igual, así que desempataba cualquier cosa y ganó la que
se comió «una muela». Tres castigos antes de comparar:

- **Alucinación conocida** («gracias por ver el vídeo») → se descarta la
  candidata entera. Aprendizaje 30.
- **N-grama repetido dentro del tramo** → el modelo se atascó.
- **Palabra de más de 1,5 s** → no es una palabra, es un cruce. Aprendizaje 12.
  No descarta, marca.

El acuerdo entre pasadas se guarda. Un tramo con acuerdo bajo es un tramo que
hay que oír, y es información que antes no existía.

    python scripts/transcribir.py            # las siete tomas
    python scripts/transcribir.py --toma 3   # sólo la del reel 3

Deja `work/transcripts/<toma>.json` —**el** transcript, no uno paralelo— y lo
mismo en la base, que es la memoria del proyecto. **Nada aguas abajo puede correr sin esto**: `catalogar.py`
y `beats.py` fallan si falta o si es más viejo que los tramos.
"""
import argparse
import contextlib
import difflib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import unicodedata
import wave

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402

W = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
# **Dos peldanos, y el sello dice cual.** Jaime: *«utilizamos los recursos caros
# y pesados solo en lo que ya sabemos que va a funcionar, y vamos incrementando
# robustez conforme el funnel avanza»*.
#
# Medido sobre la misma ventana de 30 s: `small` 5,7 s, `medium` 19,4 s — 3,4x.
# Y se le nota: `small` dice «para mucho impuesto» donde `medium` dice «paga», y
# tartamudea «usted tiene usted usted tiene». Eso basta para **localizar** donde
# se dice algo en 3.773 s de cinta; no basta para el subtitulo, que es portante.
MODELOS = {"barato": os.path.join(W, "ggml-small.bin"),
           "bueno": os.path.join(W, "ggml-medium.bin")}
MODELO = MODELOS["bueno"]
BASE = os.path.join("ads", "decisiones.db")

# La ventana tiene suelo (aprendizaje 18) y el paso la hace solapar. Con 30 y 15
# salian 1,69 pasadas por tramo, y con dos candidatas **no hay votacion**: se
# parecen lo mismo entre si, asi que el desempate lo decidia cualquier cosa. Con
# paso 10 son tres, que es el minimo para que una discrepancia tenga mayoria.
VENTANA = 30.0
PASO = 10.0
BORDE = 1.5      # a menos de esto del borde, la candidata paga peaje
LARGA = 1.5      # una palabra no dura mas (aprendizaje 12)
# El binario trae 4 hilos por defecto y la maquina tiene 16. Medido sobre la
# misma ventana de 40 s: 4 -> 35,1 s; 8 -> 27,8 s; 12 -> 25,0 s; 16 -> 48,3 s.
# Con 16 se sobresuscribe y **tarda mas del doble** que con 12, asi que no es
# «cuantos mas mejor»: el valor esta medido, no supuesto.
HILOS = 12
# Decodificacion voraz. Medido sobre la misma ventana de 30 s: beam 5 -> 17,0 s;
# `-bs 1 -bo 1` -> 15,4 s con **0,992 de parecido** al de beam 5, o sea el mismo
# texto. Se puede bajar aqui justamente porque hay tres pasadas y consenso: lo
# que el beam compraria —no equivocarse en una decision de decodificacion— lo
# compra mejor la votacion entre pasadas. `-bs 2` sale peor en las dos cosas
# (16,2 s y 0,934), asi que no es una escala: es un escalon.
VORAZ = ["-bs", "1", "-bo", "1"]

# Lo que el modelo dice cuando se queda sin voz. No es transcripcion, es relleno
# aprendido de YouTube — y ademas delata que ahi hay silencio (aprendizaje 30).
ALUCINACIONES = [
    "gracias por ver", "hasta la proxima", "suscribete", "subtitulos realizados",
    "subtitulado por", "amara.org", "www.", "no olvides", "nos vemos en",
    "gracias por su atencion",
]


def limpio(t):
    t = unicodedata.normalize("NFD", (t or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]+", " ", t).split()


def audio(toma):
    """El audio de la toma a 16k mono, una sola vez."""
    wav = os.path.join(rutas.temporal(), f"{toma}.16k.wav")
    if not os.path.exists(wav):
        src = f"{rutas.ORIGEN}/{toma}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn",
                        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
                       check=True)
    return wav


def sin_silencios(wav, runs, destino):
    """Copia sólo los tramos con voz, y devuelve el mapa a la cinta.

    El mapa se construye **contando muestras**, no interpolando: por eso la
    vuelta a los tiempos de la cinta es exacta y no hereda el defecto de estirar
    las palabras que cruzan un hueco eliminado (aprendizaje 1).
    """
    with contextlib.closing(wave.open(wav, "rb")) as f:
        sr = f.getframerate()
        anchura = f.getsampwidth() * f.getnchannels()
        total = f.getnframes()
        mapa, escrito = [], 0
        with contextlib.closing(wave.open(destino, "wb")) as g:
            g.setparams(f.getparams())
            for a, b in runs:
                i, j = int(a * sr), min(int(b * sr), total)
                if j <= i:
                    continue
                f.setpos(i)
                g.writeframes(f.readframes(j - i))
                mapa.append({"voz": escrito / sr, "cinta": a,
                             "dur": (j - i) / sr})
                escrito += j - i
    return mapa, escrito / sr, sr, anchura


def recorte(wav, a, b, destino, sr, anchura):
    """Un trozo del wav sin silencios, por muestras."""
    with contextlib.closing(wave.open(wav, "rb")) as f:
        i, j = int(a * sr), min(int(b * sr), f.getnframes())
        f.setpos(i)
        datos = f.readframes(j - i)
        with contextlib.closing(wave.open(destino, "wb")) as g:
            g.setparams(f.getparams())
            g.writeframes(datos)
    return len(datos) / anchura / sr


def pasada(wav, salida, modelo=None):
    """whisper sobre una ventana, con granularidad de palabra."""
    r = subprocess.run([os.path.join(W, "whisper-cli.exe"), "-m", modelo or MODELO, "-f", wav,
                    "-l", "es", "-mc", "0", "-ml", "1", "-sow", "-oj",
                    "-of", salida, "-np", "-nf", "-t", str(HILOS)] + VORAZ,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(salida + ".json"):
        registro.error("transcribir", "whisper salio mal",
                       detalle=f"{os.path.basename(salida)} rc={r.returncode}"
                               f" {(r.stderr or b'')[-160:].decode('utf8','replace')}")
        return []
    d = json.load(open(salida + ".json", encoding="utf-8"))
    out = []
    for w in d.get("transcription", []):
        t = w["offsets"]
        txt = w["text"].strip()
        if txt:
            out.append({"a": t["from"] / 1000.0, "b": t["to"] / 1000.0,
                        "t": txt})
    return sin_etiquetas(out)


def sin_etiquetas(ws):
    """Quita las etiquetas de sonido, que con `-ml 1` vienen partidas.

    `[Sonido de la puerta abriendo]` no llega como un token: llega como seis, y
    solo el primero abre y el ultimo cierra. Filtrar palabra a palabra dejaba
    pasar las cuatro de en medio — que es peor que no filtrar, porque el
    subtitulo sale diciendo «Sonido de la puerta» como si Jaime lo hubiera
    dicho. Trece de estas habia en el reel 1.

    Asi que se filtra por ESTADO: desde el token que abre corchete hasta el que
    cierra, todo fuera. Y se cierra sola a las ocho palabras por si el modelo
    abrio y no cerro, que si no se comeria el resto de la ventana.
    """
    out, dentro = [], 0
    for w in ws:
        t = w["t"].strip()
        if dentro:
            dentro -= 1
            if t.endswith("]") or t.endswith(")") or t.endswith("*"):
                dentro = 0
            continue
        if t.startswith("[") or t.startswith("(") or t.startswith("*"):
            # **El modelo tambien anota con asteriscos.** `*sonido de caja*`
            # entro entero en el reel 1 por la puerta que dejaba el filtro:
            # miraba corchete y parentesis y nada mas, asi que la anotacion
            # salia en el subtitulo como si Jaime la hubiera dicho. Aparecio
            # justo donde el afinado tapo un hueco, que es donde el modelo se
            # inventa cosas: no tiene habla que transcribir y rellena.
            dentro = (0 if (t.endswith("]") or t.endswith(")")
                            or (t.startswith("*") and t.endswith("*") and len(t) > 1))
                      else 8)
            continue
        out.append(w)
    return out


def sin_fantasmas(ws):
    """Quita la palabra duplicada que **no tiene audio propio que cortar**.

    El transcript sale de fundir varias pasadas y deja dos formas de duplicado
    que ninguna tijera puede arreglar, porque el problema no esta en el audio:

    - **La de duracion cero.** `Revise,` de 590.664 a 590.664, pegada a
      `revise`. `sin_tartamudeo` la detecta y corta su tramo — que mide cero
      segundos, o sea no corta nada — y la palabra sigue en el texto. El
      subtitulo dice «Revise, revise» para siempre.
    - **La que se pisa con su gemela.** `cuenta` 591.354-591.962 y `cuenta`
      591.744-593.276. Ahi el cinturon de C-64 hace bien en no cortar —es UNA
      palabra oida dos veces, y cortarla la borraria— pero se limita a no
      tocarla, y el texto sigue diciendo «cuenta cuenta».

    Las dos veces el fallo es el mismo: se trato como problema de montaje algo
    que es un defecto del transcript. Aqui se arregla donde esta, fundiendo las
    dos en una que abarca de la primera a la ultima.

    No toca la repeticion de verdad —«luego sube, luego sube» son dos tramos
    separados y con audio cada uno—: eso lo decide quien monta, no esto.
    """
    out = []
    for w in sorted(ws, key=lambda x: (x["start"], x["end"])):
        p = beats_palabras(w["text"])
        q = beats_palabras(out[-1]["text"]) if out else None
        if p and q and p[0] == q[0]:
            hueco = w["start"] - out[-1]["end"]
            cero = (w["end"] - w["start"] <= 0.001
                    or out[-1]["end"] - out[-1]["start"] <= 0.001)
            if cero or hueco < -0.01:
                # Una sola palabra, del arranque mas temprano al final mas
                # tardio: asi el corte que la use la abarca entera.
                out[-1] = dict(out[-1],
                               start=min(out[-1]["start"], w["start"]),
                               end=max(out[-1]["end"], w["end"]),
                               text=(w["text"] if len(w["text"]) >= len(out[-1]["text"])
                                     else out[-1]["text"]))
                continue
        out.append(w)
    return out


def beats_palabras(t):
    """La normalizacion de `beats`, importada tarde para no cerrar un ciclo."""
    import beats

    return beats.palabras(t)


def a_cinta(t, mapa):
    """De tiempo de voz a tiempo de cinta, por el tramo que lo contiene."""
    for m in mapa:
        if m["voz"] <= t < m["voz"] + m["dur"]:
            return m["cinta"] + (t - m["voz"])
    return mapa[-1]["cinta"] + mapa[-1]["dur"] if mapa else t


def atascado(palabras):
    """El modelo repitiendo el mismo trigrama es el modelo pegado."""
    ws = [w["t"].lower() for w in palabras]
    if len(ws) < 6:
        return False
    for n in (3, 4):
        for i in range(len(ws) - 2 * n + 1):
            if ws[i:i + n] == ws[i + n:i + 2 * n]:
                return True
    return False


def etiqueta(txt):
    """Lo que el modelo escribe ENTRE CORCHETES no es habla.

    En el reel 1 salieron trece `[Sonido de la puerta abriendo]` y en el 3 un
    `[SILENCIO]`. Es la misma familia que «Gracias por ver el video» —relleno
    aprendido de video subtitulado— pero por otra puerta: aquella se filtraba
    por su texto y esta no se filtraba en absoluto, asi que **acababa en un
    subtitulo**, que es portante.

    Se quita la palabra, no la ventana: alrededor de la etiqueta suele haber
    habla real.
    """
    return bool(re.match(r"^[\[\(].*[\]\)]$", txt.strip())
                or txt.strip() in ("[", "]", "(", ")"))


def alucinado(texto):
    t = " ".join(limpio(texto))
    return any(a.replace(".", "") in t for a in
               (" ".join(limpio(x)) for x in ALUCINACIONES))


def _recuerda(c, otra):
    """Cuánto de lo que oyó la otra pasada está también en ésta."""
    b = limpio(otra["texto"])
    if not b:
        return 1.0
    a = limpio(c["texto"])
    sm = difflib.SequenceMatcher(None, a, b)
    return sum(bl.size for bl in sm.get_matching_blocks()) / len(b)


def medoide(cands):
    """La que recoge lo que oyeron las demás, sin inventar lo que nadie oyó.

    El parecido simétrico —`ratio()`— no sirve aquí y costó una palabra real:
    entre «porque le duele una muela no» y «porque le duele no» las dos se
    parecen lo mismo la una a la otra, así que el desempate lo decidía la
    distancia al borde y ganó la que se comió «una muela».

    Lo que de verdad distingue una pasada buena de una que se comió algo es
    **asimétrico**: una palabra que oyeron las otras y ésta no es una palabra
    comida; una que sólo oyó ésta es una palabra inventada. Así que se puntúa
    con las dos cosas —lo que recoge de las demás, menos lo que no confirma
    ninguna—, que es exactamente para lo que sirven varias pasadas.

    Los bucles ya no llegan aquí: `atascado()` y `alucinado()` los tiraron antes.
    """
    if len(cands) == 1:
        # **Con una sola pasada no hay acuerdo: hay ausencia de discrepancia.**
        # Devolver 1,0 hacia que el barrido barato —una pasada— saliera con
        # «0 tramos por oir» y acuerdo perfecto, o sea que el peldaño menos
        # fiable se presentaba como el mas fiable. `None` dice lo que hay: no
        # se ha podido comprobar.
        return cands[0], None
    mejor, mejor_p, acuerdo = None, -1e9, 0.0
    for c in cands:
        otras = [o for o in cands if o is not c]
        recoge = sum(_recuerda(c, o) for o in otras) / len(otras)
        # Palabras que no confirma ninguna otra pasada: invencion del modelo.
        mias = set(limpio(c["texto"]))
        suyas = set()
        for o in otras:
            suyas |= set(limpio(o["texto"]))
        sola = len(mias - suyas) / max(1, len(mias))
        p = recoge - 0.35 * sola - 0.10 * c["borde"]
        if p > mejor_p:
            mejor, mejor_p, acuerdo = c, p, recoge
    return mejor, round(acuerdo, 3)


def transcribir(toma, runs, verbose=True, modelo=None, paso=None):
    tmp = rutas.temporal("tr", toma)

    voz_wav = os.path.join(tmp, "voz.wav")
    mapa, dur, sr, anchura = sin_silencios(audio(toma), runs, voz_wav)
    if verbose:
        print(f"  {dur:.0f}s de voz en {len(runs)} tramos "
              f"→ {int(dur // PASO) + 1} ventanas de {VENTANA:.0f}s")

    salto = paso or PASO
    ventanas = []
    t = 0.0
    while t < dur:
        a, b = t, min(t + VENTANA, dur)
        if b - a < 2.5 and ventanas:      # una cola corta miente; va a la anterior
            ventanas[-1] = (ventanas[-1][0], b)
            break
        ventanas.append((a, b))
        t += salto

    salidas = []
    for k, (a, b) in enumerate(ventanas):
        trozo = os.path.join(tmp, f"v{k:03d}.wav")
        recorte(voz_wav, a, b, trozo, sr, anchura)
        ws = pasada(trozo, os.path.join(tmp, f"v{k:03d}"), modelo)
        for w in ws:
            w["a"] += a
            w["b"] += a
        salidas.append({"a": a, "b": b, "ws": ws})
        if not ws:
            # Una ventana de 30 s de voz sin una palabra no es silencio: es que
            # el modelo no dijo nada. Aprendizaje 18 — devolver vacio es «no se».
            registro.error("transcribir", "ventana sin palabras", toma=toma,
                           detalle=f"{a:.1f}-{b:.1f}s")
        if verbose:
            print(f"    ventana {k + 1}/{len(ventanas)}  "
                  f"{a:6.1f}-{b:6.1f}s  {len(ws)} palabras", flush=True)

    # ── consolidar por tramo ────────────────────────────────────────────────
    finales, dudosos = [], 0
    for m in mapa:
        a, b = m["voz"], m["voz"] + m["dur"]
        cands = []
        for v in salidas:
            if v["a"] > a or v["b"] < b:
                continue                       # la ventana no lo contiene entero
            dentro = [w for w in v["ws"] if a <= (w["a"] + w["b"]) / 2 < b]
            if not dentro:
                continue
            texto = " ".join(w["t"] for w in dentro)
            if alucinado(texto):
                registro.aviso("transcribir", "alucinacion descartada", toma=toma,
                               detalle=f"{a:.2f}s «{texto[:70]}»", eco=False)
                continue
            if atascado(dentro):
                registro.aviso("transcribir", "modelo atascado", toma=toma,
                               detalle=f"{a:.2f}s «{texto[:70]}»", eco=False)
                continue
            borde = 1.0 if (a - v["a"] < BORDE or v["b"] - b < BORDE) else 0.0
            cands.append({"texto": texto, "ws": dentro, "borde": borde,
                          "ventana": [v["a"], v["b"]]})
        if not cands:
            registro.aviso("transcribir", "tramo sin candidata", toma=toma,
                           detalle=f"{m['cinta']:.2f}-{m['cinta'] + m['dur']:.2f}s"
                                   f" ({m['dur']:.1f}s de voz)", eco=False)
            continue
        elegido, acuerdo = medoide(cands)
        if acuerdo is not None and acuerdo < 0.6:
            dudosos += 1
            registro.aviso("transcribir", "pasadas en desacuerdo", toma=toma,
                           detalle=f"{m['cinta']:.2f}s acuerdo {acuerdo:.2f} ·"
                                   f" «{elegido['texto'][:70]}»", eco=False)
        for w in elegido["ws"]:
            ini = a_cinta(w["a"], mapa)
            fin = a_cinta(min(w["b"], b - 0.001), mapa)
            finales.append({
                "start": round(ini, 3), "end": round(max(ini, fin), 3),
                "text": w["t"],
                "larga": int(fin - ini > LARGA),
            })
        m["texto"] = elegido["texto"]
        m["acuerdo"] = acuerdo
        m["pasadas"] = len(cands)

    finales.sort(key=lambda w: w["start"])
    return finales, mapa, dudosos


# La marca que separa un transcript de varias pasadas de uno de una sola. No es
# decorativa: `exigir()` la comprueba y **sin ella el montaje para**.
SELLO = "pasadas"


def exigir(toma, preciso=False):
    """El transcript de varias pasadas, o no se sigue.

    La guarda estructural del paso 1. Antes cualquier script leia
    `work/transcripts/<toma>.json` sin preguntar de donde venia, y venia de una
    sola pasada de whisper: de ahi las frases de 98 s y la seleccion que se
    quedaba con lo primero. Ahora el fichero **declara como se hizo** y el que
    no lo declara se rechaza — no se avisa, se para.
    """
    receta = "  ->  python scripts/transcribir.py --toma <N>"
    ruta = f"work/transcripts/{toma}.json"
    if not os.path.exists(ruta):
        raise SystemExit(
            f"falta {ruta}. Los subtitulos van PRIMERO." + receta)
    d = json.load(open(ruta, encoding="utf-8"))
    if SELLO not in d:
        raise SystemExit(
            f"{ruta} es de UNA pasada de whisper y no sirve: se come frases,"
            f" se queda pegado y no puntua." + receta)
    if preciso and d.get("modelo") not in (None, "medium", "large-v3"):
        raise SystemExit(
            f"{ruta} se hizo con el modelo «{d.get('modelo')}», que sirve para"
            f" localizar pero no para el subtitulo." + receta)
    cortes = f"work/cuts/{toma}.json"
    if os.path.exists(cortes) and os.path.getmtime(cortes) > os.path.getmtime(ruta):
        raise SystemExit(
            f"{ruta} es mas viejo que {cortes}: los tramos cambiaron despues"
            f" de transcribir." + receta)
    return d


def guardar(toma, palabras, mapa, dudosos, modelo=None, paso=None):
    """Escribe EL transcript, no uno paralelo.

    Dos ficheros describiendo la misma cinta es el aprendizaje 33, y ya costo
    cuatro fallos: se corrige uno y el otro sigue diciendo lo de antes. Asi que
    esto sustituye a `work/transcripts/<toma>.json` en vez de convivir con el.
    """
    os.makedirs("work/transcripts", exist_ok=True)
    ruta = f"work/transcripts/{toma}.json"
    con_texto = [m for m in mapa if m.get("texto")]
    # **El sello dice lo que se hizo, no lo que dice la constante.** Guardaba
    # `PASO` del modulo mientras la corrida usaba otro: con `--pasadas 4` el
    # paso real es 7,5 y el fichero declaraba 10. Un sello que miente sobre su
    # procedencia hace imposible comparar dos corridas, que es exactamente para
    # lo que existe.
    json.dump({"toma": toma, "ventana": VENTANA, "paso": paso or PASO,
               "modelo": os.path.basename(modelo or MODELO).replace("ggml-", "").replace(".bin", ""),
               SELLO: len(con_texto) and round(
                   sum(m["pasadas"] for m in con_texto) / len(con_texto), 2),
               "dudosos": dudosos,
               "segmentos": sin_fantasmas(palabras),
               "tramos": con_texto},
              open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # El fichero ya esta escrito arriba. Lo que sigue es la base, y **un fallo
    # ahi no puede tirar quince minutos de transcripcion**: se avisa y se sigue.
    # Paso de verdad: `subtitulo.acuerdo` era NOT NULL de una version anterior y
    # `CREATE TABLE IF NOT EXISTS` no altera lo que ya existe, asi que al
    # empezar a guardar «acuerdo desconocido» reventaba el guardado entero.
    try:
        _guardar_en_base(toma, mapa)
    except Exception as e:                        # noqa: BLE001
        registro.error("transcribir", "no se pudo guardar en la base",
                       toma=toma, detalle=str(e)[:160])
    return ruta


def _guardar_en_base(toma, mapa):
    con = sqlite3.connect(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
      CREATE TABLE IF NOT EXISTS subtitulo (
        toma_id INTEGER NOT NULL REFERENCES toma(id) ON DELETE CASCADE,
        desde   REAL NOT NULL,
        hasta   REAL NOT NULL,
        texto   TEXT NOT NULL,
        acuerdo REAL,
        pasadas INTEGER NOT NULL,
        PRIMARY KEY (toma_id, desde)
      );
    """)
    fila = con.execute("select id from toma where nombre = ?", (toma,)).fetchone()
    toma_id = fila[0] if fila else con.execute(
        "insert into toma (nombre) values (?)", (toma,)).lastrowid
    con.execute("delete from subtitulo where toma_id = ?", (toma_id,))
    con.executemany(
        "insert into subtitulo (toma_id, desde, hasta, texto, acuerdo, pasadas)"
        " values (?,?,?,?,?,?)",
        [(toma_id, round(m["cinta"], 3), round(m["cinta"] + m["dur"], 3),
          m["texto"], m["acuerdo"], m["pasadas"])
         for m in mapa if m.get("texto")])
    con.commit()
    con.close()


def _saneado(toma, d):
    """Pasa por el transcript ya escrito los filtros que no existian al hacerlo.

    **Un arreglo que solo vale para las cintas futuras no arregla nada**: las
    siete de este proyecto costaron horas de CPU y no se van a rehacer porque
    el filtro de etiquetas creciera. Asi que se aplica al pasar, que es cuando
    el paso ya tiene el fichero delante, y se reescribe solo si cambio algo.

    Es la misma idea que la cobertura de C-89: el paso comprueba el resultado
    que tiene, no el trabajo que recuerda haber hecho.
    """
    ws = d.get("segmentos") or []
    # `sin_etiquetas` habla en el idioma de la transcripcion —`t`— y el fichero
    # guarda `text`; se traduce en los dos sentidos en vez de duplicar la regla.
    puente = [{"t": w["text"], "_w": w} for w in ws]
    limpias = [x["_w"] for x in sin_etiquetas(puente)]
    limpias = sin_fantasmas(limpias)
    if len(limpias) == len(ws):
        return d, 0
    quitadas = len(ws) - len(limpias)
    d["segmentos"] = limpias
    json.dump(d, open(f"work/transcripts/{toma}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return d, quitadas


class Incompleta(Exception):
    """La cinta tiene habla sin texto y afinarla no la tapo.

    **Tiene que ser una excepcion propia.** El bucle usa `SystemExit` para otra
    cosa —`exigir()` la lanza cuando la cinta aun no esta sellada, y ahi
    significa «hazla»— y la caza con un `except SystemExit: pass`. Si el aviso
    viajara por esa via, el paso lo entenderia como «rehazla entera»: media hora
    de CPU para repetir el barrido que ya dejo esos tramos vacios.
    """


def _sin_cubrir(toma, d):
    """Cuantos segundos de habla medida se quedaron sin una sola palabra.

    Los tramos de `work/cuts/<toma>.json` los midio el detector de silencio
    sobre el audio: dicen donde hay voz. Si en uno de esos tramos el transcript
    no tiene ninguna palabra, ahi falta texto — y el paso no puede decir «ya
    esta».
    """
    import json as _js

    try:
        runs = _js.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
    except Exception:                              # noqa: BLE001
        return 0.0
    return sum(b0 - a0 for a0, b0 in _huecos(toma, d))


def _huecos(toma, d, minimo=1.0):
    """**Donde** falta el texto, no solo cuanto. Tramos de voz sin palabra.

    `_sin_cubrir` daba un numero y con un numero solo se puede hacer una cosa:
    rehacer la cinta entera. Eso costo media hora de CPU en el reel 1 y dejo
    43 de los 102 segundos igual, porque el barrido vuelve a usar las mismas
    ventanas que ya fallaron. Los tramos, en cambio, se pueden afinar uno a
    uno con contexto mas ancho, que es para lo que existe `afinar`.
    """
    import json as _js

    try:
        runs = _js.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
    except Exception:                              # noqa: BLE001
        return []
    ws = d.get("segmentos") or []
    hue = [(a0, b0) for a0, b0 in runs
           if b0 - a0 >= minimo and not any(a0 <= w["start"] < b0 for w in ws)]
    # **Lo que ya se oyo y se descarto no vuelve a parar el paso.** Sin esto la
    # linea se planta igual en cada corrida y la lectura hay que rehacerla de
    # memoria; con esto la decision esta escrita y se puede discutir. Solo callan
    # los tramos declarados uno a uno: un agujero nuevo sigue parando.
    try:
        c = sqlite3.connect(BASE)
        ya = c.execute("select desde, hasta from hueco_oido"
                       " where toma = ? and veredicto = 'descartado'",
                       (toma,)).fetchall()
        c.close()
    except Exception:                              # noqa: BLE001
        return hue
    return [(a0, b0) for a0, b0 in hue
            if not any(abs(a0 - d0) < 0.3 and abs(b0 - h0) < 0.3 for d0, h0 in ya)]


def suena(w, a, b):
    """¿Esta palabra se oye dentro del corte `[a, b]`?

    **La vara es la del oido, no la del filtro.** Exigir la palabra entera
    dentro del rango se come una en cada borde de cada segmento: en reel-06 e5
    «estructura» acababa 51 milesimas despues del corte y el texto del montaje
    decia «que facture 180 mil sin puede estar perdiendo» (C-84). El espectador
    oye lo que suena, asi que la palabra esta si **mas de la mitad** de su
    duracion cae dentro.

    Vive aqui porque aqui viven las palabras: lo tenian copiado `Pieza.texto` y
    las dos extracciones de `revalidar.py`, y una regla de medida repetida en
    tres sitios son tres reglas en cuanto alguien toca una.
    """
    dur = w["end"] - w["start"]
    if dur <= 0:
        # **La palabra sin duracion existe y se oye.** Whisper devuelve marcas
        # iguales cuando dos palabras caen en el mismo frame: hay 207 en las
        # siete cintas. Con `> dur/2` ninguna pasaba —`0 > 0` es falso— y se
        # perdian palabras portantes: reel-01 e3 se quedaba sin «Pongamoslo» y
        # reel-06 e2 sin «mes». Para ella la vara es estar dentro.
        return a <= w["start"] <= b
    return (min(b, w["end"]) - max(a, w["start"])) > dur / 2


def afinar(toma, tramos, pasadas=4):
    """JUBILADO para la via normal. Re-transcribe SOLO esos tramos.

    **Este es el camino de salvamento y es donde vivieron los fallos.** Jaime lo
    diagnostico: *«estos problemas surgen por intentar salvar lo que habia antes
    en lugar de desarrollar de nuevo el proceso limpio»*. De los cinco fallos de
    esa sesion, cuatro salieron de conservar lo anterior, y tres de ellos de
    aqui: la costura duplicando palabras (C-64), el acuerdo desconocido
    reventando el formateo, y la media sobre valores que ya podian ser nulos.

    El proceso canonico es **una sola corrida con `--pasadas 4`**: cuesta 1,6x y
    no tiene fusion, que es lo unico que esta funcion anade. Se conserva porque
    el peldaño barato del embudo si la necesita —catalogar con `small` y afinar
    con `medium` solo lo preseleccionado (C-59)—, y ahi la fusion se justifica
    porque lo que cambia es el MODELO, no el numero de pasadas.

    Regla: **no se usa para arreglar una corrida floja. Se rehace la corrida.**

    Es el peldano que sube la robustez sin pagarla en toda la cinta. Jaime:
    *«utilizamos los recursos caros y pesados solo en lo que ya sabemos que va a
    funcionar, y vamos incrementando robustez conforme el funnel avanza»*.

    Medido sobre el reel 6: el barrido barato —`small`, una pasada— cuesta 60 s
    frente a los ~7 min del bueno, y **acierta el sitio en 7 de 9 etapas**. Las
    otras dos caen en otro lado. O sea sirve para **preseleccionar y no para
    elegir**, y esta funcion es la que convierte esa lista corta en una
    decision: se vuelve a oir con `medium` solo lo preseleccionado.

    El resultado se **funde** en el transcript: las palabras del tramo afinado
    sustituyen a las que habia, y el resto queda igual. Asi no hay dos ficheros
    describiendo la misma cinta (aprendizaje 33).
    """
    ruta = f"work/transcripts/{toma}.json"
    d = json.load(open(ruta, encoding="utf-8"))
    runs = json.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
    tmp = rutas.temporal("afinar", toma)
    voz_wav = os.path.join(tmp, "voz.wav")
    mapa, dur, sr, anchura = sin_silencios(audio(toma), runs, voz_wav)

    # De tiempo de cinta a tiempo de voz, que es donde vive el wav recortado.
    def a_voz(t):
        """De cinta a voz, **pegandose al tramo mas cercano si cae en el hueco**.

        Los extremos que llegan aqui vienen de `recortar()`, que resta 0,06 s
        para no comerse el ataque de la palabra — y con eso el instante cae en
        el silencio de antes del tramo. Devolver `None` ahi hacia que el tramo
        no se afinara y el aviso decia «sin voz», que es verdad y no es el
        problema.
        """
        for m in mapa:
            if m["cinta"] <= t < m["cinta"] + m["dur"]:
                return m["voz"] + (t - m["cinta"])
        cerca = min(mapa, key=lambda m: min(abs(m["cinta"] - t),
                                            abs(m["cinta"] + m["dur"] - t)),
                    default=None)
        if cerca and min(abs(cerca["cinta"] - t),
                         abs(cerca["cinta"] + cerca["dur"] - t)) < 1.5:
            return (cerca["voz"] if t < cerca["cinta"]
                    else cerca["voz"] + cerca["dur"])
        return None

    def al_tramo(a, b):
        """Estira el rango hasta las fronteras de los tramos que toca.

        Es lo que hace imposible la costura: se sustituye desde el arranque de
        un tramo hasta el final de otro, y entre medias no hay palabra partida
        porque ahi el detector midio silencio.
        """
        toca = [(x, y) for x, y in runs if y > a and x < b]
        if not toca:
            return None
        return min(x for x, _ in toca), max(y for _, y in toca)

    redondeados = []
    for a, b in tramos:
        r = al_tramo(a, b)
        if not r:
            registro.aviso("transcribir", "tramo a afinar sin voz",
                           toma=toma, detalle=f"{a:.2f}-{b:.2f}", eco=False)
            continue
        if redondeados and r[0] <= redondeados[-1][1] + 0.01:
            redondeados[-1] = (redondeados[-1][0], max(redondeados[-1][1], r[1]))
        else:
            redondeados.append(r)
    tramos = redondeados

    # **Solo se quita lo viejo de los tramos que SI dieron texto.** Si una
    # pasada no devuelve nada —whisper calla, la ventana sale alucinada, el
    # tramo no tiene voz— y aun asi se borran las palabras de antes, queda un
    # hueco: la cinta pierde ese trozo y todo lo que dependa de el se queda sin
    # texto. Medido: `20260825_135637` con seis huecos, y ocho de los once
    # trozos del reel-01 sin una sola palabra.
    # `hechos` son los tramos cuyas palabras se SUSTITUYEN; `oidos`, todos los
    # que pasaron por el modelo bueno — incluidos aquellos en los que se decidio
    # quedarse con lo viejo. Son cosas distintas y hacen falta las dos: lo
    # primero manda el borrado, lo segundo es lo que la puerta pregunta.
    hechos, oidos, nuevas, tocados = [], [], [], 0
    for a, b in tramos:
        va, vb = a_voz(a), a_voz(max(a, b - 0.01))
        if va is None or vb is None:
            registro.aviso("transcribir", "tramo a afinar sin voz",
                           toma=toma, detalle=f"{a:.2f}-{b:.2f}", eco=False)
            continue
        # Ventana centrada y con contexto: por debajo del suelo whisper calla.
        centro = (va + vb) / 2
        ancho = max(VENTANA, (vb - va) + 8.0)
        cands = []
        for k in range(pasadas):
            desp = (k - (pasadas - 1) / 2) * (ancho / (pasadas + 1))
            w0 = max(0.0, min(dur - ancho, centro - ancho / 2 + desp))
            trozo = os.path.join(tmp, f"a{k:02d}.wav")
            recorte(voz_wav, w0, min(w0 + ancho, dur), trozo, sr, anchura)
            ws = pasada(trozo, os.path.join(tmp, f"a{k:02d}"), MODELOS["bueno"])
            dentro = [w for w in ws
                      if va <= w["a"] + w0 + (w["b"] - w["a"]) / 2 < vb]
            for w in dentro:
                w["a"] += w0
                w["b"] += w0
            txt = " ".join(w["t"] for w in dentro)
            if dentro and not alucinado(txt) and not atascado(dentro):
                cands.append({"texto": txt, "ws": dentro, "borde": 0.0})
        if not cands:
            # **Y no se calla.** Este `continue` era la unica salida muda del
            # afinado: si las cuatro pasadas salian vacias, alucinadas o
            # atascadas, la funcion devolvia «0 afinados» sin decir de que
            # tramo ni por que. Eso bloquea la linea entera, porque la puerta
            # de composicion exige el CC afinado y no hay forma de saber que
            # falta: paso con el remate del reel-01 traido de otra cinta.
            registro.aviso("transcribir", "ningun candidato sobrevivio",
                           toma=toma,
                           detalle=f"{a:.2f}-{b:.2f}: {pasadas} pasadas, todas"
                                   f" vacias, alucinadas o atascadas", eco=True)
            continue
        elegido, acuerdo = medoide(cands)
        # **Y no se acepta si trae menos de lo que se va a llevar.**
        #
        # `afinar` sustituye el tramo entero: borra lo viejo que lo toca y pone
        # lo nuevo. Si la pasada nueva oye menos —pasa, y pasa justo en los
        # tramos dificiles, que son los que se mandan a afinar— la cinta pierde
        # palabras a cambio de nada y nadie se entera, porque el paso informa de
        # los tramos que hizo, no de las palabras que quedaron.
        #
        # Es la misma familia que C-89: medir el resultado y no el esfuerzo. Y
        # aqui la cuenta es trivial, que es lo que la hace imperdonable.
        viejas = [w for w in d["segmentos"]
                  if w["end"] > a + 0.001 and w["start"] < b - 0.001]
        if len(elegido["ws"]) < len(viejas):
            registro.aviso("transcribir", "afinado que resta: se queda lo viejo",
                           toma=toma,
                           detalle=f"{a:.2f}-{b:.2f}: {len(viejas)} palabras ->"
                                   f" {len(elegido['ws'])}", eco=False)
            # **Pero el tramo queda oido.** Se paso por el modelo bueno y la
            # decision fue conservar lo que habia, que es un resultado del
            # afinado y no una ausencia de el. Sin esto la puerta de
            # composicion pedia el barrido caro, el barrido se negaba a empeorar
            # el texto, y la pieza se quedaba trabada entre las dos — le paso al
            # remate del reel-01 traido de otra cinta.
            oidos.append((a, b))
            continue
        for w in elegido["ws"]:
            ini = a_cinta(w["a"], mapa)
            fin = a_cinta(min(w["b"], vb - 0.001), mapa)
            nuevas.append({"start": round(ini, 3), "end": round(max(ini, fin), 3),
                           "text": w["t"], "larga": int(fin - ini > LARGA)})
        hechos.append((a, b))
        tocados += 1
        # `acuerdo` es None cuando solo sobrevivio una pasada: con una no hay
        # acuerdo, hay ausencia de discrepancia. Formatearlo como numero
        # reventaba el afinado entero — y justo despues de arreglar que dejara
        # de mentir con un 1,00.
        registro.nota("transcribir", "tramo afinado", toma=toma,
                      detalle=f"{a:.2f}-{b:.2f} acuerdo "
                              f"{'sin medir' if acuerdo is None else f'{acuerdo:.2f}'}"
                              f" ({len(cands)} pasadas)")

    if not nuevas:
        if oidos:
            d["afinado"] = sorted(set(
                [tuple(x) for x in d.get("afinado", [])] + oidos))
            json.dump(d, open(ruta, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
        return d, 0
    # **La costura duplica si no se corta por los dos lados.** Se quitaban las
    # palabras viejas cuyo CENTRO caia dentro del tramo, pero las nuevas se
    # salen un poco por el borde: al fundir quedaba «odontologo odontologo
    # odontologo» y «El contador es como es como el medico». Una palabra
    # duplicada aqui es un subtitulo duplicado despues.
    #
    # Asi que se quita lo viejo que **toca** el tramo —no solo lo que esta
    # centrado dentro— y se recorta lo nuevo a los limites del tramo.
    # **La costura no se arregla: se elimina.** Pregunta de Jaime, y es la
    # correcta: *«si lo haces desde el comienzo es mas solido o mas fragil? Si
    # es igual de fragil, entonces hay que corregir el problema»*.
    #
    # Los dos fallos de este camino —duplicar palabras al fundir (C-64), y el
    # acuerdo desconocido reventando el formateo— salian de lo mismo: unir dos
    # transcripciones de audio que se solapa. Parchear el borde es tapar el
    # sintoma; el arreglo es que **no haya borde que unir**.
    #
    # Lo consigue el tramo: su frontera es **silencio medido** por el detector,
    # no mitad de palabra. Si el afinado sustituye tramos ENTEROS, lo viejo y lo
    # nuevo nunca comparten una palabra y el solape deja de existir. Por eso
    # `afinar` redondea lo que le piden al tramo que lo contiene antes de nada.
    # **Tramo a tramo, nunca del primero al ultimo.** Esto tomaba el minimo y el
    # maximo de TODOS los tramos y borraba lo que hubiera en medio: afinar el
    # segundo 87 y el 590 de una cinta se llevaba por delante los 503 segundos
    # intermedios. Medido: la cinta 135637 paso de 935 palabras a 342, y en el
    # hueco 408-519 vivian las ocho tomas alternativas del bootcamp — o sea el
    # abanico entero donde hay que elegir, que es la materia prima del paso
    # siguiente. El sintoma es cruel: la pieza montada se ve perfecta, porque
    # sus tramos SI estan; lo que desaparece es todo lo que no se uso.
    def _toca(w):
        return any(w["end"] > x + 0.001 and w["start"] < y - 0.001
                   for x, y in hechos)

    fuera = [w for w in d["segmentos"] if not _toca(w)]
    d["segmentos"] = sin_fantasmas(fuera + nuevas)
    d["afinado"] = sorted(set(tuple(t) for t in
                              [tuple(x) for x in d.get("afinado", [])] +
                              [tuple(t) for t in hechos] + oidos))
    json.dump(d, open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d, tocados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toma", type=int, help="sólo el reel N")
    ap.add_argument("--todas", action="store_true", help="incluye reel-03-alt")
    ap.add_argument("--pasadas", type=int, default=None,
                    help="cuantas veces se oye cada tramo; el paso sale de"
                         " dividir la ventana entre esto")
    ap.add_argument("--dudosos", action="store_true",
                    help="[salvamento] re-oye los tramos donde discreparon."
                         " Lo normal es rehacer la toma con --pasadas 4")
    ap.add_argument("--suelo", type=float, default=0.6,
                    help="por debajo de este acuerdo se considera dudoso")
    ap.add_argument("--afinar", nargs="+", metavar="A-B",
                    help="re-transcribe solo esos tramos con el modelo bueno")
    ap.add_argument("--elegidos", type=int, metavar="N",
                    help="afina SOLO los tramos que el EDL del reel N eligio")
    ap.add_argument("--barato", action="store_true",
                    help="modelo pequeno y una sola pasada: para catalogar")
    ap.add_argument("--rehacer", action="store_true",
                    help="vuelve a transcribir aunque ya este sellada")
    a = ap.parse_args()

    if a.toma:
        tomas = [rutas.TOMAS[f"reel-{a.toma:02d}"]]
    else:
        # **El catalogo es del MATERIAL, no de las piezas.** Antes esto recorria
        # los seis reels y la cinta `20260825_231011` —4,6 GB— solo entraba con
        # `--todas`, que ningun paso pasaba: llevaba desde el principio con su
        # audio y sus silencios hechos y **sin una sola palabra transcrita**.
        #
        # Y no es que sobrara una cinta: es que **lo que no se transcribe no
        # existe para nadie**. El corte cruza cintas —una etapa del reel 1 sale
        # de la cinta del 3— y la busqueda por el corpus decide si una frase que
        # falta se puede recuperar o hay que mandarla a tablero. Con una cinta
        # fuera, esa busqueda contesta «no esta en ninguna» sin haber mirado.
        #
        # Asi que se transcribe todo lo que hay en `rutas.TOMAS`, tenga libreto
        # o no. Una cinta sin guion no es una cinta sin valor: es material.
        # El corpus se descubre mirando la carpeta, no se declara.
        tomas = rutas.material()

    if a.dudosos:
        # **Corregir donde el primer paso dijo que no se fiaba.** Jaime: *«si no
        # hubo el primer paso, dificilmente podras encontrar los demas; el
        # primer paso es clave para confirmar o negar los videos y sobre este es
        # que tenemos que corregir»*. Los tramos con acuerdo bajo ya estan
        # marcados por el propio barrido: aqui se vuelven a oir con mas pasadas.
        import sqlite3
        toma = tomas[0]
        con = sqlite3.connect(BASE)
        tr = [(d, h) for d, h in con.execute(
            "select s.desde, s.hasta from subtitulo s join toma t on t.id = s.toma_id"
            " where t.nombre = ? and s.acuerdo is not null and s.acuerdo < ?"
            " order by s.acuerdo", (toma, a.suelo))]
        con.close()
        # Se funden los que casi se tocan: afinar dos veces lo mismo es pagarlo
        # dos veces, y ademas una ventana mas ancha da mejor contexto.
        tr.sort()
        j = []
        for d, h in tr:
            if j and d - j[-1][1] < 2.0:
                j[-1] = (j[-1][0], h)
            else:
                j.append((d, h))
        print(f"{toma}: {len(tr)} tramos dudosos -> {len(j)} ventanas a afinar")
        d2, n = afinar(toma, j)
        print(f"  {n}/{len(j)} afinados -> {len(d2['segmentos'])} palabras")
        return

    if a.elegidos:
        """El caro, y solo donde se va a usar.

        Regla de Jaime, y la precisó él mismo despues: *«la revision cara no es
        para identificar redundancia, es para obtener los scripts ajustados a la
        realidad; la redundancia necesita criterio editorial»*.

        O sea que lo que este paso aporta es **fidelidad**: saber qué se dijo
        exactamente, palabra por palabra, en los tramos que se van a usar. Nada
        más. Quitar la repeticion es un juicio —cuál de las tres versiones
        comunica más— y eso vive en `redundancia.prompt.md`.

        Confundir las dos cosas lleva a esperar que una transcripcion mejor
        resuelva un problema editorial, y no lo hace: deja el mismo texto
        repetido tres veces, sólo que bien escrito.

        Antes se pagaban cuatro pasadas sobre la cinta entera —media hora larga
        por cinta— para acabar usando dos minutos de ella. Ahora el barato dice
        que hay y donde, la seleccion elige, y **el caro entra solo en los
        tramos elegidos**: que es donde hace falta precision de palabra, porque
        es donde `depurar.py` tiene que ver la repeticion para quitarla.
        """
        slug = f"reel-{a.elegidos:02d}"
        edl = json.load(open(f"ads/{slug}/edl-sell.json", encoding="utf-8"))
        por_toma = {}
        for rango, det in zip(edl["segmentos"], edl["detalle"]):
            t = det.get("toma") or rutas.TOMAS[slug]
            # Un margen a cada lado: la redundancia suele empezar justo antes
            # del corte, y afinar solo lo de dentro no la deja ver.
            por_toma.setdefault(t, []).append(
                (max(0.0, rango[0] - 1.5), rango[1] + 1.5))
        total = 0
        for t, tramos in por_toma.items():
            d, n = afinar(t, tramos)
            total += n
            print(f"  {t}: {n}/{len(tramos)} tramos elegidos afinados"
                  f" -> {len(d['segmentos'])} palabras")
        print(f"{slug}: {total} tramos afinados con el modelo bueno")
        return

    if a.afinar:
        toma = tomas[0]
        tr = [tuple(float(x) for x in t.split("-")) for t in a.afinar]
        d, n = afinar(toma, tr)
        print(f"{toma}: {n}/{len(tr)} tramos afinados con el modelo bueno"
              f" -> {len(d['segmentos'])} palabras")
        return

    for toma in tomas:
        # **Lo ya transcrito no se repite.** Cada toma cuesta media hora larga de
        # CPU, asi que rehacer una que ya esta sellada y al dia es tirar el rato.
        # `exigir()` es quien sabe si vale: sello puesto y no mas vieja que los
        # tramos. Con --rehacer se fuerza.
        if not a.rehacer:
            try:
                transcribir_ya = exigir(toma)
                # **Sellada no es lo mismo que entera.** El sello dice cuantas
                # pasadas se hicieron, no si la cinta tiene agujeros; y una
                # cinta con agujeros deja sin texto a las etapas que caen ahi
                # —ocho de los once trozos del reel 1— mientras el paso repite
                # «ya esta». Se mira tambien la cobertura contra los tramos de
                # habla medidos, que es lo que dice cuanto deberia haber.
                transcribir_ya, quitadas = _saneado(toma, transcribir_ya)
                if quitadas:
                    print(f"── {toma} ── saneado: {quitadas} palabra(s)"
                          f" fantasma o de etiqueta fuera")
                falta = _sin_cubrir(toma, transcribir_ya)
                if falta > 20.0:
                    # **Se tapa el agujero donde esta.** Los tramos huerfanos
                    # se vuelven a oir con el modelo bueno y una ventana mas
                    # ancha; rehacer la cinta entera es caro y repite el mismo
                    # barrido que ya los dejo vacios.
                    hue = _huecos(toma, transcribir_ya)
                    print(f"── {toma} ── sellada pero con {falta:.0f}s de habla"
                          f" sin texto en {len(hue)} tramos: se afinan")
                    j = []
                    for d0, h0 in sorted(hue):
                        if j and d0 - j[-1][1] < 2.0:
                            j[-1] = (j[-1][0], h0)
                        else:
                            j.append((d0, h0))
                    transcribir_ya, n = afinar(toma, j)
                    falta = _sin_cubrir(toma, transcribir_ya)
                    print(f"   {n}/{len(j)} afinados → quedan {falta:.0f}s"
                          f" sin texto")
                    # **Y si sigue faltando, para y avisa.** Regla de Jaime:
                    # *«si algo no funciona a la primera, paras y que genere
                    # error»*. Un tramo que no suelta texto tras afinarlo o no
                    # es habla o no se entiende, y las dos cosas las decide
                    # quien monta — no un umbral.
                    if falta > 20.0:
                        for d0, h0 in _huecos(toma, transcribir_ya)[:10]:
                            print(f"   sin texto: {d0:.1f}-{h0:.1f}s")
                        raise Incompleta(
                            f"{toma}: {falta:.0f}s de habla sin texto tras"
                            f" afinar. Oye esos tramos y decide: o se rehace"
                            f" la cinta (--rehacer) o no son habla.")
                print(f"── {toma} ── ya esta ({transcribir_ya['pasadas']} pasadas"
                      f" por tramo, {len(transcribir_ya['segmentos'])} palabras)")
                continue
            except SystemExit:
                pass
        runs = json.load(open(f"work/cuts/{toma}.json",
                              encoding="utf-8"))["segmentos"]
        print(f"── {toma} ──")
        modelo = MODELOS["barato" if a.barato else "bueno"]
        # **Un solo camino.** Jaime, tras ver que los dos fallos de la sesion
        # salian del afinado y no del barrido: *«prefiero que los hagas desde el
        # principio con el proceso nuevo y compares al final»*, y *«no podemos
        # estar todo el tiempo revisando a que algo quede»*. Mas pasadas de una
        # vez cuesta 1,6x y **quita el merge entero**, que es donde vivia la
        # fragilidad.
        paso = (VENTANA if a.barato
                else (VENTANA / a.pasadas if a.pasadas else None))
        palabras, mapa, dudosos = transcribir(
            toma, runs, modelo=modelo, paso=paso)
        ruta = guardar(toma, palabras, mapa, dudosos, modelo, paso)
        con_texto = [m for m in mapa if m.get("texto")]
        largas = sum(w["larga"] for w in palabras)
        # Solo promedian los que TIENEN acuerdo: un tramo que cayo en una sola
        # ventana no tiene con que compararse, y meterlo como 0 o como 1 son las
        # dos formas de mentir. Es el tercer sitio donde hacer representable el
        # «desconocido» rompio algo que asumia un numero — los otros dos fueron
        # el formateo y el NOT NULL de la tabla.
        medidos = [m["acuerdo"] for m in con_texto if m.get("acuerdo") is not None]
        acuerdo = (sum(medidos) / len(medidos)) if medidos else 0.0
        registro.nota("transcribir", "toma transcrita", toma=toma,
                      detalle=f"{len(palabras)} palabras, {len(con_texto)}/{len(runs)}"
                              f" tramos, acuerdo {acuerdo:.2f}, {largas} estiradas")
        print(f"  {len(palabras)} palabras · {len(con_texto)}/{len(runs)} tramos"
              f" · acuerdo medio {acuerdo:.2f} ({len(medidos)} medidos)"
              f" · {dudosos} tramos por oír · {largas} palabras estiradas"
              f" → {ruta}")


if __name__ == "__main__":
    main()
