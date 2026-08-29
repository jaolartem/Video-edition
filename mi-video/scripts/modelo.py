"""El modelo de datos: valida, migra y cierra el ciclo de vida de una pieza.

Regla de Jaime: *«valida el modelo de datos y agrega lo que haga falta, une y
crea, optimiza el modelo, lo mínimo básico es tercer nivel de normalización»*. Y
el ciclo que tiene que soportar, con sus palabras:

> *«Copio un vídeo de un lado, sale el vídeo renderizado, se aprueba uno por
> uno, y de cada versión aprobada me das el audio virgen para pasarlo por Adobe
> Podcast, lo reemplazas y lo subimos.»*

## Lo que faltaba, y no era poco

El modelo sabía **cómo se decide** una pieza —libretos, etapas, candidatos,
elecciones, descripciones— y no sabía **nada de su vida después**. No existía la
versión, así que «la versión aprobada» no se podía nombrar; ni la aprobación, así
que «se aprueba uno por uno» vivía en el chat; ni el audio por versión, así que
cuál WAV corresponde a qué corte era cosa de mirar fechas; ni la publicación.

Sin eso, el ciclo que él describe **no se puede ejecutar dos veces igual**, que
es justo lo que un pipeline tiene que garantizar.

## Las cuatro tablas nuevas

    version       cada render de una pieza, con la huella de SU corte
    aprobacion    el veredicto sobre una version concreta
    audio_version el virgen que sale y el limpio que vuelve, atados a la version
    publicacion   donde y cuando se subio

La **huella** es lo que hace que esto no mienta: se calcula sobre los cortes y
sus cintas, no sobre el fichero. Dos renders del mismo corte son la misma
versión aunque el JSON se haya reescrito; un corte distinto es otra versión
aunque el fichero pese lo mismo. Es la misma lección que la caducidad por
contenido: comparar lo que significa, no lo que ocupa.

## Tercer nivel

Se arregla lo que estaba en segunda: `revision`, `escena_desc`, `densidad`,
`descartado` y `banco` referían al vídeo **por texto** (`video_slug`), no por
clave. Un slug repetido en cinco tablas es cinco sitios donde se puede escribir
mal y ninguno donde salte. Se les añade `video_id` con clave foránea y se
rellena; la columna de texto se conserva por compatibilidad, pero la que manda
es la clave.

    python scripts/modelo.py            # valida y dice que falta
    python scripts/modelo.py --migrar   # crea y rellena lo que falte
"""
import argparse
import datetime
import hashlib
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))

BASE = "ads/decisiones.db"

