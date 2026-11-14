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

# **La consola de Windows es cp1252 y esto imprime una flecha.**
#
# Es el gotcha 1 del proyecto por enesima vez: `UnicodeEncodeError` sobre «→» y
# el paso muere DESPUES de medir, asi que el trabajo esta hecho y no se ve.
# `registro` ya sabe arreglarlo y lo hace por todos: importarlo pone el canal en
# UTF-8 en vez de repetir aqui la misma linea, que es como se acaba teniendo
# ocho copias de la misma tirita.
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro  # noqa: E402,F401
from dominio.idioma import Idioma  # noqa: E402


def pal(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z]+", t)


#: Los primeros segundos, donde una palabra repetida se nota y en el cuerpo no.
#: Jaime: *«esas repeticiones al inicio, mal: al inicio es fluido y rapido»*.
ARRANQUE = 20.0

#: Cuantas veces puede salir la misma palabra de contenido en el arranque antes
#: de que suene a machaqueo. Tres: dos es enfasis, tres ya es una muletilla.
VECES_MAX = 2



def machaca(r, arranque=ARRANQUE, veces=VECES_MAX):
    """Palabras de contenido que se repiten en el arranque de la pieza.

    Jaime, sobre reel-03: *«usted, usted al inicio, y otra vez repeticion;
    luego "y nunca le ha preguntado al contador porque", sigue, y "es que, es
    que"»*. Y `revisar()` decia **cero repeticiones**: busca frases de cuatro
    palabras repetidas, y esto es otra cosa — la misma palabra volviendo cada
    pocos segundos.

    En medio de la pieza eso puede ser cohesion. En el arranque es machaqueo, y
    ahi Jaime no da margen: *«al inicio es fluido y rapido»*. Un tartamudeo a
    mitad se perdona; en el gancho decide si se sigue viendo.
    """
    import collections

    llanas = Idioma.de_pieza(str(r.get("video", "")).replace(".mp4", "")).llanas
    donde = collections.defaultdict(list)
    for c in r["captions"]:
        t = c["at"] / 30
        if t > arranque:
            break
        for w in pal(c["text"]):
            if len(w) > 2 and w not in llanas:
                donde[w].append(round(t, 1))
    return sorted(((w, cu) for w, cu in donde.items() if len(cu) > veces),
                  key=lambda x: -len(x[1]))


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


def _arranque(r):
    """Lo que machaca en los primeros segundos. Se cuenta aparte y pesa mas."""
    m = machaca(r)
    for w, cuando in m:
        print(f"   ARRANQUE: «{w}» {len(cuando)} veces en {cuando}"
              f" — al inicio es fluido y rapido")
    return len(m)


if __name__ == "__main__":
    reels = json.load(open("src/reels.json", encoding="utf-8"))
    sel = sys.argv[1:]
    hoy = [r for r in reels
           if not sel or r["id"] in sel or r["id"][-1] in sel]
    total = sum(revisar(r) + _arranque(r) for r in hoy)
    print(f"\nTOTAL repeticiones a decidir: {total}")
