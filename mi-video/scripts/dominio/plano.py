"""**Un plano sostenido**: escenas seguidas que comparten encuadre y fuente.

Regla de Jaime, 25-9-2026, y es dura —no un referente—:

> *«Cuando hay un cambio de escena se debe mantener la nueva escena por al menos
> 5 segundos, y para salir de esa escena se requiere o un tablero o un movimiento
> de cámara. Los cambios abruptos no pueden continuar.»*

## Qué cuenta como cambio de escena, y por qué no es cada corte

En `plan-full.json` cada tramo del montaje es una «escena», así que leído
literal el lote entero incumpliría: reel-14 tiene 16 de 20 por debajo de 5 s, y
la regla de corte de `docs/montaje.md` pide justo lo contrario —objetivo ~3 s—.
No se contradicen: hablan de cosas distintas.

**Un corte dentro del mismo plano no cambia de escena**: es un salto para quitar
una pausa, y el espectador no lo lee como un sitio nuevo. Lo que cambia de
escena es que cambie **el encuadre o la fuente**. Por eso aquí las escenas
seguidas con el mismo par se suman en un bloque, y es el bloque el que tiene que
durar.

Medido con esta definición: reel-10 —la que Jaime aprobó y le gustó— es la
**única con cero bloques por debajo de 5 s**; reel-12 tiene 17 de 21.

## Y la salida

`recorrido` no vale: es un microdesplazamiento de 0,02 que llevan **todas** las
escenas, así que aceptarlo daría por buena cualquier salida. Lo que vale:

- `transicion` distinta de `"corte"` —«filete», «glitch»—,
- un cambio real de escala (`zoom.hasta` se mueve más de 0,05),
- o un tablero en ese beat.
"""
from __future__ import annotations

import json
import os

#: Lo que como mínimo dura un plano nuevo antes de poder salir de él.
MINIMO = 5.0

#: Cuánto tiene que moverse la escala para que cuente como movimiento de cámara.
#: Por debajo de esto es la deriva de siempre, no una decisión.
PASO_ZOOM = 0.05


class Bloque:
    """Un plano sostenido, con lo que hay que saber de él."""

    def __init__(self, beat, encuadre):
        self.beat = beat
        self.encuadre = encuadre
        self.dura = 0.0
        self.sale = False

    def reparo(self) -> str | None:
        """Qué le falta, o `None` si está bien. Se dice uno, no los dos."""
        if self.dura < MINIMO:
            return (f"regla de plano · b{self.beat}: «{self.encuadre}» dura"
                    f" {self.dura:.1f}s y el mínimo es {MINIMO:.0f}")
        if not self.sale:
            return (f"regla de plano · b{self.beat}: se sale de «{self.encuadre}»"
                    f" con un corte a secas — falta tablero o movimiento")
        return None

    def __str__(self):
        return f"[b{self.beat} {self.encuadre} {self.dura:.1f}s]"


def _tableros(slug) -> set:
    """Los beats que llevan tablero. Sin base, ninguno — y entonces sólo cuentan
    la transición y el zoom, que es el caso conservador."""
    try:
        import sqlite3

        import basedatos

        con = basedatos.abrir("ads/decisiones.db")
        con.row_factory = sqlite3.Row
        # **De `escena_desc`, no de `etapa_tablero`.** La primera version leia
        # `etapa_tablero`, que para reel-09 devuelve `set()` — o sea que la pata
        # «o un tablero» de la regla de Jaime **no contaba nunca** y el medidor
        # exigia transicion o zoom siempre. Lo destapo el disenador al medir su
        # propia pieza. Quien sabe que una etapa lleva tablero es su descripcion.
        filas = con.execute(
            "select etapa_orden from escena_desc"
            " where video_slug = ? and componente is not null", (slug,))
        fuera = {r[0] for r in filas}
        con.close()
        return fuera
    except Exception:                              # noqa: BLE001
        return set()


def bloques(slug) -> list:
    """Los planos sostenidos de la pieza, en orden. `[]` si no hay plan."""
    f = os.path.join("work", "scenes", slug, "plan-full.json")
    if not os.path.exists(f):
        return []
    with open(f, encoding="utf-8") as fh:
        escenas = json.load(fh).get("escenas") or []
    tb, fuera, cur, antes = _tableros(slug), [], None, None
    for e in escenas:
        clave = (e.get("encuadre"), str(e.get("fuente"))[:40])
        z = (e.get("zoom") or {}).get("hasta")
        sale = (str(e.get("transicion")) != "corte"
                or (antes is not None and z is not None
                    and abs(z - antes) > PASO_ZOOM)
                or e.get("beat") in tb)
        if cur is None or cur._clave != clave:
            cur = Bloque(e.get("beat"), e.get("encuadre"))
            cur._clave = clave
            fuera.append(cur)
        cur.dura += float(e.get("duracion")
                          or (e["origen_hasta"] - e["origen_desde"]))
        cur.sale = cur.sale or sale
        antes = z
    return fuera


def reparos(slug) -> list:
    """Lo que hay que arreglar de los planos de esa pieza."""
    return [r for r in (b.reparo() for b in bloques(slug)) if r]
