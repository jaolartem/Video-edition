"""
Transcribe una toma sin darle silencio a Whisper, y devuelve los tiempos del original.

Por qué no se transcribe el audio tal cual
------------------------------------------
Se intentó y salió basura verificable: en una toma, 170 segmentos idénticos
diciendo la misma frase; en otra, 60 de 64 segmentos eran «[Pausa]». Estas tomas
tienen 26–51% de aire muerto más pausas largas de pensar, y Whisper **alucina en
bucle sobre silencio prolongado** — una vez arranca el bucle, lo arrastra.

Dos medidas contra eso:

1. **No darle silencio.** Se concatena solo el habla —usando los tramos que ya
   detectó `cut-silence.py`— y se transcribe eso. Whisper no puede alucinar
   sobre un silencio que no existe en el fichero.
2. **`-mc 0`** (contexto máximo cero). Whisper alimenta cada ventana con el texto
   de la anterior; si una alucina, la siguiente hereda el bucle. Cortando el
   contexto, cada ventana se juzga sola.

Los tiempos se remapean al original, que es lo único que sirve para montar: el
EDL tiene que apuntar al bruto, no a un audio intermedio que no existe en disco.

Uso:
    python scripts/transcribe-speech.py --audio work/audio/X_full.wav \\
        --cuts work/cuts/X.json --out work/transcripts/X.json
"""
import argparse
import json
import os
import subprocess
import sys

WHISPER = os.path.join("whisper.cpp", "whisper-cli.exe")
MODEL = os.path.join("whisper.cpp", "ggml-medium.bin")


def build_speech_wav(audio, segments, out_wav):
    """Concatena solo los tramos con habla en un único WAV."""
    parts, labels = [], []
    for i, (a, b) in enumerate(segments):
        parts.append(f"[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS[a{i}]")
        labels.append(f"[a{i}]")
    graph = ";".join(parts) + f";{''.join(labels)}concat=n={len(segments)}:v=0:a=1[out]"

    # El grafo va en fichero: con ~150 tramos supera el limite de linea de Windows.
    script = out_wav + ".filter.txt"
    with open(script, "w", encoding="utf-8") as f:
        f.write(graph)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", audio,
         "-filter_complex_script", script, "-map", "[out]",
         "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", out_wav],
        check=True,
    )
    os.remove(script)


def make_mapper(segments):
    """
    Devuelve una función que traduce tiempo-en-habla a tiempo-en-original.

    El WAV de habla es la concatenación de los tramos, así que el tiempo `t`
    cae en el tramo cuyo acumulado lo contiene, desplazado por el inicio real
    de ese tramo.
    """
    table, acc = [], 0.0
    for a, b in segments:
        table.append((acc, acc + (b - a), a))
        acc += b - a
    total = acc

    def to_original(t):
        t = max(0.0, min(t, total))
        for lo, hi, orig in table:
            if t <= hi:
                return orig + (t - lo)
        return table[-1][2] + (table[-1][1] - table[-1][0])

    return to_original, total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--cuts", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    cuts = json.load(open(args.cuts, encoding="utf-8"))
    segments = cuts["segmentos"]

    speech_wav = args.out.replace(".json", "_speech.wav")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    if not os.path.exists(speech_wav):
        print(f"Concatenando {len(segments)} tramos de habla...", file=sys.stderr)
        build_speech_wav(args.audio, segments, speech_wav)

    base = speech_wav.replace(".wav", "")
    print("Transcribiendo (sin silencio, sin contexto arrastrado)...", file=sys.stderr)
    subprocess.run(
        [WHISPER, "-m", MODEL, "-l", "es", "-f", speech_wav,
         "-oj", "-of", base,
         # Nivel PALABRA. Al quitar los silencios los intentos quedan pegados y
         # Whisper los fusiona en un solo segmento: «eso no es mala suerte» tres
         # veces seguidas. Sin tiempos por palabra no hay forma de cortar entre
         # el segundo intento y el tercero. Ademas es lo que necesitan el
         # anclaje de tableros y los subtitulos.
         "-ml", "1", "-sow",
         # Contexto cero: corta el arrastre de alucinaciones entre ventanas.
         "-mc", "0",
         # Umbrales mas estrictos para descartar ventanas de baja confianza.
         "-et", "2.6", "-lpt", "-0.8"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    raw = json.load(open(base + ".json", encoding="utf-8"))
    to_original, total = make_mapper(segments)

    mapped = []
    for s in raw["transcription"]:
        a = float(s["offsets"]["from"]) / 1000
        b = float(s["offsets"]["to"]) / 1000
        text = s["text"].strip()
        if not text or text.startswith("["):
            continue
        mapped.append({
            "start": round(to_original(a), 3),
            "end": round(to_original(b), 3),
            "text": text,
        })

    json.dump({"segmentos": mapped, "habla_s": round(total, 1),
               "origen": args.audio},
              open(args.out, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)

    uniq = len({m["text"] for m in mapped})
    print(f"{len(mapped)} palabras ({uniq} distintas) sobre {total/60:.1f} min de habla "
          f"-> {args.out}", file=sys.stderr)
    if mapped and uniq < len(mapped) * 0.12:
        print("AVISO: vocabulario muy pobre, posible alucinacion residual.", file=sys.stderr)
