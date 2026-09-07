"""La fuente de verdad de cada decisión, declarada y comprobada.

Regla de Jaime, después de recibir cuatro veces la misma pieza: *«deja clara en
código la fuente de verdad»*. Y el diagnóstico que la motiva, suyo también:
*«la decisión de componer está escuchando las indicaciones viejas»*, *«se
persiste después de dos refactorizaciones mayores: el problema no son las
instrucciones»*.

## Qué problema resuelve este fichero

Cada decisión de una pieza puede existir en dos representaciones: la que se
corrige y la que se monta. Cuando no son la misma, corregir es apuntar a una de
dos copias y acertar por suerte — y el sistema **no falla al corregir, falla al
entregar, y calla**. Se pagó cinco veces en un día: el tablero, la cifra, el
libreto, el nivel de sonido y el hecho mismo de estar montada.

Escribirlo en `docs/correcciones.md` no basta: un documento no impide que la
próxima reescritura vuelva a leer la copia. Aquí cada decisión declara

- **dónde vive** — el único sitio donde se corrige,
- **quién la lee** — con la línea literal que lo demuestra,
- **qué está prohibido** — la línea que, si vuelve a existir, significa que
  alguien volvió a leer la segunda copia.

Es el mismo mecanismo de aguja de `docs/correcciones.md`, y por la misma razón:
un fichero se reescribe entero y sigue existiendo; la línea que hace el trabajo,
no.

    python scripts/verdad.py            # la tabla, y falla si algo no cuadra

Corre en `montar.sh` junto a `guardas.mjs`: es barato —lee ficheros— y va
delante por eso mismo.
"""
import dataclasses
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclasses.dataclass(frozen=True)
class Aguja:
    """Una línea literal que tiene que existir (o no existir) en un fichero."""

    fichero: str
    linea: str

    def esta(self) -> bool:
        try:
            with open(os.path.join(RAIZ, self.fichero), encoding="utf-8") as f:
                return self.linea in f.read()
        except OSError:
            return False

    def __str__(self):
        return f"`{self.fichero}` :: `{self.linea}`"


@dataclasses.dataclass(frozen=True)
class Verdad:
    """Una decisión, su único sitio, quién la lee y qué no puede volver."""

    decision: str
    vive_en: str
    #: La línea que demuestra que el que monta lee la fuente buena.
    lee: tuple[Aguja, ...]
    #: Líneas que NO pueden existir: son el consumidor leyendo la otra copia.
    prohibido: tuple[Aguja, ...] = ()
    #: La otra representación, si sigue existiendo y para qué sirve ahora.
    copia: str = ""
    #: Qué pasó cuando no había una sola fuente. Es el coste, con su fecha.
    costo: str = ""