NUEVAS = """
-- El ciclo de vida de una pieza, que no existia en el modelo
--
-- Jaime: *«copio un video de un lado, sale el video renderizado, se aprueba uno
-- por uno, y de cada version aprobada me das el audio virgen para pasarlo por
-- Adobe Podcast, lo reemplazas y lo subimos»*. Nada de eso se podia nombrar.

CREATE TABLE IF NOT EXISTS version (
  id         INTEGER PRIMARY KEY,
  video_id   INTEGER NOT NULL REFERENCES video(id),
  n          INTEGER NOT NULL,
  -- **La huella es del CORTE, no del fichero.** Dos renders del mismo montaje
  -- son la misma version aunque el JSON se reescriba; un corte distinto es otra
  -- aunque el fichero pese igual. Comparar lo que significa, no lo que ocupa.
  huella     TEXT NOT NULL,
  duracion_s REAL,
  fichero    TEXT,
  -- El commit donde vive este estado. Git es el que sabe si algo se movio, asi
  -- que la version apunta ahi en vez de duplicar su trabajo.
  commit_git TEXT,
  fecha      TEXT NOT NULL,
  UNIQUE (video_id, n),
  UNIQUE (video_id, huella)
);

CREATE TABLE IF NOT EXISTS aprobacion (
  version_id INTEGER PRIMARY KEY REFERENCES version(id),
  veredicto  TEXT NOT NULL CHECK (veredicto IN ('aprobada','rehacer')),
  quien      TEXT NOT NULL,
  notas      TEXT,
  fecha      TEXT NOT NULL
);

-- El audio de una version: el virgen que sale y el limpio que vuelve.
--
-- Va atado a la VERSION y no al video porque un corte distinto es otro audio:
-- reintegrar el limpio de una version en otra desincroniza la pieza entera, y
-- eso no se ve hasta el render. `duracion_s` de las dos permite comprobarlo
-- antes de tocar nada.
CREATE TABLE IF NOT EXISTS audio_version (
  version_id INTEGER PRIMARY KEY REFERENCES version(id),
  virgen     TEXT NOT NULL,
  virgen_s   REAL,
  limpio     TEXT,
  limpio_s   REAL,
  integrado  TEXT,
  fecha      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publicacion (
  version_id INTEGER PRIMARY KEY REFERENCES version(id),
  destino    TEXT NOT NULL,
  fecha      TEXT NOT NULL
);

-- Lo que se midio de cada version. Cierra el ciclo por el otro lado: la version
-- no solo existe, tiene numeros que se pueden comparar entre piezas y entre
-- tandas. Usa `tipo_medicion`, que llevaba meses en el esquema sin que nadie la
-- leyera.
CREATE TABLE IF NOT EXISTS medicion (
  version_id      INTEGER NOT NULL REFERENCES version(id),
  tipo_id         INTEGER NOT NULL REFERENCES tipo_medicion(id),
  valor           REAL NOT NULL,
  fecha           TEXT NOT NULL,
  PRIMARY KEY (version_id, tipo_id)
);

CREATE INDEX IF NOT EXISTS version_video ON version (video_id, n);

-- La maquina de estados: la etiqueta llama al servicio
--
-- Jaime, corrigiendo la arquitectura: *«eso forma parte del modelo: las fases y
-- los estados son etiquetas que llaman servicios; si una etiqueta esta en un
-- paso, entonces avanza automaticamente en ese paso, y si no avanza pues para
-- eso es el log»*.
--
-- El pipeline era una **secuencia**: un bash que corria los pasos en orden, todos,
-- siempre. Eso obliga a que cada paso sepa saltarse solo, y a que el orden viva
-- en un fichero de texto en vez de en el modelo. Con la maquina, la pieza lleva
-- su etiqueta, la etiqueta dice que servicio la mueve, y **el orden es un dato**.
--
-- `fase` ya existia con seis estados y solo llegaba hasta `cortado`: no cubria
-- ni la aprobacion, ni el audio, ni la publicacion, que es justo el ciclo que
-- hay que poder repetir.
ALTER_FASE_SERVICIO;

-- En que fase esta cada pieza AHORA, y como llego.
--
-- Se guarda el historial y no solo el ultimo estado: cuando una pieza se atasca,
-- lo que hace falta saber es cuantas veces intento pasar y por que no pudo, y
-- eso con un solo campo no se ve.
CREATE TABLE IF NOT EXISTS video_fase (
  id        INTEGER PRIMARY KEY,
  video_id  INTEGER NOT NULL REFERENCES video(id),
  fase_id   INTEGER NOT NULL REFERENCES fase(id),
  entro     TEXT NOT NULL,
  -- Vacio si avanzo limpio; el motivo si se quedo. **Un estado que no avanza
  -- sin motivo escrito es un estado que nadie puede desatascar.**
  por_que   TEXT
);

CREATE INDEX IF NOT EXISTS video_fase_ult ON video_fase (video_id, id DESC);
"""

