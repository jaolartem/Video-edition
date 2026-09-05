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

MESES_LARGO = ("enero", "febrero", "marzo", "abril", "mayo", "junio",
               "julio", "agosto", "septiembre", "octubre", "noviembre",
               "diciembre")


def evento(fecha=None):
    """**Cuando es el evento**, derivado de la escalera y no escrito.

    Jaime: *«simplifica las fuentes, solo queremos una fuente de verdad»*.

    La fecha vivia a mano en `scripts/reels/cta.mjs` —`fecha: "21 de
    septiembre"`— y a la vez, como hecho, en el ultimo escalon de la tabla
    `precio`, cuyo `hasta` es `2026-09-21T11:30` con la nota «cierra con el
    evento». Dos copias del mismo dia: el que se mueva primero deja al otro
    mintiendo, y la escalera se movio DOS VECES en un solo dia.

    Y ademas cierra un encargo que pidio quien compuso reel-01: sin ano, la
    pieza caduca el 22 de septiembre si se reutiliza. Aqui el ano esta porque la
    tabla lo tiene.
    """
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    fila = con.execute(
        "select hasta from precio where ancla = 0 order by hasta desc limit 1"
    ).fetchone()
    con.close()
    if not fila:
        return None
    a, m, d = fila["hasta"][:10].split("-")
    return {
        "iso": fila["hasta"],
        # Como se dice: es lo que la voz dice y lo que el cierre rotula.
        "dice": f"{int(d)} de {MESES_LARGO[int(m) - 1]}",
        # Con ano, para lo que se queda colgado y hay que fechar.
        "con_ano": f"{int(d)} {MESES[int(m) - 1].upper()} {a}",
    }


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
