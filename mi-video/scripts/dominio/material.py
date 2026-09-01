"""Todo lo grabado, mirado como corpus: dónde se dice algo y dónde no se habla.

Dos preguntas que sólo se pueden contestar sobre **todas** las cintas a la vez, y
por eso no son de la pieza:

- **¿Dónde está dicha esta frase?** Regla de Jaime, y ensancha el abanico:
  *«usualmente se repite más de dos veces… incluso a veces se repite en otro
  video»*. La mejor toma de una frase **no tiene por qué estar en la cinta de esa
  pieza**. Ya pasó y se resolvió a mano: el «virtual» que le faltaba al reel 1
  estaba en la cinta del reel 2.
- **¿Dónde sale en cuadro y callado?** *«Otra forma de hacer transiciones es
  hacer B-rolls con pedazos del video donde yo salgo en silencio, leyendo o
  haciendo algo… dar espacio intencional a dos secciones diferentes, o dar el
  espacio para pensar cuando algo importante se dijo»*. No hace falta grabar nada
  nuevo: hay 149 huecos de dos segundos o más en las siete cintas.

**Y las dos preguntan por `Cinta`, no por el fichero.** Leían `segmentos` del
JSON en crudo, así que veían las palabras tal y como las estampó el modelo:
estiradas sobre el silencio y a veces sin duración. Para el abanico eso mueve los
segundos que devuelve; para los B-rolls es peor —una palabra estirada **tapa el
hueco entero**— y además esquiva el sello, o sea que un transcript de una sola
pasada contestaba como si fuera bueno.
"""
from __future__ import annotations

import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from . import vocabulario as _voc  # noqa: E402
from .cinta import Cinta  # noqa: E402

#: Un B-roll más largo que esto deja de ser transición y se vuelve una pausa.
BROLL_MAX = 8.0
#: Lo que se deja a cada lado del hueco para no morder la palabra vecina.
AIRE_BORDE = 0.15


def cintas(nombres=None) -> list:
    """Las cintas sobre las que se puede buscar: las que tienen transcript.

    Se **descubren** mirando la carpeta, no se declaran. `rutas.TOMAS` mapea reel
    a cinta y lo escribe una persona; sobre ese mapa incompleto se contestó «esa
    frase no está en ninguna cinta» y se mandaron etapas a tablero (C-74).
    """
    if nombres:
        return [Cinta(str(c)) for c in nombres]
    return [Cinta(os.path.splitext(os.path.basename(r))[0])
            for r in sorted(glob.glob("work/transcripts/*.json"))]


def _palabras(c: Cinta) -> list:
    """Las palabras de la cinta, o ninguna si no se puede sostener."""
    try:
        c.exigir(cobertura=False)
        return c.palabras()
    except Exception:                              # noqa: BLE001
        return []


def abanico(frase: str, nombres=None, tope: int = 12) -> list:
    """Cada aparición de esa frase, **ordenada de mejor a peor entrega**.

    Devuelve la cinta, sus segundos, lo que se oye alrededor y su intensidad —la
    entrega, sin signo—. No decide: da material para decidir.
    """
    buscada = _voc.palabras(frase)
    if not buscada:
        return []
    fuera = []
    for c in cintas(nombres):
        pal = [(w, p) for p in _palabras(c) for w in _voc.palabras(p.texto)]
        for i in range(len(pal) - len(buscada) + 1):
            if [w for w, _ in pal[i:i + len(buscada)]] != buscada:
                continue
            trozo = pal[i:i + len(buscada)]
            contexto = " ".join(
                p.texto for _, p in pal[max(0, i - 6):i + len(buscada) + 6])
            fuera.append({"toma": c.nombre,
                          "desde": round(trozo[0][1].empieza, 2),
                          "hasta": round(trozo[-1][1].acaba, 2),
                          "contexto": contexto, "intensidad": None})
    # La entrega sólo de las que hay, y con tope: medir es lo caro.
    try:
        import beats

        for x in fuera[:tope]:
            m = beats.intensidad(x["toma"], x["desde"], x["hasta"]) or {}
            if m.get("intensidad") is not None:
                x["intensidad"] = round(float(m["intensidad"]), 2)
    except Exception:                              # noqa: BLE001
        pass
    return sorted(fuera, key=lambda x: -(x["intensidad"] or -1))


def brolls(minimo: float = 2.0, maximo: float = BROLL_MAX, nombres=None) -> list:
    """Los tramos donde él está en cuadro y **no habla**. Material de transición.

    Dos usos, y los dos son de ritmo, no de relleno: **entre dos secciones**,
    para que no se pisen, y **después de algo importante**, para dejarlo caer. Un
    B-roll que no hace ninguna de las dos cosas es tiempo muerto, y esta pieza
    vive de que no sobre nada.
    """
    fuera = []
    for c in cintas(nombres):
        ws = _palabras(c)
        for a, b in zip(ws, ws[1:]):
            hueco = b.empieza - a.acaba
            if hueco < minimo:
                continue
            fuera.append({"toma": c.nombre,
                          "desde": round(a.acaba + AIRE_BORDE, 2),
                          "hasta": round(min(b.empieza - AIRE_BORDE,
                                             a.acaba + maximo), 2),
                          "dura": round(min(hueco, maximo) - 2 * AIRE_BORDE, 2),
                          "antes": a.texto, "despues": b.texto})
    return sorted(fuera, key=lambda x: -x["dura"])
