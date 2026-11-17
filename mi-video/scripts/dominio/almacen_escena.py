"""Lo medido sobre el corte, guardado escena a escena (C-753).

Jaime, 17-11-2026: *«todo por escena es todo»*. La cara, los huecos y el
trasfondo se medían sobre el corte entero cada vez que el corte cambiaba,
aunque sólo hubiera cambiado una escena. Cada uno guarda ahora lo de cada
escena por **la huella de lo que esa escena enseña**: qué cinta, qué tramo, qué
recorte, cuánto dura; más lo que la medida misma lee (`extra`). Una escena que
no cambió se lee del almacén; las demás se miden.

Lo guardado va **contado desde el inicio de la escena**: dónde cae en la pieza
lo pone quien lo lee, así que una escena que se corre de sitio porque otra
creció sigue valiendo.
"""
from __future__ import annotations

import hashlib
import json
import os


def clave(e: dict, extra=None) -> str:
    """La huella de una escena del plan: lo que el corte enseña en ella."""
    crudo = json.dumps([e.get("fuente"), e.get("origen_desde"), e.get("origen_hasta"),
                        e.get("filtro"), e.get("duracion"), e.get("pausa"),
                        e.get("angulo"), e.get("zoom"), extra],
                       ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


class Almacen:
    """Lo medido de las escenas de una pieza, por su clave."""

    def __init__(self, slug: str, nombre: str):
        self.ruta = os.path.join("work", "scenes", slug, f"{nombre}.porescena.json")
        try:
            self.antes = json.load(open(self.ruta, encoding="utf-8"))
        except (OSError, ValueError):
            self.antes = {}
        self.ahora, self.medidas = {}, 0

    def toma(self, k):
        """Lo medido de esa escena, o `None` si hay que medirla."""
        if k in self.antes:
            self.ahora[k] = self.antes[k]
            return self.antes[k]
        return None

    def pon(self, k, valor):
        self.ahora[k] = valor
        self.medidas += 1
        return valor

    def guarda(self) -> None:
        """Sólo lo de las escenas de hoy: lo de escenas que ya no están, sale."""
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        with open(self.ruta, "w", encoding="utf-8") as f:
            json.dump(self.ahora, f, ensure_ascii=False)
