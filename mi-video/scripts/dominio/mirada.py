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


def _memo(slug):
    ruta = os.path.join("work", "scenes", slug, "mirada.json")
    return ruta, (json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {})


def cuenta(trozos, memo) -> tuple[int, int]:
    """`(de frente, mirados)` en `MUESTRAS` fotogramas repartidos por los trozos
    `[(cinta, desde, hasta)]`, aunque la etapa esté hecha de varios."""
    import rutas

    from .rostro import de_frente

    largo = sum(h - d for _c, d, h in trozos)
    frente = mirados = 0
    for k in range(MUESTRAS):
        pos, punto = largo * (k + 1) / (MUESTRAS + 1), None
        for c, d, h in trozos:
            if pos <= h - d:
                punto = (c, d + pos)
                break
            pos -= h - d
        if punto is None:
            continue
        clave = f"{punto[0]}:{punto[1]:.2f}"
        if clave not in memo:
            memo[clave] = list(de_frente(rutas.cinta(punto[0]), [punto[1]]))
        frente, mirados = frente + memo[clave][0], mirados + memo[clave][1]
    return frente, mirados


def en_dossier(slug, fila, toma, tramos) -> dict:
    """La fila del dossier con la mirada medida, si la etapa lleva VIDEO de Jaime:
    la de su toma y la de cada candidata.

    Sin esto, quien elige la toma de una etapa «a cámara» elegía a ciegas: el
    pedido no traía ni hoja ni fotogramas, así que la puerta la devolvía por la
    mirada y el compositor volvía a escoger sin ver (C-685). Medirlo es código.
    """
    if not fila.get("video_decidido"):
        return fila
    ruta, memo = _memo(slug)

    def _dice(trozos):
        k, n = cuenta(trozos, memo)
        return f"{k} de {n} fotogramas de frente" if n else None

    fila["mirada"] = _dice([(toma, d, h) for d, h in tramos])
    for c in fila.get("candidatas") or []:
        c["mirada"] = _dice([(c["toma"], c["desde"], c["hasta"])])
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(memo, fh)
    return fila


def reparos(slug) -> list:
    """Las etapas que van a cámara y en su toma no se le ven los ojos de frente."""
    plan = os.path.join("work", "scenes", slug, "plan-full.json")
    etapas = _a_camara(slug)
    if not etapas or not os.path.exists(plan):
        return []
    with open(plan, encoding="utf-8") as f:
        escenas = [e for e in json.load(f).get("escenas") or []
                   if e.get("beat") in etapas and not e.get("angulo")]
    ruta, memo = _memo(slug)
    fuera = []
    for beat in sorted({e["beat"] for e in escenas}):
        frente, mirados = cuenta([(e["fuente"], e["origen_desde"], e["origen_hasta"])
                                  for e in escenas if e["beat"] == beat], memo)
        if mirados and frente / mirados < BASTA:
            fuera.append(f"{REGLA} b{beat}: va a cámara y en la toma no se le ven"
                         f" los ojos de frente ({frente} de {mirados} fotogramas)"
                         " — otra toma que mire a cámara, y si no la hay, panel")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(memo, f)
    return fuera
