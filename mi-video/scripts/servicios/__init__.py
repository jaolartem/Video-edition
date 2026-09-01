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
from .disenar import ServicioDisenar
from .redundancia import ServicioRedundancia
from .repaso import ServicioRepaso
from .respaldo import ServicioRespaldo
from .revalidar import ServicioRevalidar
from .verificar import ServicioVerificar
from .revisar import ServicioRevisar
from .visto import ServicioVisto

# Los que ya son objetos. El resto entra por `ServicioScript` con la plantilla
# que diga la tabla `fase`.
REGISTRO: dict[str, Servicio] = {
    "sin_redundancia": ServicioRedundancia(),
    "repasado": ServicioRepaso(),
    "respaldado": ServicioRespaldo(),
    "disenado": ServicioDisenar(),
    "revalidado": ServicioRevalidar(),
    "verificado": ServicioVerificar(),
    "visto": ServicioVisto(),
    # El criterio humano no tiene servicio: lo mueve el mirando la pieza.
    "revisado": ServicioRevisar(),
    "aprobado": Espera("aprobado"),
}


class Recogido(Servicio):
    """Un servicio con su fallo recogido. **Todos pasan por aquí.**

    Regla de Jaime, y corrige el método antes que el código: *«todos los pasos
    con código van con try / if not para el log de errores; no puedes estar
    buscando a ojo»*.

    Buscar a ojo significa leer una traza, arreglar esa línea, volver a correr y
    encontrar la siguiente. Es lento y, peor, **sólo encuentra lo que revienta
    delante de ti**: el fallo de `redundancia` con un `NoneType` llevaba horas en
    el log de incidencias sin que nadie lo mirase, porque nadie se cayó por él.

    Envolver aquí y no en cada clase es lo que hace que no se pueda olvidar: un
    paso nuevo entra por `para()` y ya viene recogido, sin que su autor tenga que
    acordarse. Un `try` que hay que recordar poner es un `try` que falta.

    **Y no se traga el fallo.** Devuelve un `Resultado` que dice que no pudo, con
    el tipo y el mensaje dentro, para que el motor lo anote y pare esa pieza — no
    las otras seis.
    """

    def __init__(self, dentro: Servicio):
        self.dentro = dentro
        self.nombre = getattr(dentro, "nombre", "?")
        self.escribe_cintas = getattr(dentro, "escribe_cintas", False)

    def puede(self, pieza):
        try:
            return self.dentro.puede(pieza)
        except Exception as e:                     # noqa: BLE001
            return False, f"no se pudo preguntar: {type(e).__name__}: {e}"[:200]

    def correr(self, pieza) -> Resultado:
        import registro

        try:
            return self.dentro.correr(pieza)
        except Exception as e:                     # noqa: BLE001
            motivo = f"{self.nombre} revento: {type(e).__name__}: {e}"
            registro.aviso("servicio", "el paso revento",
                           detalle=f"{pieza.slug}: {motivo}"[:600], eco=True)
            return Resultado(False, motivo=motivo[:300])

    def __repr__(self):
        return f"<Recogido {self.dentro!r}>"


def para(fase_nombre: str, plantilla: str | None) -> Servicio | None:
    """El servicio de una fase, **ya con su fallo recogido**.

    El objeto si lo hay, si no el script envuelto; y en los dos casos dentro de
    `Recogido`, que es lo que garantiza que ningún paso pueda reventar la línea
    sin dejar rastro en el log.
    """
    if fase_nombre in REGISTRO:
        return Recogido(REGISTRO[fase_nombre])
    if plantilla:
        return Recogido(ServicioScript(fase_nombre, plantilla))
    return None
