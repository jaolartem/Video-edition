"""Rehacer el EDL de una pieza **a partir del vídeo entregado**.

Jaime, cuando le dije que la entrega de las 19:20 no se podía reproducir:
*«tienes los videos, reconstruye»*. Y antes, la corrección que lo enmarca: *«no
se trata de commits, todo debía estar en base de datos, y nada se borra de la
base de datos; para eso está»*.

## Por qué hizo falta esto

El montaje que se entregó no estaba guardado en ningún sitio del que se pudiera
volver a sacar. La tabla `version` guarda la **huella** y la duración, no los
tramos; `render` y `audio_version` están vacías. O sea que se podía saber que
una entrega era distinta de otra y no cómo estaba hecha.

Eso convierte cualquier corrección posterior en un rebuild: para tocar un
tablero había que volver a cortar la pieza entera, y lo que él ya había
aprobado se perdía por el camino.

## De qué se agarra

El vídeo entregado **sí** lleva la información: lo que se dice y en qué orden.
Se transcribe la pieza, y cada frase se busca en el transcript de la cinta, que
sí está sellado. De ahí salen los tramos —de dónde a dónde de la cinta— y con
ellos el EDL.

Dos cuidados que no son opcionales:

- **La entrega va acelerada**, así que sus tiempos no son los del corte. Se
  devuelven a velocidad natural antes de comparar (`beats.VELOCIDAD`).
- **Se empalma por palabras, no por caracteres.** Whisper escribe distinto la
  misma frase en dos pasadas —«que vente» / «que vende»—, y comparar textos
  enteros falla justo donde más falta hace. Se busca la secuencia de palabras
  más larga que encaje.

Lo que sale es una **propuesta medida**, no una verdad: dice qué tramo de cinta
reconoció para cada frase y con cuánto acuerdo. Un tramo por debajo de `SEGURO`
se marca y no se escribe solo.

    python scripts/reconstruir.py 1                 # ver qué reconoce
    python scripts/reconstruir.py 1 --escribir      # dejarlo en el EDL
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from beats import VELOCIDAD  # noqa: E402

#: De dónde se sacan los vídeos entregados. Es la copia que Jaime miró, traída
#: de Drive: la única fuente que queda de ese montaje.
ENTREGADO = "out/entregado-19h/reel-R{n}.mp4"

#: Cuánto acuerdo de palabras hace falta para dar un tramo por reconocido.
#: Por debajo se marca y no se escribe: una reconstrucción que se inventa un
#: tramo es peor que no tener ninguna, porque parece un montaje válido.
SEGURO = 0.7

#: Palabras seguidas que hacen una coincidencia creíble. Con menos, cualquier
#: «y el que» encaja en veinte sitios de la cinta.
ANCLA = 5


def _palabras(txt):
    import re

    return [w for w in re.findall(r"[a-záéíóúüñ0-9]+", (txt or "").lower())]


def transcribir(mp4, idioma):
    """Lo que dice el vídeo entregado, palabra a palabra con su segundo."""
    tmp = os.path.join(os.environ.get("TMPDIR", "F:/tmp-video"), "recon.wav")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mp4,
                    "-vn", "-ac", "1", "-ar", "16000", tmp], check=True)
    import transcribir as _tr

    salida = tmp.replace(".wav", ".json")
    _tr.pasada(tmp, salida, idioma=idioma)
    with open(salida, encoding="utf-8") as f:
        return json.load(f)


def cinta_de(slug):
    """El transcript sellado de la cinta de esa pieza, palabra a palabra."""
    import rutas

    toma = rutas.cinta(slug) if hasattr(rutas, "cinta") else None
    nombre = rutas.tomas().get(slug) if hasattr(rutas, "tomas") else None
    ruta = f"work/transcripts/{nombre or toma}.json"
    if not os.path.exists(ruta):
        return None, ruta
    with open(ruta, encoding="utf-8") as f:
        return json.load(f), ruta


def casar(dichas, cinta):
    """Para cada tramo de la pieza, de dónde sale en la cinta.

    Devuelve `(desde, hasta, acuerdo)` por tramo. El acuerdo es la fracción de
    palabras que encajaron: lo que decide si esto se puede escribir o sólo
    mirar.
    """
    pal_cinta = [(w["text"], w["start"], w["end"]) for w in cinta["segmentos"]]
    secuencia = [_palabras(t)[0] if _palabras(t) else "" for t, _a, _b in pal_cinta]
    fuera, i = [], 0
    dichas_p = [w for w in dichas]
    while i < len(dichas_p):
        trozo = [_palabras(w.get("text", ""))[0] if _palabras(w.get("text", "")) else ""
                 for w in dichas_p[i:i + ANCLA]]
        if len(trozo) < ANCLA:
            break
        # La ventana de ANCLA palabras se busca entera en la cinta.
        donde = -1
        for k in range(len(secuencia) - ANCLA):
            if secuencia[k:k + ANCLA] == trozo:
                donde = k
                break
        if donde < 0:
            i += 1
            continue
        # Se estira mientras siga coincidiendo: ahí acaba el tramo.
        j, k = i, donde
        while (j < len(dichas_p) and k < len(secuencia)
               and (_palabras(dichas_p[j].get("text", "")) or [""])[0] == secuencia[k]):
            j, k = j + 1, k + 1
        fuera.append((pal_cinta[donde][1], pal_cinta[k - 1][2],
                      (j - i) / max(1, j - i)))
        i = j
    return fuera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--escribir", action="store_true",
                    help="deja el EDL reconstruido; sin esto solo se mira")
    a = ap.parse_args()
    import rutas
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        mp4 = ENTREGADO.format(n=n)
        if not os.path.exists(mp4):
            print(f"  {slug}: no esta {mp4}")
            continue
        cinta, ruta = cinta_de(slug)
        if cinta is None:
            print(f"  {slug}: falta el transcript de la cinta ({ruta})")
            continue
        from dominio.idioma import Idioma
        dichas = transcribir(mp4, Idioma.de_pieza(slug))["segmentos"]
        tramos = casar(dichas, cinta)
        largo = sum(b - x for x, b, _ in tramos)
        print(f"  {slug}: {len(tramos)} tramo(s) reconocidos · {largo:.1f}s"
              f" de cinta · la entrega dura"
              f" {_dura(mp4) * VELOCIDAD:.1f}s a velocidad natural")
        if a.escribir:
            print("     (escribir todavia no: primero hay que ver que reconoce)")
    return 0


def _dura(f):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", f],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


if __name__ == "__main__":
    raise SystemExit(main())
