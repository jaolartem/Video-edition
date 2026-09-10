-- **El esquema que anade `modelo.py`**, encima de `esquema.sql`.
--
-- Vivia como una cadena de 249 lineas dentro de `modelo.py`, y por eso ese
-- fichero media 473: mas de la mitad de su "codigo" era DDL. SQL escrito en
-- una cadena de Python no lo colorea nadie, no lo comprueba nadie y se lee
-- peor; aqui es lo que es, y al lado de `esquema.sql`, que es donde se busca.
--
-- Se aplica desde `migraciones.esquema()`. Todo es `IF NOT EXISTS`: correrlo
-- dos veces no hace nada la segunda.
--
-- El `ALTER TABLE fase ADD COLUMN servicio` que vivia aqui como el marcador
-- `ALTER_FASE_SERVICIO;` ya no esta: SQLite no sabe anadir una columna solo si
-- falta, asi que eso es una migracion y vive con las demas, en
-- `migraciones._fase_servicio`.

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
--
-- La tabla `fase` no se crea aqui —ya venia en `esquema.sql`—: lo que hacia
-- falta era su columna `servicio` y sus filas. La columna la pone
-- `migraciones._fase_servicio`; las filas, `migraciones._ciclo`, leyendo
-- `dominio.fase.CICLO`, que es donde esta escrito el camino.

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

-- Las reglas como CLASES, no como texto repetido en cada nota
--
-- Jaime: *«no hay cambios temporales o pasajeros, hay clases y subclases»*, y
-- *«puedes crear una subclase o una clase nueva»*.
--
-- `revision.regla` era texto libre: 65 notas con 24 redacciones distintas, y las
-- tres primeras eran **la misma regla escrita de tres maneras** (32 + 9 + 3
-- notas). Eso no es una regla aplicada 44 veces: son 44 copias que se pueden
-- contradecir entre si, y ninguna que se pueda marcar como automatizada de una
-- vez.
--
-- Con clases, una correccion suya deja de ser un parche para ESA pieza y pasa a
-- ser una instancia de algo que vale para las 16-50. Y cuando algo no encaja, la
-- salida no es una excepcion en el codigo: es **una subclase**.
CREATE TABLE IF NOT EXISTS regla (
  id           INTEGER PRIMARY KEY,
  -- La familia: redundancia, integridad, sonido, grafico, subtitulo, proceso.
  clase        TEXT NOT NULL,
  -- Si es una subclase, de quien. NULL es una clase de primer nivel.
  padre_id     INTEGER REFERENCES regla(id),
  enunciado    TEXT NOT NULL,
  -- **Automatizada se marca en la REGLA, no en la nota.** Una regla que ya vive
  -- en codigo lo esta para todas sus instancias; marcarlo nota a nota era decir
  -- treinta veces lo mismo y poder equivocarse en la treinta y una.
  automatizada INTEGER NOT NULL DEFAULT 0,
  donde        TEXT,
  fecha        TEXT
);

CREATE INDEX IF NOT EXISTS regla_clase ON regla (clase, padre_id);

-- De donde sale cada cifra que la pieza pone delante del espectador
--
-- Jaime: *«lo importante es que la fuente aparezca en todos esos datos; pon en
-- los CC el valor real, y un cuadro con la fuente de la info»*.
--
-- El hueco estaba justo al reves de como parecia. Los componentes **ya exigen**
-- la fuente —`Comparacion` no compila sin ella, y eso es deliberado: *«el
-- cumplimiento va en la API, no en la revision»*—, pero el valor se escribia a
-- mano en `reels-spec.mjs`, una cadena por pieza: «Calculo de Jaime Olarte ·
-- $21 por cada $100 facturado». Un literal por pieza es la misma trampa que un
-- `if (slug === ...)`: no escala a 16-50 anuncios, no se puede auditar, y el
-- tablero que dibuja el CAMINO —el que se usa de verdad— ni siquiera recibia
-- fuente.
--
-- Con esto, la fuente **viaja con el dato**: la escribe el paso que la busca, la
-- lee el que dibuja, y la puerta puede negarse a sacar en pantalla una cifra que
-- no la tiene.
CREATE TABLE IF NOT EXISTS fuente (
  id        INTEGER PRIMARY KEY,
  -- Como se rotula en pantalla: organismo + documento. Se guarda ya redactado
  -- porque es lo que el espectador lee, no una referencia interna.
  rotulo    TEXT NOT NULL UNIQUE,
  organismo TEXT,
  url       TEXT,
  -- El año fiscal o la fecha de lo que dice. **Una tasa sin año caduca en
  -- silencio**, que es la peor forma de caducar.
  vigencia  TEXT,
  cita      TEXT,
  fecha     TEXT
);

