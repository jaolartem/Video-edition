"""Un paso completado enciende el siguiente. Uno, no una ronda.

Jaime, 7-9-2026: *«debe avanzar por etiquetas que activen procesos y agentes… un
proceso completado, un cambio de estado; un cambio de estado activa un nuevo
proceso»*. Y sobre lo que había: *«el que hace que avance es el agente en bash,
está mal»*, *«ahora lo que tengo es un mini tú que mueve todo pero adentro del
programa»*.

## La diferencia con el despachador, que no es de tamaño

`avanzar --despachar` **patrulla**: recorre las siete piezas, mira cuál se puede
mover y la mueve, una y otra vez. Esto **reacciona**: se enciende cuando un paso
acaba, da un salto, y se apaga. Nadie recorre nada.

Y son dos cosas distintas aunque el salto lo dé la misma función. La patrulla
tiene que saber de todas las piezas y decidir a quién le toca — eso es un
orquestador, y es la figura que sobra. La reacción sólo sabe de la pieza que
acaba de moverse, que es la única sobre la que hay algo nuevo que decir.

## Un salto, y por qué no dos

`tope=1`. Si el paso siguiente también acaba, será **él** quien dispare el
suyo — y si no acaba, la pieza se queda donde debe, esperando a quien la atienda.
Encadenar aquí sería reconstruir la ronda por dentro: la misma patrulla, con el
bucle escondido en la recursión.

## Y una llamada dentro de otra no dispara

`avanzar` ejecuta el paso, y el paso puede escribir estado — así que sin guarda
un salto encendería otro desde dentro de sí mismo, sin fondo. `_EN_VUELO` corta
eso, **y por pieza**: lo que hay que impedir es que una se llame a sí misma, no
que dos avancen a la vez.

## Y por eso esto no es una fila

Jaime, 7-9-2026: *«al final es modular, cada video llama las funciones, no pasa
por ellas»*. No hay una cinta transportadora con siete piezas encima: cada una
llama a lo que necesita cuando su estado cambia, y las funciones son biblioteca,
no estaciones. De ahí que el paralelismo sea lo normal y no algo que haya que
organizar — el único recurso que de verdad comparten es la cinta, y eso lo
serializa `planificador.py` sólo en los pasos que la reescriben.
"""
from __future__ import annotations

import os
import threading

#: Las piezas con un disparo en curso. **Por pieza, no una bandera global.**
#:
#: Jaime, 7-9-2026: *«al final es modular, cada video llama las funciones, no
#: pasa por ellas»*. Con una bandera unica el modelo era el contrario —una sola
#: linea por la que pasan las siete— y bastaba que reel-01 estuviera dando su
#: salto para que reel-05 no pudiera dar el suyo. La reentrada que hay que
#: cortar es la de UNA pieza llamandose a si misma; dos piezas distintas no se
#: estorban, y el unico recurso que de verdad comparten —la cinta— ya lo
#: serializa `planificador.py`, y solo en los pasos que la reescriben.
_EN_VUELO = set()
_CERROJO = threading.Lock()

#: Con esto puesto, el estado se escribe y no enciende nada. Existe para poder
#: mover una pieza a mano sin que la linea salga corriendo detras — que es lo
#: que hace falta cuando se esta arreglando algo.
#:
#: **Y es lo unico que apaga el disparador, que por lo demas esta siempre
#: puesto.** Jaime, 7-9-2026: *«el disparador es el que se encarga de lanzarlos,
#: y debe estar activo siempre»*.
APAGADO = "DISPARO_APAGADO"

#: Que oficio contesta cada buzon. Los nombres son los de `.claude/agents/`, y un
#: buzon sin oficio declarado no se llama: existe y lo contesta quien pueda, que
#: es el caso honesto mientras ese agente no este escrito.
OFICIO = {"describir": "compositor", "disenar": "disenador", "visto": "disenador"}

