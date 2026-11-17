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
from dominio import memoria as _memoria  # noqa: E402
import entidades  # noqa: E402

#: El DDL. Al lado de `esquema.sql`, que es donde se busca un `CREATE TABLE`.
ESQUEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "esquema-modelo.sql")

# Las que referian al video por texto. Segunda forma normal: el slug repetido en
# cinco tablas es cinco sitios donde escribirlo mal y ninguno donde saltar.
POR_SLUG = ("revision", "escena_desc", "densidad", "descartado")

# Vacias y sin nadie que las lea. Una tabla que no se usa no es inofensiva:
# aparece en el esquema, alguien la lee como si significara algo, y ahi empieza
# el error.
# **Y tres mas, que `conectado.py` encontro vacias y sin nadie que las
# escriba.** `tarjeta` y `tratamiento` guardan datos que hoy viven en otro sitio
# —el pie de las tarjetas sale del paso 2, la velocidad es una sola para el
# lote—, y `asignacion` duplica `work/asignacion/*.json`. Una tabla declarada y
# vacia es una promesa de estado que no se cumple: mejor no tenerla que tenerla
# mintiendo. Si alguna vuelve a hacer falta, vuelve con quien la escriba.
MUERTAS = ("tarjeta_bloque", "tarjeta_remate", "render", "escena",
           "tarjeta", "tratamiento", "asignacion")

