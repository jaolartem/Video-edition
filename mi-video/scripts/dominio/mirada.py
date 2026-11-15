"""**A cámara es con los ojos de frente.** Una regla de plano más (C-683).

Jaime, 14-11-2026: *«cuando dice que estoy yo en cámara, siempre tengo que estar
mostrando los ojos y hablando directamente a la cámara; eso tiene que ser
fundamental. Si no está eso, entonces se pone el panel. Si no hay una toma buena
conmigo cara, entonces buscas una toma que esté mejor»*. Y la otra mitad: *«lo
que está grabado mirando el computador es porque no va en cámara»*.

Se mide, no se supone: en cada etapa que va a cámara —su descripción dice plano
`en cuadro` o `cerrado` y no lleva nada encima— se miran tres fotogramas de la
cinta y se cuenta en cuántos se le ve de frente (`rostro.de_frente`). Si no
llega a la mitad, sale el reparo; `servicios/verificar.py` lo devuelve a
`revalidado`, que es quien elige otra toma, y si no la hay, el panel.

La medida se guarda en `work/scenes/<slug>/mirada.json` por cinta y segundo: la
puerta pasa muchas veces y un fotograma ya mirado no cambia.
"""
from __future__ import annotations

import json
import os

#: El prefijo del motivo: lo busca `servicios/verificar.py` para devolverlo.
REGLA = "regla de mirada ·"
#: Fotogramas por etapa, y la parte de ellos que tiene que ser de frente.
MUESTRAS = 3
BASTA = 0.5
A_CAMARA = ("en cuadro", "cerrado")


def _a_camara(slug) -> set:
    """Las etapas que van a cámara sin nada encima, según su descripción."""
    try:
        import basedatos

        con = basedatos.abrir("ads/decisiones.db")
        filas = con.execute(
            "select etapa_orden from escena_desc where video_slug = ?"
            " and plano in (?, ?) and componente is null", (slug, *A_CAMARA))
        fuera = {r[0] for r in filas}
        con.close()
        return fuera
    except Exception:                              # noqa: BLE001
        return set()


def reparos(slug) -> list:
    """Las etapas que van a cámara y en su toma no se le ven los ojos de frente."""
    plan = os.path.join("work", "scenes", slug, "plan-full.json")
    etapas = _a_camara(slug)
    if not etapas or not os.path.exists(plan):
        return []
    import rutas

    from .rostro import de_frente

    with open(plan, encoding="utf-8") as f:
        escenas = [e for e in json.load(f).get("escenas") or []
                   if e.get("beat") in etapas and not e.get("angulo")]
    guardado = os.path.join("work", "scenes", slug, "mirada.json")
    memo = json.load(open(guardado, encoding="utf-8")) if os.path.exists(guardado) else {}
    fuera = []
    for beat in sorted({e["beat"] for e in escenas}):
        suyas = [e for e in escenas if e["beat"] == beat]
        largo = sum(e["origen_hasta"] - e["origen_desde"] for e in suyas)
        frente = mirados = 0
        for k in range(MUESTRAS):
            # Repartidos por la etapa entera, aunque esté hecha de varios trozos.
            pos, t, e = largo * (k + 1) / (MUESTRAS + 1), None, None
            for e in suyas:
                d = e["origen_hasta"] - e["origen_desde"]
                if pos <= d:
                    t = e["origen_desde"] + pos
                    break
                pos -= d
            if t is None:
                continue
            clave = f"{e['fuente']}:{t:.2f}"
            if clave not in memo:
                memo[clave] = list(de_frente(rutas.cinta(e["fuente"]), [t]))
            frente, mirados = frente + memo[clave][0], mirados + memo[clave][1]
        if mirados and frente / mirados < BASTA:
            fuera.append(f"{REGLA} b{beat}: va a cámara y en la toma no se le ven"
                         f" los ojos de frente ({frente} de {mirados} fotogramas)"
                         " — otra toma que mire a cámara, y si no la hay, panel")
    with open(guardado, "w", encoding="utf-8") as f:
        json.dump(memo, f)
    return fuera
