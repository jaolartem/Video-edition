"""El ritmo del montaje: qué silencio es de la pieza y cuál sobra.

Jaime, 20-10-2026, viendo R18 —una confesión que su plan pedía de 70 a 75 s,
*«dicha despacio»*, *«nada va apretado, los cortes solo quitan muletillas,
silencios reales»*— entregada en 59,4 s: *«está muy recortado, como si hubieran
cortado el tiempo por encima del guion»*, *«las tomas son demasiado fuertes, el
video debe ser más fluido así se demore más»* y *«los cortes se sienten como
saltos»*.

Medido: se le quitaron 16,8 s de pausa —7,2 s en nueve cortes dentro de una
misma frase, siete de ellos de silencio puro, y 9,6 s de aire dentro de los
tramos— con la vara de una pieza de lista dicha: `AIRE` = 0,16 s, igual para
todas.

El remedio lo dio él: *«antes de recalcular, hay que crear dos modelos, uno
general y otro para estos casos»*, *«POO, una subclase»*, *«la original debe
funcionar por defecto»*. Así que `Ritmo` es el de siempre, con los números de
siempre, y `Confesion` lo hereda y cambia tres. La pieza dice cuál es el suyo
en `ads/frames.json` —`"ritmo": "confesion"`— y si no dice nada es `Ritmo`.

Lo lee `plan-reel.mjs` por `consulta.py ritmo`. No es un `if (slug === …)`: lo
que separa dos piezas es una declaración suya.
"""
from __future__ import annotations

import json

from .ajuste import HUECO

FRAMES = "ads/frames.json"


class Ritmo:
    """El general: el de siempre, y el que vale si la pieza no declara otro."""

    nombre = "general"
    #: El silencio que se respeta dentro de un tramo. Jaime lo bajó de 0,25 a
    #: 0,16 viendo el primer render: *«muchos silencios entre frases pueden ser
    #: cortados; como son microsegundos, los cortes no se suelen notar»*.
    aire = 0.16
    #: El hueco sin voz entre dos tramos seguidos de la misma cinta y la misma
    #: etapa que se conserva en vez de cortarse. Cero: se corta siempre.
    unir = 0.0
    #: Si un salto dentro de la etapa —otro momento de la cinta— cambia de
    #: encuadre. No: dentro de una etapa todas las escenas piden el mismo.
    cambia_encuadre = False

    @classmethod
    def de(cls, slug: str) -> "Ritmo":
        """El ritmo que declara la pieza. Uno que no existe para, no se adivina."""
        try:
            d = json.load(open(FRAMES, encoding="utf-8"))
            pedido = (d["reels"].get(slug) or {}).get("ritmo") or cls.nombre
        except (OSError, KeyError, ValueError):
            pedido = cls.nombre
        modelos = {m.nombre: m for m in (cls, *cls.__subclasses__())}
        if pedido not in modelos:
            raise ValueError(f"{slug}: no hay ritmo «{pedido}»; hay {sorted(modelos)}")
        return modelos[pedido]()

    def como_dict(self) -> dict:
        return {"nombre": self.nombre, "aire": self.aire, "unir": self.unir,
                "cambia_encuadre": self.cambia_encuadre}


class Confesion(Ritmo):
    """Lo que se dice despacio: la pausa es del hablante y el corte sólo quita muletillas.

    Un silencio de hasta `HUECO` —1,2 s, la frontera que el proyecto ya usa entre
    «pausa del hablante» y «aire muerto»— se queda, dentro del tramo y entre dos
    tramos seguidos sin voz en medio. Y lo que sí se corta dentro de una etapa
    —un tropiezo, otro momento de la cinta— cambia de encuadre, que es como se
    tapa un salto con una sola cámara.
    """

    nombre = "confesion"
    aire = HUECO
    unir = HUECO
    cambia_encuadre = True


def alarga(slug: str) -> float:
    """Cuánto alarga la pieza el ritmo: los huecos que el plan conservó (C-621).

    El JSON mide los tramos; lo que `Confesion` deja entre dos tramos seguidos
    no está en `duracion_montada_s`. Lo dice el plan, que es quien lo decide, y
    lo suma `version.cuadra_con_el_json` igual que las pausas del compás.
    """
    try:
        plan = json.load(open(f"work/scenes/{slug}/plan-full.json", encoding="utf-8"))
    except (OSError, ValueError):
        return 0.0
    return float(plan.get("pausas_del_ritmo_s") or 0.0)
