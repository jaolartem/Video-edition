"""La redundancia, que la decide el modelo de lenguaje y no Python.

Regla de Jaime, y cierra el diseño de este paso:

    *«La redundancia no es algo que se pueda inferir con código fácilmente.
    Necesitaríamos un modelo probabilístico de predicción de lenguaje, que es
    exactamente lo que tenemos contigo. No está en la capacidad de Python ni de
    ninguna de sus dependencias.»*

Está comprobado y costó tres intentos. Un trigrama no ve que «de cada 100
dólares que él» y «100 dólares que él recibe él» son la misma frase empezada dos
veces: **no comparten ningún trigrama**. Ni que «pero que el sistema se quedó» y
«pero que el sistema capturó» dicen lo mismo con otro verbo. Eso es comprender,
no comparar cadenas, y el último intento —`partir_por_repeticion`— dejó la pieza
más larga que antes.

## El reparto, y por qué es limpio

**Se queda en `depurar.py`** lo que de verdad es mecánico y se mide: el aire —un
hueco sin una sola palabra— y el tartamudeo —la misma palabra pegada a sí misma.

**Viene aquí** todo lo que necesita entender la frase: la misma idea dicha dos
veces con otras palabras, el arranque abortado, la cola que no cierra, el dato
repetido.

## Cómo funciona

Este script no decide nada. Prepara el **dossier** —el texto de la pieza montada,
por etapas, con la entrega medida al lado— y carga de vuelta los cortes que el
modelo devuelve, que entran en `revision` como notas `cortar` **ancladas al
texto**. Anclarlas al texto y no al segundo es lo que hace que sobrevivan a que
la pieza se vuelva a montar (C-79).

    python scripts/redundancia.py 2               # el dossier del reel 2
    python scripts/redundancia.py --cargar 2 c.json  # los cortes que devolvio
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import revision  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

PROMPT = os.path.join(os.path.dirname(__file__), "redundancia.prompt.md")

REGLA = ("la repeticion del bruto es un abanico para elegir, no basura que"
         " recortar: sobra UNA version, la que mas comunique. Reconocerlo es"
         " prediccion de lenguaje, no coincidencia de n-gramas: por eso vive en"
         " el paso de IA y no en Python.")


def dossier(slug, con_voz=True):
    """El texto de la pieza montada, por trozos y en orden, con su entrega.

    Se recorre en **orden de montaje** porque es lo que el espectador oye, y con
    el texto de la cinta —cuatro pasadas— porque es el bueno. Los números de
    entrega van al lado para que la eleccion entre dos versiones no sea a ojo.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache, out, t = {}, [], 0.0
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        toma = det.get("toma") or rutas.TOMAS.get(slug)
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        ws = [w["text"] for w in cache[toma]
              if rango[0] - 0.02 <= w["start"] and w["end"] <= rango[1] + 0.02]
        dur = (rango[1] - rango[0]) / beats.VELOCIDAD
        if ws:
            fila = {"en": round(t, 1), "beat": det.get("beat"),
                    "etapa": det.get("etapa"), "texto": " ".join(ws)}
            if con_voz and rango[1] - rango[0] > 0.6:
                try:
                    fila["voz"] = round(
                        float(beats.expresividad(toma, rango[0], rango[1])), 2)
                    fila["tono"] = round(
                        beats.cambio_de_tono(toma, rango[0], rango[1]), 1)
                except Exception:                  # noqa: BLE001
                    pass
            out.append(fila)
        t += dur
    return out


def cargar(slug, cortes, pasada=1):
    """Mete los cortes que devolvio el modelo como notas de revision.

    **No se aplican aqui.** Entran en `revision` con su ancla y su porque, y las
    aplica `revision.py` — que es quien sabe re-aplicarlas cuando la pieza se
    vuelve a montar. Un paso que corta por su cuenta se pisa con el otro.
    """
    n = 0
    for c in cortes:
        ancla = (c.get("ancla") or "").strip()
        if not ancla:
            continue
        revision.anotar(slug, "cortar", None, None,
                        c.get("por_que") or "redundancia",
                        regla=REGLA, pasada=pasada, ancla=ancla)
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--cargar", metavar="JSON",
                    help="fichero con los cortes que devolvio el modelo")
    a = ap.parse_args()
    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        slug = f"reel-{n:02d}"
        if a.cargar:
            cortes = json.load(open(a.cargar, encoding="utf-8"))
            print(f"{slug}: {cargar(slug, cortes)} corte(s) anotados")
            continue
        filas = dossier(slug)
        if not filas:
            continue
        print(f"\n===== {slug} — el prompt esta en {PROMPT} =====")
        for f in filas:
            voz = (f"  [voz {f['voz']} · tono {f['tono']}]"
                   if "voz" in f else "")
            print(f"{f['en']:>6.1f}  b{f['beat']}{voz}\n        {f['texto']}")


if __name__ == "__main__":
    main()
