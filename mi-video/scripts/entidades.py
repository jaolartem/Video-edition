"""Las migraciones que convierten **texto libre en entidad**.

Jaime, 10-9-2026, despues de encontrarme cuatro seguidas: *«cada paso que das en
la supuesta normalidad es un paso en donde encuentro entidades»*, y *«las estoy
encontrando yo; tu las mandas por buenas»*.

## Por que no viven en `migraciones.py`

Porque son otra cosa. Alli se cambia **la forma** de una tabla —una columna que
nace, un unico que se muda, una tabla que se parte—; aqui se cambia **lo que
significa un valor**: una cadena repetida que resulta ser un catalogo, una clave
foranea escrita como texto, un vocabulario que estaba en la cabeza de quien lo
escribio.

Estaban juntas porque las dos se corren al migrar, y con eso `migraciones.py`
paso del techo de 300 lineas. La regla del proyecto no es partir por tamano sino
por responsabilidad, y aqui la frontera ya estaba: las siete funciones de abajo
no tocan ni una forma de tabla, y ninguna de las de alla mira un vocabulario.

Las corre `migraciones.migrar()`, que sigue siendo el unico sitio desde el que
se migra.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


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
    for n in ("persona", "oficio", "paso", "revisor"):
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
           "paso": ("medir", "abrir tiquet"),
           # **El diseñador aprueba tramos contra el vídeo.** Jaime, 12-9-2026:
           # *«el diseñador no aprueba videos, aprueba tramos contra video; si un
           # tramo esta bien nunca mas pasa por diseñador; se aprueba y listo»*.
           # Es un oficio que además revisa lo renderizado; el compositor, no.
           "revisor": ("aprobar", "decidir criterio", "abrir tiquet")}
    for tipo, ps in dan.items():
        t = con.execute("select id from tipo_autor where nombre = ?", (tipo,)).fetchone()[0]
        for n in ps:
            pid = con.execute("select id from permiso where nombre = ?", (n,)).fetchone()[0]
            con.execute("insert or ignore into agencia values (?,?)", (t, pid))
    con.execute("update autor set tipo_id = (select id from tipo_autor where"
                " nombre = 'revisor') where nombre = 'disenador'")
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
