"""El montaje **mientras se construye**: qué etapa tiene ya su trozo de cinta.

No confundir con `dominio.montaje.Montaje`, que es su hermano de después: aquél
lee `ads/<slug>/edl-sell.json` y contesta qué se montó; éste es lo que se lleva
armado cuando todavía no hay EDL. Dos momentos del mismo sustantivo, y mezclarlos
sería preguntarle a un fichero que aún no existe.

**Por qué es un objeto.** Era `usados` y `elegidos`, dos listas paralelas que
`montar()` iba rellenando en cinco sitios distintos, más un `total` que se
calculaba dos veces con dos fórmulas distintas —una sobre las unidades y otra
sobre los cortes— y se llamaban igual. Y la regla que las une, *«una etapa
cumplida cierra su idea»*, vivía como una comprensión de lista en medio del
bucle: quien añadía un caso nuevo tenía que acordarse de tocar las dos listas.

Aquí se añade por una sola puerta —`pon`— y la regla la contesta el objeto.
"""
from __future__ import annotations

import sys

from .candidata import IGUAL, parecido
from .poda import podar


def _di(msg: str) -> None:
    print(msg, file=sys.stderr)


class Armado:
    """Las etapas que ya tienen toma, en el orden en que se fueron cerrando."""

    def __init__(self, etapas, toma: str):
        #: Las etapas del frame, para poder preguntar qué exige cada una.
        self.etapas = list(etapas)
        self.toma = toma
        #: Las unidades tal cual, para saber qué trozo de cinta ya está gastado.
        self.usados: list = []
        #: Lo que sale de aquí: una entrada por etapa cumplida.
        self.elegidos: list = []

    # ── qué queda por repartir ───────────────────────────────────────────────
    def libres(self, cands) -> list:
        """Las unidades que todavía pueden competir.

        **Una etapa cumplida cierra su idea.** Dos filtros, y hacen falta los
        dos: el de tiempo quita el mismo trozo de cinta, el de contenido quita el
        mismo intento dicho en otro momento. Sin el segundo, cuatro intentos de
        una idea entraban bajo cuatro etapas distintas — es literalmente lo que
        pasó en el reel 1, donde la pieza decía la misma tesis cuatro veces con
        otras palabras y el detector de repetición no la veía porque compara
        n-gramas.
        """
        return [u for u in cands
                if not any(min(u["b"], v["b"]) - max(u["a"], v["a"]) > 0.2
                           for v in self.usados)
                and not any(parecido(u, v) > IGUAL for v in self.usados)]

    @property
    def ultimo(self) -> float:
        """Dónde acaba lo último que entró. Jaime graba en orden, y desempata."""
        return max((u["b"] for u in self.elegidos), default=0.0)

    def tiene(self, n: int) -> bool:
        return any(u["beat"] == n for u in self.elegidos)

    # ── la única puerta de entrada ───────────────────────────────────────────
    def pon(self, etapa, u, cubre=1.0, voz=None) -> dict:
        """Da por cumplida una etapa con esa unidad.

        `voz` a `None` significa **no medida**, y no es lo mismo que plana: una
        etapa aprobada de oído o un cierre declarado no los ha medido nadie, y
        decir «0,0 st» de ellos es informar de una entrega que nadie ha oído.
        """
        self.usados.append(u)
        puesta = {**u, "beat": etapa.n, "etapa": etapa.nombre,
                  "obligatorio": etapa.obligatoria, "score": cubre, "voz": voz}
        self.elegidos.append(puesta)
        return puesta

    def declara(self, etapa, u, cubre=1.0, voz=None, delante=False) -> dict:
        """Da por cumplida una etapa con un tramo **declarado de oído**.

        No gasta candidata —el tramo no salió del concurso, así que no hay nada
        que cerrar— y puede entrar por delante: la apertura declarada **es** el
        primer beat, y si se añadiera al final el listado la contaría fuera de
        orden.
        """
        puesta = {**u, "beat": etapa.n, "etapa": etapa.nombre,
                  "obligatorio": etapa.obligatoria, "score": cubre, "voz": voz}
        if delante:
            self.elegidos.insert(0, puesta)
        else:
            self.elegidos.append(puesta)
        return puesta

    # ── lo que se limpia encima, sin elegir nada ─────────────────────────────
    def recorta(self, ajustes) -> None:
        """Aplica los recortes finos de entrada y salida declarados por etapa.

        Recortar por dónde entra una frase es ejecución, no mensaje: no se
        consulta, se declara y se aplica. De dónde salen los declara
        `dominio.decidido.Decidido.ajustes` — el frame y la base, por la misma
        puerta.
        """
        for u in self.elegidos:
            d = ajustes.get(f"beat_{u['beat']}_entra_en")
            if d is not None and u["a"] < d < u["b"]:
                u["a"] = d
            h = ajustes.get(f"beat_{u['beat']}_sale_en")
            if h is not None and u["a"] < h < u["b"]:
                u["b"] = h

    def poda(self) -> None:
        """Quita de cada unidad lo que ya dijo dentro de sí misma.

        **Va aquí, sobre lo ya elegido**, y no antes: cada unidad pierde sus
        repeticiones internas —y sobre todo sus autocorrecciones, que son
        información contradictoria en pantalla— cuando ya se sabe con qué
        recorte se queda. La regla vive en `dominio.poda`.
        """
        for u in self.elegidos:
            i = u["beat"] - 1
            exige = self.etapas[i].debe_decir if i < len(self.etapas) else []
            r = podar(u, exige)
            if not r:
                continue
            tramos, quitado, que = r
            u["tramos"] = (u["tramos"][:-1] + tramos) if u.get("tramos") else tramos
            _di(f"  beat {u['beat']}: podadas repeticiones ({quitado}s) — "
                f"«{que[:70]}»")

    # ── lo que sale ──────────────────────────────────────────────────────────
    def segs(self) -> list:
        """Los cortes, en orden de libreto.

        Una unidad puede traer varios tramos: son frases seguidas de la misma
        toma con la cola redundante fuera (ver `poda.unir`), o lo que dejó la
        poda. Si no trae ninguno, el corte es la unidad entera.
        """
        return [t for u in self.elegidos
                for t in (u.get("tramos") or [[round(u["a"], 3), round(u["b"], 3)]])]

    @property
    def duracion(self) -> float:
        """Lo que suman las unidades elegidas, **antes** de cortar por tramos."""
        return sum(u["b"] - u["a"] for u in self.elegidos)

    def __str__(self) -> str:
        return (f"armado de {self.toma}: {len(self.elegidos)}/{len(self.etapas)}"
                f" etapas, {self.duracion:.1f}s")
