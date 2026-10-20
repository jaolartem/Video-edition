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
import time

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

#: Las preguntas por las que ya se llamo a un oficio en este proceso: por su
#: huella, `(veces, cuando fue la ultima)`. Vive aqui y no en el objeto porque
#: es memoria del disparador —de quien llama—, no del oficio: el oficio es de
#: su pieza y se construye nuevo cada vez que se le busca.
_LLAMADOS = {}

#: Cuantas veces seguidas se llama por la misma pregunta, y cuanto se espera
#: antes de volver a preguntar.
#:
#: **El plazo existe porque «para toda la vida del proceso» dejo de ser una
#: tarde.** Con el disparador puesto —*«debe estar activo siempre»*— un proceso
#: vive dias, asi que quemar la pregunta en el es quemarla para siempre. Medido
#: el 9-9-2026: reel-03 se quedo en `repasado` con su pedido escrito y el bucle
#: dando vueltas cada 100 s **sin nombrarlo ni una vez** — el aviso de «la pieza
#: no avanza» no salta cuando la pieza espera a un oficio, asi que la unica
#: pieza parada era la unica invisible.
TOPE = 2
REINTENTO = 600

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
    from .oficio import POR_BASH
    if not POR_BASH:
        # Se dice una vez por pregunta y se deja abierta para los agentes.
        if quien.huella not in _LLAMADOS:
            _LLAMADOS[quien.huella] = (0, time.time())
            _anota(f"{slug}: pedido abierto para {quien} — {quien.pedido}")
        return False
    # **A la misma pregunta se le llama dos veces seguidas, y luego con
    # plazo.** Con el motor
    # puesto, repetirla en cada vuelta seria despertar al oficio para contestar
    # lo mismo — el coste exacto que hizo retirar la patrulla. Pero una sola vez
    # tampoco vale: la primera llamada se puede caer por algo de fuera —la
    # credencial, la red, un CLI colgado— y con un intento la pregunta quedaba
    # quemada para toda la vida del proceso, con el disparador puesto mirandola
    # sin volver a intentarlo nunca. Dos separa «no contesta» de «no se pudo
    # llamar». Si el pedido se reescribe, su huella cambia y vuelve a entrar.
    veces, ultimo = _LLAMADOS.get(quien.huella, (0, 0.0))
    ahora = time.time()
    if veces >= TOPE and ahora - ultimo < REINTENTO:
        # **Y callarse no es una opcion.** Se dice una vez —no en cada vuelta—,
        # porque una pieza parada y sin nombrar es peor que una parada y dicha.
        if veces == TOPE:
            _LLAMADOS[quien.huella] = (veces + 1, ultimo)
            _anota(f"{slug}: {quien} no contesta despues de {TOPE} llamadas."
                   f" La pieza NO avanza; se le vuelve a preguntar en"
                   f" {REINTENTO // 60} min")
        return False
    if veces >= TOPE:
        veces = 0                                  # pasado el plazo, se repregunta
    _LLAMADOS[quien.huella] = (veces + 1, ahora)
    try:
        hecho = quien.llama()
    except Exception as e:                         # noqa: BLE001
        # Llamar no puede tumbar al que llama: `avanzar` invoca esto fuera de
        # todo `try`, asi que una excepcion aqui se llevaba la corrida entera.
        _anota(f"{quien} revento al llamarle: {type(e).__name__}: {e}")
        return False
    if hecho:
        _LLAMADOS[quien.huella] = (TOPE, ahora)
    return hecho


def _anota(detalle):
    """Deja constancia sin depender de que el registro exista."""
    print(f"  {detalle}", flush=True)
    try:
        import registro

        registro.aviso("oficio", "no se pudo llamar", detalle=detalle,
                       eco=False)
    except Exception:                              # noqa: BLE001
        pass


#: Con qué código sale el disparador para que `arrancar.sh` lo vuelva a poner.
REARRANCA = 75


def _version():
    """El HEAD de la copia que corre, o `None` si no se puede leer."""
    import subprocess

    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() or None


def puesto(vuelta, cada=30):
    """Se queda dando vueltas mientras corra. Es lo que hay que dejar activo.

    Jaime, 7-9-2026: *«puedes hacer que se mantenga activo para que siempre que
    este activo mueva las etiquetas»*.

    No es la patrulla que se retiro, y la diferencia es lo que cuesta una vuelta
    que no encuentra nada: leer estados y ficheros, cero tokens. Lo caro era
    despertar al oficio para que contestara lo mismo, y eso lo corta
    `_LLAMADOS`: a una pregunta se le llama dos veces como mucho —la segunda
    cubre que la primera se cayera por algo de fuera— y solo vuelve a entrar si
    su pedido se reescribe.

    Vive aqui y no en el motor porque son dos responsabilidades: recorrer el
    camino es de `avanzar`, y estar puesto es del disparador.
    """
    import time

    print("disparador puesto — mueve las etiquetas mientras corra",
          file=__import__("sys").stderr)
    # **Una pieza plantada no apaga el reparto.** `avanzar` se planta a
    # proposito con `SystemExit` cuando algo hay que arreglar —dos intentos
    # fallando por lo mismo, un bucle de vueltas— y eso esta bien en una corrida
    # a mano. Aqui es lo contrario: mata el puesto entero, y las otras seis
    # piezas dejan de moverse por una. Se anota y se sigue a la vuelta
    # siguiente, que es lo que el propio motor hace con `planta=False`.
    corre = _version()
    while True:
        try:
            vuelta()
        except KeyboardInterrupt:
            return
        except (SystemExit, Exception) as e:       # noqa: BLE001
            _anota(f"la vuelta del disparador se corto: {type(e).__name__}: {e}")
        # **Y si el código cambió, se rearranca** (C-629). Los pasos corren
        # dentro de este proceso, así que lo fusionado no entraba hasta
        # reiniciarlo: 20-10, cuatro arreglos (C-625..628) fusionados y la línea
        # seguía parando reel-20 con el `revalidar` de las 17:59.
        if corre and _version() != corre:
            print("disparador: el codigo cambio — se rearranca para correrlo",
                  file=__import__("sys").stderr)
            raise SystemExit(REARRANCA)
        try:
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
