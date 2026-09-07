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

#: Los eslabones, EN ORDEN, y **de quién depende cada uno**. Cuatro cosas: cómo
#: se llama, qué fichero produce, con qué se le despierta, y de qué eslabón
#: anterior come.
#:
#: **La dependencia se declara, no se deduce de la posición.** Estaba deducida —
#: cada eslabón se comparaba con el que tuviera delante en la lista— y eso metía
#: parentescos que no existen: `cara` iba detrás de `subtitulos`, así que
#: resubtitular una pieza daba por caducada la medida de la cara de las SIETE.
#: La cara se mide sobre el corte y no sabe nada del subtítulo.
#:
#: Costaba `sujeto.py` —MediaPipe, el paso lento— siete veces por nada. Jaime,
#: viéndolo: *«no empezar de 0»*.
#:
#: Y hay un agravante que conviene tener presente: `subtitulos` escribe UN solo
#: fichero para las siete (`work/subs/todos.json`), así que tocar una pieza
#: mueve la fecha de todas. Mientras siga compartido, cualquier eslabón que
#: cuelgue de él caduca en bloque.
ESLABONES = [
    ("edl",         "ads/{s}/edl-sell.json",              "revision --aplicar · depurar · costuras", None),
    ("plan",        "work/scenes/{s}/plan-full.json",     "plan-reel.mjs",      "edl"),
    ("encuadres",   "work/scenes/{s}/plan-full.json",     "punch-ins.py",       "plan"),
    ("corte",       "public/{s}.mp4",                     "render-hook.mjs",    "encuadres"),
    ("subtitulos",  "work/subs/todos.json",               "subtitular.py",      "corte"),
    # De `corte`, no de `subtitulos`: se mide la cara sobre el vídeo cortado.
    ("cara",        "work/scenes/{s}/cara.json",          "sujeto.py",          "corte"),
    # La otra mitad de `cara`, y del mismo corte: a qué lado deja sitio su
    # cuerpo, escena por escena. Sin esto el volumen de un panel se coloca a
    # ojo, que es como doce de trece acabaron dibujados encima de él.
    ("huecos",      "work/scenes/{s}/huecos.json",        "hueco.py",           "corte"),
    # Qué hay DETRÁS del subtítulo, escena por escena: con eso se decide si el
    # cc lleva caja, va limpio o va en negativo. Del corte, como las otras dos
    # medidas de imagen — se mide sobre el cuadro que ve el espectador. Si el
    # corte cambia, el fondo del cc cambia y hay que volver a medir.
    ("trasfondo",   "work/scenes/{s}/trasfondo.json",     "trasfondo.py",       "corte"),
    # **Dos entradas, y las dos se declaran.** El spec come de las dos medidas
    # que cuelgan del corte, y dejar sólo una habría sido perder la otra en
    # silencio — que es justo el parentesco deducido contra el que avisa la nota
    # de arriba, con el signo cambiado.
    ("spec",        "src/reels.json",                     "reels-spec.mjs",     ("huecos", "trasfondo")),
    ("render",      "out/reels/reel-R{n}.mp4",            "render.mjs",         "spec"),
    ("efectos",     "out/audio-voz/reel-R{n}-efectos.wav", "efectos.mjs",       "render"),
    ("entrega",     "out/entrega/reel-R{n}.mp4",          "voz-limpia.py · musica.sh", "efectos"),
]


def _cuando(ruta):
    return os.path.getmtime(ruta) if os.path.exists(ruta) else None


def _codigo(quien):
    """Cuándo se tocó por última vez el código que produce ese eslabón.

    **El agujero que tapa.** La cadena comparaba cada artefacto con su *entrada*
    y con nada más. Así que arreglar el productor no caducaba nada: el plan de
    reel-06 seguía «al día» con el `plan-reel.mjs` de antes de C-233, y la pieza
    se volvía a entregar arrastrando 2,88 s de aire muerto que el fallo le metía
    desde el mapa de silencios de otra cinta.

    Es la avería de siempre en su forma más cara: la corrección existe, está
    probada, y la entrega sale con el código viejo porque nadie declaró que el
    código también es una entrada.

    La columna `quien` ya decía qué script produce cada eslabón; sólo era un
    apunte para leer. Aquí se convierte en dependencia de verdad.
    """
    ts = []
    for parte in quien.split("·"):
        nombre = parte.strip().split()[0]
        if "." not in nombre:
            continue
        aqui = os.path.dirname(os.path.abspath(__file__))
        # `sujeto.py` vive en `dominio/`, y buscarlo solo en `scripts/`
        # dejaba ese eslabon sin productor: la comprobacion se saltaba en
        # silencio, que es la forma de fallar que este proyecto ya conoce.
        t = _cuando(os.path.join(aqui, nombre)) or _cuando(
            os.path.join(aqui, "dominio", nombre))
        if t is not None:
            ts.append((t, nombre))
    return max(ts) if ts else None


