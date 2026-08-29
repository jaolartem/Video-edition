"""Segunda revision del texto sobre un EDL YA montado.

`assemble.py` la hace al montar. Esto la hace **sobre lo que hay en disco**, que
es lo que importa cuando un EDL se generó hace rato y desde entonces han cambiado
cosas — o cuando hay que revisar los seis sin volver a montarlos y arriesgarse a
perder los arranques elegidos a oído (aprendizaje 13: las heuristicas limpian,
no eligen).

Dos cosas se miran, las mismas que en el montaje:

- **Palabras estiradas** (>1,5 s). No son palabras, son cruces de silencio
  eliminado; los tiempos a su alrededor no son fiables y es justo donde el corte
  sale mal.
- **Repeticion interna que sobrevivio al recorte**: el mismo n-grama dos veces
  dentro de un enunciado.

Y una tercera, de coherencia del propio fichero: **`segmentos` y `detalle` tienen
que describir la misma pieza**. Son dos vistas de lo mismo —los cortes y los
enunciados— y al sustituir a mano la toma con «al mes» del reel 2 solo se toco
`segmentos`. El EDL quedo diciendo dos cosas distintas y la revision seguia
avisando de una palabra que ya no estaba en la pieza. Un artefacto con dos vistas
incoherentes es peor que uno con una sola.
"""
import json
import re
import sys

MAPA = {
    "reel-01": "20260825_135637", "reel-02": "20260825_144010",
    "reel-03": "20260825_224414", "reel-04": "20260825_225808",
    "reel-05": "20260825_151758", "reel-06": "20260825_231706",
}
LARGA = 1.5


def clave(texto):
    return [w for w in re.findall(r"[a-záéíóúüñ]+", texto.lower()) if len(w) > 2]


def revisar(reel):
    edl = json.load(open(f"ads/{reel}/edl-sell.json", encoding="utf-8"))
    words = json.load(open(f"work/transcripts/{MAPA[reel]}.json",
                          encoding="utf-8"))["segmentos"]
    avisos = []
    for u in edl.get("detalle", []):
        ws = [w for w in words if u["start"] <= w["start"] < u["end"]]
        largas = [w for w in ws if w["end"] - w["start"] > LARGA]
        if largas:
            peor = max(largas, key=lambda w: w["end"] - w["start"])
            avisos.append((u["start"], peor, len(largas), None))
        k = clave(u.get("texto", ""))
        for n in range(2, 5):
            grams = [tuple(k[i:i + n]) for i in range(len(k) - n + 1)]
            repetido = next((g for g in grams if grams.count(g) > 1), None)
            if repetido:
                avisos.append((u["start"], None, 0, " ".join(repetido)))
                break

    # Coherencia entre las dos vistas del EDL.
    segmentos = edl.get("segmentos", [])
    detalle = edl.get("detalle", [])
    huerfanos = [u["start"] for u in detalle
                 if not any(a - 0.05 <= u["start"] <= b + 0.05 for a, b in segmentos)]
    dur_seg = sum(b - a for a, b in segmentos)

    zonas = edl.get("zonas", {})
    print(f"\n=== {reel} · {edl.get('duracion_montada_s')}s "
          f"(gancho {zonas.get('gancho_s')} / cuerpo {zonas.get('cuerpo_s')} / "
          f"CTA {zonas.get('cta_s')}) ===")
    if edl.get("revision", {}).get("zonas_no_fiables"):
        print("  ojo: zonas medidas en tramo BRUTO, no describen lo que se ve")
    if huerfanos:
        print(f"  INCOHERENTE: {len(huerfanos)} enunciados de `detalle` no estan "
              f"en `segmentos` — {', '.join(f'{t:.2f}s' for t in huerfanos[:4])}")
    if abs(dur_seg - (edl.get("duracion_montada_s") or 0)) > 0.2:
        print(f"  INCOHERENTE: segmentos suman {dur_seg:.2f}s pero "
              f"duracion_montada_s dice {edl.get('duracion_montada_s')}")
    if not avisos:
        print("  sin avisos")
        return 0
    print(f"  {len(avisos)} enunciados a mirar dos veces")
    for t, peor, n, rep in sorted(avisos, key=lambda a: a[0])[:6]:
        if peor is not None:
            print(f"   {t:7.2f}s  palabra estirada «{peor['text'].strip()}» "
                  f"({peor['end']-peor['start']:.1f}s), {n} en el enunciado")
        else:
            print(f"   {t:7.2f}s  repeticion interna sin recortar: «{rep}»")
    if len(avisos) > 6:
        print(f"   … y {len(avisos)-6} mas")
    return len(avisos)


if __name__ == "__main__":
    reels = sys.argv[1:] or list(MAPA)
    total = sum(revisar(r) for r in reels)
    print(f"\nTOTAL enunciados a revisar: {total}")
