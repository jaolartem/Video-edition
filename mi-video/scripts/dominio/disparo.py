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

#: Las preguntas por las que ya se llamo a un oficio en este proceso, por su
#: huella. Vive aqui y no en el objeto porque es memoria del disparador —de
#: quien llama—, no del oficio: el oficio es de su pieza y se construye nuevo
#: cada vez que se le busca.
_LLAMADOS = set()

def llama(slug):
    """Llama al oficio que esa pieza esta esperando. Cierto si contesto.

    Es la puerta publica del disparador, y existe porque los dos caminos tienen
    que pasar por ella: el salto reactivo —`dispara`, cuando un paso acaba— y la
    corrida a mano de `avanzar`, que recorre la pieza sin encender ningun salto.
    Colgada solo del salto, una corrida a mano dejaba el pedido escrito y a
    nadie llamado, que es como quedaron reel-01, reel-03 y reel-05 el 7-9-2026.

    Quien es ese oficio, donde deja su respuesta y como se le llama lo sabe el
    propio `Oficio`: aqui solo esta la regla de cuando se le llama.
    """
    if not encendido():
        return False
    from .oficio import Oficio

    quien = Oficio.de(slug)
    if not quien:
        return False
    # **A la misma pregunta no se le llama dos veces.** Con el motor puesto, una
    # vuelta que vuelve a ver el mismo pedido sin contestar despertaria al mismo
    # oficio para contestar lo mismo — el coste exacto que hizo retirar la
    # patrulla. Si el pedido se reescribe, su huella cambia y vuelve a entrar.
    if quien.huella in _LLAMADOS:
        return False
    _LLAMADOS.add(quien.huella)
    return quien.llama()


def puesto(vuelta, cada=30):
    """Se queda dando vueltas mientras corra. Es lo que hay que dejar activo.

    Jaime, 7-9-2026: *«puedes hacer que se mantenga activo para que siempre que
    este activo mueva las etiquetas»*.

    No es la patrulla que se retiro, y la diferencia es lo que cuesta una vuelta
    que no encuentra nada: leer estados y ficheros, cero tokens. Lo caro era
    despertar al oficio para que contestara lo mismo, y eso lo corta
    `_LLAMADOS`: a una pregunta se le llama una vez y solo vuelve a entrar si su
    pedido se reescribe.

    Vive aqui y no en el motor porque son dos responsabilidades: recorrer el
    camino es de `avanzar`, y estar puesto es del disparador.
    """
    import time

    print("disparador puesto — mueve las etiquetas mientras corra",
          file=__import__("sys").stderr)
    while True:
        try:
            vuelta()
            time.sleep(max(5, int(cada)))
        except KeyboardInterrupt:
            return


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
        if llama(slug):
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