# La escalera que fijo Jaime el 29 de agosto de 2026, corrida para arrancar hoy.
# El Early Bird se conserva como fila pasada: es el ancla.
# **Y corrida otra vez el 4 de septiembre, que es la que vale.** Jaime: *«otro
# tiket, deja el precio de 20 dolares hasta el 9 de septiembre»* y *«el bloque
# de 30 corrio hasta el 15 y el resto pues de 40»*.
#
# Aqui seguia la anterior —20 al 4, 30 al 11— y esta lista se **reinserta en
# cada migracion**, asi que la escalera vieja volvia a aparecer al lado de la
# nueva. Con las dos vivas, `precio_vigente` saco a pantalla «$20 hasta el 4 sep
# · luego $20 y $30 y $30 y $40»: una fecha vencida ese mismo dia y una escalera
# que no existe, en las siete piezas. El precio es lo unico de la pieza que el
# espectador va a pagar.
ESCALERA = [
    (10, None, "2026-08-28", 1, "Early Bird — fila pasada, ancla"),
    (20, "2026-08-29", "2026-09-09", 0, None),
    (30, "2026-09-10", "2026-09-15", 0, None),
    (40, "2026-09-16", "2026-09-21T11:30", 0, "cierra con el evento"),
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


def _version_guarda_el_montaje(con):
    """`version` guardaba una huella; ahora guarda **el montaje**.

    Jaime, cuando le dije que la entrega que había aprobado no se podía volver a
    producir: *«no se trata de commits, todo debía estar en base de datos, y nada
    se borra de la base de datos; para eso está»*. Tenía razón y la tabla le daba
    la razón a medias: `huella`, `duracion_s` y `commit_git` dicen **que** una
    versión es distinta de otra, no **cómo** estaba hecha.

    El coste fue exacto: siete piezas entregadas el 4 de septiembre a las 19:20,
    trece correcciones suyas sobre ellas, y ninguna forma de rehacerlas —los
    cortes se habían movido y no quedaba de dónde sacar los de esa entrega—.

    Con `edl` y `spec` dentro, una versión se vuelve a montar sola.
    """
    cols = {r["name"] for r in con.execute("pragma table_info(version)")}
    for c, tipo in (("edl", "TEXT"), ("spec", "TEXT"), ("sha_entrega", "TEXT")):
        if c not in cols:
            con.execute(f"alter table version add column {c} {tipo}")


def _huella_del_corte(con):
    """La columna `huella` de `version` vuelve a ser la del corte.

    El esquema lo dice encima de la columna —*«la huella es del CORTE, no del
    fichero»*— y dentro habia otra cosa: `sellar.py` guardaba
    `sha1(edl + sha_del_mp4)`, la de la ENTREGA. No fue un descuido: la tabla
    exigia `(video_id, huella)` unico y dos mezclas del mismo corte —lo que
    produce `remezclar.py`— chocaban. C-217 escribio la leccion correcta y la
    aplico al reves: cambio el contenido de la columna en vez de la restriccion.

    **Lo que costo.** De las 95 versiones de la base, **ninguna** coincidia con
    la huella de su corte, y `donde.py` las compara con la del EDL de hoy: decia
    «CAMBIO» en las siete piezas siempre. Era la unica senal de si el corte que
    Jaime firmo seguia en pie.

    Lo que distingue dos entregas del mismo corte es el fichero, y eso ya tiene
    columna: `sha_entrega`, unica por pieza en las 95 filas y la que este mismo
    paso usa para no duplicar. El unico se muda ahi.

    **El DDL no se copia: se transforma.** Repetir aqui la tabla entera seria
    una segunda declaracion del esquema, que es la averia que este proyecto
    lleva pagando. Se lee la que hay y se le cambia lo que cambia.
    """
    fila = con.execute("select sql from sqlite_master where name = 'version'"
                       " and type = 'table'").fetchone()
    if not fila or "UNIQUE (video_id, huella)" not in (fila[0] or ""):
        return
    import json as _json

    from dominio.version import huella_de

    ddl = (fila[0].replace("UNIQUE (video_id, huella)",
                           "UNIQUE (video_id, sha_entrega)")
           .replace("CREATE TABLE version", "CREATE TABLE version_nueva", 1)
           .replace("create table version", "create table version_nueva", 1))
    cols = [r["name"] for r in con.execute("pragma table_info(version)")]
    filas = [dict(r) for r in con.execute("select * from version order by id")]
    for d in filas:
        if not d.get("edl"):
            continue
        try:
            d["huella"] = huella_de(_json.loads(d["edl"])) or d["huella"]
        except (ValueError, KeyError, TypeError):
            pass
    # **Tabla nueva, copiar, tirar la vieja y renombrar**: el orden que manda
    # SQLite para cambiar un `UNIQUE`. Con `legacy_alter_table`, porque sin el
    # un `rename` reescribe las referencias de las cuatro tablas que apuntan
    # aqui —`aprobacion`, `audio_version`, `publicacion`, `medicion`— y el paso
    # siguiente se estrella contra su propia clave foranea.
    con.commit()
    con.execute("pragma foreign_keys = off")
    con.execute("pragma legacy_alter_table = on")
    con.execute(ddl)
    ponlos = ", ".join(cols)
    huecos = ", ".join(":" + c for c in cols)
    for d in filas:
        con.execute(f"insert into version_nueva ({ponlos}) values ({huecos})", d)
    con.execute("drop table version")
    con.execute("alter table version_nueva rename to version")
    con.execute("create index if not exists version_video on version (video_id, n)")
    con.commit()
    con.execute("pragma legacy_alter_table = off")
    con.execute("pragma foreign_keys = on")
    return ["version.huella vuelve a ser la del corte"]


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



def _declaradas_en_el_esquema():
    """Los nombres de tabla que `esquema.sql` declara. Se lee, no se copia."""
    import re

    fuera = set()
    for f in (ESQUEMA, os.path.join(os.path.dirname(ESQUEMA), "esquema.sql")):
        try:
            with open(f, encoding="utf-8") as h:
                fuera |= set(re.findall(
                    r"CREATE TABLE(?:\s+IF NOT EXISTS)?\s+(\w+)", h.read(), re.I))
        except OSError:
            pass
    return fuera


def _muertas(con):
    """Las tablas vacias y sin lector se tiran. Con filas dentro, no se tocan.

    **Y no se tira lo que el esquema declara.** `esquema.sql` es el modelo —su
    propia cabecera lo dice: *«1FN, nada de grupos repetidos; por eso
    `tarjeta_bloque` es una tabla y no una columna»*— y esto las borraba por
    estar vacias, para que `esquema()` las recreara en el arranque siguiente:
    `migrar()` corrido dos veces devolvia cinco drops y luego nada, en bucle.
    Dos mecanismos con la intencion contraria sobre la misma tabla.

    Gana el modelo. Una tabla declarada y vacia es una promesa pendiente —se ve
    en `conectado.py`, que para eso esta—; una tabla borrada y recreada cada
    arranque no es ni promesa ni aviso: es ruido. C-356.
    """
    declaradas = _declaradas_en_el_esquema()
    hecho = []
    for t in MUERTAS:
        if t in declaradas:
            continue
        try:
            n = con.execute(f"select count(*) from {t}").fetchone()[0]
            if n == 0:
                con.execute(f"drop table {t}")
                hecho.append(f"-{t}")
        except sqlite3.OperationalError:
            pass
    return hecho


def _segmento_con_etiqueta(con):
    """Cada segmento lleva su propia etiqueta, y aprobar es una de ellas.

    Jaime, 10-9-2026: *«la aprobacion de la pieza es igual a la aprobacion de
    todos los segmentos, y cada segmento se debe revisar como la unidad de
    analisis»*, y despues: *«cada segmento con su propia etiqueta»*.

    Lo que habia era un veredicto por VERSION —`aprobacion` es `version_id,
    veredicto, quien`—, asi que la pieza entera estaba bien o no lo estaba. Con
    eso, una correccion de un tramo volvia a poner en juego las seis etapas, y
    «lo aprobado no se rediscute» no se podia cumplir: no habia con que decir
    que la 3 seguia buena.

    **La huella es lo que la hace verdad.** La etiqueta se pone contra el corte
    que el segmento tenia ese dia; si sus tramos se mueven, lo que se etiqueto
    era otra cosa y la fila deja de aplicar **sola**, sin que nadie se acuerde
    de retirarla. Es la vara que ya usan `corte_fijo` y `ticket`, y su ausencia
    es lo que costo las siete vueltas del reel-01.

    Sin fila el segmento esta abierto: no hay que sembrar seis filas en falso
    al declarar una pieza.
    """
    con.execute("""
      CREATE TABLE IF NOT EXISTS segmento (
        video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
        etapa    INTEGER NOT NULL,
        -- Donde esta ESE segmento: una fase del ciclo, o 'aprobado'.
        etiqueta TEXT NOT NULL,
        -- El corte contra el que se puso. Ver `dominio/segmento.py::huella`.
        huella   TEXT NOT NULL,
        quien    TEXT NOT NULL,
        cuando   TEXT NOT NULL,
        PRIMARY KEY (video_id, etapa)
      )""")
    return True


def _paso_de_instruccion_apunta_bien(con):
    """`instruccion.paso_id` decia apuntar a `fase` y guardaba areas.

    Lo hice yo el 10-9-2026 en dos pasos: primero mapee `instruccion.paso`
    contra `fase` —resolvio 1 de 37, porque sus valores son `audio`, `corte`,
    `disenar` y `montaje`, que son el area de la que habla la instruccion y no
    pasos del ciclo— y luego lo mande a su propio catalogo. Pero la columna ya
    estaba declarada `REFERENCES fase(id)` y SQLite no cambia una foranea: se
    quedo diciendo una cosa y guardando otra.

    No se veia hasta que `conectado.copias_que_discrepan` empezo a comparar la
    copia con su clave, y salio en las 37. Una foranea que apunta a la tabla
    equivocada es peor que no tenerla: se puede unir, devuelve filas, y son de
    otro sitio.
    """
    fk = {f[3]: f[2] for f in con.execute("pragma foreign_key_list(instruccion)")}
    if fk.get("paso_id") != "fase":
        return False
    con.execute("alter table instruccion drop column paso_id")
    return True


def _escena_corrige_marca(con):
    """`escena_desc` gana `corrige_marca` (C-630) y `cc_lado` (C-633)."""
    cols = {r[1] for r in con.execute("pragma table_info(escena_desc)")}
    if not cols:
        return False
    nuevas = [(c, d) for c, d in (("corrige_marca", "TEXT"), ("cc_lado",
              "TEXT CHECK (cc_lado IN ('der','izq'))")) if c not in cols]
    for c, d in nuevas:
        con.execute(f"ALTER TABLE escena_desc ADD COLUMN {c} {d}")
    return bool(nuevas)


def _video_vision(con):
    """`video` gana `vision`, la visión del director de la pieza (C-737)."""
    cols = {r[1] for r in con.execute("pragma table_info(video)")}
    if not cols or "vision" in cols:
        return False
    con.execute("ALTER TABLE video ADD COLUMN vision TEXT")
    return True


def _etapa_video(con):
    """`etapa` gana `video`, la columna VIDEO del guion (C-738): la intención de
    lo que se ve, en SQL y no sólo en `frames.json`."""
    cols = {r[1] for r in con.execute("pragma table_info(etapa)")}
    if not cols or "video" in cols:
        return False
    con.execute("ALTER TABLE etapa ADD COLUMN video TEXT")
    return True


def _documento(con):
    """El sello de lo que publica la línea (C-738): cada documento de escena y de
    pieza, con la huella de lo que se escribió. Si el fichero ya no casa, alguien
    lo tocó por fuera y la pieza se para."""
    con.execute("CREATE TABLE IF NOT EXISTS documento (ruta TEXT PRIMARY KEY,"
                " slug TEXT NOT NULL, huella TEXT NOT NULL, escrito TEXT NOT NULL)")
    return False


def migrar():
    """Aplica todo lo que falte, en orden. Devuelve lo que de verdad cambio."""
    con = _con()
    _fase_servicio(con)
    esquema(con)
    _revision_estructurada(con)
    _escena_voz(con)
    _escena_corrige_marca(con)
    _video_vision(con)
    _etapa_video(con)
    _documento(con)
    _corte_fijo_etapa(con)
    _corte_fijo_huella(con)
    _escalera(con)
    _ciclo(con)
    _version_guarda_el_montaje(con)
    _huella_del_corte(con)
    _segmento_con_etiqueta(con)
    # Lo que cada paso ya pregunto, por segmento (C-561).
    _memoria.crea(con)
    entidades._entidades_de_la_escena(con)
    entidades._camara_es_una_seleccion(con)
    entidades._tipo_escena_es_una_seleccion(con)
    _paso_de_instruccion_apunta_bien(con)
    entidades._vocabularios(con)
    entidades._foraneas_de_texto(con)
    entidades._retiradas_fuera_del_catalogo(con)
    entidades._quien_es_agencia(con)
    hecho = _clave_por_slug(con)
    hecho += _muertas(con)
    con.commit()
    con.close()
    return hecho
