"""Donde esta EL SUJETO en un fotograma, recortandolo del fondo.

Jaime, al ver su cara debajo de los titulos: *«¿y esas guardas de que protegen,
si lo que hacen es poner mi cara debajo de los titulos?»*. Y la respuesta,
despues de mirarlo: de nada, porque median mal.

## Por que no vale el movimiento

`punch-ins.py` localiza al sujeto por el **centroide del movimiento**: en camara
fija, lo que se mueve es la persona. Es barato y funciona en la mesa de trabajo.

En el sofa no. En la sesion de noche tambien se mueven **la cortina y la
lampara**, y el percentil 15 de la mascara de movimiento sube con ellas. Medido
contra el render de reel-06: el ancla decia que su coronilla caia en **0,318** del
cuadro y esta en **0,435**. Doscientos veinticinco pixeles, y con ese numero se
coloca la banda de subtitulos, la ventana de las placas y los paneles.

Su propio docstring ya avisaba —*«sigue siendo heuristica: si hay algo moviendose
de fondo, se equivoca»*— y nadie comprobo nunca cuanto.

## Que hace esto en su lugar

Segmenta a la persona con MediaPipe —el mismo `selfie_segmenter` que ya usa
`text-behind.py` para pasar el rotulo por detras de el— y devuelve el borde
superior de la silueta. Una cortina no es una persona, asi que no entra en la
mascara por mucho que se mueva.

No sustituye al ancla de `punch-ins`: **la comprueba**. El recorte se sigue
calculando igual; lo que cambia es que ahora se sabe si salio donde decia.

    python scripts/dominio/sujeto.py --video public/reel-06.mp4 --en 6.5
"""
import os
import subprocess
import sys

MODELO = os.path.join("models", "selfie_segmenter.tflite")
#: Por debajo de esto la mascara no es una persona: es ruido con forma. La
#: segmentacion devuelve confianza por pixel, y el fondo de una habitacion en
#: penumbra puntua bajo pero no cero.
SEGURO = 0.6
#: Cuantas filas seguidas tienen que dar sujeto para llamarlo coronilla. Un pixel
#: suelto en el techo es un artefacto; doce filas son una cabeza.
FILAS = 12
#: Lo que un tablero se estira por encima de la costura, en segundos. Es el
#: `SOLAPE` de `scripts/reels/lectura.mjs` (24 frames a 30 fps) y aqui hace falta
#: para que el recorte no se acabe antes que la capa que lo dibuja.
SOLAPE = 0.8


def _canon_gancho():
    """Los numeros del gancho, leidos de donde viven: `src/brand/gancho.json`.

    No se copian aqui. Es la leccion de `franja.json` y la que documenta C-259:
    un numero escrito en dos sitios son dos numeros el dia que uno se mueve, y
    este en concreto —cuanto dura el gancho— ya estaba escrito en `gancho.mjs`
    mientras el recorte se hacia a mano con el numero tecleado en la linea.
    """
    import json

    with open(os.path.join("src", "brand", "gancho.json"), encoding="utf-8") as f:
        j = json.load(f)
    return float(j["dura"]), float(j["margen"])


def _fotograma(video, t, ancho=270):
    """Un fotograma en RGB, pequeno. La silueta no necesita resolucion."""
    import numpy as np

    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", str(t), "-i", video, "-frames:v", "1",
         "-vf", f"scale={ancho}:-1,format=rgb24", "-f", "rawvideo", "-"],
        capture_output=True).stdout
    if not crudo:
        return None
    alto = len(crudo) // (ancho * 3)
    if alto < 10:
        return None
    return np.frombuffer(crudo[:ancho * alto * 3],
                         dtype=np.uint8).reshape(alto, ancho, 3)


def donde_esta(video, momentos):
    """La franja que ocupa el sujeto, en fracciones del cuadro.

    Devuelve `{coronilla, pies, visto}` promediado sobre los momentos que se
    pidan, o `None` si no se pudo segmentar ninguno. `visto` dice en cuantos
    salio, que es lo que distingue una medida de una casualidad.
    """
    import numpy as np

    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision
    except ImportError:
        return None
    if not os.path.exists(MODELO):
        return None

    opts = vision.ImageSegmenterOptions(
        base_options=mp_python.BaseOptions(model_asset_path=MODELO),
        running_mode=vision.RunningMode.IMAGE,
        output_confidence_masks=True)
    arriba, abajo = [], []
    with vision.ImageSegmenter.create_from_options(opts) as seg:
        for t in momentos:
            img = _fotograma(video, t)
            if img is None:
                continue
            m = seg.segment(mp.Image(image_format=mp.ImageFormat.SRGB,
                                     data=np.ascontiguousarray(img)))
            mask = m.confidence_masks[0].numpy_view()
            filas = (mask >= SEGURO).sum(axis=1)
            # Una fila cuenta como sujeto si al menos el 2% de su ancho lo es:
            # asi un borde de cortina mal segmentado no arrastra la coronilla.
            hay = filas >= max(3, mask.shape[1] * 0.02)
            if hay.sum() < FILAS:
                continue
            ys = np.nonzero(hay)[0]
            # La coronilla es la primera fila con FILAS seguidas por debajo.
            for i in range(len(ys) - FILAS):
                if ys[i + FILAS - 1] - ys[i] == FILAS - 1:
                    arriba.append(ys[i] / mask.shape[0])
                    abajo.append(ys[-1] / mask.shape[0])
                    break
    if not arriba:
        return None
    return {"coronilla": round(float(np.median(arriba)), 3),
            "pies": round(float(np.median(abajo)), 3),
            "visto": len(arriba)}


