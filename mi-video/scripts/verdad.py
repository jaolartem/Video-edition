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
        lee=(Aguja("scripts/reels-spec.mjs", "const deLaBase = (() => {"),
             Aguja("scripts/consulta.py", 'else json.dumps(d["tablero"], ensure_ascii=False)'),),
        prohibido=(Aguja("scripts/reels-spec.mjs",
                         "const tableros = (TABLEROS[slug] ?? [])\n"),),
        copia="`TABLEROS[slug]` queda SOLO como respaldo para una pieza sin"
              " describir, y su uso se anuncia como falta.",
        costo="Cuatro entregas idénticas. La descripción de reel-01 e3 se"
              " reescribió a las 12:42 del 31 de agosto y el tablero seguía"
              " saliendo del literal: re-describir no cambiaba el vídeo.",
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
             Aguja("scripts/reels-spec.mjs", "select f.rotulo, d.condiciones from dato d"),),
        copia="La descripción puede nombrarla en prosa, pero **no puede"
              " rotular un importe que `dato` no declare**: la puerta lo para.",
        costo="Jaime cerró $14.000 —«los 300 los quité porque complica las"
              " cuentas»—; se aplicó a la descripción y no a `dato`, y al"
              " re-describir la etapa volvió el $14.300.",
    ),
    Verdad(
        decision="Que una pieza esté montada",
        vive_en="el fichero en `out/reels/`, no la etiqueta de fase",
        lee=(Aguja("scripts/avanzar.py", "def _render_caduco(pieza):"),
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
