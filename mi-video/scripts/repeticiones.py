"""Lista las repeticiones que sobreviven en el reel MONTADO.

No mira el bruto: mira los subtitulos generados, que son literalmente lo que se
oye y lo que se lee. Si una frase aparece dos veces ahi, aparece dos veces en la
pieza.

El dedup de `assemble.py` trabaja por enunciado y no ve las repeticiones que
cruzan de un corte al siguiente — «eso no es mala suerte, eso no es mala suerte»
sale de dos enunciados distintos, cada uno limpio por su cuenta.

Es una lista para decidir a mano, no un recorte automatico. La ultima vez que un
automatismo eligio que repeticion quitar se llevo la frase buena (aprendizaje 13).
"""
import json
import re
import sys
import unicodedata


def pal(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z]+", t)


def revisar(r, n=4):
    """n-gramas de `n` palabras que aparecen mas de una vez en toda la pieza."""
    texto, marcas = [], []
    for c in r["captions"]:
        ws = pal(c["text"])
        if not ws:
            continue
        # Cada palabra con SU instante, repartido dentro del subtitulo. Dandoles
        # el mismo `at` a todas, dos apariciones dentro de la misma frase salian
        # separadas por 0 s y el filtro las tiraba — justo la repeticion mas
        # evidente, «eso no es mala suerte, eso no es mala suerte».
        ini, dur = c["at"] / 30, c["duration"] / 30
        texto += ws
        marcas += [ini + dur * k / len(ws) for k in range(len(ws))]

    vistos, repes = {}, []
    for i in range(len(texto) - n + 1):
        g = tuple(texto[i:i + n])
        if g in vistos:
            # Umbral bajo a proposito. El caso mas evidente —«eso no es mala
            # suerte, eso no es mala suerte»— cae DENTRO del mismo subtitulo, y
            # con un umbral de 0,8 s se colaba justo el que mas se nota.
            if marcas[i] - vistos[g] > 0.25:
                repes.append((vistos[g], marcas[i], " ".join(g)))
                vistos[g] = marcas[i]
        else:
            vistos[g] = marcas[i]

    # Se colapsan los solapes: «no es mala suerte» y «es mala suerte eso» son la
    # misma repeticion vista dos veces.
    limpio, ultimo = [], -9
    for a, b, g in sorted(repes, key=lambda x: x[1]):
        if b - ultimo < 1.5:
            continue
        limpio.append((a, b, g))
        ultimo = b

    print(f"\n=== {r['id']} · {r['duracion']:.1f}s ===")
    if not limpio:
        print("  sin repeticiones")
        return 0
    for a, b, g in limpio:
        print(f"   {a:6.1f}s → {b:6.1f}s   «{g}»")
    return len(limpio)


if __name__ == "__main__":
    reels = json.load(open("src/reels.json", encoding="utf-8"))
    sel = sys.argv[1:]
    total = sum(revisar(r) for r in reels
                if not sel or r["id"] in sel or r["id"][-1] in sel)
    print(f"\nTOTAL repeticiones a decidir: {total}")
