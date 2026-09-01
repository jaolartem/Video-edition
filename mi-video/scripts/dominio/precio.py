"""El escalón de precio vigente hoy, y cómo se rotula.

C-28 pedía que el precio saliera **con su fecha de cierre**, y eso se cumplía con
una cadena escrita a mano que dejó de ser verdad sola. Aquí el rótulo se deriva:
mientras haya escalón vigente hay precio, y cuando no lo hay **no se imprime
nada**, que es lo único honesto una vez cerrada la inscripción.

El siguiente escalón es la mitad del argumento: sin él, un precio es una tarifa;
con él, es una ventana que se cierra.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

MESES = ("ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic")


def _abierta(fila, hoy: str) -> bool:
    """**El último día cuenta entero.**

    «hasta el 4 sep» sin hora significa hasta que acabe el 4, no hasta que
    empiece: comparando cadenas, «2026-09-04T10:00» > «2026-09-04» y la ventana
    se cerraba un día antes de lo dicho. Con hora —el cierre del evento— se
    compara tal cual.
    """
    tope = fila["hasta"] if "T" in fila["hasta"] else fila["hasta"] + "T23:59:59"
    return (not fila["desde"] or fila["desde"] <= hoy) and hoy <= tope


def vigente(fecha=None):
    """El escalón de hoy ya redactado, o `None` si ya cerró todo.

    `vale` viene escrito —«$20 hasta el 4 sep · luego $30 y $40»— porque quien lo
    consume lo rotula, y un rótulo compuesto en dos sitios se separa en cuanto
    uno cambia.
    """
    hoy = fecha or datetime.datetime.now().isoformat(timespec="seconds")
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    filas = [dict(r) for r in con.execute(
        "select * from precio where ancla = 0 order by hasta")]
    con.close()
    escalon = next((f for f in filas if _abierta(f, hoy)), None)
    if not escalon:
        return None
    luego = [f["importe"] for f in filas if f["hasta"] > escalon["hasta"]]
    d = escalon["hasta"][:10].split("-")
    vale = f"${escalon['importe']} hasta el {int(d[2])} {MESES[int(d[1]) - 1]}"
    if luego:
        vale += " · luego " + " y ".join(f"${x}" for x in luego)
    return {"importe": escalon["importe"], "hasta": escalon["hasta"],
            "vale": vale, "luego": luego}
