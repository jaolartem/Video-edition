"""El registro de servicios: qué objeto mueve cada fase.

El motor no conoce ningún script. Le pregunta a esto qué servicio corresponde a
una fase y le manda una `Pieza`. Añadir un paso es registrar un objeto; cambiar
cómo se hace un paso es cambiar una clase, no tocar el motor.

**Y la tabla `fase` sigue mandando en el ORDEN.** Aquí sólo vive el «cómo»: el
«cuándo» es un dato, como quedó cuando la línea dejó de ser una secuencia. Si una
fase no tiene servicio registrado, se cae a `ServicioScript` con lo que diga la
tabla — así los pasos que aún no se han envuelto siguen funcionando y la
migración es gradual, que es la única manera de no rehacer la máquina.
"""
from .base import Espera, Pieza, Resultado, Servicio, ServicioScript  # noqa: F401
from .redundancia import ServicioRedundancia
from .verificar import ServicioVerificar

# Los que ya son objetos. El resto entra por `ServicioScript` con la plantilla
# que diga la tabla `fase`.
REGISTRO: dict[str, Servicio] = {
    "sin_redundancia": ServicioRedundancia(),
    "verificado": ServicioVerificar(),
    "aprobado": Espera("aprobado"),
}


def para(fase_nombre: str, plantilla: str | None) -> Servicio | None:
    """El servicio de una fase: el objeto si lo hay, si no el script envuelto."""
    if fase_nombre in REGISTRO:
        return REGISTRO[fase_nombre]
    if plantilla:
        return ServicioScript(fase_nombre, plantilla)
    return None
