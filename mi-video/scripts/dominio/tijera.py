"""Lo único que cambia un montaje ya hecho, y lo deja consistente.

**Por qué es un objeto.** Nueve pasos de `costuras.py` abrían
`ads/<slug>/edl-sell.json`, movían un número y lo volvían a escribir, cada uno
con su copia del mismo bucle. Y las copias no eran iguales — nunca lo son:

- **Dos no recalculaban `duracion_s`.** Medido hoy sobre las siete piezas, la
  duración declarada miente en seis: reel-02 dice 113,62 s y sus trozos suman
  84,77 (−28,8 s), reel-06 dice 82,0 y suma 93,9 (+11,9). Es el campo por el que
  se pregunta cuánto dura una pieza sin abrirla.
- **Seis movían el segmento y dejaban el `detalle` donde estaba**, aunque cada
  fila lleva su propio `start` y `end`. En reel-01 hay 9 de 21 trozos con los
  dos números diciendo cosas distintas del mismo corte. Dos copias de la misma
  verdad, y las dos parecen correctas — que es exactamente lo que `verdad.py`
  existe para impedir.

Aquí el corte se mueve por un solo sitio, y ese sitio se encarga de que lo demás
cuadre. `Montaje` contesta lo que el montaje es; la tijera es lo que lo cambia.
"""
from __future__ import annotations

import json

from .montaje import Montaje
from .tramo import Tramo


class DecisionMovida(Exception):
    """Un paso quiso reescribir un trozo declarado. Se para el paso.

    No es un aviso: es la única forma de que un paso NUEVO no repita el fallo
    sin que nadie lo note. `mover` y `quitar` pueden negarse en silencio porque
    negarse deja el corte como estaba; `rehacer` no, porque reescribe la lista
    entera y ahí «no hacer nada» no existe.
    """


