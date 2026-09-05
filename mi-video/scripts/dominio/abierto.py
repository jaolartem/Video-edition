"""Los tiquets de Jaime que una pieza tenía que haber atendido y no atendió.

Jaime, después de una noche entera con trece correcciones suyas sin aplicar:
*«termina y sube todos los malditos tikets, todos, para eso hicimos esa maldita
tabla, y por alguna razón siempre estoy repitiendo las mismas correcciones
porque nunca llegan las indicaciones»*.

## Por qué no llegaban

La tabla `revision` guarda sus correcciones desde hace semanas, con sus palabras
literales. Y la línea **no la mira**. `avanzar --volver recortado` devuelve la
pieza a esa fase, la fase corre su paso, y el paso no pregunta si hay un tiquet
suyo esperando: la pieza atraviesa `recortado`, `disenado` y `nivelado` y sale
por el otro lado exactamente igual que entró.

Medido el 5 de septiembre: trece tiquets suyos abiertos, las siete piezas
recorridas de punta a punta dos veces, **cero aplicados**. No es que se
perdieran — es que nadie los buscó.

Es la avería de siempre en su forma más cara: una decisión guardada que el paso
que la necesita no lee. Sólo que aquí la decisión es suya.

## Cómo se cierra

Cada corrección dice en `accion` de qué es, y de ahí sale **qué paso la
arregla**. Si la pieza ya pasó ese punto y la corrección sigue abierta, la línea
se para ahí y la nombra, con su número y sus palabras.

No la aplica sola: aplicarla es trabajo del paso, y adivinarlo sería peor. Lo
que garantiza es que **ninguna pieza llega a entregarse con un tiquet suyo
abierto**, que es lo único que hacía falta para que dejara de repetirse.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"

#: De qué es una corrección → qué paso la arregla. Es el mismo reparto que ya
#: usa `dominio/ticket.py` con `RUTA`, escrito para la tabla de Jaime.
#:
#: `otro` va a `disenado` porque es donde vive el criterio: casi todas sus notas
#: de ese tipo son de qué dice la pieza o de cómo se ve, y ninguna se arregla
#: sola en un paso mecánico.
FASE = {
    "cortar": "recortado",
    "grafico": "disenado",
    "sonido": "nivelado",
    "subtitulo": "montado",
    "otro": "disenado",
}


def suyas(slug):
    """Sus correcciones abiertas de esta pieza: (id, accion, fase, palabras)."""
    try:
        cx = basedatos.abrir(BASE)
        cx.row_factory = sqlite3.Row
        filas = cx.execute(
            "select id, accion, que from revision where video_slug = ?"
            " and estado = 'pendiente' and que like '%Jaime%' order by id",
            (slug,)).fetchall()
    except sqlite3.Error:
        return []
    return [(r["id"], r["accion"], FASE.get(r["accion"], "disenado"),
             " ".join((r["que"] or "").split())[:120]) for r in filas]


def vencidas(slug, fase_actual, orden):
    """Las que ya deberían estar hechas: su paso quedó atrás y siguen abiertas.

    `orden` es el mapa nombre-de-fase → posición en el camino, para saber qué
    quedó detrás. Una corrección cuya fase todavía no ha llegado no es una
    falta: es trabajo pendiente y la línea va hacia ella.
    """
    aqui = orden.get(fase_actual)
    if aqui is None:
        return []
    return [t for t in suyas(slug)
            if orden.get(t[2]) is not None and orden[t[2]] <= aqui]


#: **La capa de instrucción del contrato**, cuando lo que hay son tiquets.
#:
#: Jaime: *«hay dos modos para cada agente; el contrato tiene dos capas, una con
#: las capacidades y otra con la instrucción. Si es general es una cosa, pero si
#: son tikets son eso»*. El prompt del paso son **las capacidades** —lo que ese
#: agente sabe hacer, y no cambia—; esto es **la instrucción** —lo que se le pide
#: hoy—. Mezclarlas es lo que convertía cada corrección en un rebuild: *«no puedo
#: estar haciendo un rebuild cada vez que corrijo cosas puntuales»*.
MODO = """

---

# HOY NO COMPONES LA PIEZA: ARREGLAS ESTOS TIQUETS

Jaime: *«no puedo estar haciendo un rebuild cada vez que corrijo cosas
puntuales»*, y *«no quiero otro rediseño ni más retrabajos, quiero las
correcciones»*.

