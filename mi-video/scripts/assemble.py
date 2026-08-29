"""RUTA ANTIGUA — NO USAR. Sustituido por `beats.py`.

Este montaje elegia enunciados por densidad y fluidez hasta gastar un
presupuesto de tiempo, y **descarta contenido**: `compress_body` tira enunciados
enteros del cuerpo y `compress_cta` recorta el cierre a 30 s. Eso contradice la
politica vigente —«respeta el guion; si hay necesidad de recortar lo definimos
al final»— y es lo que dejo cinco de seis CTA cortados a mitad de frase.

La cadena viva es: `candidatos.py` -> `asignar.wf.js` -> `beats.py` ->
`plan-reel.mjs` -> `render-hook.mjs` -> `reels-spec.mjs`. Ver `montar.sh`.

Se conserva por su historial y porque `cerrar-cta.py` documenta contra el que
fallaba. **No lo enganches a nada.**
"""

"""
Monta un reel conservando el habla buena y eliminando solo las repeticiones.

El giro respecto al intento anterior
------------------------------------
La primera versión hacía: «para cada frase del libreto, busca el mejor intento».
Eso trata el libreto como **filtro**, y descartaba entera cualquier improvisación
que no coincidiera lo bastante con el texto. Verificado en material real: 11 de
24 frases quedaron fuera no por estar mal dichas, sino porque Jaime las dijo con
otras palabras — «revise qué cuenta le sale mejor» en vez de «haga las cuentas».

Aquí se hace al revés, que es lo que significa «el libreto es guía, no contrato»:

1. Se conserva **todo el habla**, en orden.
2. Se eliminan las repeticiones comparando el material **consigo mismo**, no
   contra el guion.
3. El libreto sirve solo para dos cosas al final: comprobar cobertura y marcar
   desviaciones que alguien deba revisar por contenido.

Así la improvisación buena sobrevive por defecto, en vez de necesitar permiso.

Versión sin promoción
---------------------
El playbook es tajante: EDUCATE y CONNECT terminan en su payoff **sin CTA
comercial**; solo SELL lleva uno. Como el bloque promocional vive al final de
estas tomas, cortarlo produce una segunda pieza de otro pilar con el mismo
rodaje. Se detecta por marcas léxicas y **se corta entero** — media promo es
peor que ninguna.

Uso:
    python scripts/assemble.py --transcript work/transcripts/X.json \\
        --silence work/cuts/X.json --reel 1 --out ads/reel-01
"""
import argparse
import json
import os
import re
import sys
import unicodedata

LIBRETOS = "../docs/libretos.md"

# Marcas del bloque promocional. Son de SELL y solo de SELL.
CTA_MARKS = {
    "bootcamp", "septiembre", "link", "dolares", "dolar", "inscribase",
    "registrese", "cupo", "precio", "sube", "vale", "virtual", "vivo",
}

# Vacilaciones y arranques en falso. Se recortan de los bordes del enunciado,
# que es donde se acumulan: uno arranca dudando y cierra dudando.
MULETILLAS = {
    "eh", "em", "este", "esto", "osea", "sea", "bueno", "entonces", "verdad",
    "digamos", "mira", "vea", "ok", "listo", "ya", "aja", "mmm", "pues",
    "cierto", "no", "si", "y", "que", "porque", "pero", "ahora",
}
# Estas solo cuentan como vacilacion si van SOLAS al borde; dentro de la frase
# son conectores legitimos.
SOLO_BORDE = {"y", "que", "porque", "pero", "ahora", "no", "si", "pues"}


def normalize(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ\s]", " ", s)).strip()


def load_reel_sentences(path, reel_id):
    text = open(path, encoding="utf-8").read()
    m = re.search(rf"^## Reel {reel_id} — .*?$(.*?)(?=^## Reel |\Z)", text, re.M | re.S)
    if not m:
        return []
    body = re.sub(r"^\*\*Hook:\*\*.*$", "", m.group(1), flags=re.M)
    body = re.sub(r"^\s*[-*>].*$", "", body, flags=re.M)
    out = []
    for para in body.split("\n\n"):
        for s in re.split(r"(?<=[.?!])\s+", para.strip()):
            s = s.strip()
            if len(normalize(s).split()) >= 3:
                out.append(s)
    return out


