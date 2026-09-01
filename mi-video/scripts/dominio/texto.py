"""Cómo se normaliza un texto, y **para qué**.

Había cuatro funciones llamadas `limpio` o `norm` en cuatro ficheros, y no eran
cuatro copias de la misma regla: eran **cuatro reglas distintas con el mismo
nombre**. Ninguna decía para qué servía, así que quien llamaba tenía que
deducirlo del cuerpo — y el que se equivocaba no se enteraba, porque todas
devuelven texto.

Aquí cada una se llama por su trabajo. No cambia ninguna: son las mismas cuatro,
con el nombre que dice cuándo usarlas.
"""
from __future__ import annotations

import re
import unicodedata

#: Palabras que no distinguen un contenido de otro. Vive aquí porque es parte
#: de la regla de `contenido()`, no de quien la llama.
#:
#: **Y estuvo vacía unas horas, que es la avería que este fichero venía a
#: cerrar.** Al traer aquí la regla desde `beats.norm` moví la función y **no la
#: lista**, y como las dos versiones devuelven listas de palabras, nada falló:
#: simplemente cada «que», «usted» o «porque» empezó a contar como contenido, y
#: quien repite palabras de función subió de nota. Medido en reel-01: la etapa 1
#: pasó de 0,640 a 0,675 y la etapa 2 **de no tener material a montar 3,6 s**.
#:
#: Lo encontró el agente que partió `beats.py`, comparando el montaje viejo
#: contra el nuevo pieza por pieza. Sin esa comparación habría entrado en el
#: lote entero sin que nadie lo notara — que es exactamente cómo se pierde una
#: decisión en este proyecto.
VACIAS: frozenset[str] = frozenset({
    "que", "de", "la", "el", "en", "los", "las", "un", "una", "por", "con",
    "para", "del", "se", "su", "sus", "lo", "le", "es", "no", "mas", "pero",
    "como", "esta", "este", "esto", "usted", "yo", "va", "ya", "si", "al",
    "y", "a", "o", "sin", "hay", "muy", "todo", "todos", "eso", "ese", "ahi",
    "tiene", "ser", "son", "esa", "cada", "porque", "cuando", "donde",
})


def _sin_tildes(t: str) -> str:
    t = unicodedata.normalize("NFD", (t or "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def comparable(t: str) -> str:
    """Para **buscar un ancla** en la línea de montaje.

    Deja letras, dígitos y espacios; todo lo demás fuera. Es la vara con la que
    `revision._por_ancla` decide si el texto que la nota nombra sigue en la
    pieza, así que cambiarla mueve dónde caen los cortes.
    """
    return "".join(c for c in _sin_tildes(t) if c.isalnum() or c == " ")


def palabras(t: str) -> list[str]:
    """Para **partir en palabras** lo que dijo el modelo.

    Cualquier cosa que no sea letra o dígito separa. Devuelve lista, no cadena,
    porque quien la usa cuenta palabras.
    """
    return re.sub(r"[^a-z0-9 ]+", " ", _sin_tildes(t)).split()


def contenido(t: str) -> list[str]:
    """Para **comparar de qué habla** un trozo: sólo lo que distingue.

    Fuera lo de tres letras o menos y las vacías. Es lo que hace que «y el
    banco» y «el banco» cuenten como lo mismo — que es justo lo que se quiere al
    medir redundancia, y justo lo que NO se quiere al buscar un ancla.
    """
    return [w for w in palabras(t) if len(w) > 2 and w not in VACIAS]


def numerico(t: str) -> str:
    """Para **comparar cifras**: quita el separador de miles de dentro.

    «$180,000» y «180000» son el mismo número, y sin esto son dos textos
    distintos. Usa NFKD a propósito —no NFD— para que un «²» o un dígito ancho
    se reduzcan a su forma normal antes de comparar.
    """
    t = unicodedata.normalize("NFKD", str(t).lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"(?<=\d)[.,](?=\d)", "", t)


#: Las que `VACIAS` se come y **cambian el sentido**. `contenido` las quita
#: porque para comparar de qué habla una frase no aportan; para comparar si dice
#: lo mismo, deciden. Un texto que pierde el «no» habla de lo mismo y afirma lo
#: contrario.
NIEGAN = ("no", "ni", "sin", "nunca", "nada", "tampoco", "jamas", "pero")


def dice_lo_mismo(a: str, b: str) -> bool:
    """¿Estos dos textos dicen lo mismo, aunque no sean iguales?

    **Para qué existe.** Jaime: *«lo que ya se aprobó no se vuelve a discutir: se
    revisa que esté como se dijo»*. Una descripción se estampa con el texto sobre
    el que se escribió, y caducaba con una comparación exacta: si el corte movía
    un «su» de más al principio, la descripción se tiraba y se volvía a pedir
    entera. Eso es discutir de nuevo lo aprobado, y cuesta una llamada por etapa.

    **Y no vale un parecido.** Un 95 % de coincidencia aprueba un texto que
    perdió un «no», que es la mitad del sentido. Así que se compara lo que
    decide: las palabras de contenido, las negaciones y los números. Si los tres
    son idénticos, lo que cambió es relleno —conectores, muletillas, el arranque
    de una frase— y lo que se dijo del texto sigue siendo verdad.

    Lo que esto NO hace es decidir si la descripción es buena. Decide si sigue
    hablando del mismo texto, que es una pregunta de código.
    """
    if " ".join((a or "").split()) == " ".join((b or "").split()):
        return True
    if contenido(a) != contenido(b):
        return False
    if _cifras(a) != _cifras(b):
        return False
    return _niegan(a) == _niegan(b)


def _cifras(t: str):
    """Las cifras que aparecen, en orden y ya normalizadas.

    `numerico` normaliza el texto entero —«25 mil» y «25.000» acaban iguales—,
    que es justo lo que hace falta antes de comparar; pero devuelve el texto, no
    las cifras. Compararlo entero era comparar otra vez la frase completa, y
    entonces la regla no perdonaba ni una coma.
    """
    return re.findall(r"\d+(?:[.,]\d+)?", numerico(t or ""))


def _niegan(t: str):
    """Cuántas veces niega, en orden. El orden importa: «no es X» y «es no X»."""
    return [p for p in palabras(t) if p in NIEGAN]
