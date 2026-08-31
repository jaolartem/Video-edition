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
import rutas  # noqa: E402

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
CREATE TABLE IF NOT EXISTS tratamiento (
  id          INTEGER PRIMARY KEY,
  video_slug  TEXT NOT NULL,
  etapa_orden INTEGER NOT NULL,
  -- 1.0 es sin tocar. Por encima de ~1,2 se nota como prisa, no como energia.
  velocidad   REAL NOT NULL DEFAULT 1.0,
  por_que     TEXT NOT NULL,
  quien       TEXT,
  fecha       TEXT,
  UNIQUE (video_slug, etapa_orden)
);
"""

# El ciclo completo, en orden. Cada fase dice **que servicio la mueve a la
# siguiente**: la etiqueta llama al servicio, no al reves.
CICLO = [
    (1, "catalogado", "scripts/transcribir.py --barato"),
    (2, "elegido", "scripts/seleccionar.py {n} --edl"),
    # **Los tramos declarados se vuelven a poner justo despues de elegir.**
    # `seleccionar` rehace el EDL desde cero, asi que sin este paso cada pasada
    # del motor borraba las decisiones fijadas —el arranque bueno de reel-01
    # volvia a ser la toma dudada— y nadie se enteraba. Una decision que no
    # sobrevive a rehacer el paso anterior no es una decision: es un apaño.
    (2.5, "fijado", "scripts/fijar.py --aplicar {n}"),
    (3, "afinado", "scripts/transcribir.py --elegidos {n}"),
    (4, "depurado", "scripts/depurar.py {n}"),
    (5, "sin_redundancia", "scripts/redundancia.py {n}"),
    # **Y los cortes anotados se aplican.** `redundancia` no corta: anota en
    # `revision` con su ancla y su porque, que es lo correcto —el ancla
    # sobrevive a que la pieza se vuelva a montar y los segundos no—. Pero
    # ninguna fase los llevaba al EDL: se anotaban, `verificar` los contaba como
    # pendientes, y la pieza se montaba con la redundancia dentro.
    #
    # Es exactamente la queja de Jaime sobre el primer video —*«no parece que
    # hubieras revisado redundancia despues de las cuatro pasadas»*— y la
    # respuesta es que si se reviso: los cuatro cortes estaban escritos en la
    # base, en estado «pendiente», desde antes de montar.
    #
    # Va **antes** de `revalidado` a proposito. La segunda valoracion juzga
    # entrega y ritmo, y tiene que juzgarlos sobre la pieza sin lo que sobra;
    # ademas las notas se estampan con la huella del montaje en que se
    # apuntaron, asi que si el corte cambia primero, las notas quedan huerfanas.
    (5.2, "recortado", "scripts/revision.py --aplicar {n}"),
    (5.5, "revalidado", None),       # servicio de IA con decision acotada
    (6, "cosido", "scripts/costuras.py {n}"),

    # **Y un ultimo repaso de redundancia, con la pieza ya cosida.** Jaime:

    # *«revisemos si otra pasada extra de redundancia al final antes de

    # renderizar vale la pena — siempre»*. La de la fase 5 juzga el corte de

    # entonces, y entre medias `fijar`, `revalidado` y `cosido` lo rehacen:

    # medido en una tarde, la misma repeticion volvio tres veces. Va aqui

    # porque es el ultimo punto donde el texto ya esta cerrado y cortar

    # todavia no obliga a rehacer descripciones ni recortes.

    (6.5, "repasado", None),
    (7, "descrito", "scripts/describir.mjs {n}"),
    # **La composicion son dos pasos, no uno con dos sombreros.** Regla de
    # Jaime: *«un agente se dedica a planear y verificar y otro agente a
    # disenar»*, *«son dos tareas diferentes»*, *«uno define lo que va a haber y
    # el otro lo monta»*, *«una cadena de produccion agentica»*.
    #
    # `descrito` define QUE va a haber —que etapas componen y que tiene que
    # quedar dicho en cada una, que se ve mirando el argumento entero— y ademas
    # **escribe el contrato del siguiente**: *«el contrato del segundo lo crea el
    # primero»*. Este monta: forma, copy y familia.
    #
    # Va antes de `cortado` porque montar sobre un corte que todavia puede
    # moverse es pagarlo dos veces, y despues de `descrito` porque sin encargo no
    # hay nada que disenar.
    (7.5, "disenado", None),         # servicio de IA: el diseno grafico
    (8, "cortado", "scripts/cortar.py {n}"),
    (10, "verificado", "scripts/verificar.py {n}"),
    (11, "montado", "scripts/montar.sh {n}"),
    # **Nivelar y medir el sonido son pasos de la linea, no algo que yo haga
    # despues.** Regla de Jaime, y viene de verme hacerlo a mano: *«integra todo
    # al contrato, no debe ser por fuera del pipeline para la proxima»*.
    #
    # Los dos existian como scripts sueltos —`sonoridad.sh` desde hace dias,
    # `suena.py` desde hoy— y **no los llamaba nadie**, que en este proyecto
    # significa que no existen: los seis salian a −10 LUFS con pico +0,1 dBTP y
    # la tabla `medicion` llevaba seis tipos declarados y cero filas.
    #
    # Van ANTES de `revisado` a proposito: el criterio humano es el escalon mas
    # caro, y gastarlo en una pieza a un nivel que la plataforma va a cambiar es
    # pedirle que juzgue algo que no es lo que se publica.
    #
    # Nivelar **no es «audio adicional»** —eso son la musica y los efectos, que
    # siguen fuera hasta que apruebe—: es dejar la pieza donde las plataformas
    # normalizan, para que el nivel sea una decision del montaje y no de donde
    # se publique.
    (11.2, "nivelado", "scripts/sonoridad.sh {n}"),
    # Y medir como suena, que es lo unico que tengo en lugar de oido. Jaime:
    # *«no se escucha con subtitulos, el sonido no es escrito»*.
    (11.4, "medido", "scripts/suena.py {n} --guardar"),
    # **El criterio humano es el escalon mas caro, y por eso va aqui.** Jaime:
    # *«lo mas caro es criterio humano, por eso es el paso anterior a la
    # aprobacion»*. Mirar una pieza montada cuesta su tiempo y su atencion, asi
    # que se hace **una vez** y sobre algo que ya paso todos los filtros baratos.
    # **El diseñador revisa lo que salió, y es su segundo momento.** Jaime:
    # *«que lo revise el diseñador como paso final»*, *«asegurate de que las
    # piezas del renderizado sean revisadas por el ultimo agente y que todo
    # este en el pipline»*.
    #
    # Va DESPUES de nivelar y medir, y ANTES de que la mire el: el criterio
    # humano es el escalon mas caro del embudo, y gastarlo en una pieza con un
    # silencio de seis segundos es tirarlo. Todos los pasos anteriores juzgan lo
    # que se va a montar; este es el unico que mira lo que salio.
    (11.6, "visto", None),
    (12, "revisado", None),          # el mira y anota; lo mueve el
    (13, "aprobado", None),          # lo mueve Jaime, no un servicio
    # **La voz virgen sale DESPUES de aprobar, no antes.** Regla de Jaime:
    # *«o mejor despues de aprovacion dame un audio con mi voz y solo mi voz
    # virgen»*.
    #
    # Estaba en la fase 9, antes de montar, y eso es trabajo tirado en cuanto la
    # revision mueve un corte: el audio exportado deja de corresponder a la
    # pieza, y encima habria pasado por Adobe Podcast —que es manual y en
    # minutos suyos— para nada. Es la misma cuenta que le hizo quitar la musica
    # de las piezas sin aprobar: *«sera mas facil con el audio final y
    # definitivo, menos retrabajo»*.
    #
    # Aqui el corte ya lo cerro el, asi que lo que se exporta es lo que va a
    # sonar en la entrega.
    (13.5, "voz_entregada", "scripts/voz-limpia.py --exportar {n}"),
    (14, "voz_limpia", "scripts/voz-limpia.py {n}"),
    (15, "masterizado", "scripts/musica.sh {n}"),
    (16, "publicado", "scripts/publicar.py --finales {n}"),
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
    cf = {r[1] for r in con.execute("pragma table_info(corte_fijo)")}
    if cf and "toma" not in cf:
        mal.append("«corte_fijo» solo sabe de apertura y cierre: no hay donde"
                   " declarar el tramo de una etapa, y sin eso la composicion"
                   " no se puede aplicar por la linea")
    if "precio" not in hay:
        mal.append("falta la tabla «precio» — el precio vuelve a ser una cadena"
                   " literal, y una cadena no caduca (C-28)")
    for t in ("fuente", "dato"):
        if t not in hay:
            mal.append(f"falta la tabla «{t}» — una cifra en pantalla no tiene"
                       f" donde declarar de donde sale, y eso es cumplimiento")
    if "medicion" not in hay:
        mal.append("falta «medicion»: lo que se mide de cada render no se guarda"
                   " en ningun sitio, asi que no se puede comparar entre tandas")
    sin_usar = [t for t in VOCABULARIOS if t in hay and not con.execute(
        f"select count(*) from {t}").fetchone()[0]]
    if sin_usar:
        mal.append(f"vocabularios vacios: {sin_usar}")
    con.close()
    return mal


# La escalera que fijo Jaime el 29 de agosto de 2026, corrida para arrancar hoy.
# El Early Bird se conserva como fila pasada: es el ancla.
ESCALERA = [
    (10, None, "2026-08-28", 1, "Early Bird — fila pasada, ancla"),
    (20, "2026-08-29", "2026-09-04", 0, None),
    (30, "2026-09-05", "2026-09-11", 0, None),
    (40, "2026-09-12", "2026-09-21T11:30", 0, "cierra con el evento"),
]


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


def migrar():
    con = _con()
    cols = {r[1] for r in con.execute("pragma table_info(fase)")}
    alter = ""
    if "servicio" not in cols:
        alter += "ALTER TABLE fase ADD COLUMN servicio TEXT;"
    con.executescript(NUEVAS.replace("ALTER_FASE_SERVICIO;", alter))
    _corte_fijo_etapa(con)
    for importe, desde, hasta, ancla, nota in ESCALERA:
        con.execute("insert into precio (importe, desde, hasta, ancla, nota)"
                    " values (?,?,?,?,?) on conflict(importe, hasta) do update"
                    " set desde=excluded.desde, ancla=excluded.ancla,"
                    " nota=excluded.nota",
                    (importe, desde, hasta, ancla, nota))
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
        for n in rutas.piezas():
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