def build_utterances(words, speech_runs):
    """
    Agrupa palabras en enunciados cortando por las pausas REALES del original.

    No sirve mirar los huecos entre palabras: el transcript se hizo sobre el
    audio ya sin silencios, así que las palabras se tocan unas con otras —
    mediana de hueco 0,000 s, verificado. Las pausas viven en la deteccion de
    silencio del bruto, y es ahi donde se puede cortar sin que se note.

    Efecto lateral del remapeo: una palabra que cruza un corte parece durar lo
    que dura el silencio eliminado. Al partir en esas fronteras, esas palabras
    quedan de cierre de enunciado y su duracion deja de contaminar.
    """
    bordes = [b for _, b in speech_runs[:-1]] if speech_runs else []
    utts, cur, bi = [], None, 0
    for w in words:
        cruza = False
        while bi < len(bordes) and bordes[bi] <= w["start"] + 1e-6:
            bi += 1
        if bi < len(bordes) and w["end"] > bordes[bi] + 1e-6:
            cruza = True
        if cur is None:
            cur = {"start": w["start"], "end": w["end"], "words": [w]}
        else:
            cur["end"] = w["end"]
            cur["words"].append(w)
        if cruza:
            utts.append(cur)
            cur = None
            bi += 1
    if cur:
        utts.append(cur)
    for u in utts:
        u["norm"] = [normalize(w["text"]) for w in u["words"]]
        u["text"] = " ".join(w["text"] for w in u["words"]).strip()
        u["key"] = [x for x in u["norm"] if x and x not in MULETILLAS and len(x) > 2]
    return [u for u in utts if u["key"]]


def merge_into_sentences(utts, max_gap=1.1, max_dur=13.0):
    """
    Une enunciados sueltos en frases completas antes de seleccionar nada.

    Los enunciados se cortan en las pausas, pero **Jaime pausa a mitad de frase**
    cuando piensa. Sin unir, «el gobierno de Canada espera» y «que usted tenga
    una estructura» son dos unidades distintas, y seleccionar por densidad se
    queda con la primera y tira la segunda: el montaje sale en fragmentos sin
    verbo. Verificado en material real, producia texto inservible.

    Se une hasta encontrar puntuacion de cierre —Whisper la emite— o hasta que
    la pausa es tan larga que ya no es una frase interrumpida sino otra idea.
    """
    out, cur = [], None
    for u in utts:
        if cur is None:
            cur = {**u, "words": list(u["words"]), "norm": list(u["norm"])}
        else:
            if u["start"] - cur["end"] > max_gap:
                out.append(cur)
                cur = {**u, "words": list(u["words"]), "norm": list(u["norm"])}
                continue
            cur["words"] += u["words"]
            cur["norm"] += u["norm"]
            cur["end"] = u["end"]
        # Se cierra por puntuacion o por tope de duracion. El tope importa: sin
        # el, una parrafada sin puntos se convierte en una unidad de 60 s que ya
        # no se puede ajustar a un presupuesto de 90 — o entra entera o no entra.
        cierra = (cur["words"][-1]["text"].strip().endswith((".", "?", "!"))
                  or cur["end"] - cur["start"] >= max_dur)
        if cierra:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    for u in out:
        u["text"] = " ".join(w["text"] for w in u["words"]).strip()
        u["key"] = [x for x in u["norm"] if x and x not in MULETILLAS and len(x) > 2]
    return [u for u in out if u["key"]]


