"""El despachador: reparte pedidos y recoge respuestas hasta que no queda nada.

Vivía dentro de `avanzar.py` y son dos cosas distintas: **el enrutador** mueve
una pieza por el camino y termina; **esto** se queda encendido repartiendo
trabajo y recogiendo lo que va llegando. Jaime lo pidió así —*«el programa es un
despachador y queda encendido»*— y el techo de 300 líneas lo separó solo, que es
justo para lo que está.

    python scripts/avanzar.py --despachar
"""
import os
import sys
import time

import registro  # noqa: E402
import servicios  # noqa: E402
from servicios import Pieza  # noqa: E402
from dominio.fase import anotar, camino, fase_de  # noqa: E402
# **Lo que el despachador necesita del enrutador se le pide, no se le copia.**
# Son suyas —repartir turnos es su trabajo— pero medir una vuelta, saber que
# piezas hay y que pedidos siguen sin contestar es del enrutador, y duplicarlo
# aqui seria tener dos respuestas para la misma pregunta.
from avanzar import (  # noqa: E402
    DE_QUIEN, _contestadas_tarde, _devuelve, _respuestas, _sin_contestar,
    _una_vuelta, piezas_de)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: Vueltas sin que se mueva nada antes de apagarse. **Esto esperaba para
#: siempre**: 473 minutos colgado con diez pedidos escritos y ninguna respuesta,
#: porque el CLI no tiene sesión desde aquí y no había nadie que los contestara.
#: Un paso que espera en silencio no es un paso, es un cuelgue — y lo caro es que
#: parece que algo pasa, así que nadie mira por qué no pasa. Con la espera
#: creciente son unos cuatro minutos, de sobra para un agente lento.
PACIENCIA = 15


def despachar(a) -> None:
    """Queda encendido: reparte pedidos y recoge respuestas segun llegan.

    **Lo que es este programa.** Jaime, el 1 de septiembre: *«como el programa es
    un despachador, debe permanecer encendido mientras trabajamos; las etiquetas
    les asignan el pedido hasta que salen y se archivan; tus agentes reemplazan
    el llamado por API, pero el programa funciona como tal»*.

    Corriendolo a mano, cada respuesta esperaba a que a mi se me ocurriera
    empujar la linea. Y esperar no es gratis: entre que una respuesta se escribe
    y alguien la recoge, otra pieza puede mover la cinta que comparten y dejarla
    desfasada — 20 analisis completos se perdieron asi. Un despachador encendido
    la recoge cuando llega.

    No adivina cuando hay trabajo: **mira los ficheros de respuesta**. Mientras
    nadie conteste no hay nada que hacer y no se gasta nada en comprobarlo.
    """
    import time

    huella, quieto, atascadas = None, 0, set()
    print("despachador encendido — Ctrl-C para parar")
    while True:
        # **Una pieza atascada no apaga el despachador.**
        #
        # `avanzar` para en seco cuando una pieza falla dos veces por lo mismo, y
        # eso esta bien para una corrida a mano: dice que hay algo que arreglar.
        # Aqui es lo contrario de lo que hace falta — hay seis piezas mas
        # esperando su turno, y apagar el reparto por una es dejar de repartir.
        # Se dice una vez, se apunta, y se sigue con las demas.
        # **Lo contestado entra ANTES de avanzar.**
        #
        # Estaba detras del recorrido, o sea detras de una pasada de
        # renders que puede durar veinte minutos: la respuesta esperaba a
        # que terminara de renderizar piezas que iban a cambiar por esa
        # misma respuesta. Seis composiciones se quedaron sin aplicar asi,
        # y las piezas salieron identicas a la vuelta anterior.
        #
        # Una respuesta que llega tarde se aplica igual
        #
        # Jaime: *«las etiquetas les asignan el pedido hasta que salen y se
        # archivan»*. Si la pieza ya paso de ese paso cuando llega la respuesta,
        # nadie la consume — y la decision existe, esta escrita, y no pasa nada.
        # Es la forma mas cara de perder trabajo: se pago la llamada y no llego a
        # la pantalla.
        #
        # Paso con el gancho de reel-01: su composicion se escribio mientras la
        # pieza ya estaba en `montado`, asi que el render salio identico al de
        # antes y Jaime lo vio: *«no hay diferencia entre este y el que me
        # mostraste antes»*. Tenia razon, y el fichero llevaba una hora en disco.
        #
        # El despachador la devuelve al paso que la espera. Es su trabajo: el
        # pedido sigue asignado a esa etiqueta hasta que se archiva.
        # **Y los tickets cuyo problema ya no esta se cierran solos.**
        # Si no, la lista dice que no se ha hecho nada aunque este hecho — que
        # es lo que Jaime vio: cuatro de las cinco cosas que habia senalado ya no
        # sonaban en la pieza y sus tickets seguian abiertos.
        try:
            from dominio.ticket import cerrar_los_resueltos

            for n in piezas_de(a):
                cerrados = cerrar_los_resueltos(f"reel-{int(n):02d}")
                if cerrados:
                    print(f"  reel-{int(n):02d}: {cerrados} ticket(s) cerrados"
                          f" midiendo")
        except Exception as e:                     # noqa: BLE001
            registro.aviso("despachador", "no se pudieron cerrar tickets",
                           detalle=f"{type(e).__name__}: {e}"[:200], eco=False)
        for paso, slug in _contestadas_tarde():
            print(f"  respuesta tardia -> {paso}/{slug}: vuelve a su paso")
            _devuelve(slug, paso)

        movidos = _una_vuelta(a)
        # **Lo que espera a un agente se dice, porque es la senal de lanzarlo.**
        # Jaime: *«y lanzas el agente cuando el log sea por falta de agente»*.
        # Un pedido abierto no es un fallo: es un turno pedido y sin servir, y
        # mezclarlo con los atascos hace que no se distinga cual de los dos es.
        for paso, slug in _sin_contestar():
            clave = f"{paso}/{slug}"
            if clave not in atascadas:
                atascadas.add(clave)
                print(f"  espera agente -> {clave}")
        ahora = _respuestas()
        if movidos or ahora != huella:
            quieto = 0
        else:
            quieto += 1
            if quieto == 1:
                print("  (esperando respuestas)")
        huella = ahora
        # **Y si nadie contesta, se apaga diciendo a quién esperaba.** Ver
        # `PACIENCIA`: esto esperaba para siempre, y costó 473 minutos.
        if quieto >= PACIENCIA:
            print(f"\ndespachador: {quieto} vueltas sin que se mueva nada."
                  f" Se apaga en vez de esperar a alguien que no viene.")
            for paso, slug in _sin_contestar():
                print(f"  falta contestar -> work/servicio/{paso}/{slug}"
                      f".pedido.json")
            return
        try:
            time.sleep(min(2 + quieto * 2, 20))
        except KeyboardInterrupt:
            print("\ndespachador apagado")
            return


#: Que fase espera la respuesta de cada carpeta de pedidos.