#: El encargo es siempre el mismo texto. Lo que hay que contestar viaja DENTRO
#: del pedido —`prompt` es su contrato— y esto solo dice que fichero leer y en
#: cual escribir. Improvisar aqui seria un segundo contrato.
ENCARGO = (
    "Tu turno. Lee entero el pedido {pedido} —`prompt` es tu contrato completo y"
    " `datos` el encargo— y escribe tu respuesta en {respuesta}, con la forma que"
    " ese `prompt` define. Si el pedido no basta para contestar, se dice en la"
    " respuesta; no se va a buscar fuera."
)


def _esperando(slug):
    """El pedido sin contestar de esa pieza: `(buzon, ruta)`, o `None`.

    Sale de `servicio.pendientes`, que es la cola del servicio y ya existia. La
    pregunta que hace falta aqui es la misma acotada a una pieza: la que acaba
    de moverse es la unica sobre la que hay algo nuevo que decir.
    """
    try:
        import sys

        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if raiz not in sys.path:
            sys.path.insert(0, raiz)
        import servicio

        for paso, quien, ruta in servicio.pendientes():
            if quien == slug and paso in OFICIO:
                return paso, ruta.replace("\\", "/")
    except Exception:                              # noqa: BLE001
        pass
    return None


def _llama(oficio, pedido):
    """Llama al oficio y espera. Cierto si dejo su respuesta al lado.

    Es la vuelta que `docs/caminos.md` daba por pendiente —*«`turno.py` es el
    punto de suscripcion; falta la vuelta que lo une con `claude --agent`»*— y
    va aqui porque el disparador es lo unico que ve las dos mitades: que un paso
    acaba de dejar una pregunta escrita, y quien sabe contestarla.
    """
    import subprocess

    respuesta = pedido.replace(".pedido.json", ".respuesta.json")
    subprocess.run(["claude", "--agent", oficio, "-p",
                    ENCARGO.format(pedido=pedido, respuesta=respuesta)],
                   check=False)
    return os.path.exists(respuesta)


def encendido():
    """Si el disparo esta activo. Se puede apagar con la variable de entorno."""
    return not os.environ.get(APAGADO)


def dispara(slug, por_que=""):
    """Da UN salto a esa pieza, si toca. Devuelve qué pasó, o `None`.

    No decide el camino ni ejecuta el paso: los dos son de `avanzar`, que ya
    tiene la frontera donde los errores se anotan en vez de escaparse. Aquí sólo
    está la regla de cuándo se enciende.
    """
    if not encendido():
        return None
    try:
        n = int(str(slug)[-2:])
    except ValueError:
        return None
    with _CERROJO:
        if slug in _EN_VUELO:
            return None
        _EN_VUELO.add(slug)
    try:
        import sys

        raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if raiz not in sys.path:
            sys.path.insert(0, raiz)
        import avanzar as _a

        salto = _a.avanzar(n, tope=1, planta=False)
        # **Y si el salto la dejo esperando a un oficio, se le llama.** Un paso
        # de IA no acaba: deja la pregunta escrita y se para. Sin esto el estado
        # queda correcto —el pedido esta ahi— y no enciende nada, que es lo que
        # `docs/caminos.md` llamaba «el disparo» y daba por pendiente.
        espera = _esperando(slug)
        if espera and OFICIO.get(espera[0]):
            if _llama(OFICIO[espera[0]], espera[1]):
                # La respuesta es un evento nuevo y le toca su salto. Va por
                # `avanzar` y no por `dispara`, que para esta pieza esta cerrado
                # mientras dure esta llamada.
                salto = _a.avanzar(n, tope=1, planta=False) or salto
        return salto
    except Exception as e:                         # noqa: BLE001
        # El disparo no puede tumbar a quien lo enciende: quien acaba de
        # terminar su paso ya hizo su trabajo, y perderlo porque el siguiente
        # falle seria cobrar dos veces el mismo error.
        try:
            import registro

            registro.aviso("disparo", "no se pudo encender el paso siguiente",
                           detalle=f"{slug}: {type(e).__name__}: {e}"[:300],
                           eco=False)
        except Exception:                          # noqa: BLE001
            pass
        return None
    finally:
        with _CERROJO:
            _EN_VUELO.discard(slug)
