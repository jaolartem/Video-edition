"""
Mide el dinamismo vocal de una toma: cuánto varía la voz frente a lo plano.

Qué mide y por qué
------------------
La **variabilidad de la frecuencia fundamental (F0)** es el correlato acústico
mejor establecido de la expresividad percibida en el habla: una entrega plana
tiene poca desviación de tono, una entrega dinámica la tiene alta. Se reporta en
**semitonos** y no en hercios porque la percepción de tono es logarítmica —
comparar en hercios penaliza injustamente a las voces graves.

Se complementa con:

- **Rango de intensidad** — cuánto se mueve el volumen. Una entrega plana
  también lo es en energía.
- **Estructura de pausas** — una entrega que respira y marca énfasis pausa; una
  monótona atropella o pausa siempre igual.
- **Variación del ritmo** — no la velocidad media, sino cuánto cambia.

Límite honesto
--------------
Esto mide **dinamismo vocal**, que es lo que se pidió: que no se sienta plano.
El dinamismo es un correlato bien sustentado de la *expresividad percibida*.
**No es prueba de enganche ni de conversión** — el propio playbook prohíbe
presentar una correlación como causalidad demostrada. Sirve para ordenar
candidatas y descartar lo plano; la decisión final es de quien escucha.

Uso:
    python scripts/vocal-dynamics.py work/audio/*.wav
"""
import json
import sys
import wave

import numpy as np

SR = 16000
FRAME = int(0.040 * SR)   # 40 ms
HOP = int(0.010 * SR)     # 10 ms
F0_MIN, F0_MAX = 70, 320  # voz masculina adulta con margen


