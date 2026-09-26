"""Un corte anotado, y **dónde cae en el montaje de hoy**.

**Por qué existe, y es la avería de la segunda noche.** Jaime, el 1 de
septiembre: *«los tickets que mandé no están resueltos, otra vez se está
renderizando lo que no está actualizado»*. Medido: de 482 notas `cortar`, las 12
pendientes recortaban **0 segundos en las 7 piezas** — `revision.aplicar` las
saltaba todas antes de mirarlas.

La causa no era el ancla, que funciona: la nota 95 del reel-06 anclaba en el
montaje de hoy en 78,17-78,81 s. Era que la huella se usaba como **filtro de
entrada** — `if huella_hoy and n["huella"] != huella_hoy: continue` — y esa
guarda se autodestruye: aplicar un corte cambia el EDL, o sea que cambia la
huella, o sea que toda nota escrita contra el corte anterior queda huérfana para
siempre. 0 de 482 llevaban la huella de hoy.

## La huella no filtra: dispara el re-anclaje

Que la nota hable de otro montaje no la invalida — es exactamente para lo que se
inventó el ancla (C-79): *«el ancla es texto, sobrevive a que la pieza se vuelva
a montar»*. Lo que hace es obligar a **volver a preguntar**, y de ahí salen
cuatro respuestas, no dos:

    aplicable   el texto sigue ahí y sigue sobrando: se corta y se re-estampa
    huerfana    el sitio que nombraba ya no existe: NO se corta, se abre ticket
    cumplida    ni el texto ni lo que decía suenan: el corte ya se hizo
    ilegible    la cinta no se pudo leer: ni se aplica ni se da por hecha

## Y «sobra UNA versión» es una condición, no un adorno

Las diez notas ancladas del lote llevan la misma `regla`: *«la repetición del
bruto es un abanico para elegir... sobra UNA versión»*. Eso dice cuándo un corte
sigue teniendo sentido: **cuando queda más de una copia**. Si el montaje de hoy
sólo dice la frase una vez, cortarla no recorta una repetición, se lleva lo
único que la pieza dice.

Es el caso 95 y por poco: su ancla es «de 20 dólares», resuelve una sola vez, y
la nota explica *«el precio se dice dos veces pegadas»*. Aplicarla hoy le quita
el precio al reel-06. Por eso la duda se resuelve hacia el mismo lado que ya
declaraba `revision.aplicar`: **lo que se corta de más no vuelve solo**, y una
huérfana con ticket se recupera en cualquier momento.

## Quién cuenta los cortes pendientes

Aquí, y sólo aquí. `verificar` y `donde` tenían cada uno su SQL sobre la misma
tabla y **decían números distintos**: la puerta veía 0 —contaba sólo las de la
huella de hoy, un conjunto vacío por construcción— y `donde.py` veía 1/4/2/1/1/3.
El que mandaba era el ciego. `pendientes()` no escribe nada: mide, y quien
ejecuta es `revision.aplicar`.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from . import ancla as _an  # noqa: E402
from . import ticket as tk  # noqa: E402
from .texto import contenido  # noqa: E402

#: Cuánto del ancla tiene que seguir sonando para que la nota NO se dé por
#: cumplida. Medido el 1 de septiembre sobre las diez notas ancladas sin
#: resolver del lote: la más pobre conserva 1 de 2 palabras de contenido y
#: ninguna baja de la mitad — o sea que hoy **ninguna se archivaría sola**, que
#: es justo lo que se quiere. Archivar de menos cuesta un ticket; archivar de
#: más pierde el corte y nadie se entera (es la avería de la nota 105, cuya
#: comparación seguía en la pieza con el verbo cambiado).
SUENA_MIN = 0.5

#: Con qué se marca el ticket de una huérfana, para no abrir uno por corrida.
MARCA = "[nota {}]"


def sanear(desde, hasta, ancla):
    """Un ancla que aterrizó en la columna de los segundos, puesta en su sitio.

    `revision.anotar` recibe `(slug, accion, desde, hasta, que)` en posicional, y
    colar el texto en el tercer hueco es fácil: la fila queda con
    `desde_s='no voy a reemplazar'` y el ancla vacía. `anotar` ya lo avisa **al
    escribir**, pero las filas escritas antes de esa guarda siguen en la tabla, y
    quien las lee se las come tal cual.

    Y no se las come sin consecuencias: `revision.aplicar` ordena los cortes con
    `-x[0]` sobre esos segundos, así que una sola fila así **tira el paso entero
    con un TypeError** y la pieza se queda sin poder aplicar ningún corte. Con
    las notas #675 y #676 dentro, reel-02 no admitía ni un recorte —ni el que
    Jaime acababa de pedir— y el fallo no decía nada de anclas: decía «bad
    operand type for unary -». Lo mismo en `revision.ver`, que es el informe.

    La regla es la que ya usa `anotar`, aplicada del otro lado: **texto en la
    columna de los segundos es el ancla**; si la nota no tenía ancla, se toma, y
    los segundos quedan vacíos, que es lo que de verdad se sabe de ellos.

    Devuelve `(desde, hasta, ancla)` con los segundos como número o `None`.
    """
    def numero(v):
        if v is None or isinstance(v, (int, float)):
            return v, None
        try:
            return float(v), None
        except (TypeError, ValueError):
            return None, str(v).strip()

    desde, texto_d = numero(desde)
    hasta, texto_h = numero(hasta)
    if not (ancla or "").strip():
        ancla = texto_d or texto_h or ancla
    return desde, hasta, ancla


class Nota:
    """Una nota `cortar` de `revision`, que sabe situarse en el corte de hoy.

    No decide si hay que cortar —eso ya lo decidió quien la escribió— y no
    corta: eso es de `revision.aplicar`. Lo que aporta es **una sola respuesta**
    a «¿esto todavía se puede aplicar?», que estaba escrita de tres maneras
    distintas en tres ficheros.
    """

    APLICABLE, HUERFANA, CUMPLIDA, ILEGIBLE = (
        "aplicable", "huerfana", "cumplida", "ilegible")

    __slots__ = ("id", "slug", "ancla", "cual", "desde_s", "hasta_s",
                 "huella", "que", "estado", "_veces")

    def __init__(self, fila):
        self.id = fila["id"]
        self.slug = fila["video_slug"]
        self.ancla = (fila["ancla"] or "").strip()
        self.que = fila["que"] or ""
        self.estado = fila["estado"]
        self.desde_s, self.hasta_s, self.ancla = sanear(
            fila["desde_s"], fila["hasta_s"], self.ancla)
        self.huella = fila["huella"]
        try:
            self.cual = int(fila["cual"] or 1)
        except (IndexError, KeyError, TypeError):
            self.cual = 1
        self._veces = None

    # ── dónde cae ───────────────────────────────────────────────────────────
    def veces(self, edl) -> int:
        """Cuántas veces suena su ancla en el montaje de hoy.

        Se cuenta con la misma vara que corta —`ancla.por_ancla`, que recorre el
        EDL sobre los transcripts— en vez de con una copia local: una segunda
        versión de esta búsqueda es la avería más cara de este proyecto, porque
        las dos parecerían correctas.
        """
        if self._veces is None:
            self._veces = 0
            if self.ancla:
                while self._veces < 9:
                    r = _an.por_ancla(edl, self.ancla, self.slug,
                                      self._veces + 1)
                    if r is False:
                        return -1              # la cinta no se pudo leer
                    if not r:
                        break
                    self._veces += 1
        return self._veces

    def rango(self, edl):
        """El tramo que hay que quitar hoy, en segundos de pieza montada."""
        return (_an.por_ancla(edl, self.ancla, self.slug, self.cual)
                if self.ancla else None)

    def etapa(self, edl, cual=None):
        """En qué etapa del corte de hoy cae esa aparición de su ancla."""
        r = _an.por_ancla(edl, self.ancla, self.slug, cual or self.cual)
        if not r:
            return None
        i, _ = _an.montado_a_cinta(edl, r[0])
        detalle = edl.get("detalle") or []
        return detalle[i].get("beat") if 0 <= i < len(detalle) else None

    def copia_al_lado(self, edl) -> bool:
        """¿La otra copia que justifica el corte está en la MISMA etapa?

        **«Sobra UNA versión» habla de una repetición, y una repetición vive
        dentro de una etapa.** Contando las apariciones en la pieza entera, dos
        etapas que comparten dos palabras se leen como una copia de más que
        nadie dijo — y entonces `cual`, que es un **ordinal contado en un
        montaje que ya no existe**, elige la aparición equivocada.

        Es la avería del 4 de septiembre en reel-01, y es el ticket #127 otra
        vez: la nota 181 («en ontario», aparición 1) se escribió contra un
        montaje donde la primera era el arranque abortado del beat 3. Ese
        arranque ya lo quitaron las notas 344 y 375, así que hoy la primera es
        la buena y la segunda vive en el beat 6, sesenta segundos más allá.
        Aplicarla partió un tramo declarado continuo y dejó la pieza diciendo
        «un dueño de negocio que gana 180 mil al año», sin el lugar.

        No hace falta para una nota escrita contra ESTE corte: allí el ordinal
        se contó sobre lo que hay.
        """
        mia = self.etapa(edl)
        return any(self.etapa(edl, k) == mia
                   for k in range(1, self.veces(edl) + 1) if k != self.cual)

    def sigue_sonando(self, edl) -> bool:
        """¿Lo que el ancla decía sigue en la pieza, aunque con otras palabras?

        Un ancla que no resuelve **no demuestra que el corte se hiciera**: deja
        de resolver igual cuando el montaje cambió de toma y la misma idea se
        dice con otro verbo. Sin esta comprobación la nota se sellaba como
        «aplicada — el texto ya no está en la pieza» y la decisión de si esa
        repetición remata o sobra no la tomaba nadie.
        """
        from .montaje import Montaje

        try:
            m = Montaje(self.slug)
            hoy = set(contenido(" ".join(m.texto(t) for t, _ in m.tramos())))
        except Exception:                          # noqa: BLE001
            return True                            # sin poder mirar, no archiva
        pide = contenido(self.ancla.split("|")[0])
        if not pide:
            return True
        return sum(1 for w in pide if w in hoy) / len(pide) >= SUENA_MIN

    def clase(self, edl) -> str:
        """En cuál de los cuatro casos cae esta nota, contra el corte de hoy."""
        if not self.ancla:
            # **Sin texto no hay nada que re-anclar.** Los segundos son del
            # montaje en que se apuntó y hoy señalan otra frase: la nota 263 del
            # reel-01 decía «el segundo 20 dice "y cuan"» y el segundo 20 de hoy
            # cae en «el gobierno de Canadá espera que usted tenga». Cortar por
            # ahí es cortar a ciegas (C-92), así que sube a ticket.
            return self.APLICABLE if self._de_hoy() else self.HUERFANA
        veces = self.veces(edl)
        if veces < 0:
            return self.ILEGIBLE
        if veces == 0:
            return self.HUERFANA if self.sigue_sonando(edl) else self.CUMPLIDA
        if self._de_hoy():
            # Se escribió mirando ESTE corte: el ordinal se contó sobre lo que
            # hay, así que señala lo que la nota nombraba.
            return self.APLICABLE if veces >= self.cual else self.HUERFANA
        if veces > 1 and self.copia_al_lado(edl):
            # De otro montaje, pero la copia que la justifica sigue en su etapa:
            # quitarla deja la pieza diciéndolo, que es la condición de «sobra
            # UNA versión». Si la otra aparición vive en otra etapa no son dos
            # copias: son dos frases que comparten palabras, y el ordinal ya no
            # apunta a la que la nota nombraba (ver `copia_al_lado`).
            return self.APLICABLE if veces >= self.cual else self.HUERFANA
        # Resuelve una sola vez y la nota es de otro montaje: lo que sobraba ya
        # no sobra, y cortar se llevaría la única copia.
        return self.HUERFANA

    def _de_hoy(self) -> bool:
        return bool(self.huella) and self.huella == _huella(self.slug)

    # ── lo que se hace con ella ─────────────────────────────────────────────
    def desahuciar(self, con) -> int | None:
        """La pasa a `huerfana` y **abre ticket con sus palabras literales**.

        Sin esto la nota se queda `pendiente` para siempre: inaplicable e
        inmortal a la vez —nadie la corta, nadie la retira y nadie le dice a
        Jaime que se quedó sin sitio—. La 263 llevaba así veinte horas y un
        re-montaje.
        """
        con.execute("update revision set estado = 'huerfana' where id = ?",
                    (self.id,))
        self.estado = self.HUERFANA
        marca = MARCA.format(self.id)
        if any(marca in (t["dijo"] or "") for t in tk.abiertos(self.slug)):
            return None                            # ya tiene el suyo abierto
        falta = ("no traía ancla de texto"
                 if not self.ancla else
                 f"«{self.ancla[:70]}» ya no señala nada que sobre")
        return tk.abrir(self.slug,
                        f"{marca} corte sin aplicar: {falta}. Decía:"
                        f" {self.que[:220]}", tipo="sobra")

    def resucitar(self, con) -> None:
        """Vuelve a `pendiente` y cierra su ticket: el sitio volvió a existir."""
        if self.estado != self.HUERFANA:
            return
        con.execute("update revision set estado = 'pendiente' where id = ?",
                    (self.id,))
        self.estado = "pendiente"
        marca = MARCA.format(self.id)
        for t in tk.abiertos(self.slug):
            if marca in (t["dijo"] or ""):
                tk.contestar(t["id"], "el texto volvió a estar en la pieza: la"
                                      " nota se re-ancla contra el corte de hoy",
                             estado="arreglado", quien="la linea")

    # ── la cuenta, y sale de un solo sitio ──────────────────────────────────
    @classmethod
    def pendientes(cls, slug: str) -> tuple[list, list]:
        """`(aplicables hoy, huérfanas)`. **No escribe nada.**

        La puerta bloquea con las primeras y sólo anota las segundas: una
        huérfana no la puede aplicar ningún paso, así que parar por ella deja la
        pieza sin salida —es la avería que ya costó el bloqueo del reel-06—.
        Lo que no puede volver a pasar es que las dos sean el mismo número y
        cada fichero lo cuente a su manera.
        """
        edl = _edl(slug)
        if edl is None:
            return [], []
        con = basedatos.abrir()
        con.row_factory = sqlite3.Row
        filas = con.execute(
            "select * from revision where video_slug = ? and accion = 'cortar'"
            " and estado in ('pendiente','huerfana') order by id",
            (slug,)).fetchall()
        con.close()
        aplicables, huerfanas = [], []
        for f in filas:
            n = cls(f)
            c = n.clase(edl)
            if c == cls.APLICABLE:
                aplicables.append(n)
            elif c == cls.HUERFANA or n.estado == cls.HUERFANA:
                huerfanas.append(n)
        return aplicables, huerfanas


    # ── lo que sube a Jaime ─────────────────────────────────────────────────
    @classmethod
    def subidas(cls, slug: str) -> list:
        """Lo que subió y Jaime todavía no ha cerrado. **Sin filtrar por huella.**

        Filtrar por el montaje de hoy es la guarda que se autodestruye, y en este
        fichero ya está contada: aplicar un corte cambia el EDL, o sea la huella,
        o sea que lo escrito contra el corte anterior queda fuera para siempre —
        0 de 482. Aquí sería peor que en `cortar`, porque lo que caducaría es
        **cumplimiento**: bastaría tocar el corte para que una cifra sin fuente
        dejara de parar la pieza.

        Una nota `sube` no caduca con el montaje: caduca cuando Jaime la cierra,
        con `python scripts/revision.py --cerrar <id> --como aplicada`.

        **Aquí sólo se lee.** Quien las escribe es `servicio._escala`, en el
        paso: C-198 sacó de este fichero el import del paso justo para que el
        dominio no lo llamara, y la guarda de esa corrección me lo paró en
        cuanto lo puse otra vez. Medir y decidir es de aquí; escribir, no.
        """
        con = basedatos.abrir()
        con.row_factory = sqlite3.Row
        filas = con.execute(
            "select * from revision where video_slug = ? and estado = 'sube'"
            " order by id", (slug,)).fetchall()
        con.close()
        return [cls(f) for f in filas]


def _edl(slug: str):
    ruta = os.path.join("ads", slug, "edl-sell.json")
    if not os.path.exists(ruta):
        return None
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def _huella(slug: str):
    try:
        import modelo

        return modelo.huella_edl(slug)
    except Exception:                              # noqa: BLE001
        return None
