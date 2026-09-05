-- Base de decisiones del montaje. SQLite, en tercera forma normal.
--
-- Jaime: «hazla relacional con varias entidades —video, frame, parte del frame,
-- mensaje esperado— pero mantén un nivel de normalización de tercer nivel, sin
-- excusas y desde origen; eso nos va a facilitar mucho el trabajo».
--
-- ## Qué se gana con normalizar
--
-- Hasta ahora las decisiones vivían repartidas en cuatro JSON y el mismo dato
-- aparecía en dos sitios. Eso ya costó cuatro fallos registrados en
-- `docs/correcciones.md` — C-04, C-05, el aprendizaje 33 y el 43: siempre el
-- mismo patrón, dos fuentes que se separan en cuanto una cambia.
--
-- En 3FN eso deja de ser posible por construcción: cada hecho vive en un sitio.
-- El nombre de una estructura está en `estructura`, no repetido en cada vídeo;
-- el texto de una unidad está en `unidad`, no copiado en cada asignación.
--
-- ## Las tres formas, y dónde se aplican aquí
--
-- 1FN — nada de grupos repetidos. Por eso `tarjeta_bloque` es una tabla y no
--       una lista dentro de la tarjeta, y `placa_etapa` es una tabla y no un
--       array `sirve[]`.
-- 2FN — ningún atributo depende de parte de una clave compuesta. Las claves
--       compuestas de este esquema (`placa_etapa`, `etapa_canonica`) sólo
--       llevan atributos que dependen de la clave entera.
-- 3FN — ninguna dependencia transitiva. `video` guarda `estructura_id`, nunca
--       el nombre de la estructura; `asignacion` guarda `unidad_id`, nunca el
--       texto de la unidad.
--
--   sqlite3 ads/decisiones.db < scripts/esquema.sql

PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────────────
-- CATÁLOGO: lo que existe con independencia de un vídeo concreto
-- ─────────────────────────────────────────────────────────────────────────

-- Las seis estructuras de ads de pago del playbook.
CREATE TABLE IF NOT EXISTS estructura (
  id        INTEGER PRIMARY KEY,
  nombre    TEXT NOT NULL UNIQUE,          -- «Information Gap»
  descripcion TEXT
);

-- La secuencia canónica de cada estructura. Es la que manda: el guion se
-- reparte DENTRO de ella, no al revés.
CREATE TABLE IF NOT EXISTS etapa_canonica (
  estructura_id INTEGER NOT NULL REFERENCES estructura(id) ON DELETE CASCADE,
  orden         INTEGER NOT NULL,          -- 1, 2, 3…
  nombre        TEXT NOT NULL,             -- «coste de no entenderlo»
  PRIMARY KEY (estructura_id, orden)
);

-- Mecanismos conductuales. Uno primario y uno secundario como mucho por pieza;
-- son hipótesis de trabajo, no botones.
CREATE TABLE IF NOT EXISTS mecanismo (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);

-- Las tomas grabadas.
CREATE TABLE IF NOT EXISTS toma (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE              -- «20260825_135637»
);

-- Placas de fondo. `dice` es lo que muestra; `siente`, lo que provoca — y pesa
-- igual: emparejar por el objeto sólo sirve para estos seis reels, emparejar
-- por el sentimiento sirve para los cincuenta.
CREATE TABLE IF NOT EXISTS placa (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE,             -- «c8-pressure»
  dice   TEXT NOT NULL,
  siente TEXT NOT NULL
);

-- ─────────────────────────────────────────────────────────────────────────
-- LA PIEZA
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS video (
  id            INTEGER PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,      -- «reel-01»
  estructura_id INTEGER NOT NULL REFERENCES estructura(id),
  toma_id       INTEGER NOT NULL REFERENCES toma(id),
  mecanismo_primario_id   INTEGER REFERENCES mecanismo(id),
  mecanismo_secundario_id INTEGER REFERENCES mecanismo(id),
  -- Por qué se le asignó esa estructura. Se guarda porque cuatro de las seis
  -- venían mal etiquetadas y el razonamiento importa más que la etiqueta.
  porque        TEXT
);

-- **La parte del frame.** Una fila por etapa de la pieza, en orden.
--
-- `mensaje_esperado` es lo que esa etapa tiene que comunicar — sale del libreto,
-- pero entra como DESCRIPCIÓN, no como el texto a buscar: el libreto es
-- accidental y el módulo es el copy.
CREATE TABLE IF NOT EXISTS etapa (
  id               INTEGER PRIMARY KEY,
  video_id         INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
  orden            INTEGER NOT NULL,
  -- Apunta a la etapa canónica de la estructura. El NOMBRE no se copia aquí:
  -- eso sería dependencia transitiva.
  estructura_id    INTEGER NOT NULL,
  etapa_orden      INTEGER NOT NULL,
  mensaje_esperado TEXT NOT NULL,
  obligatorio      INTEGER NOT NULL DEFAULT 0,
  UNIQUE (video_id, orden),
  FOREIGN KEY (estructura_id, etapa_orden)
    REFERENCES etapa_canonica(estructura_id, orden)
);

