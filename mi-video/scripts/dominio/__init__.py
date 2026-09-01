"""El dominio: los sustantivos de este proyecto, cada uno dueño de su verdad.

**Por qué existe este paquete.** Medido el 1 de septiembre: 22.506 líneas, 447
funciones sueltas, 23 clases — el **5 %** del código en objetos. Y las averías
no estaban repartidas al azar: estaban donde el dato del dominio viaja desnudo.

Jaime lo dijo así, y ordena todo lo demás: *«el problema es básicamente que no
hay una estructura, no hay una disciplina de código»*, *«hacer que todas las
agujas apunten al mismo lugar a través de la programación orientada a
objetos»*.

**La regla que hace que esto no vuelva a pasar:** un dato del dominio no viaja
como lista, `dict` ni tupla. Viaja como objeto, y el objeto sabe validarse. Un
`[desde, hasta]` que a veces trae un tercer elemento es una discrepancia
esperando; un `Tramo` que siempre sabe de qué cinta es, no.
"""
from .cinta import Cinta, CintaIncompleta
from .palabra import Palabra
from .tramo import Tramo, TramoInvalido

__all__ = ["Cinta", "CintaIncompleta", "Palabra", "Tramo", "TramoInvalido"]
