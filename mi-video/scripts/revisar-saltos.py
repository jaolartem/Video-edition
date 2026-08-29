"""Comprueba los saltos de audio del CUERPO montado, no solo del gancho.

`revisar-cortes.py` mira el plan de escenas del gancho. Esto mira `segmentos` del
EDL, que es donde vive el cuerpo y el CTA: cada par de cortes consecutivos que no
se tocan es un **salto de audio**, y si no cae en frontera de tramo de habla se
oye — una silaba cortada, una palabra que empieza y no acaba.

Es lo que hace que un CTA suene «desincronizado»: no esta desplazado, esta
empalmado donde no debia.

**Caer dentro de un tramo no basta para ser defecto.** Un tramo de habla es una
frase entera: cortar entre dos de sus palabras es edicion normal, y marcar eso
daba 56 avisos donde no hay 56 problemas. El defecto es cortar **dentro de una
palabra**. Asi que se cruzan las dos fuentes, igual que en `revisar-cortes.py`:
limpio si cae en frontera de tramo O entre palabras; sucio solo si parte una.
"""
import json
import sys

MAPA = {
    "reel-01": "20260825_135637", "reel-02": "20260825_144010",
    "reel-03": "20260825_224414", "reel-04": "20260825_225808",
    "reel-05": "20260825_151758", "reel-06": "20260825_231706",
}
BORDE = 0.06


def revisar(reel):
    d = json.load(open(f"ads/{reel}/edl-sell.json", encoding="utf-8"))
    tramos = json.load(open(f"work/cuts/{MAPA[reel]}.json",
                            encoding="utf-8"))["segmentos"]
    palabras = json.load(open(f"work/transcripts/{MAPA[reel]}.json",
                              encoding="utf-8"))["segmentos"]
    segs = d["segmentos"]

    def limpio(t):
        if any(abs(t - a) <= BORDE or abs(t - b) <= BORDE for a, b in tramos):
            return True
        w = next((w for w in palabras
                  if w["start"] - BORDE <= t <= w["end"] + BORDE), None)
        if w is None:
            return True  # entre palabras
        # Una palabra estirada no describe una palabra sino un hueco: sus
        # bordes no sirven para juzgar nada.
        if w["end"] - w["start"] > 1.5:
            return True
        return not (w["start"] + BORDE < t < w["end"] - BORDE)

    sucios = []
    for a, b in zip(segs, segs[1:]):
        if abs(a[1] - b[0]) < 1e-3:
            continue  # continuo: no hay salto
        for t, lado in ((a[1], "sale"), (b[0], "entra")):
            if not limpio(t):
                sucios.append((t, lado))
    print(f"\n=== {reel} · {len(segs)} cortes ===")
    if not sucios:
        print("  todos los saltos caen en frontera de habla")
    else:
        print(f"  {len(sucios)} saltos NO caen en frontera:")
        for t, lado in sucios[:8]:
            w = next((w for w in palabras
                      if w["start"] <= t <= w["end"]), None)
            txt = f" parte «{w['text'].strip()}»" if w else ""
            print(f"   {t:8.2f}s  {lado}{txt}")
    return len(sucios)


if __name__ == "__main__":
    total = sum(revisar(r) for r in sys.argv[1:] or list(MAPA))
    print(f"\nTOTAL saltos sucios: {total}")
