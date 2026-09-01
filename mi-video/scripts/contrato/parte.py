"""El parte: lo único de este paquete que escribe en pantalla y para la línea.

Dos salidas y nada más. `bloques()` renderiza la prosa compartida con su
huella, para pegarla en los prompts; `parte()` dice de cada contrato qué se
exige y no viaja, qué viaja y nadie mira, qué clave no ejecuta nada y cuánta
deuda hay declarada — y **para** en los dos casos que no son deuda sino
incumplimiento: un campo exigido que no viaja y no dice por qué, y una aguja
que ya no existe.

Va aparte de `registro.py` a propósito: lo que mide y lo que escribe son dos
cosas, y mezclarlas es lo que hacía que el parte imprimiera cuatro números
calculados sin tocar el disco mientras la comprobación que sí lo tocaba no la
llamaba nadie.
"""
from __future__ import annotations

from .aguja import NADIE


def bloques(registro):
    print("Los bloques compartidos, con su marca:\n")
    for b in registro.bloques.values():
        print(f"{b.marca()}\n{b.texto.strip()}\n{b.fin()}\n")


def parte(registro):
    for c in registro.contratos.values():
        faltan = [x for x in c.campos_todos() if x.manda is None and x.exige]
        sobran = [x for x in c.campos_todos() if x.manda is not None and not x.exige]
        inertes = [k for k in c.claves_todas() if NADIE in k.dispara]
        deuda = [(k.nombre, a) for k in c.claves_todas() for a in k.dispara
                 if a.pendiente]
        print(f"\n== {c.paso} == {len(c.momentos)} momento(s):"
              f" {', '.join(m.fase for m in c.momentos)}")
        print(f"   exigidos y no enviados : {len(faltan)}"
              + ("  -> " + ", ".join(x.nombre for x in faltan) if faltan else ""))
        print(f"   enviados y no pedidos  : {len(sobran)}"
              + ("  -> " + ", ".join(x.nombre for x in sobran) if sobran else ""))
        print(f"   claves inertes         : {len(inertes)}"
              + ("  -> " + ", ".join(k.nombre for k in inertes) if inertes else ""))
        print(f"   deuda declarada        : {len(deuda)}")

    calladas = registro.calladas()
    if calladas:
        print("")
        print(f"EXIGIDO, NO ENVIADO Y SIN EXPLICAR — {len(calladas)}:")
        for m in calladas:
            print(f"  · {m}")
        raise SystemExit(1)

    perdidos, sin_clausula = registro.revisar()
    if sin_clausula:
        print(f"\nclausulas por escribir ({len(sin_clausula)}), no bloquean:")
        for m in sin_clausula:
            print(f"  · {m}")
    if perdidos:
        print(f"\nEL CONTRATO NO SE SOSTIENE — {len(perdidos)} mecanismo(s)"
              f" perdido(s):")
        for m in perdidos:
            print(f"  · {m}")
        raise SystemExit(1)
    print(f"\ncontratos:"
          f" {sum(len(c.campos_todos()) for c in registro.contratos.values())}"
          f" campos, todas las agujas en pie.")
