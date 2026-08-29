"""Corrige la SALIDA de un plan para que el gancho cierre la frase.

Un gancho que corta a mitad de idea no se publica. `revisar-cortes.py` dice cual
corta; esto lo mueve, y **recorta al tramo de habla** para no reintroducir el
silencio que se habia quitado (el error que costo 6–13 s por reel).
"""
import argparse
import json


def main(plan_path, tk, nueva_salida):
    plan = json.load(open(plan_path, encoding="utf-8"))
    tramos = json.load(open(f"work/cuts/{tk}.json", encoding="utf-8"))["segmentos"]
    esc = plan["escenas"]
    ult = esc[-1]

    # La salida se pega al final del tramo de habla que la contiene: mas alla
    # solo hay silencio, y meterlo es exactamente lo que hay que evitar.
    fin = nueva_salida
    for a, b in tramos:
        if a <= nueva_salida <= b:
            fin = min(nueva_salida, b)
            break
    else:
        # Cae en silencio: retrocede al final del ultimo tramo con voz.
        previos = [b for a, b in tramos if b <= nueva_salida]
        if previos:
            fin = max(previos)

    antes = ult["origen_hasta"]
    ult["origen_hasta"] = round(fin, 3)
    ult["duracion"] = round(ult["origen_hasta"] - ult["origen_desde"], 3)
    plan["gancho_s"] = round(sum(e["duracion"] for e in esc), 3)
    json.dump(plan, open(plan_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"{plan_path}: salida {antes:.2f} -> {ult['origen_hasta']:.2f} "
          f"(+{ult['origen_hasta']-antes:.2f}s)  gancho {plan['gancho_s']:.2f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--toma", required=True)
    ap.add_argument("--salida", type=float, required=True)
    a = ap.parse_args()
    main(a.plan, a.toma, a.salida)
