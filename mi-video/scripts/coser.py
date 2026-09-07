"""Cose la voz limpia sobre el corte de hoy, TRAMO A TRAMO.

Jaime: *«cuadra lo que quepa de la version optimizada que hay, corta y pega lo
que falte»*.

## Por que no vale sustituir la pista entera

`voz-limpia.py` compara duraciones y sustituye la pista completa o no sustituye
nada. Eso funciona mientras el corte no se toque. En cuanto se rehace —quitar
aire muerto, mover una costura, alargar un beat— los tramos se desplazan **cada
uno por su lado**, y entonces la pista limpia deja de corresponder al montaje
aunque dure lo mismo.

Medido en reel-04: la mejor alineacion global da un pico de 0,186 sobre 1, y de
sus siete ventanas de diez segundos solo dos casan. No es un desfase ni una cola
que falte: es otro montaje.

## Que hace esto

Para cada tramo del corte de hoy busca **ese mismo audio** dentro de la pista
limpia, deslizandolo hasta que encaje. Si lo encuentra con confianza, usa el
tramo limpio; si no, deja el del corte. La pieza sale con la voz optimizada donde
la hay y con la de origen donde no, sin desincronizar nada: cada trozo va en su
sitio porque su sitio es el que dice el corte.

**Y se declara lo que quedo sin limpiar**, que es lo que hay que decidir despues:
un tramo crudo entre dos limpios se oye, y si son muchos conviene volver a pasar
la pieza entera por Adobe en vez de coser.

    python scripts/coser.py 4
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SR = 1000
VENTANA = 20
#: Por debajo de esto no se da por encontrado un tramo. Mismo criterio y misma
#: escala que `desfase.py`: el pico del cruce contra lo que vale un cruce
#: cualquiera. Aqui se compara un trozo corto contra una pista larga, asi que el
#: fondo es mas alto y el listo se pone mas arriba.
CLARO = 8.0
#: Un tramo mas corto que esto no se busca: no hay envolvente que cruzar y el
#: resultado seria ruido. Se deja crudo.
MINIMO = 0.8


def _env(f, desde=None, dura=None):
    import numpy as np

    cmd = ["ffmpeg", "-v", "error"]
    if desde is not None:
        cmd += ["-ss", f"{desde:.3f}"]
    cmd += ["-i", f]
    if dura is not None:
        cmd += ["-t", f"{dura:.3f}"]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    crudo = subprocess.run(cmd, capture_output=True, check=True).stdout
    x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32)
    if len(x) < VENTANA * 4:
        return None
    n = len(x) // VENTANA
    e = np.abs(x[: n * VENTANA].reshape(n, VENTANA)).mean(axis=1)
    e -= e.mean()
    d = np.sqrt((e ** 2).sum())
    return e / d if d else None


def _donde(trozo, pista):
    """Donde empieza `trozo` dentro de `pista`, en segundos, o `None`."""
    import numpy as np

    if trozo is None or pista is None or len(trozo) >= len(pista):
        return None
    c = np.correlate(pista, trozo, mode="valid")
    i = int(np.argmax(np.abs(c)))
    pico = float(np.abs(c[i]))
    fondo = float(np.abs(c).mean()) or 1e-9
    if pico / fondo < CLARO:
        return None
    return i * VENTANA / SR


def _limpia_de(n):
    """La pista optimizada de la pieza, si la hay."""
    import glob

    import rutas

    base = f"reel-{n:02d}-voz"
    fuera = []
    for d in rutas.RECOGER:
        if not os.path.isdir(d):
            continue
        for f in glob.glob(os.path.join(d, "*.wav")):
            nom = os.path.basename(f).lower()[:-4]
            if nom.startswith(base.lower()) and nom != base.lower() \
                    and "-sin-cola" not in nom and "-con-cola" not in nom:
                fuera.append(f)
    return max(fuera, key=os.path.getmtime) if fuera else None


def main():
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("piezas", nargs="+", type=int)
    p.add_argument("--ver", action="store_true", help="solo mide, no escribe")
    a = p.parse_args()
    for n in a.piezas:
        slug = f"reel-{n:02d}"
        corte = f"public/{slug}.mp4"
        limpia = _limpia_de(n)
        if not limpia:
            print(f"R{n}: sin pista optimizada"); continue
        edl = json.load(open(f"ads/{slug}/edl-sell.json", encoding="utf-8"))
        pista = _env(limpia)
        piezas, crudos, t = [], [], 0.0
        for i, (d, h) in enumerate(edl["segmentos"]):
            dura = h - d
            en = None
            if dura >= MINIMO:
                en = _donde(_env(corte, t, dura), pista)
            if en is None:
                crudos.append((round(t, 2), round(dura, 2)))
                piezas.append(("corte", t, dura))
            else:
                piezas.append(("limpia", en, dura))
            t += dura
        hay = sum(d for k, _, d in piezas if k == "limpia")
        print(f"R{n}: {len(piezas)} tramos · {hay:.1f}s de {t:.1f}s con voz limpia"
              f" ({hay / t * 100:.0f}%) · {len(crudos)} tramo(s) crudos")
        if a.ver:
            for s, d in crudos[:6]:
                print(f"     crudo en {s:.1f}s ({d:.1f}s)")
            continue
        _pegar(slug, corte, limpia, piezas)


def _pegar(slug, corte, limpia, piezas):
    """Concatena los trozos en su orden y sustituye la pista del video."""
    import tempfile

    import rutas
    # En el temporal del proyecto, no en el del sistema:  no cruza
    # de disco en Windows, y el temporal del sistema esta en C:.
    tmp = tempfile.mkdtemp(prefix="coser-", dir=rutas.temporal())
    trozos = []
    for i, (de, desde, dura) in enumerate(piezas):
        f = os.path.join(tmp, f"{i:03d}.wav")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{desde:.3f}",
             "-i", corte if de == "corte" else limpia, "-t", f"{dura:.3f}",
             "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", f],
            check=True)
        trozos.append(f)
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w", encoding="utf-8") as fh:
        for f in trozos:
            fh.write(f"file '{f.replace(chr(92), '/')}'\n")
    pegado = os.path.join(tmp, "voz.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", lista, "-c", "copy", pegado], check=True)
    salida = f"out/audio-puro/{slug}-voz-cosida.wav"
    os.replace(pegado, salida)
    print(f"     -> {salida}")


if __name__ == "__main__":
    main()
