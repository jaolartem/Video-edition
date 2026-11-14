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
import basedatos
import subprocess
import sys
import unicodedata
import wave

sys.path.insert(0, os.path.dirname(__file__))
import gpu  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402
from dominio.idioma import ES, Idioma  # noqa: E402

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
#
# Con la tarjeta puesta este numero **ya no manda** —4 hilos 8,5 s contra 12
# hilos 8,7 s, que es ruido— porque el encoder dejo de estar en la CPU. Se queda
# en 12 porque sigue siendo el bueno para la caida a CPU. Ver `gpu.py`.
HILOS = 12
# Decodificacion voraz. Medido sobre la misma ventana de 30 s: beam 5 -> 17,0 s;
# `-bs 1 -bo 1` -> 15,4 s con **0,992 de parecido** al de beam 5, o sea el mismo
# texto. Se puede bajar aqui justamente porque hay tres pasadas y consenso: lo
# que el beam compraria —no equivocarse en una decision de decodificacion— lo
# compra mejor la votacion entre pasadas. `-bs 2` sale peor en las dos cosas
# (16,2 s y 0,934), asi que no es una escala: es un escalon.
VORAZ = ["-bs", "1", "-bo", "1"]
# **El arranque de cada palabra lo mide el alineamiento, no el reparto.** Sin
# `-dtw`, whisper reparte el tiempo de cada segmento entre sus tokens por lo que
# miden, y eso no mira el audio: sobre la misma frase de la cinta
# 20261015_124118, cuatro ventanas pusieron «y yo no sé cuál» en 250,36, 250,76,
# 251,57 y 251,81 — la onda dice 251,76. Con `-dtw` las cuatro dicen 251,91-251,99.
# Cada modelo trae sus propias cabezas de alineamiento, de ahí el nombre; y el
# binario calla el DTW con flash attention puesta (`t_dtw` = -1), de ahí `-nfa`.
# Medido: 11,7 s por ventana contra 12,5 s sin él. Ver C-610.
ALINEA = {"ggml-small.bin": "small", "ggml-medium.bin": "medium"}

# Lo que el modelo dice cuando se queda sin voz. No es transcripcion, es relleno
# aprendido de YouTube — y ademas delata que ahi hay silencio (aprendizaje 30).
ALUCINACIONES = [
    "gracias por ver", "hasta la proxima", "suscribete", "subtitulos realizados",
    "subtitulado por", "amara.org", "www.", "no olvides", "nos vemos en",
    "gracias por su atencion",
]


def limpio(t):
    """Las palabras de un texto. La regla vive en `dominio.texto`."""
    from dominio import texto as _tx

    return _tx.palabras(t)


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


