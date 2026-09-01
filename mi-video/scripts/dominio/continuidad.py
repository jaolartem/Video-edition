"""¿El mensaje sobrevive a los cortes? Contar y juzgar, en el mismo sitio.

**La fragmentación no es un criterio: es una consecuencia.** Regla de Jaime: *«el
criterio no es temporal, el criterio es emocional; la mejor es la que más
comunique, no la que menos cortes tenga — pero si los cortes rompen la
continuidad del mensaje y queda todo fraccionado, la fuerza comunicativa se
pierde»*.

Contar cortes premiaba a la toma tibia: la entregada con más voz trae más falsos
arranques y por tanto más costuras, así que **descartaba justo lo que hay que
quedarse**. Se comprobó en reel-01: descartar las dos mejores dejó la etapa 2
peor de lo que estaba (7 trozos/24 s → 8 trozos/25 s).

Lo que sí rompe son dos cosas **a la vez**, tal y como él las dijo: que la
costura salte idea, y que lo que quede sean esquirlas. Quitar aire entre dos
frases no rompe nada — ahí ya había una frontera y el corte sólo la usa.

**Y por qué el juicio vive aquí.** La cuenta estaba en una función y el veredicto
—`rotas/costuras > FRACTURA and esquirlas/trozos > FRACTURA`— escrito a mano en
el bucle de quien llamaba. Una regla partida en dos: la mitad de arriba se puede
cambiar sin que la de abajo se entere, y entonces hay dos definiciones de
«mensaje roto» y las dos parecen correctas.
"""
from __future__ import annotations

from .depuracion import enteras_en

#: Lo que puede saltar una costura sin que el que escucha aterrice en otro sitio.
SALTO_MAX = 0.8
#: Por debajo de esto un trozo no da para una idea: es una esquirla.
TROZO_IDEA = 1.2
#: Y por encima de qué fracción de cada cosa se declara fracturada. La mitad, en
#: las dos: menos que eso es una toma con una costura fea, no un mensaje roto.
FRACTURA = 0.5


class Continuidad:
    """Cuánto de lo que se cortó respeta la frontera que ya había.

    Una costura es **limpia** cuando lo que se llevó era silencio: ahí el
    hablante ya había cerrado y el corte sólo usa esa frontera. Es **rota**
    cuando se llevó palabras y más de `SALTO_MAX` segundos.
    """

    __slots__ = ("rotas", "costuras", "esquirlas", "trozos")

    def __init__(self, palabras, trozos):
        self.rotas = self.costuras = 0
        for (_, y0), (x1, _) in zip(trozos, trozos[1:]):
            self.costuras += 1
            if enteras_en(palabras, y0, x1, margen=0.0) and (x1 - y0) > SALTO_MAX:
                self.rotas += 1
        self.esquirlas = sum(1 for x, y in trozos if y - x < TROZO_IDEA)
        self.trozos = len(trozos)

    @property
    def rota(self) -> bool:
        """El mensaje queda roto: salta idea **y** lo que queda son esquirlas."""
        return bool(self.costuras
                    and self.rotas / self.costuras > FRACTURA
                    and self.esquirlas / max(self.trozos, 1) > FRACTURA)

    @property
    def motivo(self) -> str:
        """Por qué, con los números delante. Es lo que se guarda en `descartado`."""
        return (f"mensaje roto: {self.rotas}/{self.costuras} costuras saltan"
                f" idea, {self.esquirlas}/{self.trozos} trozos por debajo de"
                f" {TROZO_IDEA}s")

    def cuenta(self) -> tuple:
        """`(rotas, costuras, esquirlas)`, para quien ya preguntaba así."""
        return self.rotas, self.costuras, self.esquirlas

    def __str__(self) -> str:
        return (f"{self.rotas}/{self.costuras} costuras rotas ·"
                f" {self.esquirlas}/{self.trozos} esquirlas")