def trim_hesitations(utt):
    """
    Recorta vacilaciones de los bordes del enunciado.

    «eh, bueno, entonces… el banco no le presta… ¿no?» — la idea util esta en
    medio. Con tiempos por palabra se puede quitar exactamente el arranque y el
    cierre dubitativos sin tocar el resto. Solo se recorta en los BORDES: en
    mitad de la frase, «pero» o «porque» son conectores, no dudas.
    """
    w, n = utt["words"], utt["norm"]
    i, j = 0, len(w)
    while i < j and n[i] in MULETILLAS:
        i += 1
    while j > i and n[j - 1] in MULETILLAS:
        j -= 1
    # Si el recorte se lo come casi todo, es que el enunciado era solo relleno.
    if j - i < 2:
        return None
    if i == 0 and j == len(w):
        return utt
    out = {**utt, "words": w[i:j], "norm": n[i:j],
           "start": w[i]["start"], "end": w[j - 1]["end"]}
    out["text"] = " ".join(x["text"] for x in out["words"]).strip()
    out["key"] = [x for x in out["norm"] if x and x not in MULETILLAS and len(x) > 2]
    return out if out["key"] else None


def density(utt):
    """
    Palabras de contenido por segundo. Mide cuanto DICE un enunciado por lo que
    ocupa: es lo que separa una idea de un rodeo.
    """
    dur = utt["end"] - utt["start"]
    return len(utt["key"]) / dur if dur > 0.2 else 0.0


def split_zones(utts, promo_i, hook_s=16.0):
    """
    Parte la toma en tres zonas, porque cada una se edita con reglas distintas.

    - **Gancho**: los primeros segundos. Es lo unico que decide si alguien se
      queda, asi que no se comprime: se preserva entero.
    - **Cuerpo**: aqui vive el rodeo, y aqui cae toda la compresion.
    - **CTA**: se preserva igual que el gancho. Un CTA recortado a trozos pierde
      la oferta, la fecha o la accion, y entonces deja de ser un CTA.

    Tratarlas por igual con un presupuesto global fue el error anterior: la
    seleccion voraz se llevaba el CTA o dejaba el reel sin argumento, segun que
    se protegiera.
    """
    if not utts:
        return [], [], []
    t0 = utts[0]["start"]
    gancho = [u for u in utts if u["start"] - t0 < hook_s]
    if not gancho:
        gancho = utts[:1]
    resto = utts[len(gancho):]
    if promo_i is None:
        return gancho, resto, []
    corte = max(0, promo_i - len(gancho))
    return gancho, resto[:corte], resto[corte:]


def compress_body(body, budget_s):
    """
    Comprime SOLO el cuerpo, quedandose con lo que mas dice por segundo.

    El rodeo se reconoce por densidad baja: muchas palabras, poco contenido. Se
    ordena por contenido-por-segundo ponderado con fluidez y se llena el
    presupuesto; despues se devuelve en orden cronologico, que es el unico en el
    que el argumento se sostiene.
    """
    total = sum(u["end"] - u["start"] for u in body)
    if total <= budget_s:
        return body, 0
    orden = sorted(body, key=lambda u: -(density(u) * 0.7 + quality(u) * 0.3))
    sel, usado = [], 0.0
    for u in orden:
        d = u["end"] - u["start"]
        if usado + d <= budget_s:
            sel.append(u)
            usado += d
    sel.sort(key=lambda u: u["start"])
    return sel, len(body) - len(sel)


def compress_cta(cta, max_s=30.0):
    """
    El CTA se preserva, pero sin sus repeticiones.

    «esta semana el bootcamp esta en 20 dolares» dicho dos veces es una vez. Se
    conservan los enunciados que aportan un elemento nuevo —oferta, fecha,
    precio, accion— y se descartan los que solo repiten uno ya cubierto.
    """
    ELEMENTOS = {
        "oferta": {"bootcamp", "virtual", "vivo"},
        "fecha": {"septiembre", "octubre", "noviembre"},
        "precio": {"dolares", "dolar", "vale", "precio", "sube"},
        "accion": {"link", "abajo", "inscribase", "registrese", "revise"},
    }
    cubiertos, sel, usado = set(), [], 0.0
    for u in cta:
        aporta = {k for k, v in ELEMENTOS.items()
                  if v & set(u["key"]) and k not in cubiertos}
        if not aporta:
            continue
        d = u["end"] - u["start"]
        if usado + d > max_s:
            continue
        cubiertos |= aporta
        sel.append(u)
        usado += d
    sel.sort(key=lambda u: u["start"])
    return sel, sorted(cubiertos)