CREATE TABLE IF NOT EXISTS dato (
  id           INTEGER PRIMARY KEY,
  video_id     INTEGER NOT NULL REFERENCES video(id),
  etapa_orden  INTEGER NOT NULL,
  cifra        TEXT NOT NULL,
  afirmacion   TEXT NOT NULL,
  fuente_id    INTEGER REFERENCES fuente(id),
  -- Lo que hay que declarar para que la cifra no engañe: provincia, tipo de
  -- ingreso, horizonte temporal, supuestos del caso. El playbook lo exige y
  -- `TwoPaths` ya lo pide por API con `horizon` y `condition`.
  condiciones  TEXT,
  -- `sin_fuente` no es un registro incompleto: es **el estado honesto** de un
  -- dato que todavia no se puede rotular, y es lo que la puerta mira para no
  -- dejarlo salir en pantalla.
  respalda     TEXT NOT NULL DEFAULT 'sin_fuente'
                 CHECK (respalda IN ('si','parcial','no','sin_fuente')),
  nota         TEXT,
  fecha        TEXT,
  UNIQUE (video_id, etapa_orden, cifra)
);

CREATE INDEX IF NOT EXISTS dato_etapa ON dato (video_id, etapa_orden);

-- La escalera de precios, con sus ventanas
--
-- C-28 cerro que un precio sale con su fecha de cierre —*«un $20 a secas deja de
-- ser cierto pasado manana»*— y aun asi volvio a pasar: el rotulo vivia como
-- cadena literal en `reels-spec.mjs` (`"$20 hasta el 28 ago"`), una por pieza. Un
-- literal no caduca: **el que caduca es el mundo**, y la cadena se queda ahi
-- diciendo una fecha que ya paso.
--
-- Con la escalera como dato, el rotulo se **deriva de la fecha del render**, y
-- una pieza que se monta fuera de toda ventana no puede imprimir precio.
--
-- El escalon pasado no se borra: Jaime lo dejo dicho del Early Bird —*«se queda
-- como fila pasada, ancla, no se borra»*—. Un precio tachado es lo que hace que
-- el vigente se lea como oportunidad y no como tarifa.
CREATE TABLE IF NOT EXISTS precio (
  id      INTEGER PRIMARY KEY,
  importe INTEGER NOT NULL,
  -- NULL en el ancla: no tiene apertura, solo cierre.
  desde   TEXT,
  hasta   TEXT NOT NULL,
  ancla   INTEGER NOT NULL DEFAULT 0,
  nota    TEXT,
  UNIQUE (importe, hasta)
);

-- Un tramo de habla que se oyo y **no aporta texto a la pieza**.
--
-- El paso 1 se planta cuando la cinta tiene habla sin transcribir, y hace bien:
-- asi salieron los 102 segundos mudos del reel 1. Pero no todo hueco es una
-- perdida. La cinta es un abanico —*«se grabo asi para poder escoger una buena
-- entre estas»*— y sus 29 segundos restantes son falsos arranques y tomas
-- repetidas de una linea que ya esta transcrita tres veces mas alla.
--
-- Sin esta tabla esa lectura se queda en la cabeza de quien la hizo y el paso
-- vuelve a plantarse en la corrida siguiente, identico. Con ella la decision
-- **existe fuera de la conversacion**: dice quien la tomo, cuando y por que, y
-- se puede discutir. Es la misma regla que gobierna el resto del proyecto —
-- una decision que no queda registrada no ocurrio.
--
-- No abre la puerta a saltarse huecos nuevos: solo silencia los tramos
-- declarados uno a uno. Un agujero que aparezca en otro sitio sigue parando.
CREATE TABLE IF NOT EXISTS hueco_oido (
  id        INTEGER PRIMARY KEY,
  toma      TEXT NOT NULL,
  desde     REAL NOT NULL,
  hasta     REAL NOT NULL,
  -- `descartado` = se oyo y no aporta. `pendiente` = aun no se ha oido.
  veredicto TEXT NOT NULL DEFAULT 'descartado',
  por_que   TEXT NOT NULL,
  quien     TEXT,
  fecha     TEXT,
  UNIQUE (toma, desde, hasta)
);

