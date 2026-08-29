"""Recalcula gancho/cuerpo/CTA en duración REAL sin volver a montar.

Cuatro EDL —los anteriores al arreglo de `dur_real()`— reportan las zonas en
**tramo bruto**: incluyen los silencios que luego se quitan. En reel-01 eso da un
gancho de 31,2 s cuando en pantalla dura bastante menos, y un número que no
corresponde a nada de lo que se ve es peor que no tenerlo (aprendizaje 16).

Regenerar el EDL entero arreglaría los números **y sustituiría los arranques
elegidos a oído** (aprendizaje 13), así que no se toca la selección. Las
fronteras de zona se reconstruyen: los enunciados van en orden, y las sumas
brutas que el propio EDL declara dicen dónde cae cada corte de zona. A partir de
ahí, la duración real de cada grupo sale de `segmentos`.

Determinista y sin decidir nada: solo vuelve a medir lo que ya estaba elegido.
"""
import json
import sys


def real(inicio, fin, segmentos):
    """Segundos con habla entre dos instantes del bruto."""
    return sum(max(0.0, min(fin, b) - max(inicio, a)) for a, b in segmentos)


def rehacer(reel):
    f = f"ads/{reel}/edl-sell.json"
    d = json.load(open(f, encoding="utf-8"))
    z = d["zonas"]
    # Tambien se recalculan las que ya estaban en duracion real: al quitar los
    # restos de menos de 0,4 s y al sustituir la toma con «al mes», la seleccion
    # cambio y las zonas se quedaron describiendo el montaje anterior. Un numero
    # que fue correcto no lo sigue siendo por haberlo sido.
    en_bruto = bool(d.get("revision", {}).get("zonas_no_fiables"))
    det = sorted(d["detalle"], key=lambda u: u["start"])
    segs = d["segmentos"]

    # Se camina la lista acumulando BRUTO hasta alcanzar cada frontera
    # declarada. Es la misma aritmética con la que se escribieron.
    fronteras = [z["gancho_s"], z["gancho_s"] + z["cuerpo_s"]]
    grupos, acc, k = [[], [], []], 0.0, 0
    for u in det:
        if k < 2 and acc >= fronteras[k] - 1e-6:
            k += 1
        grupos[k].append(u)
        # Si ya venian en real, la aritmetica de las fronteras tambien es real.
        acc += (u["end"] - u["start"]) if en_bruto else real(u["start"], u["end"], segs)

    nombres = ("gancho_s", "cuerpo_s", "cta_s")
    antes = [z[n] for n in nombres]
    nuevos = [round(sum(real(u["start"], u["end"], segs) for u in g), 1)
              for g in grupos]

    # Guarda: la reconstruccion supone que los enunciados van en el mismo orden
    # en el bruto y en la linea de tiempo. **En reel-05 no es asi** — su
    # apertura en frio sale del minuto 682 y va PRIMERA, asi que ordenar por
    # tiempo de origen la manda al final y las fronteras caen donde no es. Si
    # las tres zonas no suman la duracion montada, la reconstruccion no vale y
    # **no se escribe**: un numero equivocado es peor que uno marcado como
    # dudoso, que es justo la leccion del aprendizaje 16.
    if abs(sum(nuevos) - d["duracion_montada_s"]) > 0.3:
        d.setdefault("revision", {})["zonas_no_fiables"] = True
        d["revision"]["zonas_sin_reconstruir"] = (
            f"Suman {sum(nuevos):.1f}s frente a {d['duracion_montada_s']}s montados. "
            "Los enunciados no van en orden cronologico (apertura en frio), asi "
            "que las fronteras de zona no se pueden deducir. Hay que remontar "
            "pasando el mismo --apertura."
        )
        json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{reel}: NO reconstruible ({sum(nuevos):.1f} vs "
              f"{d['duracion_montada_s']}) — marcado, sin tocar los numeros")
        return
    for nombre, valor in zip(nombres, nuevos):
        z[nombre] = valor
    z["zonas_en_bruto"] = False
    d.setdefault("revision", {})["zonas_no_fiables"] = False
    d["revision"]["zonas_recalculadas"] = (
        "Medidas de nuevo en duración real sobre la misma selección; no se "
        "re-montó nada."
    )
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    suma = sum(z[n] for n in nombres)
    print(f"{reel}: {antes} (bruto {sum(antes):.1f}) -> "
          f"[{z['gancho_s']}, {z['cuerpo_s']}, {z['cta_s']}] "
          f"(real {suma:.1f}, montada {d['duracion_montada_s']})")


if __name__ == "__main__":
    for r in sys.argv[1:] or ["reel-01", "reel-02", "reel-03",
                              "reel-04", "reel-05", "reel-06"]:
        rehacer(r)
