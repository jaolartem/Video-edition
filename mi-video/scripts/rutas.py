"""Las carpetas del proyecto, en un solo sitio. Version Python de `rutas.mjs`.

Misma precedencia: `--origen` / `--destino` en la linea de comandos, luego
`VIDEO_ORIGEN` / `VIDEO_DESTINO` del entorno, y al final `rutas.json`. Asi una
tanda concreta se redirige sin tocar el fichero.
"""
import json
import os
import re
import sys

_cfg = json.load(open("rutas.json", encoding="utf-8"))


def _de_arg(nombre):
    bandera = f"--{nombre}"
    if bandera in sys.argv:
        i = sys.argv.index(bandera)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def _barras(p):
    return p.replace("\\", "/").rstrip("/")


ORIGEN = _barras(_de_arg("origen") or os.environ.get("VIDEO_ORIGEN")
                 or _cfg["origen"])
DESTINO = _barras(_de_arg("destino") or os.environ.get("VIDEO_DESTINO")
                  or _cfg["destino"])
# Todo lo temporal, NUNCA en C:. Ver la nota en rutas.json.
TEMPORAL = _barras(_de_arg("tmp") or os.environ.get("VIDEO_TMP")
                   or _cfg.get("temporal", "tmp"))
os.makedirs(TEMPORAL, exist_ok=True)
TRABAJO = _cfg.get("trabajo", "work")
PUBLICO = _cfg.get("publico", "public")
FUENTES = _cfg.get("fuentes", {})
TOMAS = _cfg.get("tomas", {})
# `AAAAMMDD_HHMMSS`: lo que la camara pone y lo que un derivado no tiene.
_ES_CINTA = re.compile(r"^\d{8}_\d{6}$")


def material():
    """**Todas las cintas que hay**, no las que alguien apunto en el mapa.

    `TOMAS` mapea reel -> cinta y lo escribe una persona. Eso hace falta —el
    montaje necesita saber que cinta alimenta que pieza— pero **no puede ser la
    definicion del corpus**: una cinta que nadie apunta no existe para el
    sistema, y el sistema contesta preguntas sobre el corpus.

    Ya paso dos veces en el mismo dia. `20260825_231011` estaba en local, con su
    audio y sus silencios hechos, y sin transcribir (C-74); y `20260814_142032`
    estaba en la carpeta del rodaje en Drive y ni siquiera se habia copiado. Las
    dos son grabaciones enteras. Sobre ese corpus incompleto se contesto «esa
    frase no esta en ninguna cinta» y se mandaron etapas a tablero.

    Asi que el corpus se **descubre**, mirando la carpeta. Lo que este en
    `ORIGEN` es material, tenga libreto o no, este en el mapa o no.
    """
    # **Una cinta existe si ha dejado CUALQUIER rastro**, no solo si su mp4 esta
    # en esta carpeta. Jaime, fijando el criterio: *«el corpus es abierto a
    # todo; la idea es hacer un video reciclado en el futuro sin grabar nada»*.
    #
    # Mirando solo `ORIGEN/*.mp4` se quedaban fuera dos grabaciones enteras del
    # 14 de agosto —`20260814_140257` y `20260814_141115`— que tenian su audio
    # extraido aqui mismo y cuyo bruto no se habia copiado de Drive. O sea que
    # el material estaba a medio camino y para el sistema no existia: sus frases
    # no podian ser candidatas de nada y la busqueda contestaba «eso no esta
    # grabado» sin haberlas mirado. Es C-74 una vez mas, y la tercera vez que el
    # mismo error cuesta material.
    #
    # Y la forma del nombre es lo que separa una cinta de un derivado: un proxy
    # (`p151758_300`) o un recorte (`..._full`, `..._deep`) tienen audio y no
    # son grabaciones. Se pide `AAAAMMDD_HHMMSS` y no hace falta lista negra.
    huellas = set(TOMAS.values())
    if os.path.isdir(ORIGEN):
        huellas |= {f[:-4] for f in os.listdir(ORIGEN)
                    if f.lower().endswith(".mp4")}
    for sub, ext in (("transcripts", ".json"), ("cuts", ".json"),
                     ("audio", ".wav")):
        d = os.path.join(TRABAJO, sub)
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if f.lower().endswith(ext):
                huellas.add(f[: -len(ext)].replace("_full", "").replace("_deep", ""))
    return sorted(t for t in huellas if _ES_CINTA.match(t))


def piezas():
    """**Cuantas piezas hay**, preguntandolo, no contandolo de memoria.

    Diecisiete sitios del proyecto llevaban escrito `[1, 2, 3, 4, 5, 6]` o
    `range(1, 7)`. Mientras el lote fueron seis eso funcionaba y era invisible;
    en cuanto aparecio la septima —la cinta del 14 de agosto, 160 s de una sola
    toma— la consecuencia no fue un error, fue **silencio**: `donde.py` decia
    donde esta cada pieza y contestaba por seis, `avanzar.py` movia seis, y la
    septima no aparecia como pendiente en ningun sitio porque para el sistema no
    existia. Jaime lo dijo en dos palabras: *«son 7»*.

    Es exactamente lo mismo que `material()` para las cintas (C-74): un numero
    que alguien escribio deja de ser cierto y nadie se entera, porque lo que
    falta no se puede echar de menos.

    Se pregunta a la base, que es quien sabe cuantas piezas hay declaradas. Si
    la base no contesta, se cae al lote historico para no dejar la linea muerta.
    """
    import sqlite3
    import basedatos

    try:
        con = basedatos.abrir("ads/decisiones.db")
        ns = [int(r[0][-2:]) for r in con.execute(
            "select slug from video where slug like 'reel-%' order by slug")]
        con.close()
        return ns or [1, 2, 3, 4, 5, 6]
    except Exception:                              # noqa: BLE001
        return [1, 2, 3, 4, 5, 6]


def temporal(*partes):
    """Carpeta temporal propia, creada si hace falta. Nunca en C:."""
    p = os.path.join(TEMPORAL, *partes)
    os.makedirs(p, exist_ok=True)
    return _barras(p)


def bruto(reel):
    """Ruta del bruto de un reel, resuelta contra ORIGEN."""
    toma = TOMAS.get(reel)
    if not toma:
        raise SystemExit(f"sin toma declarada para {reel} en rutas.json")
    return f"{ORIGEN}/{toma}.mp4"


def salida(*partes):
    """Ruta de salida dentro de DESTINO, creando la carpeta si hace falta."""
    p = os.path.join(DESTINO, *partes)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return _barras(p)
