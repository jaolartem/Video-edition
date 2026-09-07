"""**El canto de papel**: como se rasga una silueta para que no parezca tijera.

Aprobado por Jaime el 6-9-2026 sobre reel-02 e2, despues de seis vueltas de
mirar. La receta esta escrita en `docs/canon.md`, en *«El panel con el dentro»*,
y aqui esta en codigo — que es la unica forma de que no se pierda:

- **Ruido de grano grueso sobre la distancia al borde.** El canto se desplaza en
  pixeles reales, no en una fraccion, asi que el desgarro mide lo mismo tenga el
  sujeto el tamano que tenga.
- **Una orla clara de fibra por fuera, de grosor variable.** Sin la orla no se
  lee como papel; con grosor constante se lee como contorno dibujado.
- **Solo la mancha grande.** Lo suelto que la segmentacion arrastra —la silla, el
  cable— es *«el fondo de las imagenes apareciendo»*, que Jaime prohibio por su
  nombre.
- **Mediana, no desenfoque.** Su pregunta lo zanjo: *«¿la trama de la camisa es
  un problema mayor a que se pierda expresividad y comunicacion no verbal?»*. El
  gaussiano borra la trama y los rasgos por igual; la mediana respeta los cantos.

## La trampa, y cuesta un render entero

**La semilla del ruido es constante en todos los fotogramas.** El rasgado se
calcula por fotograma desde la mascara de ESE fotograma —una mascara fija
recortaria en cuanto el sujeto se mueve— pero el campo de ruido es siempre el
mismo. Con semilla por fotograma el canto hierve y deja de leerse como papel:
se lee como ruido de video.

## Lo que NO hace

No escalona. Los doce escalones de gris van por fotograma dentro de Remotion
(`src/components/Recorte.tsx`), que es donde vive el sistema visual y donde el
tratamiento —blanco y negro, color o sepia— se decide por etapa. Aqui solo se
produce el recorte con su canto.
"""
import numpy as np

#: **La semilla, y es constante a proposito.** Ver arriba: con una semilla por
#: fotograma el canto hierve. No se toca sin mirar el resultado en movimiento.
SEMILLA = 20260906
#: Grano GRUESO, en pixeles de correlacion. Con grano fino el canto se lee como
#: ruido digital; el papel rompe en trozos, no en pixeles.
#:
#: **Y son dos escalas, no una.** Con una sola el canto sale ondulado —una curva
#: suave, que es un recorte mal hecho, no un desgarro—: el papel rompe a lo
#: grande Y se deshilacha a lo pequeno al mismo tiempo. `FINO` es la segunda.
GRANO = 7
FINO = 4.0
#: Cuanto mueve el ruido el canto, en pixeles: la profundidad del desgarro y la
#: del deshilachado. La segunda es menor porque es fibra, no rotura.
MORDIDA = 5.0
MORDIDA_FINA = 1.6
#: Grosor medio de la orla de fibra, en pixeles. Varia con el segundo campo, y
#: mucho: con grosor constante se lee como contorno dibujado.
ORLA = 5.5
#: El claro de la fibra: `lightNeutral` de `src/brand/paleta.ts`. No es blanco —
#: el blanco puro no esta en la paleta y canta sobre las placas.
CLARO = np.array([233.0, 234.0, 236.0], dtype=np.float32)
#: La mascara vale a partir de aqui. Numero calibrado por Jaime mirando.
UMBRAL = 0.62
#: Pasos de contraccion. Dos: el borde crudo arrastra un halo del fondo.
CONTRAE = 2
#: Cuanto baja la franja de la cabeza desde la coronilla, en fraccion del alto.
#: 0,15 sobre 1920 son 288 px: el pelo, la cara y el arranque de los hombros —
#: exactamente por donde le pasa el bloque. Ver `cabeza`.
CABEZA = 0.15
#: Los percentiles del tramo util, **dentro de la mascara**. Del 5 al 95: por
#: debajo estan las sombras de la habitacion y por encima los brillos, y ninguno
#: dice nada de la cara.
BAJO, ALTO = 5, 95


