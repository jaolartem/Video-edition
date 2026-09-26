"""De qué minuto de la obra se saca la cama, y por qué de ése.

Jaime, oyendo reel-01 ya montada: *«la música no se escucha»*.

## El número, antes que la explicación

Medido sobre la entrega, en los silencios **reales** de la voz —no en los huecos
flojos, que era mi primera medida y estaba mal—: la música está a `-29,3 dBFS` y
la voz llega a `-11,1`. **Dieciocho decibelios** por debajo. Un lecho bajo
palabra vive entre 12 y 16; a 18, en el altavoz de un móvil, no está.

## Por qué pasa, si el nivel se fijó a mano

`musica.sh` lleva la ganancia de forma que **el pasaje más fuerte** aterrice en
`MUSI`. Esa regla existe por una razón buena y medida: con la ganancia atada a la
media, los crescendos de una sinfonía se plantaban encima de la voz.

Pero garantiza un techo, no un suelo. El primer movimiento de una sinfonía tiene
doce decibelios entre su clímax y su reposo, así que fijar el clímax en -22 deja
el resto de la pieza —que es casi toda— muy por debajo. Un solo número no puede
sujetar los dos extremos de un material que se mueve tanto.

## Qué se hace en su lugar

**Elegir el tramo, no aplastarlo.** Jaime fue explícito sobre esto: *«no agregues
efectos o máscaras al sonido, sólo baja el volumen a esas frecuencias y ya»*. Un
compresor sobre la cama resolvería la aritmética y desobedecería la instrucción,
y además le quitaría a la obra justo lo que la hace estar viva.

Una obra dura entre cinco y once minutos y la pieza necesita ochenta segundos.
Hay de sobra donde escoger: se busca el tramo cuyo nivel **se queda quieto**, y
sobre ése la misma regla del techo deja también un suelo alto. No se procesa
nada; se decide de dónde se corta.

    python scripts/cama.py public/musica/reel-01.mp3 81 "equalizer=..."
    python scripts/cama.py --nivel reel-06     # a qué LUFS entra su cama
    python scripts/cama.py --objetivo          # cuántos dB bajo la voz
    python scripts/cama.py --cola              # el silencio del final

## Y quién lee el fichero

`src/brand/cama.json` se lee **aquí y sólo aquí**. Estaba abierto a mano desde
tres sitios —dos `python -c` dentro de `musica.sh` y un número escrito a pelo en
`remezclar.py`— y por eso `objetivo_db` podía decir 16 mientras el bucle que
mezcla apuntaba a 14: la decisión vivía en el fichero y el que mezcla no la
leía. Ahora la pregunta «¿a qué nivel entra la cama?» tiene una respuesta.
"""
import json
import os
import subprocess
import sys

#: Donde vive la decisión: nivel de la cama, separación objetivo y cola.
FICHERO = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "src", "brand", "cama.json")


def leer():
    """Lo declarado en `src/brand/cama.json`."""
    with open(FICHERO, encoding="utf-8") as f:
        return json.load(f)


def nivel(slug):
    """A qué LUFS entra la cama de esa pieza: el suyo si lo tiene, o el de lote."""
    d = leer()
    return d["piezas"].get(slug, d["por_defecto"])


def cola(slug=None):
    """Cuanto silencio va al final de la pieza, en segundos.

    Lo anade `musica.sh` al mezclar y lo cuenta `version.cuadra_con_el_json`
    para no acusar de larga a una entrega que lleva dentro lo que la propia
    linea le puso. Vive aqui porque `cama.json` se lee en este fichero y en
    ninguno mas: el numero estaba dentro de una rama del CLI, o sea legible
    solo desde la linea de comandos.
    """
    # **Y la suya si la tiene.** Jaime, 16-9, sobre reel-10 acelerada: *«la
    # cola, dejala en 0.3»*. Es de la pieza y no del lote —«cada pieza tiene su
    # propia logica»—: a 1,15x los 0,6 s de lote son 0,31 s de mas sobre los 30
    # que tiene que medir, y recortar silencio es mas barato que estirar mas su
    # voz. El lote sigue en `cola_s`.
    d = leer()
    if slug and slug in (d.get("colas") or {}):
        return float(d["colas"][slug])
    return float(d.get("cola_s", 0.6))


