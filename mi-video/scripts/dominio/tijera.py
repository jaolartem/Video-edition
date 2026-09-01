"""Lo único que cambia un montaje ya hecho, y lo deja consistente.

**Por qué es un objeto.** Nueve pasos de `costuras.py` abrían
`ads/<slug>/edl-sell.json`, movían un número y lo volvían a escribir, cada uno
con su copia del mismo bucle. Y las copias no eran iguales — nunca lo son:

- **Dos no recalculaban `duracion_s`.** Medido hoy sobre las siete piezas, la
  duración declarada miente en seis: reel-02 dice 113,62 s y sus trozos suman
  84,77 (−28,8 s), reel-06 dice 82,0 y suma 93,9 (+11,9). Es el campo por el que
  se pregunta cuánto dura una pieza sin abrirla.
- **Seis movían el segmento y dejaban el `detalle` donde estaba**, aunque cada
  fila lleva su propio `start` y `end`. En reel-01 hay 9 de 21 trozos con los
  dos números diciendo cosas distintas del mismo corte. Dos copias de la misma
  verdad, y las dos parecen correctas — que es exactamente lo que `verdad.py`
  existe para impedir.

Aquí el corte se mueve por un solo sitio, y ese sitio se encarga de que lo demás
cuadre. `Montaje` contesta lo que el montaje es; la tijera es lo que lo cambia.
"""
from __future__ import annotations

import json

from .montaje import Montaje
from .tramo import Tramo


class Tijera:
    """El montaje de `slug`, abierto para cambiarlo.

    Nada se escribe hasta `guardar()`, y `guardar()` no hace nada si no se movió
    nada: un paso que corre en seco no puede tocar el fichero por descuido.
    """

    __slots__ = ("m", "_sucio")

    def __init__(self, slug):
        self.m = Montaje(slug)
        self._sucio = False

    # ── lo que hay ──────────────────────────────────────────────────────────
    @property
    def slug(self) -> str:
        return self.m.slug

    @property
    def existe(self) -> bool:
        return self.m.existe

    def __len__(self) -> int:
        return len(self.m.edl.get("segmentos") or [])

    def tramo(self, i: int) -> Tramo:
        return Tramo.de_lista(self.m.edl["segmentos"][i],
                              self.m.edl["detalle"][i].get("toma") or "")

    def detalle(self, i: int) -> dict:
        return self.m.edl["detalle"][i]

    def beat(self, i: int):
        return self.detalle(i).get("beat")

    def fijado(self, i: int) -> bool:
        return bool(self.detalle(i).get("fijado"))

    # ── lo que se puede cambiar ─────────────────────────────────────────────
    def mover(self, i: int, nuevo: Tramo) -> bool:
        """El trozo `i` pasa a ser `nuevo`. **Y su detalle se mueve con él.**"""
        viejo = self.tramo(i)
        if abs(nuevo.desde - viejo.desde) < 1e-9 and abs(nuevo.hasta - viejo.hasta) < 1e-9:
            return False
        self.m.edl["segmentos"][i] = [nuevo.desde, nuevo.hasta]
        self.m.edl["detalle"][i] = {**self.detalle(i),
                                    "start": nuevo.desde, "end": nuevo.hasta}
        self._sucio = True
        return True

    def quitar(self, indices) -> int:
        """Fuera esos trozos, con su detalle."""
        fuera = set(indices)
        if not fuera:
            return 0
        edl = self.m.edl
        for clave in ("segmentos", "detalle"):
            edl[clave] = [x for k, x in enumerate(edl[clave]) if k not in fuera]
        self._sucio = True
        return len(fuera)

    def rehacer(self, trozos) -> None:
        """Reescribe la lista entera con `[(Tramo, detalle), …]`.

        Para quien parte un trozo en varios: quitar el aire muerto de dentro de
        un segmento no lo acorta, lo **divide**, y entonces no hay un índice que
        mover sino una lista nueva.
        """
        edl = self.m.edl
        edl["segmentos"] = [[t.desde, t.hasta] for t, _ in trozos]
        edl["detalle"] = [{**d, "start": t.desde, "end": t.hasta}
                          for t, d in trozos]
        edl["fuentes"] = [d.get("toma") or "" for _, d in trozos]
        self._sucio = True

    def anotar(self, clave: str, valor) -> None:
        """Deja escrito en el montaje algo que no es un corte."""
        if valor is None:
            self.m.edl.pop(clave, None)
        else:
            self.m.edl[clave] = valor
        self._sucio = True

    # ── y se escribe ────────────────────────────────────────────────────────
    def guardar(self) -> bool:
        """**La duración se recalcula siempre**: es la suma de los trozos.

        No es un adorno del fichero. Es lo que lee quien pregunta cuánto dura
        una pieza sin abrirla, y dejarla al criterio de cada paso es cómo llegó
        a mentir en seis de las siete.
        """
        if not self._sucio:
            return False
        edl = self.m.edl
        edl["duracion_s"] = round(
            sum(float(b) - float(a) for a, b in
                (s[:2] for s in edl.get("segmentos") or [])), 2)
        with open(self.m.pieza.ruta_edl, "w", encoding="utf-8") as f:
            json.dump(edl, f, ensure_ascii=False, indent=1)
        self._sucio = False
        return True

    def __str__(self) -> str:
        return f"tijera sobre {self.slug} ({len(self)} trozos)"
