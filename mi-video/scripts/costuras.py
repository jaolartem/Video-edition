"""Las costuras: buscar el mejor corte y, si no lo hay, marcarla para disimular.

Regla de Jaime, y trae las dos mitades: *«busca los mejores cortes posibles, y si
no, utiliza la transición del glitch, con ésa se disimula — glitch y cambio de
cámara, más cerca o más lejos»*.

Y antes había dado el diagnóstico: *«si notas que los cortes de tono o de ritmo
son muy profundos, sabes que se va a notar en vídeo, por lo que puedes escoger o
buscar otro fragmento que puntúe mejor»*.

## Por qué el glitch no puede ir en todas

Iba en todas. Y una máscara que se pone siempre deja de ser máscara: se convierte
en el efecto, y entonces el corte limpio y el corte malo se ven igual de raros.
Jaime ya lo había acotado en su día — *«el glitch para cambios de escena o en
cortes de escena que quedan mal»*—: **donde quedan mal**, no en todas.

## El orden, que importa

1. **Mover el corte.** Casi siempre hay una frontera de palabra a medio segundo
   que empalma mejor. Es gratis y no se nota nada, porque no se añade: se elige.
2. **Si no la hay, disimular.** Glitch **y cambio de encuadre a la vez** — el ojo
   perdona un salto de voz cuando el plano también cambió, porque le da un
   motivo. Uno solo de los dos no basta.

## Qué es una costura dura

Sólo cuenta donde **se quitaron palabras**. Si entre un trozo y el siguiente sólo
se fue silencio, la voz continúa: el cambio de tono es prosodia, no empalme.

Los umbrales están medidos sobre estas seis cintas y son los de percepción, no de
manual: por debajo de `TONO_OK` semitonos y `RITMO_OK` palabras por segundo, la
unión no se oye.

    python scripts/costuras.py            # el informe de las seis
    python scripts/costuras.py --arreglar 2   # mueve lo que se pueda y marca el resto
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import registro  # noqa: E402
import transcribir  # noqa: E402

# Por debajo de esto la costura no se oye. Medido sobre el lote.
TONO_OK = 2.5
RITMO_OK = 3.0
# Cuánto se puede mover un extremo buscando un empalme mejor. Medio segundo es
# una palabra corta: más allá se empieza a cambiar lo que se dice.
MARGEN = 0.6


def _pal(toma, cache):
    if toma not in cache:
        try:
            cache[toma] = transcribir.exigir(toma)["segmentos"]
        except SystemExit:
            cache[toma] = []
    return cache[toma]


def dura(salto):
    """¿Se va a oír esta unión?"""
    return (salto.get("tono") or 0) > TONO_OK or (salto.get("ritmo") or 0) > RITMO_OK


def medir(edl, i, cache):
    """El salto de la costura entre el segmento i y el i+1, o None si no es empalme."""
    (a0, b0), (a1, _) = edl["segmentos"][i], edl["segmentos"][i + 1]
    t0 = edl["detalle"][i].get("toma")
    t1 = edl["detalle"][i + 1].get("toma")
    if t0 != t1:
        # Cambio de cinta: el plano cambia entero, no hay costura que disimular.
        return None
    ws = _pal(t0, cache)
    # Sólo es empalme si entre los dos trozos había palabras.
    if not [w for w in ws if b0 <= w["start"] and w["end"] <= a1]:
        return None
    return beats.salto(t0, b0, t1, a1, ws)


def mejor(edl, i, cache):
    """Busca una frontera de palabra cercana que empalme mejor.

    Se prueban los finales de palabra dentro de `MARGEN` antes de `b0` y los
    comienzos dentro de `MARGEN` después de `a1`. **No se inventa un corte a
    mitad de palabra**: sólo se eligen fronteras que ya existen.

    Devuelve `(b0, a1, salto)` de la mejor combinación, que puede ser la actual.
    """
    (a0, b0), (a1, b1) = edl["segmentos"][i], edl["segmentos"][i + 1]
    t0 = edl["detalle"][i].get("toma")
    ws = _pal(t0, cache)
    finales = [b0] + [w["end"] for w in ws
                      if b0 - MARGEN <= w["end"] <= b0 and w["end"] - a0 > 0.8]
    inicios = [a1] + [w["start"] for w in ws
                      if a1 <= w["start"] <= a1 + MARGEN and b1 - w["start"] > 0.8]
    # **Mover el corte no puede costar voz.** Jaime, sobre el objetivo de todo
    # esto: *«el punto es transmitir mas emocion»*. Un optimizador que solo
    # minimiza el salto acaba eligiendo el trozo mas plano, porque lo plano
    # empalma con todo — y eso es exactamente lo contrario de lo que la pieza
    # necesita.
    #
    # Asi que la entrega es una **restriccion**, no un termino mas: una
    # alternativa que baje la expresividad por debajo de la actual se descarta
    # aunque empalme perfecto. Si ninguna la respeta, la costura se disimula con
    # glitch — mejor un corte tapado que una entrega aplanada.
    voz0 = (float(beats.expresividad(t0, a0, b0))
            + float(beats.expresividad(t0, a1, b1))) / 2
    coste = None
    elegido = (b0, a1, None)
    for f in sorted(set(round(x, 3) for x in finales)):
        for n in sorted(set(round(x, 3) for x in inicios)):
            if n <= f:
                continue
            voz = (float(beats.expresividad(t0, a0, f))
                   + float(beats.expresividad(t0, n, b1))) / 2
            if voz < voz0 - 0.15:          # pierde entrega: no compensa
                continue
            s = beats.salto(t0, f, t0, n, ws)
            c = (s.get("tono") or 0) / TONO_OK + (s.get("ritmo") or 0) / RITMO_OK
            if coste is None or c < coste:
                coste, elegido = c, (f, n, s)
    return elegido


def arreglar(slug, ver=False):
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return
    edl = json.load(open(ruta, encoding="utf-8"))
    cache = {}
    movidas, duras, total = 0, [], 0
    for i in range(len(edl["segmentos"]) - 1):
        s = medir(edl, i, cache)
        if s is None:
            continue
        total += 1
        if not dura(s):
            continue
        f, n, s2 = mejor(edl, i, cache)
        if s2 and not dura(s2):
            if not ver:
                edl["segmentos"][i][1] = f
                edl["segmentos"][i + 1][0] = n
                edl["detalle"][i]["end"] = f
                edl["detalle"][i + 1]["start"] = n
            movidas += 1
            print(f"  {slug} costura {i}: movida — tono {s['tono']}→{s2['tono']}"
                  f" · ritmo {s['ritmo']}→{s2['ritmo']}")
        else:
            duras.append(i)
    # **Lo que no tuvo arreglo se marca para disimular**, y el spec pone ahi el
    # glitch y el cambio de encuadre. Los dos juntos: el ojo perdona un salto de
    # voz cuando el plano tambien cambio, porque le da un motivo.
    if not ver:
        edl["costuras_duras"] = duras
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if duras:
            registro.nota("costuras", "costuras que se disimulan",
                          detalle=f"{slug}: {len(duras)} de {total}")
    print(f"{slug}: {total} empalmes · {movidas} movidas · {len(duras)} a disimular")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true")
    a = ap.parse_args()
    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        arreglar(f"reel-{n:02d}", ver=a.ver)


if __name__ == "__main__":
    main()
