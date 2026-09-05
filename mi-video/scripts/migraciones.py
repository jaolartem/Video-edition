"""Los cambios que ya se le hicieron al modelo, **uno por función**.

Regla de Jaime, y es la que gobierna este fichero: *«si te doy instrucciones
cambias la máquina, no la rehaces»*. Una migración es exactamente eso — un
cambio, con su motivo escrito, que se puede aplicar sobre lo que ya hay sin
regenerarlo. Por eso cada cambio histórico es una función con nombre y no una
línea suelta dentro de un `migrar()` de cincuenta.

## Qué hay aquí y qué no

Aquí está **lo que cambia la base**. Lo que dice qué forma tiene está en
`esquema-modelo.sql`, y lo que comprueba que se aplicó, en `modelo.validar()`.
Eran las tres cosas en el mismo fichero de 473 líneas, y la del medio —el DDL—
ocupaba 249 de ellas.

## Todas son idempotentes, y no por elegancia

`python scripts/modelo.py --migrar` lo corre la línea, no una persona: se
ejecuta en cada pasada del motor sobre seis piezas. Una migración que se aplica
dos veces y la segunda hace algo es una avería que aparece el día que nadie la
está mirando. Por eso cada función mira primero si ya está hecha y devuelve
`False`.

## Y una lista de tablas escrita una vez

`POR_SLUG` y `MUERTAS` viven aquí porque son el objetivo de una migración —qué
tablas hay que reatar por clave y cuáles hay que tirar—, y `modelo.validar()`
las importa de aquí para comprobar el resultado. Escritas en los dos sitios
serían dos listas: el día que una tabla saliera de una y no de la otra, migrar
y validar dejarían de hablar de lo mismo y las dos parecerían correctas.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import basedatos  # noqa: E402
from dominio.fase import CICLO  # noqa: E402

#: El DDL. Al lado de `esquema.sql`, que es donde se busca un `CREATE TABLE`.
ESQUEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "esquema-modelo.sql")

# Las que referian al video por texto. Segunda forma normal: el slug repetido en
# cinco tablas es cinco sitios donde escribirlo mal y ninguno donde saltar.
POR_SLUG = ("revision", "escena_desc", "densidad", "descartado")

# Vacias y sin nadie que las lea. Una tabla que no se usa no es inofensiva:
# aparece en el esquema, alguien la lee como si significara algo, y ahi empieza
# el error.
MUERTAS = ("tarjeta_bloque", "tarjeta_remate", "render", "escena")

# La escalera que fijo Jaime el 29 de agosto de 2026, corrida para arrancar hoy.
# El Early Bird se conserva como fila pasada: es el ancla.
ESCALERA = [
    (10, None, "2026-08-28", 1, "Early Bird — fila pasada, ancla"),
    (20, "2026-08-29", "2026-09-04", 0, None),
    (30, "2026-09-05", "2026-09-11", 0, None),
    (40, "2026-09-12", "2026-09-21T11:30", 0, "cierra con el evento"),
]


def _con():
    c = basedatos.abrir()
    c.row_factory = sqlite3.Row
    c.execute("pragma foreign_keys = on")
    return c


def _fase_servicio(con):
    """`fase` gana la columna que dice **qué servicio mueve la pieza**.

    Es la mitad en Python de lo que el comentario de `esquema-modelo.sql`
    explica: la etiqueta llama al servicio, no al revés. Vivía dentro del propio
    DDL como el marcador `ALTER_FASE_SERVICIO;`, una cadena que `migrar()`
    sustituía por un `ALTER TABLE` o por nada antes de ejecutar el script.

    Ese apaño existía porque SQLite no sabe añadir una columna sólo si falta, y
    obligaba a que el esquema fuese una plantilla en vez de SQL — así no podía
    salir del fichero de Python. Aquí es lo que siempre fue: una migración.
    """
    cols = {r[1] for r in con.execute("pragma table_info(fase)")}
    if "servicio" in cols:
        return False
    con.execute("ALTER TABLE fase ADD COLUMN servicio TEXT")
    return True


def esquema(con):
    """Las tablas que el modelo añade. Todo `IF NOT EXISTS`: repetir no hace nada."""
    con.executescript(open(ESQUEMA, encoding="utf-8").read())


def _revision_estructurada(con):
    """Una nota deja de ser prosa: dice de que PIEZA, que ETAPA y que TEMA habla.

    Jaime, viendo 130 escaladas: *«casi todos los que me han presentado son
    repeticiones de lo mismo»*, y despues: *«hazlo estructurado»*.

    El problema no era el volumen: era que la misma observacion, remedida en cada
    corrida, entraba como nota nueva porque la clave de deduplicacion miraba las
    primeras catorce palabras del texto. «El gancho abre plano: la etapa 1 puntua
    0,71» y «El gancho abre tibio: la etapa 1 puntua 0,71» son la misma nota y
    ninguna clave de texto las une — cambia el adjetivo y cambia la medida.

    Con `etapa` y `tema` en columnas, la clave es exacta: una pieza, una etapa, un
    tema es UNA nota, y las vueltas siguientes suben `veces` en vez de apilar.
    """
    cols = {r[1] for r in con.execute("pragma table_info(revision)")}
    for c, tipo in (("etapa", "integer"), ("tema", "text"), ("medida", "real")):
        if c not in cols:
            con.execute(f"alter table revision add column {c} {tipo}")
    con.execute("create index if not exists idx_revision_tema"
                " on revision (video_slug, tema, etapa)")


def _escena_voz(con):
    """`escena_desc` gana la columna donde se declara el tratamiento de voz.

    Jaime: *«que cambie mi voz en los punchlines»*. Es una decision sobre el
    material de esa etapa —como `camara`— y por eso vive en su propia columna y
    no dentro del JSON de la camara: son dos cosas distintas, y una columna que
    significa dos cosas es la averia que este proyecto paga mas cara.

    La lee `dominio/remate.py` y la escribe `servicios/disenar.aplicar`. Sin la
    columna el disenador declararia y el paso de audio no leeria nada, que es
    declarar sin implementar otra vez.
    """
    cols = {r[1] for r in con.execute("pragma table_info(escena_desc)")}
    # Sin tabla no hay columna que anadir: `db.py` la crea con `esquema.sql` y
    # esto corre antes. Devolver `False` en vez de reventar es lo que mantiene
    # la migracion idempotente en una base recien nacida.
    if not cols or "voz" in cols:
        return False
    con.execute("ALTER TABLE escena_desc ADD COLUMN voz TEXT")
    return True


def _corte_fijo_etapa(con):
    """`corte_fijo` deja de servir solo para la apertura y el cierre.

    La composicion sabe decir «esta etapa no entrega y la toma buena esta en el
    segundo 516», y no habia donde declararlo: el CHECK solo admitia `apertura`
    y `cierre`. Aplicar esa decision era editar el EDL a mano — el agujero por
    el que este proyecto pierde el estado.

    Se anaden tambien `toma` —el tramo bueno puede estar en OTRA cinta, y sin
    esa columna el fijado apuntaria a la del video—, y `quien`/`fecha`, porque
    una decision declarada sin autor no se puede discutir despues.

    SQLite no sabe alterar un CHECK, asi que se reconstruye la tabla. Las 13
    filas que hay se conservan.
    """
    cols = {r[1] for r in con.execute("pragma table_info(corte_fijo)")}
    if "toma" in cols:
        return False
    con.executescript("""
      CREATE TABLE corte_fijo_nuevo (
        id       INTEGER PRIMARY KEY,
        video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
        papel    TEXT NOT NULL CHECK (papel IN ('apertura','cierre','etapa')),
        -- En `etapa` es el numero de beat; en apertura/cierre, el orden.
        orden    INTEGER NOT NULL DEFAULT 0,
        desde    REAL NOT NULL,
        hasta    REAL NOT NULL,
        toma     TEXT,
        por_que  TEXT,
        quien    TEXT,
        fecha    TEXT,
        -- Varios tramos por etapa: la idea puede vivir en dos sitios de
        -- la cinta, y con la clave sin `desde` el segundo pisaba al primero.
        UNIQUE (video_id, papel, orden, desde),
        CHECK (hasta > desde)
      );
      INSERT INTO corte_fijo_nuevo (id, video_id, papel, orden, desde, hasta,
                                    por_que)
        SELECT id, video_id, papel, orden, desde, hasta, por_que
          FROM corte_fijo;
      DROP TABLE corte_fijo;
      ALTER TABLE corte_fijo_nuevo RENAME TO corte_fijo;
    """)
    return True


def _corte_fijo_huella(con):
    """Una declaracion guarda **contra que texto** se decidio.

    `corte_fijo` guardaba el tramo, el porque, el autor y la fecha. Lo que no
    guardaba era la prueba, y por eso una declaracion sobrevivia a que la prueba
    cambiara: al reparar `20260825_225808` aparecieron 194 s de habla que no
    existian, las cinco piezas se devolvieron a `elegido` para que la seleccion
    los viera —y el paso 2.5 volvio a poner encima las decisiones tomadas
    cuando ese material no estaba. Rebobinar no basto.

    No sirve la fecha: la linea reescribe los transcripts en su propio paso
    `afinado`, asi que comparar fechas invalidaria todas las declaraciones en
    cada corrida. Lo que vale es lo que `revision` ya hace con `huella`:
    estampar la prueba y compararla.
    """
    cols = {r[1] for r in con.execute("pragma table_info(corte_fijo)")}
    if "huella" in cols:
        return False
    con.execute("ALTER TABLE corte_fijo ADD COLUMN huella TEXT")
    return True


def _escalera(con):
    """Los escalones de precio, con sus ventanas. Se corrigen, no se duplican."""
    for importe, desde, hasta, ancla, nota in ESCALERA:
        con.execute("insert into precio (importe, desde, hasta, ancla, nota)"
                    " values (?,?,?,?,?) on conflict(importe, hasta) do update"
                    " set desde=excluded.desde, ancla=excluded.ancla,"
                    " nota=excluded.nota",
                    (importe, desde, hasta, ancla, nota))


def _ciclo(con):
    """El camino de fases, tal y como lo declara `dominio.fase.CICLO`.

    Idempotente: se corrige el orden y el servicio de las que ya estan y se
    anaden las que faltan. Una fase que se renombre en el CICLO entra como nueva
    y la vieja se queda —es historia de las piezas que pasaron por ella— pero
    `camino()` la seguira listando, asi que renombrar es una decision, no un
    retoque.
    """
    for orden, nombre, serv in CICLO:
        ya = con.execute("select id from fase where nombre = ?",
                         (nombre,)).fetchone()
        if ya:
            con.execute("update fase set orden = ?, servicio = ? where id = ?",
                        (orden, serv, ya["id"]))
        else:
            con.execute("insert into fase (nombre, orden, servicio)"
                        " values (?,?,?)", (nombre, orden, serv))


def _clave_por_slug(con):
    """Las tablas que referian al video por texto ganan su clave foranea."""
    hecho = []
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
    return hecho


def _muertas(con):
    """Las tablas vacias y sin lector se tiran. Con filas dentro, no se tocan."""
    hecho = []
    for t in MUERTAS:
        try:
            n = con.execute(f"select count(*) from {t}").fetchone()[0]
            if n == 0:
                con.execute(f"drop table {t}")
                hecho.append(f"-{t}")
        except sqlite3.OperationalError:
            pass
    return hecho


def migrar():
    """Aplica todo lo que falte, en orden. Devuelve lo que de verdad cambio."""
    con = _con()
    _fase_servicio(con)
    esquema(con)
    _revision_estructurada(con)
    _escena_voz(con)
    _corte_fijo_etapa(con)
    _corte_fijo_huella(con)
    _escalera(con)
    _ciclo(con)
    hecho = _clave_por_slug(con)
    hecho += _muertas(con)
    con.commit()
    con.close()
    return hecho
