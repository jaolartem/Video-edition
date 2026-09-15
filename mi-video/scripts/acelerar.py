"""Acelerar la pieza a su velocidad de entrega, y dejarla lista para mezclar.

Vivia dentro de `voz-limpia.py` y es otra cosa: aquel reintegra la voz limpiada
fuera; esto convierte el render en entrega. El techo de 300 lineas las separo,
que es justo para lo que esta.
"""
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import registro  # noqa: E402
import rutas  # noqa: E402
from beats import VELOCIDAD  # noqa: E402
# **Lo que mide se le pide a quien lo mide.** `duracion` vive en `voz-limpia`, y
# copiarla aqui seria tener dos respuestas para «cuanto dura esto». El import va
# dentro de la funcion porque `voz-limpia` importa de aqui: al reves es un ciclo.

def _acelerar(n) -> bool:
    """Acelera la pieza y su voz a `VELOCIDAD`, sin tocar el tono."""
    # `sincronia` ya sabe cuanto dura un fichero y lo usa medio proyecto; el
    # guion de `voz-limpia.py` impide importarlo por nombre, y copiar la funcion
    # seria la quinta version de «cuanto dura esto» en este repositorio.
    from sincronia import _cuanto as duracion
    v = f"out/reels/reel-R{n}.mp4"
    if not os.path.exists(v) or VELOCIDAD == 1.0:
        return False
    # **Y no se acelera dos veces.** Esto sobreescribe el render EN SU SITIO,
    # asi que una segunda pasada de `voz-limpia` lo vuelve a estirar: reel-01
    # paso de 93,4 s a 81,2 s y el render original se perdio — no hay vuelta
    # atras, hay que rehacerlo.
    #
    # La senal es la duracion: el spec dice cuanto mide la pieza SIN acelerar,
    # asi que un fichero que ya mide eso partido por la velocidad ya paso por
    # aqui. Media decima de tolerancia, que es lo que mueve el recodificado.
    try:
        import json as _json
        with open('src/reels.json', encoding='utf-8') as f:
            _sp = next((x for x in _json.load(f)
                        if x.get("id") == f"Reel-R{n}"), None)
        if _sp:
            _esperado = _sp["duracion"] / VELOCIDAD
            if abs(duracion(v) - _esperado) < 0.5:  # ya acelerado
                print(f"R{n}: ya iba a {VELOCIDAD}x, no se toca")
                return False
    except (OSError, ValueError, KeyError, TypeError):
        pass
    tmp = v.replace(".mp4", "-acelerado.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", v,
             "-filter_complex",
             f"[0:v]setpts=PTS/{VELOCIDAD}[v];[0:a]atempo={VELOCIDAD}[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "h264_amf",
             "-quality", "quality", "-rc", "cqp", "-qp_i", "20",
             "-qp_p", "20", "-pix_fmt", "yuv420p", "-c:a", "aac",
             "-b:a", "192k", tmp],
            capture_output=True, check=True)
        # **Y NO se escribe encima del render.** Este mismo comentario lleva
        # semanas diciendo que sobreescribir en su sitio pierde el original, y
        # el codigo lo seguia haciendo con una guarda contra la segunda pasada.
        # La guarda no basta: con el render convertido en entrega, `out/reels/`
        # deja de contener lo que su nombre dice, y todo lo que compara contra
        # el —la sincronia de la voz, la huella, el chequeo de montada— compara
        # contra otra cosa. Medido: `reel-R1.mp4` duraba 83,48 s en vez de 96,4,
        # y con eso la guarda de voz informaba de «sobran 12 s» en las siete.
        #
        # El acelerado es la ENTREGA y va a la bandeja de salida. El render se
        # queda intacto, que es lo que permite rehacer el audio sin re-renderizar.
        import rutas as _ru
        final = _ru.salida("entrega", f"reel-R{n}.mp4")
        os.replace(tmp, final)
        # **Copia SIN MUSICA: es sobre la que se mezcla.** `musica.sh` tomaba
        # la entrega, asi que cada corrida sumaba otra capa —27,1 dB con una
        # capa contra 13,6 en la entrega de reel-06, con el mismo valor—. Aqui
        # la pieza esta acelerada y aun muda: guardarlo hace que mezclar sea
        # idempotente. Ver C-233.
        # **Y la ruta se le pregunta a la pieza.** Estaba escrita aqui y en
        # otros cinco sitios; el que la lee para decidir si la entrega va
        # acelerada es `cuadra_con_el_json`, y dos maneras de nombrar el mismo
        # fichero son dos respuestas en cuanto una cambie. C-495.
        from dominio.pieza import Pieza
        shutil.copy2(final, Pieza(n).muda)
    except (OSError, subprocess.SubprocessError) as e:
        registro.aviso("voz-limpia", "no se pudo acelerar",
                       detalle=f"R{n}: {type(e).__name__}", eco=True)
        return False
    print(f"R{n}: acelerada a {VELOCIDAD}x  ({duracion(final):.2f}s)"
          f"  ->  {final}")
    return True


