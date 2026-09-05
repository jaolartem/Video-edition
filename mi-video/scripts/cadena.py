"""Desde qué eslabón hay que volver a correr la línea.

Jaime, después de un día entero de piezas a medio hacer: *«si retrocedes en una
línea de producción la tienes que pasar completa luego»*.

## El problema que resuelve

La línea tiene nueve eslabones y cada uno produce un artefacto que el siguiente
lee. Tocar uno **invalida todos los que vienen después** — y hasta hoy nadie lo
comprobaba salvo en un sitio (`_render_caduco`, y sólo para el render).

Así que pasaba esto: se rehacía el EDL, se regeneraban dos de los cinco pasos de
en medio a mano, y la pieza salía con el corte nuevo, los subtítulos viejos y el
audio de otra edición. Nada fallaba: cada paso hacía su trabajo con la entrada
que encontró.

## Cómo se decide

Por fecha de modificación, que es la única señal que hay y la misma que el propio
`montar.sh` ya usa para el plan. Si un artefacto es **más viejo que su entrada**,
ese eslabón y todos los siguientes están caducados.

No mira el contenido: un `touch` lo despierta y una edición que no cambia nada lo
despierta igual. Es deliberado — equivocarse hacia rehacer de más cuesta minutos;
equivocarse hacia rehacer de menos cuesta una entrega mal montada, que es lo que
llevamos pagando.

    python scripts/cadena.py 2        # desde donde hay que correr reel-02
    python scripts/cadena.py          # las siete
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: Los eslabones, EN ORDEN. Cada uno: cómo se llama, qué fichero produce, y con
#: qué se le despierta. El orden es el de la línea y no se reordena por
#: conveniencia: es el orden en que un dato depende del anterior.
ESLABONES = [
    ("edl",         "ads/{s}/edl-sell.json",              "revision --aplicar · depurar · costuras"),
    ("plan",        "work/scenes/{s}/plan-full.json",     "plan-reel.mjs"),
    ("encuadres",   "work/scenes/{s}/plan-full.json",     "punch-ins.py"),
    ("corte",       "public/{s}.mp4",                     "render-hook.mjs"),
    ("subtitulos",  "work/subs/todos.json",               "subtitular.py"),
    ("cara",        "work/scenes/{s}/cara.json",          "sujeto.py"),
    ("spec",        "src/reels.json",                     "reels-spec.mjs"),
    ("render",      "out/reels/reel-R{n}.mp4",            "render.mjs"),
    ("efectos",     "out/audio-voz/reel-R{n}-efectos.wav", "efectos.mjs"),
    ("entrega",     "out/entrega/reel-R{n}.mp4",          "voz-limpia.py · musica.sh"),
]


def _cuando(ruta):
    return os.path.getmtime(ruta) if os.path.exists(ruta) else None


def desde(n):
    """El primer eslabón caducado de la pieza `n`, o `None` si está al día."""
    s = f"reel-{n:02d}"
    previo = None
    for i, (nombre, patron, quien) in enumerate(ESLABONES):
        ruta = patron.format(s=s, n=n)
        t = _cuando(ruta)
        if t is None:
            return (i, nombre, quien, f"no existe {ruta}")
        # `encuadres` comparte fichero con `plan`: no se compara consigo mismo.
        if previo is not None and ruta != previo[1] and t < previo[0]:
            return (i, nombre, quien,
                    f"{ruta} es mas viejo que {previo[1]}")
        previo = (t, ruta)
    return None


def main():
    ns = [int(x) for x in sys.argv[1:] if x.isdigit()] or list(range(1, 8))
    sucias = 0
    for n in ns:
        d = desde(n)
        if d is None:
            print(f"  reel-{n:02d}: al dia")
            continue
        sucias += 1
        i, nombre, quien, por = d
        resto = " -> ".join(x[0] for x in ESLABONES[i:])
        print(f"  reel-{n:02d}: caducada en «{nombre}» — {por}")
        print(f"            hay que correr: {resto}")
        print(f"            empezando por: {quien}")
    print(f"\ncadena: {sucias} de {len(ns)} pieza(s) con eslabones que rehacer"
          if sucias else "\ncadena: las piezas estan al dia de punta a punta.")
    return 1 if sucias else 0


if __name__ == "__main__":
    raise SystemExit(main())
