"""Lo que sobra de una ventana ya elegida: extremos, repetición y costura.

**Las tres reglas de no-redundancia (C-58)**, y en este orden por un motivo: se
poda dentro antes de mirar la costura, porque podar cambia dónde empieza la
ventana; y los extremos se recortan al final, cuando ya no se mueven.

1. `dentro()`   — lo dicho dos veces **dentro** de la misma ventana.
2. `costura()`  — lo que se repite **cruzando el corte**: cola de una, cabeza de
   la siguiente. Aprendizaje 31, trece casos en los seis reels montados.
3. `una_sola_vez()` — el mismo dato declarado en **dos etapas** distintas. Ésta
   no recorta: avisa con el sitio, porque cuál de las dos sobra depende del
   argumento y ésa no es una decisión del script (aprendizaje 13).

**Por qué es un objeto.** Las tres recibían la lista de palabras de la cinta por
parámetro, y las tres la volvían a filtrar con la misma expresión escrita a mano
—`a - 0.01 <= w["start"] and w["end"] <= b + 0.01`, cuatro copias—. Ahora la
vara vive en `Ventana.dentro()` y las tijeras saben de qué cinta son sus
palabras: pasarles las de otra grabación deja de ser posible.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402

from . import pesos  # noqa: E402
from ..idioma import Idioma  # noqa: E402
from ..tramo import TramoInvalido  # noqa: E402
from .ventana import Ventana  # noqa: E402


def _cabeza(w) -> str:
    return (beats.palabras(w.texto) or [""])[0]


def _contenido(ws) -> list[tuple]:
    """`(índice en ws, primera palabra de contenido)`, sólo de las que aportan."""
    return [(i, n[0]) for i, n in
            ((i, beats.norm(w.texto)) for i, w in enumerate(ws)) if n]


class Tijeras:
    """Las tijeras de UNA cinta: saben de qué palabras hablan."""

    def __init__(self, palabras):
        self.palabras = palabras

    # ── 1. los extremos ──────────────────────────────────────────────────────
    def extremos(self, v: Ventana) -> Ventana:
        """Quita del extremo lo que cuelga, con los tiempos de palabra.

        Un extremo que parte una unidad sintáctica no descalifica la ventana: se
        recorta, que es lo que haría un montador. «...preguntado al contador
        **por**» cierra en «contador».

        Se recorta por palabra y no por tramo a propósito: el tramo es la pausa
        medida y aquí hay que entrar por dentro. El corte cae en silencio de
        todos modos porque el montaje funde 50 ms por escena.

        **La cola sí, la cabeza casi no.** Detrás de una palabra de función la
        frase no ha acabado, siempre. Pero una frase **puede empezar** por «y»,
        «si», «no» o «usted»: recortando la cabeza por la misma regla, «y si
        usted no sabe qué pedir» se quedó en «sabe qué pedir» y perdió la
        condición entera. Así que por delante sólo se quita el resto de la idea
        anterior —el fragmento cortado.
        """
        ws = v.dentro(self.palabras)
        if len(ws) <= pesos.SUELO_PALABRAS:
            return v
        ini, fin = 0, len(ws)
        colgantes = Idioma.de_cinta(v.toma).colgantes
        while (fin - ini > pesos.SUELO_PALABRAS
               and _cabeza(ws[fin - 1]) in colgantes):
            fin -= 1
        while fin - ini > pesos.SUELO_PALABRAS and (
                not _cabeza(ws[ini]) or ws[ini].texto.strip().endswith("...")):
            ini += 1
        if ini == 0 and fin == len(ws):
            return v
        return self._recorte(v, max(v.a, ws[ini].empieza - pesos.ATAQUE),
                             min(v.b, ws[fin - 1].acaba + pesos.CAIDA),
                             ws[ini:fin]) or v

    # ── 2. lo dicho dos veces dentro ─────────────────────────────────────────
    def dentro(self, v: Ventana, parrafo: str = "", exige=()) -> Ventana:
        """Lo dicho dos veces dentro de la ventana: se queda la ÚLTIMA.

        Regla de Jaime, dicha varias veces y siempre igual: *«repites demasiadas
        veces 21 dólares»*, *«el libreto marca una sola no dos»*. Y la razón de
        quedarse con la última es cómo graba: repite hasta que sale, así que
        **la buena suele ser la de después** (aprendizaje 25).

        Se corta sólo cuando el trigrama de contenido es **idéntico**. Eso es un
        reintento, no una figura: la anáfora que sí vale —«de cada 100 dólares
        que él recibe… de cada 100 dólares que usted recibe»— cambia una palabra
        de contenido, y por eso no la toca (aprendizaje 13).

        **La poda limpia, no elige.** Jaime dice «30.000 dólares» siete veces
        dentro de una misma tirada, así que quedarse con la última aparición
        tiraba la frase buena y dejaba el tropiezo. La diferencia entre el
        reintento y la insistencia no está en el trigrama: está en si lo que
        queda **sigue diciendo la etapa**. Se prueban las dos formas —quedarse
        con la última y quedarse con la primera— y gana la que no empeore; si
        ninguna vale, no se toca.
        """
        ws = v.dentro(self.palabras)
        if len(ws) < pesos.SUELO_PODA:
            return v
        cont = _contenido(ws)
        for n in (4, 3):
            for x in range(len(cont) - 2 * n + 1):
                g1 = [c[1] for c in cont[x:x + n]]
                for y in range(x + n, len(cont) - n + 1):
                    if [c[1] for c in cont[y:y + n]] != g1:
                        continue
                    corte = cont[y][0]
                    if (corte < pesos.POR_DELANTE
                            or len(ws) - corte < pesos.POR_DETRAS):
                        continue
                    ultimo = cont[y - 1][0]
                    for cand in (self._recorte(v, ws[corte].empieza - pesos.ATAQUE,
                                               v.b, ws[corte:]),
                                 self._recorte(v, v.a,
                                               ws[ultimo].acaba + pesos.CAIDA,
                                               ws[:ultimo + 1])):
                        if cand is not None and (
                                not parrafo
                                or self._sigue_diciendo(cand, v, parrafo, exige)):
                            return self.dentro(cand, parrafo, exige)
        return v

    # ── 3. lo que se repite cruzando el corte ────────────────────────────────
    def costura(self, cola: str, v: Ventana) -> Ventana:
        """La repetición que cruza el corte: cola de una, cabeza de la siguiente.

        Aprendizaje 31 —*«las repeticiones que sobreviven cruzan el corte»*—:
        cada ventana está limpia por su cuenta y juntas dicen «eso no es mala
        suerte, eso no es mala suerte». Se quita de la SEGUNDA, que es donde
        sobra: la primera ya cerró su idea.
        """
        ws = v.dentro(self.palabras)
        fin = beats.norm(cola)[-pesos.COLA:]
        cabeza = _contenido(ws)[:pesos.COLA]
        corte = 0
        for n in range(min(len(fin), len(cabeza)), 0, -1):
            if fin[-n:] == [c[1] for c in cabeza[:n]]:
                corte = cabeza[n - 1][0] + 1
                break
        if not corte or len(ws) - corte < pesos.POR_DETRAS:
            return v
        return self._recorte(v, ws[corte].empieza - pesos.ATAQUE, v.b,
                             ws[corte:]) or v

    # ── lo de dentro ─────────────────────────────────────────────────────────
    @staticmethod
    def _recorte(v: Ventana, desde: float, hasta: float, ws) -> Ventana | None:
        """La misma ventana con otros extremos, o `None` si el recorte la anula.

        Un recorte que deja el final antes del principio no es un recorte: es un
        error de cuenta, y el `Tramo` lo dice en vez de dejarlo pasar.
        """
        try:
            return v.movida(desde, hasta,
                            texto=" ".join(w.texto for w in ws).strip())
        except TramoInvalido:
            return None

    @staticmethod
    def _sigue_diciendo(nuevo: Ventana, viejo: Ventana, parrafo: str, exige) -> bool:
        """¿Sigue diciendo la etapa después de podar?"""
        def val(v):
            c = float(beats.puntua(
                parrafo, {"texto": v.texto, "clave": set(beats.norm(v.texto))}))
            d = all(beats.dice(v.texto, t) for t in exige) if exige else True
            return (1 if d else 0, c)
        return val(nuevo) >= val(viejo)


def una_sola_vez(plan, ventanas, frame) -> list[tuple]:
    """Cada dato declarado se dice UNA vez en la pieza.

    *«El libreto marca una sola no dos.»* La cadena impide que dos etapas usen
    el mismo trozo de cinta, pero no que el mismo dato —21 dólares, 1.890.000—
    aparezca en dos trozos distintos. Esto no recorta: **avisa con el sitio**.
    """
    fuera: list[tuple] = []
    for s0, _k in enumerate(plan):
        exige = (frame["beats"][s0].get("debe_decir") or []
                 if s0 < len(frame["beats"]) else [])
        for t in exige or []:
            donde = [(o + 1, ventanas[j].a) for o, j in enumerate(plan)
                     if j is not None and beats.dice(ventanas[j].texto, t)]
            if len(donde) > 1 and not any(t == x[0] for x in fuera):
                fuera.append((t, s0 + 1, donde))
    return fuera
