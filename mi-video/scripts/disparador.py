"""El disparador, puesto: mientras corra, mueve las etiquetas.

Jaime, 7-9-2026: *«el disparador es el que se encarga de lanzarlos, y debe estar
activo siempre»*, y *«puedes hacer que se mantenga activo para que siempre que
esté activo mueva las etiquetas»*.

Es la entrada del disparador, igual que `turno.py` es la del oficio. La regla de
cuándo se enciende vive en `dominio/disparo.py`; aquí sólo está el quedarse.

## No es la patrulla que se retiró

Aquélla recorría las piezas decidiendo a cuál le tocaba —un orquestador— y
**despertaba a los oficios para contestar lo mismo**, que es lo que costaba:
*«necesitamos ahorrar tokens, ese agente no debe existir»*. Una vuelta que no
encuentra nada aquí lee estados y ficheros y ya: cero tokens. Y a una pregunta se
le llama una vez — lo guarda `disparo._LLAMADOS`, y sólo vuelve a entrar si su
pedido se reescribe.

## Y varios oficios a la vez

*«Podemos lanzar varios agentes a la vez, no tenemos que hacer fila, es una
arquitectura por servicios»*. Con `--hilos`, cada pieza va por su lado y llama a
su oficio cuando le toca; el único turno de la casa lo reparte
`planificador.permiso`, y sólo a los pasos que reescriben una cinta.

    python scripts/disparador.py            # puesto, sobre todas las piezas
    python scripts/disparador.py 1 3 5      # sólo esas
    python scripts/disparador.py --cada 60  # cada cuánto vuelve a mirar
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avanzar  # noqa: E402
from dominio import disparo  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--cada", type=int, default=30, metavar="S",
                    help="segundos entre vueltas (por defecto 30)")
    ap.add_argument("--hilos", type=int, default=4, metavar="N",
                    help="cuantas piezas a la vez")
    a = ap.parse_args()
    # Lo que `avanzar` espera de una corrida normal: recorrer y no devolver
    # nada a ninguna fase. `--volver` es de una corrida a mano, no de estar
    # puesto: repetirlo en cada vuelta seria devolver la pieza para siempre.
    a.ver, a.paso, a.volver, a.por_que = False, None, None, ""
    disparo.puesto(lambda: avanzar._una_vuelta(a), a.cada)


if __name__ == "__main__":
    main()
