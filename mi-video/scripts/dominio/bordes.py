"""¿Un corte cae encima de la voz? Medido en la ONDA, no en el transcript.

Jaime, tres piezas seguidas: *«dice "para due…", sin terminar»* (R7), *«al final
dice "el link está a…"»* (R6), *«el cierre del R-04 quedó truncado también, sólo
el link»*. Tres veces el mismo defecto en tres piezas distintas: no es de
ninguna de las tres.

## Por qué la comprobación que había no los cazaba

`costuras.palabras_enteras` ya mira que ningún corte caiga dentro de una
palabra, y **corre**. Pero usa los bordes que da el transcript, y en este
proyecto el transcript miente justo donde importa: hay palabras con duración
cero —ocho seguidas entre 109,28 y 109,31 en una cinta— y otras estiradas
—«dejo» ocupando 3,36 s—. Medido: caza 4 cortes en reel-06 y **0 en reel-07**,
cuya frase sí estaba partida a la mitad.

Una comprobación que pregunta a una fuente que miente no comprueba: confirma.

## Qué mira esto

El audio del bruto en el propio segundo del corte. Si en el instante en que se
corta **todavía hay voz sonando**, el corte cae encima de una palabra, diga lo
que diga el transcript. No hace falta saber qué palabra es ni dónde empieza: se
oye o no se oye.

El final de la pieza es donde más caro sale —ahí se pide la acción— pero el
defecto es el mismo en cualquier costura.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rutas  # noqa: E402

#: Por encima de esto hay voz. −42 dBFS es el mismo umbral con el que el resto
#: del proyecto separa habla de sala; por debajo está el ruido del cuarto.
VOZ = -42.0

#: Cuánto se mira a cada lado del corte, en segundos. 80 ms: menos que una
#: sílaba, así que si ahí suena, suena la palabra que se está cortando.
MIRADA = 0.08

SR = 1000


def _db(mp4, desde, dura):
    """El nivel medio de ese trocito de cinta, en dB. `None` si no se pudo."""
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, desde):.3f}",
         "-t", f"{dura:.3f}", "-i", mp4, "-vn", "-ac", "1",
         "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True).stdout
    if len(crudo) < 40:
        return None
    import numpy as np

    x = np.frombuffer(crudo, dtype=np.int16).astype(float) / 32768
    return float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))


def callado(toma, t):
    """¿La cinta ya está callada justo DESPUÉS de `t`?

    Es la misma pregunta que hace `sucios`, suelta, para que **quien coloca un
    borde la use antes** en vez de enterarse después. Sin esto sólo existía el
    veredicto: el paso que fija los tramos preguntaba al transcript, y quien
    juzgaba preguntaba a la onda, así que el corte salía sucio y el aviso
    llegaba una vuelta más tarde.

    Medir el mismo hecho con dos varas es como se firma un corte sucio creyendo
    que está limpio (C-171): ésta es la vara del que juzga, prestada.
    """
    mp4 = rutas.cinta(toma) if toma else None
    if not mp4 or not os.path.exists(mp4):
        return False
    db = _db(mp4, t, MIRADA)
    return db is not None and db <= VOZ


def callado_antes(toma, t):
    """¿La cinta está callada justo ANTES de `t`? La otra mitad de `callado`.

    Para una entrada: si ahí ya no suena, la palabra anterior acabó, diga lo que
    diga el transcript, que la estira sobre el silencio (C-481).
    """
    mp4 = rutas.cinta(toma) if toma else None
    if not mp4 or not os.path.exists(mp4):
        return False
    db = _db(mp4, t - MIRADA, MIRADA)
    return db is not None and db <= VOZ


def mas_quieto(toma, desde, hasta, ventana=0.02, paso=0.005):
    """El instante más callado de la cinta entre `desde` y `hasta`, a 16 kHz.

    Para una entrada entre dos palabras dichas de un tirón: el transcript las da
    pegadas y su frontera puede caer todavía en la anterior. En reel-16 e2 ponía
    «porque» en 217,091 con «presta» sonando a -14,5 dB, y la caída real —el
    cierre de la /p/— estaba en 217,14 (-20,8 dB). `None` si no se pudo medir.
    """
    mp4 = rutas.cinta(toma) if toma else None
    if not mp4 or not os.path.exists(mp4) or hasta <= desde:
        return None
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, desde):.3f}",
         "-t", f"{hasta - desde + ventana:.3f}", "-i", mp4, "-vn", "-ac", "1",
         "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    import numpy as np

    x = np.frombuffer(crudo, dtype=np.int16).astype(float) / 32768
    w, h = int(ventana * 16000), int(paso * 16000)
    if len(x) < w:
        return None
    rms = [(float(np.sqrt((x[i:i + w] ** 2).mean())), i)
           for i in range(0, len(x) - w + 1, h)]
    _, i = min(rms)
    return round(desde + (i + w / 2) / 16000, 3)


def sucios(slug):
    """Los cortes que caen encima de la voz. Lista vacía = ninguno.

    Mira el final de cada tramo, que es donde se guillotina una palabra: el
    principio se comprueba por el otro lado del mismo empalme.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8") as f:
        edl = json.load(f)
    fuera = []
    for i, (d, (_a, b)) in enumerate(zip(edl.get("detalle") or [],
                                         edl.get("segmentos") or [])):
        toma = d.get("toma")
        mp4 = rutas.cinta(toma) if toma else None
        if not mp4 or not os.path.exists(mp4):
            continue
        # Justo ANTES del corte: si ahí suena, la palabra estaba en curso.
        antes = _db(mp4, b - MIRADA, MIRADA)
        # Y justo DESPUÉS: si también suena, es que sigue hablando y la tijera
        # cayó en medio. Si calla, el corte llegó a un silencio y está bien.
        despues = _db(mp4, b, MIRADA)
        if antes is None or despues is None:
            continue
        if antes > VOZ and despues > VOZ:
            fuera.append({"segmento": i, "beat": d.get("beat"),
                          "en": round(b, 3), "toma": toma,
                          "antes": round(antes, 1),
                          "despues": round(despues, 1)})
    return fuera


def main():
    piezas = [int(x) for x in sys.argv[1:] if x.isdigit()] or rutas.piezas()
    total = 0
    for n in piezas:
        slug = f"reel-{n:02d}"
        malos = sucios(slug)
        total += len(malos)
        for m in malos:
            print(f"  {slug} b{m['beat']}: el corte de {m['en']}s cae encima de"
                  f" la voz ({m['antes']} dB antes, {m['despues']} despues)")
        print(f"  {slug}: {len(malos)} corte(s) sobre la voz")
    print(f"\nbordes: {total} corte(s) que se comen una palabra"
          if total else "\nbordes: ningun corte cae encima de la voz.")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
