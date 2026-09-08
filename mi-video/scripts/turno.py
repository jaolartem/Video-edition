"""El punto de suscripción de un oficio: espera su turno y lo dice.

Jaime, 7-9-2026, viendo lo que habíamos montado: *«son dos agentes que se
suscriben a un contexto específico, cada agente en su bash y con sus
instrucciones precisas; ahora lo que tengo es un mini tú que mueve todo pero
adentro del programa»*.

## Por qué el despachador era el error

`avanzar.py --despachar` recorre las piezas, decide cuál toca, llama al servicio
y recoge la respuesta. Eso es un orquestador central — **la misma figura que
sobraba, escrita en Python**. Mientras exista, los oficios no trabajan: son
llamados.

Lo que este fichero hace es dar la vuelta a la relación. **No llama a nadie: se
queda esperando y contesta a una sola pregunta** —«¿hay algo para mí?»— con la
ruta del pedido. Quien pregunta es el oficio, desde su propia terminal, con sus
propias instrucciones. La línea deja de empujar y pasa a ofrecer.

## Y por eso la IA se usa sólo cuando hace falta

De las 24 etapas del ciclo, 18 son código y una es de Jaime. Un oficio suscrito
sólo despierta cuando hay un pedido de SU paso: las otras diecinueve pasan sin
que nadie llame a un modelo.

    python scripts/turno.py descrito           # espera y dice la ruta
    python scripts/turno.py disenado --ya      # mira una vez y sale
    python scripts/turno.py descrito --cada 5  # con qué frecuencia mira
"""
import argparse
import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import avanzar as _avanzar  # noqa: E402

#: Qué carpeta de pedidos es de cada paso. Es el mismo reparto que ya usa
#: `avanzar.DE_QUIEN`, leído en la otra dirección: de la fase a su buzón.
#: Y se deriva del reparto que ya existe, no se copia: escrito dos veces son dos
#: listas, y estas dos ya habian divergido —`revisar` estaba en una y no en la
#: otra—, con lo que un oficio suscrito a un paso real se quedaba sin buzon.
BUZON = {fase: buzon for buzon, fase in _avanzar.DE_QUIEN.items()}


def hay(paso):
    """Los pedidos de ese paso todavía sin contestar. `[(slug, ruta)]`.

    Un pedido está servido cuando existe su respuesta al lado: no hace falta
    marcar nada, porque el par de ficheros ya lo dice. Es la misma señal que
    usa el archivado, y una señal que se deduce no se puede desincronizar.
    """
    carpeta = os.path.join("work", "servicio", BUZON.get(paso, paso))
    fuera = []
    for p in sorted(glob.glob(os.path.join(carpeta, "*.pedido.json"))):
        slug = os.path.basename(p)[: -len(".pedido.json")]
        if not os.path.exists(os.path.join(carpeta, f"{slug}.respuesta.json")):
            fuera.append((slug, p.replace("\\", "/")))
    return fuera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paso", help="la fase de la que eres el oficio")
    ap.add_argument("--ya", action="store_true",
                    help="mira una vez y sale, en vez de esperar")
    ap.add_argument("--cada", type=int, default=10,
                    help="segundos entre miradas (por defecto 10)")
    a = ap.parse_args()
    if a.paso not in BUZON:
        raise SystemExit(f"«{a.paso}» no tiene buzon. Los que hay:"
                         f" {', '.join(sorted(BUZON))}")

    dicho = False
    while True:
        pendientes = hay(a.paso)
        if pendientes:
            slug, ruta = pendientes[0]
            # **Y se deja escrito a quién espera la pieza**, para que se vea sin
            # mirar esta consola: el estado de la pieza es el sitio donde eso
            # vive. Ver `dominio/estado.py`.
            try:
                from dominio import estado
                estado.espera(slug, a.paso, os.path.basename(ruta))
            except Exception:                      # noqa: BLE001
                pass
            print(ruta)
            return
        if a.ya:
            print("")
            return
        if not dicho:
            print(f"suscrito a «{a.paso}» — esperando turno", file=sys.stderr)
            dicho = True
        try:
            time.sleep(max(1, a.cada))
        except KeyboardInterrupt:
            print("", file=sys.stderr)
            return


if __name__ == "__main__":
    main()
