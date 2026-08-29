"""Cierra el CTA de cada reel: la frase entera, no la que cupo en el presupuesto.

Cinco de los seis terminaban a mitad de palabra —«…voy a hacer un», «…cada
semana le podría estar cos»— porque `--budget 90` corta el ultimo enunciado
cuando se acaba el presupuesto en vez de dejarlo fuera o completarlo. En un SELL
eso es lo peor que puede pasar: **el CTA es la pieza**.

Los cierres se eligen A MANO leyendo los tramos de habla, no por regla. En esta
cola hay de todo —intentos repetidos, la fecha vieja del 14 de septiembre, y en
el reel 4 hasta «¿me puedes echar una mirada?»— y ninguna heuristica distingue
eso del cierre bueno (aprendizaje 13).
"""
import json

# Por reel: (tramos que se QUITAN del final, tramos que se PONEN).
CIERRES = {
    # «…le pueden estar costando hasta 550» + el contraste con los 20.
    "reel-01": ([(532.15, 547.71)],
                [(561.85, 568.44), (583.139, 585.754)]),
    # El CTA del libreto entero, hasta «el link esta abajo en la descripcion».
    "reel-02": ([(500.15, 513.77)],
                [(500.15, 515.293), (522.168, 527.628), (534.054, 537.34)]),
    # «…lo que menos quiero es que tenga usted otra barrera.»
    "reel-03": ([], [(395.038, 397.106), (404.648, 410.038)]),
    # Se corta antes de «si no no» y del «¿me puedes echar una mirada?».
    # El link lo lleva la tarjeta: en el audio solo hay intentos partidos.
    "reel-04": ([(607.27, 618.25)], [(607.27, 618.245)]),
    # Ojo: la cola trae DOS intentos con «el 14 de septiembre», que es la fecha
    # vieja. Se entra despues, en el «este 21 de septiembre».
    "reel-05": ([(703.74, 709.37)],
                [(715.30, 719.652), (755.619, 760.834)]),
    # Ya cerraba bien: «entonces abajo le dejo el link».
    "reel-06": ([], []),
}


def main():
    for reel, (fuera, dentro) in CIERRES.items():
        f = f"ads/{reel}/edl-sell.json"
        d = json.load(open(f, encoding="utf-8"))
        segs = [list(s) for s in d["segmentos"]]
        antes = len(segs)
        for a, b in fuera:
            segs = [s for s in segs
                    if not (abs(s[0] - a) < 0.05 and abs(s[1] - b) < 0.05)]
        segs += [[a, b] for a, b in dentro]
        segs.sort(key=lambda s: s[0])
        d["segmentos"] = segs
        d["duracion_montada_s"] = round(sum(b - a for a, b in segs), 2)
        d.setdefault("revision", {})["cta_cerrado"] = (
            "Cierre elegido a mano sobre los tramos de habla; el corte por "
            "presupuesto lo dejaba a mitad de frase."
        )
        print(f"{reel}: {antes} -> {len(segs)} cortes · "
              f"{d['duracion_montada_s']}s")
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
