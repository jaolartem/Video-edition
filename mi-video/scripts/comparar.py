"""Compara dos corridas de transcripcion sin tomar ninguna por verdad.

Correccion de Jaime, y es de metodo: *«armonizar dos procesos diferentes de
origen es ilogico porque las referencias en uno son especulativas y en otro son
relacionales; o la unidad basica de comparacion no es la misma, no vas a poder
comparar»*.

De ahi salen las dos mitades de este informe, y la separacion importa:

1. **Medidas relacionales, para las seis cintas.** Estan definidas igual en las
   dos corridas y **no necesitan una verdad**: cuanto se contradice cada
   transcripcion consigo misma. Tramos recuperados, acuerdo entre pasadas,
   tramos dudosos, palabras estiradas. Eso si se puede comparar.

2. **Diff de texto, solo donde el «antes» viene de UN proceso.** Tres de los
   seis llevaban afinado encima (11, 9 y 6 ventanas) y tres no. Diffear los seis
   mezclaria dos origenes y daria un numero, no un resultado. El propio fichero
   dice de donde viene —`modelo`, `paso`, `pasadas`, `afinado`— asi que el
   conjunto valido se elige solo.

    python scripts/comparar.py F:/tmp-video/antes-4p
"""
import difflib
import glob
import json
import os
import sys


def leer(p):
    d = json.load(open(p, encoding="utf-8"))
    tr = [m for m in d.get("tramos", []) if m.get("texto")]
    med = [m["acuerdo"] for m in tr if m.get("acuerdo") is not None]
    return {
        "palabras": len(d.get("segmentos", [])),
        "tramos": len(tr),
        "acuerdo": (sum(med) / len(med)) if med else None,
        "dudosos": sum(1 for x in med if x < 0.6),
        "estiradas": sum(w.get("larga", 0) for w in d.get("segmentos", [])),
        "pasadas": d.get("pasadas"),
        "afinado": len(d.get("afinado", [])),
        "texto": " ".join(w["text"].strip() for w in d.get("segmentos", [])),
    }


def main():
    antes_dir = sys.argv[1] if len(sys.argv) > 1 else "F:/tmp-video/antes-4p"
    print("MEDIDAS RELACIONALES (las dos corridas, misma definicion)")
    print(f"  {'cinta':<16} {'palabras':>16} {'tramos':>13} {'acuerdo':>13}"
          f" {'dudosos':>11} {'estiradas':>11}")
    limpias = []
    for pa in sorted(glob.glob(os.path.join(antes_dir, "2026*.json"))):
        toma = os.path.basename(pa).replace(".json", "")
        pb = f"work/transcripts/{toma}.json"
        if not os.path.exists(pb):
            continue
        a, b = leer(pa), leer(pb)
        f = lambda x, y, d=0: (f"{x:.{d}f}->{y:.{d}f}" if isinstance(x, float)
                               else f"{x}->{y}")
        ac = ("  -" if a["acuerdo"] is None or b["acuerdo"] is None
              else f"{a['acuerdo']:.2f}->{b['acuerdo']:.2f}")
        print(f"  {toma:<16} {f(a['palabras'], b['palabras']):>16}"
              f" {f(a['tramos'], b['tramos']):>13} {ac:>13}"
              f" {f(a['dudosos'], b['dudosos']):>11}"
              f" {f(a['estiradas'], b['estiradas']):>11}")
        if not a["afinado"]:
            limpias.append((toma, a, b))

    print(f"\nDIFF DE TEXTO — solo las {len(limpias)} cintas cuyo «antes» viene de"
          f" un solo proceso")
    print("  (las que llevaban afinado encima quedan fuera: mezclar dos origenes"
          " no da un resultado)")
    for toma, a, b in limpias:
        pa, pb = a["texto"].split(), b["texto"].split()
        sm = difflib.SequenceMatcher(None, pa, pb)
        cambios = [o for o in sm.get_opcodes() if o[0] != "equal"]
        gana = sum(j2 - j1 for t, _, _, j1, j2 in cambios if t in ("insert", "replace"))
        pierde = sum(i2 - i1 for t, i1, i2, _, _ in cambios if t in ("delete", "replace"))
        print(f"  {toma}: {sm.ratio():.4f} igual · {len(cambios)} bloques ·"
              f" +{gana} palabras / -{pierde}")
        for t, i1, i2, j1, j2 in cambios[:6]:
            print(f"      {t:<8} {' '.join(pa[i1:i2])[:40]:<40} -> {' '.join(pb[j1:j2])[:40]}")


if __name__ == "__main__":
    main()
