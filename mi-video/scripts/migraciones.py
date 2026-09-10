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


def _entidades_de_la_escena(con):
    """`tablero`, `panel`, `camara` y `voz` dejan de ser columnas y son entidades.

    Jaime, 10-9-2026: *«tablero es una entidad, no una columna; panel es una
    entidad, no una columna; tipo de escena es una entidad que relaciona otras
    entidades. Si me dices que una tabla es una columna no hay nada de tercera
    normalizacion»*. Y sobre la forma: *«utiliza tablas de conexion para las
    relaciones 1:n y n:n»*.

    Lo que habia. `escena_desc` son **24 columnas** haciendo de escena, tablero,
    camara, voz, correccion e integridad a la vez, y cuatro de ellas guardan una
    entidad entera en TEXT: `tablero` (50 filas), `tablero_propuesto` (36),
    `camara` (52) y `voz` (6). Medido: en **35 de las 36** filas que tienen las
    dos, `tablero` y `tablero_propuesto` dicen cosas distintas y nada declara
    cual manda — porque no son dos columnas, son **una entidad con dos estados**
    aplastada en el ancho de la fila. Y `panel` ni siquiera existia: los tres de
    reel-03 se calculan al vuelo y mueren en el spec, asi que no se pueden
    declarar, ni aprobar, ni recibir un tiquet.

    El ancla es `etapa` —62 filas, una por etapa montada, las mismas 62 que
    `escena_desc`—, y se une por `etapa.orden`, **no** por `etapa.etapa_orden`:
    62 de 62 contra 46 de 62. Dos columnas de la misma tabla que se llaman casi
    igual y no significan lo mismo.

    Las conexiones llevan lo que es de la RELACION y no de la entidad: el estado
    de un tablero en su etapa, o el segundo en el que entra un panel.
    """
    pass  # el modelo lo declara `esquema-modelo.sql`
    return True


def _camara_es_una_seleccion(con):
    """`camara` no es la entidad: es la **seleccion** de especificaciones tecnicas.

    Jaime, 10-9-2026, corrigiendo dos veces seguidas: *«de esas 5 cuantas son
    entidades? transicion es una entidad»*, y despues: *«varias de esas son
    entidades; camara debe ser una tabla de seleccion de especificaciones
    tecnicas, como el encuadre, como casi todas las que pones ahi»*.

    Lo que yo habia hecho era mover el problema: saque `camara` de una columna
    de `escena_desc` y la deje como una fila con cinco textos sueltos dentro.
    Un `encuadre` no es una cadena que se repita 38 veces — es un catalogo, y lo
    mismo `movimiento` (45) y `virado` (5). Y `transicion` (35) ni siquiera es de
    la camara: **ya tenia su tabla**, con seis filas que no escribia ni leia
    nadie, mientras el dato vivia dentro del JSON de otra entidad. El valor
    `filete` que usan cinco etapas no estaba en ese catalogo.

    Asi que: cada especificacion su tabla, `camara` la fila que las relaciona, y
    la etapa conectada a esa seleccion. `detras` —una sola etapa, «columna»— se
    queda fuera a proposito: es del mundo de `placa` y no se decide aqui.
    """
    cols = {r[1] for r in con.execute("pragma table_info(camara)")}
    if "encuadre_id" in cols:
        return False
    con.executescript("""
      CREATE TABLE IF NOT EXISTS encuadre   (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
      CREATE TABLE IF NOT EXISTS movimiento (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
      CREATE TABLE IF NOT EXISTS virado     (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
      DROP TABLE IF EXISTS etapa_camara;
      DROP TABLE IF EXISTS camara;
      CREATE TABLE camara (
        id            INTEGER PRIMARY KEY,
        encuadre_id   INTEGER REFERENCES encuadre(id),
        movimiento_id INTEGER REFERENCES movimiento(id),
        virado_id     INTEGER REFERENCES virado(id),
        UNIQUE (encuadre_id, movimiento_id, virado_id)
      );
      CREATE TABLE etapa_camara (
        etapa_id  INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        camara_id INTEGER NOT NULL REFERENCES camara(id) ON DELETE CASCADE,
        PRIMARY KEY (etapa_id)
      );
      CREATE TABLE IF NOT EXISTS etapa_transicion (
        etapa_id      INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        transicion_id INTEGER NOT NULL REFERENCES transicion(id) ON DELETE CASCADE,
        PRIMARY KEY (etapa_id)
      );
      INSERT OR IGNORE INTO transicion (nombre) VALUES ('filete');
    """)
    return True