def desde(n):
    """El primer eslabón caducado de la pieza `n`, o `None` si está al día."""
    s = f"reel-{n:02d}"
    cuando, donde = {}, {}
    for i, (nombre, patron, quien, come_de) in enumerate(ESLABONES):
        ruta = patron.format(s=s, n=n)
        t = _cuando(ruta)
        if t is None:
            return (i, nombre, quien, f"no existe {ruta}")
        # Un eslabón puede comer de varios: el spec come del hueco y del
        # trasfondo, y comparar sólo con uno deja al otro sin caducar.
        for come in (come_de,) if isinstance(come_de, str) else (come_de or ()):
            padre = cuando.get(come)
            # `encuadres` comparte fichero con `plan`: no se compara consigo mismo.
            if padre is not None and ruta != donde[come] and t < padre:
                return (i, nombre, quien,
                        f"{ruta} es mas viejo que {donde[come]}")
        cod = _codigo(quien)
        if cod and t < cod[0]:
            return (i, nombre, quien, f"{ruta} se hizo con el {cod[1]} de antes")
        cuando[nombre], donde[nombre] = t, ruta
    return None


def hay_que(nombre, n):
    """¿Hay que rehacer ese eslabón de esa pieza? `(sí/no, por qué)`.

    **Es la pregunta que la línea nunca hacía.** Este fichero declaraba los trece
    eslabones desde el principio y sólo se le citaba en comentarios: `montar.sh`
    comprobaba tres a mano con `-nt` y los otros diez corrían siempre. El corte
    del bruto 4K son 65 s medidos y el render 3,6 min, **cada montaje, hubiera
    cambiado algo o no** — que es exactamente lo que produce el aviso «salió
    IDÉNTICA al render anterior», sólo que cobrado después.

    La regla sale de `desde()` y no se inventa otra: si la pieza caduca en el
    eslabón *i*, hay que correr **de *i* en adelante**. Un eslabón anterior está
    al día por definición, porque lo que come ya estaba bien.
    """
    orden = {e[0]: i for i, e in enumerate(ESLABONES)}
    if nombre not in orden:
        # **`ValueError`, no `SystemExit`.** `SystemExit` sale con 1, que es
        # exactamente el codigo con el que esta funcion dice «esta al dia»: un
        # eslabon mal escrito hacia que el `if` del shell saltara el paso en
        # silencio. Una errata no puede leerse como «no hace falta».
        raise ValueError(
            f"no existe el eslabon «{nombre}». Los que hay: " + ", ".join(orden))
    d = desde(n)
    if d is None:
        return False, "la pieza esta al dia de punta a punta"
    i, donde, _quien, por = d
    if orden[nombre] < i:
        return False, f"la cadena caduca mas adelante, en «{donde}»"
    return True, por


def main():
    # `--hay-que <eslabon> <n>`: la pregunta de un paso concreto, para el shell.
    # Sale con 0 si hay que rehacerlo —que es lo que un `if` de bash lee como
    # «sí»— y con 1 si está al día.
    if "--hay-que" in sys.argv:
        # **Tres codigos, no dos.** 0 = hay que rehacerlo · 1 = esta al dia ·
        # 2 = no se pudo contestar. Sin el tercero, quien pregunta desde el
        # shell no puede distinguir «no hace falta» de «me equivoque al
        # preguntar», y las dos cosas se leen igual: saltandose el paso.
        try:
            i = sys.argv.index("--hay-que")
            nombre = sys.argv[i + 1]
            n = int(sys.argv[i + 2])
            toca, por = hay_que(nombre, n)
        except (IndexError, ValueError) as e:
            print(f"cadena: {e}", file=sys.stderr)
            print("  uso: cadena.py --hay-que <eslabon> <numero de pieza>",
                  file=sys.stderr)
            return 2
        print(f"  {nombre} R{n}: " + (f"se rehace — {por}" if toca
                                      else f"al dia — {por}"))
        return 0 if toca else 1

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
