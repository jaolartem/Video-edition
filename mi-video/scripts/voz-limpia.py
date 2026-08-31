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
import json
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

# **La convencion de nombres, que la puso el.** Jaime: *«ya viste que la
# estructura de guardado es regular: el mismo nombre mas otra parte al final»*.
#
# Yo exporto `reel-01-voz.wav` y el devuelve `reel-01-voz-enhanced-v2.wav`. Asi
# que el limpiado es **cualquier fichero que empiece por el nombre base y sea
# mas largo**: no hay que obligarle a renombrar seis ficheros ni adivinar que
# sufijo pone cada herramienta.
BASE_VOZ = "{slug}-voz"


def exportar(n):
    """Saca la voz del reel n **sin tocarla**: el paso 1 de los dos que pidio.

    Cada tramo se extrae del bruto tal cual y se pegan. Sin estirar, sin
    ecualizar, sin fundidos, sin musica y sin normalizar. Es lo que Jaime pidio
    con esas palabras: *«quiero el audio de la voz separado sin
    modificaciones»*.

    **Y a velocidad natural.** La primera vez le di el audio ya estirado a
    1,15x, o sea resintetizado por `rubberband`, y encima paso por Adobe: dos
    resintesis encadenadas. De ahi lo raro. Ahora el estirado no existe
    (`beats.VELOCIDAD` es 1), pero aunque volviera, esto sale del bruto y no del
    montaje: la limpieza va **antes** de cualquier transformacion.
    """
    slug = f"reel-{n:02d}"
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return None
    sys.path.insert(0, os.path.dirname(__file__))
    import rutas as _ru
    edl = json.load(open(ruta, encoding="utf-8"))
    # **La voz se exporta del PLAN, que es lo que se renderiza.**
    #
    # Salia del EDL, y el EDL no es la pieza: `plan-reel` quita el aire de cada
    # corte antes de repartirlo en escenas. Medido en reel-01: el wav duraba
    # 109,2 s y el video 100,9. Eso no es un detalle de contabilidad — este wav
    # se manda a limpiar fuera y **vuelve para pegarse encima del montaje**, asi
    # que ocho segundos de mas significan que la voz limpia entra desfasada y
    # creciendo, que es exactamente el fallo que costo C-97 por la puerta de las
    # capas. Jaime lo vio al instante: *«entonces si no cuadra»*.
    #
    # Si no hay plan todavia se cae al EDL, que es mejor que no exportar nada.
    plan = None
    try:
        plan = json.load(open(f"work/scenes/{slug}/plan-full.json",
                              encoding="utf-8"))["escenas"]
    except Exception:                              # noqa: BLE001
        plan = None
    if plan:
        # Las escenas del plan no llevan de que cinta salen, asi que se resuelve
        # **por contenido**: la escena cae dentro del corte del EDL que la
        # engendro, y ese corte si sabe su cinta. Por indice no vale — el plan
        # parte un corte en varias escenas, asi que las listas no se
        # corresponden. Y con el remate del reel-01 viniendo de otra cinta, dar
        # por hecha la del reel seria traerse el audio equivocado.
        def _toma(e):
            for (x, y), d in zip(edl["segmentos"], edl["detalle"]):
                if e["origen_desde"] >= x - 0.05 and e["origen_hasta"] <= y + 0.05:
                    return d.get("toma")
            return edl["detalle"][0].get("toma")

        pares = [([e["origen_desde"], e["origen_hasta"]], {"toma": _toma(e)})
                 for e in plan]
    else:
        pares = list(zip(edl["segmentos"], edl["detalle"]))
    os.makedirs("out/audio-voz", exist_ok=True)
    os.makedirs("F:/tmp-video/voz", exist_ok=True)
    trozos = []
    for i, (r, d) in enumerate(pares):
        f = f"F:/tmp-video/voz/{slug}-{i:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(r[0]),
             "-i", f"{_ru.ORIGEN}/{d['toma']}.mp4",
             "-t", str(round(r[1] - r[0], 3)), "-vn",
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", f], check=True)
        trozos.append(f)
    lista = f"F:/tmp-video/voz/{slug}.txt"
    open(lista, "w", encoding="utf-8").write(
        "\n".join("file '{}'".format(t) for t in trozos) + "\n")
    out = f"out/audio-voz/{BASE_VOZ.format(slug=slug)}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", lista, "-c", "copy", out], check=True)
    # Y a la carpeta donde el la recoge y deja la limpiada.
    for carpeta in CARPETAS:
        if os.path.isdir(carpeta):
            import shutil
            shutil.copy2(out, carpeta)
            break
    return out


def duracion(f):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", f], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def candidato(n):
    """El WAV limpiado del reel n, si lo hay.

    Por la convencion de nombres: el limpiado es el que **empieza por el nombre
    base y es mas largo** — `reel-01-voz.wav` -> `reel-01-voz-enhanced-v2.wav`.
    Entre varios, el mas reciente.
    """
    base = BASE_VOZ.format(slug=f"reel-{n:02d}").lower()
    vistos = []
    for carpeta in CARPETAS:
        if not os.path.isdir(carpeta):
            continue
        for f in glob.glob(os.path.join(carpeta, "*.wav")):
            nom = os.path.basename(f).lower()[:-4]
            if nom.startswith(base) and len(nom) > len(base):
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
    ap.add_argument("--exportar", action="store_true",
                    help="paso 1: saca la voz sin modificar a la carpeta")
    a = ap.parse_args()
    if a.exportar:
        for n in (a.reels or rutas.piezas()):
            f = exportar(n)
            if f:
                d = duracion(f)
                print(f"R{n}: {os.path.basename(f)}  {d:.2f}s sin modificar")
        print(f"\nen {CARPETAS[0]}")
        return
    hechos = []
    for n in (a.reels or rutas.piezas()):
        if integrar(n, ver=a.ver):
            hechos.append(n)
    if hechos and not a.ver:
        print(f"\nmasterizando {len(hechos)}: {hechos}")
        subprocess.run(["bash", "scripts/musica.sh", *[str(x) for x in hechos]])


if __name__ == "__main__":
    main()