def _retiradas_fuera_del_catalogo(con):
    """Una transicion retirada no se queda en el catalogo esperando a que la pidan.

    Jaime, 10-9-2026: *«borra la cortinilla, es horrible»*. Y ya estaba
    declarada retirada — `camara.mjs :: RETIRADAS` la lleva con su motivo y su
    sustituto, `glitch`— desde que reel-01 salio con una placa de 0,7 s en el
    segundo 61,7 y el dijo: *«eso ya lo habiamos depreciado, por que el
    disenador volvio a traer esa cortina?»*.

    Lo que fallo entonces vuelve a fallar ahora, una capa mas abajo: el menu la
    daba por retirada y **el catalogo la seguia ofreciendo**, con cuatro etapas
    usandola —reel-01 e6, reel-02 e7, reel-04 e7 y reel-06 e4—. Un mecanismo que
    sigue en la tabla no esta retirado: esta esperando.

    Las que la usaban pasan a su sustituto **declarado**, no a uno que elija yo:
    lo dice `RETIRADAS.cortinilla.en_su_lugar`. Y la lista se lee de ahi, que es
    donde vive la decision — copiarla aqui seria la segunda carta.
    """
    import json
    import subprocess

    # **Lo retirado no se borra: se marca, y apunta a lo que va en su lugar.**
    # La columna se anade aqui y no en el `.sql` porque un ALTER no es
    # idempotente y ese fichero se corre en cada arranque.
    if "en_su_lugar" not in {r[1] for r in con.execute("pragma table_info(transicion)")}:
        con.execute("alter table transicion add column en_su_lugar INTEGER"
                    " REFERENCES transicion(id)")
    try:
        salida = subprocess.run(
            ["node", "-e", "import('./scripts/camara.mjs').then(m =>"
                           " console.log(JSON.stringify(m.RETIRADAS || {})))"],
            capture_output=True, text=True, timeout=30).stdout.strip()
        retiradas = json.loads(salida or "{}")
    except Exception:                              # noqa: BLE001
        return False
    hecho = False
    for nombre, d in retiradas.items():
        vieja = con.execute("select id from transicion where nombre = ?",
                            (nombre,)).fetchone()
        if not vieja:
            vieja = (con.execute("insert into transicion (nombre) values (?)",
                                 (nombre,)).lastrowid,)
        nueva = con.execute("select id from transicion where nombre = ?",
                            (d.get("en_su_lugar"),)).fetchone()
        if nueva:
            con.execute("update etapa_transicion set transicion_id = ?"
                        " where transicion_id = ?", (nueva[0], vieja[0]))
            # **Se marca, no se borra.** Borrarla no la retiraba: el volcado la
            # volvia a insertar en cuanto encontraba una descripcion vieja que
            # la nombraba. Marcada, `cat()` la redirige sola y el que compone
            # ve que existio y por que no esta.
            con.execute("update transicion set en_su_lugar = ? where id = ?",
                        (nueva[0], vieja[0]))
        else:
            con.execute("delete from etapa_transicion where transicion_id = ?",
                        (vieja[0],))
            con.execute("delete from transicion where id = ?", (vieja[0],))
        hecho = True
    return hecho


