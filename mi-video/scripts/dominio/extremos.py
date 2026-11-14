"""Los dos extremos declarados de la pieza: por dónde abre y por dónde cierra.

**Las decisiones de oído se re-imponen.** `apertura` y `cierre` salen de
`ads/frames.json` y mandan sobre lo que eligió el montaje: es el aprendizaje 13
convertido en dato — las heurísticas limpian, no eligen.

Y los dos extremos han costado un fallo cada uno, por la misma razón por los dos
lados: **un tramo declarado que no se ata a su etapa deja la etapa contada como
vacía aunque su frase esté en pantalla.** El reel 1 cerraba sin registro teniendo
la frase a veinte segundos; el reel 2 daba el beat 10 por vacío con «el link está
abajo» ya montado. Por eso aquí no basta con meter el tramo en los cortes: hay
que decir de qué etapa es.
"""
from __future__ import annotations

import sys

from . import enunciado as _enun
from . import vocabulario as _voc
from .idioma import Idioma
from .voz import Voz


def _di(msg: str) -> None:
    print(msg, file=sys.stderr)


def sin(segs, rangos) -> list:
    """Quita de `segs` lo que pisa `rangos`.

    Por INTERSECCION, no por igualdad: el tramo a sustituir suele estar partido
    en varios despues de quitar silencios.
    """
    return [t for t in segs
            if not any(min(t[1], y) - max(t[0], x) > 0.05 for x, y in rangos)]


def repetido_por(elegidos, ws, rangos, idioma=None) -> list:
    """Las unidades elegidas que un tramo declarado vuelve a decir.

    **Jaime graba en orden y repite hasta que sale**: *«no paso a la siguiente
    frase sin tener al menos una toma o serie de tomas ajustada»*. De ahi que
    entre dos versiones de la misma idea **la buena sea la ultima**, y que las
    anteriores sean intentos, no material.

    La apertura y el cierre se eligen de oido y casi siempre son una toma
    POSTERIOR y mejor del mismo beat. Sin esto el montaje emitia las dos: en el
    reel 3 la pieza decia la tesis dos veces seguidas, primero en su version
    floja y luego en la buena, que es lo que Jaime llamo *«mutilado,
    repetitivo»*.
    """
    dicho = {r: set(_voc.contenido(_enun.texto_en(ws, r), idioma))
             for r in map(tuple, rangos)}
    malos = []
    for u in elegidos:
        k = set(_voc.contenido(u.get("texto", ""), idioma))
        if not k:
            continue
        for r, palabras in dicho.items():
            if not palabras:
                continue
            comun = len(k & palabras) / max(1, len(k))
            # Que el tramo declarado diga casi todo lo que dice la unidad.
            if comun > 0.7 and u["a"] < r[0]:
                malos.append((u, r, round(comun, 2)))
                break
    return malos


def abrir(armado, frame, segs, ws) -> list:
    """Impone la apertura declarada sobre los cortes, si la hay.

    **La apertura RECORTA la unidad, no la sustituye.**

    Es la distincion de `estado.py` entre `recortar` y `rechazado`, que ya costo
    un fallo una vez: una frase que **si dice** la etapa pero entra mal se
    recorta; sustituirla entera tira la frase buena. El reel 2 lo enseno crudo —
    la apertura declarada (97,20-99,98) vive DENTRO de la unidad que el paso 2
    eligio para el beat 1 (81,39-105,11), asi que sustituirla dejaba la etapa en
    «en Brampton, tiene dos contratos,» y la pieza empezaba por un fragmento de
    dos segundos.

    Si la apertura cae dentro de una unidad elegida, se conserva **desde donde
    Jaime dijo hasta donde acaba la frase**. Si no toca ninguna, se impone tal
    cual, que es el caso para el que se penso.
    """
    apertura = frame.get("apertura")
    if not apertura:
        return segs
    elegidos = armado.elegidos
    dentro = next((u for u in elegidos
                   if u["a"] <= apertura[0] + 0.05 and apertura[1] <= u["b"] + 0.05),
                  None)
    trozo = [apertura[0], round(dentro["b"], 3)] if dentro else apertura
    segs = [trozo] + sin(segs, [trozo])
    # Y lo que la apertura ya dice, no se dice otra vez antes.
    # La unidad de la que sale el propio recorte no cuenta: el tramo no la
    # repite, **es ella**. Sin esto la regla se comia el beat que acababa de
    # conservar (C-47).
    for u, _, cuanto in [x for x in repetido_por(elegidos, ws, [trozo],
                                           Idioma.de_cinta(armado.toma))
                         if x[0] is not dentro]:
        _di(f"  beat {u['beat']}: la apertura dice lo mismo "
            f"({int(cuanto * 100)}% de las palabras) y es posterior. "
            f"Grabas en orden y repites hasta que sale: **la buena es la "
            f"ultima**, asi que el beat se queda con la apertura.")
        segs = [t for t in segs
                if not (min(t[1], u["b"]) - max(t[0], u["a"]) > 0.05)]
        # **El beat no se pierde: cambia de toma.** Borrarlo de `elegidos` lo
        # dejaba contado como SIN MATERIAL teniendo su frase en pantalla, que es
        # el defecto de C-27 por otra puerta.
        u["a"], u["b"] = trozo[0], trozo[1]
        u["tramos"] = [list(trozo)]

    # **La apertura declarada ES el primer beat.** Si no se elige unidad para
    # el, el beat sale contado como SIN MATERIAL y se le fabrica una tarjeta que
    # tapa justo la apertura. Es el mismo agujero que ya tenia el cierre (C-27)
    # por el otro extremo de la pieza.
    if not armado.tiene(1):
        txt = _enun.texto_en(ws, trozo)
        armado.declara(
            armado.etapas[0],
            {"a": trozo[0], "b": trozo[1], "texto": txt,
             "clave": set(_voc.contenido(txt, Idioma.de_cinta(armado.toma))),
             "pal": []},
            voz=Voz(trozo[0], trozo[1], armado.toma).expresividad,
            delante=True)
        _di("  beat 1: lo cumple la apertura declarada.")
    return segs


def cerrar(armado, frame, segs) -> list:
    """Impone el cierre declarado, y lo ata a la etapa de registro.

    El cierre declarado ES la etapa de registro. Sin esto la comprobacion de
    obligatorios la da por vacia y avisa de un agujero que no existe.
    """
    cierre = frame.get("cierre")
    if not cierre:
        return segs
    segs = sin(segs, cierre) + cierre
    ultima = armado.etapas[-1]
    if not armado.tiene(ultima.n):
        # `voz: None` — el cierre viene declarado de oido y nadie lo ha medido.
        # Un `0.0` aqui decia «plano» de la unica etapa que pide la accion.
        armado.declara(ultima,
                       {"a": cierre[0][0], "b": cierre[-1][1],
                        "texto": "(cierre declarado)", "clave": set()})
    return segs
