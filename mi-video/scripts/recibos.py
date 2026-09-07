"""Tiquets de servicio cerrados sin que el servicio contestara.

Jaime, 7-9-2026, despues de ver reel-03 mal por segunda vez: *«habia un
compositor para arreglar el tramo que faltaba, y habia un disenador para recibir
las ordenes del compositor y para revisar todo»*. Y la pregunta que lo cierra:
*«en que momento te parecio buena idea saltarte el proceso?»*.

## Que mira

Un tiquet cuyo `vuelve_a` es `descrito` o `disenado` lo atiende **un servicio**,
y ese servicio deja recibo: un pedido escrito en `work/servicio/<paso>/` y una
respuesta recogida de ahi. `dominio.ticket.contestar` ya no deja cerrar uno sin
esa respuesta —ver `SinRecibo`—, pero eso solo puede impedir los proximos. Los
que ya se colaron siguen en la tabla diciendo que se atendio algo que nadie
miro, y esos son los que se leen aqui.

## Por que es deuda declarada y no un fallo a secas

Porque son 37, de meses de linea, y parar el montaje por todos ellos no arregla
ninguno: deja de salir la pieza de hoy. Es el mismo trato que `tamano.py` le da
al techo de 300 lineas, y por el mismo motivo — **la deuda se declara, se ve, y
solo puede bajar**. Lo que no puede pasar es que aparezca uno nuevo.

    python scripts/recibos.py             # los que no estan declarados
    python scripts/recibos.py --declarar  # fija la deuda con lo que hay hoy
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dominio import ticket  # noqa: E402

#: La deuda: los cerrados sin recibo el dia que esto paso a ser guarda.
DEUDA = "docs/recibo-deuda.txt"


def declarada():
    if not os.path.exists(DEUDA):
        return set()
    fuera = set()
    for l in open(DEUDA, encoding="utf-8"):
        l = l.strip()
        if l and not l.startswith("#"):
            fuera.add(int(l.split()[0]))
    return fuera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", nargs="?")
    ap.add_argument("--declarar", action="store_true",
                    help="fija la deuda con lo que hay hoy")
    a = ap.parse_args()
    faltan = ticket.sin_recibo(a.pieza)

    if a.declarar:
        with open(DEUDA, "w", encoding="utf-8", newline="\n") as h:
            h.write("# Tiquets de servicio cerrados sin recibo el dia que esto\n"
                    "# paso a ser guarda. SOLO BAJA: uno nuevo para el montaje.\n")
            for t in faltan:
                h.write(f"{t['id']} {t['pieza']} {t['vuelve_a']} {t['cerrado']}\n")
        print(f"deuda declarada: {len(faltan)} tiquet(s) sin recibo")
        return

    ya = declarada()
    nuevos = [t for t in faltan if t["id"] not in ya]
    if not nuevos:
        print(f"recibos: ningun tiquet nuevo sin recibo ({len(faltan)} en deuda)")
        return
    print(f"\nEL CONDUCTO ES UNA GUARDA - {len(nuevos)} tiquet(s) cerrado(s)"
          f" sin que su servicio contestara:")
    for t in nuevos:
        print(f"  · #{t['id']} {t['pieza']} vuelve a «{t['vuelve_a']}»,"
              f" cerrado {t['cerrado']}, y no hay respuesta de ese paso")
    print("\nUn tiquet de servicio se cierra cuando el paso contesta, no cuando"
          "\nalguien lo da por contestado: sin pedido no hay orden escrita, y"
          "\nsin respuesta no hay nada que revisar.")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
