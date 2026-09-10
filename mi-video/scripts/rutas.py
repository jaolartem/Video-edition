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
#: Donde se dejan las voces para limpiar y de donde se recogen. Va en F:
#: porque es la memoria de trabajo; G: guarda solo lo final. `RECOGER`
#: incluye ademas las carpetas donde el pueda haber dejado algo ya.
LIMPIAR = _barras(_cfg.get("limpiar", "F:/Edicion de video/Audio para limpiar"))
RECOGER = [LIMPIAR, "out/audio-puro",
           "G:/My Drive/Creación de videos/Audio para limpiar"]
PUBLICO = _cfg.get("publico", "public")
FUENTES = _cfg.get("fuentes", {})
TOMAS = _cfg.get("tomas", {})
# `AAAAMMDD_HHMMSS`: lo que la camara pone y lo que un derivado no tiene.
_ES_CINTA = re.compile(r"^\d{8}_\d{6}$")


#: Donde instala Git for Windows su `bash.exe`. No es adivinar: son las dos
#: rutas del instalador oficial, y se miran solo si el PATH no lo trae.
BASH = ("C:/Program Files/Git/bin/bash.exe",
        "C:/Program Files (x86)/Git/bin/bash.exe")


def interprete():
    """Con que se corre un `.sh`. **Se resuelve, no se hereda.**

    `servicios/base.py` anteponia el literal `"bash"` y `planificador` hacia
    `which("bash")`: los dos dependen del PATH de la ventana desde la que
    alguien arranca la linea. Desde Git Bash va y desde PowerShell no.

    Medido el 9-9-2026: `masterizado` de reel-01 murio con `FileNotFoundError
    [WinError 2]` y la pieza se quedo en `voz_limpia`. Un paso del ciclo no
    puede depender de con que consola se llamo, y si de verdad no hay
    interprete se dice con su nombre en vez de reventar con un errno.
    """
    import shutil

    return (shutil.which("bash") or shutil.which("sh")
            or next((x for x in BASH if os.path.exists(x)), None)
            or _sin_interprete())


def _sin_interprete():
    raise SystemExit(
        "no hay con que correr un .sh: `bash` no esta en el PATH ni en "
        + " ni en ".join(BASH)
        + ". Instala Git for Windows o anade su carpeta `bin` al PATH.")


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
        for f in os.listdir(ORIGEN):
            # Un `.mp4` suelto es una grabacion de un angulo; una CARPETA con
            # nombre de cinta es una grabacion de varios. Las dos cuentan igual:
            # si solo se miraran los ficheros, la primera grabacion a dos
            # camaras no existiria para el corpus y sus frases no podrian ser
            # candidatas de nada. Es C-74 por la puerta de la carpeta.
            if f.lower().endswith(".mp4"):
                huellas.add(f[:-4])
            elif os.path.isdir(os.path.join(ORIGEN, f)):
                huellas.add(f)
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


#: Lo que se admite dentro de una carpeta de grabacion. Un `.wav` suelto no es
#: un angulo: es audio, y ya tiene su sitio en `work/audio`.
_ANGULO = (".mp4", ".mov", ".mkv")


def angulos(toma):
    """Los VIDEOS que componen una grabacion, en orden. Uno solo si es plana.

    Jaime, al ver que dos camaras a la vez ya casi se podian montar: *«para eso,
    de aca en adelante subo cada video grabado de esta forma en una carpeta con
    los videos que lo componen»*.

    Asi que una grabacion deja de ser **un fichero** y pasa a ser **una carpeta
    con angulos dentro**. Las dos formas conviven a proposito: las siete cintas
    de agosto son ficheros planos y siguen siendo grabaciones de un angulo, que
    es lo que son. Nada de lo que ya funciona tiene que enterarse.

    El orden es alfabetico y no es un detalle: **el primero es el principal**, y
    de el sale todo lo que hoy pide «la cinta» —transcripcion, cortes, audio—.
    Con nombres de camara (`A`, `B`, `cam1`, `cam2`) sale solo; si hace falta
    otro, se renombra el fichero, que es mas barato que declararlo en un mapa
    que luego se desvia del disco.
    """
    d = os.path.join(ORIGEN, toma)
    if not os.path.isdir(d):
        plano = f"{ORIGEN}/{toma}.mp4"
        return [plano] if os.path.exists(plano) else []
    return [_barras(os.path.join(d, f)) for f in sorted(os.listdir(d))
            if f.lower().endswith(_ANGULO)]


def cinta(toma):
    """El video principal de una grabacion, sea fichero suelto o carpeta.

    Todo lo que hasta hoy escribia `f"{ORIGEN}/{toma}.mp4"` pregunta aqui. Es la
    unica linea que tiene que saber que una grabacion puede tener mas de un
    angulo — el resto del sistema sigue viendo una cinta.
    """
    a = angulos(toma)
    if not a:
        raise SystemExit(f"no encuentro la grabacion {toma} en {ORIGEN}"
                         f" (ni {toma}.mp4 ni carpeta {toma}/)")
    return a[0]


def bruto(reel):
    """Ruta del bruto de un reel, resuelta contra ORIGEN."""
    toma = TOMAS.get(reel)
    if not toma:
        raise SystemExit(f"sin toma declarada para {reel} en rutas.json")
    return cinta(toma)


def salida(*partes):
    """Ruta de salida dentro de DESTINO, creando la carpeta si hace falta."""
    p = os.path.join(DESTINO, *partes)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return _barras(p)