def _quien_es_agencia(con):
    """`quien` no es un nombre: es **quién actuó y qué tenía derecho a hacer**.

    Jaime, 10-9-2026: *«hay autores y hay tipos de autores. Estoy yo como
    persona asociada a mi propia imagen de marca, pero si entra otra persona la
    imagen de marca debería cambiar. También están los agentes de IA, que
    modifican y definen pasos y cosas. Quien es al final un declarador de
    agencia, requiere más trabajo que sólo declarar una entidad»*. Y precisando:
    *«el tipo no es jaime sino persona; la entidad persona tiene nombre e
    identidad de marca; agencia son los permisos que hay sobre todo»*.

    Quince cadenas para diez actores en nueve tablas, y el permiso decidido
    comparandolas: `segmento.es_suya` miraba si `quien` empieza por «jaime». Un
    derecho que se comprueba por prefijo de cadena no es un derecho. El detalle
    y las cuentas, en C-363.

    Cuatro tablas: el tipo declara la agencia y la persona **apunta** a su
    marca. Las indicaciones no se copian a una tabla porque ya son los
    contratos — `contrato/marca.py` lleva la parte fija del contrato del
    disenador desde que Jaime la separo de la variable.
    """
    pass  # el modelo lo declara `esquema-modelo.sql`
    for n in ("persona", "oficio", "paso"):
        con.execute("insert or ignore into tipo_autor (nombre) values (?)", (n,))
    permisos = [
        ("aprobar", "Cerrar una pieza o un segmento. Lo unico que el motor no"
                    " puede hacer solo, y por eso lo unico que le cierra la puerta."),
        ("decidir criterio", "Elegir entre dos cosas que cumplen: que se dice,"
                             " que se dibuja, que toma entrega mejor."),
        ("medir", "Contar lo medible. No decide: deja el numero delante de quien"
                  " decide."),
        ("abrir tiquet", "Declarar que algo esta mal en una pieza."),
    ]
    for n, p in permisos:
        con.execute("insert or ignore into permiso (nombre, por_que) values (?,?)",
                    (n, p))
    dan = {"persona": ("aprobar", "decidir criterio", "abrir tiquet"),
           "oficio": ("decidir criterio", "abrir tiquet"),
           "paso": ("medir", "abrir tiquet")}
    for tipo, ps in dan.items():
        t = con.execute("select id from tipo_autor where nombre = ?", (tipo,)).fetchone()[0]
        for n in ps:
            pid = con.execute("select id from permiso where nombre = ?", (n,)).fetchone()[0]
            con.execute("insert or ignore into agencia values (?,?)", (t, pid))
    return True


def _tipo_escena_es_una_seleccion(con):
    """`tipo_escena` guardaba trato, plano y densidad como texto. Ahora selecciona.

    Es el mismo fallo que tenia `camara` (C-361) un piso mas arriba, y lo comeli
    el mismo dia: hice la tabla que **relaciona** otras entidades guardando
    cadenas en vez de claves. Jaime: *«sigue con trato, plano, color y
    remedio»*.

    `color` entra en la seleccion —es tratamiento, como el trato y el plano— y
    `remedio` no: no es un tipo de escena, es la decision sobre un problema de
    integridad, asi que cuelga de la etapa.
    """
    cols = {r[1] for r in con.execute("pragma table_info(tipo_escena)")}
    if "trato_id" in cols:
        return False
    con.executescript("""
      DROP TABLE IF EXISTS etapa_tipo;
      DROP TABLE IF EXISTS tipo_escena;
      CREATE TABLE tipo_escena (
        id       INTEGER PRIMARY KEY,
        trato_id INTEGER REFERENCES trato(id),
        plano_id INTEGER REFERENCES plano(id),
        color_id INTEGER REFERENCES color(id),
        UNIQUE (trato_id, plano_id, color_id)
      );
      CREATE TABLE etapa_tipo (
        etapa_id INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        tipo_id  INTEGER NOT NULL REFERENCES tipo_escena(id) ON DELETE CASCADE,
        por_que  TEXT,
        PRIMARY KEY (etapa_id)
      );
    """)
    return True


#: Los vocabularios del dominio que seguian escritos a mano, con la tabla que
#: los declara. Es una lista y no codigo repetido: cada linea es «esta columna
#: es este catalogo», y `_vocabularios` hace lo mismo con todas.
#:
#: Jaime, 10-9-2026: *«cada paso que das en la supuesta normalidad es un paso en
#: donde encuentro entidades»*. Contadas por `conectado.py`, no por mi.
#: Columnas que ya apuntaban a una tabla existente y la nombraban por su texto:
#: `toma` tiene tabla desde el principio y `fase` tambien. Una clave foranea
#: escrita como cadena es una clave foranea que nadie puede exigir.
FORANEAS = (
    ("corte_fijo",  "toma",      "toma", "nombre"),
    ("incidencia",  "toma",      "toma", "nombre"),
    ("ticket",      "vuelve_a",  "fase", "nombre"),
)