def pasada(wav, salida, modelo=None, idioma: Idioma = ES):
    """whisper sobre una ventana, con granularidad de palabra y alineada.

    En la lengua de la cinta: con `-l es` fijo, una cinta en inglés salía
    transcrita al español (C-665).
    """
    modelo = modelo or MODELO
    r = subprocess.run(gpu.whisper() + ["-m", modelo, "-f", wav,
                    *idioma.banderas, "-mc", "0", "-ml", "1", "-sow", "-ojf",
                    "-of", salida, "-np", "-nf", "-t", str(HILOS),
                    "-dtw", ALINEA[os.path.basename(modelo)], "-nfa"] + VORAZ,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(salida + ".json"):
        registro.error("transcribir", "whisper salio mal",
                       detalle=f"{os.path.basename(salida)} rc={r.returncode}"
                               f" {(r.stderr or b'')[-160:].decode('utf8','replace')}")
        return []
    d = json.load(open(salida + ".json", encoding="utf-8"))
    from dominio import pasadas as _p

    out = _p.alineadas(d.get("transcription", []), LARGA)
    if out is None:
        registro.error("transcribir", "whisper sin alineamiento",
                       detalle=f"{os.path.basename(salida)}: ninguna palabra trae"
                               f" t_dtw; sin el, los tiempos no miran el audio")
        return []
    return sin_etiquetas(out)


def sin_etiquetas(ws):
    """Fuera lo que el modelo se inventa. Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.sin_etiquetas(ws)


def sin_fantasmas(ws):
    """Fuera el duplicado de fundir pasadas. Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.sin_fantasmas(ws)


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
    """Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.atascado(palabras)


def etiqueta(txt):
    """Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.etiqueta(txt)


def alucinado(texto):
    """Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.alucinado(texto)


def medoide(cands):
    """La candidata del medio entre varias pasadas. Ver `dominio.pasadas`."""
    from dominio import pasadas as _p

    return _p.medoide(cands)


def transcribir(toma, runs, verbose=True, modelo=None, paso=None):
    tmp = rutas.temporal("tr", toma)

    voz_wav = os.path.join(tmp, "voz.wav")
    mapa, dur, sr, anchura = sin_silencios(audio(toma), runs, voz_wav)
    # Que corre esto se dice ANTES, no despues. Una corrida que iba a durar
    # cuarenta minutos y dura ochenta no se nota mientras pasa.
    d = gpu.aviso_si_cae("transcribir")
    if verbose:
        print(f"  {dur:.0f}s de voz en {len(runs)} tramos "
              f"→ {int(dur // PASO) + 1} ventanas de {VENTANA:.0f}s"
              f"  ·  {d['tarjeta'] if d['backend'] else 'CPU'}")

    salto = paso or PASO
    idioma = Idioma.de_cinta(toma)
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
        ws = pasada(trozo, os.path.join(tmp, f"v{k:03d}"), modelo, idioma)
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
            # **Por el arranque, que es lo medido** (C-610). El centro mezclaba
            # el arranque con un final que nadie mide, y una palabra estirada
            # sobre el hueco caia en el tramo de despues: «la verdad, síganme»
            # entro dos veces, la segunda sobre el ruido de una caja.
            dentro = [w for w in v["ws"] if a <= w["a"] < b]
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


def exigir(toma, preciso=False, cobertura=True, varias=True):
    """El transcript de varias pasadas, o no se sigue. **La puerta.**

    Lo que comprueba y cómo entrega las palabras vive ahora en
    `dominio.Cinta` —existencia, sello, frescura, cobertura, palabras pegadas al
    habla y con sitio—, porque eso es lo que se sabe de una cinta y la cinta es
    quien tiene que saberlo. Aquí queda la firma que usan los treinta y un
    sitios que ya llamaban, y el único filtro que no es de la cinta sino de para
    qué se pide: `preciso`.
    """
    from dominio import Cinta

    c = Cinta(toma)
    c.exigir(cobertura=cobertura, varias=varias)
    d = c.datos()
    if preciso and d.get("modelo") not in (None, "medium", "large-v3"):
        raise SystemExit(
            f"{c.transcript} se hizo con el modelo «{d.get('modelo')}», que"
            f" sirve para localizar pero no para el subtitulo."
            f"  ->  python scripts/transcribir.py --toma <N>")
    d["segmentos"] = [p.a_dict() for p in c.palabras()]
    return d



def guardar(toma, palabras, mapa, dudosos, modelo=None, paso=None):
    """Escribe EL transcript, no uno paralelo. Ver `dominio.transcripcion`."""
    from dominio import transcripcion

    return transcripcion.guardar(toma, palabras, mapa, dudosos, modelo, paso)


def _guardar_en_base(toma, mapa):
    """Ver `dominio.transcripcion`."""
    from dominio import transcripcion

    return transcripcion._guardar_en_base(toma, mapa)


def _saneado(toma, d):
    """Los filtros que no existian al hacer la cinta. Ver `dominio.transcripcion`."""
    from dominio import transcripcion

    return transcripcion._saneado(toma, d)


#: **La misma excepcion, no una parecida.** Habia dos clases para esto —una
#: aqui y otra en el dominio— y eso no es desorden estetico: `revision` cazaba
#: `transcribir.Incompleta` y la cinta lanzaba `CintaIncompleta`, asi que la
#: excepcion se escapaba y el paso moria en vez de anotar que no pudo leer la
#: cinta. Dos nombres para una cosa son dos comportamientos en cuanto alguien
#: toca uno.
from dominio import CintaIncompleta as Incompleta  # noqa: E402


def _sin_cubrir(toma, d=None):
    """Segundos de habla medida sin una sola palabra. Lo sabe la `Cinta`."""
    from dominio import Cinta

    return Cinta(toma).sin_texto()


def _huecos(toma, d=None, minimo=1.0):
    """**Dónde** falta el texto. Lo sabe la `Cinta`."""
    from dominio import Cinta

    return Cinta(toma).huecos(minimo)


def suena(w, a, b):
    """¿Esta palabra se oye dentro del corte `[a, b]`? La vara del oído.

    La regla vive en `dominio.Palabra.suena_en`, que es de quien es. Aquí queda
    el nombre que ya usaban `revision` y los dos extractores de `revalidar`.
    """
    from dominio import Palabra

    return Palabra.de_dict(w).suena_en(a, b)



def afinar(toma, tramos, pasadas=4):
    """Re-transcribe SOLO esos tramos con el modelo bueno.

    El trabajo vive en `dominio.afinado`, que es de quien es: elegir qué se
    vuelve a oír y fundirlo con lo que había son reglas del salvamento, no del
    paso que transcribe. Aquí queda el nombre, que ya llaman `seleccionar` y
    `revalidar`.
    """
    from dominio import afinado

    return afinado.afinar(toma, tramos, pasadas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toma", help="sólo el reel N, o el nombre de una cinta")
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
        # **Se admite el nombre de la cinta, no solo el numero de reel.**
        # Esto resolvia siempre por `rutas.TOMAS`, o sea que la unica manera de
        # transcribir algo era que ya estuviera mapeado a una pieza — y este es
        # justo el paso por el que una grabacion nueva **entra** al sistema.
        # Circulo cerrado: para transcribirla tenia que ser pieza, y para ser
        # pieza tenia que estar transcrita. La cinta del 14 de agosto llevaba
        # ahi desde el principio por esto.
        if str(a.toma).isdigit() and len(str(a.toma)) <= 2:
            tomas = [rutas.TOMAS[f"reel-{int(a.toma):02d}"]]
        elif str(a.toma) in rutas.material():
            tomas = [str(a.toma)]
        else:
            raise SystemExit(
                f"«{a.toma}» no es un reel ni una cinta del material."
                f" Hay: {', '.join(rutas.material())}")
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
        from dominio import afinado

        toma = tomas[0]
        j = afinado.dudosos(toma, a.suelo)
        print(f"{toma}: {len(j)} ventanas dudosas a afinar")
        d2, n = afinar(toma, j)
        print(f"  {n}/{len(j)} afinados -> {len(d2['segmentos'])} palabras")
        return

    if a.elegidos:
        from dominio import afinado

        slug = f"reel-{a.elegidos:02d}"
        total = 0
        for t, todos in afinado.elegidos(slug).items():
            tramos = afinado.pendientes(t, todos)
            if not tramos:
                print(f"  {t}: los {len(todos)} tramos elegidos ya estaban afinados")
                continue
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
        # La receta de dejar una cinta usable vive en `dominio.preparacion`:
        # aquí sólo se recorre la lista. Ver su docstring — es la contraparte de
        # `Cinta.exigir()`, que dice si sirve pero no qué hacer cuando no.
        from dominio import preparacion

        preparacion.preparar(toma, rehacer=a.rehacer, pasadas=a.pasadas,
                             barato=a.barato)


if __name__ == "__main__":
    main()
