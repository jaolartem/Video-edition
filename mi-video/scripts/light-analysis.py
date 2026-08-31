"""
Mide luz y temperatura de color de cada toma, para elegir por criterio y no a ojo.

Qué mide
--------
Se muestrea un fotograma cada N segundos y se leen las estadísticas de señal que
da ffmpeg:

- **YAVG** — luma media. La exposición.
- **UAVG / VAVG** — croma medio. U es el eje azul–amarillo y V el rojo–cian; el
  punto neutro de ambos es 128. Una U por debajo de 128 tira a azul (luz fría) y
  por encima tira a amarillo (luz cálida).

De ahí salen dos cosas distintas y las dos importan:

- **Nivel** — si está bien expuesta y con qué dominante de color.
- **Consistencia** — cuánto varían esos valores DENTRO de la toma. Una toma que
  cambia de luz a mitad es peor que una mal expuesta pero estable: lo primero no
  se arregla con un ajuste global, lo segundo sí.

Límite honesto
--------------
Sin una referencia de blanco en el encuadre no se puede calcular una temperatura
de color en kelvin de verdad. Lo que se reporta es la **dominante medida en el
espacio YUV**, que sirve para comparar tomas entre sí — no para afirmar "esto
son 4200 K".

Y hay un sesgo que impide leer el valor absoluto como error de balance de
blancos: **la piel es rojiza por naturaleza**. En un primer plano hablando a
cámara el rostro domina el encuadre, así que Cr siempre saldrá alto y Cb bajo
aunque el balance sea correcto. Por eso el número sirve para **comparar tomas
entre sí** y para detectar que una se va respecto de las demás; corregir a ciegas
hasta el neutro dejaría a Jaime con cara de cadáver.

Uso:
    python scripts/light-analysis.py <video.mp4> [más vídeos...]
"""
import json
import subprocess
import sys
import os


import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402


SAMPLE_EVERY_S = 15


def sample(video):
    """
    Un fotograma cada 15 s, reescalado a 320 px antes de medir.

    Se usa `-i` y no el filtro `movie=`: ese filtro exige escapar la ruta dentro
    del grafo de filtros y se rompe con espacios y acentos — y aquí el material
    vive en «G:/My Drive/Creación de videos/…». El reescalado va ANTES de
    signalstats porque sobre 4K el análisis por fotograma cuesta mucho más y las
    medias de luma y croma apenas cambian al reducir.
    """
    proc = subprocess.run(
        ["ffmpeg", "-v", "error"] + gpu.decodifica() + ["-i", video,
         "-vf", f"fps=1/{SAMPLE_EVERY_S},scale=320:-1,signalstats,metadata=print:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    rows, cur = [], {}
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith("frame:"):
            if {"Y", "U", "V"} <= cur.keys():
                rows.append((cur["Y"], cur["U"], cur["V"]))
            cur = {}
        elif "signalstats.YAVG=" in line:
            cur["Y"] = float(line.split("=")[1])
        elif "signalstats.UAVG=" in line:
            cur["U"] = float(line.split("=")[1])
        elif "signalstats.VAVG=" in line:
            cur["V"] = float(line.split("=")[1])
    if {"Y", "U", "V"} <= cur.keys():
        rows.append((cur["Y"], cur["U"], cur["V"]))
    return np.array(rows) if rows else None


def analyse(video):
    a = sample(video)
    if a is None or len(a) < 2:
        return {"file": video, "error": "no se pudo muestrear"}

    y, u, v = a[:, 0], a[:, 1], a[:, 2]
    # 128 es el neutro de croma en YUV de 8 bits.
    #
    # SIGNO, que es fácil de invertir: U es Cb (diferencia de azul) y V es Cr
    # (diferencia de rojo). Cb POR DEBAJO de 128 significa MENOS azul, es decir
    # más cálido — no más frío. Cr por encima de 128 significa más rojo, también
    # más cálido. Los dos ejes apuntan al mismo sitio.
    cb = float(u.mean() - 128)
    cr = float(v.mean() - 128)
    warm = -cb + cr  # positivo = cálido

    return {
        "file": video.replace("\\", "/").split("/")[-1],
        "muestras": len(a),
        "luma_media": round(float(y.mean()), 1),
        # Variación de exposición dentro de la toma: lo que no arregla un ajuste global.
        "luma_sd": round(float(y.std()), 2),
        "luma_min": round(float(y.min()), 1),
        "luma_max": round(float(y.max()), 1),
        "cb_offset": round(cb, 2),
        "cr_offset": round(cr, 2),
        "indice_calidez": round(warm, 2),
        "croma_u_sd": round(float(u.std()), 2),
        "croma_v_sd": round(float(v.std()), 2),
        "tendencia": (
            "cálida" if warm > 3 else "fría" if warm < -3 else "neutra"
        ),
    }


if __name__ == "__main__":
    out = [analyse(v) for v in sys.argv[1:]]
    print(json.dumps(out, indent=2, ensure_ascii=False))