VOCABULARIOS = (
    ("corte_fijo",  "papel",    "papel_corte"),
    ("colocacion",  "tipo",     "tipo_colocacion"),
    ("dato",        "respalda", "respaldo_dato"),
    ("densidad",    "nivel",    "nivel"),
    ("fragmento",   "origen",   "origen_fragmento"),
    ("incidencia",  "nivel",    "nivel_incidencia"),
    ("instruccion", "ambito",   "ambito"),
    # `paso` NO es una fase: sus valores son `audio`, `corte`, `disenar`,
    # `montado` y `montaje`, y solo uno coincide con el ciclo. Es el area
    # de la que habla la instruccion, que es otra cosa.
    ("instruccion", "paso",     "area_instruccion"),
    ("instruccion", "estado",   "estado_instruccion"),
    ("regla",       "clase",    "clase_regla"),
    ("revision",    "accion",   "accion_revision"),
    ("revision",    "estado",   "estado_revision"),
    ("ticket",      "tipo",     "tipo_ticket"),
    ("ticket",      "estado",   "estado_ticket"),
    ("ticket",      "cierra_con", "medida"),
    ("etapa_tablero", "estado",   "estado_tablero"),
    # Los 17 pasos que dejan aviso. Con 10.823 filas detras, «que scripts
    # hablan» no se puede contestar sin recorrerlas todas.
    ("incidencia",  "script",   "script_incidencia"),
)


def _foraneas_de_texto(con):
    """Claves foraneas escritas como cadena, teniendo su tabla al lado.

    `corte_fijo.toma` y `incidencia.toma` nombran las cintas por su nombre
    cuando `toma` es una tabla desde el principio; `instruccion.paso` y
    `ticket.vuelve_a` nombran fases igual. Una clave foranea escrita como texto
    no la puede exigir nadie: un paso que ya no existe se queda escrito y solo
    se descubre cuando algo lo busca — como paso con `--volver descrito`, que
    nombraba una fase que significaba lo contrario de lo que yo creia.
    """
    hecho = False
    for tabla, col, destino, campo in FORANEAS:
        cols = {r[1] for r in con.execute(f"pragma table_info({tabla})")}
        if not cols or col not in cols:
            continue
        clave = f"{col}_id"
        if clave not in cols:
            con.execute(f"alter table {tabla} add column {clave} INTEGER"
                        f" REFERENCES {destino}(id)")
        con.execute(f"update {tabla} set {clave} = (select id from {destino}"
                    f" where {destino}.{campo} = {tabla}.{col})"
                    f" where {col} is not null and {col} <> ''")
        hecho = True
    return hecho


def _vocabularios(con):
    """Cada vocabulario a su tabla, y la columna con su clave al lado.

    Catorce columnas de texto libre con entre dos y doce valores repetidos
    cientos de veces. Como texto no se pueden declarar —«que medidas existen»
    no se puede contestar sin leer 213 filas—, ni relacionar, ni impedir que
    entre una decimoquinta por una errata.

    El texto se queda de momento: lo leen pasos que todavia no han cambiado, y
    quitarlo antes de moverlos seria romper la linea por normalizar. Lo que
    `conectado.py` cuenta a partir de ahora es la diferencia entre «no tiene
    tabla» y «la tiene y aun arrastra su copia», que no son la misma deuda.
    """
    hecho = False
    for tabla, col, catalogo in VOCABULARIOS:
        try:
            cols = {r[1] for r in con.execute(f"pragma table_info({tabla})")}
        except sqlite3.OperationalError:
            continue
        if not cols or col not in cols:
            continue
        con.execute(f"CREATE TABLE IF NOT EXISTS {catalogo} ("
                    f" id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE)")
        clave = f"{col}_id"
        if clave not in cols:
            con.execute(f"alter table {tabla} add column {clave} INTEGER"
                        f" REFERENCES {catalogo}(id)")
        for (v,) in con.execute(f"select distinct {col} from {tabla}"
                                f" where {col} is not null and {col} <> ''"):
            if not isinstance(v, str):
                continue
            con.execute(f"insert or ignore into {catalogo} (nombre) values (?)", (v,))
            con.execute(f"update {tabla} set {clave} ="
                        f" (select id from {catalogo} where nombre = ?)"
                        f" where {col} = ?", (v, v))
        hecho = True
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
    _version_guarda_el_montaje(con)
    _segmento_con_etiqueta(con)
    _entidades_de_la_escena(con)
    _camara_es_una_seleccion(con)
    _tipo_escena_es_una_seleccion(con)
    _vocabularios(con)
    _foraneas_de_texto(con)
    _retiradas_fuera_del_catalogo(con)
    _quien_es_agencia(con)
    hecho = _clave_por_slug(con)
    hecho += _muertas(con)
    con.commit()
    con.close()
    return hecho
