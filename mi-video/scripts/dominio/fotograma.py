"""Un segundo de la hoja guía: lo que se ve en él, en doce caracteres.

**Por qué es una responsabilidad propia** (C-725). Jaime, 16-11-2026, después
de que la guía de reel-23 se rehiciera entera por un tablero de e2: *«si algo
falla un paso, no hay que volver a pasar desde el comienzo… lo que está bien no
se toca; si hay que agregarle algo, es agregarle, no volverlo a poner desde el
comienzo»*.

La carpeta de la guía era de la huella del spec entero, así que cambiar un
tablero de cinco segundos volvía a sacar los 117. Ahora cada segundo tiene su
propia huella:
- el código que dibuja (`src/`, sin el spec);
- lo global del spec: el EDL, los cortes, el formato;
- y sólo los elementos con tiempo que están en pantalla en ese segundo, con un
  segundo de margen para las entradas y salidas.

Un fotograma con la misma huella ya está sacado y se reutiliza. Ante la duda
la huella cambia: si algo que no se sabe situar en el tiempo se mueve, se
rehace la pieza entera, que es lo que se hacía antes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil

FPS = 30
#: Un segundo a cada lado: lo que entra o sale cerca también se ve.
MARGEN = FPS
#: No es lo que se dibuja, es su registro.
FUERA = {"huella", "bloqueado", "rompe", "compuestos", "rellenadas", "portada"}


def _h(o) -> str:
    return hashlib.sha1(json.dumps(o, sort_keys=True, ensure_ascii=False)
                        .encode("utf-8")).hexdigest()[:12]


def _codigo(raiz="src") -> str:
    """Lo que dibuja: todo `src/` menos el spec, que se mira segundo a segundo."""
    h = hashlib.sha1()
    for d, _sub, fs in sorted(os.walk(raiz)):
        for f in sorted(fs):
            if f == "reels.json" or not f.endswith((".ts", ".tsx", ".json", ".css")):
                continue
            p = os.path.join(d, f)
            h.update(p.replace("\\", "/").encode())
            with open(p, "rb") as x:
                h.update(x.read())
    return h.hexdigest()[:12]


def _cuando(e) -> tuple[float, float] | None:
    """El intervalo en fotogramas de un elemento, o `None` si no tiene tiempo."""
    if not isinstance(e, dict):
        return None
    if isinstance(e.get("at"), (int, float)) and isinstance(e.get("duration"), (int, float)):
        return e["at"], e["at"] + e["duration"]
    if isinstance(e.get("a"), (int, float)) and isinstance(e.get("b"), (int, float)):
        return e["a"], e["b"]
    if isinstance(e.get("desde"), (int, float)) and isinstance(e.get("hasta"), (int, float)):
        return e["desde"] * FPS, e["hasta"] * FPS
    return None


class Fotogramas:
    """Las huellas de los segundos de una pieza, leídas de su spec."""

    def __init__(self, spec: dict, codigo: str | None = None):
        self.codigo = codigo or _codigo()
        self.temporales: dict[str, list] = {}
        fijo = {}
        for k, v in spec.items():
            if k in FUERA:
                continue
            # `cara` es fija salvo su lista de escenas, que tiene tiempo.
            if k == "cara" and isinstance(v, dict):
                fijo[k] = {c: x for c, x in v.items() if c != "escenas"}
                v = v.get("escenas") or []
            if isinstance(v, list) and v and all(_cuando(e) for e in v):
                self.temporales[k] = v
            else:
                fijo[k] = v
        self.fijo = _h([self.codigo, fijo])

    def huella(self, frame: int) -> str:
        """Lo que se ve en ese fotograma: lo fijo y lo que está en pantalla."""
        ahi = {k: [e for e in v if _cuando(e)[0] - MARGEN <= frame < _cuando(e)[1] + MARGEN]
               for k, v in self.temporales.items()}
        return _h([self.fijo, frame, ahi])


def reutiliza(fotos: Fotogramas, frames: dict, salida: str, almacen: str) -> int:
    """Pone en `salida` los fotogramas cuya huella ya se sacó. Devuelve cuántos.

    `frames` es `{nombre: frame}`; el almacén guarda cada uno por su huella.
    """
    os.makedirs(salida, exist_ok=True)
    n = 0
    for nombre, frame in frames.items():
        hecho = os.path.join(salida, f"{nombre}.png")
        guardado = os.path.join(almacen, f"{fotos.huella(frame)}.png")
        if os.path.isfile(hecho) or not os.path.isfile(guardado):
            continue
        shutil.copyfile(guardado, hecho)
        n += 1
    return n


def guarda(fotos: Fotogramas, frames: dict, salida: str, almacen: str) -> None:
    """Lo recién sacado entra en el almacén con su huella, para la próxima."""
    os.makedirs(almacen, exist_ok=True)
    for nombre, frame in frames.items():
        hecho = os.path.join(salida, f"{nombre}.png")
        guardado = os.path.join(almacen, f"{fotos.huella(frame)}.png")
        if os.path.isfile(hecho) and os.path.getsize(hecho) > 0 and not os.path.isfile(guardado):
            shutil.copyfile(hecho, guardado)
