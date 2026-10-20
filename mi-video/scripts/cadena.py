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
    # De ESA pieza, no el fichero compartido (C-567): subtitular otra pieza
    # movia `todos.json` y esta parecia al dia sin estarlo, o al reves.
    ("subtitulos",  "work/subs/{s}.json",                 "subtitular.py",      "corte"),
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
    # La huella del spec de ESA pieza (C-567). `src/reels.json` es uno para
    # las 22: cualquier escritura caducaba el render de todas.
    ("spec",        "work/scenes/{s}/spec.huella",        "reels-spec.mjs",     ("huecos", "trasfondo")),
    # **Y el render come también de `src/`** (C-475): los componentes son el
    # código que dibuja. Con sólo `render.mjs`, arreglar un componente no
    # caducaba nada — reel-14 se volvió a entregar a las 14:00 con el render de
    # las 13:47, de antes de C-474, y las casillas seguían entrando solas.
    ("render",      "out/reels/reel-R{n}.mp4",            "render.mjs · src/",  "spec"),
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
    aqui = os.path.dirname(os.path.abspath(__file__))
    for parte in quien.split("·"):
        nombre = parte.strip().split()[0]
        # Una carpeta (`src/`) cuenta por su fichero más reciente.
        if nombre.endswith("/"):
            raiz = os.path.join(aqui, "..", nombre)
            t = max((os.path.getmtime(os.path.join(d, f))
                     for d, _, fs in os.walk(raiz) for f in fs
                     if f.endswith((".ts", ".tsx", ".json"))
                     # El spec no es codigo: es el dato de cada pieza (C-567).
                     and f != "reels.json"), default=None)
            if t is not None:
                ts.append((t, nombre))
            continue
        if "." not in nombre:
            continue
        # `sujeto.py` vive en `dominio/`, y buscarlo solo en `scripts/`
        # dejaba ese eslabon sin productor: la comprobacion se saltaba en
        # silencio, que es la forma de fallar que este proyecto ya conoce.
        t = _cuando(os.path.join(aqui, nombre)) or _cuando(
            os.path.join(aqui, "dominio", nombre))
        if t is not None:
            ts.append((t, nombre))
    return max(ts) if ts else None


def _misma_huella(s, n):
    """¿El render se hizo con el spec de hoy? Por contenido, no por fecha (C-595).

    `render.mjs` estampa al lado del mp4 la huella del spec que pintó; si es la
    misma que la de la pieza, lo dibujado no ha cambiado aunque la fecha del
    spec se mueva cada vez que se mira.
    """
    def leer(r):
        try:
            return open(r, encoding="utf-8").read().strip()
        except OSError:
            return None
    hay = leer(f"out/reels/reel-R{n}.mp4.huella")
    return hay is not None and hay == leer(f"work/scenes/{s}/spec.huella")


def _camara_al_dia(s):
    """¿El plan se hizo con la cámara que hoy decide la base? (C-598)

    La misma huella que deja `plan-reel.mjs` en `camara.huella`: las filas
    `(etapa_orden, camara, tablero)` de `escena_desc`, por orden.
    """
    import hashlib
    import json
    import sqlite3
    try:
        hay = open(f"work/scenes/{s}/camara.huella", encoding="utf-8").read().strip()
        con = sqlite3.connect("file:ads/decisiones.db?mode=ro", uri=True, timeout=10)
        filas = [list(r) for r in con.execute(
            "select etapa_orden, camara, tablero from escena_desc"
            " where video_slug = ? order by etapa_orden", (s,))]
        con.close()
    except (OSError, sqlite3.Error):
        return True
    txt = json.dumps(filas, ensure_ascii=False, separators=(",", ":"))
    return hay == hashlib.sha1(txt.encode("utf-8")).hexdigest()[:12]


def _ritmo_al_dia(s):
    """¿El plan se hizo con el modelo de montaje que hoy declara la pieza? (C-619)

    `plan-reel.mjs` deja el nombre en `ritmo.huella`. Un plan sin ella es de
    antes de los modelos, o sea del general: así declarar el ritmo de una pieza
    rehace su plan y no caduca el de las demás.
    """
    from dominio.ritmo import Ritmo

    try:
        hay = open(f"work/scenes/{s}/ritmo.huella", encoding="utf-8").read().strip()
    except OSError:
        hay = Ritmo.nombre
    return hay == Ritmo.de(s).nombre


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
            if padre is not None and ruta != donde[come] and t < padre                     and not (nombre == "render" and _misma_huella(s, n)):
                return (i, nombre, quien,
                        f"{ruta} es mas viejo que {donde[come]}")
        if nombre == "plan" and not _camara_al_dia(s):
            return (i, nombre, quien, "la camara decidida cambio y el plan no la tiene")
        if nombre == "plan" and not _ritmo_al_dia(s):
            return (i, nombre, quien, "el ritmo declarado cambio y el plan no lo tiene")
        cod = _codigo(quien)
        if cod and t < cod[0]:
            return (i, nombre, quien, f"{ruta} se hizo con el {cod[1]} de antes")
        cuando[nombre], donde[nombre] = t, ruta
    return None


def refresca_spec(n):
    """Rehace el spec antes de preguntar si el render esta al dia (C-582).

    La huella del spec (C-567) sólo se reescribía dentro del montaje. El salto
    «ya está al día» de `avanzar` preguntaba antes de montar, así que un diseño
    nuevo no movía nada: reel-19 pasó de `verificado` a `montado` en el mismo
    segundo con el render de antes, y la huella nueva llegó dos segundos tarde.
    El diseño vive en la base y no tiene fecha de fichero: se pregunta al spec.
    """
    import subprocess

    subprocess.run(["node", "scripts/reels-spec.mjs"], capture_output=True,
                   env=dict(os.environ, REELS_PEDIDOS=str(n)))


def hay_que(nombre, n, refresca=False):
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
    if refresca and nombre == "render":
        refresca_spec(n)
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

    import rutas
    ns = [int(x) for x in sys.argv[1:] if x.isdigit()] or rutas.piezas()
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