def granos(alto, ancho):
    """Los campos de ruido, generados UNA vez y con semilla fija.

    Vuelve `(mordida, fibra)`: la primera en pixeles ya —lleva sus dos escalas
    dentro, la rotura grande y el deshilachado— y la segunda normalizada a 0-1,
    que es la que engorda y adelgaza la orla. Se reutilizan en todos los
    fotogramas de la pasada: ahi esta la diferencia entre un canto de papel y un
    canto que hierve.
    """
    from scipy.ndimage import gaussian_filter

    rng = np.random.default_rng(SEMILLA)

    def campo(sigma):
        """Ruido centrado en 0 y con desviacion 1, a la escala que se pida."""
        g = gaussian_filter(rng.standard_normal((alto, ancho)), sigma)
        return (g / max(float(g.std()), 1e-6)).astype(np.float32)

    mordida = campo(GRANO) * MORDIDA + campo(FINO) * MORDIDA_FINA
    fibra = campo(GRANO * 2.4)
    fibra = (fibra - fibra.min()) / max(float(fibra.max() - fibra.min()), 1e-6)
    return mordida, fibra


def nucleo(m):
    """La mancha grande de la mascara: cerrada, contraida y sin lo suelto."""
    from scipy import ndimage

    b = ndimage.binary_closing(m >= UMBRAL, np.ones((5, 5), bool))
    b = ndimage.binary_erosion(b, np.ones((3, 3), bool), iterations=CONTRAE)
    etiquetas, cuantas = ndimage.label(b)
    if cuantas <= 1:
        return b
    tam = ndimage.sum(b, etiquetas, range(1, cuantas + 1))
    return etiquetas == int(np.argmax(tam)) + 1


def limpiar(dentro, radio=1.1):
    """El canto SIN papel: la mancha grande y nada mas.

    **Es el canto del gancho, y la diferencia no es de gusto.** El recorte del
    gancho se compone sobre EL MISMO PLANO del que salio, asi que la orla clara
    de fibra —que en un collage dice «esto es papel»— aqui dibuja una silueta
    blanca alrededor de el sobre su propia foto: se lee como pegatina recortada
    con tijera, que es lo contrario de lo que buscaba. En el panel el recorte
    aterriza sobre una placa, y ahi la fibra si tiene contra que leerse.

    Lo unico que se hace es suavizar el escalonado del pixel: `nucleo` ya viene
    binarizada al 0,62, cerrada, contraida dos pasos y sin lo suelto. El
    remapeo devuelve un canto de ~1 px en vez de la rampa ancha que dejaria un
    gaussiano solo — una rampa ancha ES el halo que esto viene a quitar.
    """
    from scipy.ndimage import gaussian_filter

    g = gaussian_filter(dentro.astype(np.float32), radio)
    return np.clip((g - 0.35) / 0.30, 0.0, 1.0)


def coronilla(dentro):
    """La fila mas alta con sujeto, en fraccion del alto. `None` si no hay.

    Es lo que el gancho necesita para colocar el rotulo: el texto va DETRAS de
    su cabeza, asi que donde acaba el bloque lo decide donde empieza su pelo, y
    eso cambia de pieza a pieza. Se mide aqui porque aqui esta la mascara —
    medirlo otra vez en otro sitio seria una segunda copia de un dato que ya
    existe, y las segundas copias divergen.
    """
    filas = np.flatnonzero(dentro.any(axis=1))
    return float(filas[0]) / dentro.shape[0] if filas.size else None


