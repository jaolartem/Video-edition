"""Los tramos leídos de cada pieza, y qué los cubre.

Instrucción de Jaime (T-01): *«si en el audio se está leyendo, ese tramo va
cubierto con tablero: la cara no aparece en cámara limpia mientras se lee»*. Y
el diagnóstico: *«no es un error de edición ni una toma inservible. Es que el
compositor no tenía criterio escrito sobre qué hacer con los tramos leídos»*.

Esto no decide nada: **mide**. Pone al lado, para cada tramo leído, lo que dice
el EDL montado y lo que decide hoy la regla, que es lo único que prueba si el
cambio sirvió. El umbral y la medida ya existían —`seleccionar.py :: literal()`
compara la toma con el libreto por secuencias de cuatro palabras, y `trato.py ::
LEIDA` pone el corte en 0,60— así que aquí no se mide nada nuevo.

    python scripts/lectura.py            # las piezas con EDL
    python scripts/lectura.py --detalle  # tramo a tramo
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trato as trato_mod  # noqa: E402

#: Los caminos que cubren la cara. Uno, y es el tablero. Ver `lectura.mjs`.
CUBRE = {"tablero"}


def tramos(ruta):
    """Los segmentos leídos de un EDL, con su trato de hoy y el que toca.

    `desde_s` no viaja en el detalle —es el reloj del montaje, no el de la
    cinta— así que la portada no se deduce: se toma la que el EDL ya marcó. Es
    una decisión mecánica que no se renegocia aquí.
    """
    edl = json.load(open(ruta, encoding="utf-8"))
    slug = os.path.basename(os.path.dirname(ruta))
    out = []
    for d in edl.get("detalle") or []:
        lit = d.get("literal")
        if lit is None or lit < trato_mod.LEIDA:
            continue
        nivel, figura, _ = trato_mod.densidad(slug, d["beat"])
        ahora, porque = trato_mod.decidir(
            desde_s=0.0 if d.get("trato") == "portada" else 99.0,
            dura_s=(d.get("end") or 0) - (d.get("start") or 0),
            parrafo="", texto=d.get("texto") or "", literal=lit,
            voz_st=d.get("voz_st"), nivel=nivel, figura=figura,
            decidido=trato_mod.decidido(slug, d["beat"]))
        out.append({"slug": slug, "beat": d["beat"], "literal": lit,
                    "antes": d.get("trato"), "ahora": ahora, "porque": porque})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detalle", action="store_true")
    a = ap.parse_args()

    # **La unidad es el beat, no el corte.** `depurar.py` parte una etapa en
    # varios trozos al quitar el aire y todos heredan el mismo detalle, asi que
    # contando segmentos el mismo tramo leido sale dos y tres veces. Es la misma
    # razon por la que `reels-spec.mjs` agrupa por beat antes de componer.
    vistos, filas = set(), []
    for ruta in sorted(glob.glob(os.path.join("ads", "reel-*", "edl-sell.json"))):
        for f in tramos(ruta):
            if (f["slug"], f["beat"]) in vistos:
                continue
            vistos.add((f["slug"], f["beat"]))
            filas.append(f)

    antes = [f for f in filas if f["antes"] not in CUBRE]
    ahora = [f for f in filas if f["ahora"] not in CUBRE]
    if a.detalle:
        for f in filas:
            marca = "" if f["ahora"] in CUBRE else "   <-- sigue sin cubrir"
            print(f"  {f['slug']} b{f['beat']:<2} lee al {f['literal']:.0%}"
                  f"  {str(f['antes']):<12} -> {f['ahora']:<12}{marca}")
            print(f"      {f['porque']}")
    print(f"\nlectura: {len(filas)} tramos leidos (>= {trato_mod.LEIDA:.0%} de"
          f" secuencia literal)")
    print(f"  sin tablero encima, como estan montados : {len(antes)}")
    print(f"  sin tablero encima, con la regla de hoy : {len(ahora)}")
    if ahora:
        # La portada es el unico caso que la regla no cubre a proposito: el
        # gancho nunca es un tablero y el remedio es elegir otra apertura.
        for f in ahora:
            print(f"   · {f['slug']} b{f['beat']}: {f['porque']}")


if __name__ == "__main__":
    main()
