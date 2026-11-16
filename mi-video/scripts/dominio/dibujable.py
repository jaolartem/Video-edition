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


def sube_tiquets(respuesta) -> list:
    """Los `tiquets` declarados dentro de un tablero, al primer nivel. Los subidos.

    **Se coloca, no se devuelve** (C-612). #784 de reel-18, 20-10: el diseñador
    arregló e8 y escribió `tiquets: [784]` dentro del tablero; `aplicar` sólo lee
    el primer nivel, así que el tiquet siguió abierto con el trabajo hecho y la
    pieza volvió a pararse. Es una llave mal puesta, como `cubre` (C-589), y
    devolverla costaría otra ronda de agente por algo que el código sabe colocar.
    """
    sueltos = [i for t in respuesta.get("tableros") or [] if isinstance(t, dict)
               for x in (t.pop("tiquets", None),
                         (t.get("props") or {}).pop("tiquets", None)) if x
               for i in (x if isinstance(x, list) else [x])]
    if sueltos:
        ya = respuesta.get("tiquets") or []
        respuesta["tiquets"] = list(dict.fromkeys(
            (ya if isinstance(ya, list) else [ya]) + sueltos))
    return sueltos


def puerta(pieza, tableros, respuesta=None):
    """`None` si todo se dibuja; si no, el `Resultado` que lo devuelve.

    Y antes, los tiquets que vengan dentro de un tablero suben a la respuesta
    (`sube_tiquets`, C-612).

    **`cubre` se lee también al lado de `kind`** (C-589). La línea lo mira
    dentro de `props`, y el diseñador lo escribió fuera tres veces el 18 y el
    19-10 (reel-19, reel-20 y reel-22): cada vez el panel contó como tablero a
    pleno sin cara, y volvió una ronda entera por una llave mal puesta. Se mueve
    a `props` aquí, antes de mirar y de guardar.
    """
    if isinstance(respuesta, dict):
        sube_tiquets(respuesta)
    falta = faltas(pieza, tableros)
    return devuelve(pieza, falta) if falta else None


def faltas(pieza, tableros) -> dict:
    """Lo que no se dibuja, por etapa, **sin abrir nada**: la regla a secas.

    La usa la puerta al llegar y la usa quien diseña ANTES de entregar
    (`consulta.py dibujable`, C-648). Reel-22, 21-10: dos vueltas por dos
    cintas de 27 caracteres, y el diseñador escribió que no tenía con qué
    comprobarlo — contaba los caracteres a mano contra `topes`.
    """
    for t in tableros or []:
        if isinstance(t, dict) and t.get("cubre") and "cubre" not in (t.get("props") or {}):
            t["props"] = {**(t.get("props") or {}), "cubre": t.pop("cubre")}
    from dominio.lienzo import Lienzo
    return consulta([], {"cara": cara(pieza), "tableros": tableros,
                         "formato": Lienzo.de_pieza(pieza.slug).formato}) or {}


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
