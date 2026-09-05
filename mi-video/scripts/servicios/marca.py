"""Lo que el REPOSITORIO le dice al diseñador sobre la marca.

Cuatro lectores y un solo trabajo: abrir un fichero del proyecto y ponerlo en el
pedido. La paleta y los topes de `src/brand/`, los efectos que existen de
verdad, y las 26 láminas de `docs/ejemplos/` con su anatomía.

**Ninguno de los cuatro decide nada**, y por eso viven juntos y aparte del
servicio: un hex citado de memoria es un hex que se desvía, un sonido descrito
con palabras —«un roce grave y arrastrado»— es una capa que se monta muda, y un
tope recordado es un render que muere a mitad. Lo que va al diseñador sale del
disco cada vez.

Salió de `disenar.py` cuando ese fichero pasó del techo de 300: leer el
repositorio y orquestar el paso son dos cosas, y la primera no cambia nunca
mientras la segunda cambia cada semana.
"""
import json
import os

#: La carpeta `mi-video`. Tres `dirname`: este fichero cuelga de
#: `scripts/servicios/`, igual que `caja.py`.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sonidos():
    """Los efectos que EXISTEN, con lo que hace cada uno.

    El pedido no los llevaba, asi que quien componia describia el sonido con
    sus palabras —«un roce grave y arrastrado cuando el bloque gris se mete
    debajo de la segunda barra»— y sonaba el que casara por casualidad, o
    ninguno. Jaime pide que los efectos sean coherentes; para eso hay que saber
    contra que se elige.

    Se leen de `escena.mjs`, que es donde vive la lista que el render honra. Una
    segunda copia aqui seria una lista que se desvia el dia que alguien anada
    un efecto.
    """
    import json
    import subprocess

    try:
        salida = subprocess.run(
            ["node", "-e",
             "import('./scripts/escena.mjs').then(m=>console.log("
             "JSON.stringify([...m.SUENAN])))"],
            capture_output=True, text=True, cwd=RAIZ, check=True).stdout
        nombres = json.loads(salida.strip())
    except Exception:                              # noqa: BLE001
        return {"error": "no se pudo leer el catalogo de sonidos"}
    QUE_HACE = {
        "mark": "clic seco: un marcador que aparece",
        "draw": "trazo corto y continuo: una linea que se dibuja",
        "fork": "algo que se separa en dos",
        "land": "golpe seco: algo que aterriza o se detiene",
        "type": "tecleo: texto que se escribe letra a letra",
        "whoosh": "barrido: algo que cruza el cuadro",
        "glitch": "distorsion breve: la senal que se rompe",
    }
    return {"disponibles": {n: QUE_HACE.get(n, "") for n in nombres},
            "la_regla": "El sonido sigue al MOVIMIENTO: si algo entra, cruza"
                         " o se rompe, suena; si nada se mueve, no.",
            "como_declararlo": "Usa el nombre exacto de la lista. Describir el"
                                " sonido con tus palabras deja la capa muda."}


def _laminas():
    """Las 26 laminas y su anatomia. **La autoridad visual, no un adjunto.**

    Jaime: *«al contrato del disenador le falto el contexto de la imagen de marca
    y de lo que hacemos en terminos graficos; no vio los ejemplos, que estan
    dentro de la documentacion o deben estar»*. Estaban — en `docs/ejemplos/` —
    y el pedido no los mencionaba, asi que quien componia trabajaba con una
    paleta y una lista de prohibiciones. De ahi sale el minimalismo corporativo
    que el rechazo: *«estamos lejos de ese estilo… buscamos neoconstructivista,
    el nieto millennial o alfa del constructivismo ruso»*.

    Viaja el LEEME entero —que describe la anatomia de las 26— y las RUTAS de
    los PNG, para que quien contesta pueda abrirlos. Un canon citado de memoria
    es un canon que se desvia; uno que no viaja es uno que no existe.
    """
    import glob

    raiz = os.path.join(os.path.dirname(RAIZ), "docs", "ejemplos")
    try:
        leeme = open(os.path.join(raiz, "LEEME.md"), encoding="utf-8").read()
    except OSError:
        return {"error": "no se pudo leer docs/ejemplos/LEEME.md"}
    pngs = sorted(glob.glob(os.path.join(raiz, "*", "*.png")))
    if not pngs:
        return {"error": "docs/ejemplos/ no tiene laminas: el canon no llega"}
    return {"anatomia": leeme,
            "laminas": [q.replace(chr(92), "/") for q in pngs],
            "como_usarlas": "Abrelas. Son la autoridad visual y no hay otra:"
                            " si lo que compones no se parece a estas, esta mal"
                            " aunque cumpla la paleta."}


def _canon():
    """La paleta y las prohibiciones, del repositorio y no de memoria.

    Se leen los tokens de verdad: un canon citado de memoria es un canon que se
    desvía sin que nadie lo note, y aquí el color es lo que dice dónde mirar.
    """
    # **Se leen todos los ficheros de marca, no uno.** Esto miraba sólo
    # `tokens.ts`, y el día que la paleta se mudó a `paleta.ts` empezó a
    # devolver **cero colores en silencio** — un `{}` que el prompt del
    # diseñador recibe como «no hay canon» sin que nada falle. Es el fallo que
    # el propio docstring de arriba dice que no puede pasar, cometido por una
    # ruta escrita a mano.
    #
    # Leer la carpeta entera no es un parche más ancho: es que el canon **es**
    # `src/brand/`, no un fichero concreto de dentro. Que mañana se parta otra
    # vez no vuelve a romper esto.
    import glob
    import re

    t = ""
    for f in sorted(glob.glob(os.path.join(RAIZ, "src", "brand", "*.ts"))):
        try:
            t += open(f, encoding="utf-8").read() + "\n"
        except OSError:
            continue
    if not t:
        return {"error": "no se pudo leer src/brand/"}
    colores = dict(re.findall(r"(\w+):\s*\"(#[0-9a-fA-F]{3,8})\"", t))
    # Y si no sale ni un color, **se dice**: un canon vacío no es un canon.
    if not colores:
        return {"error": "src/brand/ no declara ningun color: el canon no llega"}
    return {
        "colores": colores,
        "tipografia": {
            "titulares y cifras": "Anton, versales",
            "texto sobre video": "Montserrat 700-900",
            "datos y cabeceras": "JetBrains Mono, versales, tracking amplio",
            "prohibida": "cualquier serif: se emborrona con la compresion",
        },
        "prohibido": [
            "sombras, degradados suaves, backdrop-filter, esquinas Material",
            "rebote, confeti, wiggle, Easing.back",
            "ilustracion amable: blobs, dibujitos, iconografia redondeada",
            "fotografia de familia sonriente de stock",
            "el oro decorando: si hay tres cosas en oro, dos sobran",
        ],
        "familias": {
            "cargada": "fotomontaje a sangre, punto de fuga, geometria rota;"
                       " para el golpe y el concepto",
            "tranquila": "negro o navy liso, geometria plana a escuadra;"
                         " para las cifras que hay que leer",
        },
    }


def _topes():
    """Los topes de texto, que **fallan el render** en vez de avisar."""
    ruta = os.path.join(RAIZ, "src", "brand", "copy.ts")
    try:
        t = open(ruta, encoding="utf-8").read()
    except OSError:
        return {"error": "no se pudo leer src/brand/copy.ts"}
    import re

    return {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d{2,3})\b", t)}
