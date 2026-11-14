"""Quién se queda con qué trozo de cinta, y la última palabra de Jaime.

En orden de cinta y sin solaparse, maximizando el total: es la programación
dinámica de `en_orden()`. Eso respeta *«casi siempre secuencial»* sin imponer
que lo sea —una etapa puede quedarse vacía si su mejor ventana vale menos que lo
que le quita a las demás—, y hace **imposible por construcción** que dos etapas
usen el mismo trozo de cinta, que es de donde salía «repites demasiadas veces 21
dólares».

Y lo que la programación dinámica no puede ver —la misma frase dicha en dos
puntos distintos de la cinta— lo quita `sin_repetir()`, que vuelve a repartir
prohibiendo la copia peor puntuada.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402
import estado  # noqa: E402
import registro  # noqa: E402

from . import pesos  # noqa: E402
from ..idioma import Idioma  # noqa: E402
from ..tramo import Tramo, TramoInvalido  # noqa: E402
from .ventana import Ventana  # noqa: E402


def con_toma(plan) -> list:
    """Las etapas del plan que salieron con material."""
    return [k for k in plan if k is not None]


def _dicen_lo_mismo(uno: str, otro: str, idioma=None) -> bool:
    a, b = set(beats.norm(uno, idioma)), set(beats.norm(otro, idioma))
    if not a or not b:
        return False
    return len(a & b) / min(len(a), len(b)) > pesos.IGUALES


class Reparto:
    """El reparto de las etapas de una pieza sobre las ventanas del corpus."""

    def __init__(self, marcas, ventanas, premio):
        self.marcas = marcas
        self.ventanas = ventanas
        self.premio = premio

    # ── en orden de cinta ────────────────────────────────────────────────────
    def en_orden(self, prohibidas=frozenset()) -> tuple[list, float]:
        """Reparte en orden de cinta y sin solaparse, al mayor total.

        `marcas[s][k]` es lo que vale la ventana k para la etapa s. La
        recurrencia es la de siempre —o se salta la ventana, o se toma y se
        sigue por la primera que empieza después de que ésta acabe— y su efecto
        de fondo es el que importa: **dos etapas no pueden usar el mismo trozo
        de cinta.**
        """
        vs, marcas = self.ventanas, self.marcas
        S, K = len(marcas), len(vs)
        # Para cada ventana, la primera que ya no la pisa. Dos ventanas de
        # cintas distintas no se pisan nunca: son grabaciones separadas.
        sig = [K] * K
        for k in range(K):
            for m in range(k + 1, K):
                if not vs[k].solapa(vs[m]):
                    sig[k] = m
                    break
        NADA = float("-inf")
        dp = [[NADA] * (K + 1) for _ in range(S + 1)]
        de = [[None] * (K + 1) for _ in range(S + 1)]
        for k in range(K + 1):
            dp[S][k] = 0.0
        for s in range(S - 1, -1, -1):
            dp[s][K] = dp[s + 1][K]      # sin ventana: la etapa va con tarjeta
            de[s][K] = ("salta", None)
            for k in range(K - 1, -1, -1):
                mejor, arg = dp[s][k + 1], ("otra", None)
                if dp[s + 1][K] > mejor:
                    mejor, arg = dp[s + 1][K], ("salta", None)
                if k not in prohibidas and marcas[s][k] is not None:
                    cand = marcas[s][k] + self.premio[s] + dp[s + 1][sig[k]]
                    if cand > mejor:
                        mejor, arg = cand, ("toma", k)
                dp[s][k], de[s][k] = mejor, arg
        plan, s, k = [], 0, 0
        while s < S:
            que, dato = de[s][k]
            if que == "otra":
                k += 1
                continue
            plan.append(dato)
            s += 1
            k = sig[dato] if dato is not None else K
        return plan, dp[0][0]

    # ── sin exigir orden ─────────────────────────────────────────────────────
    def libre(self, prohibidas=frozenset()) -> tuple[list, float]:
        """Reparte sin exigir orden de cinta, cuando el orden no da.

        Jaime lo dijo con todas las letras: *«no siempre secuencial pero siempre
        por etapas completas»*. La cadena impone el orden, y en el reel 2 —donde
        regrabó el argumento entero y las tomas buenas de las etapas finales
        están ANTES en la cinta— eso dejaba **3 etapas de 10 teniendo candidatas
        en siete**.

        **Las obligatorias se sirven primero.** Tomando siempre el mejor par,
        una etapa larga se come el trozo donde vive el material de la siguiente
        y ésta se queda sin nada — el reel 5 perdió su etapa 4 así. El voraz no
        reconsidera, así que la única forma de que no pase es el orden: una
        etapa obligatoria sin material rompe la estructura, y eso vale más que
        cualquier ganancia de cobertura en su vecina.
        """
        vs, marcas, premio = self.ventanas, self.marcas, self.premio
        pares = sorted(((marcas[s][k] + premio[s], s, k)
                        for s in range(len(marcas))
                        for k in range(len(vs))
                        if marcas[s][k] is not None and k not in prohibidas),
                       reverse=True)
        techo = max(premio) if premio else 0
        obl = {s for s in range(len(marcas)) if premio[s] >= techo}
        orden = ([x for x in pares if x[1] in obl]
                 + [x for x in pares if x[1] not in obl])
        plan = [None] * len(marcas)
        libres, usados = set(range(len(marcas))), []
        for _, s, k in orden:
            if s not in libres or any(vs[k].solapa(vs[u]) for u in usados):
                continue
            plan[s] = k
            usados.append(k)
            libres.discard(s)
        total = sum(marcas[s][k] + premio[s]
                    for s, k in enumerate(plan) if k is not None)
        return plan, total

    # ── y sin decir lo mismo dos veces ───────────────────────────────────────
    def sin_repetir(self, plan) -> list:
        """Quita la copia peor puntuada cuando dos etapas dicen lo mismo.

        La cadena impide usar el mismo trozo dos veces, pero no que Jaime diga
        la misma frase en dos puntos de la cinta y caigan las dos. Eso era
        «repites demasiadas veces 21 dólares», y es la parte del proceso que
        Jaime nombra aparte: *«evitamos las repeticiones»*.

        **Se prohíbe la copia, no el trozo de cinta.** Con 876 ventanas, muchas
        solapadas, tumbar un índice deja a la cadena elegir la de al lado, que
        dice exactamente lo mismo. Pero prohibir sólo la región, en el reel 2
        —donde Jaime repite mucho— arrasaba candidatas y el reparto caía de 10
        etapas a 3: se prohíbe lo que pisa a la peor **y además** dice lo mismo.
        """
        vs = self.ventanas
        for _ in range(4):
            malas, elegidas = set(), [(s, k) for s, k in enumerate(plan)
                                      if k is not None]
            for x in range(len(elegidas)):
                for y in range(x + 1, len(elegidas)):
                    (s1, k1), (s2, k2) = elegidas[x], elegidas[y]
                    if not _dicen_lo_mismo(vs[k1].texto, vs[k2].texto,
                                           Idioma.de_cinta(vs[k1].toma)):
                        continue
                    peor = k1 if self.marcas[s1][k1] < self.marcas[s2][k2] else k2
                    malas |= {z for z, w in enumerate(vs)
                              if w.solapa(vs[peor])
                              and _dicen_lo_mismo(w.texto, vs[peor].texto,
                                                 Idioma.de_cinta(w.toma))}
            if not malas:
                return plan
            nuevo, _ = self.en_orden(prohibidas=malas)
            # **Quitar una repetición no puede costar una etapa.** Si el reparto
            # nuevo cubre menos, la veda se pasó de ancha y vale más la pieza
            # completa: se avisa y se deja como estaba.
            if len(con_toma(nuevo)) < len(con_toma(plan)):
                registro.aviso("seleccionar", "veda de repeticion descartada",
                               detalle=f"habria dejado {len(con_toma(nuevo))}"
                                       f" etapas de {len(con_toma(plan))}",
                               eco=False)
                return plan
            plan = nuevo
        return plan


def manda_jaime(plan, marcas, ventanas, corpus, slug: str, toma: str) -> list:
    """Lo que Jaime ya juzgó **no se vuelve a elegir**.

    Es el aprendizaje 13 —*«las heurísticas limpian, no eligen»*— y ya se
    incumplió tres veces en una sesión: un automatismo sustituyó el arranque
    elegido de oído y hubo que re-imponerlo a mano en cada montaje.

    Los cuatro estados de `ads/estado.json`, y cada uno hace algo distinto:

    - `aprobado`  — se usa **el rango declarado**, tal cual. No se busca.
    - `recortar`  — se conserva lo elegido y se aplica `entra_en`/`sale_en`.
    - `rechazado` — la etapa va con tarjeta y **no se busca sustituto**.
    - lo demás    — lo elige el reparto.
    """
    est = estado.cargar().get("reels", {}).get(slug, {})
    if not est:
        return plan
    for clave, dec in est.items():
        try:
            s0 = int(clave) - 1
        except ValueError:
            continue
        if not (0 <= s0 < len(plan)):
            continue
        e = dec.get("estado") if isinstance(dec, dict) else dec
        if e == "rechazado":
            plan[s0] = None
            registro.nota("seleccionar", "etapa rechazada por Jaime",
                          detalle=f"{slug} etapa {clave}")
            continue
        k = plan[s0]
        if e == "aprobado" and dec.get("desde") is not None:
            a, b = float(dec["desde"]), float(dec["hasta"])
        elif e == "recortar":
            a = float(dec.get("entra_en", ventanas[k].a if k is not None else 0))
            b = float(dec.get("sale_en", ventanas[k].b if k is not None else 0))
            # **Un punto de entrada puede apuntar a otra unidad.** El `entra_en`
            # del reel 1 etapa 7 es 563,3 y la ventana que eligió el reparto
            # acaba en 539: aplicarlo tal cual daba el rango invertido
            # `563,30-539,03`, o sea cero segundos de voz y ningún aviso. Lo que
            # Jaime decidió ahí es **dónde entra**; hasta dónde llega lo decide
            # el reparto, así que se busca la mejor candidata que empiece ahí.
            if b <= a or k is None or not (ventanas[k].a <= a <= ventanas[k].b):
                # Sólo las candidatas originales tienen marca: `ventanas` crece
                # con las que se añaden aquí.
                cerca = [(marcas[s0][x], x) for x in range(len(marcas[s0]))
                         if marcas[s0][x] is not None
                         and abs(ventanas[x].a - a) < 2.0
                         and (not dec.get("sale_en") or ventanas[x].b <= b + 0.3)]
                if not cerca:
                    registro.error("seleccionar", "recorte que no cuadra",
                                   detalle=f"{slug} etapa {clave}: entra_en {a}"
                                           f" no cae en ninguna candidata")
                    continue
                k = max(cerca)[1]
                a, b = ventanas[k].a, ventanas[k].b
        else:
            continue
        try:
            tramo = Tramo(round(a, 3), round(b, 3), toma)
        except TramoInvalido as err:
            registro.error("seleccionar", "rango de Jaime imposible",
                           detalle=f"{slug} etapa {clave}: {err}")
            continue
        v = Ventana(tramo=tramo, de_jaime=e,
                    texto=(dec.get("texto")
                           or tramo.texto_de(corpus.palabras(toma))))
        ventanas.append(v.remedida(corpus.habla(toma)))
        plan[s0] = len(ventanas) - 1
        registro.nota("seleccionar", f"etapa {e} por Jaime",
                      detalle=f"{slug} etapa {clave}: {a:.2f}-{b:.2f}")
    return plan
