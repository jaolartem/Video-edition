"""De qué palabras está hecho un texto — contadas **una sola vez**.

**La regla no vive aquí; las respuestas sí.** Cómo se parte un texto y qué
palabras distinguen un contenido de otro lo declara `dominio.texto`, que es su
dueño. Este módulo no añade una quinta regla de normalización —esa fue la avería
de las cuatro `limpio`/`norm` distintas con el mismo nombre—: añade **memoria**.

Y hacía falta porque los mismos textos se parten una y otra vez. `seleccionar.py`
puntúa cada ventana contra cada etapa, así que las 5.373 ventanas del corpus se
re-tokenizan una vez por etapa: **50 millones de llamadas a
`unicodedata.category` sobre los mismos 9.951 textos**, medido con cProfile.
Eran 93 s de las dos barridas de las seis piezas, y bajan a 8 s.

No hace falta una tarjeta gráfica para esto — se probó la pregunta y la
respuesta era un `dict`. Recordar lo que ya se calculó es más barato que
calcularlo en paralelo.

El tamaño se acota solo: la clave es el texto y los textos son los del corpus.
Medido, 9.951 entradas por proceso; y cada script corre en el suyo, así que no
hay nada que vaciar.

## AVISO: `dominio.texto.VACIAS` está vacío, y eso cambia lo que se monta

`contenido()` dice filtrar «las palabras que no distinguen un contenido de otro»
y hoy **no filtra ninguna**: sólo tira las de tres letras o menos. `beats.norm`
sí las filtraba —sesenta palabras: «que», «usted», «esto», «tiene», «mas»,
«porque», «cuando»…— y al pasar a `contenido()` se cayeron sin que nadie lo
notara, porque las dos versiones devuelven listas de palabras y ninguna falla.

No es cosmético: `candidata.puntua` mide cobertura sobre esas listas, así que
con las vacías dentro **todo enunciado cubre más**. Medido en reel-01, con el
libreto y las 39 unidades de hoy: la etapa 1 pasa de 0,640 a 0,675 y la etapa 2
—«revelación»— pasa de SIN MATERIAL a montar 3,6 s. Cada palabra de función que
se cuela sube la nota de quien la repite, que es justo lo contrario de lo que la
lista existía para evitar.

Esto **no** se arregla aquí: una segunda lista de vacías al lado de la primera
es la avería de las cuatro `norm`, otra vez. Se arregla llenando
`dominio.texto.VACIAS` con la lista que vivía en `beats.VACIAS` —recuperable con
`git show HEAD:mi-video/scripts/beats.py`— y volviendo a mirar el lote, porque
mueve la selección de todas las piezas.
"""
from __future__ import annotations

from . import texto as _tx

_PARTIDO, _NORMADO = {}, {}


def palabras(t):
    """Las palabras tal cual, sin tildes ni puntuación. No filtra nada.

    **Devuelve una copia, no lo guardado.** La lista cacheada se devolvía tal
    cual —un 14% más rápido— y eso cambia el contrato en silencio: hoy nadie
    muta lo que sale de aquí, pero el día que alguien haga un `.append` sobre el
    resultado envenena la caché y **el fallo aparece en otra función**. Copiar
    una lista de veinte palabras cuesta menos que ese rato de depuración.
    """
    ws = _PARTIDO.get(t)
    if ws is None:
        ws = _PARTIDO[t] = _tx.palabras(t)
    return list(ws)


def contenido(t, idioma=None):
    """De qué habla un texto, sólo lo que distingue. Regla en `dominio.texto`.

    Lo que no distingue depende de la lengua (C-665), así que la caché la
    lleva en la clave: sin ella, un texto inglés y uno español iguales en
    letras compartirían respuesta.
    """
    clave = t if idioma is None or idioma.codigo == "es" else (idioma.codigo, t)
    ws = _NORMADO.get(clave)
    if ws is None:
        ws = _NORMADO[clave] = _tx.contenido(t, idioma)
    return list(ws)
