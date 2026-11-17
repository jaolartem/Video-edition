"""**Dónde cae un segundo**: de qué vídeo es y qué etapa ocupa.

El tiquet es lo que Jaime dice; esto es dónde aterriza. Vivían juntos porque el
tiquet fue lo primero que necesitó preguntarlo, y con eso `ticket.py` pasó del
techo de 300 líneas. Son dos cosas: una guarda una observación con su respuesta,
y la otra contesta una pregunta de reloj que no sabe nada de tiquets.

Y es el hermano en Python de `scripts/reels/reloj.mjs`, que contesta lo mismo
del lado del render.

## Las dos escalas, que es lo que se perdía

La entrega va acelerada y el montaje no. Medido sobre las siete piezas: el corte
declarado y el fichero entregado se llevan un factor de **1,13 a 1,20**
(reel-04: 79,2 s de corte, 68,5 s entregados). Así que «el segundo 30» son dos
sitios distintos, y la diferencia **crece hacia el final** — que es donde vive
el CTA.
"""
from __future__ import annotations

import json
import os

#: La carpeta `mi-video`, sacada de este fichero y no del cwd.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: No es un beat: es «no se pudo leer el EDL». Confundirlo con `None` —que sí
#: es una respuesta, «ese segundo no cae en ninguna etapa»— borraba el beat
#: bueno de cinco tiquets por abrir un fichero en la ruta equivocada.
SIN_EDL = object()


def _por_el_plan(pieza, segundo):
    """El beat según **el plan**, que es la línea que se renderiza.

    Devuelve `None` si no hay plan que leer, para que el EDL siga de respaldo.
    """
    ruta = os.path.join(RAIZ, "work", "scenes", pieza, "plan-full.json")
    if not os.path.exists(ruta):
        return None
    try:
        escenas = json.load(open(ruta, encoding="utf-8")).get("escenas") or []
    except (OSError, ValueError):
        return None
    for e in escenas:
        a = float(e.get("montado_desde", 0.0))
        if a <= segundo < a + float(e.get("duracion", 0.0)):
            b = e.get("beat", e.get("etapa_orden"))
            return None if b is None else int(b)
    return None
def beat_en(pieza, segundo):
    """Qué etapa cae en ese segundo de la pieza montada.

    ## El reloj es el del PLAN, no el del EDL

    Se recorría el EDL sumando duraciones, y el EDL **no es el reloj de la
    pieza**: `plan-reel` le quita el aire a cada corte antes de repartirlo en
    escenas —regla de Jaime, *«lo de los silencios también puede ser
    aritmético»*— así que la imagen corre sobre una línea más corta. Está medido
    en `reels/reloj.mjs`: 6,83 s en reel-01, y **el desfase crece hacia el
    final**.

    Consecuencia, medida el 6-9-2026 al abrir tres tickets sobre reel-07: el del
    segundo 38 se archivó en la etapa 3 teniendo que ser la 4, y el del 63 en la
    5 teniendo que ser la 6. Dos de tres, y las dos al final de la pieza, que es
    donde vive el CTA.

    Y no es un error de etiqueta: `dominio/abierto.py` empareja ticket y etapa
    **por beat**, así que un ticket mal colocado abre en el pedido de diseño la
    lámina de al lado. Es justo lo que este fichero declara que viene a evitar —
    *«atender la objeción en la etapa equivocada es peor que no atenderla»*— y
    lo hacía con la lista equivocada. Aprendizaje 33 otra vez: **manda la que se
    renderiza**.

    El EDL se queda de respaldo para la pieza que todavía no tiene plan: ahí es
    la única referencia que hay, y una aproximación declarada vale más que un
    `None`.

    **Y distingue dos «no» que no son el mismo.** `None` es «ese segundo no cae
    en ninguna etapa», que es una respuesta; `SIN_EDL` es «no pude leer el EDL»,
    que no lo es. Confundirlos es lo que hacia que `recolocar` borrase el beat
    bueno de cinco tickets por abrir un fichero en la ruta equivocada: borrar un
    dato porque no se pudo comprobar es peor que no comprobarlo.
    """
    if segundo is None:
        return None
    porPlan = _por_el_plan(pieza, segundo)
    if porPlan is not None:
        return porPlan
    ruta = os.path.join(RAIZ, "ads", pieza, "edl-sell.json")
    if not os.path.exists(ruta):
        return SIN_EDL
    try:
        edl = json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return SIN_EDL
    t = 0.0
    for (a, b), det in zip(edl.get("segmentos", []), edl.get("detalle", [])):
        dur = float(b) - float(a)
        if t <= segundo < t + dur:
            return det.get("beat")
        t += dur
    return None
def a_montaje(segundo, de="entrega", pieza=None):
    """El segundo dictado, traído a la escala del montaje. `(s, cuánto movió)`.

    `de="montaje"` es el render sin acelerar —lo que hay en `out/reels`, y la
    escala del EDL y del plan— y no toca nada. `de="entrega"` es lo que se
    publica, que va a `beats.VELOCIDAD`.
    """
    if segundo is None:
        return None, 0.0
    factor = 1.0
    if de == "entrega":
        import sys as _s

        _s.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        import beats

        # **La de SU pieza.** Desde el 16-9 la velocidad puede ser por pieza
        # (reel-10 va a 1,13 y el lote a 1,0), asi que un segundo dictado sobre
        # la entrega se convierte con la que esa pieza lleva de verdad. Sin
        # `pieza` contesta la del lote, que es lo que preguntan los pasos que no
        # miran una en concreto.
        factor = beats.velocidad(pieza)
    return round(float(segundo) * factor, 3), round(
        float(segundo) * (factor - 1.0), 3)
