"""Una sola puerta para abrir `decisiones.db`, y **una sola conexión por proceso**.

**Por qué existe.** Había 47 `sqlite3.connect(...)` repartidos por 31 ficheros y
ninguno decía cuánto espera. Pero el `timeout` sólo era la mitad del problema, y
la mitad pequeña.

**La grande: un proceso se bloqueaba a sí mismo.** `revalidar` abre su conexión,
escribe una nota sin confirmar todavía, y llama a `fijar.declarar`, que abre
*otra* conexión y quiere borrar la etapa. Para SQLite son dos escritores
distintos peleándose por la misma base — aunque sean el mismo programa. Y ahí no
hay espera que valga: el que aguanta la transacción es el que está esperando, así
que esperar sólo alarga el fallo. `avanzar` murió dos veces seguidas exactamente
ahí, con las siete respuestas de la ronda ya escritas y sin aplicar.

**Arreglo: el proceso tiene una conexión, no muchas.** Quien pida abrir recibe la
misma, así que las llamadas anidadas comparten transacción en vez de competir por
ella. `close()` no cierra —cerrarla dejaría al de fuera sin base a mitad de su
trabajo—; la suelta el sistema al terminar el proceso, que es cuando de verdad ha
acabado. Los scripts de esta línea son cortos y de un solo hilo: es justo el caso
donde compartir conexión es lo correcto y no un truco.

**Y lo que arregla de fondo** no es ninguna de las dos cosas: es que la regla de
cómo se abre la base viva en **un** sitio. Cuarenta y siete copias de una decisión
son cuarenta y siete sitios donde puede divergir, y este proyecto ya sabe cómo
acaba eso.
"""
import os
import sqlite3

#: Dónde vive la base. Estaba escrito a mano en una docena de ficheros, que es
#: la misma avería de siempre en su versión más tonta: mover el fichero exigía
#: acordarse de doce sitios.
BASE = "ads/decisiones.db"

#: Lo que se espera a que otro **proceso** suelte la escritura. Dentro del
#: propio proceso ya no se espera a nadie: la conexión es la misma.
ESPERA = 30.0

#: Una conexión viva por fichero de base. La clave es la ruta absoluta, para
#: que `ads/decisiones.db` y su forma absoluta no abran dos.
_VIVAS = {}


class _Conexion(sqlite3.Connection):
    """La conexión del proceso. `close()` no cierra.

    Cerrar de verdad rompería al llamador de fuera, que sigue teniendo trabajo
    con la misma conexión: el patrón `con = _con() ... con.close()` está en
    treinta ficheros y es correcto cuando cada uno tiene la suya. Aquí la
    comparten, así que cerrar es lo único que no puede hacer.
    """

    def close(self):                               # noqa: D102
        try:
            self.commit()
        except sqlite3.Error:
            pass


def abrir(ruta=None, **kw):
    """La conexión del proceso para esa base. Siempre la misma."""
    ruta = ruta or BASE
    clave = os.path.abspath(ruta)
    cx = _VIVAS.get(clave)
    if cx is not None:
        return cx
    kw.setdefault("timeout", ESPERA)
    kw.setdefault("check_same_thread", False)
    cx = sqlite3.connect(ruta, factory=_Conexion, **kw)
    # El `timeout` cubre la conexión; el `pragma` cubre cada sentencia, que es
    # donde de verdad se choca contra otro proceso. Cuestan una llamada.
    cx.execute(f"pragma busy_timeout = {int(ESPERA * 1000)}")
    # **WAL: un escritor y todos los lectores que hagan falta, a la vez.**
    #
    # En el modo por defecto una escritura bloquea la base entera, lectores
    # incluidos. Con siete piezas que comparten ocho cintas eso significa que
    # cualquier paso que escriba para a todos los que sólo quieren mirar — y es
    # lo que hace imposible correr la línea en paralelo, que es el paso
    # siguiente del plan de rendimiento.
    #
    # Es una propiedad del fichero, no de la conexión: se pone una vez y se
    # queda. Se comprueba lo que devuelve en vez de suponerlo, porque en algunos
    # sistemas de ficheros —los de red, sobre todo— SQLite lo rechaza y sigue en
    # el modo de antes sin decir nada.
    try:
        modo = cx.execute("pragma journal_mode = wal").fetchone()
        if modo and str(modo[0]).lower() != "wal":
            print(f"  aviso: la base no acepta WAL, se queda en «{modo[0]}»:"
                  f" la linea no podra correr en paralelo")
    except sqlite3.Error:
        pass
    _VIVAS[clave] = cx
    return cx


def cerrar_todo():
    """Suelta las conexiones de verdad. Para quien termine y quiera dejarlo limpio."""
    for cx in list(_VIVAS.values()):
        try:
            cx.commit()
            sqlite3.Connection.close(cx)
        except sqlite3.Error:
            pass
    _VIVAS.clear()
