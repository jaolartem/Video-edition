"""El corte, escrito donde el montaje lo lee: `ads/<slug>/edl-sell.json`.

Se **conserva** del EDL anterior todo lo que no sale de la selección —pilar,
estructura, mecanismo, la fecha declarada de la oferta— y se rehace lo que sí:
los cortes, el detalle por etapa y las duraciones. Así cambiar de selección no
borra un dato de la oferta que nadie ha vuelto a decidir.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

import beats  # noqa: E402
import trato as trato_mod  # noqa: E402

#: Las etapas de cierre que declara el frame. Las zonas van por **función de la
#: etapa y no por reloj**: el gancho es el primer beat y el CTA empieza en la
#: primera etapa de cierre. Vive en `dominio/libreto.py`, que corta por ella a
#: las piezas derivadas (C-388).
from dominio.libreto import CIERRE  # noqa: E402

#: Lo que describe a UN EDL concreto y **no se hereda al escribir otro**.
#: Arrastrarlas hacía que `depurar` se saltara una selección recién hecha y que
#: `revision` se saltara todos los cortes de Jaime creyéndolos ya aplicados: la
#: corrección se perdía en silencio, que es la peor forma de perderse.
DE_LA_OPERACION = ("depurado", "depurado_n", "notas_aplicadas", "revision_final")


def _sin_toma(s0, etapa, oblig, libreto, v=None) -> dict:
    """La etapa que va con tarjeta, y por qué. Si lee y viene plana, su propio
    texto es el copy del tablero: por ser exacto dice lo que el libreto quería."""
    fila = {"beat": s0 + 1, "etapa": etapa, "obligatorio": oblig,
            "libreto": (libreto[s0] if s0 < len(libreto) else "")[:400]}
    if v is not None:
        fila.update({"motivo": "lectura plana", "literal": v.lectura,
                     "voz_st": v.voz_st, "copy": v.texto[:400]})
    return fila


def escribir(slug: str, plan, ventanas, libreto, frame) -> tuple[str, float]:
    """Escribe el EDL desde el reparto. Devuelve `(ruta, segundos de voz)`."""
    ruta = os.path.join("ads", slug, "edl-sell.json")
    base = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}

    segs, det, sin_toma, fuentes = [], [], [], []
    # Segundo en que empieza cada segmento en la SALIDA, para saber si cae en el
    # gancho.
    voz_acum = 0.0
    for s0, k in enumerate(plan):
        beat = frame["beats"][s0] if s0 < len(frame["beats"]) else {}
        etapa = beat.get("etapa") or ""
        oblig = bool(beat.get("obligatorio"))
        if k is None:
            sin_toma.append(_sin_toma(s0, etapa, oblig, libreto))
            continue
        v = ventanas[k]
        if v.a_tablero:
            sin_toma.append(_sin_toma(s0, etapa, oblig, libreto, v))
            continue
        parrafo = libreto[s0] if s0 < len(libreto) else ""
        cubre, dice = v.det.get(s0, (0.0, 0))
        lit = v.lee(parrafo)
        # **Cuánto se podía cubrir de esta etapa como mucho.** Sin este número,
        # la cobertura sola mide LITERALIDAD contra el párrafo del libreto: si el
        # párrafo es largo, decir sólo lo esencial puntúa bajo aunque cumpla la
        # etapa. Jaime: *«la idea no es tomar el libreto literal, es tomar la
        # intención comunicativa de cada parte»*.
        mejor = max((w.det[s0][0] for w in ventanas if s0 in w.det), default=cubre)
        # El tratamiento se DECIDE con lo medido, no se declara a mano.
        niv, fig, _pq = trato_mod.densidad(slug, s0 + 1)
        tr, porque = trato_mod.decidir(
            desde_s=round(voz_acum, 2), dura_s=v.dura, parrafo=parrafo,
            texto=v.texto, literal=lit, voz_st=v.voz_st, nivel=niv, figura=fig,
            # Lo que el LLM decidió mirando la pieza entera manda sobre la
            # heurística: la necesidad del video no se ve desde un segmento.
            decidido=trato_mod.decidido(slug, s0 + 1))
        voz_acum += v.dura / beats.VELOCIDAD
        segs.append([v.a, v.b])
        fuentes.append(v.toma)
        det.append({"start": v.a, "end": v.b, "beat": s0 + 1, "etapa": etapa,
                    "obligatorio": oblig, "cobertura": round(float(cubre), 3),
                    "dice": int(dice), "cubre_max": round(float(mejor), 3),
                    "de_jaime": v.de_jaime or None, "toma": v.toma,
                    "literal": round(lit, 3), "voz_st": v.voz_st,
                    "trato": tr, "trato_porque": porque,
                    "densidad": niv, "figura": fig, "texto": v.texto})

    voz = sum(b - a for a, b in segs)
    # El aire que se quitó cuenta el de lo que **entra en la pieza**: sumar el de
    # una etapa que se fue a tablero es declarar un ahorro que no se hizo.
    aire = sum(ventanas[k].aire for k in plan
               if k is not None and not ventanas[k].a_tablero)
    cta_i = [i for i, d in enumerate(det)
             if any(c in (d["etapa"] or "").lower() for c in CIERRE)]
    corte = min(cta_i) if cta_i else len(det)
    zonas = dict(base.get("zonas") or {})
    zonas.update({
        "gancho_s": round(det[0]["end"] - det[0]["start"], 2) if det else 0,
        "cuerpo_s": round(sum(d["end"] - d["start"] for d in det[1:corte]), 2),
        "cta_s": round(sum(d["end"] - d["start"] for d in det[corte:]), 2),
    })

    out = dict(base)
    out.update({
        # El pilar lo declara la pieza (C-388): un reel derivado es EDUCATE.
        "pilar": frame.get("pilar", base.get("pilar", "SELL")),
        "estructura": frame.get("estructura", base.get("estructura")),
        "mecanismo": frame.get("mecanismo", base.get("mecanismo")),
        "zonas": zonas,
        "enunciados": len(segs),
        "duracion_montada_s": round(voz, 2),
        "aire_muerto_eliminado_s": round(aire, 2),
        "segmentos": segs,
        # **De qué grabación sale cada corte.** Un video no tiene por qué salir
        # de una sola cinta: Jaime regraba, y a veces graba la última parte de un
        # video en otra sesión. Si todos coinciden esto es redundante y no
        # estorba; si no, es lo único que permite cortar.
        "fuentes": fuentes,
        "detalle": det,
        "sin_toma": sin_toma,
    })
    out["revision"] = _revision(base, segs)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    json.dump(out, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return ruta, voz


def _revision(base: dict, segs) -> dict:
    """Lo que este EDL declara de sí mismo.

    **Las marcas de operacion NO se heredan**: describen lo que se le hizo a UN
    EDL concreto, y aquí se está escribiendo otro.
    """
    rev = dict(base.get("revision") or {})
    for marca in DE_LA_OPERACION:
        rev.pop(marca, None)
    rev["montaje"] = ("Por etapas del frame: la seccion la marca el guion y los "
                      "extremos la pausa medida. Ver scripts/seleccionar.py "
                      "(C-55) sobre el transcript de varias pasadas (C-54).")
    if segs != sorted(segs):
        # Aprendizaje 35: **cronológico no es montado**. Ya rompió tres
        # herramientas que asumían orden de cinta, así que el dato lo dice por sí
        # mismo en vez de esperar a que cada una se entere.
        rev["orden"] = ("Los segmentos van en orden de MONTAJE, no de cinta:"
                        " este reparto usa tomas fuera de orden porque en la"
                        " cinta las etapas finales se grabaron antes.")
    rev["no_redundante"] = ("podar_dentro + limpiar_costura + una_sola_vez "
                            "(C-58): nada se dice dos veces.")
    return rev
