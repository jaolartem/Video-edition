"""Reintegra la voz limpiada fuera, sin tocar el montaje.

Regla de Jaime, y viene de un fallo mío: *«el sonido se escucha con mucho eco la
voz, se perdieron factores y suena muy feo; voy a pasarlo por Adobe Podcast,
dame los audios de los vídeos sin arreglos, puros»*. Y después: *«en esa misma
carpeta te dejo los optimizados»*.

## Por qué la limpieza se hace fuera

Le puse a la voz una cadena de corrección —highpass, campana a 250 Hz, presencia
a 3200, de-esser— para responder a *«no se mejoró la calidad»*. Fue un error de
lectura: lo que había pedido era *«dejar el sonido de la voz un poco más
natural»*, y yo contesté con **más** procesado. El corte de 250 Hz es
exactamente lo que le quita el cuerpo a una voz masculina.

Una herramienta que hace **sólo** eso lo hace mejor. Así que el reparto queda:
el pipeline corta, sincroniza y mezcla; la limpieza de voz es un paso externo, y
esto la devuelve a su sitio.

## Lo que comprueba antes de tocar nada

**La duración.** Un fichero limpiado que no dura lo mismo desincroniza la pieza
entera, y eso no se ve hasta el render. Si difiere más de `TOLERANCIA`, se dice
y no se sustituye — un audio desplazado medio segundo es peor que uno con eco.

    python scripts/voz-limpia.py --ver     # que encontraria y si encaja
    python scripts/voz-limpia.py           # sustituye y masteriza
"""
import argparse
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402

# Donde Jaime deja los limpiados. La local es el respaldo por si Drive no esta
# montado; se miran las dos y gana la mas reciente.
CARPETAS = [
    "G:/My Drive/Creación de videos/Audio para limpiar",
    "out/audio-puro",
]

# Cuanto puede diferir la duracion antes de considerarlo otro audio. Cuarenta
# milisegundos es medio frame: por debajo no se ve, por encima se nota en los
# labios.
TOLERANCIA = 0.04


def duracion(f):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", f], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def candidato(n):
    """El WAV limpiado del reel n, si lo hay.

    Se acepta cualquier nombre que lleve `reel-R<n>` **menos el original**: las
    herramientas de limpieza renombran a su gusto —«(enhanced)», «_clean»— y
    obligar a un nombre exacto sería obligarle a él a renombrar seis ficheros.
    Entre varios, el más reciente.
    """
    vistos = []
    for carpeta in CARPETAS:
        if not os.path.isdir(carpeta):
            continue
        for f in glob.glob(os.path.join(carpeta, "*.wav")):
            base = os.path.basename(f).lower()
            if not re.search(rf"reel-r0?{n}\b", base):
                continue
            if base.endswith("-puro.wav"):
                continue          # el que le di yo, no el que devuelve
            vistos.append(f)
    return max(vistos, key=os.path.getmtime) if vistos else None


def integrar(n, ver=False):
    video = f"out/reels/reel-R{n}.mp4"
    if not os.path.exists(video):
        return False
    wav = candidato(n)
    if not wav:
        print(f"R{n}: sin audio limpiado todavia")
        return False
    dv, da = duracion(video), duracion(wav)
    if abs(dv - da) > TOLERANCIA:
        print(f"R{n}: NO encaja — el video dura {dv:.2f}s y el audio {da:.2f}s"
              f" ({abs(dv - da):.2f}s de diferencia). No se sustituye:"
              f" desincronizaria la pieza entera.")
        registro.aviso("voz-limpia", "audio limpiado con otra duracion",
                       detalle=f"R{n}: {dv:.2f} vs {da:.2f}", eco=False)
        return False
    print(f"R{n}: {os.path.basename(wav)} encaja ({da:.2f}s)")
    if ver:
        return True
    # Se sustituye la pista sin recodificar el video: es copia de flujo.
    tmp = f"F:/tmp-video/reel-R{n}-voz.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav,
         "-map", "0:v", "-map", "1:a", "-c:v", "copy",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", tmp],
        check=True)
    os.replace(tmp, video)
    registro.nota("voz-limpia", "voz limpiada reintegrada",
                  detalle=f"R{n}: {os.path.basename(wav)}")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()
    hechos = []
    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        if integrar(n, ver=a.ver):
            hechos.append(n)
    if hechos and not a.ver:
        print(f"\nmasterizando {len(hechos)}: {hechos}")
        subprocess.run(["bash", "scripts/musica.sh", *[str(x) for x in hechos]])


if __name__ == "__main__":
    main()
