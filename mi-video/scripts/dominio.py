"""Los tipos del dominio: `Rango`, `Palabra`, `Tramo`, `Ventana`, `Unidad`.

Encargo de Jaime: *«no quiero monolitos, quiero servicios concretos»*. Esto va
**antes** de partir ningún fichero, y el orden es lo contraintuitivo.

## Por qué esto primero

`scripts/forma.py` cuenta **1.809 accesos de la forma `obj["campo"]` sobre 233
nombres de campo distintos**. Ninguno de esos 233 nombres existe declarado en
ningún sitio: no hay dónde mirar qué campos tiene una ventana candidata ni qué
garantiza que estén. Partir `seleccionar.py` en cuatro ficheros reparte los
mismos accesos sin tipo entre más ficheros — **mueve el monolito, no lo
deshace**.

Y ya cuesta. El mismo concepto se escribe de dos maneras según de dónde venga:

    ["start"] / ["end"]   273 accesos   cuando el rango viene del transcript
    ["a"] / ["b"]         143 accesos   cuando viene de una ventana

Son el mismo hecho —un trozo de cinta entre dos instantes— con dos nombres, y
por eso cada función que recibe «un rango» tiene que saber de dónde salió. `Rango`
es lo primero que hay aquí, y es la mitad del valor de este módulo.

## Y por qué no se reescribe nada de golpe

Regla de Jaime: *«si te doy instrucciones cambias la máquina, no la rehaces»*.
Convertir 1.809 accesos de una vez es rehacerla, y además el paso 1 y la
selección son lo que produce las piezas de esta semana.

Así que cada tipo trae `de_dict()` y `a_dict()`, y **puede vivir al lado del
diccionario**: una función se convierte, devuelve `a_dict()` en el borde, y las
demás no se enteran. El número de `forma.py` es el que dice cuánto queda — baja
solo si esto se usa, y no baja si se decora.

    from dominio import Rango, Palabra, Ventana

Nada aquí toca la base ni el disco: son datos con nombre y las cuentas que se
derivan de ellos. Lo que decide sigue decidiéndolo quien decidía.
"""
from dataclasses import dataclass, field

# El suelo por debajo del cual dos instantes son el mismo. Los tiempos vienen de
# ffmpeg y de whisper redondeados a milisegundos, así que comparar por igualdad
# exacta hace que `0.1 + 0.2` decida un corte.
EPS = 0.002


@dataclass(frozen=True, order=True)
class Rango:
    """Un trozo de cinta entre dos instantes, en segundos.

    **Un solo nombre para lo que se llamaba de dos maneras.** `desde`/`hasta`
    aquí; `de_ab()` y `de_startend()` traducen desde los dos dialectos que hay
    en el código, y `a_ab()`/`a_startend()` devuelven al que espere quien llame.
    Traducir en el borde es lo que permite convertir una función sin tocar a sus
    vecinas.
    """
    desde: float
    hasta: float

    def __post_init__(self):
        if self.hasta < self.desde - EPS:
            raise ValueError(f"rango al reves: {self.desde} > {self.hasta}")

    @property
    def dur(self) -> float:
        return max(0.0, self.hasta - self.desde)

    @property
    def centro(self) -> float:
        return (self.desde + self.hasta) / 2

    def contiene(self, t: float) -> bool:
        return self.desde - EPS <= t < self.hasta + EPS

    def dentro_de(self, otro: "Rango") -> bool:
        return (otro.desde - EPS <= self.desde
                and self.hasta <= otro.hasta + EPS)

    def solapa(self, otro: "Rango") -> float:
        """Cuántos segundos comparten. 0 si no se tocan."""
        return max(0.0, min(self.hasta, otro.hasta) - max(self.desde, otro.desde))

    # ── los dos dialectos ────────────────────────────────────────────────
    @classmethod
    def de_ab(cls, d: dict) -> "Rango":
        return cls(float(d["a"]), float(d["b"]))

    @classmethod
    def de_startend(cls, d: dict) -> "Rango":
        return cls(float(d["start"]), float(d["end"]))

    @classmethod
    def de_desdehasta(cls, d: dict) -> "Rango":
        return cls(float(d["desde"]), float(d["hasta"]))

    def a_ab(self) -> dict:
        return {"a": round(self.desde, 3), "b": round(self.hasta, 3)}

    def a_startend(self) -> dict:
        return {"start": round(self.desde, 3), "end": round(self.hasta, 3)}

    def a_desdehasta(self) -> dict:
        return {"desde": round(self.desde, 3), "hasta": round(self.hasta, 3)}