# El ciclo completo, en orden. Cada fase dice **que servicio la mueve a la
# siguiente**: la etiqueta llama al servicio, no al reves.
CICLO = [
    (1, "catalogado", "scripts/transcribir.py --barato"),
    (2, "elegido", "scripts/seleccionar.py {n} --edl"),
    (3, "afinado", "scripts/transcribir.py --elegidos {n}"),
    (4, "depurado", "scripts/depurar.py {n}"),
    (5, "sin_redundancia", "scripts/redundancia.py {n}"),
    (6, "cosido", "scripts/costuras.py {n}"),
    (7, "descrito", "scripts/describir.mjs {n}"),
    (8, "cortado", "scripts/cortar.py {n}"),
    (9, "voz_entregada", "scripts/voz-limpia.py --exportar {n}"),
    (10, "verificado", "scripts/verificar.py {n}"),
    (11, "montado", "scripts/montar.sh {n}"),
    (12, "aprobado", None),          # lo mueve Jaime, no un servicio
    (13, "voz_limpia", "scripts/voz-limpia.py {n}"),
    (14, "masterizado", "scripts/musica.sh {n}"),
    (15, "publicado", "scripts/publicar.py --finales {n}"),
]

# Las que referian al video por texto. Segunda forma normal: el slug repetido en
# cinco tablas es cinco sitios donde escribirlo mal y ninguno donde saltar.
POR_SLUG = ("revision", "escena_desc", "densidad", "descartado")

# Vacias y sin nadie que las lea. Una tabla que no se usa no es inofensiva:
# aparece en el esquema, alguien la lee como si significara algo, y ahi empieza
# el error.
MUERTAS = ("tarjeta_bloque", "tarjeta_remate", "render", "escena")

# **Y tres que parecian muertas y son vocabularios sin usar.**
#
# `tipo_medicion` trae exactamente lo que `musica.sh` mide en cada render
# —sonoridad, pico real, muestras saturadas, duracion—; `estado_decision` es el
# vocabulario de `ads/estado.json`; `decidido_por` es el `quien` que hoy viaja
# como texto suelto en cuatro tablas.
#
# Borrarlas habria sido lo comodo. Lo correcto es **usarlas**: eso es unir en vez
# de crear, que es lo que Jaime pidio. Un vocabulario en una tabla es un sitio
# donde el valor esta escrito bien; el mismo vocabulario repetido como cadena en
# cuatro sitios son cuatro sitios donde puede estar mal.
VOCABULARIOS = ("tipo_medicion", "estado_decision", "decidido_por")


def _con():
    c = sqlite3.connect(BASE)
    c.row_factory = sqlite3.Row
    c.execute("pragma foreign_keys = on")
    return c


def huella_edl(slug):
    """La huella del corte de una pieza. Ver el comentario de `version.huella`."""
    p = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(p):
        return None
    e = json.load(open(p, encoding="utf-8"))
    return hashlib.sha1(json.dumps(
        [[round(a, 3), round(b, 3), d.get("toma"), d.get("beat")]
         for (a, b), d in zip(e["segmentos"], e["detalle"])],
        ensure_ascii=False).encode("utf-8")).hexdigest()[:12]


def validar():
    """Qué le falta al modelo. Lista vacía es que está entero."""
    con = _con()
    hay = {r[0] for r in con.execute(
        "select name from sqlite_master where type='table'")}
    mal = []
    for t in ("version", "aprobacion", "audio_version", "publicacion"):
        if t not in hay:
            mal.append(f"falta la tabla «{t}» — el ciclo de vida no se puede"
                       f" registrar")
    for t in POR_SLUG:
        if t in hay:
            cols = {r[1] for r in con.execute(f"pragma table_info({t})")}
            if "video_id" not in cols:
                mal.append(f"«{t}» refiere al video por texto y no por clave"
                           f" (2NF)")
    vivas = [t for t in MUERTAS if t in hay]
    if vivas:
        mal.append(f"tablas vacias y sin uso, confunden el esquema: {vivas}")
    if "medicion" not in hay:
        mal.append("falta «medicion»: lo que se mide de cada render no se guarda"
                   " en ningun sitio, asi que no se puede comparar entre tandas")
    sin_usar = [t for t in VOCABULARIOS if t in hay and not con.execute(
        f"select count(*) from {t}").fetchone()[0]]
    if sin_usar:
        mal.append(f"vocabularios vacios: {sin_usar}")
    con.close()
    return mal


