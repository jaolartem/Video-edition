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
"""
import subprocess
import sys

#: Ventana de análisis, en segundos. Tres es lo que la norma de sonoridad llama
#: «corto plazo»: por debajo persigue notas sueltas y por encima difumina el
#: crescendo, que es justo lo que hay que ver.
VENTANA = 3.0

#: Cada cuánto se prueba un comienzo. Cinco segundos son suficientes —la
#: diferencia entre dos arranques más cercanos no llega a un decibelio— y dejan
#: la cuenta en unas decenas de candidatos en vez de miles.
PASO = 5.0

#: Lo que puede moverse el tramo elegido, de su reposo a su clímax. Ocho
#: decibelios: por debajo de eso ya no hay obra clásica que valga —el Poco
#: allegretto de Brahms entero se mueve 11,8— y por encima vuelve el problema
#: que esto viene a resolver.
RANGO_MAX = 8.0

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
    mejor, cual = None, 0.0
    for i in range(0, len(v) - ancho + 1, salto):
        t = v[i:i + ancho]
        alto, tipico = np.percentile(t, 95), np.percentile(t, 50)
        rango = alto - tipico
        # Lo que se maximiza es el SUELO. Penalizar el rango por encima del
        # tope, en vez de descartarlo, evita quedarse sin candidatos con una
        # obra que se mueve entera —y entonces gana el que menos se mueva.
        nota = tipico - max(0.0, rango - RANGO_MAX)
        if mejor is None or nota > mejor:
            mejor, cual = nota, i * VENTANA
    return round(cual, 1)


def main():
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