-- Unidades de audio: un intento continuo de una sola toma, con sus pausas
-- dentro. Nunca dos trozos cosidos.
CREATE TABLE IF NOT EXISTS unidad (
  id      INTEGER PRIMARY KEY,
  toma_id INTEGER NOT NULL REFERENCES toma(id) ON DELETE CASCADE,
  desde   REAL NOT NULL,
  hasta   REAL NOT NULL,
  texto   TEXT NOT NULL,
  aire    REAL NOT NULL DEFAULT 0,   -- silencio interno medido, en segundos
  abre    INTEGER NOT NULL DEFAULT 0,-- empieza en mayúscula
  cierra  INTEGER NOT NULL DEFAULT 0,-- acaba en punto
  voz_st  REAL,                      -- expresividad medida, en semitonos
  UNIQUE (toma_id, desde, hasta),
  CHECK (hasta > desde)
);

-- ─────────────────────────────────────────────────────────────────────────
-- LA DECISIÓN — el corazón de la base
-- ─────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS estado_decision (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO estado_decision (id, nombre) VALUES
  (1, 'pendiente'),   -- lo elige el paso 2
  (2, 'aprobado'),    -- está bien; NO se re-elige
  (3, 'recortar'),    -- sirve, pero entra o sale mal: se conserva y se recorta
  (4, 'rechazado');   -- no sirve: la etapa va con animación

CREATE TABLE IF NOT EXISTS decidido_por (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO decidido_por (id, nombre) VALUES
  (1, 'codigo'), (2, 'ia'), (3, 'jaime');

-- Una etapa, una decisión. Es lo que permite corregir un segmento sin mover los
-- demás: se cambia esta fila y el resto sale idéntico.
-- ─────────────────────────────────────────────────────────────────────────
-- LA CANDIDATURA — qué trozo de cinta puede servir para qué función
-- ─────────────────────────────────────────────────────────────────────────
--
-- Regla de Jaime: *«cada sección de la cinta se relaciona con lo que debe decir
-- en el libreto y a su vez con la función en el frame»*. Y antes: *«tienes que
-- catalogar toda la grabación y de ahí seleccionar las mejores tomas»*.
--
-- `asignacion` no puede llevar esto: tiene `etapa_id` de clave primaria, así que
-- sólo cabe **la decisión**, una por etapa. Lo que faltaba es la tabla de lo
-- POSIBLE — cada unidad contra cada etapa, con si dice lo que la etapa exige y
-- cuánto de su mensaje cubre.
--
-- Es la diferencia entre buscar y catalogar. Buscando se para en el primer
-- trozo que encaja; con esta tabla delante se ven los ocho sitios donde se dice
-- el 53,53% y se elige. Eso es lo que el montaje no estaba haciendo.
CREATE TABLE IF NOT EXISTS candidatura (
  etapa_id  INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
  unidad_id INTEGER NOT NULL REFERENCES unidad(id) ON DELETE CASCADE,
  -- ¿dice lo que la etapa declara que hay que decir? (`debe_decir` del frame)
  dice      INTEGER NOT NULL DEFAULT 0,
  -- cuánto del mensaje esperado cubre, de 0 a 1
  cubre     REAL NOT NULL DEFAULT 0,
  PRIMARY KEY (etapa_id, unidad_id)
);

CREATE TABLE IF NOT EXISTS asignacion (
  etapa_id        INTEGER PRIMARY KEY REFERENCES etapa(id) ON DELETE CASCADE,
  unidad_id       INTEGER REFERENCES unidad(id),  -- NULL = va con animación
  estado_id       INTEGER NOT NULL REFERENCES estado_decision(id),
  decidido_por_id INTEGER NOT NULL REFERENCES decidido_por(id),
  entra_en        REAL,   -- recorte de entrada, si lo hay
  sale_en         REAL,   -- recorte de salida, si lo hay
  por_que         TEXT,
  fecha           TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ─────────────────────────────────────────────────────────────────────────
-- LO QUE SE VE
-- ─────────────────────────────────────────────────────────────────────────

-- Qué placa acompaña a qué etapa. Tabla propia y no una lista: una placa sirve
-- a varias etapas y una etapa admite varias placas candidatas.
CREATE TABLE IF NOT EXISTS placa_etapa (
  placa_id INTEGER NOT NULL REFERENCES placa(id) ON DELETE CASCADE,
  etapa_id INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
  elegida  INTEGER NOT NULL DEFAULT 0,   -- 1 = la que se usa
  PRIMARY KEY (placa_id, etapa_id)
);

-- Copy de la tarjeta de una etapa sin toma.
CREATE TABLE IF NOT EXISTS tarjeta (
  etapa_id INTEGER PRIMARY KEY REFERENCES etapa(id) ON DELETE CASCADE,
  pie      TEXT
);

-- Los bloques y las líneas del remate, en tablas propias: 1FN prohíbe el grupo
-- repetido dentro de la tarjeta.
CREATE TABLE IF NOT EXISTS tarjeta_bloque (
  etapa_id INTEGER NOT NULL REFERENCES tarjeta(etapa_id) ON DELETE CASCADE,
  orden    INTEGER NOT NULL,
  texto    TEXT NOT NULL,
  PRIMARY KEY (etapa_id, orden)
);
CREATE TABLE IF NOT EXISTS tarjeta_remate (
  etapa_id INTEGER NOT NULL REFERENCES tarjeta(etapa_id) ON DELETE CASCADE,
  orden    INTEGER NOT NULL,
  texto    TEXT NOT NULL,
  PRIMARY KEY (etapa_id, orden)
);

-- La marca de humanidad. Una o dos por minuto — en piezas de 80-90 s, UNA — así
-- que va por etapa y el conteo por vídeo es una consulta, no un campo.
CREATE TABLE IF NOT EXISTS marca_humanidad (
  etapa_id       INTEGER PRIMARY KEY REFERENCES etapa(id) ON DELETE CASCADE,
  dice           TEXT NOT NULL,   -- lo que se oye
  es             TEXT NOT NULL,   -- lo que se lee
  blanco_y_negro INTEGER NOT NULL DEFAULT 0,
  maximo_s       REAL NOT NULL DEFAULT 1.6,
  por_que        TEXT
);

-- Decisiones de oído sobre la pieza entera, no sobre una etapa: la apertura en
-- frío y el cierre. Van aquí y no en `asignacion` porque no pertenecen a una
-- etapa concreta.
CREATE TABLE IF NOT EXISTS corte_fijo (
  id       INTEGER PRIMARY KEY,
  video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
  papel    TEXT NOT NULL CHECK (papel IN ('apertura', 'cierre')),
  orden    INTEGER NOT NULL DEFAULT 0,
  desde    REAL NOT NULL,
  hasta    REAL NOT NULL,
  por_que  TEXT,
  UNIQUE (video_id, papel, orden),
  CHECK (hasta > desde)
);

-- ─────────────────────────────────────────────────────────────────────────
-- EL LOG DE CORRECCIONES
-- ─────────────────────────────────────────────────────────────────────────

-- Una entrada no está cerrada hasta que `mecanismo` apunta a un fichero: una
-- corrección que sólo arregla la instancia no está hecha.
CREATE TABLE IF NOT EXISTS correccion (
  id        INTEGER PRIMARY KEY,
  codigo    TEXT NOT NULL UNIQUE,   -- «C-01»
  fecha     TEXT NOT NULL,
  sintoma   TEXT NOT NULL,
  causa     TEXT NOT NULL,
  mecanismo TEXT,                   -- fichero donde quedó imposible repetirlo
  deteccion TEXT,
  video_id  INTEGER REFERENCES video(id)
);

-- ─────────────────────────────────────────────────────────────────────────
-- VISTAS: lo que el montaje pregunta
-- ─────────────────────────────────────────────────────────────────────────

-- El plan de una pieza, listo para montar. Aquí sí se juntan los nombres —
-- una vista puede desnormalizar; una tabla no.
CREATE VIEW IF NOT EXISTS v_plan AS
SELECT v.slug            AS video,
       e.orden           AS etapa_n,
       ec.nombre         AS etapa,
       e.obligatorio,
       e.mensaje_esperado,
       ed.nombre         AS estado,
       dp.nombre         AS decidido_por,
       COALESCE(a.entra_en, u.desde) AS desde,
       COALESCE(a.sale_en,  u.hasta) AS hasta,
       u.texto,
       u.voz_st,
       a.por_que
FROM etapa e
JOIN video v          ON v.id = e.video_id
JOIN etapa_canonica ec ON ec.estructura_id = e.estructura_id
                      AND ec.orden = e.etapa_orden
LEFT JOIN asignacion a ON a.etapa_id = e.id
LEFT JOIN unidad u     ON u.id = a.unidad_id
LEFT JOIN estado_decision ed ON ed.id = a.estado_id
LEFT JOIN decidido_por dp    ON dp.id = a.decidido_por_id
ORDER BY v.slug, e.orden;

-- Qué le falta a cada pieza para poder publicarse.
CREATE VIEW IF NOT EXISTS v_pendiente AS
SELECT v.slug AS video, e.orden AS etapa_n, ec.nombre AS etapa, e.obligatorio
FROM etapa e
JOIN video v           ON v.id = e.video_id
JOIN etapa_canonica ec  ON ec.estructura_id = e.estructura_id
                       AND ec.orden = e.etapa_orden
LEFT JOIN asignacion a  ON a.etapa_id = e.id
WHERE a.etapa_id IS NULL OR a.estado_id = 1
ORDER BY e.obligatorio DESC, v.slug, e.orden;

-- ─────────────────────────────────────────────────────────────────────────
-- LA MEMORIA: nada queda fuera
-- ─────────────────────────────────────────────────────────────────────────
--
-- Jaime: «todo se registra en la base de datos, nada queda por fuera; la base
-- de datos es la memoria del proyecto y de cada etapa de cada vídeo».
--
-- Por eso también entran aquí las mediciones y los renders. Un número medido
-- que vive en la salida de una consola se pierde en cuanto se cierra, y luego
-- se vuelve a medir o —peor— se supone.

-- Cada render, con su configuración y lo que tardó. Sirve para dos cosas:
-- saber qué se entregó, y no volver a discutir qué configuración es más rápida.
CREATE TABLE IF NOT EXISTS render (
  id        INTEGER PRIMARY KEY,
  video_id  INTEGER REFERENCES video(id) ON DELETE CASCADE,
  fecha     TEXT NOT NULL DEFAULT (datetime('now')),
  proposito TEXT NOT NULL CHECK (proposito IN ('entrega','revision','banco')),
  ancho     INTEGER NOT NULL,
  alto      INTEGER NOT NULL,
  frames    INTEGER,
  segundos  REAL NOT NULL,          -- lo que tardó
  config    TEXT NOT NULL,          -- las banderas, literales
  nota      TEXT
);

-- Tipos de medición, para no repetir la cadena en cada fila.
CREATE TABLE IF NOT EXISTS tipo_medicion (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE,
  unidad TEXT NOT NULL
);
INSERT OR IGNORE INTO tipo_medicion (id, nombre, unidad) VALUES
  (1,'sonoridad','LUFS'),
  (2,'pico_real','dBTP'),
  (3,'muestras_saturadas','muestras'),
  (4,'duracion','s'),
  (5,'expresividad','semitonos'),
  (6,'aire_quitado','s');

-- Una medición, de una pieza o de una etapa concreta.
CREATE TABLE IF NOT EXISTS medicion (
  id       INTEGER PRIMARY KEY,
  video_id INTEGER REFERENCES video(id) ON DELETE CASCADE,
  etapa_id INTEGER REFERENCES etapa(id) ON DELETE CASCADE,
  tipo_id  INTEGER NOT NULL REFERENCES tipo_medicion(id),
  valor    REAL NOT NULL,
  fecha    TEXT NOT NULL DEFAULT (datetime('now')),
  nota     TEXT
);

CREATE VIEW IF NOT EXISTS v_memoria AS
SELECT v.slug AS video, tm.nombre AS medida, m.valor, tm.unidad,
       e.orden AS etapa_n, m.fecha, m.nota
FROM medicion m
LEFT JOIN video v ON v.id = m.video_id
LEFT JOIN etapa e ON e.id = m.etapa_id
JOIN tipo_medicion tm ON tm.id = m.tipo_id
ORDER BY m.fecha DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- El fragmento, la escena y el libreto: cada uno con su instancia
--
-- Correccion de Jaime, y tenia razon: *«cada parte o cada fragmento debe
-- guardarse por separado, e identificarse por separado; de esa manera el
-- segmento queda relacionado a un video, pero tambien a un frame, y tambien a
-- una intencion comunicativa o libreto»*. Y despues: *«no creo que este al
-- tercer grado si cada uno de estos elementos no tiene su propia instancia»*.
--
-- Lo que fallaba: la tabla `propuesta` guardaba `desde`, `hasta` y `texto`
-- DENTRO de la fila de la eleccion. O sea el fragmento no existia — era un
-- atributo de la decision, y su texto dependia transitivamente de un rango que
-- no era la clave. Con dos elecciones sobre el mismo trozo, el texto quedaba
-- escrito dos veces y podia divergir: exactamente el defecto que la 3FN
-- previene y que a este proyecto ya le costo cuatro fallos (C-04, C-05, 33, 43).
--
-- Las tres entidades que faltaban, y que responde cada una:
--
--   libreto    - QUE habia que decir ahi. La intencion comunicativa, en sus
--                palabras. Es del video y del orden, no de la etapa canonica:
--                dos videos con la misma estructura dicen cosas distintas.
--   fragmento  - QUE TROZO DE CINTA es. Existe por si mismo, se puede oir, se
--                puede aprobar, y **sobrevive a que la eleccion cambie**.
--   escena     - COMO SE VE ese fragmento. Un fragmento se parte en varias
--                escenas por encuadre; la escena no es otro trozo de cinta, es
--                otro modo de mirarlo.
--
-- Y el fragmento se relaciona con las unidades que abarca en vez de repetir su
-- texto: `fragmento_unidad`. El texto vive en `unidad` y en ningun sitio mas.

CREATE TABLE IF NOT EXISTS libreto (
  id       INTEGER PRIMARY KEY,
  video_id INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
  orden    INTEGER NOT NULL,
  texto    TEXT NOT NULL,
  UNIQUE (video_id, orden)
);

CREATE TABLE IF NOT EXISTS fragmento (
  id      INTEGER PRIMARY KEY,
  toma_id INTEGER NOT NULL REFERENCES toma(id) ON DELETE CASCADE,
  desde   REAL NOT NULL,
  hasta   REAL NOT NULL,
  -- De donde salio: el reparto, una decision de Jaime, un corte fijo.
  origen  TEXT NOT NULL DEFAULT 'reparto',
  UNIQUE (toma_id, desde, hasta),
  CHECK (hasta > desde)
);

CREATE TABLE IF NOT EXISTS fragmento_unidad (
  fragmento_id INTEGER NOT NULL REFERENCES fragmento(id) ON DELETE CASCADE,
  unidad_id    INTEGER NOT NULL REFERENCES unidad(id) ON DELETE CASCADE,
  PRIMARY KEY (fragmento_id, unidad_id)
);

-- Que fragmento cumple que etapa. Es la eleccion, y **solo la eleccion**: ni el
-- rango ni el texto viven aqui.
CREATE TABLE IF NOT EXISTS eleccion (
  etapa_id     INTEGER PRIMARY KEY REFERENCES etapa(id) ON DELETE CASCADE,
  fragmento_id INTEGER REFERENCES fragmento(id) ON DELETE SET NULL,
  cubre        REAL,
  dice         INTEGER NOT NULL DEFAULT 0,
  quien        TEXT NOT NULL DEFAULT 'seleccionar',
  fecha        TEXT
);

CREATE TABLE IF NOT EXISTS escena (
  id           INTEGER PRIMARY KEY,
  fragmento_id INTEGER NOT NULL REFERENCES fragmento(id) ON DELETE CASCADE,
  orden        INTEGER NOT NULL,
  origen_desde REAL NOT NULL,
  origen_hasta REAL NOT NULL,
  encuadre     TEXT,
  zoom_hasta   REAL,
  UNIQUE (fragmento_id, orden)
);

-- El embudo: cada fragmento pasa por sus etapas, y sólo se renderiza lo bueno
--
-- Jaime: *«tenemos un embudo: primero ponemos cada cosa en su lugar, luego
-- escogemos la mejor, luego la preparamos para que este bien —pero ya no todo
-- el video, esa parte especifica— y luego renderizamos, pero solo lo que ya
-- sabemos que esta bien»*.
--
-- La consecuencia de fondo es que **la unidad de render es el fragmento**, no
-- la pieza. Eso cambia dos cosas de golpe:
--
--   1. Corregir un segmento deja de costar un montaje entero. Se vuelve a
--      cortar ese fichero y los demas quedan idénticos — que es la «semi
--      aplicacion» que Jaime pidio hace tiempo y que hasta ahora dependia de
--      que nadie tocara lo demas.
--   2. **Desaparece el acoplamiento a una sola cinta.** El corte abria un solo
--      `-i` y `punch-ins.py` calculaba un ancla por fichero, asi que un reel
--      con material de dos sesiones salia descuadrado (aprendizaje 20). Con el
--      fragmento como unidad, cada uno se corta de SU fichero con SU ancla: no
--      hay dos fuentes en un corte, hay dos cortes.
--
-- Los estados son el embudo, en orden, y ninguno se salta:
--
--   catalogado - existe en la cinta y esta indexado
--   elegido    - cumple una etapa; es la mejor candidata de esa seccion
--   preparado  - ya se le hizo la revision estricta: sin redundancia, extremos
--                limpios, dato declarado presente
--   cortado    - tiene fichero propio en work/fragmentos/
--   aprobado   - Jaime lo oyo y vale
--   rechazado  - no vale; la etapa va con tablero y no se busca sustituto

CREATE TABLE IF NOT EXISTS fase (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE,
  orden  INTEGER NOT NULL
);
INSERT OR IGNORE INTO fase (nombre, orden) VALUES
  ('catalogado', 1), ('elegido', 2), ('preparado', 3),
  ('cortado', 4), ('aprobado', 5), ('rechazado', 0);

-- El estado de cada fragmento y su fichero. Va aparte de `fragmento` porque el
-- fragmento es lo que ES —un trozo de cinta— y esto es por donde VA.
CREATE TABLE IF NOT EXISTS paso (
  fragmento_id INTEGER PRIMARY KEY REFERENCES fragmento(id) ON DELETE CASCADE,
  fase_id      INTEGER NOT NULL REFERENCES fase(id),
  fichero      TEXT,
  duracion     REAL,
  por_que      TEXT,
  fecha        TEXT
);

-- La tabla de colocacion: el registro de renderizado
--
-- Idea de Jaime: *«la tabla de renderizado tiene id de video de entrada, id de
-- video de salida (renderizado fragmento), id segmento de entrada, id segmento
-- esperado por libreto, posicion en el video de salida; las transiciones ocupan
-- una columna y lo que tenemos es un registro de renderizado»*.
--
-- Es una tabla de conexiones, y es la pieza que faltaba: hasta ahora la linea
-- de tiempo vivia dentro de `edl-sell.json` y de `plan-full.json`, o sea en dos
-- ficheros que se derivan uno del otro y se separan en cuanto uno cambia.
--
-- Tres decisiones sobre la forma, y las tres evitan que se separe:
--
--   * **El video de entrada NO es columna.** Se llega por `fragmento -> toma`.
--     Guardarlo aqui seria dependencia transitiva —el defecto que tenia
--     `propuesta`— y permitiria que un dia dijeran cosas distintas.
--   * **La transicion NO es columna: es su propia tabla** (`empalme`). Empezo
--     siendo una columna «la que entra a esta fila», y Jaime lo corrigio —*«las
--     transiciones a otra tabla mejor»*—. Tiene razon y el motivo es que una
--     transicion **tiene cosas propias**: dura, puede llevar sonido, puede
--     tener parametros. Como columna solo cabe su nombre, y la duracion de la
--     cortinilla acabaria escrita en otro sitio.
--   * **La huella cierra el registro.** Es el resumen de todo lo que decide
--     como se ve esta pieza —fragmento, encuadre, transicion, tratamiento—: si
--     no cambio, no se vuelve a renderizar. Eso es lo que hace que el peldaño
--     caro solo toque lo que cambio, en vez de la pieza entera.
--
-- Y `fragmento_id` puede ser NULL a proposito: un tablero o una tarjeta ocupan
-- su sitio en la linea de tiempo y **no salen de la cinta**. Esa es la union de
-- la teorica y la practica de la que hablaba Jaime — aqui se ve que puede
-- faltar cualquiera de los dos lados.

CREATE TABLE IF NOT EXISTS transicion (
  id     INTEGER PRIMARY KEY,
  nombre TEXT NOT NULL UNIQUE
);
INSERT OR IGNORE INTO transicion (nombre) VALUES
  ('corte'), ('glitch'), ('cortinilla'), ('barrido'), ('encadenado'), ('ninguna');

CREATE TABLE IF NOT EXISTS colocacion (
  id            INTEGER PRIMARY KEY,
  video_id      INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
  orden         INTEGER NOT NULL,
  -- Donde empieza en la linea de tiempo de SALIDA, en segundos.
  desde_s       REAL NOT NULL,
  dura_s        REAL NOT NULL,
  -- El segmento de entrada. NULL cuando la pieza no sale de la cinta.
  fragmento_id  INTEGER REFERENCES fragmento(id) ON DELETE SET NULL,
  -- La seccion de frame que sirve: el segmento esperado por el libreto.
  etapa_id      INTEGER REFERENCES etapa(id) ON DELETE SET NULL,
  tipo          TEXT NOT NULL DEFAULT 'toma',
  -- El fragmento ya renderizado, y la huella de lo que lo produjo.
  fichero       TEXT,
  huella        TEXT,
  fecha         TEXT,
  UNIQUE (video_id, orden)
);
CREATE INDEX IF NOT EXISTS colocacion_huella ON colocacion (huella);


-- El empalme: el hecho que ocurre ENTRE dos colocaciones
--
-- *«Las transiciones a otra tabla mejor.»* Y es lo correcto: una transicion no
-- es un atributo de una pieza, es lo que pasa entre dos — con duracion propia,
-- con sonido propio, y a veces sin ninguna de las dos piezas (la apertura no
-- tiene antes; el cierre no tiene despues).
--
-- `antes_id` NULL es la apertura de la pieza; `despues_id` NULL es el cierre.
-- La unicidad va sobre `despues_id` porque **a cada pieza se entra una sola
-- vez**: eso impide escribir dos veces el mismo empalme, que es justo lo que
-- pasaria con la transicion como columna en las dos filas.

CREATE TABLE IF NOT EXISTS empalme (
  id            INTEGER PRIMARY KEY,
  video_id      INTEGER NOT NULL REFERENCES video(id) ON DELETE CASCADE,
  antes_id      INTEGER REFERENCES colocacion(id) ON DELETE CASCADE,
  despues_id    INTEGER REFERENCES colocacion(id) ON DELETE CASCADE,
  transicion_id INTEGER NOT NULL REFERENCES transicion(id),
  dura_s        REAL NOT NULL DEFAULT 0,
  -- El sonido va en el frame del movimiento que lo produce, asi que el empalme
  -- es quien sabe cual toca. NULL = el corte no suena.
  sonido        TEXT,
  UNIQUE (video_id, despues_id)
);

-- Varias tomas para el mismo segmento esperado: la relacion es 1:N
--
-- Recordatorio de Jaime: *«la relacion entre segmento esperado y segmento
-- grabado no es 1:1, es 1:N — varias tomas para el mismo segmento, por eso
-- escogemos la mejor»*.
--
-- El modelo tenia la decision (`eleccion`, una fila por etapa) y no tenia las
-- alternativas: las 700-1.300 ventanas candidatas vivian en memoria dentro de
-- `seleccionar.py` y solo sobrevivia la ganadora. Consecuencias, las tres
-- reales:
--
--   * No se podia decir «esta no sirve, usa la siguiente» sin volver a correr
--     la seleccion entera y confiar en que diera lo mismo.
--   * No se veia **por que** gano una: sin las otras al lado, la puntuacion es
--     un numero suelto.
--   * Y la expresividad —el paso 3 de Jaime, «entre las que dicen lo mismo
--     manda la emocion»— no tenia donde aplicarse: medirla sobre mil ventanas
--     es carisimo, sobre cinco finalistas es gratis. Es el embudo otra vez: el
--     recurso caro solo sobre lo que ya paso el filtro barato.
--
-- `puesto` es el orden en que quedaron, no una nota: 1 es la elegida. Y
-- `descartada_por` guarda el motivo cuando alguien la tumba a mano, que es lo
-- que hace que rechazar una toma sea una decision registrada y no un borrado.

CREATE TABLE IF NOT EXISTS candidato (
  etapa_id       INTEGER NOT NULL REFERENCES etapa(id) ON DELETE CASCADE,
  fragmento_id   INTEGER NOT NULL REFERENCES fragmento(id) ON DELETE CASCADE,
  puesto         INTEGER NOT NULL,
  puntuacion     REAL,
  cubre          REAL,
  dice           INTEGER NOT NULL DEFAULT 0,
  voz_st         REAL,
  descartada_por TEXT,
  PRIMARY KEY (etapa_id, fragmento_id)
);
CREATE INDEX IF NOT EXISTS candidato_orden ON candidato (etapa_id, puesto);

-- La densidad de una idea la juzga la IA, no un contador de digitos
--
-- Correccion de Jaime: *«apenas tenemos los libretos o los segmentos podemos
-- identificar la densidad del mismo; eso lo tienes que hacer tu como IA, no se
-- si sea buena idea delegarlo a un Python»*.
--
-- No lo es, y la prueba fue el primer intento: `compleja()` devolvia cierto si
-- el parrafo tenia una cifra o mas de 40 palabras. Con esa regla «53,53% de
-- impuesto marginal sobre un salario» y «cuesta 20 dolares» pesan igual, que es
-- evidentemente falso. La densidad es cuanto tiene que sostener el espectador a
-- la vez —cuantos terminos nuevos, cuantas condiciones encadenadas, cuanta
-- cuenta que no puede rebobinar— y eso es una lectura de sentido.
--
-- Se guarda porque es el paso no determinista: decidido una vez, se reutiliza.
-- El proyecto ya lo exige para el paso 2 (*«lo que es por IA debe tener un
-- mecanismo para que siempre lo hagas exactamente igual»*) y esta es la misma
-- clase de decision.
--
-- `figura` es lo otro que solo se ve leyendo: que se podria DIBUJAR de esto —un
-- odontologo, una señal de prohibido, un camino que se bifurca—. Un Python
-- puede buscar la palabra «dentista»; no puede ver que «usted no va a X» pide
-- un camino que se divide.

CREATE TABLE IF NOT EXISTS densidad (
  video_slug  TEXT NOT NULL,
  etapa_orden INTEGER NOT NULL,
  nivel       TEXT NOT NULL CHECK (nivel IN ('baja','media','alta')),
  figura      TEXT,
  por_que     TEXT NOT NULL,
  quien       TEXT NOT NULL DEFAULT 'ia',
  fecha       TEXT,
  PRIMARY KEY (video_slug, etapa_orden)
);

-- La descripcion de la escena, no su puntuacion
--
-- Correccion de Jaime: *«incluso puedes determinar el tipo de grafico desde
-- antes de que lo renderices, sabes que debe ir en cada lugar, y si para la
-- emocion que queremos representar conviene cambiar artificialmente la
-- composicion del color, puedes avivarlo o apagarlo. Aca el punto no es
-- puntuar, el punto es tener una descripcion de la escena»*.
--
-- Y antes: *«no existe otra herramienta en el mundo que pueda hacer un analisis
-- de complejidad acertado»*. Ese es el argumento entero: reducir la escena a un
-- numero tira lo unico que un modelo de lenguaje aporta. `alta` no dice que
-- dibujar; «una cantidad, una raya, y el momento en que la cruza» si.
--
-- Cada columna responde algo que el render necesita y ninguna metrica contesta:
--
--   que_pasa    - la escena en una frase: lo que el grafico tiene que decir
--   emocion     - a donde va el espectador; decide color y ritmo
--   componente  - cual tablero del canon sirve, si sirve alguno
--   grafico     - que se dibuja EN CONCRETO, no «un diagrama»
--   color       - avivar, apagar o dejar; el oro va donde hay que mirar
--   sonido      - el movimiento que suena: si se pega, suena a pegado
--   plano       - donde esta Jaime: en cuadro, cerrado o fuera

CREATE TABLE IF NOT EXISTS escena_desc (
  video_slug  TEXT NOT NULL,
  etapa_orden INTEGER NOT NULL,
  que_pasa    TEXT NOT NULL,
  emocion     TEXT,
  componente  TEXT,
  grafico     TEXT,
  color       TEXT CHECK (color IN ('avivar','apagar','dejar')),
  sonido      TEXT,
  plano       TEXT CHECK (plano IN ('en cuadro','cerrado','fuera')),
  -- **El tratamiento lo decide el LLM, no un umbral.** Jaime: *«el tablero no
  -- exige una lectura plana, la tolera, la permite; es alternativa cuando no hay
  -- una opcion mejor. La decision se da en funcion de dos variables:
  -- complejidad y necesidad del video, y por eso la debe tomar un LLM, porque
  -- el contexto es el video en general»*.
  --
  -- Un umbral solo ve el segmento. La segunda variable —lo que la pieza
  -- necesita— solo se ve mirando las etapas juntas, asi que se decide en el
  -- paso de descripcion, que ya recibe la pieza entera.
  trato        TEXT CHECK (trato IN ('portada','tablero','cercano','metafora','diapositiva')),
  trato_porque TEXT,
  -- Que prioriza esta etapa entre dos tomas que dicen lo mismo. Jaime: *«para
  -- la intencion comunicativa a veces es mejor una toma limpia y sin errores,
  -- pero no es en todos los casos»*. Como no es en todos los casos, no puede
  -- ser un umbral: lo decide quien ve la pieza entera, etapa por etapa.
  prioridad    TEXT CHECK (prioridad IN ('entrega','limpieza')),
  -- **La composicion es el seguro del mensaje.** Jaime: *«no hubo lectura del
  -- guion original para entender lo que habia y si era necesario cambiarlo en
  -- la etapa de composicion de la escena, que es el seguro, y lo que permite
  -- garantizar que se respete la integridad del mensaje del guion; asi el guion
  -- no se respete, la intencion comunicativa si»*.
  --
  -- `integridad` dice que se rompe en esta etapa cuando se lee la pieza
  -- seguida: una cifra sin antecedente, un anclaje que recoge algo que nunca
  -- aparecio, una comparacion con un solo lado, una frase de dos mitades sin la
  -- segunda. NULL cuando la etapa sostiene lo que el libreto queria decir.
  --
  -- `remedio` dice que hacer con ello, y es lo que el resto del camino obedece.
  -- **El texto que esta descripcion describe.** Es lo que permite saber si
  -- caduco, y es la diferencia entre un sistema modular y uno que se rehace
  -- entero por cualquier cosa.
  --
  -- Antes se comparaban FECHAS: si el EDL se reescribia, toda la descripcion
  -- quedaba en entredicho aunque la etapa dijera exactamente lo mismo. Jaime lo
  -- corto: *«tenemos una estructura modular para poder apegarnos a la
  -- estructura sin tener que cambiar todo, pero si a cada ajuste de tuerca
  -- cambias el motor nunca vamos a llegar a ningun lado»*.
  --
  -- Con el texto guardado, caduca **solo la etapa cuyo texto se movio**. Las
  -- demas siguen valiendo, que es la razon de que el sistema sea modular.
  sobre_texto  TEXT,
  integridad   TEXT,
  -- **Cuando lo dicho contradice un dato con fuente del libreto.** No se
  -- corrige el libreto ni se tapa el desliz: el subtitulo dice la verdad encima
  -- y palpita. Jaime: *«el libreto dice la verdad, esta es una oportunidad para
  -- que el error se manifieste»*. Es cumplimiento, que es la prioridad 1 del
  -- proyecto, convertido en recurso visual en vez de en un parche.
  corrige_dice TEXT,
  corrige_es   TEXT,
  remedio      TEXT CHECK (remedio IN ('ninguno','tablero','recuperar','cortar')),
  quien       TEXT NOT NULL DEFAULT 'ia',
  fecha       TEXT,
  PRIMARY KEY (video_slug, etapa_orden)
);

-- Lo descartado despues de depurar, para que la eleccion no lo repita
--
-- Regla de Jaime: *«se revisa para retirar directamente; ahora, si queda
-- demasiado fragmentado, cosa demasiado cortada, pues pasamos a la
-- siguiente»*.
--
-- Sin esta tabla el aviso era papel: `depurar.py` decia «esta toma queda
-- picada» y la siguiente corrida volvia a elegirla, porque nada recordaba el
-- descarte. Con ella, `seleccionar.py` la excluye y toma la siguiente candidata
-- — que ya esta guardada en `candidato`, que existe justo para esto.
--
-- Y el descarte es una DECISION, no un borrado: queda con su motivo y su fecha,
-- asi que se puede revisar por que una toma no se uso.

CREATE TABLE IF NOT EXISTS descartado (
  video_slug   TEXT NOT NULL,
  etapa_orden  INTEGER NOT NULL,
  fragmento_id INTEGER REFERENCES fragmento(id) ON DELETE CASCADE,
  desde        REAL NOT NULL,
  hasta        REAL NOT NULL,
  motivo       TEXT NOT NULL,
  fecha        TEXT,
  PRIMARY KEY (video_slug, etapa_orden, desde, hasta)
);


-- La revision final, y el motivo de que sea una tabla y no un mensaje
--
-- Jaime: *«vamos a instaurar una ultima etapa, la revision final; en esta etapa
-- quitamos partes de cada video, haciendo ajustes finales»*. Y lo que la
-- convierte en parte del sistema y no en una lista de recados: *«importante,
-- las correcciones se van integrando para que se puedan automatizar, que sirvan
-- de entrenamiento»*.
--
-- Por eso cada nota lleva DOS cosas: `que` —sus palabras, literales, que no se
-- reescriben— y `regla`, la version general de esa nota. Una nota arregla un
-- video; una regla arregla el lote y los 16-50 que vienen. Cuando la regla ya
-- vive en codigo, el estado pasa a `automatizada` y esa nota no vuelve a
-- necesitar mano.
--
-- Y por eso hay `pasada`: *«este no pasa directo con las correcciones, pero en
-- segunda revision pasa»*. Una pieza corregida no se aprueba sola: se vuelve a
-- mirar.
CREATE TABLE IF NOT EXISTS revision (
  id          INTEGER PRIMARY KEY,
  video_slug  TEXT NOT NULL,
  pasada      INTEGER NOT NULL DEFAULT 1,
  -- En tiempo de la pieza montada, que es lo que el mira. NULL si la nota es
  -- de la pieza entera y no de un tramo.
  desde_s     REAL,
  hasta_s     REAL,
  -- **El ancla de texto, que es lo unico que sobrevive.** Los segundos son de
  -- la pieza montada, y la pieza montada cambia en cuanto se re-elige o se
  -- depura: una nota anclada a «el segundo 55» apunta a otra cosa a la
  -- siguiente corrida, y el corte cae donde no es. El texto no se mueve.
  ancla       TEXT,
  accion      TEXT NOT NULL CHECK (accion IN
                ('cortar','sonido','grafico','subtitulo','ritmo','otro')),
  que         TEXT NOT NULL,
  regla       TEXT,
  estado      TEXT NOT NULL DEFAULT 'pendiente'
                CHECK (estado IN ('pendiente','aplicada','automatizada','sube','huerfana')),
  fecha       TEXT
);

CREATE INDEX IF NOT EXISTS revision_pieza ON revision (video_slug, pasada);


-- Material que se saca de una pieza pero **no se tira**
--
-- Jaime, al aprobar que el bloque de corporaciones saliera del reel 2: *«yo
-- comparto tu opinion respecto al bloque, pero en el futuro puede servir para
-- otro video»*.
--
-- Sacar algo de una pieza es una decision sobre ESA pieza, no sobre el
-- material. Un bloque que oscurece un argumento puede ser el argumento entero
-- de otro — y en un lote de 16-50 anuncios eso pasa constantemente. Sin esta
-- tabla, lo cortado desaparece: nadie recuerda que existe, y la cinta es larga.
CREATE TABLE IF NOT EXISTS banco (
  id          INTEGER PRIMARY KEY,
  toma        TEXT NOT NULL,
  desde       REAL NOT NULL,
  hasta       REAL NOT NULL,
  texto       TEXT NOT NULL,
  -- De donde salio y por que se saco. Las dos cosas: el porque es lo que dice
  -- a un futuro montador si le sirve o le pasaria lo mismo.
  de_video    TEXT,
  por_que     TEXT,
  -- Para que podria servir, si se sabe. Vacio es honesto: no se inventa.
  para_que    TEXT,
  fecha       TEXT
);