def medido_contra(slug):
    """Contra qué objetivo se midió el nivel de esa pieza. `None` si no consta."""
    return leer().get("medido_contra", {}).get(slug)


def al_dia(slug) -> bool:
    """Si su `MUSI` responde al objetivo que rige HOY.

    **Un nivel no caduca por viejo, caduca por cambiar la pregunta.** El 15-9
    se movió `objetivo_db` de 18 a 26 y los ocho niveles guardados siguieron
    siendo números perfectamente medidos — sólo que contra otra separación. Sin
    esto, el fichero decía 26 y el audio sonaba a 18 y no había forma de verlo
    salvo volviendo a mezclar las catorce.

    Se contesta comparando, no recalculando: mover el nivel sin medirlo es
    escribir un número que dice «medido» y no lo está. C-501.
    """
    c = medido_contra(slug)
    return c is not None and abs(c - objetivo(slug)) < 0.05


def objetivo(slug=None):
    """Cuántos dB bajo la voz tiene que quedar SU cama.

    **Por pieza, igual que el nivel, y por el mismo motivo.** `por_defecto` no
    podía servir a siete obras distintas y `objetivo_db` tampoco: la separación
    que hace que una guitarra sola acompañe deja una cuerda entera encima de la
    voz. Jaime, 14-9-2026, oyendo reel-13 entregada a los 18 dB de lote:
    *«bájale un poco a la música del video, quedó muy alta»*.

    Y va aquí y no como un número suelto en quien mezcla: bajarlo sin
    declararlo lo habría deshecho `calibrar-cama.py` en la siguiente vuelta,
    que busca justamente hasta caer en el objetivo. C-500.
    """
    d = leer()
    if slug is None:
        return d["objetivo_db"]
    return d.get("objetivos", {}).get(slug, d["objetivo_db"])

#: Ventana de análisis, en segundos. Tres es lo que la norma de sonoridad llama
#: «corto plazo»: por debajo persigue notas sueltas y por encima difumina el
#: crescendo, que es justo lo que hay que ver.
VENTANA = 3.0

#: Cada cuánto se prueba un comienzo. Cinco segundos son suficientes —la
#: diferencia entre dos arranques más cercanos no llega a un decibelio— y dejan
#: la cuenta en unas decenas de candidatos en vez de miles.
PASO = 5.0

#: Lo que puede moverse el tramo elegido, de su reposo a su clímax.
#:
#: Estaba en 8 y **medido en la entrega no bastaba**: reel-05 salió con 16,4 dB
#: de recorrido y su pico 1,6 dB POR ENCIMA de la voz. Jaime, sobre las siete:
#: *«la música ya no interrumpe, pero ahora el volumen alto sobresale por encima
#: de la voz y no la acompaña»*.
#:
#: **5, que es lo que mide reel-04** —la única de la que nunca se quejó: 3,2 dB
#: de recorrido en la entrega—. Por encima de eso deja de acompañar y empieza a
#: competir, y una cama que compite no es una cama.
RANGO_MAX = 5.0

SR = 1000


def _niveles(mp3, talla, sr=SR):
    """El nivel en dB de cada ventana, de punta a punta de la obra."""
    import numpy as np

    af = (talla + ",") if talla else ""
    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", mp3, "-vn", "-af", f"{af}aresample={sr}",
         "-ac", "1", "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(crudo, dtype=np.int16).astype(float) / 32768
    n = int(sr * VENTANA)
    if len(x) < n * 4:
        return None
    m = len(x) // n * n
    r = np.sqrt((x[:m].reshape(-1, n) ** 2).mean(1)) + 1e-9
    return 20 * np.log10(r)


