"""El log de lo que pasa mientras corre, para no enterarse tarde.

Regla de Jaime: *«haz un log de errores, hay que estar pendientes de lo que
sucede»*. Y es la que le faltaba al paso 1: la transcripción tarda media hora por
toma, corre en segundo plano y **lo que sale mal ahí no lo ve nadie** — una
ventana que devuelve vacío, un tramo sin candidata, whisper saliendo con error.
Todo eso pasaba y el único rastro era una cifra resumida al final.

Va a la base, que es la memoria del proyecto, y no a un fichero suelto: así una
incidencia de hace tres días sigue estando cuando aparece el defecto que
explica.

    python scripts/registro.py            # lo de hoy
    python scripts/registro.py --todo     # todo
    python scripts/registro.py --limpiar  # borra lo anotado

Los niveles, y el criterio para elegirlos:

- `error`  — algo no se hizo. Un proceso que sale mal, un fichero que falta.
- `aviso`  — se hizo, pero hay motivo para dudar. Acuerdo bajo entre pasadas,
             palabra estirada, candidata tirada por atasco.
- `nota`   — pasó algo que conviene poder contar después. Cuántas ventanas,
             cuánto tardó.

Lo que **no** va aquí: las decisiones. Ésas viven en `asignacion` y en
`docs/correcciones.md`. Esto es lo que ocurrió, no lo que se decidió.
"""
import argparse
import datetime
import os
import sqlite3
import sys

import basedatos

# **Lo que este proyecto escribe es UTF-8, lo diga Windows o no.**
#
# La consola de Windows es cp1252 y Python escribe en ella tal cual: **un solo
# caracter fuera de esa pagina mata el paso entero**. Hoy paso tres veces, en
# tres sitios distintos, y la tercera se llevo el despachador con las siete
# piezas en marcha — por una flecha, «→», en una linea de log.
#
# No es un fallo del texto: es que el canal de diagnostico se rompe justo cuando
# tiene algo que contar, y lo que se pierde es el motivo. Los textos de este
# proyecto son espanoles y llevan tildes, comillas angulares y flechas; escribir
# en cp1252 no era una opcion, era una bomba con retardo.
#
# Va aqui porque `registro` es quien manda lo que se escribe, y lo importa todo
# el que escribe algo. `errors="replace"` porque perder un caracter de un mensaje
# es barato; perder el mensaje —y con el, la corrida— no.
for _canal in (sys.stdout, sys.stderr):
    try:
        _canal.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
import sys

BASE = os.path.join("ads", "decisiones.db")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS incidencia (
  id      INTEGER PRIMARY KEY,
  cuando  TEXT NOT NULL,
  nivel   TEXT NOT NULL CHECK (nivel IN ('error','aviso','nota')),
  script  TEXT NOT NULL,
  toma    TEXT,
  asunto  TEXT NOT NULL,
  detalle TEXT
);
CREATE INDEX IF NOT EXISTS incidencia_cuando ON incidencia (cuando);
"""


def _con():
    con = basedatos.abrir(BASE)
    con.executescript(ESQUEMA)
    return con


def anota(nivel, script, asunto, toma=None, detalle=None, eco=True):
    """Deja constancia. Nunca revienta: un log que tumba el proceso no sirve."""
    try:
        con = _con()
        con.execute(
            "insert into incidencia (cuando, nivel, script, toma, asunto, detalle)"
            " values (?,?,?,?,?,?)",
            (datetime.datetime.now().isoformat(timespec="seconds"),
             nivel, script, toma, asunto,
             None if detalle is None else str(detalle)))
        con.commit()
        con.close()
    except Exception as e:                      # noqa: BLE001
        print(f"  [registro no disponible: {e}]", file=sys.stderr)
    if eco and nivel != "nota":
        marca = "ERROR" if nivel == "error" else "aviso"
        print(f"  [{marca}] {asunto}" + (f" · {detalle}" if detalle else ""),
              flush=True)


def error(script, asunto, **kw):
    anota("error", script, asunto, **kw)


def aviso(script, asunto, **kw):
    anota("aviso", script, asunto, **kw)


def nota(script, asunto, **kw):
    anota("nota", script, asunto, **kw)


def resumen(desde=None):
    """Lo anotado, agrupado, para mirarlo de un vistazo."""
    con = _con()
    q = ("select nivel, script, asunto, count(*), max(cuando)"
         " from incidencia" + (" where cuando >= ?" if desde else "") +
         " group by nivel, script, asunto"
         " order by case nivel when 'error' then 0 when 'aviso' then 1 else 2 end,"
         " count(*) desc")
    filas = con.execute(q, (desde,) if desde else ()).fetchall()
    if not filas:
        print("sin incidencias" + (" hoy" if desde else ""))
    for nivel, script, asunto, n, ult in filas:
        print(f"  {nivel:<5} {n:>4}x  {script:<16} {asunto}   (ult. {ult[11:16]})")
    con.close()
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true", help="no solo lo de hoy")
    # **Escribir desde fuera de Python.** `guardas.mjs` es el otro sitio que
    # para la linea, y es Node: sin esto imprimia y salia sin dejar fila, que
    # es justo lo que Jaime pidio cerrar — *«no solo necesito que pare,
    # necesito un log»*. Tres argumentos y ya; no es una segunda puerta, es la
    # misma `anota` con una linea de comandos.
    ap.add_argument("--anota", nargs=4,
                    metavar=("NIVEL", "SCRIPT", "ASUNTO", "DETALLE"))
    ap.add_argument("--limpiar", action="store_true")
    ap.add_argument("--detalle", help="las lineas de un asunto concreto")
    a = ap.parse_args()
    if a.anota:
        nivel, script, asunto, detalle = a.anota
        anota(nivel, script, asunto, detalle=detalle, eco=False)
        return
    if a.limpiar:
        con = _con()
        n = con.execute("select count(*) from incidencia").fetchone()[0]
        con.execute("delete from incidencia")
        con.commit()
        con.close()
        print(f"borradas {n} incidencias")
        return
    if a.detalle:
        con = _con()
        for c, ni, t, d in con.execute(
                "select cuando, nivel, toma, detalle from incidencia"
                " where asunto = ? order by cuando", (a.detalle,)):
            print(f"  {c[11:19]} {ni:<5} {t or '':<16} {d or ''}")
        con.close()
        return
    hoy = datetime.date.today().isoformat()
    resumen(None if a.todo else hoy)


if __name__ == "__main__":
    main()


def atascadas(ultimo):
    """Dice que piezas se quedaron atascadas mientras las demas seguian.

    Desde C-370 una tanda no se planta por una pieza —*«apagar el reparto por
    una es dejar de repartir»*—, y eso abre un riesgo nuevo: que se quede
    atascada **en silencio** y el parte se lea como si todo hubiera ido. El
    reparto sigue; el aviso no se calla.

    Vive aqui y no en `avanzar` porque informar no es enrutar: es la misma
    frontera que separa medir de decidir.
    """
    malas = [r for r in ultimo.values()
             if "lleva dos intentos" in (r.get("motivo") or "")]
    if not malas:
        return 0
    print("")
    print(f"{len(malas)} pieza(s) atascadas — las demas siguieron:")
    for r in malas:
        print(f"  · {r['slug']}: {r['motivo']}")
    print("Corrige eso y vuelve a correr; el detalle esta en el log.")
    return len(malas)
