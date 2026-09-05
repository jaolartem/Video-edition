"""
Detecta el aire muerto de una toma y produce la lista de tramos que sobreviven.

Por qué no se quitan TODOS los silencios
----------------------------------------
Quitar todo silencio y "que no suene plano" tiran en direcciones opuestas: la
pausa retórica es parte del dinamismo — de hecho es una de las métricas que
`vocal-dynamics.py` puntúa. Un montaje sin ninguna pausa suena a ametralladora y
aplana exactamente lo que se quería conservar.

Por eso hay dos umbrales:

- **`--keep`** (por defecto 0,45 s): pausa que se respeta. Es la que respira y
  marca énfasis.
- Todo silencio por encima de `--keep` se recorta **hasta** `--keep`, no se
  elimina del todo. Así desaparece el aire muerto y sobrevive el ritmo.

Además se deja `--pad` de margen a cada lado del corte: cortar pegado a la
consonante se lleva el ataque de la palabra y suena chascado.

Uso:
    python scripts/cut-silence.py work/audio/X_full.wav
    python scripts/cut-silence.py work/audio/X_full.wav --keep 0.35 --noise -38
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# **Los dos umbrales viven en el dominio, no aquí.** Quien LEE estos tramos
# —`dominio.cinta`— necesita saber cuánto silencio lleva pegado cada extremo
# para poder decir dónde suena la voz de verdad. Escritos en los dos sitios son
# dos reglas: basta correr esto con otro `--keep` para que el otro mienta.
from dominio.cinta import MARGEN, PAUSA  # noqa: E402


def detect_silences(wav, noise_db, min_dur):
    """Delega en el `silencedetect` de ffmpeg: es el detector estándar y ya está."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", wav,
         "-af", f"silencedetect=noise={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    silences, start = [], None
    for line in proc.stderr.splitlines():
        if "silence_start:" in line:
            start = float(line.split("silence_start:")[1].strip())
        elif "silence_end:" in line and start is not None:
            end = float(line.split("silence_end:")[1].split("|")[0].strip())
            silences.append((start, end))
            start = None
    return silences


def duration(wav):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", wav],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return float(out.stdout.strip())


def build_segments(silences, total, keep, pad):
    """
    Convierte los silencios en los tramos que se conservan.

    Un silencio más largo que `keep` no se borra: se recorta a `keep`. El tramo
    conservado se extiende `pad` a cada lado para no comerse el ataque de la
    palabra siguiente.
    """
    segments, cursor = [], 0.0
    for s, e in silences:
        gap = e - s
        if gap <= keep:
            continue  # pausa legítima, no se toca
        cut_from = min(s + keep / 2 + pad, e)
        cut_to = max(e - keep / 2 - pad, cut_from)
        if cut_to > cursor:
            segments.append((cursor, cut_from))
        cursor = cut_to
    if cursor < total:
        segments.append((cursor, total))
    return [(round(a, 3), round(b, 3)) for a, b in segments if b - a > 0.08]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("wav")
    ap.add_argument("--noise", type=float, default=-36.0, help="umbral en dB")
    ap.add_argument("--keep", type=float, default=PAUSA, help="pausa que se respeta (s)")
    ap.add_argument("--pad", type=float, default=MARGEN, help="margen a cada lado (s)")
    args = ap.parse_args()

    total = duration(args.wav)
    silences = detect_silences(args.wav, args.noise, 0.20)
    segments = build_segments(silences, total, args.keep, args.pad)
    kept = sum(b - a for a, b in segments)

    print(json.dumps({
        "file": args.wav,
        "duracion_original_s": round(total, 1),
        "duracion_cortada_s": round(kept, 1),
        "eliminado_s": round(total - kept, 1),
        "eliminado_pct": round((total - kept) / total * 100, 1),
        "silencios_detectados": len(silences),
        "cortes": len(segments),
        "segmentos": segments,
    }, indent=2, ensure_ascii=False))

    print(
        f"{args.wav}: {total/60:.1f} min → {kept/60:.1f} min "
        f"({(total-kept)/total*100:.0f}% de aire muerto, {len(segments)} tramos)",
        file=sys.stderr,
    )
