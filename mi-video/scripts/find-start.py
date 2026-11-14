"""
Encuentra donde empieza el intento LIMPIO del gancho de un reel.

El problema
-----------
Cada toma arranca con intentos fallidos, ajustes y ruido antes de la version
buena. El transcript completo no sirve para localizarla: los tiempos estan
remapeados sobre el audio sin silencios, asi que las palabras que cruzan un
hueco quedan estiradas y el texto miente sobre donde empieza cada cosa.

El metodo que si funciona
-------------------------
**Transcribir cada candidato por separado.** Se prueban los arranques de los
tramos de habla, se transcribe un trozo corto desde cada uno, y se queda el
primero cuyo texto contenga la frase de gancho del libreto de forma completa.

Es el mismo procedimiento que resolvio el Reel 1 en un intento despues de que el
transcript global me hiciera cortar tres veces donde no era.

Uso:
    python scripts/find-start.py --audio work/audio/X_full.wav \\
        --cuts work/cuts/X.json --reel 2
"""
import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402
from dominio.idioma import ES, Idioma  # noqa: E402

# El binario lo elige `gpu.py`, que es el unico que sabe si hay tarjeta.
WHISPER = gpu.whisper()[0]
MODEL = os.path.join("whisper.cpp", "ggml-medium.bin")


def normalize(s):
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9ñ\s]", " ", s)).strip()


def hook_del_libreto(path, reel):
    txt = open(path, encoding="utf-8").read()
    m = re.search(rf"^## Reel {reel} — .*?$(.*?)(?=^## Reel |\Z)", txt, re.M | re.S)
    if not m:
        raise SystemExit(f"No encuentro el Reel {reel}")
    h = re.search(r"^\*\*Hook:\*\*\s*«(.+?)»", m.group(1), re.M)
    if h:
        return h.group(1)
    # Sin marca de hook, la primera frase del cuerpo.
    cuerpo = re.sub(r"^\s*[-*>].*$", "", m.group(1), flags=re.M).strip()
    return re.split(r"(?<=[.?!])\s+", cuerpo)[0]


def transcribir(audio, desde, dur=8.0, idioma: Idioma = ES):
    tmp = "work/_fs.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", str(desde), "-t", str(dur),
         "-i", audio, "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", tmp],
        check=True)
    subprocess.run(
        [WHISPER, "-m", MODEL, *idioma.banderas, "-f", tmp, "-otxt",
         "-of", tmp.replace(".wav", ""), "-nt", "-mc", "0"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return open(tmp.replace(".wav", ".txt"), encoding="utf-8").read().strip()


def cobertura(dicho, hook):
    """Fraccion de palabras de contenido del gancho que aparecen en lo dicho."""
    hw = [w for w in normalize(hook).split() if len(w) > 3]
    if not hw:
        return 0.0
    d = normalize(dicho)
    return sum(1 for w in hw if w in d) / len(hw)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cuts", required=True)
    ap.add_argument("--reel", type=int, required=True)
    ap.add_argument("--libretos", default="../docs/libretos.md")
    ap.add_argument("--max-candidatos", type=int, default=14)
    args = ap.parse_args()

    hook = hook_del_libreto(args.libretos, args.reel)
    print(f"gancho del libreto: «{hook[:74]}»\n", file=sys.stderr)

    runs = json.load(open(args.cuts, encoding="utf-8"))["segmentos"]
    # Solo tramos con cuerpo: los de menos de 1,5 s no pueden contener el gancho.
    cand = [a for a, b in runs if b - a >= 1.5][: args.max_candidatos]

    mejor = None
    for a in cand:
        dicho = transcribir(args.audio, a,
                            idioma=Idioma.de_pieza(f"reel-{args.reel:02d}"))
        c = cobertura(dicho, hook)
        marca = ""
        if mejor is None or c > mejor[1]:
            mejor = (a, c, dicho)
            marca = "  <-- mejor hasta ahora"
        print(f"  {a:7.2f}s  cobertura {c:.0%}  «{dicho[:56]}»{marca}", file=sys.stderr)
        # Cobertura casi total: no hace falta seguir buscando.
        if c >= 0.85:
            break

    a, c, dicho = mejor
    print(f"\narranque propuesto: {a:.2f}s (cobertura {c:.0%})", file=sys.stderr)
    print(f"dice: «{dicho[:110]}»", file=sys.stderr)
    if c < 0.6:
        print("AVISO: cobertura baja. Revisar a oido antes de montar.",
              file=sys.stderr)
    print(f"{a:.2f}")