def de_la_pieza(n, muestras=4):
    """Mide la pieza YA CORTADA y guarda el resultado donde el spec lo lee.

    Se mide sobre `public/reel-NN.mp4` y no sobre la cinta a proposito: ahi ya
    estan aplicados el recorte, el encuadre y el acercamiento, asi que lo que
    sale es **donde queda su cara en el cuadro que ve el espectador** — que es la
    unica pregunta que importaba y la que el ancla de movimiento contestaba mal.

    Se guarda en `work/scenes/reel-NN/cara.json` porque cuesta unos segundos por
    pieza y el spec se arma muchas veces. Se rehace cuando se rehace el corte.
    """
    import json

    video = f"public/reel-{n:02d}.mp4"
    if not os.path.exists(video):
        return None
    # **Y la cara de cada escena, en el mismo fichero** (C-624). Absoluto:
    # `montar.sh` corre este fichero como script, sin paquete.
    from dominio.rostro import por_escena
    import statistics

    escenas = por_escena(n, video)
    # **La de la pieza sale de sus escenas** (C-753): la mediana de lo medido
    # en cada una. Muestrear la pieza entera aparte la volvía a mirar toda cada
    # vez que cambiaba una escena.
    co = [e["coronilla"] for e in escenas if e.get("coronilla") is not None]
    pi = [e["_pies"] for e in escenas if e.get("_pies") is not None]
    for e in escenas:
        e.pop("_pies", None)
    if not co:
        return None
    m = {"coronilla": round(statistics.median(co), 3),
         "pies": round(statistics.median(pi), 3) if pi else None, "visto": len(co)}
    m["escenas"] = escenas
    d = os.path.join("work", "scenes", f"reel-{n:02d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "cara.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    return m


def _ventanas_detras(n):
    """Que etapas pidieron algo POR DETRAS, y donde caen en el corte.

    Sale del PLAN y no de la base a proposito: `plan-reel.mjs` ya copio
    `camara.detras` a cada escena, y el plan es el mismo reloj que luego usa
    `reels/imagen.mjs` para colocar la capa. Preguntarselo a `escena_desc` seria
    la segunda copia de la misma decision, y el dia que las dos no coincidan la
    silueta saldria recortada de un tramo y apilada sobre otro.
    """
    import json

    plan = os.path.join("work", "scenes", f"reel-{n:02d}", "plan-full.json")
    if not os.path.exists(plan):
        return {}
    escenas = json.load(open(plan, encoding="utf-8"))["escenas"]
    t, ventanas = 0.0, {}
    for e in escenas:
        dura = float(e.get("duracion") or 0)
        if e.get("detras"):
            # El canto lo pide la forma del tablero: `cuadro` es un retrato de
            # canto limpio, la pegatina es papel (C-384). Lo copia `plan-reel`.
            canto = "limpio" if e.get("canto") == "limpio" else "papel"
            v = ventanas.setdefault(int(e["beat"]), [t, t, canto])
            # **Y se pasa el SOLAPE.** Un tablero se estira 0,8 s por encima de
            # la costura para taparla (`reels/lectura.mjs`), asi que la capa
            # sigue en pantalla cuando la ventana del beat ya acabo. Sin este
            # margen el recorte se queda sin fotogramas justo ahi y el sujeto se
            # congela en el ultimo, que es lo que se ve.
            v[1] = t + dura + SOLAPE
        t += dura
    # **Y el gancho pide el suyo aunque el plan no diga `detras`.** El rotulo le
    # pasa por detras de la cabeza en TODAS las piezas —es el camino, no una
    # decision de escena—, asi que su recorte es del proceso y no de una lista.
    # Estaba fuera: `portada.mjs` sabia decir que faltaba y la unica forma de
    # producirlo era teclear la linea a mano, o sea un paso que hay que acordarse
    # de correr (C-242). Y va con canto LIMPIO: se compone sobre el mismo plano
    # del que salio, y ahi la orla de fibra dibuja una pegatina (C-259).
    dura, margen = _canon_gancho()
    beat = int(escenas[0]["beat"]) if escenas else 1
    ventanas[beat] = [0.0, dura + margen, "limpio"]
    return ventanas


def recortes_de_la_pieza(n):
    """El recorte del sujeto, con alfa, para las etapas que lo pidieron.

    Es lo que faltaba para que `text-behind.py` sirviera de algo: sabia sacar la
    silueta y **nadie del render la consumia**, asi que «letras detras» llevaba
    meses en la lista de lo que no se puede pedir. Aqui se produce por etapa y
    queda en `public/`, que es de donde Remotion sirve sus ficheros.

    Va pegado a `de_la_pieza` y no en un paso aparte por la razon de siempre: un
    paso que hay que acordarse de correr no es un paso del proceso (C-242). El
    que mide donde esta su cara sobre el corte nuevo es el mismo que tiene que
    volver a recortarlo, y se llama en el mismo sitio.

    Se rehace solo si el corte es mas nuevo que el recorte: la pasada cuesta
    ~6 s de CPU por segundo de etapa y el montaje se lanza muchas veces.
    """
    video = f"public/reel-{n:02d}.mp4"
    hechos = []
    if not os.path.exists(video):
        return hechos
    for beat, (a, b, canto) in sorted(_ventanas_detras(n).items()):
        dest = os.path.join("public", "recorte", f"reel-{n:02d}-e{beat}.webm")
        ficha = os.path.splitext(dest)[0] + ".json"
        # **Y la ficha cuenta tanto como el recorte.** Ahi viven la coronilla y
        # la cabeza, que son de donde el gancho saca el sitio y el lado del
        # bloque: un recorte al dia con la ficha vieja coloca el rotulo con la
        # medida de otro corte, y eso no se ve hasta mirar el fotograma. Solo la
        # pasada de canto `limpio` la escribe, asi que solo esa la exige — con
        # la condicion a secas, el recorte del panel se rehacia SIEMPRE.
        hechos_al_dia = [dest] + ([ficha] if canto == "limpio" else [])
        # **Al día por lo que hay en su ventana, no por la fecha del corte**
        # (C-750): cambiar otra escena reescribe el mp4 entero y caducaba los
        # recortes de todas, a ~6 s de CPU por segundo de etapa. Su huella es lo
        # que el corte enseña en su ventana —qué cinta, qué tramo, qué recorte—
        # contado desde su inicio, y su canto.
        huella = _huella_ventana(n, a, b, canto)
        sello = os.path.splitext(dest)[0] + ".huella"
        if (all(os.path.exists(f) for f in hechos_al_dia) and os.path.exists(sello)
                and open(sello, encoding="utf-8").read().strip() == huella):
            hechos.append(f"e{beat} al dia")
            continue
        r = subprocess.run(
            [sys.executable, os.path.join("scripts", "text-behind.py"),
             "--video", video, "--desde", f"{a:.3f}", "--hasta", f"{b:.3f}",
             "--canto", canto, "--out", dest])
        if r.returncode == 0:
            open(sello, "w", encoding="utf-8").write(huella)
        hechos.append(f"e{beat} {a:.1f}-{b:.1f}s"
                      + ("" if r.returncode == 0 else " FALLO"))
    return hechos


def _huella_ventana(n, a, b, canto) -> str:
    """Lo que el corte enseña entre `a` y `b` segundos, contado desde `a` (C-750)."""
    import hashlib
    import json

    plan = os.path.join("work", "scenes", f"reel-{n:02d}", "plan-full.json")
    escenas = json.load(open(plan, encoding="utf-8"))["escenas"]
    t, ahi = 0.0, []
    for e in escenas:
        dura = float(e.get("duracion") or 0)
        if t < b and t + dura > a:
            ahi.append([e.get("fuente"), e.get("origen_desde"), e.get("origen_hasta"),
                        e.get("filtro"), round(t - a, 3), round(dura, 3)])
        t += dura
    crudo = json.dumps([round(b - a, 3), canto, ahi], ensure_ascii=False)
    return hashlib.sha1(crudo.encode("utf-8")).hexdigest()[:16]


def main():
    import argparse
    import json

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--video")
    p.add_argument("--en", type=float, nargs="+", help="segundos donde mirar")
    p.add_argument("piezas", nargs="*", type=int,
                   help="numeros de pieza: mide el corte y guarda")
    a = p.parse_args()
    if a.video and a.en:
        print(json.dumps(donde_esta(a.video, a.en), ensure_ascii=False))
        return
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import rutas
    for n in a.piezas or rutas.piezas():
        m = de_la_pieza(n)
        r = recortes_de_la_pieza(n)
        print(f"R{n}: {json.dumps(m, ensure_ascii=False) if m else 'sin corte'}"
              + (f" · recortes: {', '.join(r)}" if r else ""))


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    main()
