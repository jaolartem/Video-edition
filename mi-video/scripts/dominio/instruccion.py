"""Lo que Jaime ha dicho, para no tener que decirlo otra vez.

**Por qué existe.** Jaime: *«agrega una tabla de comentarios para correcciones,
he hecho las mismas n veces, es importante guardarlas»*. Y el ejemplo que lo
acompaña es el que duele: *«dije cambia el CTA por otro y arregla con edición lo
que falta»* — dicho, y no ejecutado.

La tabla `correccion` que ya existía guarda **mis** correcciones de código: qué
se rompió, por qué, y qué mecanismo lo hace imposible de repetir. Esto es lo
contrario y faltaba: **las suyas**. Una instrucción editorial vive hoy en el chat
—o sea, en el contexto— y el contexto se limpia. Por eso hay que repetirla.

## Lo que la hace útil, y no es guardarla

Guardar una instrucción y no llevarla al paso que debe obedecerla es archivarla.
Por eso `para(paso, slug)` devuelve las que aplican, y `servicio.pedir()` las mete
en **todo** pedido: quien contesta las ve sin que nadie se acuerde de pegarlas.

Es la misma forma que `hoy` y `datos_respaldados` (C-151): lo que vale para todos
los contratos viaja por un solo sitio.

## `veces` es el dato importante

Cada vez que una instrucción se repite, sube el contador. No es estadística: es
**la medida de lo que cuesta no tener esto**. Una instrucción con `veces = 4` es
cuatro turnos de criterio de Jaime gastados en decir lo mismo, y el número lo
dice sin discusión.

## Los cuatro estados, y la diferencia importa

- `pendiente` — dicha y no hecha. Es lo que hay que mirar antes que nada.
- `aplicada` — hecha en esta pieza. Puede volver a hacer falta en la siguiente.
- `en la maquina` — ya no depende de que nadie se acuerde: hay un mecanismo. Es
  el único estado que cierra de verdad, y la columna `aguja` dice dónde.
- `descartada` — la miró y dijo que no. **Faltaba**, y la falta tenía coste: sin
  este estado, una propuesta que Jaime rechaza se queda en `pendiente` y
  `servicio.pedir()` la sigue metiendo en todos los pedidos **como si fuera
  regla**. La alternativa era marcarla `aplicada`, que es mentir en la tabla.

  Pasó el 4 de septiembre con T-03, la compuerta de cifras: su documento decía
  *«Estado: propuesta»* y yo la mandé a implementar. Jaime: *«la regla propuesta
  no»*. Un registro que sólo sabe decir «hecha» o «por hacer» no puede guardar un
  «no», y entonces el «no» se pierde y la propuesta vuelve sola.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

ESQUEMA = """
CREATE TABLE IF NOT EXISTS instruccion (
  id       INTEGER PRIMARY KEY,
  cuando   TEXT NOT NULL,
  dijo     TEXT NOT NULL,            -- sus palabras, sin resumir
  ambito   TEXT NOT NULL             -- 'lote' | 'pieza' | 'paso'
           CHECK (ambito IN ('lote','pieza','paso')),
  pieza    TEXT,                     -- slug, si es de una
  paso     TEXT,                     -- fase, si es de uno
  estado   TEXT NOT NULL DEFAULT 'pendiente'
           CHECK (estado IN ('pendiente','aplicada','en la maquina',
                             'descartada')),
  veces    INTEGER NOT NULL DEFAULT 1,
  aguja    TEXT,                     -- donde quedo imposible de olvidar
  nota     TEXT
)
"""


def _con():
    cx = basedatos.abrir()
    cx.row_factory = sqlite3.Row
    basedatos.esquema(cx, ESQUEMA)
    _al_dia(cx)
    return cx


def _al_dia(cx):
    """Añade `descartada` a una tabla que se creó sin ese estado.

    `CREATE TABLE IF NOT EXISTS` no toca una tabla que ya existe, así que ampliar
    un `CHECK` en `ESQUEMA` no cambia nada en la base que ya está escrita: el
    estado nuevo se declara y sigue sin poder guardarse. Es la avería de este
    proyecto en su forma más pequeña — declarar sin implementar.

    Se rehace la tabla, que es lo único que SQLite permite para cambiar un
    `CHECK`, y se copia fila por fila dentro de una transacción. Corre una vez:
    la segunda encuentra el estado ya declarado y se va.
    """
    fila = cx.execute("select sql from sqlite_master where type = 'table'"
                      " and name = 'instruccion'").fetchone()
    if not fila or "descartada" in (fila[0] or ""):
        return
    cx.executescript(
        "begin;"
        " alter table instruccion rename to instruccion_vieja;"
        + ESQUEMA.replace("IF NOT EXISTS ", "") + ";"
        " insert into instruccion select * from instruccion_vieja;"
        " drop table instruccion_vieja;"
        "commit;")


def guardar(dijo, ambito="lote", pieza=None, paso=None, nota=None):
    """Apunta lo que dijo. Si ya estaba dicho, **sube el contador**.

    Repetir no crea una fila nueva: sube `veces` en la que ya hay. Dos filas con
    la misma instrucción serían dos instrucciones, y entonces nadie sabría
    cuántas veces ha habido que decirla — que es justo el dato que hace falta.
    """
    cx = _con()
    ya = cx.execute(
        "select id, veces from instruccion where dijo = ? and"
        " coalesce(pieza,'') = coalesce(?,'') and coalesce(paso,'') = coalesce(?,'')",
        (dijo, pieza, paso)).fetchone()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    if ya:
        cx.execute("update instruccion set veces = veces + 1, cuando = ?,"
                   " estado = 'pendiente' where id = ?", (ahora, ya["id"]))
        cx.commit()
        return ya["veces"] + 1
    cx.execute(
        "insert into instruccion (cuando, dijo, ambito, pieza, paso, nota)"
        " values (?,?,?,?,?,?)", (ahora, dijo, ambito, pieza, paso, nota))
    cx.commit()
    return 1


def cerrar(id_, estado="aplicada", aguja=None, nota=None):
    """La da por hecha. `en la maquina` **exige** decir dónde.

    Sin aguja, «en la máquina» es una promesa: alguien dirá que ya está resuelto
    y nadie podrá comprobarlo. Es la misma regla que el log de correcciones.
    """
    if estado == "en la maquina" and not aguja:
        raise ValueError("«en la maquina» sin aguja es una promesa, no un cierre")
    cx = _con()
    cx.execute("update instruccion set estado = ?, aguja = coalesce(?, aguja),"
               " nota = coalesce(?, nota) where id = ?",
               (estado, aguja, nota, id_))
    cx.commit()


def para(paso=None, pieza=None):
    """Las que aplican a ese paso y esa pieza, **sin las ya cerradas del todo**.

    Las `en la maquina` no viajan: ya hay un mecanismo que las cumple, y
    repetirlas en el pedido sería pedirle a quien contesta que vigile algo que el
    código ya garantiza.
    """
    cx = _con()
    filas = cx.execute(
        "select id, cuando, dijo, ambito, pieza, paso, estado, veces, nota"
        "  from instruccion"
        " where estado <> 'en la maquina'"
        "   and (ambito = 'lote'"
        "        or (ambito = 'pieza' and pieza = ?)"
        "        or (ambito = 'paso' and paso = ?))"
        " order by veces desc, id", (pieza, paso)).fetchall()
    cx.close()
    return [dict(f) for f in filas]


def todas():
    cx = _con()
    filas = [dict(f) for f in cx.execute(
        "select * from instruccion order by estado, veces desc, id")]
    cx.close()
    return filas
