"""El tablero que está declarado y **no dice nada en pantalla**.

Es la avería de la casa por su lado más callado: no falta el dato, está puesto
y no llega. `escena_desc.tablero` de reel-05 e2 declaraba
`{kind: "tipo", cubre: "panel", figura: "serie"}` y ni una palabra de copy, así
que `armarPaneles` lo tiraba en su `.filter(bloques.length)`, `TableroDeclarado`
devolvía `null` por no tener texto, y en pantalla quedaban **13,6 s de tres
paralelogramos de 40 px** sobre su pecho.

Y el paso que compone no volvía a preguntar, porque `encargos()` sólo miraba si
la columna `tablero` estaba **puesta**. Estaba: puesta y muda.

Su encargo sí decía qué tenía que verse —*«dos fichas rectangulares que entran
en diagonal desde el borde derecho: REALTOR / TRES CASAS EN UN TRIMESTRE y
RETAIL / EMPEZÓ A GUARDAR MÁS»*— pero eso es prosa, y de la prosa no se saca
copy con una expresión regular: Jaime paró esa versión en el sitio. La única
salida es volver a preguntárselo a quien tiene el criterio.

Vive aquí y no dentro del servicio porque es una pregunta del **dominio** —¿este
tablero llega a la pantalla?— y la contesta igual quien compone, quien audita y
quien informa.
"""
from __future__ import annotations

import json

#: Claves que se escriben **para el motor**, no para la pantalla: la placa es
#: una imagen, `sfx` un nombre de fichero, `figura` el nombre de un dibujo y
#: `cubre`/`familia`/`oro` instrucciones de composición.
#:
#: Es la misma lista que ya declaran `src/components/declarado/lineas.ts` —para
#: no rotular «430» ni «land» en versales de 96 px— y `scripts/reels/lectura.mjs`
#: —para no contarlas como bloques de lectura—. Aquí sirve para la pregunta
#: contraria: si se quitan todas, **¿queda algo que rotular?**
NO_ES_COPY = frozenset({
    "familia", "zona", "cubre", "oro", "sound", "fondo", "filete", "figura",
    "sfx", "camara", "motion", "placa", "recorte", "fuerza", "deriva",
    "anclas", "entrada", "paso", "alinea", "duracion", "condiciones_en_fila",
})


def _hay(v) -> bool:
    """¿Este valor declarado lleva algo que se pueda rotular?"""
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, bool):
        return False
    if isinstance(v, (int, float)):
        return True
    if isinstance(v, list):
        return any(_hay(x) for x in v)
    if isinstance(v, dict):
        return any(_hay(x) for k, x in v.items() if k not in NO_ES_COPY)
    return False


def sin_copy(fila) -> bool:
    """¿El tablero declarado de esta fila llega a pantalla **sin una línea**?

    `fila` es una fila de `escena_desc` con su columna `tablero`. Sin tablero
    devuelve `False`: eso no es un tablero mudo, es no tener tablero, y de eso
    ya se encarga quien pregunta. Un `tablero` ilegible cuenta como mudo — que
    no se pueda leer y que no diga nada acaban igual en la pantalla.
    """
    try:
        crudo = fila["tablero"]
    except (KeyError, IndexError, TypeError):
        return False
    if not crudo:
        return False
    try:
        props = (json.loads(crudo) or {}).get("props") or {}
    except (TypeError, ValueError):
        return True
    return not any(_hay(v) for k, v in props.items() if k not in NO_ES_COPY)