@dataclass
class Palabra:
    """Una palabra del transcript, con su instante y su sello de sospecha.

    `larga` no es decoración: una palabra de más de 1,5 s no es una palabra, es
    un cruce de dos (aprendizaje 12). Se marca, no se descarta.
    """
    rango: Rango
    texto: str
    larga: bool = False

    @classmethod
    def de_dict(cls, d: dict) -> "Palabra":
        return cls(Rango.de_startend(d), d.get("text", ""),
                   bool(d.get("larga", 0)))

    def a_dict(self) -> dict:
        return {**self.rango.a_startend(), "text": self.texto,
                "larga": int(self.larga)}


@dataclass
class Tramo:
    """Un tramo de voz medido por el detector, no por el modelo.

    La unidad de análisis del paso 1. La pausa la mide el detector de habla; el
    texto lo pone whisper después, y puede faltar — un tramo sin palabras **no
    es silencio, es un tramo del que no se sacó nada**, que es el aprendizaje 18
    y la razón de que `texto` sea opcional en vez de cadena vacía.
    """
    rango: Rango
    texto: str | None = None
    acuerdo: float | None = None
    pasadas: int = 0

    @property
    def con_voz(self) -> bool:
        return bool(self.texto)


@dataclass
class Ventana:
    """Una candidata: el trozo que empieza en un tramo y acaba en otro.

    Es lo que `seleccionar.ventanas()` produce a millares y lo que se puntúa
    contra cada etapa. Los campos son los que ya tenía el diccionario; lo que
    cambia es que ahora están declarados en un sitio.
    """
    rango: Rango
    texto: str
    toma: str | None = None
    i: int = 0
    j: int = 0
    voz: float = 0.0
    aire: float = 0.0
    entra: float = 0.0
    sale: float = 0.0
    sobra: float = 0.0
    trunca: float = 0.0
    extra: dict = field(default_factory=dict)

    @classmethod
    def de_dict(cls, d: dict) -> "Ventana":
        conocidos = {"a", "b", "texto", "toma", "i", "j", "voz", "aire",
                     "entra", "sale", "sobra", "trunca"}
        return cls(Rango.de_ab(d), d.get("texto", ""), d.get("toma"),
                   d.get("i", 0), d.get("j", 0), d.get("voz", 0.0),
                   d.get("aire", 0.0), d.get("entra", 0.0), d.get("sale", 0.0),
                   d.get("sobra", 0.0), d.get("trunca", 0.0),
                   # Lo que el paso siguiente le cuelgue —`det`, `literal`,
                   # `voz_st`— sigue viajando. Un tipo que pierde campos al
                   # convertir es peor que el diccionario.
                   {k: v for k, v in d.items() if k not in conocidos})

    def a_dict(self) -> dict:
        return {**self.rango.a_ab(), "texto": self.texto, "toma": self.toma,
                "i": self.i, "j": self.j, "voz": self.voz, "aire": self.aire,
                "entra": self.entra, "sale": self.sale, "sobra": self.sobra,
                "trunca": self.trunca, **self.extra}


@dataclass
class Unidad:
    """Lo catalogado: un tramo de la cinta con su texto y sus columnas.

    Lo que antes era motivo de exclusión —el aire, si abre en mayúscula, si
    cierra en punto— es una columna, no un filtro. Aquí se cataloga el átomo;
    quien decide es `seleccionar`.
    """
    rango: Rango
    texto: str
    toma: str | None = None
    aire: float = 0.0
    abre: bool = False
    cierra: bool = False
    acuerdo: float = 1.0

    @classmethod
    def de_dict(cls, d: dict) -> "Unidad":
        return cls(Rango.de_desdehasta(d), d.get("texto", ""), d.get("toma"),
                   d.get("aire", 0.0), bool(d.get("abre")),
                   bool(d.get("cierra")), d.get("acuerdo", 1.0))

    def a_dict(self) -> dict:
        return {**self.rango.a_desdehasta(), "texto": self.texto,
                "toma": self.toma, "aire": self.aire, "abre": int(self.abre),
                "cierra": int(self.cierra), "acuerdo": self.acuerdo}
