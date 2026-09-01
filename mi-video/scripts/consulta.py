"""Las consultas que necesitan los pasos de IA, **por nombre y desde la consola**.

El paso de IA vive en JavaScript porque ahí está el `fetch`, pero la base es de
Python en todo el resto del proyecto. En vez de abrir la base desde los dos
lados —dos formas de escribir la misma tabla es de donde salen los fallos de este
proyecto— el lado JS pide por nombre y aquí está la única puerta.

    python scripts/consulta.py escenas_por_describir '[[], false]'
    python scripts/consulta.py guardar_escena @work/escena.json

**Y esto es la puerta, no la implementación.** Cada verbo de aquí está escrito en
los prompts de los contratos: su nombre y su salida son un compromiso. Lo que
contesta cada uno vive en `dominio/`, donde el sustantivo que sabe la respuesta
es su dueño — `Montaje` sabe de sus tramos, `Guion` de sus pausas, `Escena` de
quién manda sobre cada campo de una descripción. Aquí queda el nombre que el CLI
llama y la traducción a ese objeto, que es exactamente lo que hace
`transcribir.exigir` con `dominio.Cinta`.

Leer y escribir son dos oficios y compartían fichero: diez consultas para los
agentes conviviendo con las dos escrituras que aceptan lo que los agentes
contestan. Siguen entrando por la misma puerta —el CLI es uno— y ya no comparten
código.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dominio import onda as _onda  # noqa: E402
from dominio.cruce import cruces as _cruces  # noqa: E402
from dominio.encargo import por_describir as _por_describir  # noqa: E402
from dominio.escena import Escena, EscenaInvalida  # noqa: E402
from dominio.guion import Guion  # noqa: E402
from dominio.material import abanico as _abanico  # noqa: E402
from dominio.material import brolls as _brolls  # noqa: E402
from dominio.montaje import Montaje  # noqa: E402
from dominio.precio import vigente as _vigente  # noqa: E402
from dominio.repetido import repetido as _repetido  # noqa: E402


def _montado(slug):
    """El montaje de esa pieza, o `None` si todavía no hay corte que mirar."""
    m = Montaje(slug)
    return m if m.existe else None


# ── lo que se pregunta ──────────────────────────────────────────────────────
def escenas_por_describir(reels=None, rehacer=False):
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    return _por_describir(reels, rehacer)


def cc_afinado(slug):
    """Cuánto del montaje de esta pieza pasó por el barrido de cuatro pasadas."""
    m = _montado(slug)
    return m.afinado() if m else {}


def bordes_sucios(slug):
    """Los bordes que hay que mirar, por etapa. El detector apunta; no decide."""
    m = _montado(slug)
    return m.bordes_sucios() if m else {}


def cruces(slug):
    """Lo que se repite a los dos lados de una costura, sin cortarlo.

        python scripts/consulta.py cruces '["reel-01"]'
    """
    m = _montado(slug)
    return _cruces(m) if m else []


def onda(slug):
    """La curva emocional de la pieza, etapa por etapa. No decide: dibuja.

        python scripts/consulta.py onda '["reel-01"]'
    """
    m = _montado(slug)
    return _onda.curva(m) if m else []


def repetido(slug, n=3):
    """Lo que la pieza dice **dos veces**, con la entrega de cada una al lado."""
    m = _montado(slug)
    return _repetido(m, n) if m else []


def abanico(frase, cintas=None, tope=12):
    """Dónde está dicha esa frase **en todo el material**, y cómo de bien.

        python scripts/consulta.py abanico '["el 21 de septiembre"]'
    """
    return _abanico(frase, cintas, tope)


def brolls(minimo=2.0, maximo=8.0, cintas=None):
    """Los tramos donde él está en cuadro y no habla. Material de transición."""
    return _brolls(minimo, maximo, cintas)


def pausas(slug):
    """Las etapas cuyo silencio de entrada **no se recorta**: `{etapa: motivo}`."""
    return Guion(slug).pausas()


def precio_vigente(fecha=None):
    """El escalón de hoy y cómo se rotula. `None` si ya cerró todo."""
    return _vigente(fecha)


# ── lo que se escribe ───────────────────────────────────────────────────────
#
# **Un error de contenido tiene que salir por la consola como error.** El dominio
# lo dice con su propia excepción —`EscenaInvalida`, que es lo correcto para
# quien lo llama desde Python—; el CLI necesita además código de salida y
# mensaje, que es `SystemExit`. La traducción vive aquí, en el borde, y no dentro
# del objeto: un dominio que lanza `SystemExit` mata al que lo importa.
def guardar_escena(slug, orden, d):
    """Guarda la descripción de una etapa, con el texto que describe."""
    try:
        return Escena(slug, orden).guardar(d)
    except EscenaInvalida as e:
        raise SystemExit(str(e)) from e


def guardar_tablero(slug, orden, tablero):
    """Guarda SOLO el tablero de una etapa. Es la entrega del paso de diseño."""
    try:
        return Escena(slug, orden).poner_tablero(tablero)
    except EscenaInvalida as e:
        raise SystemExit(str(e)) from e


VERBOS = {"escenas_por_describir": escenas_por_describir,
          "cc_afinado": cc_afinado,
          "bordes_sucios": bordes_sucios,
          "cruces": cruces,
          "onda": onda,
          "repetido": repetido,
          "abanico": abanico,
          "brolls": brolls,
          "pausas": pausas,
          "precio_vigente": precio_vigente,
          "guardar_escena": guardar_escena,
          "guardar_tablero": guardar_tablero}


def _argumentos(argv):
    """Los argumentos del verbo. **`@fichero` en vez del JSON en la línea.**

    El argumento viaja por la consola, y la consola de Windows es cp1252 mientras
    que todo lo que se guarda aquí lleva tildes y comillas angulares. Pasar una
    descripción de escena como argumento es meter «qué pasa» por un canal que no
    sabe escribir la «é»: se rompe, o peor, entra mutilada.

    Coste medido: seis agentes de composición gastaron su turno entero peleando
    con el escapado —88 mensajes uno de ellos— y no escribieron ni una
    descripción. No era torpeza suya: era que el único camino que les di pasaba
    por ahí. Con `@`, el JSON viaja en un fichero UTF-8 y la línea lleva sólo
    ASCII — el mismo acuerdo que ya usa `work/servicio/` para los pasos de IA.
    """
    if len(argv) <= 2:
        return []
    if argv[2].startswith("@"):
        return json.load(io.open(argv[2][1:], encoding="utf-8"))
    return json.loads(argv[2])


if __name__ == "__main__":
    print(json.dumps(VERBOS[sys.argv[1]](*_argumentos(sys.argv)),
                     ensure_ascii=False))
