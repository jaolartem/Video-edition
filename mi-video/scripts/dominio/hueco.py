"""Cuanto sitio libre deja SU CUERPO a cada lado, escena por escena.

`sujeto.py` mide la franja vertical que ocupa —donde cae la coronilla— y con eso
se coloca la banda del subtitulo y el rotulo del gancho. Falta la otra mitad:
**a que lado hay hueco y de que ancho**, que es lo que decide donde cabe el
volumen de un panel.

## Por que hizo falta

Hasta ahora el lado salia de una sola cuenta en `reels-spec.mjs`: el centro del
recorte de la PRIMERA escena de la pieza. Dos cosas fallan ahi.

La primera es que el recorte apenas se mueve en horizontal —la camara esta
fija y el encuadre solo se acerca—, asi que ese numero da practicamente el mismo
lado para las siete piezas y para todas sus escenas: no es una medida del hueco,
es una constante disfrazada. En reel-01 el plan ni siquiera trae recorte, asi que
la cuenta caia en su valor por defecto y elegia `izq` **con el sujeto a la
izquierda**.

La segunda es que el lado no basta: hace falta **cuanto**. Medido sobre las
siete, en la banda donde se dibuja el volumen (del 23,5% al 53,5% de la altura),
el hueco de ese lado iba de 0,00 a 0,53 del ancho, y el volumen pide 0,30. O sea
que **doce de los trece volumenes se estaban dibujando encima de el** — el de
reel-05 e7 le cruzaba las gafas— y nadie lo sabia porque nadie lo media.

Es la leccion de `sujeto.py` otra vez, en el otro eje: una medida que no varia
entre piezas grabadas en sesiones distintas no es una medida.

## Que se mide y donde

Se segmenta a la persona con MediaPipe —el mismo `selfie_segmenter` que ya usan
`sujeto.py` y `text-behind.py`— sobre el video YA CORTADO, que es el cuadro que
ve el espectador. Una muestra por escena del plan, en su punto medio.

De la mascara se toma **solo la banda del volumen**: una mano en el regazo no
quita sitio a una capa que vive a media altura. Y se guarda el borde izquierdo y
el derecho del sujeto dentro de esa banda, en fracciones del ancho.

    python scripts/dominio/hueco.py 5
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dominio.sujeto import MODELO, SEGURO, _fotograma  # noqa: E402

#: La banda de altura donde vive el volumen de un panel, en fracciones del
#: cuadro. Sale de `src/components/Volumen.tsx` —arranca en 0,235 y mide 0,30 de
#: alto— y esta escrita ahi UNA vez; aqui se lee de `volumenes.json` para que no
#: sean dos numeros el dia que uno se mueva.
def _banda():
    with open(os.path.join("src", "brand", "volumenes.json"),
              encoding="utf-8") as f:
        c = json.load(f)["caja"]
    return float(c["arriba"]), float(c["arriba"]) + float(c["alto"])


#: Cuanta columna tiene que dar sujeto para contarla como ocupada. Un pixel mal
#: segmentado en el borde de la cortina no estrecha el hueco; un 5% de la banda,
#: si.
DENSIDAD = 0.05


def _escenas(n):
    """Los tramos del corte, con su punto medio en la linea de tiempo montada."""
    plan = os.path.join("work", "scenes", f"reel-{n:02d}", "plan-full.json")
    if not os.path.exists(plan):
        return []
    with open(plan, encoding="utf-8") as f:
        escenas = json.load(f)["escenas"]
    t, tramos = 0.0, []
    for e in escenas:
        dura = float(e.get("duracion") or 0)
        if dura > 0:
            tramos.append({"desde": round(t, 3), "hasta": round(t + dura, 3),
                           "en": round(t + dura / 2, 3), "_plan": e})
        t += dura
    return tramos


def _costados(seg, video, t, arriba, abajo):
    """Los dos bordes del sujeto en la banda, o `None` si no se pudo segmentar."""
    import numpy as np
    import mediapipe as mp

    img = _fotograma(video, t)
    if img is None:
        return None
    m = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                             data=np.ascontiguousarray(img)))
    mask = np.asarray(m.confidence_masks[0].numpy_view()) >= SEGURO
    alto, ancho = mask.shape[0], mask.shape[1]
    banda = mask[int(alto * arriba):int(alto * abajo), :]
    if not banda.shape[0]:
        return None
    hay = banda.sum(axis=0) >= max(2, banda.shape[0] * DENSIDAD)
    xs = np.nonzero(hay)[0]
    if not len(xs):
        # Banda libre de punta a punta: cabe donde sea. Se dice con numeros y no
        # con un `None`, que obligaria a quien lee a inventarse el caso.
        return {"izq": 1.0, "der": 0.0}
    return {"izq": round(float(xs[0]) / ancho, 3),
            "der": round(1.0 - float(xs[-1] + 1) / ancho, 3)}


def de_la_pieza(n):
    """Mide el hueco de cada escena y lo deja donde el spec lo lee.

    Devuelve la lista de tramos con su hueco a cada lado, y la guarda en
    `work/scenes/reel-NN/huecos.json`. Cuesta unos segundos por pieza —una
    segmentacion por escena— y por eso se guarda: el spec se arma muchas veces.

    `izq` y `der` son **hueco libre**, no posicion del sujeto: 0,22 en `der`
    quiere decir que del 78% del ancho hacia la derecha no hay nadie.
    """
    try:
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError:
        return None
    if not os.path.exists(MODELO):
        return None
    video = f"public/reel-{n:02d}.mp4"
    tramos = _escenas(n)
    if not os.path.exists(video) or not tramos:
        return None

    arriba, abajo = _banda()
    opts = vision.ImageSegmenterOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODELO),
        running_mode=vision.RunningMode.IMAGE,
        output_confidence_masks=True)
    from .almacen_escena import Almacen, clave

    # **Escena a escena** (C-753): sólo se segmenta la escena que cambió.
    alm, salida, seg = Almacen(f"reel-{n:02d}", "huecos"), [], None
    for tr in tramos:
        k = clave(tr.pop("_plan"), [arriba, abajo])
        lados = alm.toma(k)
        if lados is None:
            seg = seg or vision.ImageSegmenter.create_from_options(opts)
            lados = alm.pon(k, _costados(seg, video, tr["en"], arriba, abajo) or {})
        if lados:
            salida.append({**tr, **lados})
    if seg:
        seg.close()
    alm.guarda()
    if not salida:
        return None
    d = os.path.join("work", "scenes", f"reel-{n:02d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "huecos.json"), "w", encoding="utf-8") as f:
        json.dump({"banda": [arriba, abajo], "tramos": salida}, f,
                  ensure_ascii=False, indent=1)
    return salida


if __name__ == "__main__":
    import rutas
    piezas = [int(a) for a in sys.argv[1:]] or rutas.piezas()
    for n in piezas:
        m = de_la_pieza(n)
        print(f"reel-{n:02d}: " + (f"{len(m)} escenas medidas" if m
                                   else "sin medir (falta video, plan o MediaPipe)"))
