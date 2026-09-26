"""**El alcance de un encargo: hasta dónde llega lo que se pide hoy.**

Jaime, 8-9-2026, corrigiéndome cuando yo proponía darle otras herramientas al
paso de tiquets: *«los dos caminos son composición o tiquet; el tiquet puede y
debe tener las mismas herramientas que composición, las mismas formas de
componer, pero acotado únicamente al segmento del tiquet; lo demás puede sugerir
pero no abrir tiquet ni correr de nuevo, de otra forma los tiquets nunca se
resuelven»*. Y acto seguido: *«las herramientas quedan iguales… lo que cambia es
el alcance. Esto es POO»*.

Así que no hay dos oficios ni dos juegos de herramientas: **hay uno, y un
alcance**. Componer de cero es este mismo objeto con el alcance abierto.

## Por qué es un objeto y no cinco funciones

Estaba repartido en `abierto.py` entre `encargo`, `alcance`, `modo`, `abre` y
`_de_la_tabla_ticket`, y la respuesta viajaba como tupla desnuda —
`(hay, etapas, todas)`—: quien la recibía tenía que saber que el primero es si
hay tiquets, el segundo qué etapas abren y el tercero si alguno habla de la
pieza entera. Es el dato desnudo que este proyecto paga caro, y con él pasó lo
de siempre: cada sitio lo interpretaba a su manera y el paso de composición
acabó preguntando por la pieza entera para arreglar una palabra.

Aquí lo sabe el objeto, y las tres preguntas que se le hacen son suyas: **¿esta
etapa entra?**, **¿qué se le dice al que contesta?** y **¿qué puede tocar?**.
"""
from __future__ import annotations


class Alcance:
    """Hasta dónde llega el encargo de una pieza en una fase.

    Sin tiquets es el camino de composición: la pieza entera, sin instrucción
    añadida. Con tiquets es el otro camino, y **sólo cambia hasta dónde llega**.
    """

    def __init__(self, slug: str, fase: str, tiquets=None, etapas=None,
                 toda_la_pieza: bool = False, instruccion: str = ""):
        self.slug = slug
        self.fase = fase
        #: Los tiquets de esa fase, con sus palabras enteras.
        self.tiquets = list(tiquets or [])
        #: Las etapas que los tiquets nombran.
        self.etapas = set(etapas or ())
        #: Cierto cuando alguno habla de la pieza y no de una escena.
        self.toda_la_pieza = bool(toda_la_pieza)
        #: La capa de instrucción del contrato, o `""` en composición.
        self.instruccion = instruccion or ""

    @classmethod
    def de(cls, slug: str, fase: str) -> "Alcance":
        """El alcance real de esa pieza en esa fase, leído de lo que hay abierto."""
        from . import abierto

        suyos = [t for t in abierto.suyas(slug) if t[2] == fase]
        if not suyos:
            return cls(slug, fase)
        tiquets = [{"id": i, "de": acc, "dice": txt} for i, acc, _f, txt in suyos]
        # **Se le pregunta a CADA tiquet si nombra escena, no se cuentan.**
        #
        # Esto era `len(etapas) < len(tiquets)`, y con eso dos tiquets sobre la
        # misma escena hacian «de la pieza entera» a los dos. No es un caso
        # raro: es lo normal en cuanto Jaime mira una pieza dos veces. Medido
        # el 16-9-2026 en reel-11, con los siete tiquets de subtitulos mas el
        # del panel — los ocho con su beat, ninguno suelto— repartidos en cinco
        # escenas: 5 < 8, `toda_la_pieza` salia cierto, y `editables` devolvia
        # `[]` sobre una pieza aprobada. O sea que la orden que llegaba al
        # disenador era «no puedes tocar nada» justo cuando cada tiquet decia
        # exactamente donde.
        #
        # La pregunta buena es la que ya se hacia una vez: `etapa_de` contesta
        # por tiquet. Uno solo sin escena basta para abrir la pieza, que es lo
        # que el atributo dice significar.
        nombran = [abierto.etapa_de(t["dice"]) for t in tiquets]
        etapas = {e for e in nombran if e is not None}
        etapas |= abierto.beats_de_tiquets(slug, fase)
        return cls(slug, fase, tiquets=tiquets, etapas=etapas,
                   toda_la_pieza=any(e is None for e in nombran),
                   instruccion=abierto.MODO)

    def __bool__(self) -> bool:
        """Cierto si hay algo que acotar. Falso es el camino de composición."""
        return bool(self.tiquets)

    @property
    def editables(self):
        """Las etapas que se pueden tocar, o `None` si es la pieza entera.

        `None` no es un hueco: es **refactor**, componer de cero. Una lista
        significa «sólo éstas», y el resto está aprobado.

        **Y quien dice qué está aprobado es el segmento, no el tiquet.** Esto
        se calculaba sólo de los tiquets abiertos, así que sin ninguno devolvía
        `None` — «la pieza entera»— aunque las siete etapas estuvieran firmadas.
        Medido el 10-9-2026 con cero tiquets abiertos: `Alcance.editables` decía
        `None` en las siete piezas mientras el marcador decía que reel-02, -04,
        -06 y -07 no tenían **ninguna** etapa abierta. O sea, la orden que le
        llegaba al compositor era recomponer entero lo ya aprobado.

        Jaime, 10-9-2026: *«dos modos: refactor, que es todo el documento, o
        segmento por segmento, que ya está declarado en el Json»*. Los dos
        salen de aquí, y de una sola fuente.
        """
        try:
            from . import segmento as _sg

            segs = _sg.Segmento.de(self.slug)
            abiertos = [x.n for x in segs if not x.aprobado]
            # Nada aprobado todavia: es refactor de verdad, la pieza entera.
            if segs and len(abiertos) < len(segs):
                # Un tiquet no abre lo aprobado por su cuenta: acota DENTRO de
                # lo que ya estaba abierto, o nombra la etapa que reabre.
                if self and self.etapas and not self.toda_la_pieza:
                    return sorted(set(abiertos) | self.etapas)
                return sorted(abiertos)
        except Exception:                          # noqa: BLE001
            pass
        if not self or self.toda_la_pieza or not self.etapas:
            return None
        return sorted(self.etapas)

    def abre(self, etapa) -> bool:
        """¿Este encargo vuelve a poner esa etapa sobre la mesa?

        Una etapa ya resuelta no entra sola —se describe una vez—, pero un
        tiquet suyo la abre: no la rehace, la abre para mirarla con la
        corrección delante.
        """
        if not self:
            return False
        try:
            return self.toda_la_pieza or int(etapa) in self.etapas
        except (TypeError, ValueError):
            return False

    def sobre(self, prompt: str, payload: dict) -> tuple:
        """Pone el alcance encima del contrato: `(prompt, payload)`.

        Las capacidades no cambian —son lo que el oficio sabe hacer—; lo que se
        añade es hasta dónde llega el encargo de hoy.
        """
        if not self:
            return prompt, payload
        return (prompt + self.instruccion,
                {**payload, "modo": "tiquets", "tiquets": self.tiquets})
