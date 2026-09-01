"""La curva emocional de una pieza, etapa por etapa. **No decide: dibuja.**

Regla de Jaime, y es la que ordena la seleccion entera:

> *«El efecto que buscamos es mas parecido a una onda: arriba, luego abajo,
> luego arriba otra vez. En la seleccion hay una narrativa emocional, y es la
> que nos dice cual fragmento es el mejor.»* Y la vara de si va o no va: *«si
> hablo de muerte no quiero estar cagado de la risa; si hablo de futuro no
> quiero sonar como un desesperado»*.

**Lo que no hace es decir cual deberia ser la altura de cada etapa.** Eso
depende de que se este diciendo ahi, y saberlo es leer la frase — no es
aritmetica. El detector apunta; quien monta decide.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Por debajo de esto la etapa no transmite: ni grave ni aguda, tibia.
TIBIA = 1.2


def curva(montaje) -> list:
    """Por etapa: `intensidad`, `altura`, `velocidad` y lo que se oye.

    **Cada tramo se mide contra SU cinta.** Esto tomaba la toma del primer
    corte de la etapa y medía con ella todos los demás, así que una etapa
    cosida de dos grabaciones —que es de donde sale el escalón del precio— se
    medía sobre el audio equivocado y salía tibia sin serlo. El `Tramo` sabe de
    qué cinta es; sólo había que preguntárselo.
    """
    import beats

    fuera = []
    for beat, partes in sorted(montaje.por_beat().items(),
                               key=lambda kv: (kv[0] is None, kv[0])):
        if beat is None:
            continue
        total = sum(t.dura for t, _ in partes) or 1.0
        acc = {"intensidad": 0.0, "altura": 0.0, "velocidad": 0.0}
        for t, _ in partes:
            m = beats.intensidad(t.cinta, t.desde, t.hasta,
                                 montaje.crudas(t.cinta)) or {}
            peso = t.dura / total
            for k in acc:
                acc[k] += peso * float(m.get(k) or 0.0)
        fuera.append({
            "etapa": beat,
            "titulo": partes[0][1].get("etapa"),
            "intensidad": round(acc["intensidad"], 2),
            "altura": round(acc["altura"], 2),
            "velocidad": round(acc["velocidad"], 2),
            "tibio": acc["intensidad"] < TIBIA,
            "texto": " ".join(montaje.texto(t) for t, _ in partes)[:120],
        })
    return fuera
