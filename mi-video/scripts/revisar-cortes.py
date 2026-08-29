"""Comprueba que ningun corte del plan cae DENTRO de una palabra.

La regla del proyecto es que el corte cae en frontera de frase y **nunca a mitad
de palabra**. Un plan puede cumplirlo en la escena 0 y romperlo en la 3: cada
frontera de escena es un corte, no solo la entrada y la salida de la pieza.

Punch-in NO es corte de audio
-----------------------------
Cuando una escena sale en el mismo instante en que entra la siguiente, el audio
**no se toca**: lo unico que cambia es el recorte. Eso es un punch-in, y partir
una palabra ahi no se oye porque no hay nada partido. Marcarlo seria dar la
alarma sobre lo que el sistema hace bien.

Solo son defecto:
  - la ENTRADA de la pieza y su SALIDA, que si cortan audio de verdad
  - los saltos entre escenas donde `sale != entra`

Palabras estiradas
------------------
Ademas marca las de mas de 1.5 s. Una palabra hablada no dura tanto: si el
transcript la da mas larga es que **cruza un silencio eliminado**, y entonces
sus tiempos —y los del corte que se apoye en ellos— no son fiables. En reel-06
hay una 'la' de 25,7 s: ahi el numero no describe una palabra, describe un hueco.

Y por eso manda el tramo de habla, no la palabra
------------------------------------------------
Un corte que cae en **frontera de tramo de habla** es limpio por definicion: ahi
no hay voz que partir, solo silencio que se quita. La primera version de este
script no lo miraba y dio cinco falsos positivos en reel-06 — decia que partia
'sigue.' cuando en realidad el corte caia en 41.265, el final exacto de un tramo,
y lo que la palabra "duraba" era el silencio de 1,09 s que viene detras.

El transcript describe lo que se dijo; los tramos, donde hubo voz. Para juzgar un
corte manda el segundo.
"""
import json
import sys

MAPA = {
    "reel-01": "20260825_135637", "reel-02": "20260825_144010",
    "reel-03": "20260825_224414", "reel-04": "20260825_225808",
    "reel-05": "20260825_151758", "reel-06": "20260825_231706",
}
LARGA = 1.5
# Margen para dar un corte por coincidente con una frontera de tramo de habla.
BORDE = 0.06
# Tolerancia de roce: si el corte cae a menos de esto del borde de la palabra,
# es frontera limpia. Version apretada de la tolerancia de +/-0.5 s de la regla
# de corte, porque aqui se mide contra la palabra y no contra la frase.
ROCE = 0.08


def palabra_en(segs, t):
    for s in segs:
        if s["start"] - ROCE <= t <= s["end"] + ROCE:
            return s
    return None


def parte(w, t):
    return w is not None and w["start"] + ROCE < t < w["end"] - ROCE


def en_frontera(tramos, t):
    """El corte cae donde empieza o acaba un tramo de habla: no parte voz."""
    return any(abs(t - a) <= BORDE or abs(t - b) <= BORDE for a, b in tramos)


def revisar(reel):
    plan = json.load(open(f"work/scenes/{reel}/plan.json", encoding="utf-8"))
    segs = json.load(open(f"work/transcripts/{MAPA[reel]}.json",
                          encoding="utf-8"))["segmentos"]
    tramos = json.load(open(f"work/cuts/{MAPA[reel]}.json",
                            encoding="utf-8"))["segmentos"]
    esc = plan["escenas"]
    print(f"\n=== {reel} ===")
    fallos = []

    # Los cortes de audio reales: entrada de la pieza, salida de la pieza, y
    # cada salto donde una escena no continua en el instante de la anterior.
    cortes = [("entrada", esc[0]["origen_desde"])]
    for a, b in zip(esc, esc[1:]):
        if abs(a["origen_hasta"] - b["origen_desde"]) > 1e-3:
            cortes.append((f"salto esc{a['indice']}->{b['indice']} sale",
                           a["origen_hasta"]))
            cortes.append((f"salto esc{a['indice']}->{b['indice']} entra",
                           b["origen_desde"]))
    cortes.append(("salida", esc[-1]["origen_hasta"]))

    for etiqueta, t in cortes:
        if en_frontera(tramos, t):
            print(f"  {etiqueta:26} {t:8.2f}  frontera de tramo — limpio")
            continue
        w = palabra_en(segs, t)
        if parte(w, t):
            resto = w["end"] - t
            fallos.append((etiqueta, t, w, resto))
            print(f"  {etiqueta:26} {t:8.2f}  PARTE {w['text']!r} "
                  f"({w['start']:.2f}-{w['end']:.2f}) faltan {resto:.2f}s")
        if w is not None and w["end"] - w["start"] > LARGA:
            print(f"  {etiqueta:26} {t:8.2f}  estirada {w['text']!r} "
                  f"{w['end'] - w['start']:.2f}s — cruza un silencio, tiempos no fiables")

    punchins = sum(1 for a, b in zip(esc, esc[1:])
                   if abs(a["origen_hasta"] - b["origen_desde"]) <= 1e-3)
    print(f"  ({punchins} punch-in{'s' if punchins != 1 else ''} sin corte de audio)")
    if not fallos:
        print("  sin cortes de audio dentro de palabra")
    return len(fallos)


if __name__ == "__main__":
    reels = sys.argv[1:] or list(MAPA)
    total = sum(revisar(r) for r in reels)
    print(f"\nTOTAL cortes de audio dentro de palabra: {total}")
