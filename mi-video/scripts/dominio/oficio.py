"""El oficio que contesta un pedido: quién es, dónde está y cómo se le llama.

Un oficio viajaba como `(paso, ruta)` y su nombre como entrada de un `dict`, que
es exactamente el dato desnudo que este proyecto paga caro: quien lo recibe tiene
que saber que el primero es el buzón y el segundo el pedido, y derivar de ahí la
ruta de la respuesta por su cuenta. Aquí lo sabe el objeto.

## Varios a la vez, que no es un detalle de rendimiento

Jaime, 7-9-2026: *«podemos lanzar varios agentes a la vez, no tenemos que hacer
fila, es una arquitectura por servicios»*. Nada aquí serializa: un `Oficio` es de
su pieza, se le llama y contesta. El único turno de la casa lo reparte
`planificador.permiso`, y sólo a los pasos que reescriben una cinta — los de IA
no la tocan, así que pasan sin candado.

## Y la credencial es la de quien lanza

`claude --agent` usa la credencial de la terminal que lo arranca: desde un shell
abierto dentro de una sesión dice `Not logged in` y no contesta. Eso no es un
fallo que haya que tapar — el pedido se queda escrito y abierto, que es el lado
seguro y ya es lo que hace `servicio.pedir` cuando el CLI no está.
"""
from __future__ import annotations

import os
import subprocess

#: Qué oficio contesta cada buzón. Los nombres son los de `.claude/agents/`, y un
#: buzón sin oficio declarado no se llama: existe y lo contesta quien pueda, que
#: es el caso honesto mientras ese agente no esté escrito.
DE = {"describir": "compositor", "disenar": "disenador", "visto": "disenador"}

#: El encargo es siempre el mismo texto. Lo que hay que contestar viaja DENTRO
#: del pedido —`prompt` es su contrato— y esto sólo dice qué fichero leer y en
#: cuál escribir. Improvisar aquí sería un segundo contrato.
ENCARGO = (
    "Tu turno. Lee entero el pedido {pedido} —`prompt` es tu contrato completo y"
    " `datos` el encargo— y escribe tu respuesta en {respuesta}, con la forma que"
    " ese `prompt` define. Si el pedido no basta para contestar, se dice en la"
    " respuesta; no se va a buscar fuera."
)


class Oficio:
    """Quien sabe contestar el pedido que una pieza dejó abierto."""

    def __init__(self, nombre: str, buzon: str, pedido: str):
        self.nombre = nombre
        self.buzon = buzon
        self.pedido = pedido.replace("\\", "/")

    @classmethod
    def de(cls, slug: str):
        """El oficio que esa pieza está esperando, o `None` si no espera a nadie.

        La cola sale de `servicio.pendientes`, que es la del servicio y ya
        existía, acotada a una pieza: la que acaba de moverse es la única sobre
        la que hay algo nuevo que decir.
        """
        try:
            import sys

            raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if raiz not in sys.path:
                sys.path.insert(0, raiz)
            import servicio

            for buzon, quien, ruta in servicio.pendientes():
                if quien == slug and DE.get(buzon):
                    return cls(DE[buzon], buzon, ruta)
        except Exception:                          # noqa: BLE001
            return None
        return None

    @property
    def respuesta(self) -> str:
        """Dónde tiene que dejar su respuesta. La deriva del pedido, no se pasa."""
        return self.pedido.replace(".pedido.json", ".respuesta.json")

    @property
    def huella(self) -> tuple:
        """La pregunta concreta que se le hizo: su pedido y cuándo se escribió.

        Es lo que distingue «no ha contestado todavía» de «hay algo nuevo que
        preguntarle». Con el motor puesto, llamarle otra vez por el mismo
        fichero es despertarle para que conteste lo mismo — el coste que hizo
        retirar la patrulla.
        """
        try:
            return (self.pedido, int(os.path.getmtime(self.pedido)))
        except OSError:
            return (self.pedido, 0)

    def contesto(self) -> bool:
        return os.path.exists(self.respuesta)

    def llama(self) -> bool:
        """Lo llama y espera. Cierto si dejó su respuesta al lado."""
        subprocess.run(["claude", "--agent", self.nombre, "-p",
                        ENCARGO.format(pedido=self.pedido,
                                       respuesta=self.respuesta)],
                       check=False)
        return self.contesto()

    def __str__(self) -> str:
        return f"{self.nombre} ({self.buzon})"
