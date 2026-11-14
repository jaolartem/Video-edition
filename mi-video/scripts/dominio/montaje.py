"""El montaje de una pieza: los tramos que quedaron, en orden y con su cinta.

**Por qué es un objeto.** Cinco preguntas distintas —la onda, la costura, lo que
se repite, los bordes sucios y cuánto del texto está afinado— abrían cada una
`ads/<slug>/edl-sell.json`, hacían su `zip(segmentos, detalle)` y se montaban su
propia caché de palabras por cinta. Cinco copias del mismo bucle, y cada copia
decidiendo por su cuenta de qué cinta sale un segmento.

Eso no es repetición estética: `fuentes` y `detalle[i].toma` **discrepan** en
cuanto un corte se parte en trozos —en reel-01 hay 22 fuentes para 21
segmentos—, así que dos copias del mismo bucle leyendo campos distintos
contestan cosas distintas sobre la misma pieza y las dos parecen correctas.

Aquí el montaje responde por sí mismo, **una vez y leyendo `detalle.toma`**, que
es la única fuente que el corte usa de verdad.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .cinta import Cinta  # noqa: E402
from .habla import Habla, colgante  # noqa: E402
from .idioma import Idioma  # noqa: E402
from .pieza import Pieza  # noqa: E402
from .tramo import Tramo, TramoInvalido  # noqa: E402

#: Por debajo de esto la palabra de antes entra pegada al corte: no hay silencio
#: en medio que separe una idea de la otra.
PEGADA = 0.20


class Montaje:
    """Lo que de verdad se montó de una pieza. Se pregunta, no se reconstruye."""

    #: Las palabras de cada cinta, una vez para todas las piezas. Son ocho
    #: cintas para siete piezas: releerlas por pieza multiplica por siete el
    #: trabajo para el mismo dato. Es el mismo motivo que `Pieza._CINTAS`.
    _PALABRAS: dict = {}

    def __init__(self, slug: str):
        self.slug = str(slug)
        self.pieza = Pieza(int(self.slug.split("-")[1]))
        self._edl = None

    # ── lo que el montaje es ────────────────────────────────────────────────
    @property
    def edl(self) -> dict:
        if self._edl is None:
            self._edl = self.pieza.edl or {}
        return self._edl

    @property
    def existe(self) -> bool:
        return bool(self.edl.get("segmentos"))

    def tramos(self) -> list:
        """Cada corte como `(Tramo, detalle)`, en orden de montaje.

        El `Tramo` nace ya sabiendo de qué cinta es —`detalle.toma`—, que es lo
        que impide que el trozo traído de otra grabación se pierda por el
        camino: con la lista pelada, quien recibía `[desde, hasta]` no tenía
        forma de saberlo y filtraba por longitud (C-151).
        """
        edl = self.edl
        fuera = []
        for rango, det in zip(edl.get("segmentos") or [],
                              edl.get("detalle") or []):
            fuera.append((Tramo.de_lista(rango, det.get("toma") or ""), det))
        return fuera

    def por_beat(self) -> dict:
        """Los tramos de cada etapa, agrupados. Una etapa son varios cortes."""
        por: dict = {}
        for t, det in self.tramos():
            por.setdefault(det.get("beat"), []).append((t, det))
        return por

    # ── lo que se oye ───────────────────────────────────────────────────────
    def palabras(self, cinta: str) -> list:
        """Las palabras de esa cinta, **pegadas al habla y con sitio**.

        Se piden a la `Cinta`, no al fichero: es ella quien sabe que ninguna
        palabra suena donde se midió silencio y que ninguna se queda sin
        tiempo. Una cinta que no se puede sostener se contesta vacía —quien
        pregunte lo verá vacío— en vez de inventar texto.
        """
        if cinta not in Montaje._PALABRAS:
            try:
                c = Cinta(cinta)
                c.exigir(cobertura=False)
                Montaje._PALABRAS[cinta] = c.palabras()
            except Exception:                      # noqa: BLE001
                Montaje._PALABRAS[cinta] = []
        return Montaje._PALABRAS[cinta]

    def habla(self, cinta: str) -> Habla:
        """El habla de esa cinta: sus palabras y lo que permiten cortar."""
        return Habla.de(cinta, self.palabras(cinta))

    def crudas(self, cinta: str) -> list:
        """Las mismas palabras en el formato del fichero, para `beats`.

        `beats` mide sobre `{"start", "end", "text"}` y aquí se habla de
        `Palabra`. Se traduce en un solo sitio —y una sola vez por cinta— en vez
        de que cada llamada se monte su propia lista: convertir novecientas
        palabras por tramo medido es el tipo de coste que no se ve.
        """
        return self.habla(cinta).dicts()

    def dentro(self, tramo: Tramo) -> list:
        """Las palabras que se oyen en ese tramo, con la vara del oído."""
        return tramo.palabras_de(self.palabras(tramo.cinta))

    def texto(self, tramo: Tramo) -> str:
        return tramo.texto_de(self.palabras(tramo.cinta))

    # ── si el texto que se va a leer es el bueno ────────────────────────────
    def afinado(self) -> dict:
        """Qué fracción del montaje de cada etapa pasó por el barrido caro.

        Jaime, sobre para qué existe ese barrido: *«la idea del barrido caro es
        que el agente de IA tenga el CC correcto, y pueda tomar decisiones sobre
        él, eliminar redundancia y componer las escenas»*. O sea que **no es un
        paso de acabado: es la entrada de los pasos de IA**. Cuatro de las seis
        piezas llegaron a montarse con el 0% afinado, y la revisión leyó «le
        que» donde la cinta dice otra cosa.

        **Se cuentan PALABRAS, no segundos.** Un tramo con medio segundo de
        silencio en el borde no llega nunca al 95% por tiempo —ahí no hay nada
        que afinar— y el paso se quedaba bloqueado pidiendo un barrido que ya
        había corrido. Lo que la comprobación quiere saber es si el texto que el
        agente va a leer es el bueno, y eso son las palabras.
        """
        rangos, por = {}, {}
        for t, det in self.tramos():
            if t.cinta not in rangos:
                try:
                    dat = Cinta(t.cinta).datos()
                    # Lo intentado sin fruto cuenta: no hay pasada mejor (C-599).
                    rangos[t.cinta] = (dat.get("afinado") or []) + (dat.get("intentado") or [])
                except Exception:                  # noqa: BLE001
                    rangos[t.cinta] = []
            af = rangos[t.cinta]
            dentro = fuera = 0
            for p in self.dentro(t):
                if any(p.empieza >= x - 0.001 and p.acaba <= y + 0.001
                       for x, y in af):
                    dentro += 1
                else:
                    fuera += 1
            d0, t0 = por.get(det.get("beat"), (0, 0))
            por[det.get("beat")] = (d0 + dentro, t0 + dentro + fuera)
        return {b: round(d / t, 3) if t else 1.0 for b, (d, t) in por.items()}

    # ── los bordes que hay que mirar ────────────────────────────────────────
    def bordes_sucios(self) -> dict:
        """Por etapa, los bordes que **hay que mirar** — sin decidir nada.

        Regla de Jaime, y corrige lo que yo estaba haciendo: *«la solución es que
        el detector apunte y tú decidas caso a caso, sin degradar el esfuerzo que
        haces; eso se logra con una revisión del guion después de correr las
        cuatro pasadas, es decir, tú compones después de que este paso se dio»*.

        Lo que se arregla solo es **aritmética** y se queda en `costuras.py`: un
        corte no puede caer dentro de una palabra, y dos trozos de la misma cinta
        no pueden pisarse. Lo que exige entender la frase —si la palabra pegada
        delante es la cabeza que falta o la cola de otra idea, si el conector del
        final sobra o le falta el objeto— **no se decide con un umbral**.

        Qué palabra deja la frase a medias lo dice `dominio.habla.colgante`, que
        es su dueño: aquí había una lista propia de 27 palabras, más corta que la
        suya, y dos listas de lo mismo son dos reglas en cuanto alguien toca una.
        """
        tramos, por = self.tramos(), {}
        for t, d in tramos:
            ws = self.palabras(t.cinta)
            if not ws:
                continue
            dentro = t.palabras_de(ws)
            antes = [p for p in ws if p.acaba <= t.desde + 0.001]
            avisos = []
            if antes and dentro and t.desde - antes[-1].acaba < PEGADA:
                # ¿Esa palabra está en la pieza? Si no, la entrada se le pega.
                suya = any(t2.cinta == t.cinta
                           and antes[-1].suena_en(t2.desde, t2.hasta)
                           for t2, _ in tramos)
                if not suya:
                    avisos.append(
                        {"donde": "entrada", "en": round(t.desde, 2),
                         "pegada_a": " ".join(p.texto for p in antes[-4:]),
                         "entra": " ".join(p.texto for p in dentro[:6])})
            if dentro and colgante(dentro[-1].texto, Idioma.de_cinta(t.cinta)):
                sigue = [p for p in ws if p.empieza >= t.hasta - 0.001][:5]
                avisos.append(
                    {"donde": "salida", "en": round(t.hasta, 2),
                     "acaba_en": " ".join(p.texto for p in dentro[-5:]),
                     "seguia": " ".join(p.texto for p in sigue)})
            if avisos:
                # **La clave es SIEMPRE texto, y se normaliza aqui.** Este
                # diccionario viaja dentro del pedido, y JSON convierte las
                # claves de un objeto en cadenas: leido en proceso llegaba con
                # enteros y leido tras pasar por el fichero, con cadenas. El
                # mismo dato con dos tipos de clave son dos datos, y quien lo
                # indexaba con el tipo que no era veia **todas las etapas
                # limpias**. Con eso se cerro en falso el ticket #17 de reel-01
                # —el beat 3 tenia el borde de 262,47— y la pieza salio con el
                # defecto y la lista diciendo que se habia atendido.
                por.setdefault(str(d.get("beat")), []).extend(avisos)
        return por

    def __str__(self) -> str:
        return f"montaje de {self.slug} ({len(self.tramos())} trozos)"


__all__ = ["Montaje", "Tramo", "TramoInvalido"]
