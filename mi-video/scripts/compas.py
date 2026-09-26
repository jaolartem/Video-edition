"""**A qué compás baila cada pieza.** Una sola puerta a `src/brand/compas.json`.

Jaime, 17-9-2026: *«quiero que algunas tomas inicien dentro del beat de la
canción, que el reel baile con la música»*. Las costuras están donde el habla
las deja y no se mueven; lo que se mueve es la espera entre ellas, y la fase con
la que entra la canción.

Se lee **aquí y sólo aquí**, por lo de siempre: `cama.json` acabó con
`objetivo_db` diciendo 16 mientras el bucle que mezclaba usaba 14, porque dos
sitios leían el mismo fichero (C-235).

Lo consumen tres: `render-hook.mjs` congela los frames, `musica.sh` corre la
canción a su fase, y `version.cuadra_con_el_json` cuenta las pausas para no
acusar de larga a una pieza que las lleva declaradas.
"""
import json
import os

RUTA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "src", "brand", "compas.json")


def leer():
    try:
        with open(RUTA, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def de(slug):
    """Lo declarado para esa pieza, o `None` si no baila con nada."""
    d = leer().get(slug)
    return d if isinstance(d, dict) else None


def pausas(slug):
    """`{indice de escena: segundos}`. Vacío si no tiene."""
    return (de(slug) or {}).get("pausas") or {}


def total(slug):
    """Cuánto alarga la pieza el hecho de bailar, en segundos."""
    return float(sum(float(v) for v in pausas(slug).values()))


def fase(slug):
    """Cuánto se corre su canción para que los golpes caigan en las costuras."""
    return float((de(slug) or {}).get("fase") or 0.0)


def ventanas(slug, fps=30.0, reloj="entrega"):
    """Dónde cae cada pausa en el reloj de la ENTREGA: `[(desde, hasta)]`.

    Hace falta porque una pausa **no es un hueco cualquiera**: es el sitio donde
    la música tiene que oírse sola, que es de lo que va bailar. Midiendo la
    separación de la cama sin excluirlas, el peor hueco pasa a ser siempre una
    pausa y la calibración la hunde — justo donde Jaime quiere el golpe.

    Se arma con el plan, que es quien sabe cuánto dura cada escena, y con la
    velocidad de la pieza, que es lo que separa el reloj del corte del de la
    entrega.

    `reloj="corte"` las devuelve sin dividir por la velocidad: es el reloj en el
    que vive `public/reel-NN.mp4`, y por tanto el de la voz que se exporta.
    """
    import json
    import os

    ps = pausas(slug)
    if not ps:
        return []
    import beats
    v = beats.velocidad(slug) if reloj == "entrega" else 1.0
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "work", "scenes", slug, "plan-full.json")
    try:
        with open(ruta, encoding="utf-8") as f:
            escenas = json.load(f)["escenas"]
    except (OSError, ValueError, KeyError):
        return []
    fuera, t = [], 0.0
    for e in escenas:
        t += round((e["origen_hasta"] - e["origen_desde"]) * fps) / fps
        p = float(ps.get(str(e["indice"]), 0))
        if p:
            fuera.append((t / v, (t + p) / v))
            t += p
    return fuera


def desde(slug):
    """Desde qué segundo de su canción entra la cama, si la pieza lo declara.

    `cama.py` elige el pasaje que se queda quieto, que es lo correcto por
    defecto. Pero «quieto» no es «parejo»: puede decaer de punta a punta y dejar
    el final de la pieza sin cama. Cuando su oído lo pilla, el pasaje se declara
    aquí — y tiene que entrar **en fase**, o mover la música deshace el baile.
    """
    v = (de(slug) or {}).get("desde")
    return float(v) if v is not None else None


def bpm(slug):
    return float((de(slug) or {}).get("bpm") or 0.0)


#: **Y aquí NO va un realce por golpe.** Se probó el 18-9 —subir la cama 4 dB
#: dentro de cada pausa— y se quitó por dos razones, no por gusto:
#:
#: 1. **Dos mecanismos mandando sobre lo mismo.** `calibrar-cama` fija el nivel
#:    midiendo, y el realce lo deshacía por encima: con él puesto la pieza medía
#:    11,0 dB de separación contra los 15 declarados, y la guarda decía FUERA.
#:    Es la avería de la casa —dos fuentes para una decisión— con otra ropa.
#: 2. **Siete ventanas escritas a mano se rompen en cuanto cambia el ritmo**, que
#:    es justo lo que se acababa de desacoplar (C-527).
#:
#: Lo que la práctica manda para que el golpe se oiga no es subir la música en
#: él: es que la cama esté a un nivel honesto y que **la pausa la descubra**. Si
#: aun así no basta, la herramienta es el ducking —la cama baja bajo la voz y
#: vuelve sola al callar—, que es un mecanismo y no siete excepciones.


if __name__ == "__main__":
    #     python scripts/compas.py --ventanas reel-14
    import sys as _s

    if len(_s.argv) > 2 and _s.argv[1] == "--ventanas":
        for a, b in ventanas(_s.argv[2]):
            print(f"{a:.3f} {b:.3f}")
