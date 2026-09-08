"""El estado de una pieza, en un fichero que se puede leer y escribir.

Jaime, 7-9-2026, sobre por qué la línea no anda sola: *«el que hace que avance es
el agente en bash, está mal; debe avanzar por etiquetas que activen procesos y
agentes. Se necesita un JSON por vídeo que diga el estado, y que cada agente
pueda modificarlo conforme avanza: un proceso completado, un cambio de estado; un
cambio de estado activa un nuevo proceso. Inteligencia artificial sólo cuando sea
necesario»*.

## Qué cambia respecto de lo que había

El estado ya existía —`video_fase` en la base— y por eso esto **no lo sustituye:
lo publica**. La diferencia no es dónde se guarda, es **quién puede tocarlo**.

Los dos oficios de la línea trabajan con `Read` y `Write` y nada más: no tienen
con qué abrir la base, a propósito. Así que hasta hoy un agente terminaba su
trabajo y **no podía decirlo** — hacía falta alguien en medio que leyera su
respuesta y moviera la pieza. Ese alguien era yo, y por eso la línea no andaba
sin mí.

Un fichero por pieza cierra ese hueco: el que termina escribe que terminó, y el
cambio es lo que enciende el paso siguiente.

## Y no decide nada

Esto no elige la etapa siguiente ni ejecuta nada: **dice dónde está la pieza y
qué la espera**. `dominio/fase.py` sigue siendo el camino y `avanzar.py` sigue
siendo quien recorre. Aquí sólo se escribe lo que ya pasó, y en un sitio donde lo
lea quien no puede abrir la base.

    from dominio import estado
    estado.escribe("reel-03")          # vuelca lo que dice la base
    estado.marca("reel-03", "disenado", "hecho", quien="disenador")
"""
from __future__ import annotations

import datetime
import json
import os