-- Lo que la POSTPRODUCCION le hace a una etapa cuando la cinta no da mas.
--
-- Hay tibiezas que no se arreglan editando: la toma es la que es y no hay otra
-- mejor en las siete cintas. Jaime, al ver el mecanismo del reel-01 condenado a
-- ir grave: *«ahora estas son las tomas que hay, podemos intentar hacer cosas en
-- postproduccion para esto — subir un poquito el registro pasando la voz a 1.15x
-- de velocidad en ciertos espacios»*.
--
-- **Y el factor entra en el reloj de la pieza, no encima.** Una escena a 1,15x
-- dura menos en el montaje que en la cinta, asi que `plan-reel` avanza por
-- `duracion / velocidad`. Si esto no fuera asi volveriamos a tener dos lineas de
-- tiempo, que es el fallo mas caro de esta sesion (C-97 y C-103).
-- **`tratamiento` NO se declara aqui, y es a proposito.** La creaba este
-- fichero y `migraciones.MUERTAS` la tiraba por vacia y sin lector, en cada
-- arranque, para siempre: `migrar()` corrido tres veces devolvia
-- `['-tratamiento']` las tres. Una tabla que se crea y se borra en bucle no es
-- una promesa: es ruido con forma de esquema.
--
-- Se declara el dia que alguien la escriba y la lea, que es cuando entre la
-- postproduccion. Lo de arriba queda como el porque, que es lo que hay que
-- conservar. C-353.



-- ══════════════════════════════════════════════════════════════════
-- EL MODELO DE LA ESCENA Y LA AGENCIA
--
-- Jaime, 10-9-2026: «tablero es una entidad, no una columna; panel es una
-- entidad, no una columna; tipo de escena es una entidad que relaciona
-- otras entidades», «utiliza tablas de conexion para las relaciones 1:n y
-- n:n», y «quien es al final un declarador de agencia».
--
-- Vienen de `migraciones.py`, que llego a 300 lineas por acumular veinte
-- declaraciones: el modelo se declara aqui y alli se queda solo lo que hay
-- que sembrar o mover. Es la misma separacion que hizo `contrato/`.
-- ══════════════════════════════════════════════════════════════════

-- de `migraciones._entidades_de_la_escena`
CREATE TABLE IF NOT EXISTS tablero (
        id      INTEGER PRIMARY KEY,
        kind    TEXT NOT NULL,
        props   TEXT NOT NULL,
        encargo TEXT
      );
      CREATE TABLE IF NOT EXISTS etapa_tablero (
        etapa_id   INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        tablero_id INTEGER NOT NULL REFERENCES tablero(id) ON DELETE CASCADE,
        -- Lo que distinguia a las dos columnas, ahora en la relacion.
        estado     TEXT NOT NULL CHECK (estado IN ('propuesto','aplicado')),
        quien      TEXT,
        fecha      TEXT,
        PRIMARY KEY (etapa_id, estado)
      );
      CREATE TABLE IF NOT EXISTS panel (
        id      INTEGER PRIMARY KEY,
        bloques TEXT NOT NULL,
        cubre   TEXT,
        lado    TEXT
      );
      CREATE TABLE IF NOT EXISTS etapa_panel (
        etapa_id INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        panel_id INTEGER NOT NULL REFERENCES panel(id) ON DELETE CASCADE,
        hueco    REAL,
        PRIMARY KEY (etapa_id, panel_id)
      );
      CREATE TABLE IF NOT EXISTS camara (
        id         INTEGER PRIMARY KEY,
        encuadre   TEXT,
        movimiento TEXT,
        UNIQUE (encuadre, movimiento)
      );
      CREATE TABLE IF NOT EXISTS etapa_camara (
        etapa_id  INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        camara_id INTEGER NOT NULL REFERENCES camara(id) ON DELETE CASCADE,
        PRIMARY KEY (etapa_id)
      );
      CREATE TABLE IF NOT EXISTS voz (
        id    INTEGER PRIMARY KEY,
        trato TEXT NOT NULL,
        sobre TEXT,
        dura  REAL
      );
      CREATE TABLE IF NOT EXISTS etapa_voz (
        etapa_id INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        voz_id   INTEGER NOT NULL REFERENCES voz(id) ON DELETE CASCADE,
        PRIMARY KEY (etapa_id)
      );
      -- **La entidad que relaciona otras.** Trato, plano y densidad viajaban
      -- repetidos en cada fila de `escena_desc`; aqui son una combinacion con
      -- nombre, que es lo que permite decir «estas tres etapas son del mismo
      -- tipo» sin comparar tres cadenas.
      CREATE TABLE IF NOT EXISTS tipo_escena (
        id       INTEGER PRIMARY KEY,
        trato    TEXT,
        plano    TEXT,
        densidad TEXT,
        UNIQUE (trato, plano, densidad)
      );
      CREATE TABLE IF NOT EXISTS etapa_tipo (
        etapa_id INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
        tipo_id  INTEGER NOT NULL REFERENCES tipo_escena(id) ON DELETE CASCADE,
        por_que  TEXT,
        PRIMARY KEY (etapa_id)
      );

