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
        # **Lo que no se pudo medir se cae del promedio; no entra como cero.**
        #
        # Con el cero, un beat cuya ventana es corta salia con `intensidad: 0.0`
        # y **`tibio: true`**: la peor entrega posible, dicha de un trozo que
        # nadie midio. Y `tibio` viaja al que decide, asi que era una etapa
        # buena marcada como floja por no haberse podido medir.
        #
        # El peso tambien se renormaliza sobre lo presente: si de tres partes
        # solo se midio una, la media es la de esa, no un tercio de ella.
        acc = {"intensidad": [], "altura": [], "velocidad": []}
        for t, _ in partes:
            m = beats.intensidad(t.cinta, t.desde, t.hasta,
                                 montaje.crudas(t.cinta)) or {}
            for k in acc:
                if m.get(k) is not None:
                    acc[k].append((float(m[k]), t.dura))
        med = {k: (sum(v * p for v, p in ps) / sum(p for _, p in ps)
                   if ps and sum(p for _, p in ps) else None)
               for k, ps in acc.items()}
        inten = med["intensidad"]
        fuera.append({
            "etapa": beat,
            "titulo": partes[0][1].get("etapa"),
            "intensidad": None if inten is None else round(inten, 2),
            "altura": None if med["altura"] is None else round(med["altura"], 2),
            "velocidad": (None if med["velocidad"] is None
                          else round(med["velocidad"], 2)),
            "tibio": None if inten is None else inten < TIBIA,
            "texto": " ".join(montaje.texto(t) for t, _ in partes)[:120],
        })
    return fuera
