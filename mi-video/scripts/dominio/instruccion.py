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


#: **A quién va cada una** (C-661). Sin filas, a todos: es como funcionaba, y
#: una instrucción nueva llega a todos hasta que alguien la reparte. `operador`
#: no es un buzón: lo que sólo va a él no viaja a ningún oficio.
REPARTO = """
CREATE TABLE IF NOT EXISTS instruccion_para (
  instruccion_id INTEGER NOT NULL REFERENCES instruccion(id),
  buzon          TEXT NOT NULL,
  PRIMARY KEY (instruccion_id, buzon)
)
"""
OPERADOR = "operador"


def _con():
    cx = basedatos.abrir()
    cx.row_factory = sqlite3.Row
    basedatos.esquema(cx, ESQUEMA)
    basedatos.esquema(cx, REPARTO)
    _al_dia(cx)
    return cx


def repartir(id_, *buzones):
    """Deja dicho a qué buzones va. Sustituye el reparto entero; repetirlo deja lo mismo.

    Falla con un buzón que no existe, igual que `cerrar` falla sin aguja: un
    reparto a un nombre equivocado es una instrucción que no llega a nadie.
    """
    from .oficio import BUZONES

    malos = [b for b in buzones if b not in BUZONES and b != OPERADOR]
    if malos or not buzones:
        raise ValueError(f"instruccion #{id_}: buzones que no existen: {malos or 'ninguno'}")
    cx = _con()
    cx.execute("delete from instruccion_para where instruccion_id = ?", (id_,))
    cx.executemany("insert into instruccion_para values (?, ?)",
                   [(id_, b) for b in dict.fromkeys(buzones)])
    cx.commit()


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

    **Y las `descartada` tampoco, que es para lo que se creó ese estado.** Lo
    dice el docstring de este módulo desde que existe: *«sin este estado, una
    propuesta que Jaime rechaza se queda en `pendiente` y `servicio.pedir()` la
    sigue metiendo en todos los pedidos como si fuera regla»*. El estado se
    creó y esta consulta nunca aprendió a excluirlo: de las 155 que viajaban en
    cada pedido, **41 eran instrucciones que Jaime ya había rechazado** — y
    viajaban ocho veces por pieza, con el mismo peso que las vivas.
    """
    cx = _con()
    filas = cx.execute(
        "select id, cuando, dijo, ambito, pieza, paso, estado, veces, nota"
        "  from instruccion"
        " where estado not in ('en la maquina', 'descartada')"
        "   and (ambito = 'lote'"
        "        or (ambito = 'pieza' and pieza = ?)"
        "        or (ambito = 'paso' and paso = ?))"
        # **Y sólo las de este buzón, si están repartidas** (C-661): las 114 iban
        # enteras a los ocho, 78 KB por pedido para quedarse cada uno con unas
        # pocas, y cada agente formándose su criterio con las de los demás.
        "   and (? is null or not exists (select 1 from instruccion_para r"
        "                                 where r.instruccion_id = instruccion.id)"
        "        or exists (select 1 from instruccion_para r"
        "                   where r.instruccion_id = instruccion.id and r.buzon = ?))"
        " order by veces desc, id", (pieza, paso, paso, paso)).fetchall()
    cx.close()
    return [dict(f) for f in filas]


#: Los pasos a los que de verdad se reparte un pedido. Salen del disco y no de
#: una lista escrita al lado, que es como se desincronizan.
def _pasos_reales():
    raiz = os.path.join("work", "servicio")
    return {d for d in os.listdir(raiz)} if os.path.isdir(raiz) else set()


def etiquetas_huerfanas():
    """Instrucciones con un `paso` que no es el de ningún paso de servicio.

    **Por qué no se filtra por `paso` y ya.** Parece el arreglo obvio —37 filas
    llevan `paso` y la consulta lo ignora porque su `ambito` es `lote`— y es una
    trampa: los nombres no son los mismos. Las etiquetas dicen `montaje`,
    `corte`, `audio`, `montado`; los pasos de servicio son `describir`,
    `disenar`, `redundancia`, `revalidar`, `repaso`, `fuentes`, `revisar`,
    `visto`. Sólo `disenar` casa en los dos vocabularios.

    O sea que filtrar por `paso` **dejaría 23 instrucciones de Jaime sin llegar
    a nadie**, que es peor que llegar a todos. Así que aquí se mide y se dice;
    juntar los dos vocabularios es una decisión, y se toma mirando esta lista.
    """
    reales = _pasos_reales()
    cx = _con()
    filas = cx.execute(
        "select paso, count(*) n from instruccion"
        " where paso is not null and estado not in"
        " ('en la maquina', 'descartada') group by paso").fetchall()
    cx.close()
    return {f["paso"]: f["n"] for f in filas if f["paso"] not in reales}


def todas():
    cx = _con()
    filas = [dict(f) for f in cx.execute(
        "select * from instruccion order by estado, veces desc, id")]
    cx.close()
    return filas


def por_ambito(todas):
    """Las de la pieza en el pedido; las de todo el lote, por referencia (C-564).

    Son 114 de 118 renglones identicos en cada pedido de cada pieza: se leen
    una vez por ronda desde `work/servicio/_comun/`, no una por pedido.
    """
    from .volcado import _en_renglones, comun

    if not isinstance(todas, list):
        return todas
    lote = [i for i in todas if isinstance(i, dict) and i.get("ambito") == "lote"]
    suyas = [i for i in todas if i not in lote]
    return {"de_todo_el_lote": comun("instrucciones", _en_renglones(lote)),
            "de_esta_pieza": _en_renglones(suyas)}
