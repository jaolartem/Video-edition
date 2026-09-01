"""Lo que se dice en una cinta, y **dónde deja cortar**.

**Por qué es un objeto.** Ocho pasos de `costuras.py` montaban cada uno su
`cache = {}` de palabras por cinta, y cada uno decidía por su cuenta qué contaba
como frontera de frase. Es la avería de siempre en pequeño: la misma pregunta
contestada en ocho sitios diverge en cuanto alguien toca uno — y aquí ya había
divergido, porque tres de los ocho ordenaban las palabras y cinco no.

Aquí se le pregunta al habla, y el habla contesta **una vez y para todos**.
"""
from __future__ import annotations

#: El silencio que basta para que el oído oiga una frontera. Por debajo de eso
#: el corte entra pegado a la palabra de antes.
AIRE = 0.30
#: Lo que hace falta para que se oiga la consonante con la que arranca una
#: palabra. Por debajo de 60 ms la primera sílaba entra descabezada y por encima
#: de 120 se cuela el final de lo anterior; 80 es el centro de esa ventana.
ATAQUE = 0.08

#: Palabras con las que una frase **no puede acabar**: artículos, preposiciones
#: y conectores. Si el último trozo de una etapa muere en una de éstas, la idea
#: se quedó sin objeto.
COLGANTES = {"y", "o", "u", "pero", "porque", "que", "cuando", "si", "de", "del",
             "la", "el", "los", "las", "un", "una", "unos", "unas", "en", "a",
             "al", "con", "para", "por", "su", "sus", "se", "le", "les", "lo",
             "me", "te", "nos", "es", "son", "mi", "tu", "como", "sin", "sobre",
             "entre", "hasta", "desde", "muy", "mas", "más", "ya", "no"}

#: Con qué cierra una idea. La coma sólo cuenta al buscar la cabeza de ESTA
#: frase, nunca al cerrarla: con el punto solo, `reel-03` se traía «usted tiene
#: un contador» dos veces.
CIERRA = (".", "?", "!")


def colgante(txt: str) -> bool:
    """¿Es una palabra con la que la frase se queda a medias?"""
    return txt.strip(".,¿?¡!;:").lower() in COLGANTES


def cierra(p, coma: bool = False) -> bool:
    """¿Esta palabra cierra una idea, según la puntuación del transcript?"""
    return p.texto.strip().endswith(CIERRA + ((",",) if coma else ()))


class Habla:
    """Las palabras de la cinta `cinta`, ya sostenibles, y lo que permiten.

    Las palabras salen de `Cinta.palabras()`, que es quien las pega al habla
    medida y les da sitio. Aquí sólo se contesta lo que se puede preguntar sobre
    ellas: dónde empieza y acaba una frase, y si un corte cae dentro de una.
    """

    __slots__ = ("cinta", "palabras", "_fronteras", "_dicts")

    _CACHE: dict = {}

    def __init__(self, cinta, palabras) -> None:
        self.cinta = str(cinta or "")
        self.palabras = list(palabras)
        self._fronteras = None
        self._dicts = None

    @classmethod
    def de(cls, cinta, palabras) -> "Habla":
        """El habla de esa cinta, con las fronteras ya calculadas.

        **Las palabras no se cargan aquí: se reciben.** Quien las tiene es
        `Montaje.palabras`, que es el único sitio que las pide a la `Cinta`.
        Montar aquí una segunda caché con su propio criterio de qué transcript
        vale sería la avería de siempre: dos respuestas a «qué se dice en esta
        cinta», las dos razonables, y ninguna forma de notar que difieren.
        """
        c = str(cinta or "")
        if c not in cls._CACHE:
            cls._CACHE[c] = cls(c, palabras)
        return cls._CACHE[c]

    def __bool__(self) -> bool:
        return bool(self.palabras)

    def __len__(self) -> int:
        return len(self.palabras)

    # ── lo que se oye dónde ──────────────────────────────────────────────────
    def en(self, tramo) -> list:
        """Las palabras que se oyen dentro de ese tramo. La vara del oído."""
        return tramo.palabras_de(self.palabras)

    def primera_tras(self, t: float):
        """La primera palabra que todavía suena en `t`, o `None`."""
        return next((p for p in self.palabras if p.acaba > t + 0.001), None)

    def dicts(self) -> list:
        """Las mismas palabras en el formato que espera `beats`."""
        if self._dicts is None:
            self._dicts = [p.a_dict() for p in self.palabras]
        return self._dicts

    # ── dónde deja cortar ────────────────────────────────────────────────────
    def fronteras(self) -> tuple[list, list]:
        """Los sitios donde una frase puede empezar o acabar de verdad.

        Dos señales, y las dos salen de la transcripción buena:

        - **La puntuación.** El barrido de cuatro pasadas devuelve puntos e
          interrogantes, así que se sabe dónde cierra una idea sin adivinar.
        - **El aire.** Un hueco de `AIRE` entre dos palabras es una frontera
          aunque no lleve punto: el hablante respiró ahí.
        """
        if self._fronteras is not None:
            return self._fronteras
        ws, ini, fin = self.palabras, [], []
        for k, p in enumerate(ws):
            antes = ws[k - 1] if k else None
            if antes is None or p.empieza - antes.acaba >= AIRE or cierra(antes):
                ini.append(p.empieza)
            sig = ws[k + 1] if k + 1 < len(ws) else None
            if sig is None or sig.empieza - p.acaba >= AIRE or cierra(p):
                fin.append(p.acaba)
        self._fronteras = (sorted(set(ini)), sorted(set(fin)))
        return self._fronteras

    def fuera_de_palabra(self, x: float, hacia: str) -> float:
        """Saca un corte de dentro de una palabra. `hacia` es 'ini' o 'fin'.

        Regla de Jaime mirando el primer render: *«muy importante que los cortes
        sean finos»*, y dos ejemplos suyos de lo que pasa cuando no lo son — en
        el segundo 58 se oye «30, much» y en el 1:15 queda «rente», la cola de
        «diferente». Las dos son el mismo fallo: el corte cayó a mitad de
        palabra, y eso no se arregla con criterio: se saca. Es aritmética, y por
        eso puede correr siempre.

        **Al borde exacto, sin margen.** Con ±0,02 el corte salía de una palabra
        y entraba en la de al lado —el transcript las da pegadas—, así que el
        arreglo oscilaba: once cortes «arreglados» en cada pasada,
        indefinidamente.
        """
        for p in self.palabras:
            if not p.empieza < x < p.acaba:
                continue
            if hacia == "ini":
                # **Un respiro no es un corte a medias.** El ataque retrocede 80
                # ms para que se oiga la consonante inicial, y ese retroceso cae
                # dentro de la palabra ANTERIOR porque el transcript las da
                # pegadas. Sin esta salvedad los dos pasos se deshacían el
                # trabajo el uno al otro.
                if p.acaba - x <= ATAQUE + 0.005:
                    return x
                return p.empieza if (x - p.empieza) / max(p.dura, 1e-6) < 0.5 \
                    else p.acaba
            return p.acaba if (x - p.empieza) / max(p.dura, 1e-6) > 0.5 \
                else p.empieza
        return x

    def __str__(self) -> str:
        return f"{len(self.palabras)} palabras de {self.cinta}"
