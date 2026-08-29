"""Las carpetas del proyecto, en un solo sitio. Version Python de `rutas.mjs`.

Misma precedencia: `--origen` / `--destino` en la linea de comandos, luego
`VIDEO_ORIGEN` / `VIDEO_DESTINO` del entorno, y al final `rutas.json`. Asi una
tanda concreta se redirige sin tocar el fichero.
"""
import json
import os
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
    if not os.path.isdir(ORIGEN):
        return sorted(set(TOMAS.values()))
    hay = sorted(f[:-4] for f in os.listdir(ORIGEN)
                 if f.lower().endswith(".mp4"))
    # Lo declarado que no este en disco se conserva: puede estar pendiente de
    # copiar y el resto del camino ya lo sabe pedir.
    return sorted(set(hay) | set(TOMAS.values()))


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
