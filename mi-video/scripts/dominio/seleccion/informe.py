"""Lo que la selección cuenta por pantalla, y lo que deja en el registro.

**un informe largo hace que se pierda lo importante**. Así que
esto imprime lo que hay que decidir —una etapa que se va a tablero, un dato que
el recorte se llevó, un dato repetido— y el reparto, y nada más.

Lo que además hay que poder discutir mañana no se imprime: se **anota**. Un
aviso que sólo sale por pantalla se pierde con la terminal.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import registro  # noqa: E402

from .reparto import con_toma  # noqa: E402


class Informe:
    """Cuenta una corrida. No decide nada: lee lo que la corrida ya decidió."""

    def __init__(self, corrida):
        self.c = corrida

    def cabecera(self) -> None:
        c = self.c
        print(f"{c.slug} · {c.toma}: {len(c.corpus.habla(c.toma))} tramos"
              f" → {len(c.ventanas)} ventanas candidatas")

    def escalera(self, tramos, afinados: int) -> None:
        largo = sum(b - a for a, b in tramos)
        print(f"escalera: {len(tramos)} tramos ({largo:.0f}s de cinta) a afinar"
              f" con el modelo bueno, de {len(self.c.ventanas)} ventanas")
        print(f"  {afinados} tramos afinados -> vuelvo a repartir de cero")

    def handicap(self, rotas, paso: float) -> None:
        if rotas:
            print(f"  {len(rotas)} toma(s) con handicap por mensaje roto"
                  f" (-{paso} st, no eliminadas)")

    def voz(self, cambios) -> None:
        for etapa, antes, ahora in cambios:
            print(f"  la voz cambia la etapa {etapa}:"
                  f" {antes or 0:.2f} -> {ahora or 0:.2f} st")

    def reparto(self, total: float) -> None:
        print(f"reparto: {len(con_toma(self.c.plan))}/{len(self.c.libreto)}"
              f" etapas con toma · puntuacion {total:.2f}")

    def tableros(self, movidas) -> None:
        for etapa, lit, voz, txt in movidas:
            print(f"  A TABLERO: etapa {etapa} — lee el libreto al {lit:.0%} y lo"
                  f" entrega plano ({voz:.1f} st). Su texto es el copy del tablero.")
            print(f"      «{txt[:110]}»")
            registro.nota("seleccionar", "lectura plana a tablero",
                          detalle=f"{self.c.slug} etapa {etapa}:"
                                  f" literal {lit:.2f}, voz {voz:.1f}")

    def perdidos(self, perdidos) -> None:
        for etapa, exige in perdidos:
            print(f"  OJO: la etapa {etapa} exige {exige} y el recorte se lo llevo")
            registro.aviso("seleccionar", "el recorte se llevo el dato exigido",
                           detalle=f"{self.c.slug} etapa {etapa}: {exige}",
                           eco=False)

    def repetidos(self, repes) -> None:
        for t, _etapa, donde in repes:
            sitios = ", ".join(f"etapa {o} ({a:.1f}s)" for o, a in donde)
            print(f"  REDUNDANTE: «{t}» se dice en {len(donde)} sitios — {sitios}")
            registro.aviso("seleccionar", "dato repetido en la pieza",
                           detalle=f"{self.c.slug} «{t}»: {sitios}", eco=False)

    def etapas(self, todo: bool = False) -> None:
        """El reparto etapa por etapa, y con `todo` los finalistas de cada una."""
        c = self.c
        print()
        for s0, k in enumerate(c.plan):
            exige = c.exige(s0)
            cab = (f"{s0 + 1}. {c.beat(s0).get('etapa') or ''}"
                   + (f"  [exige {', '.join(exige)}]" if exige else ""))
            if k is None:
                print(f"{cab}\n    SIN TOMA → tarjeta\n")
                continue
            v = c.ventanas[k]
            cubre, dice = v.det.get(s0, (0.0, 0))
            print(f"{cab}\n    {v.a:7.2f}-{v.b:7.2f}  voz {v.voz:5.1f}s"
                  f"  aire {v.aire:4.1f}s  cubre {cubre:.2f}"
                  f"{'  DICE' if dice else ''}")
            print(f"    {v.texto[:220]}\n")
            if todo:
                self._finalistas(s0)

    def _finalistas(self, s0: int) -> None:
        fila = self.c.marcas[s0]
        top = sorted((x for x in range(len(fila)) if fila[x] is not None),
                     key=lambda x: -fila[x])[:5]
        for x in top:
            w = self.c.ventanas[x]
            print(f"      {fila[x]:+.2f}  {w.a:7.2f}-{w.b:7.2f}  {w.texto[:110]}")
        print()
