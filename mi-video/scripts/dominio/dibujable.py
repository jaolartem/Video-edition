"""La puerta del diseño, del lado de Python: ¿se puede dibujar? C-562.

La regla vive en `formas.mjs` y la expone `scripts/dibujable.mjs`; esto la
pregunta desde `servicios/disenar.py` cuando llega la respuesta, en vez de
esperar a que el montaje la descubra tres pasos después.
"""
from __future__ import annotations

import json
import subprocess



#: La marca de los tiquets que abre la puerta del diseño (C-562).
NO_SE_DIBUJA = "no se dibuja (al llegar):"


def cara(pieza) -> bool:
    """Si la pieza muestra su cara en todo tablero (T-06)."""
    from dominio.libreto import Libreto
    return Libreto(pieza.n).frame().get("cara") == "siempre"


def consulta(args, entrada=None):
    """Pregunta a `scripts/dibujable.mjs`, que expone la regla de `formas.mjs`."""
    r = subprocess.run(["node", "scripts/dibujable.mjs", *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       input=json.dumps(entrada or {}, ensure_ascii=False))
    try:
        return json.loads(r.stdout or "null")
    except ValueError:
        return None


def devuelve(pieza, faltas: dict):
    """Tiquet por etapa y la respuesta fuera, para que conteste otra vez. Una vez.

    Si la etapa ya volvio una vez por esto, no se insiste aqui: sigue y la para
    el montaje con su tope (C-551), que es donde sube a Jaime.
    """
    import servicio as contrato
    from servicios.base import Resultado

    from . import ticket

    hechas = {t.get("beat") for t in ticket.historia(pieza.slug)
              if (t.get("dijo") or "").startswith(NO_SE_DIBUJA)}
    nuevas = {e: f for e, f in faltas.items() if int(e) not in hechas}
    if not nuevas:
        return None
    for e, f in nuevas.items():
        ticket.abrir(pieza.slug, f"{NO_SE_DIBUJA} e{e}: " + " | ".join(f),
                     etapa=str(e), vuelve_a="disenado")
    contrato._archivar("disenar", pieza.slug, sufijo="no_dibujable",
                       solo_respuesta=True)
    return Resultado(False, motivo="espera diseno -> " + contrato.ruta_pedido(
        "disenar", pieza.slug) + f" (no se dibujan: {sorted(nuevas)})")


def puerta(pieza, tableros):
    """`None` si todo se dibuja; si no, el `Resultado` que lo devuelve.

    **`cubre` se lee también al lado de `kind`** (C-589). La línea lo mira
    dentro de `props`, y el diseñador lo escribió fuera tres veces el 18 y el
    19-10 (reel-19, reel-20 y reel-22): cada vez el panel contó como tablero a
    pleno sin cara, y volvió una ronda entera por una llave mal puesta. Se mueve
    a `props` aquí, antes de mirar y de guardar.
    """
    for t in tableros or []:
        if isinstance(t, dict) and t.get("cubre") and "cubre" not in (t.get("props") or {}):
            t["props"] = {**(t.get("props") or {}), "cubre": t.pop("cubre")}
    faltas = consulta([], {"cara": cara(pieza), "tableros": tableros})
    return devuelve(pieza, faltas) if faltas else None


#: Lo que en el pedido del disenador es igual para todas las piezas (C-564).
TALLER = ('canon', 'canon_escrito', 'laminas', 'estilo', 'antes_de_dibujar', 'sonidos', 'oficio_reel', 'prioridad', 'piezas', 'como_combinar', 'figuras', 'volumenes', 'correccion', 'verse', 'tres_d', 'camara', 'voz', 'composicion', 'topes')


def taller(payload: dict) -> str:
    """Saca el taller del pedido y lo deja una vez en `_comun/`. Su ruta."""
    from .volcado import comun

    return comun("disenar-taller", {k: payload.pop(k) for k in TALLER if k in payload})


def de_la_pieza(pieza) -> dict:
    """Lo que el pedido del disenador dice de su cara en esta pieza."""
    siempre = cara(pieza)
    return {"cara_en_todo_tablero": siempre,
            "con_su_cara_a_pleno": consulta(["--con-su-cara"]) if siempre else None}
