"""El motor: la etiqueta llama al servicio y el servicio mueve la etiqueta.

Regla de Jaime, y es de arquitectura: *«las fases y los estados son etiquetas que
llaman servicios; si una etiqueta está en un paso, entonces avanza
automáticamente en ese paso, y si no avanza pues para eso es el log»*.

## Qué cambia respecto a la línea de antes

`pipeline.sh` era una **secuencia**: un bash que corría los pasos en orden,
todos, siempre, para las seis piezas. Eso tiene tres problemas y los tres se
notaron hoy:

- **El orden vivía en un fichero de texto**, no en el modelo. Añadir un paso era
  editar bash y acordarse de dónde ponerlo.
- **Cada paso tenía que saber saltarse solo**, así que la lógica de «esto ya está
  hecho» estaba repetida en once sitios y en cada uno de una manera.
- **Una pieza atascada arrastraba a las demás**, porque la unidad era la corrida
  y no la pieza.

Con la máquina, cada pieza lleva su etiqueta, la etiqueta dice qué servicio la
mueve, y **el orden es un dato**: se cambia en la tabla `fase`, no en el código.

## Y lo que no avanza queda en el log

Un servicio que falla no para el lote: deja la pieza donde estaba, escribe el
motivo en `video_fase.por_que` y en `incidencia`, y las demás siguen. Eso es lo
que él dijo con *«si no avanza pues para eso es el log»* — y es la diferencia
entre un pipeline y un script: el pipeline **sabe dónde se quedó cada cosa**.

Las fases sin servicio —`aprobado`— las mueve Jaime. El motor las respeta: se
para ahí y lo dice, porque no hay nada que ejecutar.

    python scripts/avanzar.py            # mueve todo lo que se pueda mover
    python scripts/avanzar.py 3          # solo el reel 3
    python scripts/avanzar.py --ver      # que haria, sin hacerlo
    python scripts/avanzar.py --paso 1   # un salto por pieza y para
"""
import argparse
import datetime
import os
import shlex
import sqlite3
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    c = sqlite3.connect(BASE)
    c.row_factory = sqlite3.Row
    return c


def fases(con):
    """El ciclo, en orden. Sin las de ámbito fragmento, que son otra cosa."""
    return [r for r in con.execute(
        "select id, nombre, orden, servicio from fase where orden > 0"
        " and nombre <> 'preparado' order by orden")]


def donde(con, video_id):
    """La fase actual de una pieza. Sin historial, es la primera del ciclo."""
    r = con.execute(
        "select f.id, f.nombre, f.orden, f.servicio from video_fase vf"
        " join fase f on f.id = vf.fase_id where vf.video_id = ?"
        " order by vf.id desc limit 1", (video_id,)).fetchone()
    return r


def marcar(con, video_id, fase_id, por_que=None):
    con.execute("insert into video_fase (video_id, fase_id, entro, por_que)"
                " values (?,?,?,?)",
                (video_id, fase_id, datetime.datetime.now().isoformat(
                    timespec="seconds"), por_que))
    con.commit()


def correr(servicio, n):
    """Ejecuta el servicio de una fase. Devuelve `(ok, salida)`.

    El servicio se declara en la tabla con `{n}` donde va el número de reel: el
    modelo sabe **qué** llamar, y esto sólo sabe **cómo**. Un servicio nuevo se
    añade insertando una fila, no tocando este fichero.
    """
    cmd = servicio.format(n=n)
    partes = shlex.split(cmd)
    if partes[0].endswith(".py"):
        partes = [sys.executable] + partes
    elif partes[0].endswith(".mjs"):
        partes = ["node"] + partes
    elif partes[0].endswith(".sh"):
        partes = ["bash"] + partes
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    r = subprocess.run(partes, capture_output=True, text=True, env=env)
    return r.returncode == 0, (r.stdout or "") + (r.stderr or "")


def avanzar(n, ver=False, tope=None):
    """Mueve una pieza tan lejos como pueda. Devuelve dónde se quedó y por qué."""
    con = _con()
    slug = f"reel-{n:02d}"
    v = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        con.close()
        return None
    ciclo = fases(con)
    actual = donde(con, v["id"])
    if actual is None:
        # Sin historial: entra por la primera del ciclo.
        actual = ciclo[0]
        if not ver:
            marcar(con, v["id"], actual["id"])
    saltos = 0
    motivo = None
    while True:
        i = next((k for k, f in enumerate(ciclo) if f["id"] == actual["id"]), None)
        if i is None or i + 1 >= len(ciclo):
            motivo = "final del ciclo"
            break
        siguiente = ciclo[i + 1]
        serv = siguiente["servicio"]
        if not serv:
            # **La fase sin servicio la mueve Jaime.** El motor se para y lo
            # dice: no hay nada que ejecutar, y fingir que si lo hay seria
            # avanzar una pieza que nadie ha aprobado.
            motivo = f"espera a Jaime para pasar a «{siguiente['nombre']}»"
            break
        if ver:
            print(f"  {slug}: {actual['nombre']} -> {siguiente['nombre']}"
                  f"   ({serv.format(n=n)})")
            actual = siguiente
            saltos += 1
            if tope and saltos >= tope:
                break
            continue
        ok, salida = correr(serv, n)
        if not ok:
            motivo = (f"«{siguiente['nombre']}» no paso: "
                      + (salida.strip().splitlines() or ["sin salida"])[-1][:160])
            marcar(con, v["id"], actual["id"], motivo)
            registro.aviso("avanzar", "la pieza no avanza",
                           detalle=f"{slug}: {motivo}", eco=False)
            break
        marcar(con, v["id"], siguiente["id"])
        actual = siguiente
        saltos += 1
        if tope and saltos >= tope:
            motivo = "tope de saltos"
            break
    con.close()
    return {"slug": slug, "fase": actual["nombre"], "saltos": saltos,
            "motivo": motivo}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true", help="que haria, sin hacerlo")
    ap.add_argument("--paso", type=int, metavar="N",
                    help="como mucho N saltos por pieza")
    a = ap.parse_args()
    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        r = avanzar(n, ver=a.ver, tope=a.paso)
        if not r:
            continue
        print(f"{r['slug']}: {r['fase']}"
              + (f"  (+{r['saltos']})" if r["saltos"] else "")
              + (f"  — {r['motivo']}" if r["motivo"] else ""))


if __name__ == "__main__":
    main()