#: La carpeta `mi-video`, sacada de este fichero y no del cwd — tres
#: `dirname`, y se cuentan: `scripts/dominio/estado.py`.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Dónde vive el estado de cada pieza. Junto a su EDL, que es el otro artefacto
#: que la describe: quien mira la carpeta de una pieza ve las dos cosas.
def ruta(slug):
    return os.path.join(RAIZ, "ads", slug, "estado.json")


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def lee(slug):
    """Lo que hay escrito, o el esqueleto si todavía no hay nada."""
    r = ruta(slug)
    if os.path.exists(r):
        try:
            return json.load(open(r, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"pieza": slug, "etapa": None, "desde": None, "espera": None,
            "abiertos": [], "hecho": [], "log": []}


def _guarda(slug, d):
    r = ruta(slug)
    os.makedirs(os.path.dirname(r), exist_ok=True)
    # **El log sólo baja de tamaño por el final.** Es el recorrido de la pieza y
    # es lo que se mira cuando algo salió mal; recortarlo por arriba perdería
    # justo el principio, que es donde empieza la explicación.
    d["log"] = d.get("log", [])[-60:]
    with open(r, "w", encoding="utf-8", newline="\n") as h:
        json.dump(d, h, ensure_ascii=False, indent=1)
    return d


def escribe(slug):
    """Vuelca a disco lo que la base dice hoy de esa pieza.

    Es el puente de una sola dirección: la base manda, esto la publica. Se llama
    cuando la pieza se mueve, para que el fichero no envejezca — un estado viejo
    es peor que no tenerlo, porque parece verdad.
    """
    from . import fase as _f
    from . import ticket as _t

    d = lee(slug)
    try:
        con = _f._con()
        r = con.execute(
            "select f.nombre, vf.entro from video_fase vf"
            " join fase f on f.id = vf.fase_id join video v on v.id = vf.video_id"
            " where v.slug = ? order by vf.entro desc, vf.rowid desc limit 1",
            (slug,)).fetchone()
        con.close()
        if r:
            if d.get("etapa") != r["nombre"]:
                d.setdefault("log", []).append(
                    {"cuando": r["entro"], "etapa": r["nombre"], "que": "entra"})
            d["etapa"], d["desde"] = r["nombre"], r["entro"]
    except Exception:                              # noqa: BLE001
        pass
    try:
        d["abiertos"] = [
            {"id": t["id"], "va_a": t.get("vuelve_a") or "", "beat": t.get("beat"),
             "dice": " ".join((t.get("dijo") or "").split())[:200]}
            for t in _t.abiertos(slug)]
    except Exception:                              # noqa: BLE001
        pass
    # **Y si llego al final, se cierra en vez de guardarse.** Ver `cierra`.
    try:
        from .fase import CICLO
        if d.get("etapa") and d["etapa"] == CICLO[-1][1]:
            cierra(slug, "llego al final del camino")
            return d
    except Exception:                              # noqa: BLE001
        pass
    d["visto_por_ultima_vez"] = _ahora()
    return _guarda(slug, d)


def cierra(slug, por_que="el proceso termino"):
    """Borra el estado de una pieza. **Es memoria de trabajo, no archivo.**

    Jaime, 7-9-2026: *«que se borre cuando se cierre, o cuando se termine el
    proceso»*. Es la misma regla con la que trata el disco: F: es memoria de
    trabajo y al cerrar se vacia; lo que queda es lo final.

    Y no se pierde nada: el recorrido esta en `video_fase`, los tiquets en su
    tabla y las versiones selladas en `version`. Esto era **la vista de lo que
    esta en vuelo**, y una pieza terminada ya no vuela — dejarla ahi convierte
    el tablero en una lista de lo que hubo, que es justo lo que no se mira.
    """
    r = ruta(slug)
    try:
        if os.path.exists(r):
            os.remove(r)
            return True
    except OSError:
        pass
    return False


def espera(slug, quien, que):
    """Deja escrito **a quién espera** la pieza y para qué.

    Es la mitad que faltaba para que un turno pedido se distinga de un atasco.
    El despachador ya lo decía por consola —«espera agente -> disenar/reel-04»—
    y por consola no lo lee nadie dos minutos después.
    """
    d = lee(slug)
    d["espera"] = {"quien": quien, "que": que, "desde": _ahora()}
    d.setdefault("log", []).append(
        {"cuando": _ahora(), "etapa": d.get("etapa"), "que": f"espera a {quien}"})
    return _guarda(slug, d)


def marca(slug, paso, resultado, quien="la linea", nota=""):
    """**Un proceso completado, escrito por quien lo completó.**

    Aquí es donde un agente que sólo tiene `Read` y `Write` puede por fin decir
    que terminó. Antes su respuesta se quedaba en un fichero que sólo la línea
    sabía leer, y hacía falta alguien en medio.

    No mueve la pieza: escribir que un paso acabó y decidir cuál viene después
    son dos cosas, y la segunda es de `fase.py`. Lo que esto hace es que la
    primera **deje rastro** — y un rastro es lo que puede disparar la segunda.
    """
    d = lee(slug)
    if d.get("espera", {}) and (d.get("espera") or {}).get("quien") == quien:
        d["espera"] = None
    fila = {"paso": paso, "resultado": resultado, "quien": quien,
            "cuando": _ahora()}
    if nota:
        fila["nota"] = nota[:400]
    d["hecho"] = [h for h in d.get("hecho", []) if h.get("paso") != paso]
    d["hecho"].append(fila)
    d.setdefault("log", []).append(
        {"cuando": fila["cuando"], "etapa": d.get("etapa"),
         "que": f"{paso}: {resultado} ({quien})"})
    _guarda(slug, d)
    # **Y el cambio enciende el paso siguiente.** Jaime: *«un proceso
    # completado, un cambio de estado; un cambio de estado activa un nuevo
    # proceso»*. Ver `dominio/disparo.py` — un salto, y sin agente en medio:
    # los 18 pasos de codigo del ciclo se encadenan sin encender un modelo.
    if resultado not in ("fallo", "espera"):
        try:
            from . import disparo
            disparo.dispara(slug, f"{paso} lo dejo en «{resultado}»")
        except Exception:                          # noqa: BLE001
            pass
    return lee(slug)


def todas(piezas):
    """El estado de varias piezas, para mirarlas de una vez."""
    return {s: lee(s) for s in piezas}