def donde(mp3, dura, talla=""):
    """El segundo por el que hay que empezar a cortar la cama. 0 si da igual.

    Se queda con el tramo **más alto de los que se están quietos**, y si ninguno
    se está quieto, con el que menos se mueva de los altos. Las dos mitades del
    criterio importan: sólo por quietud se elegiría un pianissimo entero, y sólo
    por altura, el clímax.
    """
    import numpy as np

    v = _niveles(mp3, talla)
    if v is None:
        return 0.0
    ancho = max(2, int(dura / VENTANA))
    if len(v) <= ancho:
        return 0.0
    salto = max(1, int(PASO / VENTANA))
    mejor, cual, ancho_elegido = None, 0.0, 0.0
    for i in range(0, len(v) - ancho + 1, salto):
        t = v[i:i + ancho]
        alto, tipico = np.percentile(t, 95), np.percentile(t, 50)
        rango = alto - tipico
        # Lo que se maximiza es el SUELO. Penalizar el rango por encima del
        # tope, en vez de descartarlo, evita quedarse sin candidatos con una
        # obra que se mueve entera —y entonces gana el que menos se mueva.
        nota = tipico - max(0.0, rango - RANGO_MAX)
        if mejor is None or nota > mejor:
            mejor, cual, ancho_elegido = nota, i * VENTANA, rango
    # **Y si ni el mejor se esta quieto, se dice.**
    #
    # Penalizar el rango sin rechazarlo evita quedarse sin candidatos, pero
    # tambien deja pasar en SILENCIO una obra que se mueve entera — y entonces
    # el pasaje elegido sigue teniendo un climax que se planta sobre la voz.
    # Jaime lo oyo en las siete: *«la musica ya no interrumpe, pero ahora el
    # volumen alto sobresale por encima de la voz y no la acompana»*.
    #
    # Medido en la entrega, la cama de reel-05 se movia **16,4 dB** y su pico
    # quedaba 1,6 dB POR ENCIMA de su voz; reel-04, la unica de la que nunca se
    # quejo, se mueve 3,2. La respuesta a una obra que no se queda quieta no es
    # bajarla mas —desaparece— sino **otra obra**, y eso lo decide el, no esto.
    if ancho_elegido > RANGO_MAX:
        print(f"cama: el tramo mas quieto de esta obra se mueve"
              f" {ancho_elegido:.1f} dB, y el tope son {RANGO_MAX:.0f}."
              f" Va a sobresalir sobre la voz: no es una cama, es una pieza.",
              file=sys.stderr)
    return round(cual, 1)


def main():
    # Las tres preguntas que el fichero contesta, para quien no es Python
    # —`musica.sh`—. Van aquí y no como otro `python -c` suelto: un `json.load`
    # escrito en la línea de órdenes es una segunda lectura del fichero, y dos
    # lecturas es como `objetivo_db` acabó diciendo una cosa y la mezcla otra.
    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        que = sys.argv[1][2:]
        if que == "nivel":
            print(nivel(sys.argv[2]))
        elif que == "objetivo":
            print(objetivo(sys.argv[2] if len(sys.argv) > 2 else None))
        elif que == "cola":
            print(cola(sys.argv[2] if len(sys.argv) > 2 else None))
        else:
            return 2
        return 0
    if len(sys.argv) < 3:
        return 2
    mp3, dura = sys.argv[1], float(sys.argv[2])
    talla = sys.argv[3] if len(sys.argv) > 3 else ""
    try:
        print(donde(mp3, dura, talla))
    except Exception:                              # noqa: BLE001
        # **Si no se puede medir, se empieza por el principio.** Es lo que se
        # hacia antes de existir esto: peor cama, pero pieza con musica.
        print(0.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