def trim_internal_repeat(utt, min_n=3):
    """
    Recorta el arranque de un enunciado que reinicia dentro de sí mismo.

    «eso no es mala suerte, eso no es mala suerte, eso no es mala suerte» es un
    solo enunciado con tres intentos pegados. Se busca el n-grama repetido más
    largo y se conserva **la última** aparición: el reinicio final suele ser el
    bueno, porque es el que Jaime dio por válido antes de seguir.
    """
    n_words = utt["norm"]
    best = None
    for n in range(min_n, min(12, len(n_words) // 2 + 1)):
        first = tuple(n_words[:n])
        for i in range(n, len(n_words) - n + 1):
            if tuple(n_words[i:i + n]) == first:
                best = i
    if best:
        utt = {**utt,
               "words": utt["words"][best:],
               "norm": utt["norm"][best:],
               "start": utt["words"][best]["start"]}
        utt["text"] = " ".join(w["text"] for w in utt["words"]).strip()
        utt["key"] = [x for x in utt["norm"] if x and x not in MULETILLAS and len(x) > 2]
    return utt


def similar(a, b):
    """Solapamiento de contenido entre dos enunciados, simétrico."""
    sa, sb = set(a["key"]), set(b["key"])
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / min(len(sa), len(sb))


def stutter(words):
    """Proporción de palabras atrapadas en una repetición cercana."""
    if len(words) < 2:
        return 0.0
    marcadas = set()
    for n in range(1, 6):
        if len(words) < n * 2:
            break
        vistos = {}
        for i in range(len(words) - n + 1):
            gram = tuple(words[i:i + n])
            if gram in vistos and i - vistos[gram] <= n + 3:
                marcadas.update(range(vistos[gram], vistos[gram] + n))
                marcadas.update(range(i, i + n))
            vistos[gram] = i
    return len(marcadas) / len(words)


def quality(utt):
    """
    Calidad de entrega, sin mirar el libreto.

    Fluidez manda; después, densidad de contenido (un enunciado que dice mucho
    en pocas palabras está mejor dicho que uno lleno de muletillas).
    """
    flu = 1 - min(stutter(utt["norm"]) * 3, 1.0)
    dens = len(utt["key"]) / max(len(utt["norm"]), 1)
    return round(flu * 0.7 + dens * 0.3, 4)


def dedupe(utts, thresh=0.62):
    """
    De cada grupo de enunciados que dicen lo mismo, sobrevive el mejor.

    Se compara cada enunciado con los anteriores **por contenido propio**, no
    contra el guion: así se detectan también las repeticiones de cosas que Jaime
    improvisó y que no están en el libreto.
    """
    grupos = []
    for u in utts:
        for g in grupos:
            if similar(u, g[0]) >= thresh:
                g.append(u)
                break
        else:
            grupos.append([u])
    keep = []
    for g in grupos:
        g.sort(key=lambda u: (-quality(u), u["start"]))
        keep.append({**g[0], "intentos": len(g)})
    keep.sort(key=lambda u: u["start"])
    return keep


def find_promo_start(utts):
    """
    Primer enunciado del bloque promocional.

    Se busca en el último 45% de la línea de tiempo: las marcas de CTA pueden
    aparecer sueltas antes («le voy a explicar…») y cortar ahí se llevaría el
    argumento por delante.
    """
    if not utts:
        return None
    corte = utts[0]["start"] + (utts[-1]["end"] - utts[0]["start"]) * 0.55
    for i, u in enumerate(utts):
        if u["start"] >= corte and CTA_MARKS & set(u["key"]):
            return i
    return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--silence")
    ap.add_argument("--reel", type=int)
    ap.add_argument("--libretos", default=LIBRETOS)
    ap.add_argument("--out", required=True)
    # 90 s para reels, 120 s para ads. La comunicacion tiene que ser directa.
    ap.add_argument("--budget", type=float, default=90.0)
    # Fecha real de la oferta. Si en el audio se dice otra, el CTA hablado no
    # se puede publicar y hay que sustituirlo por tarjeta.
    ap.add_argument("--fecha", default="21 de septiembre")
    # Segundo del bruto donde empieza el argumento. Todo lo anterior —arranques
    # en falso, ajustes, leer el libreto— se descarta.
    #
    # Se pasa a mano a proposito. Se intento detectar la lectura midiendo la
    # altura de la cabeza y **la hipotesis no se sostuvo**: los valores salieron
    # en un solo grupo apretado (rango intercuartilico 0,016), sin las dos
    # poblaciones que harian falta para separar. Marcar con eso seria inventarse
    # una distincion que los datos no tienen.
    ap.add_argument("--desde", type=float, default=0.0)
    # Duracion de la zona de gancho. Mas corto = mas directo.
    ap.add_argument("--gancho", type=float, default=16.0)
    # Apertura en frio: segundo del bruto cuya frase abre la pieza.
    #
    # Esa frase se coloca al principio Y SE CONSERVA en su posicion natural. No
    # es un truco de montaje: en frio plantea una pregunta que se entiende sin
    # contexto, y cuando vuelve al final ya lleva todo el argumento detras. La
    # misma frase cumple dos funciones distintas.
    #
    # Se da como RANGO explicito «inicio:fin», no como instante.
    #
    # Buscar el enunciado mas cercano no servia: el recorte de repeticion
    # interna conserva la ULTIMA aparicion de una frase repetida, asi que la
    # apertura acababa siendo el fragmento final en vez de la frase entera.
    # Cuando la frase se elige a oido, el rango se sabe — y saberlo gana a
    # deducirlo.
    ap.add_argument("--apertura", default="", help="inicio:fin en segundos")
    args = ap.parse_args()

    words = json.load(open(args.transcript, encoding="utf-8"))["segmentos"]
    # Restos de alucinacion: al partir por palabra, «[sonido al abrir la puerta]»
    # deja los corchetes en palabras sueltas y el resto se cuela como texto.
    ARTEFACTOS = {"sonido", "pausa", "musica", "risas", "abrir", "puerta", "caja",
                  "silencio", "aplausos"}
    words = [w for w in words
             if "[" not in w["text"] and "]" not in w["text"]
             and normalize(w["text"]) not in ARTEFACTOS]

    speech_runs = []
    if args.silence:
        speech_runs = json.load(open(args.silence, encoding="utf-8"))["segmentos"]

    utts = [trim_internal_repeat(u) for u in build_utterances(words, speech_runs)]
    if args.desde > 0:
        # Se RECORTA, no se descarta.
        #
        # Filtrar por `start >= desde` tiraba el enunciado entero cuando su
        # arranque caia antes del corte — y con el, el gancho: el primer
        # enunciado empezaba con ruido pero contenia la frase de apertura
        # completa. Recortando, se pierde el ruido y se conserva el argumento.
        antes = len(utts)
        recortados = 0
        vivos = []
        for u in utts:
            if u["end"] <= args.desde:
                continue
            if u["start"] < args.desde:
                keep = [i for i, w in enumerate(u["words"]) if w["end"] > args.desde]
                if not keep:
                    continue
                k0 = keep[0]
                u = {**u, "words": u["words"][k0:], "norm": u["norm"][k0:],
                     "start": max(args.desde, u["words"][k0]["start"])}
                u["text"] = " ".join(w["text"] for w in u["words"]).strip()
                u["key"] = [x for x in u["norm"] if x and x not in MULETILLAS and len(x) > 2]
                if not u["key"]:
                    continue
                recortados += 1
            vivos.append(u)
        print(f"  arranque en {args.desde:.1f}s: {antes-len(vivos)} enunciados "
              f"descartados, {recortados} recortado(s)", file=sys.stderr)
        utts = vivos

    # AVISO de palabras anormalmente largas.
    #
    # Una palabra hablada no dura mas de ~1,5 s. Si aparece durando mas, no es
    # una palabra: es una que **cruza un silencio eliminado** y quedo estirada
    # sobre el hueco al remapear los tiempos. Ahi el texto miente sobre donde
    # empieza y acaba cada cosa, y cortar por ese punto sale mal.
    #
    # Verificado: la palabra «negocio» aparecia durando 8,4 s y el «su» previo
    # quedo asignado a un intento anterior, lo que hizo cortar donde no era.
    largas = [w for w in words if w["end"] - w["start"] > 1.5]
    if largas:
        print(f"  AVISO: {len(largas)} palabras estiradas (cruzan silencio "
              f"eliminado). Los tiempos alrededor no son fiables:", file=sys.stderr)
        for w in sorted(largas, key=lambda x: -(x["end"] - x["start"]))[:5]:
            print(f"    {w['start']:7.2f}-{w['end']:7.2f} "
                  f"({w['end']-w['start']:4.1f}s) «{w['text'].strip()}»", file=sys.stderr)

    utts = merge_into_sentences(utts)
    # Otra vez tras fusionar: al unir dos mitades de frase pueden quedar
    # pegados dos intentos que por separado no se solapaban.
    utts = [trim_internal_repeat(u) for u in utts]
    utts = [x for x in (trim_hesitations(u) for u in utts) if x]
    limpio = dedupe(utts)

    # **El arranque no se sustituye.**
    #
    # Si se indico `--desde`, ese enunciado es el gancho elegido a oido y manda
    # sobre la puntuacion. El dedup llego a cambiarlo por otro intento posterior
    # que puntuaba mas alto en densidad pero empezaba con una palabra suelta:
    # el compuesto ganaba y el arranque limpio se perdia. Quien elige el gancho
    # es quien escucha.
    if args.desde > 0 and utts:
        abridor = min(utts, key=lambda u: abs(u["start"] - args.desde))
        if not limpio or limpio[0]["start"] != abridor["start"]:
            # Fuera lo que se solape en tiempo Y lo que repita su contenido: el
            # dedup habia elegido OTRO intento de la misma frase, asi que al
            # meter el bueno hay que sacar el que sustituia — si no, la misma
            # frase suena dos veces.
            limpio = [u for u in limpio
                      if (u["end"] <= abridor["start"] or u["start"] >= abridor["end"])
                      and similar(u, abridor) < 0.62]
            limpio = [abridor] + limpio
            limpio.sort(key=lambda u: u["start"])
            print(f"  arranque fijado en {abridor['start']:.1f}s "
                  f"(el dedup proponia otro; su duplicado eliminado)",
                  file=sys.stderr)
    promo_i = find_promo_start(limpio)

    os.makedirs(args.out, exist_ok=True)

    def intersecar(seleccion):
        """
        Recorta cada enunciado a los tramos con HABLA del original.

        Sin esto el EDL arrastra los silencios que se quitaron para transcribir:
        los tiempos estan en la linea del bruto, asi que un enunciado que cruza
        aire muerto lo vuelve a incluir al renderizar. Verificado — una palabra
        aparecia durando 8,4 s porque cruzaba un silencio eliminado, y ese
        silencio reaparecia en el montaje.
        """
        if not speech_runs:
            return [[u["start"], u["end"]] for u in seleccion]
        out = []
        for u in seleccion:
            for a, b in speech_runs:
                lo, hi = max(u["start"], a), min(u["end"], b)
                if hi - lo > 0.12:
                    if out and lo - out[-1][1] < 0.06:
                        out[-1][1] = hi          # tramos contiguos: se funden
                    else:
                        out.append([round(lo, 3), round(hi, 3)])
        return out

    def escribir(nombre, seleccion, pilar, cortados=0, zonas=None):
        trozos = intersecar(seleccion)
        if apertura is not None:
            # La apertura va delante SIN eliminarse de su sitio: aparece dos
            # veces a proposito, que es el recurso completo.
            frente = intersecar([apertura])
            if frente and (not trozos or trozos[0] != frente[0]):
                trozos = frente + trozos
        bruto = sum(u["end"] - u["start"] for u in seleccion)
        if apertura is not None:
            bruto += apertura["end"] - apertura["start"]
        total = sum(b - a for a, b in trozos)
        data = {
            "pilar": pilar,
            "zonas": zonas or {},
            "cta": pilar == "SELL",
            "enunciados": len(seleccion),
            "duracion_montada_s": round(total, 1),
            "aire_muerto_eliminado_s": round(bruto - total, 1),
            "segmentos": trozos,
            "detalle": [{"start": round(u["start"], 3), "end": round(u["end"], 3),
                         "intentos": u.get("intentos", 1), "calidad": quality(u),
                         "texto": u["text"]} for u in seleccion],
        }
        path = os.path.join(args.out, nombre)
        json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        z = zonas or {}
        print(f"  {pilar:8} {total:5.1f}s (−{bruto-total:.1f}s de aire) / tope {args.budget:.0f}s · "
              f"gancho {z.get('gancho_s',0):.0f}s + cuerpo {z.get('cuerpo_s',0):.0f}s "
              f"+ cta {z.get('cta_s',0):.0f}s · {cortados} rodeos fuera → {path}",
              file=sys.stderr)

    print(f"{len(utts)} enunciados · {len(limpio)} tras quitar repeticiones "
          f"({len(utts)-len(limpio)} eliminadas)", file=sys.stderr)

    def revisar_texto(seleccion, etiqueta):
        """
        Segunda revision del texto YA montado.

        La primera avisa al leer el transcript; esta mira lo que de verdad va a
        salir. Son dos pasadas a proposito: un enunciado puede parecer limpio en
        el transcript completo y arrastrar una palabra estirada justo en el
        corte elegido, que es donde mas duele.
        """
        avisos = []
        for u in seleccion:
            ws = [w for w in words if u["start"] <= w["start"] < u["end"]]
            largas = [w for w in ws if w["end"] - w["start"] > 1.5]
            if largas:
                peor = max(largas, key=lambda w: w["end"] - w["start"])
                avisos.append((u["start"], peor, len(largas)))
            # Repeticion que sobrevivio al recorte.
            k = u["key"]
            for n in range(2, 5):
                grams = [tuple(k[i:i+n]) for i in range(len(k)-n+1)]
                if len(grams) != len(set(grams)):
                    avisos.append((u["start"], None, 0))
                    break
        if avisos:
            print(f"  REVISION {etiqueta}: {len(avisos)} enunciados a mirar dos veces",
                  file=sys.stderr)
            for t, peor, n in avisos[:4]:
                if peor is not None:
                    print(f"    {t:7.2f}s  palabra estirada «{peor['text'].strip()}» "
                          f"({peor['end']-peor['start']:.1f}s), {n} en el enunciado",
                          file=sys.stderr)
                else:
                    print(f"    {t:7.2f}s  repeticion interna sin recortar",
                          file=sys.stderr)
        else:
            print(f"  REVISION {etiqueta}: sin avisos", file=sys.stderr)

    def intersecar(seleccion):
        """Recorta cada enunciado a los tramos con HABLA del original."""
        if not speech_runs:
            return [[u["start"], u["end"]] for u in seleccion]
        out = []
        for u in sorted(seleccion, key=lambda x: x["start"]):
            for a, b in speech_runs:
                lo, hi = max(u["start"], a), min(u["end"], b)
                if hi - lo > 0.12:
                    if out and lo - out[-1][1] < 0.06:
                        out[-1][1] = hi
                    else:
                        out.append([round(lo, 3), round(hi, 3)])
        return out

    gancho, cuerpo, cta = split_zones(limpio, promo_i, hook_s=args.gancho)
    cta_sel, cubiertos = compress_cta(cta)

    fijo_s = sum(u["end"] - u["start"] for u in gancho + cta_sel)
    cuerpo_sel, rodeos = compress_body(cuerpo, max(10.0, args.budget - fijo_s))

    apertura = None
    if args.apertura:
        a, b = (float(x) for x in args.apertura.split(":"))
        apertura = {"start": a, "end": b, "text": ""}
        dicho = " ".join(w["text"] for w in words if a <= w["start"] < b).strip()
        print(f"  apertura en frio: [{a:.1f}-{b:.1f}s] «{dicho[:56]}»",
              file=sys.stderr)

    sell = gancho + cuerpo_sel + cta_sel

    def dur_real(seleccion):
        """
        Duracion YA descontando los silencios que se eliminan.

        Medir el bruto engana: un enunciado que cruza aire muerto abarca mucho
        mas de lo que suena. Se reportaba un gancho de 24,8 s cuando el corte
        real eran 8,8 — un numero que no corresponde a nada de lo que se ve.
        """
        return round(sum(b - a for a, b in intersecar(seleccion)), 1)

    zonas_sell = {
        "gancho_s": dur_real(gancho),
        "cuerpo_s": dur_real(cuerpo_sel),
        "cta_s": dur_real(cta_sel),
        "cta_elementos": cubiertos,
    }
    # Verificacion de fecha. Un CTA que anuncia el dia equivocado no es un
    # detalle de montaje: invalida la pieza. Si el audio no coincide con la
    # fecha real, se marca para sustituir por tarjeta animada — tapar la voz
    # con un rotulo correcto seria peor, porque el cartel contradiria lo dicho.
    dia_real = re.search(r"\d+", args.fecha)
    # Sobre todo el bloque promocional: si la fecha mala esta en un enunciado
    # que la seleccion descarto, sigue siendo un problema del material.
    dicho_cta = normalize(" ".join(u["text"] for u in cta))
    dias = set(re.findall(r"(\d{1,2})", dicho_cta))
    palabras_dia = {"veintiuno": "21", "catorce": "14", "quince": "15",
                    "veinte": "20", "trece": "13", "dieciseis": "16"}
    for pal, num in palabras_dia.items():
        if pal in dicho_cta:
            dias.add(num)
    fecha_mala = bool(dia_real) and dia_real.group() not in dias and bool(dias & {
        "13", "14", "15", "16", "20", "21", "22"})
    zonas_sell["fecha_declarada"] = args.fecha
    zonas_sell["fecha_en_audio"] = sorted(dias)
    zonas_sell["cta_sustituir_por_tarjeta"] = fecha_mala

    revisar_texto(cuerpo_sel, "cuerpo SELL")
    escribir("edl-sell.json", sell, "SELL", rodeos, zonas_sell)
    if fecha_mala:
        print(f"  FECHA INCORRECTA en el CTA hablado (dice {sorted(dias)}, "
              f"real «{args.fecha}»). Marcado para sustituir por CtaCard.",
              file=sys.stderr)

    # Sin promo: el presupuesto liberado por el CTA se lo queda el cuerpo.
    cuerpo_edu, rodeos_edu = compress_body(
        cuerpo, max(10.0, args.budget - sum(u["end"] - u["start"] for u in gancho)))
    edu = gancho + cuerpo_edu
    if sum(u["end"] - u["start"] for u in edu) >= 25:
        escribir("edl-educate.json", edu, "EDUCATE", rodeos_edu, {
            "gancho_s": dur_real(gancho),
            "cuerpo_s": dur_real(cuerpo_edu),
            "cta_s": 0.0,
        })


    if promo_i is not None:
        print(f"  promo desde {limpio[promo_i]['start']:.1f}s: "
              f"«{limpio[promo_i]['text'][:54]}»", file=sys.stderr)
    else:
        print("  sin bloque promocional claro: no hay version EDUCATE.",
              file=sys.stderr)

    if args.reel:
        sentences = load_reel_sentences(args.libretos, args.reel)
        dicho = normalize(" ".join(u["text"] for u in limpio))
        faltan = [s for s in sentences
                  if sum(1 for w in normalize(s).split() if len(w) > 3 and w in dicho)
                  < len([w for w in normalize(s).split() if len(w) > 3]) * 0.5]
        print(f"  cobertura del libreto: {len(sentences)-len(faltan)}/{len(sentences)} "
              f"frases reconocibles", file=sys.stderr)
        for s in faltan[:5]:
            print(f"    sin rastro: {s[:64]}", file=sys.stderr)