def migrar():
    con = _con()
    cols = {r[1] for r in con.execute("pragma table_info(fase)")}
    alter = ""
    if "servicio" not in cols:
        alter += "ALTER TABLE fase ADD COLUMN servicio TEXT;"
    con.executescript(NUEVAS.replace("ALTER_FASE_SERVICIO;", alter))
    # El ciclo, idempotente: se corrige el nombre y el servicio de las que ya
    # estan y se anaden las que faltan.
    for orden, nombre, serv in CICLO:
        ya = con.execute("select id from fase where nombre = ?",
                         (nombre,)).fetchone()
        if ya:
            con.execute("update fase set orden = ?, servicio = ? where id = ?",
                        (orden, serv, ya["id"]))
        else:
            con.execute("insert into fase (nombre, orden, servicio)"
                        " values (?,?,?)", (nombre, orden, serv))
    hecho = []
    # Clave foranea al video donde habia texto.
    vid = {r["slug"]: r["id"] for r in con.execute("select id, slug from video")}
    for t in POR_SLUG:
        cols = {r[1] for r in con.execute(f"pragma table_info({t})")}
        if not cols or "video_id" in cols:
            continue
        con.execute(f"alter table {t} add column video_id INTEGER"
                    f" REFERENCES video(id)")
        for slug, i in vid.items():
            con.execute(f"update {t} set video_id = ? where video_slug = ?",
                        (i, slug))
        hecho.append(f"{t}.video_id")
    for t in MUERTAS:
        try:
            n = con.execute(f"select count(*) from {t}").fetchone()[0]
            if n == 0:
                con.execute(f"drop table {t}")
                hecho.append(f"-{t}")
        except sqlite3.OperationalError:
            pass
    con.commit()
    con.close()
    return hecho


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
    dur = None
    p = f"ads/{slug}/edl-sell.json"
    if os.path.exists(p):
        dur = json.load(open(p, encoding="utf-8")).get("duracion_montada_s")
    cur = con.execute(
        "insert into version (video_id, n, huella, duracion_s, fichero,"
        " commit_git, fecha) values (?,?,?,?,?,?,?)",
        (v["id"], n, h, dur, fichero, commit,
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    vid = cur.lastrowid
    con.close()
    return vid


def medir(version_id, valores):
    """Guarda lo medido de una version, por su vocabulario.

    `valores` es `{"sonoridad": -14.1, "pico_real": -1.3, ...}` con los nombres
    de `tipo_medicion`. Un nombre que no este en el vocabulario **no se
    inventa**: se ignora y se dice, porque una medida sin tipo declarado es una
    medida que nadie sabra interpretar dentro de un mes.
    """
    con = _con()
    tipos = {r["nombre"]: r["id"] for r in con.execute(
        "select id, nombre from tipo_medicion")}
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    fuera = []
    for k, v in valores.items():
        if k not in tipos:
            fuera.append(k)
            continue
        con.execute("insert or replace into medicion (version_id, tipo_id,"
                    " valor, fecha) values (?,?,?,?)",
                    (version_id, tipos[k], float(v), ahora))
    con.commit()
    con.close()
    return fuera


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--migrar", action="store_true")
    ap.add_argument("--registrar", action="store_true",
                    help="apunta el corte actual de las seis como version")
    a = ap.parse_args()
    if a.migrar:
        hecho = migrar()
        print("modelo migrado:", ", ".join(hecho) if hecho else "nada que hacer")
    if a.registrar:
        for n in range(1, 7):
            slug = f"reel-{n:02d}"
            v = registrar_version(slug)
            print(f"{slug}: version {v}" if v else f"{slug}: sin EDL")
        return
    mal = validar()
    if not mal:
        print("modelo: entero")
        return
    print(f"modelo: {len(mal)} cosa(s) que arreglar")
    for m in mal:
        print(f"    · {m}")
    print("\n  python scripts/modelo.py --migrar")


if __name__ == "__main__":
    main()
