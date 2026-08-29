"""Pega cada empalme del EDL a la frontera de habla mas cercana.

Un empalme que cae DENTRO de un tramo de habla corta una silaba por la mitad. Es
lo que hace que un CTA suene «desincronizado»: no esta desplazado, esta pegado
donde no debia. Medido sobre los seis: 56 empalmes fuera de frontera.

Solo se mueve lo que esta **a menos de `TOLERANCIA`**. Mas lejos que eso el
empalme no es un desajuste de milisegundos sino una decision de contenido —hay
palabras enteras de por medio— y esas no las toma un script (aprendizaje 13). Se
listan para mirarlas.
"""
import json
import sys

MAPA = {
    "reel-01": "20260825_135637", "reel-02": "20260825_144010",
    "reel-03": "20260825_224414", "reel-04": "20260825_225808",
    "reel-05": "20260825_151758", "reel-06": "20260825_231706",
}
# Una silaba corta ronda los 0,15-0,25 s. Por encima ya es otra palabra.
TOLERANCIA = 0.25


def pegar(reel):
    f = f"ads/{reel}/edl-sell.json"
    d = json.load(open(f, encoding="utf-8"))
    tramos = json.load(open(f"work/cuts/{MAPA[reel]}.json",
                            encoding="utf-8"))["segmentos"]
    bordes = sorted({round(x, 3) for ab in tramos for x in ab})

    def cerca(t):
        b = min(bordes, key=lambda x: abs(x - t))
        return b if abs(b - t) <= TOLERANCIA else None

    dentro = lambda t: any(a + 1e-3 < t < b - 1e-3 for a, b in tramos)

    segs = [list(s) for s in d["segmentos"]]
    movidos, lejos = 0, []
    for i, s in enumerate(segs):
        for j, lado in ((0, "entra"), (1, "sale")):
            # El primer arranque y el ultimo cierre son de la pieza, no
            # empalmes: no se tocan.
            if (i == 0 and j == 0) or (i == len(segs) - 1 and j == 1):
                continue
            if not dentro(s[j]):
                continue
            b = cerca(s[j])
            if b is None:
                lejos.append((s[j], lado))
                continue
            s[j] = b
            movidos += 1

    segs = [s for s in segs if s[1] - s[0] >= 0.4]
    d["segmentos"] = segs
    d["duracion_montada_s"] = round(sum(b - a for a, b in segs), 2)
    d.setdefault("revision", {})["empalmes_pegados"] = movidos
    if lejos:
        d["revision"]["empalmes_a_revisar"] = [
            {"t": round(t, 2), "lado": l} for t, l in lejos]
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{reel}: {movidos} empalmes pegados, {len(lejos)} a revisar a mano "
          f"-> {d['duracion_montada_s']}s")
    return len(lejos)


if __name__ == "__main__":
    total = sum(pegar(r) for r in sys.argv[1:] or list(MAPA))
    print(f"\nempalmes que necesitan decision: {total}")
