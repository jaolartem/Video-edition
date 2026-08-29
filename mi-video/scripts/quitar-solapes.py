"""Quita cortes que se solapan con otro dentro del mismo EDL.

Al insertar los cierres de CTA a mano se anadio en el reel 2 el tramo
500,15-515,29 sin quitar los cuatro cortes que ya lo cubrian por trozos, asi que
**el CTA sonaba tres veces**: doce segundos repetidos en una pieza de ochenta y
cuatro.

Dos cortes que se solapan casi nunca son intencionales — lo intencional es
repetir una FRASE en dos sitios distintos de la pieza, no reproducir el mismo
tramo del bruto dos veces seguidas. Se conserva el mas largo, que es el que
lleva la frase entera.

Ojo con el orden: el de `segmentos` es el de la linea de tiempo, no el del
bruto (reel 5, apertura en frio). Aqui no se reordena nada.
"""
import json
import sys


def solapan(a, b):
    return min(a[1], b[1]) - max(a[0], b[0]) > 0.15


def limpiar(reel):
    f = f"ads/{reel}/edl-sell.json"
    d = json.load(open(f, encoding="utf-8"))
    segs = [list(s) for s in d["segmentos"]]
    # Se recorre de mas largo a mas corto: el largo se queda, los que caen
    # dentro se van.
    orden = sorted(range(len(segs)), key=lambda i: -(segs[i][1] - segs[i][0]))
    fuera = set()
    for k, i in enumerate(orden):
        if i in fuera:
            continue
        for j in orden[k + 1:]:
            if j not in fuera and solapan(segs[i], segs[j]):
                fuera.add(j)
    if not fuera:
        print(f"{reel}: sin solapes")
        return 0
    quitados = [segs[i] for i in sorted(fuera)]
    d["segmentos"] = [s for i, s in enumerate(segs) if i not in fuera]
    d["detalle"] = [u for u in d["detalle"]
                    if any(a - 0.05 <= u["start"] <= b + 0.05
                           for a, b in d["segmentos"])]
    d["duracion_montada_s"] = round(sum(b - a for a, b in d["segmentos"]), 2)
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{reel}: fuera {len(fuera)} solapes "
          f"({', '.join(f'{a:.2f}-{b:.2f}' for a, b in quitados)}) "
          f"-> {d['duracion_montada_s']}s")
    return len(fuera)


if __name__ == "__main__":
    total = sum(limpiar(r) for r in sys.argv[1:] or
                [f"reel-{i:02d}" for i in range(1, 7)])
    print(f"\nsolapes eliminados: {total}")