def cabeza(dentro):
    """Que columnas ocupa su CABEZA, en fracciones del ancho. `None` si no hay.

    Es la otra mitad de lo que el gancho necesita para colocar el bloque, y sale
    de la misma mascara que `coronilla` por el mismo motivo: medirlo en otro
    sitio seria una segunda copia. Jaime, sobre la variedad del gancho: *«el lado
    y la altura los decide DONDE ESTA EL; el texto ocupa el hueco que deja su
    cuerpo. Si esta a la derecha del cuadro, el bloque va a la izquierda»*. Sin
    este numero el lado se elige por gusto, que es lo que dejo las siete laminas
    con el mismo bloque en la misma esquina.

    **Se mira desde su coronilla hacia abajo, no el cuadro entero.** El centroide
    de la silueta completa lo mandan las piernas y el sillon: medido sobre las
    siete sale entre 0,44 y 0,52 en todas, o sea no distingue nada. La cabeza y
    los hombros si, y ademas es la franja correcta: es por ahi por donde el
    bloque le pasa por detras.
    """
    filas = np.flatnonzero(dentro.any(axis=1))
    if not filas.size:
        return None
    banda = dentro[filas[0]:filas[0] + int(dentro.shape[0] * CABEZA)]
    cols = np.flatnonzero(banda.any(axis=0))
    if not cols.size:
        return None
    ancho = dentro.shape[1]
    return float(cols[0]) / ancho, float(cols[-1]) / ancho


def rasgar(dentro, mordida, fibra):
    """El canto: `(alfa, orla)` a partir de la mascara de ESTE fotograma.

    `alfa` es la silueta con el canto mordido y `orla` la fibra clara que va por
    fuera. Se calculan sobre la distancia con signo al borde —positiva dentro,
    negativa fuera— para que el ruido desplace el canto en pixeles reales.
    """
    from scipy.ndimage import distance_transform_edt as edt

    canto = (edt(dentro) - edt(~dentro)).astype(np.float32) + mordida
    alfa = np.clip(canto + 0.5, 0.0, 1.0)
    grosor = np.maximum(ORLA * (0.25 + 1.6 * fibra), 1e-6)
    orla = np.clip(1.0 + canto / grosor, 0.0, 1.0) * (canto < 0)
    return alfa, orla


def rango(frame, dentro):
    """El tramo util del plano **dentro de la mascara**, en 0-255.

    Se mide una vez por pasada y se reutiliza: la camara es fija y la exposicion
    no cambia dentro de una etapa, asi que medirlo por fotograma solo anadiria
    parpadeo — los doce escalones se moverian de sitio con cada gesto suyo.
    """
    gris = frame @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    v = gris[dentro]
    if v.size < 1000:
        return 0.0, 255.0
    a, b = np.percentile(v, [BAJO, ALTO])
    return float(a), float(max(b, a + 1.0))


def estirar(frame, tramo):
    """Lleva ese tramo a 0-255. **Los doce escalones los pone Remotion encima.**

    Sin esto, en una habitacion en penumbra el sujeto entero cae en los tres
    escalones de abajo y sale como una mancha negra sobre la masa negra — que es
    exactamente lo que se vio en el primer fotograma del render. La receta del
    canon dice *«doce escalones por percentiles del 5 al 95 dentro de la
    mascara»*, y el estirado es esa mitad: un filtro SVG no mira el histograma,
    asi que va aqui, que es donde la mascara existe.
    """
    a, b = tramo
    return np.clip((frame - a) * (255.0 / (b - a)), 0.0, 255.0)


def sobre_papel(frame, alfa, orla):
    """El fotograma recortado: color del plano dentro, fibra clara en el canto."""
    a = np.clip(alfa + orla, 0.0, 1.0)
    peso = (orla / np.maximum(a, 1e-6))[:, :, None]
    return np.dstack([frame * (1 - peso) + CLARO * peso, a * 255.0])


def mediana(frame):
    """Mediana de 5 sobre el plano. **No desenfoque**: respeta los cantos.

    Va aqui y no en Remotion porque un filtro SVG no sabe hacer una mediana, y
    porque es lo que deja la trama de la camisa tranquila sin comerse los rasgos
    — que es la pregunta que Jaime hizo y que decidio esto.
    """
    import cv2

    return cv2.medianBlur(frame.astype(np.uint8), 5).astype(np.float32)