-- de `migraciones._quien_es_agencia`
CREATE TABLE IF NOT EXISTS tipo_autor (
        id     INTEGER PRIMARY KEY,
        nombre TEXT NOT NULL UNIQUE
      );
      CREATE TABLE IF NOT EXISTS permiso (
        id      INTEGER PRIMARY KEY,
        nombre  TEXT NOT NULL UNIQUE,
        por_que TEXT
      );
      -- **La agencia: que puede hacer cada tipo.** Va por tipo y no por autor
      -- porque el derecho es de la clase — «aprobar es de una persona» vale para
      -- cualquier persona, no solo para la que hay hoy.
      CREATE TABLE IF NOT EXISTS agencia (
        tipo_id    INTEGER NOT NULL REFERENCES tipo_autor(id) ON DELETE CASCADE,
        permiso_id INTEGER NOT NULL REFERENCES permiso(id) ON DELETE CASCADE,
        PRIMARY KEY (tipo_id, permiso_id)
      );
      CREATE TABLE IF NOT EXISTS autor (
        id      INTEGER PRIMARY KEY,
        tipo_id INTEGER NOT NULL REFERENCES tipo_autor(id),
        nombre  TEXT NOT NULL UNIQUE
      );
      -- La persona es una entidad, no una fila de `autor` con una etiqueta:
      -- tiene nombre propio y **su** identidad de marca.
      -- **Y su marca NO se guarda aqui: se apunta.** Jaime: *«las
      -- indicaciones son los contratos»*, y el contrato de la marca ya
      -- existe — `contrato/marca.py :: MARCA`, la parte fija del contrato
      -- del disenador, con sus palabras: *«el contrato del disenador tiene
      -- dos partes: una variable, que es la que da el compositor, y otra
      -- fija, que son las reglas de la marca personal»*. Copiar esa prosa a
      -- una tabla seria la segunda carta. `marca` dice **cual** bloque le
      -- toca, y por eso otra persona trae el suyo sin tocar nada mas.
      CREATE TABLE IF NOT EXISTS persona (
        autor_id INTEGER PRIMARY KEY REFERENCES autor(id) ON DELETE CASCADE,
        nombre   TEXT NOT NULL,
        marca    TEXT
      );


-- **Como se escribio cada autor, historicamente.** Quince formas para diez
-- actores: `Jaime` y `jaime`, `el compositor` y `compositor`, `diseno` y
-- `disenador`. Resolverlas recortando la cadena en el codigo es decidir
-- comparando texto — justo lo que C-363 quito de la agencia. Aqui la
-- equivalencia esta declarada, se puede mirar y se puede discutir.
CREATE TABLE IF NOT EXISTS autor_alias (
  alias    TEXT PRIMARY KEY,
  autor_id INTEGER NOT NULL REFERENCES autor(id) ON DELETE CASCADE
);


-- **El trato, el plano, el color y el remedio: cuatro catalogos.** Jaime,
-- 10-9-2026, despues de la camara: *«sigue con trato, plano, color y remedio»*.
-- Eran texto libre en `escena_desc` —5, 3, 3 y 4 valores en 62 filas— y
-- `tipo_escena` repetia el fallo un piso mas arriba: se creo el mismo dia
-- guardando `trato`, `plano` y `densidad` como texto, o sea la seleccion
-- hecha de cadenas en vez de claves.
--
-- `tipo_escena` pasa a ser lo que su nombre dice: la seleccion que relaciona
-- otras entidades. `remedio` va aparte porque no es un tipo — es la decision
-- sobre un problema de integridad, y por eso cuelga de la etapa y no del tipo.
CREATE TABLE IF NOT EXISTS trato   (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS plano   (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS color   (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS remedio (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS nivel   (id INTEGER PRIMARY KEY, nombre TEXT NOT NULL UNIQUE);

CREATE TABLE IF NOT EXISTS etapa_remedio (
  etapa_id   INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
  remedio_id INTEGER NOT NULL REFERENCES remedio(id) ON DELETE CASCADE,
  PRIMARY KEY (etapa_id)
);


-- (`transicion.en_su_lugar` lo anade `migraciones._retiradas_fuera_del_catalogo`:
--  un ALTER no es idempotente y este fichero se corre en cada arranque.)
;