class Tijera:
    """El montaje de `slug`, abierto para cambiarlo.

    Nada se escribe hasta `guardar()`, y `guardar()` no hace nada si no se movió
    nada: un paso que corre en seco no puede tocar el fichero por descuido.

    ## Y lo declarado no se mueve, lo pida quien lo pida

    C-161 puso esa pregunta —`fijado(i)`— dentro de un paso, `pasada_callada`.
    Duró lo que tardó en aparecer el siguiente paso que mueve algo: `colas`
    devolvía un borde declarado **1,533 s** tarde en 60 tramos del lote, `mudos`
    borraba dos tramos declarados enteros —uno de ellos la cola del CTA de
    reel-05— y `sin_eco` recortaba colas declaradas incluso corriendo en seco.

    Poner el `if` en los cinco sitios sólo aplaza el sexto. Se pone **aquí**,
    que es por donde pasan todos: un montaje sólo cambia por `mover`, `ajustar`,
    `quitar` y `rehacer`, y las cuatro preguntan quién puso ese trozo ahí. Un
    paso que no se acuerde de preguntar tampoco puede saltárselo.

    La única puerta que un trozo declarado deja abierta es `ajustar`, y no la
    abre la confianza: la abre la huella. Ver ahí por qué.
    """

    __slots__ = ("m", "_sucio", "respetados")

    def __init__(self, slug):
        self.m = Montaje(slug)
        self._sucio = False
        #: Los trozos declarados que algún paso quiso tocar y no pudo. Vacío es
        #: lo normal; que no lo esté significa que un paso empujó contra una
        #: decisión declarada, y eso se dice al guardar.
        self.respetados = set()

    # ── lo que hay ──────────────────────────────────────────────────────────
    @property
    def slug(self) -> str:
        return self.m.slug

    @property
    def existe(self) -> bool:
        return self.m.existe

    def __len__(self) -> int:
        return len(self.m.edl.get("segmentos") or [])

    def tramo(self, i: int) -> Tramo:
        return Tramo.de_lista(self.m.edl["segmentos"][i],
                              self.m.edl["detalle"][i].get("toma") or "")

    def detalle(self, i: int) -> dict:
        return self.m.edl["detalle"][i]

    def beat(self, i: int):
        return self.detalle(i).get("beat")

    def fijado(self, i: int) -> bool:
        return bool(self.detalle(i).get("fijado"))

    # ── lo que se puede cambiar ─────────────────────────────────────────────
    def mover(self, i: int, nuevo: Tramo) -> bool:
        """El trozo `i` pasa a ser `nuevo`. **Y su detalle se mueve con él.**

        Devuelve si de verdad se movió, y un trozo declarado devuelve `False`:
        los pasos cuentan por el retorno, así que negarse no infla el contador
        que decide si el cosido converge.
        """
        if self.fijado(i):
            self.respetados.add(i)
            return False
        return self._escribir(i, nuevo)

    def ajustar(self, i: int, nuevo: Tramo) -> bool:
        """Cuadra el trozo `i` **sin cambiar lo que dice**. Vale en lo declarado.

        Una declaración dice *qué trozo de qué cinta* entra en la etapa —«éste, y
        no el que elija la selección»—; no dice en qué milésima de qué sílaba cae
        la tijera. Sacar un corte de dentro de una palabra no cambia esa
        decisión: la ejecuta bien. Sin este camino no había forma de hacerlo, y
        por eso `reel-03` llegó a Jaime con tres entradas a mitad de palabra y
        **catorce de sus dieciséis trozos** intocables — con las declaraciones ya
        borradas de la tabla, además, así que la marca protegía a nadie.

        **Y el permiso no se promete: se comprueba.** Vale mientras la huella del
        texto —lo que suena dentro, C-149— sea la misma antes y después. Si el
        ajuste añade o quita una palabra ya no es cuadrar el corte, es cambiar la
        etapa, y ahí manda la declaración: se respeta y se cuenta.
        """
        if not self.fijado(i):
            return self.mover(i, nuevo)
        ws = self.m.palabras(self.tramo(i).cinta)
        if not ws or self.tramo(i).huella_de(ws) != nuevo.huella_de(ws):
            self.respetados.add(i)
            return False
        return self._escribir(i, nuevo)

    def _escribir(self, i: int, nuevo: Tramo) -> bool:
        viejo = self.tramo(i)
        if abs(nuevo.desde - viejo.desde) < 1e-9 and abs(nuevo.hasta - viejo.hasta) < 1e-9:
            return False
        self.m.edl["segmentos"][i] = [nuevo.desde, nuevo.hasta]
        self.m.edl["detalle"][i] = {**self.detalle(i),
                                    "start": nuevo.desde, "end": nuevo.hasta}
        self._sucio = True
        return True

    def quitar(self, indices) -> int:
        """Fuera esos trozos, con su detalle. **Salvo los declarados.**

        `mover` ya se negaba a tocar un trozo fijado; `quitar` no preguntaba, y
        por ahi se perdio entero. El 9-9-2026 reel-03 se entrego sin el adelanto
        de los tiquets #276, #277 y #279: el cosido veia que [340,711-342,191]
        de la etapa 1 se pisaba con [340,251-342,32] de la etapa 4 —la misma
        cinta y los mismos segundos— y lo daba por audio repetido.

        **Y lo era, a proposito.** La decision de Jaime es que esa frase suene
        dos veces: de adelanto arriba y en su sitio del cuerpo. `sin_solapes`
        esta hecha para el solape que nadie quiso —«la convocatoria entera
        sonando dos veces»—, y ahi sigue valiendo; lo que no puede es disolver
        una decision porque se parece a un accidente.

        Un declarado se queda y se dice; el contador cuenta lo que de verdad
        salio, para que el paso que llama no crea que hizo mas de lo que hizo.
        """
        fuera = {i for i in indices if not self.fijado(i)}
        quedan = set(indices) - fuera
        if quedan:
            self.respetados |= quedan
            print(f"  quitar: {len(quedan)} trozo(s) declarados se quedan"
                  f" — una decision no se disuelve por parecerse a un descuido")
        if not fuera:
            return 0
        edl = self.m.edl
        for clave in ("segmentos", "detalle"):
            edl[clave] = [x for k, x in enumerate(edl[clave]) if k not in fuera]
        self._sucio = True
        return len(fuera)

    def rehacer(self, trozos) -> None:
        """Reescribe la lista entera con `[(Tramo, detalle), …]`.

        Para quien parte un trozo en varios: quitar el aire muerto de dentro de
        un segmento no lo acorta, lo **divide**, y entonces no hay un índice que
        mover sino una lista nueva.
        """
        edl = self.m.edl
        edl["segmentos"] = [[t.desde, t.hasta] for t, _ in trozos]
        edl["detalle"] = [{**d, "start": t.desde, "end": t.hasta}
                          for t, d in trozos]
        edl["fuentes"] = [d.get("toma") or "" for _, d in trozos]
        self._sucio = True

    def anotar(self, clave: str, valor) -> None:
        """Deja escrito en el montaje algo que no es un corte."""
        if valor is None:
            self.m.edl.pop(clave, None)
        else:
            self.m.edl[clave] = valor
        self._sucio = True

    # ── y se escribe ────────────────────────────────────────────────────────
    def guardar(self) -> bool:
        """**La duración se recalcula siempre**: es la suma de los trozos.

        No es un adorno del fichero. Es lo que lee quien pregunta cuánto dura
        una pieza sin abrirla, y dejarla al criterio de cada paso es cómo llegó
        a mentir en seis de las siete.

        **Y son DOS cifras, no una.** Esto escribía `duracion_s` y dejaba
        `duracion_montada_s` como estuviera, así que tras coser el reel-02 el
        fichero decía 67,98 y 67,01 a la vez — y la que `dominio/version.py`
        guarda como duración de la versión es justo la que no se tocaba. Es
        C-192 por tercera puerta: la promesa del docstring era cierta a medias.
        """
        if not self._sucio:
            return False
        edl = self.m.edl
        edl["duracion_s"] = round(
            sum(float(b) - float(a) for a, b in
                (s[:2] for s in edl.get("segmentos") or [])), 2)
        edl["duracion_montada_s"] = edl["duracion_s"]
        with open(self.m.pieza.ruta_edl, "w", encoding="utf-8") as f:
            json.dump(edl, f, ensure_ascii=False, indent=1)
        self._sucio = False
        return True

    def __str__(self) -> str:
        return f"tijera sobre {self.slug} ({len(self)} trozos)"
