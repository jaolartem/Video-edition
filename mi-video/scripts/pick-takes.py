"""
Elige, para cada frase del libreto, cuál de los intentos grabados sobrevive.

El problema
-----------
Una toma de 8 minutos contiene un reel de 90 segundos dicho tres o cuatro veces:
Jaime arranca, se traba, repite la frase, sigue, vuelve atrás. Quitar silencios
no lo resuelve — el aire muerto era el 30%, pero lo que queda son **intentos
repetidos de las mismas frases**. Hay que quedarse con uno de cada.

Qué es "el mejor intento"
-------------------------
**El libreto es guía, no contrato.** Si Jaime improvisa y suena mejor, gana la
improvisación. Por eso el parecido con el libreto **no puntúa la calidad**: sirve
solo como llave para saber de qué frase estamos hablando. Lo que se juzga es la
entrega.

1. **Fluidez** (40%) — penaliza el tartamudeo, medido como repetición de
   palabras vecinas: «un un electricista electricista» delata arranque fallido.
2. **Corte limpio** (35%) — que empiece y acabe pegado a un silencio real. Un
   intento que arranca sobre la cola del anterior no se puede cortar sin
   llevarse audio ajeno.
3. **Economía** (15%) — a igualdad de lo demás gana el más breve.
4. **Completitud** (10%) — solo desempata. No manda.

El riesgo que esto abre
-----------------------
Priorizar fluidez sobre fidelidad significa que **un error dicho con soltura gana
a la versión correcta dicha con tropiezos**. En contenido financiero regulado eso
importa. No se bloquea —el libreto es guía— pero todo intento que se aparte
mucho sale marcado con `revisar_contenido`.

Por qué trabaja sobre PALABRAS
------------------------------
Al quitar los silencios para que Whisper no alucine, los intentos quedan pegados
y el reconocimiento los fusiona: «eso no es mala suerte» tres veces en un mismo
segmento. Con tiempos por palabra se puede cortar entre el segundo intento y el
tercero; con tiempos por segmento, no.

Uso:
    python scripts/pick-takes.py --transcript work/transcripts/X.json \\
        --reel 1 --silence work/cuts/X.json --out ads/reel-01/edl.json
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

LIBRETOS = "../docs/libretos.md"

STOP = set("""de la que el en y a los del se las por un para con no una su al lo
como mas pero sus le ya o este si porque esta entre cuando muy sin sobre tambien
me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese
eso ante ellos e esto mi antes algunos yo otro otras otra tanto esa estos mucho
quienes nada muchos cual sea poco ella estar haber estas estaba estamos algunas
algo nosotros tu te ti tus ellas os esos esas es son era eran ser fue fui va van
ir hace hacer tiene tener usted mire pues bien""".split())


def normalize(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ\s]", " ", s)).strip()


def content(words):
    return [w for w in words if w not in STOP and len(w) > 2]


def load_reel_sentences(path, reel_id):
    text = open(path, encoding="utf-8").read()
    m = re.search(rf"^## Reel {reel_id} — .*?$(.*?)(?=^## Reel |\Z)", text, re.M | re.S)
    if not m:
        raise SystemExit(f"No encuentro el Reel {reel_id} en {path}")
    body = re.sub(r"^\*\*Hook:\*\*.*$", "", m.group(1), flags=re.M)
    body = re.sub(r"^\s*[-*>].*$", "", body, flags=re.M)
    out = []
    for para in body.split("\n\n"):
        para = para.strip()
        if not para or para.startswith("#"):
            continue
        for s in re.split(r"(?<=[.?!])\s+", para):
            s = s.strip()
            if len(content(normalize(s).split())) >= 2:
                out.append(s)
    return out


def build_weights(sentences):
    """
    Peso por rareza. Una palabra que sale en muchas frases no identifica nada:
    sin esto, «negocio» o «impuesto» —presentes en casi todo el libreto—
    emparejan cualquier tramo con cualquier frase.
    """
    df = Counter()
    for s in sentences:
        for w in set(content(normalize(s).split())):
            df[w] += 1
    return {w: 1.0 / (1 + c) for w, c in df.items()}


def overlap(win_words, sent_words, weights):
    """Solapamiento ponderado, normalizado por el peso total de la frase."""
    if not sent_words:
        return 0.0
    seen = set(win_words)
    total = sum(weights.get(w, 0.5) for w in set(sent_words))
    if total <= 0:
        return 0.0
    return sum(weights.get(w, 0.5) for w in set(sent_words) if w in seen) / total


def find_attempts(words, norm, sentence, weights, min_score=0.45):
    """
    Ventanas de palabras que intentan decir `sentence`, sin solaparse entre sí.

    Se prueban longitudes desde la mitad hasta el triple de la frase: el ASR
    añade muletillas y repeticiones, así que un intento puede ocupar bastante
    más palabras que las del libreto.
    """
    sw = content(normalize(sentence).split())
    n = len(sw)
    if n == 0:
        return []
    lo, hi = max(3, int(n * 0.7)), min(len(words), int(n * 2.2) + 4)

    hits = []
    for i in range(len(words)):
        best = (0.0, 0)
        for L in range(lo, hi + 1):
            if i + L > len(words):
                break
            sc = overlap(content(norm[i:i + L]), sw, weights)
            if sc > best[0]:
                best = (sc, L)
        if best[0] >= min_score:
            hits.append((best[0], i, best[1]))

    # Supresion de no-maximos: de las ventanas solapadas se queda la mejor.
    hits.sort(key=lambda x: -x[0])
    chosen, taken = [], []
    for sc, i, L in hits:
        if any(not (i + L <= a or i >= b) for a, b in taken):
            continue
        taken.append((i, i + L))
        dur = words[i + L - 1]["end"] - words[i]["start"]
        # Una frase hablada no dura mas de ~2.2 s por palabra de contenido.
        if dur > max(6.0, n * 2.2):
            continue
        chosen.append({
            "start": words[i]["start"], "end": words[i + L - 1]["end"],
            "sim": round(sc, 3),
            "raw": " ".join(w["text"] for w in words[i:i + L]),
            "words": norm[i:i + L],
        })
    chosen.sort(key=lambda c: c["start"])
    return chosen


def stutter(words):
    """
    Proporcion de palabras atrapadas en una repeticion.

    Mide n-gramas de 1 a 5 palabras, no solo palabras adyacentes. La version
    anterior solo pillaba «un un» y daba fluidez perfecta a «la mayoria de los
    emprendedores la mayoria de los emprendedores», que es justo el reinicio que
    hay que detectar: cuando Jaime se traba no repite una palabra, vuelve al
    principio de la frase.
    """
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
                # Repeticion cercana: es un reinicio, no un recurso retorico.
                marcadas.update(range(vistos[gram], vistos[gram] + n))
                marcadas.update(range(i, i + n))
            vistos[gram] = i
    return len(marcadas) / len(words)


def boundary(attempt, gaps, tol=0.30):
    if not gaps:
        return 0.5
    def near(t):
        return min(min(abs(t - a), abs(t - b)) for a, b in gaps)
    def f(t):
        return 1.0 if near(t) <= tol else max(0.0, 1 - near(t) / 2)
    return (f(attempt["start"]) + f(attempt["end"])) / 2


def score(a, gaps, shortest):
    fluidez = 1 - min(stutter(a["words"]) * 3, 1.0)
    borde = boundary(a, gaps)
    dur = a["end"] - a["start"]
    economia = min(shortest / dur, 1.0) if dur > 0 else 0.0
    total = fluidez * 0.40 + borde * 0.35 + economia * 0.15 + a["sim"] * 0.10
    return round(total, 4), {
        "fluidez": round(fluidez, 3),
        "corte_limpio": round(borde, 3),
        "economia": round(economia, 3),
        "completitud": a["sim"],
        "revisar_contenido": a["sim"] < 0.55,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--reel", type=int, required=True)
    ap.add_argument("--silence")
    ap.add_argument("--libretos", default=LIBRETOS)
    ap.add_argument("--out")
    args = ap.parse_args()

    tr = json.load(open(args.transcript, encoding="utf-8"))
    words = tr["segmentos"]
    # Restos de alucinacion tipo «[sonido al abrir la puerta]»: al partir por
    # palabra, los corchetes quedan sueltos y se cuelan como texto normal.
    ARTEFACTOS = {"sonido", "pausa", "musica", "risas", "abrir", "puerta", "caja"}
    words = [w for w in words
             if "[" not in w["text"] and "]" not in w["text"]
             and normalize(w["text"]) not in ARTEFACTOS]
    norm = [normalize(w["text"]) for w in words]

    gaps = []
    if args.silence:
        segs = json.load(open(args.silence, encoding="utf-8"))["segmentos"]
        gaps = [(segs[i][1], segs[i + 1][0]) for i in range(len(segs) - 1)]

    sentences = load_reel_sentences(args.libretos, args.reel)
    weights = build_weights(sentences)

    chosen, report, usados = [], [], []
    for idx, sentence in enumerate(sentences):
        attempts = find_attempts(words, norm, sentence, weights)
        # Nada de reutilizar audio ya asignado a otra frase.
        attempts = [a for a in attempts
                    if not any(not (a["end"] <= s or a["start"] >= e) for s, e in usados)]
        if not attempts:
            report.append({"frase": sentence[:70], "intentos": 0, "estado": "NO ENCONTRADA"})
            continue
        shortest = min(a["end"] - a["start"] for a in attempts)
        ranked = []
        for a in attempts:
            total, detalle = score(a, gaps, shortest)
            ranked.append({**a, "score": total, "detalle": detalle})
        ranked.sort(key=lambda r: -r["score"])
        best = ranked[0]
        usados.append((best["start"], best["end"]))
        chosen.append({"orden": idx, "start": best["start"], "end": best["end"],
                       "frase": sentence, "dicho": best["raw"]})
        report.append({"frase": sentence[:70], "intentos": len(attempts),
                       "elegido_s": [round(best["start"], 2), round(best["end"], 2)],
                       "score": best["score"], **best["detalle"]})

    chosen.sort(key=lambda c: c["orden"])
    total_s = sum(c["end"] - c["start"] for c in chosen)
    out = {
        "reel": args.reel, "transcript": args.transcript,
        "frases_libreto": len(sentences), "frases_encontradas": len(chosen),
        "duracion_montada_s": round(total_s, 1),
        "segmentos": [[round(c["start"], 3), round(c["end"], 3)] for c in chosen],
        "detalle": chosen, "informe": report,
    }
    js = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        open(args.out, "w", encoding="utf-8").write(js)
    else:
        print(js)

    faltan = sum(1 for r in report if r.get("estado"))
    revisar = sum(1 for r in report if r.get("revisar_contenido"))
    print(f"Reel {args.reel}: {len(chosen)}/{len(sentences)} frases · "
          f"{total_s/60:.1f} min · {faltan} sin encontrar · {revisar} a revisar",
          file=sys.stderr)
