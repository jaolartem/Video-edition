"""La memoria de trabajo se borra; el sistema se queda.

Regla de Jaime: *«lo de trabajo, en la memoria de trabajo, que la borramos cada
nuevo proyecto»*.

Y hasta ahora estaban mezclados en la misma carpeta, que es el problema: la
decision de que el reel 3 abre en el segundo 27 vale para ESTE lote y no para el
siguiente, mientras que el mecanismo que la tomo vale para los cincuenta. Si
viven juntos, al empezar un proyecto nuevo o se arrastran decisiones viejas o se
borra el sistema por error.

La frontera, y el criterio para trazarla: **¿esto seguiria siendo cierto con
otro material?**

  SISTEMA (se queda)              MEMORIA DE TRABAJO (se borra)
  ─────────────────────────       ──────────────────────────────
  scripts/                        work/            transcripts, cortes, escenas
  src/                            ads/*/           EDL y frames de este lote
  scripts/esquema.sql             ads/estado.json  lo que Jaime juzgo
  CLAUDE.md                       ads/decisiones.db  el catalogo y las elecciones
  docs/correcciones.md            docs/bitacora.md
  docs/playbook.md · ejemplos/    out/

`decisiones.db` es memoria de trabajo aunque duela: **su esquema es sistema y su
contenido no**. Por eso el reinicio la vacia y la vuelve a crear desde
`esquema.sql`, en vez de borrar el fichero — asi lo que se conserva es
exactamente lo que se puede volver a escribir.

    python scripts/proyecto.py                 # dice que borraria
    python scripts/proyecto.py --nuevo NOMBRE  # archiva y reinicia
"""
import argparse
import datetime
import io
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
import rutas  # noqa: E402

TRABAJO = ["work", "out", "docs/bitacora.md"]
DE_LOTE = ["ads/estado.json", "ads/decisiones.db"]


def tam(p):
    if os.path.isfile(p):
        return os.path.getsize(p)
    return sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(p) for f in fs
               if os.path.exists(os.path.join(r, f)))


def rehacer_esquema():
    """Reconstruye la base desde `esquema.sql` conservando los datos.

    **El esquema es codigo, no dato.** Ese fue el fallo del dia: `CREATE TABLE
    IF NOT EXISTS` no altera una tabla que ya existe, asi que `subtitulo` siguio
    con `acuerdo NOT NULL` despues de que el codigo empezara a guardar «acuerdo
    desconocido» — y el guardado reventaba sin que nada dijera por que. Migrar a
    mano tapa el caso concreto y deja vivo el mecanismo.

    Aqui se hace al reves: se crea la base **nueva** desde `esquema.sql`, se
    copian los datos tabla por tabla en las columnas que existan en las dos, y
    la vieja se guarda al lado. Lo que el esquema ya no contempla se pierde a
    proposito y se dice cuanto.
    """
    import sqlite3
    if not os.path.exists("ads/decisiones.db"):
        print("no hay base que rehacer")
        return
    sello = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    viejo = f"ads/decisiones.{sello}.db"
    shutil.copy2("ads/decisiones.db", viejo)

    nueva = "ads/decisiones.nueva.db"
    if os.path.exists(nueva):
        os.remove(nueva)
    con = sqlite3.connect(nueva)
    con.executescript(io.open("scripts/esquema.sql", encoding="utf-8").read())
    con.execute("attach database ? as vieja", (viejo,))
    tablas = [r[0] for r in con.execute(
        "select name from main.sqlite_master where type='table'"
        " and name not like 'sqlite_%'")]
    movidas = 0
    for t in tablas:
        hay = {r[1] for r in con.execute(f"pragma vieja.table_info({t})")}
        if not hay:
            continue
        cols = [r[1] for r in con.execute(f"pragma main.table_info({t})")
                if r[1] in hay]
        if not cols:
            continue
        lista = ",".join(cols)
        try:
            con.execute(f"insert or ignore into main.{t} ({lista})"
                        f" select {lista} from vieja.{t}")
            n = con.execute(f"select count(*) from main.{t}").fetchone()[0]
            if n:
                print(f"  {t:<20} {n:>6} filas")
                movidas += n
        except sqlite3.Error as e:
            print(f"  {t:<20} NO se pudo copiar: {e}")
    con.commit()
    con.execute("detach database vieja")
    con.close()
    os.replace(nueva, "ads/decisiones.db")
    print(f"base rehecha desde esquema.sql · {movidas} filas conservadas"
          f" · la anterior queda en {viejo}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rehacer-esquema", action="store_true",
                    help="recrea la base desde esquema.sql conservando datos")
    ap.add_argument("--nuevo", metavar="NOMBRE",
                    help="archiva el lote actual con ese nombre y reinicia")
    a = ap.parse_args()

    if a.rehacer_esquema:
        rehacer_esquema()
        return

    print("MEMORIA DE TRABAJO (se borra al empezar proyecto)")
    total = 0
    for p in TRABAJO + DE_LOTE + ["ads"]:
        if os.path.exists(p):
            t = tam(p)
            total += t if p != "ads" else 0
            print(f"  {p:<24} {t / 1e6:>9.1f} MB")
    print(f"  {'total':<24} {total / 1e6:>9.1f} MB")
    print("\nSISTEMA (no se toca): scripts/ src/ CLAUDE.md docs/correcciones.md"
          " docs/playbook.md docs/ejemplos/ scripts/esquema.sql")

    if not a.nuevo:
        print("\n(sin --nuevo no se borra nada)")
        return

    sello = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    archivo = os.path.join(rutas.TEMPORAL, "lotes", f"{a.nuevo}-{sello}")
    os.makedirs(archivo, exist_ok=True)
    for p in TRABAJO + DE_LOTE:
        if not os.path.exists(p):
            continue
        d = os.path.join(archivo, p.replace("/", "__"))
        (shutil.copytree if os.path.isdir(p) else shutil.copy2)(p, d)
    print(f"\narchivado en {archivo}")

    for p in TRABAJO:
        if os.path.exists(p):
            (shutil.rmtree if os.path.isdir(p) else os.remove)(p)
    for p in DE_LOTE:
        if os.path.exists(p):
            os.remove(p)
    # La base se vuelve a crear vacia: el esquema es sistema, el contenido no.
    os.makedirs("ads", exist_ok=True)
    con = sqlite3.connect("ads/decisiones.db")
    con.executescript(io.open("scripts/esquema.sql", encoding="utf-8").read())
    con.commit()
    con.close()
    print(f"memoria de trabajo vacia · base recreada desde esquema.sql"
          f" · proyecto «{a.nuevo}» listo")


if __name__ == "__main__":
    main()
