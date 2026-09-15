"""La versión de una pieza: **un corte concreto**, no un render concreto.

**Por qué es un sustantivo del dominio y no una función de `modelo.py`.** Lo dice
el propio ciclo que Jaime describe: *«de cada versión aprobada me das el audio
virgen»*. Si «la versión aprobada» no se puede nombrar, ese ciclo no se puede
ejecutar dos veces igual — y hasta hace poco no se podía: no existía la tabla, y
cuál WAV correspondía a qué corte era cosa de mirar fechas.

Vivía dentro de `modelo.py`, que es la herramienta que **migra** el esquema. Una
cosa es cambiar la forma de las tablas y otra es lo que significa una fila: dos
responsabilidades del tamaño y de la vida de cada una muy distintos.

## Lo único que hay que entender de aquí: la huella es del CORTE

Se calcula sobre los tramos y sus tomas, **no sobre el fichero**. Dos renders del
mismo montaje son la misma versión aunque el JSON se haya reescrito; un corte
distinto es otra versión aunque el fichero pese lo mismo. Es la misma lección que
la caducidad por contenido: comparar lo que significa, no lo que ocupa.

Por eso `registrar_version` es idempotente y un registro por fecha no lo sería:
renderizar dos veces lo mismo no crea dos versiones.

**Y son funciones, no una clase, a propósito.** La regla del proyecto es que un
dato del dominio no viaje desnudo —lista, `dict` o tupla—, y aquí no viaja nada:
lo que sale es la huella (una cadena que la base guarda tal cual) y el `id` de la
fila. Envolverlos en un objeto que nadie desempaqueta sería ceremonia. El día que
alguien necesite pasear una versión entera, la clase se declara aquí.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402


def _con():
    c = basedatos.abrir()
    c.row_factory = sqlite3.Row
    return c


def _edl(slug):
    """El corte de una pieza, o `None` si todavía no lo hay."""
    p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def huella_de(e):
    """La huella de un corte **que ya se tiene en la mano**.

    Existe porque la misma cuenta hacia falta sobre el corte VIVO —el fichero—
    y sobre un corte GUARDADO —la columna `version.edl`—, y la segunda se
    estaba haciendo aparte: `sellar.py` calculaba `sha1(edl + sha_del_mp4)` y
    lo guardaba en la misma columna `huella` que esta funcion llena con la del
    corte.

    **Dos escritores, una columna, dos significados.** El esquema dice, en un
    comentario encima de la columna, *«la huella es del CORTE, no del
    fichero»*, y lo que habia dentro era de la entrega: medido sobre las 95
    versiones de la base, **ninguna** coincidia con la huella de su corte. Con
    eso `donde.py` decia «CAMBIO» en las siete piezas **siempre**, hubiera
    cambiado el corte o no — un aviso que no puede ser nunca negativo no avisa
    de nada, y era el unico sitio donde mirar si lo que Jaime firmo seguia en
    pie.

    Lo que identifica una entrega distinta del mismo corte es el fichero, y eso
    ya tiene columna: `sha_entrega`.
    """
    if e is None:
        return None
    return hashlib.sha1(json.dumps(
        [[round(a, 3), round(b, 3), d.get("toma"), d.get("beat")]
         for (a, b), d in zip(e["segmentos"], e["detalle"])],
        ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def huella_edl(slug):
    """La huella del corte vivo de una pieza. Ver la cabecera de este fichero."""
    return huella_de(_edl(slug))


def registrar_version(slug, fichero=None, commit=None):
    """Apunta el corte actual como una versión. Idempotente por huella.

    Si el corte no cambió, devuelve la versión que ya había: renderizar dos
    veces lo mismo no crea dos versiones, que es lo que haría un registro por
    fecha.
    """
    h = huella_edl(slug)
    if not h:
        return None
    con = _con()
    v = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        con.close()
        return None
    ya = con.execute("select id, n from version where video_id = ? and huella = ?",
                     (v["id"], h)).fetchone()
    if ya:
        con.close()
        return ya["id"]
    n = (con.execute("select coalesce(max(n), 0) from version where video_id = ?",
                     (v["id"],)).fetchone()[0]) + 1
    e = _edl(slug)
    dur = e.get("duracion_montada_s") if e else None
    cur = con.execute(
        "insert into version (video_id, n, huella, duracion_s, fichero,"
        " commit_git, fecha) values (?,?,?,?,?,?,?)",
        (v["id"], n, h, dur, fichero, commit,
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    vid = cur.lastrowid
    con.close()
    return vid
