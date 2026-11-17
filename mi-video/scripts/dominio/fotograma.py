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
    # Un golpe (un sonido, una marca) es un instante: también tiene tiempo (C-742).
    if isinstance(e.get("at"), (int, float)) and "duration" not in e:
        return e["at"], e["at"] + 1
    if isinstance(e.get("a"), (int, float)) and isinstance(e.get("b"), (int, float)):
        return e["a"], e["b"]
    if isinstance(e.get("desde"), (int, float)) and isinstance(e.get("hasta"), (int, float)):
        return e["desde"] * FPS, e["hasta"] * FPS
    return None


#: Lo que en el spec es de la pieza entera y no cambia lo que se ve en un
#: segundo concreto: su largo, y el corte entero, que se mira escena a escena.
POR_ESCENA = {"duracion", "edl", "cortes", "ventanas"}


def _corre(e, base: int):
    """Un elemento con su tiempo contado desde `base` (el inicio de su escena)."""
    e = json.loads(json.dumps(e))
    for k in ("at", "a", "b"):
        if isinstance(e.get(k), (int, float)):
            e[k] -= base
    for k in ("desde", "hasta"):
        if isinstance(e.get(k), (int, float)):
            e[k] = round(e[k] - base / FPS, 3)
    return e


class Fotogramas:
    """Las huellas de los segundos de una pieza, leídas de su spec.

    **Por escena** (C-742). Jaime: *«la pieza es la unión de los segmentos»*.
    Si el spec dice dónde empieza y acaba cada etapa (`cc`, con su `beat`), los
    segundos se cuentan desde el inicio de su escena —`e02-03` es el cuarto
    segundo de e2— y lo que se ve en uno se mide **contado desde ahí**. Que e2
    crezca no cambia nada de e3: sus segundos siguen siendo los mismos, y lo que
    Jaime aprobó de e3 sigue aprobado. Sin `cc`, como antes: un segundo de la
    pieza entera.
    """

    def __init__(self, spec: dict, codigo: str | None = None):
        self.codigo = codigo or _codigo()
        self.temporales: dict[str, list] = {}
        self.tramos = self._tramos(spec)
        self.edl = [d for d in (spec.get("edl") or {}).get("detalle") or [] if isinstance(d, dict)]
        self.cortes = [c for c in spec.get("cortes") or [] if isinstance(c, (int, float))]
        self.dura = float(spec.get("duracion") or 0)
        fijo = {}
        for k, v in spec.items():
            if k in FUERA or (self.tramos and k in POR_ESCENA):
                continue
            # `cara` es fija salvo su lista de escenas, que tiene tiempo.
            if k == "cara" and isinstance(v, dict):
                fijo[k] = {c: x for c, x in v.items() if c != "escenas"}
                v = v.get("escenas") or []
            if isinstance(v, list) and v and all(_cuando(e) for e in v):
                self.temporales[k] = v
            elif isinstance(v, list) and self.tramos and any(_cuando(e) for e in v):
                self.temporales[k] = [e for e in v if _cuando(e)]
                fijo[k] = [e for e in v if not _cuando(e)]
            else:
                fijo[k] = v
        self.del_spec = _h(fijo)
        self.fijo = _h([self.codigo, self.del_spec])

    @staticmethod
    def _tramos(spec) -> dict:
        """`{beat: (desde, hasta)}` en fotogramas, de los subtítulos del spec."""
        out = {}
        for c in spec.get("cc") or []:
            b = c.get("beat") if isinstance(c, dict) else None
            if isinstance(b, int) and isinstance(c.get("desde"), (int, float)):
                a, z = round(c["desde"] * FPS), round(c["hasta"] * FPS)
                x = out.get(b, (a, z))
                out[b] = (min(x[0], a), max(x[1], z))
        return dict(sorted(out.items()))

    def rejilla(self) -> dict:
        """`{nombre: fotograma}` de la guía. **La única**: la leen `guia.py` y `mirar.sh`."""
        ultimo = int(self.dura * FPS) - 1
        if not self.tramos:
            return {f"s{s:03d}": min(s * FPS + 15, ultimo) for s in range(int(self.dura) + 1)}
        out = {}
        for b, (a, z) in self.tramos.items():
            k = 0
            while a + k * FPS + 15 < z or k == 0:
                out[f"e{b:02d}-{k:02d}"] = min(a + k * FPS + 15 if a + 15 < z else (a + z) // 2,
                                                ultimo)
                k += 1
        return out

    def beat(self, frame: int):
        return next((b for b, (a, z) in self.tramos.items() if a <= frame < z), None)

    def _ahi(self, frame: int) -> dict:
        return {k: [e for e in v if _cuando(e)[0] - MARGEN <= frame < _cuando(e)[1] + MARGEN]
                for k, v in self.temporales.items()}

    def _visto(self, frame: int):
        """Lo que se ve en ese fotograma, contado desde el inicio de su escena."""
        b = self.beat(frame)
        if b is None:
            return [frame, self._ahi(frame)]
        base = self.tramos[b][0]
        ahi = {k: [_corre(e, base) for e in v] for k, v in self._ahi(frame).items()}
        cortes = [c - base for c in self.cortes if abs(c - frame) <= MARGEN]
        return [b, frame - base, ahi, cortes, [d for d in self.edl if d.get("beat") == b]]

    def huella(self, frame: int) -> str:
        """Lo que se ve en ese fotograma: lo fijo y lo que está en pantalla."""
        return _h([self.fijo, *self._visto(frame)])

    def contenido(self, frame: int) -> str:
        """Lo que ese segundo dice y enseña, sin el código que lo dibuja (C-728).

        Es lo que Jaime aprueba. Un arreglo de la máquina —el empuje de C-727—
        cambia cómo se dibuja, no qué hay, y no le quita la aprobación.
        """
        return _h([self.del_spec, *self._visto(frame)])


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
