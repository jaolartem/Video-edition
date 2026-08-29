"""Compara el reel montado con su libreto y dice que CIFRAS faltan.

El detector de repeticiones ve lo que sobra; esto ve lo que **no esta**. En el
reel 2 faltaba el «se queda con 67» —el numero del dueño del yate— y sin el la
comparacion entera no cierra: la pieza plantea el contraste y no lo resuelve.
Ninguna comprobacion anterior lo habria encontrado, porque todas miran lo que
hay.

Se buscan las cifras del libreto, no frases: **un numero que el libreto declara
y el montaje no dice es un agujero en el argumento**, mientras que una frase
puede reformularse sin perder nada.
"""
import json
import re
import sys

LIBRETO = "../docs/libretos.md"
MAPA = {"Reel 1": "reel-01", "Reel 2": "reel-02", "Reel 3": "reel-03",
        "Reel 4": "reel-04", "Reel 5": "reel-05", "Reel 6": "reel-06"}


def cifras(texto):
    """Numeros con su forma normalizada, para poder compararlos."""
    out = set()
    for m in re.finditer(r"\$?\s?([\d][\d.,]*)\s*(%|por ciento)?", texto):
        n = m.group(1).replace(".", "").replace(",", "")
        if n.isdigit() and len(n) >= 2:
            out.add(n)
    return out


def dichas(reel):
    d = json.load(open(f"ads/{reel}/edl-sell.json", encoding="utf-8"))
    txt = " ".join(u.get("texto", "") for u in d.get("detalle", []))
    # «180 mil» y «189 mil» se dicen asi, no como 180000.
    txt = re.sub(r"(\d+)\s*mil", lambda m: f"{m.group(1)}000 {m.group(1)}", txt)
    return cifras(txt)


def main():
    libro = open(LIBRETO, encoding="utf-8").read()
    bloques = re.split(r"\n## ", libro)
    for b in bloques:
        titulo = b.split("\n", 1)[0].strip()
        clave = next((k for k in MAPA if titulo.startswith(k)), None)
        if not clave:
            continue
        reel = MAPA[clave]
        pedidas = cifras(b)
        # 21 y 100 son de la estructura del ejemplo, no cifras del claim.
        pedidas -= {"20", "21"}
        hay = dichas(reel)
        faltan = sorted(pedidas - hay, key=lambda x: -len(x))
        print(f"\n=== {reel} · {titulo[:40]} ===")
        print(f"  libreto: {sorted(pedidas)}")
        if faltan:
            print(f"  FALTAN:  {faltan}")
        else:
            print("  no falta ninguna cifra del libreto")


if __name__ == "__main__":
    main()