Las capacidades de arriba siguen siendo las tuyas. Lo que cambia es el encargo:

- **Toca sólo las etapas que nombran los tiquets** de `datos.tiquets`. El resto
  de la pieza está aprobado y no se rehace, ni «de paso» ni «ya que estamos».
- Devuelve **sólo esas etapas**. Una etapa que no devuelves se queda como está,
  que es justo lo que se quiere.
- Si un tiquet no se puede resolver sin tocar otra etapa, **dilo en `por_que`**
  en vez de tocarla.
- Si un tiquet ya está resuelto en el montaje de hoy, dilo también: cerrarlo
  vale tanto como aplicarlo, y callarlo no vale nada.
"""


def encargo(slug, fase):
    """La instrucción y los tiquets de esa fase, o `(None, None)` si no hay.

    Devolver `None` **no es un caso raro**: es el modo general, el de componer
    la pieza entera. Los dos modos son legítimos y la diferencia la marca si hay
    o no correcciones suyas esperando en ese paso.
    """
    suyos = [t for t in suyas(slug) if t[2] == fase]
    if not suyos:
        return None, None
    return MODO, [{"id": i, "de": acc, "dice": txt} for i, acc, _f, txt in suyos]


def etapa_de(texto):
    """La etapa que nombra una corrección suya, o `None` si habla de la pieza.

    Los tres nombres que este proyecto usa para lo mismo —`e7`, `etapa 7` y
    `beat 7`—, porque él escribe uno y la máquina escribe otro. `None` no es un
    fallo de lectura: hay correcciones que son de la pieza entera («el abuso del
    glitch en este reel»), y ésas abren todas las etapas.
    """
    import re

    m = re.search(r"(?:e|etapa\s*|beat\s*)(\d{1,2})", (texto or "").lower())
    return int(m.group(1)) if m else None


def alcance(slug, fase):
    """Qué etapas abre un tiquet suyo: `(hay_tiquets, etapas, todas)`.

    `todas` es cierto cuando alguna corrección no nombra etapa — «el abuso del
    glitch en este reel» habla de la pieza entera—. Acotar de menos pierde la
    corrección, que de los dos errores es el caro: uno cuesta mirar una etapa de
    más, el otro cuesta que él la vuelva a pedir.
    """
    _, tiquets = encargo(slug, fase)
    if not tiquets:
        return False, set(), False
    etapas = {e for e in (etapa_de(t["dice"]) for t in tiquets) if e is not None}
    return True, etapas, len(etapas) < len(tiquets)


def modo(prompt, payload, slug, fase):
    """Pone la capa de instrucción sobre el pedido, si hay tiquets de esa fase.

    Devuelve `(prompt, payload)` tocados o tal cual. Vive aquí y no en el
    servicio porque **la segunda capa es del tiquet, no del oficio**: el que
    compone y el que dibuja tienen capacidades distintas y la misma forma de
    recibir un encargo acotado.
    """
    instruccion, tiquets = encargo(slug, fase)
    if not instruccion:
        return prompt, payload
    return prompt + instruccion, {**payload, "modo": "tiquets",
                                  "tiquets": tiquets}


def cerrar(slug, fase, por_que):
    """Cierra como `aplicada` los tiquets de esa fase. Devuelve sus números.

    Lo llama **el paso que los arregló**, y por eso vive aquí: cerrar una
    corrección es parte de atenderla, no un trámite aparte. Sin esto el servicio
    componía, la nota seguía abierta y la línea se paraba otra vez por algo ya
    hecho — y la única salida era un `update` a mano contra la base.
    """
    suyos = [t[0] for t in suyas(slug) if t[2] == fase]
    if not suyos:
        return []
    try:
        cx = basedatos.abrir(BASE)
        cx.executemany(
            "update revision set estado = 'aplicada', regla = ? where id = ?",
            [(por_que[:400], i) for i in suyos])
        cx.commit()
        cx.close()
    except sqlite3.Error:
        return []
    return suyos


def abre(slug, fase, fila):
    """¿Un tiquet suyo vuelve a poner esta etapa en el encargo?

    Una etapa con su tablero ya montado no entraba —el paso sólo preguntaba por
    lo que faltaba—, así que una corrección sobre un tablero existente no
    llegaba nunca a quien podía arreglarlo.
    """
    hay, etapas, todas = alcance(slug, fase)
    return hay and (todas or fila["etapa_orden"] in etapas)
