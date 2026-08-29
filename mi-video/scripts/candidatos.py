"""Emite lo que necesita la selección por IA: etapas del frame y oraciones.

## Por qué existe

Jaime: *«este proceso lo dejamos obligatorio por código e IA al tiempo, es decir
no quiero que siga siendo opcional; los resultados han sido decepcionantes»*.

Los dos lados hacen cosas distintas y ninguno sirve solo:

- **El código garantiza la forma.** Que el candidato sea una **oración
  completa**, que haya uno por etapa, que salgan en el orden de la estructura y
  que ninguna idea se repita. Eso es mecánico y no admite criterio.
- **La IA garantiza el sentido.** Si una oración **dice la idea de la etapa**
  no lo puede decidir un solapamiento de palabras: *«no importa que no sea
  exactamente igual, importa que se mantenga la idea»*. Comparar n-gramas es
  justo lo que fallaba — elegía la frase que repetía las palabras del libreto,
  no la que decía lo mismo.

Este script produce el material para el segundo paso. No elige nada.

    python scripts/candidatos.py            # los seis, a work/candidatos/
    python scripts/candidatos.py --reel 3
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import rutas  # noqa: E402


def para(reel):
    libreto = beats.beats_del_libreto(reel)
    frame = beats.frame_del_reel(reel, libreto)
    toma = rutas.TOMAS[f"reel-{reel:02d}"]
    cands = beats.oraciones(toma)

    return {
        "reel": f"reel-{reel:02d}",
        "estructura": frame["estructura"],
        "mecanismo": frame["mecanismo"],
        # Las etapas EN ORDEN. `idea` es el párrafo del libreto, y entra sólo
        # como descripción de qué tiene que decir esa etapa — no como el texto
        # que hay que encontrar. El libreto es accidental; el módulo es el copy.
        "etapas": [
            {
                "n": i + 1,
                "etapa": b["etapa"],
                "obligatorio": bool(b.get("obligatorio")),
                "idea": libreto[i],
            }
            for i, b in enumerate(frame["beats"])
        ],
        # Oraciones completas de la toma. Todas empiezan en mayúscula y acaban
        # en punto: eso lo garantiza el código y no se negocia.
        "oraciones": [
            {
                "id": j,
                "desde": round(c["a"], 3),
                "hasta": round(c["b"], 3),
                "dur": round(c["b"] - c["a"], 2),
                "aire": c["aire"],
                "texto": c["texto"],
            }
            for j, c in enumerate(cands)
        ],
        # Lo que ya se decidió de oído y no se toca.
        "apertura": frame.get("apertura"),
        "cierre": frame.get("cierre"),
        # Tramos donde Jaime está leyendo. Van con animación, no con plano.
        "leyendo": frame.get("leyendo", []),
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reel", type=int)
    a = ap.parse_args()

    os.makedirs("work/candidatos", exist_ok=True)
    for n in ([a.reel] if a.reel else [1, 2, 3, 4, 5, 6]):
        d = para(n)
        f = f"work/candidatos/reel-{n:02d}.json"
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"reel-{n:02d} · {d['estructura']:26} "
              f"{len(d['etapas'])} etapas · {len(d['oraciones'])} oraciones → {f}")