VERDADES = (
    Verdad(
        decision="Cuándo es el evento",
        vive_en="el último escalón de la tabla `precio` — su `hasta` es el"
                " cierre, con la nota «cierra con el evento»",
        lee=(Aguja("scripts/dominio/precio.py", "def evento(fecha=None):"),),
        prohibido=(Aguja("scripts/reels/cta.mjs", 'fecha: "21 de septiembre",'),),
        copia="`src/muestras.ts` la lleva escrita, pero es un fixture del"
              " catálogo de formas: no entra en ninguna pieza.",
        costo="Jaime: *«simplifica las fuentes, sólo queremos una fuente de"
              " verdad»*. El día vivía a mano en `cta.mjs` y como hecho en la"
              " tabla, y la escalera se movió DOS VECES en una tarde. Seis de"
              " los siete diseñadores escribieron además la fecha en sus props"
              " —dos de ellos corrigiendo una vencida— porque nada decía de"
              " dónde sale. Derivarla da además el año, que sin él la pieza"
              " caduca el 22 de septiembre al reutilizarse.",
    ),
    Verdad(
        decision="Qué placas de fondo existen, qué dibuja cada una y cuál va en"
                 " cada pieza",
        vive_en="`ads/fondos.json`",
        lee=(Aguja("scripts/servicios/caja.py", "def placas_que_existen(slug"),
             Aguja("scripts/reels/material.mjs", "const PIEZAS = JSON.parse"),
             Aguja("scripts/reels/fondo.mjs", "export function faltasDeFondo("),),
        prohibido=(),
        copia="Las tablas `placa` y `placa_etapa` son una IMPORTACIÓN del JSON"
              " que hace `db.py` y **no las lee nadie**: 14 filas y una por"
              " etapa que se regeneran solas y no alimentan ningún paso."
              " Redundancia del modelo, sin consumidor.",
        costo="Las catorce placas llevaban semanas en el repositorio, con su"
              " `dice` y su `siente` escritos, y el pedido del diseñador no las"
              " mandaba: iban las 26 láminas del canon, que son para mirar, y"
              " no las placas, que son las que se pueden usar. Se pidieron"
              " treinta y cinco formas nuevas por código teniendo"
              " `r1-mecanismo` —«un canal que lleva bloques hacia el punto de"
              " fuga y una derivación que se los lleva fuera del cuadro»—"
              " esperando. Jaime: *«no es reinventar la rueda, es seguir la"
              " identidad gráfica»*. Y el mapa era **por beat**, así que cada"
              " tablero pedía la suya: R6 salió con cuatro placas, R2 y R5 con"
              " tres, y sólo R7 con una. *«Es un FONDO de tablero por reel»* —"
              " la asignación es de pieza y `fondo.mjs` para la que pinte dos.",
    ),
    Verdad(
        decision="El libreto de una pieza",
        vive_en="tabla `libreto` de `ads/decisiones.db`",
        lee=(Aguja("scripts/beats.py", "Los beats de la pieza, **desde la base**"),),
        prohibido=(Aguja("scripts/beats.py", "libro = open(LIBRETOS"),),
        copia="`docs/libretos.md` es documento para leer. Si hay que"
              " regenerarlo, se genera DESDE la base, nunca al revés.",
        costo="El parser del markdown saltaba los párrafos de menos de 40"
              " caracteres y se comió la etapa de registro de la séptima"
              " —«Le dejo el link abajo.», 22 caracteres—, que es la que pide"
              " la acción. Ocho filas en la base y el paso decía «sin libreto».",
    ),
    Verdad(
        decision="El contenido de un tablero",
        vive_en="`escena_desc.tablero`, escrito por quien compone",
        lee=(Aguja("scripts/reels/base.mjs", "export function tablerosDe(slug) {"),
             Aguja("scripts/dominio/escena.py", "NO_SE_BORRAN"),),
        prohibido=(Aguja("scripts/reels-spec.mjs",
                         "const tableros = (TABLEROS[slug] ?? [])\n"),),
        copia="`TABLEROS[slug]` queda SOLO como respaldo para una pieza sin"
              " describir, y su uso se anuncia como falta.",
        costo="Cuatro entregas idénticas. La descripción de reel-01 e3 se"
              " reescribió a las 12:42 del 31 de agosto y el tablero seguía"
              " saliendo del literal: re-describir no cambiaba el vídeo.",
    ),
    Verdad(
        decision="Cuánto separa la música de la voz",
        vive_en="`src/brand/cama.json` — `por_defecto` es el nivel al que entra"
                " la cama y `objetivo_db` la separación que ese nivel produce",
        lee=(Aguja("scripts/cama.py", "def nivel(slug):"),
             Aguja("scripts/musica.sh", "python scripts/cama.py --nivel"),
             Aguja("scripts/remezclar.py",
                   'OBJETIVO = float(cama.leer()["objetivo_db"])'),),
        prohibido=(Aguja("scripts/remezclar.py", "OBJETIVO = 14.0"),
                   Aguja("scripts/musica.sh",
                         "json.load(open('src/brand/cama.json'"),),
        copia="Ninguna. El mapa `piezas` está vacío a propósito: los siete"
              " números por pieza se midieron sobre mezclas apiladas y se"
              " tiraron (C-233). Si una obra vuelve a necesitar el suyo, se"
              " anota ahí con su motivo.",
        costo="`cama.json` declaraba `objetivo_db: 16` y **no lo leía nadie**:"
              " `remezclar.py` llevaba 14 escrito a mano y `musica.sh` abría el"
              " JSON con dos `python -c` propios. Corregir la separación en el"
              " único sitio que el fichero anuncia como suyo no cambiaba la"
              " mezcla — dos decibelios que existían sólo en el documento. Es"
              " la avería del tablero (C-142) en el paso de audio: la decisión"
              " escrita en un sitio y aplicada desde otro.",
    ),
    Verdad(
        decision="Cómo suena la voz en el remate de una etapa",
        vive_en="`escena_desc.voz`, escrito por el que monta",
        lee=(Aguja("scripts/dominio/remate.py",
                   "select etapa_orden, voz from escena_desc"),
             Aguja("scripts/musica.sh",
                   "VOZ=$(python scripts/dominio/remate.py"),),
        prohibido=(),
        copia="Ninguna, y no cabe una segunda: la ventana se deriva de"
              " `src/reels.json` —lo que el render dibujó— y el trato sale de"
              " `remate.TRATOS`, que es el mismo catálogo que viaja en el pedido"
              " y el que se aplica en la mezcla.",
        costo="Todavía ninguno, y es a propósito: la decisión nace con una sola"
              " fuente. La avería que se evita es la conocida —lo declarado en"
              " un sitio y aplicado desde otro, que es como el tablero pudo"
              " salir cuatro veces igual (C-142)—. Aquí el paso de audio le"
              " pregunta a la misma columna que el diseñador escribe, y sin"
              " declaración contesta `anull`.",
    ),
    Verdad(
        decision="El nivel de un efecto de sonido",
        vive_en="el propio `.wav`, medido por `scripts/sfx.sh` al generarlo",
        lee=(Aguja("src/brand/sfx.ts", "import picos from"),
             Aguja("scripts/sfx.sh", "sfx-picos.json"),),
        prohibido=(Aguja("src/brand/sfx.ts",
                         "const PICO_DEL_FICHERO: Record<Motion, number> = {"),),
        copia="Ninguna. `src/brand/sfx-picos.json` lo escribe el generador y"
              " no se edita a mano.",
        costo="El clic del tablero quedaba en −32 dBFS, veinte decibelios bajo"
              " la voz: audible como nada. Al regenerar los efectos los picos"
              " cambiaron 15 dB y la tabla escrita a mano siguió igual.",
    ),
    Verdad(
        decision="Una cifra que sale en pantalla",
        vive_en="tabla `dato`, con su fuente y su condición",
        lee=(Aguja("scripts/verificar.py", "y ninguna fila de"),
             Aguja("scripts/reels/cifras.mjs", "select f.rotulo, d.condiciones, d.cifra, d.respalda from dato d"),),
        copia="La descripción puede nombrarla en prosa, pero **no puede"
              " rotular un importe que `dato` no declare**: la puerta lo para.",
        costo="Jaime cerró $14.000 —«los 300 los quité porque complica las"
              " cuentas»—; se aplicó a la descripción y no a `dato`, y al"
              " re-describir la etapa volvió el $14.300.",
    ),
    Verdad(
        decision="La franja reservada al subtítulo",
        vive_en="`src/brand/franja.json`, derivada de la zona segura",
        lee=(Aguja("src/brand/franja.ts", 'import franjaJson from "./franja.json"'),
             Aguja("scripts/franja.mjs", 'leer("src/brand/franja.json")'),
             Aguja("src/components/ZonaTablero.tsx", "bottom: franja.reserva"),
             Aguja("src/components/CaptionDiscreta.tsx", "bottom: franja.desdeAbajo"),
             Aguja("scripts/describir.mjs", "criterioDeFranja()"),),
        prohibido=(Aguja("src/components/CausalChain.tsx",
                         "paddingBottom: layout.safe.bottom + layout.captionBand"),
                   Aguja("src/components/TwoPaths.tsx",
                         "paddingBottom: layout.safe.bottom + layout.captionBand"),
                   Aguja("src/components/HookTitle.tsx",
                         "paddingBottom: layout.safe.bottom + layout.captionBand"),
                   Aguja("src/components/Comparacion.tsx", "top: CC + layout.captionBand"),
                   Aguja("src/components/Acumulacion.tsx", "top: 1452"),),
        copia="Ninguna. `tokens.ts` sigue declarando la zona segura de Meta"
              " (`bottom: 672`) y la banda (`captionBand: 200`), que es de donde"
              " sale el 65% y el 10,4166%; la franja no se recalcula en cada"
              " componente.",
        costo="Los seis tableros del lote la invadían: `Comparacion` ponía el"
              " remate en 1390 y el pie en 1570, `Acumulacion` un panel hasta"
              " 1390 y su condición en 1452 — todo por debajo del 65%, o sea"
              " bajo la interfaz de la plataforma. La regla estaba escrita en"
              " dos componentes y los otros dos no la miraban.",
    ),
    Verdad(
        decision="Cuándo dos textos dicen lo mismo",
        vive_en="`scripts/dominio/texto.py` — `comparable` para buscar un ancla,"
                " `palabras` para contar, `contenido` para medir de qué habla y"
                " `apodo` para nombrar un fichero",
        lee=(Aguja("scripts/dominio/texto.py", "def _sin_tildes(t: str) -> str:"),
             Aguja("scripts/dominio/texto.py", "def apodo(t: str) -> str:"),
             Aguja("scripts/subtitular.py", "from dominio.texto import comparable as _comparable"),
             Aguja("scripts/redundancia.py", "from dominio.texto import _sin_tildes"),
             Aguja("scripts/trato.py", "from dominio.texto import _sin_tildes as _limpio"),
             Aguja("scripts/cortar.py", "from dominio.texto import apodo"),),
        copia="Ninguna en la línea. Quedan dos en `find-start.py` y"
              " `pick-takes.py`, que no los llama nadie, y una distinta a"
              " propósito en `repeticiones.py`, que tira los dígitos — ver el"
              " costo.",
        costo="Doce normalizaciones de texto en doce ficheros y **ninguna igual a"
              " otra**, contadas el 7-9-2026. Tres eran `apodo` copiado palabra"
              " por palabra; dos, `_sin_tildes` copiado igual. Y una decide"
              " distinto: `repeticiones.py` parte con `[a-z]+` y se come los"
              " dígitos, así que no ve repetida una cifra — y es el paso que"
              " decide qué se corta por repetirse.",
    ),
    Verdad(
        decision="Cuándo un tramo es lectura",
        vive_en="`scripts/trato.py`, con la medida de `seleccionar.py :: literal()`",
        lee=(Aguja("scripts/trato.py", "LEIDA = 0.60"),
             Aguja("scripts/lectura.mjs", "export const LEIDA = 0.60;"),
             Aguja("scripts/seleccionar.py", "def literal(v, parrafo, n=4):"),),
        copia="`reading-detect.py` mide la altura de la cabeza y **no decide**:"
              " la hipótesis no se sostuvo (rango intercuartílico 0,016) y el"
              " disparador es el audio, no el frame.",
        costo="El umbral vivía sólo en `trato.py` y el que compone no lo veía:"
              " cinco tramos leídos salieron en cámara limpia, uno al 97% de"
              " secuencia literal.",
    ),
    Verdad(
        decision="Con qué fondo se dibuja el subtítulo",
        vive_en="`src/brand/cc.json` los umbrales y"
                " `work/scenes/<slug>/trasfondo.json` la medida de cada escena",
        lee=(Aguja("src/brand/cc.ts", 'import ccJson from "./cc.json"'),
             Aguja("scripts/reels/cc.mjs", 'readFileSync("src/brand/cc.json"'),
             Aguja("scripts/dominio/trasfondo.py", '"cc.json"'),
             Aguja("scripts/reels/material.mjs", "export const trasfondoDe = (slug) => {"),),
        prohibido=(Aguja("src/components/captionBand/Plana.tsx",
                         "backgroundColor: color.richBlack"),),
        copia="Ninguna. El componente no elige: recibe `trato` y pinta lo que"
              " `pintaDelCc` diga. Y el negativo no es un color elegido — es"
              " `difference`, que lo calcula contra lo de debajo.",
        costo="El cuadro negro era el tratamiento único en las 142 escenas del"
              " lote, escrito a pelo dentro de `Plana`: la zona de pantalla que"
              " más tiempo está ocupada, resuelta sin componer (C-274).",
    ),
    Verdad(
        decision="Que una pieza esté montada",
        vive_en="el fichero en `out/reels/`, no la etiqueta de fase",
        lee=(Aguja("scripts/dominio/fase.py", "def _render_caduco(pieza):"),
             Aguja("scripts/avanzar.py", "caduco = _render_caduco(pieza)"),),
        copia="`video_fase` sigue siendo el camino, pero la etiqueta se"
              " comprueba contra el artefacto y contra su fecha.",
        costo="Dos veces el mismo día: la fase decía `montado` y el mp4 era de"
              " siete horas antes.",
    ),
)


def revisar():
    """Devuelve la lista de motivos por los que la verdad no es única."""
    mal = []
    for v in VERDADES:
        for a in v.lee:
            if not a.esta():
                mal.append(
                    f"«{v.decision}» dice leerse de {v.vive_en} y {a} ya no"
                    f" está. O el mecanismo se perdió, o cambió de nombre.")
        for a in v.prohibido:
            if a.esta():
                mal.append(
                    f"«{v.decision}»: volvió a existir {a}. Eso es el que monta"
                    f" leyendo la segunda copia — la fuente es {v.vive_en}.")
    return mal


def main():
    ancho = max(len(v.decision) for v in VERDADES)
    for v in VERDADES:
        print(f"  {v.decision.ljust(ancho)}  ->  {v.vive_en}")
    mal = revisar()
    if mal:
        print(f"\nLA VERDAD NO ES UNICA — {len(mal)} motivo(s):")
        for m in mal:
            print(f"  · {m}")
        raise SystemExit(1)
    print(f"\nverdad: {len(VERDADES)} decisiones, una fuente cada una.")


if __name__ == "__main__":
    sys.exit(main() or 0)
