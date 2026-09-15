"""Dónde cae un texto en el montaje de hoy. **Sólo mide: no cambia nada.**

Es la mitad de `revision.py` que contesta una pregunta —«esta frase, ¿en qué
segundo de la pieza suena?»— sin tocar el EDL ni la base. El techo lo pide con
esas palabras (`scripts/tamano.py`): *«se parte por responsabilidad: lo que
mide, lo que decide y lo que escribe son tres cosas»*. Esto es lo que mide.

**Y separarlo deshace un ciclo que ya dolía.** `dominio/nota.py` —que decide si
una nota todavía se puede aplicar— tenía que hacer `import revision` **dentro
de un método** para poder preguntar dónde cae su ancla: el dominio llamando al
paso, y con un import perezoso puesto ahí para que el ciclo no reventara al
cargar. Ahora los dos preguntan al mismo sitio y ninguno depende del otro.

La vara con la que se compara el texto no vive aquí: es `dominio/texto.py`
(`comparable`), y la de qué palabra suena dentro de un corte es
`transcribir.suena` (C-84). Aquí sólo se recorre el montaje en orden.

    ancla.por_ancla(edl, "de 20 dolares", slug, cual=2)   # -> (desde, hasta)
    ancla.montado_a_cinta(edl, 20.0)                      # -> (i, s de cinta)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: **Aquí no hay factor de velocidad, y decirlo importa.**
#:
#: Esta constante estuvo en 1,15 —el montaje se aceleraba— y bajó a 1,0 cuando
#: dejó de acelerarse en esta escala. Lo que quedó fue una constante que vale
#: 1 dividiendo en cinco sitios: **identidad disfrazada de conversión**. Y con
#: el mismo nombre que `beats.VELOCIDAD`, que vale 1,15 y sí hace algo: acelera
#: la entrega. Dos constantes con un nombre y dos significados es la avería que
#: este proyecto ya conoce con `limpio`, con `norm` y con `VOCABULARIOS`.
#:
#: El EDL, el plan y el render viven todos en tiempo de cinta, así que aquí no
#: se convierte nada. **Lo que sí hay que convertir es un tiempo dictado
#: mirando la ENTREGA**, que va a `beats.VELOCIDAD`, y eso se hace donde ese
#: tiempo entra —`dominio/ticket.py`—, no repartido por las fórmulas.


def slug_de(edl):
    return edl.get("slug") or edl.get("video_slug") or ""


def montado_a_cinta(edl, t_montado):
    """De segundo de la pieza montada a segundo de la cinta.

    Jaime mira **la pieza**, así que sus tiempos son de la pieza. El EDL vive en
    tiempo de cinta y además el montaje corre a 1,15×. Sin esta traducción, un
    «desde el segundo 20» recortaría el sitio equivocado — que es exactamente el
    tipo de fallo que no se ve hasta que ya está renderizado.

    Devuelve `(i, t_cinta)`: en qué segmento cae y en qué segundo de la cinta.
    """
    t = 0.0
    for i, (a, b) in enumerate(edl["segmentos"]):
        dur = b - a
        if t_montado <= t + dur + 1e-6:
            return i, a + (t_montado - t)
        t += dur
    return len(edl["segmentos"]) - 1, edl["segmentos"][-1][1]


def por_ancla(edl, ancla, slug="", cual=1):
    """Dónde está ese texto en la pieza, en segundos de montaje.

    Es lo que hace que una corrección sobreviva a que la pieza se vuelva a
    montar. Se busca sobre las palabras de la cinta recorridas en orden de
    montaje, que es exactamente lo que el espectador oye.

    `cual` dice **qué aparición**, y sin eso el paso de redundancia no podia
    hacer su trabajo. La cinta es un abanico: la misma frase esta grabada varias
    veces para poder escoger. Cuando dos tomas dicen exactamente lo mismo, el
    ancla —que es texto— casa con las dos, y devolvia siempre la primera. O sea
    que el paso podia medir cual se entrega mejor y **no tenia como pedir que se
    fuera la otra**.

    Medido en reel-01 e2: «terminan ganando mucho mas» dicho dos veces, la
    primera con intensidad 2,26 y la segunda con 0,22 —plana, por debajo del
    suelo de 0,25—. Sin `cual`, cortar la plana era imposible: el ancla se
    llevaba la buena.
    """
    import transcribir as _tr, rutas as _ru

    from . import texto as _tx

    limpio = _tx.comparable          # la vara con la que se busca un ancla

    # Un ancla puede ser una frase, o «desde ... hasta» separadas por «|»: para
    # un corte largo, la primera dice donde empieza y la segunda donde acaba.
    partes = [limpio(x).split() for x in ancla.split("|")]
    obj = partes[0]
    fin_obj = partes[1] if len(partes) > 1 else None
    if not obj:
        return None
    cache, linea, t, ilegible = {}, [], 0.0, set()
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        toma = det.get("toma") or _ru.TOMAS.get(slug or slug_de(edl))
        if toma not in cache:
            try:
                cache[toma] = _tr.exigir(toma)["segmentos"]
            except (SystemExit, _tr.Incompleta):
                # **Una cinta que no se puede leer no es una cinta sin texto.**
                # Con `[]` a secas el ancla no resolvia, y mas abajo eso se lee
                # como «el texto ya no esta en la pieza»: la nota se marcaba
                # `aplicada` y **el corte se perdia para siempre**, sin que
                # nadie lo contara. Se distingue una cosa de la otra.
                cache[toma] = []
                ilegible.add(toma)
        for w in cache[toma]:
            # La vara de que palabra suena dentro del corte vive en
            # `transcribir.suena` (C-84). Este era el CUARTO sitio con su propia
            # copia, y aqui el precio es alto: si la linea del montaje no es la
            # que se oye, los segundos que se calculan no son los de la pieza y
            # **el corte cae donde no es**. Reel-01 perdio media etapa 2 y el
            # cierre entero por esto.
            if _tr.suena(w, rango[0], rango[1]):
                dentro = w["start"] - rango[0]
                linea.append((limpio(w["text"]).strip(), t + dentro,
                              t + (w["end"] - rango[0])))
        t += rango[1] - rango[0]
    pal = [x[0] for x in linea]
    visto = 0
    for i in range(len(pal) - len(obj) + 1):
        if pal[i:i + len(obj)] != obj:
            continue
        visto += 1
        if visto < max(1, int(cual or 1)):
            continue
        desde = round(linea[i][1], 2)
        if not fin_obj:
            return desde, round(linea[i + len(obj) - 1][2], 2)
        for j in range(i + len(obj), len(pal) - len(fin_obj) + 1):
            if pal[j:j + len(fin_obj)] == fin_obj:
                return desde, round(linea[j + len(fin_obj) - 1][2], 2)
        return False if ilegible else None
    # **`False` es «no pude mirar»; `None` es «mire y no esta».** Son cosas
    # opuestas y las dos llegaban como `None`: quien llama lo leia como «el
    # texto ya no esta en la pieza», marcaba la nota `aplicada` y el corte
    # desaparecia sin que nadie lo contara.
    return False if ilegible else None