def read_wav(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR, f"{path}: se esperaban {SR} Hz"
        assert w.getnchannels() == 1, f"{path}: se esperaba mono"
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0


def frames(x):
    n = 1 + (len(x) - FRAME) // HOP
    if n <= 0:
        return np.empty((0, FRAME))
    idx = np.arange(FRAME)[None, :] + HOP * np.arange(n)[:, None]
    return x[idx]


def f0_track(fr):
    """
    F0 por autocorrelación normalizada, cuadro a cuadro.

    Se resta la media de cada cuadro antes de correlar: sin eso, un offset de
    continua domina la autocorrelación y el detector se engancha al retardo 0.
    """
    lag_min, lag_max = SR // F0_MAX, SR // F0_MIN
    fr = fr - fr.mean(axis=1, keepdims=True)
    win = np.hanning(FRAME)[None, :]
    fw = fr * win

    spec = np.fft.rfft(fw, n=2 * FRAME, axis=1)
    acf = np.fft.irfft(spec * np.conj(spec), axis=1)[:, :lag_max + 1]

    energy = acf[:, 0:1]
    with np.errstate(divide="ignore", invalid="ignore"):
        norm = np.where(energy > 0, acf / energy, 0.0)

    seg = norm[:, lag_min:lag_max + 1]
    best = np.argmax(seg, axis=1)
    peak = seg[np.arange(len(seg)), best]
    lag = best + lag_min

    rms = np.sqrt((fr ** 2).mean(axis=1))
    # Sonoro: pico de autocorrelación claro Y energía por encima del suelo.
    floor = np.percentile(rms, 20) * 1.6
    voiced = (peak > 0.35) & (rms > max(floor, 1e-4))

    f0 = np.where(voiced, SR / np.maximum(lag, 1), np.nan)

    # Suavizado de mediana sobre 5 cuadros (50 ms). El detector se engancha de
    # vez en cuando a la octava equivocada en cuadros sueltos; sin esto esos
    # saltos inflan la desviación y una toma plana puede parecer dinámica.
    from scipy.ndimage import median_filter
    valid = np.isfinite(f0)
    if valid.sum() > 5:
        filled = np.where(valid, f0, np.nan)
        sm = median_filter(np.nan_to_num(filled, nan=np.nanmedian(filled)), size=5)
        f0 = np.where(valid, sm, np.nan)

    return f0, voiced, rms


def analyse(path):
    x = read_wav(path)
    fr = frames(x)
    if len(fr) == 0:
        return None

    f0, voiced, rms = f0_track(fr)
    v = f0[np.isfinite(f0)]
    if len(v) < 50:
        return {"file": path, "error": "casi nada sonoro — silencio o solo ruido"}

    # Recorte de extremos: los saltos de octava del detector son atípicos.
    lo, hi = np.percentile(v, [5, 95])
    v = v[(v >= lo) & (v <= hi)]

    semitones = 12 * np.log2(v / np.median(v))
    q25, q75 = np.percentile(semitones, [25, 75])

    db = 20 * np.log10(np.maximum(rms, 1e-6))
    speech = db > (np.percentile(db, 95) - 35)
    db_speech = db[speech]

    # Pausas: tramos no sonoros de más de 200 ms.
    silent = ~voiced
    runs, cur = [], 0
    for s in silent:
        if s:
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    pauses = [r * HOP / SR for r in runs if r * HOP / SR >= 0.20]

    dur = len(x) / SR
    voiced_ratio = float(voiced.mean())

    return {
        "file": path,
        "duracion_s": round(dur, 1),
        "f0_mediana_hz": round(float(np.median(v)), 1),
        # La métrica principal.
        "f0_sd_semitonos": round(float(np.std(semitones)), 2),
        # Robusto frente a saltos de octava residuales; es el que pesa.
        "f0_iqr_semitonos": round(float(q75 - q25), 2),
        "f0_rango_semitonos": round(float(np.percentile(semitones, 90) - np.percentile(semitones, 10)), 2),
        "intensidad_sd_db": round(float(np.std(db_speech)), 2),
        "intensidad_rango_db": round(float(np.percentile(db_speech, 95) - np.percentile(db_speech, 5)), 2),
        "pausas": len(pauses),
        "pausas_por_min": round(len(pauses) / (dur / 60), 1),
        "pausa_media_s": round(float(np.mean(pauses)), 2) if pauses else 0.0,
        "pausa_sd_s": round(float(np.std(pauses)), 2) if pauses else 0.0,
        "ratio_sonoro": round(voiced_ratio, 3),
    }


def score_relative(rows):
    """
    Ordena las tomas **entre sí**, no contra una escala absoluta.

    Un índice con topes fijos saturó en 100 para todas: no existen umbrales
    absolutos validados para esta voz, así que fingirlos daba un número inútil.
    Lo que sí se puede afirmar es cuál de ESTAS tomas es la más dinámica, que es
    justo la decisión que hay que tomar.

    Los pesos son un juicio explícito: F0 pesa más por ser el correlato mejor
    sustentado de expresividad percibida. Con menos de dos tomas no hay nada que
    comparar y no se puntúa.
    """
    if len(rows) < 2:
        for m in rows:
            m["dinamismo"] = None
        return rows

    def unit(key):
        vals = np.array([m[key] for m in rows], dtype=float)
        lo, hi = vals.min(), vals.max()
        return np.zeros_like(vals) if hi - lo < 1e-9 else (vals - lo) / (hi - lo)

    comp = (
        unit("f0_iqr_semitonos") * 0.45
        + unit("f0_rango_semitonos") * 0.20
        + unit("intensidad_sd_db") * 0.20
        + unit("pausa_sd_s") * 0.15
    )
    for m, c in zip(rows, comp):
        m["dinamismo"] = round(float(c) * 100, 1)
    return rows


if __name__ == "__main__":
    out = []
    for p in sys.argv[1:]:
        m = analyse(p)
        if m is None or "error" in m:
            print(f"{p}: {m['error'] if m else 'vacío'}", file=sys.stderr)
            continue
        out.append(m)

    score_relative(out)
    out.sort(key=lambda m: -m["dinamismo"])
    print(json.dumps(out, indent=2, ensure_ascii=False))
