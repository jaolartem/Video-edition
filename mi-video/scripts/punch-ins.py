"""
Genera encuadres distintos a partir de UNA sola cámara fija en 4K.

La idea
-------
El material está grabado en 4K y la salida es 1080×1920. Eso deja **2× de margen
de recorte gratis**: se pueden sacar cinco encuadres distintos —general, medio,
medio corto, primer plano, manos— y todos siguen nítidos, porque incluso
recortando al 50% queda resolución de sobra para 1080.

Así el «cambio de plano cada 3 segundos» del gancho se resuelve **sin IA y sin
coste**, y con continuidad perfecta por construcción: es literalmente el mismo
plano, así que no hay nada que casar.

Cómo se localiza al sujeto
--------------------------
No hace falta detectar caras: en una cámara fija, **el sujeto es lo que se
mueve**. Se comparan fotogramas consecutivos y se toma el centroide del cambio.
Todo lo estático —pared, monitor, escritorio, cables— desaparece solo.

Se probó antes con detalle de alta frecuencia y **falló de forma verificable**:
el monitor con código en pantalla tiene muchísimo más detalle que una cara, así
que el ancla se iba a la derecha y el primer plano cortaba media cabeza. El
movimiento no tiene ese problema — la pantalla no se mueve.

Sigue siendo heurística: si hay algo moviéndose de fondo, se equivoca. Por eso
el ancla se imprime y se puede sobrescribir con `--anchor-x/--anchor-y`.

Uso:
    python scripts/punch-ins.py --source "G:/.../X.mp4" --plan work/scenes/reel-01/plan.json
"""
import argparse
import json
import os
import subprocess
import sys


import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gpu  # noqa: E402



def sample_frames(source, times, w=270):
    """Fotogramas en gris, pequeños: el ancla no necesita resolución."""
    out = []
    for t in times:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error"] + gpu.decodifica() + ["-ss", str(t), "-i", source,
             "-frames:v", "1", "-vf", f"scale={w}:-1,format=gray",
             "-f", "rawvideo", "-"],
            capture_output=True,
        ).stdout
        if not raw:
            continue
        h = len(raw) // w
        if h < 10:
            continue
        out.append(np.frombuffer(raw[:w * h], dtype=np.uint8).reshape(h, w).astype(float))
    return out


def find_anchor(frames):
    """
    Centroide del MOVIMIENTO: en camara fija, lo que se mueve es la persona.

    Se acumula la diferencia absoluta entre fotogramas consecutivos. La pared,
    el monitor y el escritorio se anulan; queda el sujeto.

    El eje Y se toma sobre el movimiento de la mitad superior porque el gesto de
    las manos, que se mueve mucho mas que la cara, bajaria el ancla y el encuadre
    cerrado decapitaria al sujeto.
    """
    if len(frames) < 2:
        return 0.5, 0.35
    acc = None
    for a, b in zip(frames, frames[1:]):
        if a.shape != b.shape:
            continue
        d = np.abs(b - a)
        acc = d if acc is None else acc + d
    if acc is None:
        return 0.5, 0.35

    h, w = acc.shape
    # Suavizado: el ruido de sensor tambien "se mueve" y hay que ignorarlo.
    from scipy.ndimage import uniform_filter
    acc = uniform_filter(acc, size=9)

    thr = np.percentile(acc, 92)
    mask = acc >= thr
    if mask.sum() < 20:
        return 0.5, 0.35
    ys, xs = np.nonzero(mask)

    # Altura: el BORDE SUPERIOR del movimiento, no su centro.
    #
    # El centro fallaba de forma verificable: las manos gesticulan a la altura
    # del pecho, caen dentro de la mitad superior del cuadro y arrastraban el
    # ancla hacia abajo, asi que el recorte cerrado cortaba la frente. El
    # percentil 15 de las posiciones con movimiento cae en la cabeza, que es lo
    # mas alto que se mueve.
    if ys.size <= 20:
        return 0.5, 0.30
    coronilla = float(np.percentile(ys, 15))
    ay = coronilla / h

    # Anchura: **solo la banda de la cabeza y los hombros**, no todo el
    # movimiento del cuadro.
    #
    # El docstring de arriba ya avisaba de que el centroide se equivoca "si hay
    # algo moviendose de fondo". En la sesion de noche hay un husky, y un perro
    # grande moviendose en el suelo pesa mas que una cara. La firma quedo en el
    # plan de reel-03: el recorte `medio` salio pegado al borde izquierdo
    # (x=0, recortado por el clamp), que es lo que pasa cuando el ancla se va.
    #
    # El perro esta en el suelo, muy por debajo de la coronilla, asi que
    # restringir la X a la banda de la cabeza lo excluye por construccion — y
    # de paso quita el tiron de las manos, que ya habia causado problemas en Y.
    banda = (ys >= coronilla) & (ys <= coronilla + 0.18 * h)
    ax = float(xs[banda].mean() / w) if banda.sum() > 10 else float(xs.mean() / w)
    return ax, ay


# Encuadres, como fracción de la altura del frame original.
# El más cerrado es 0.52: por debajo de la mitad se empieza a notar el reescalado
# al subir a 1080 de ancho.
# **La cabeza es SIEMPRE el eje.** Cada encuadre se define solo por cuanto
# abarca; la altura de la cabeza dentro del cuadro no cambia nunca. Asi el
# sujeto no se mueve al cortar entre planos: cambia el tamano, no la posicion,
# que es lo que hace que una serie de punch-ins se lea como una sola camara y no
# como saltos.
#
# Hubo dos intentos fallidos antes de esto, los dos verificados en imagen:
#   - Un encuadre "manos" desplazado hacia abajo encuadraba la entrepierna.
#   - Los desplazamientos tenian el signo invertido: subir el recorte empuja la
#     cabeza HACIA ABAJO dentro del cuadro, no hacia arriba.
# Fijando la cabeza, ninguno de los dos errores puede repetirse.
# **Regla de tercios.** La cara va en la interseccion de la primera linea
# horizontal con la vertical central, y va ahi en TODAS las tomas: al cortar
# entre planos el rostro no se mueve, solo cambia cuanto abarca el cuadro. Eso
# es lo que hace que una serie de punch-ins se lea como una sola camara.
#
# El valor no es 1/3 exacto porque el ancla no es la cara sino el borde superior
# del movimiento —la coronilla—. Medido sobre render: con 0.22 los ojos caian al
# 23% de altura; 0.32 los sube a la primera linea de tercios.
HEAD_POS = 0.32

# Cuanto por debajo de la coronilla caen los ojos, en fraccion de la altura del
# cuadro. El ancla mide el borde superior del movimiento —la coronilla—, pero el
# punto que el espectador sigue, y el que tiene que quedarse quieto en un
# acercamiento, son los ojos.
OJOS_BAJO_CORONILLA = 0.05

# **La cara es lo que se quiere mostrar.** Por eso no hay plano general: a cuadro
# completo el rostro ocupa una fraccion minima de una pantalla de movil vista a
# distancia de brazo, y el gesto facial —que es donde esta la interpretacion— se
# pierde. El mas abierto de la serie ya es un plano medio.
#
# El mas cerrado es 0.46: por debajo, subir a 1080 de ancho empieza a ablandar.
# El plano completo VUELVE a la serie: la composicion original fue intencional
# —encuadre, lampara, fondo— y merece presentarse. Recortarlo siempre seria
# tirar una decision que ya estaba tomada en el rodaje.
def frac_completo(ay):
    """El encuadre mas abierto que **sigue respetando el eje de la cabeza**.

    `completo` valia 1.00 — el sensor entero — y eso no es un encuadre, es la
    ausencia de uno: con el recorte a cuadro completo el ancla no tiene ningun
    efecto (x=0, y=0 siempre), asi que la cabeza cae donde caiga. Era el unico
    miembro de la serie que ignoraba la regla que gobierna a todos los demas.

    Se noto al comparar las dos sesiones, medido con `medir-sujeto.py`:

        tarde  R1 0.229   R2 0.300   R5 0.285   <- coronilla / alto del cuadro
        noche  R3 0.383   R4 0.431   R6 0.377

    De noche Jaime esta reclinado y mas lejos, asi que a cuadro completo la
    coronilla cae al 38-43% en vez de al 32%: la cara sale pequena y baja, el
    rotulo aterriza sobre el sofa en vez de sobre el torso, y los seis dejan de
    parecer la misma serie. No es un fallo del rodaje — es que 1.00 significa
    una cosa distinta en cada habitacion.

    Aqui se deriva en vez de fijarse. El recorte anclado a la cabeza cabe dentro
    del sensor solo si se cumplen las dos cosas a la vez:

        arriba:  y = ay - HEAD_POS*frac >= 0     ->  frac <= ay / HEAD_POS
        abajo:   y + frac <= 1                   ->  frac <= (1-ay)/(1-HEAD_POS)

    El mas abierto es el mayor `frac` que cumple ambas. Da 0.72 / 0.94 / 0.89 de
    tarde y 0.91 / 0.84 / 0.92 de noche, y en los seis la coronilla acaba
    exactamente en la primera linea de tercios.

    **La decision del rodaje se conserva donde aplica.** «El plano completo
    busca presentarse» sigue siendo cierto: se preserva como principio —el mas
    abierto de la serie— en vez de como el numero 1.00, que solo daba el
    encuadre pretendido cuando el sujeto se sentaba a la distancia de la tarde.
    """
    return min(1.0, ay / HEAD_POS, (1 - ay) / (1 - HEAD_POS))


ENCUADRES = [
    # `completo` se recalcula por toma en tiempo de plan; el 1.00 es solo el
    # tope. Ver `frac_completo`.
    ("completo",     1.00),
    ("medio",        0.78),
    ("primer plano", 0.52),
    # Pecho: mismo eje, algo mas abierto. Las manos entran por abajo solas.
    ("pecho",        0.66),
    ("primerisimo",  0.46),
]


def crop_rect(frac, anchor, src_w, src_h):
    """
    Rectangulo 9:16 con la cabeza siempre a la misma altura del cuadro.

    No hay desplazamiento configurable: el ancla manda y `HEAD_POS` fija donde
    cae dentro del recorte. Cuanto mas cerrado el encuadre, menos abarca — pero
    la cabeza no se mueve.
    """
    ch = src_h * frac
    cw = ch * 9 / 16
    if cw > src_w:
        cw = src_w
        ch = cw * 16 / 9
    ax, ay = anchor
    x = ax * src_w - cw / 2
    y = ay * src_h - ch * HEAD_POS
    x = max(0, min(x, src_w - cw))
    y = max(0, min(y, src_h - ch))
    return int(round(x)), int(round(y)), int(round(cw)), int(round(ch))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--anchor-x", type=float)
    ap.add_argument("--anchor-y", type=float)
    # Un ancla para TODO el plan en vez de una por escena.
    #
    # Para el gancho —dos o tres escenas— medir cada una es barato y mas
    # preciso. Para un reel entero son 20-30 escenas por pieza y cada medicion
    # son doce saltos dentro de un 4K que vive en Google Drive: la diferencia es
    # entre minutos y horas.
    #
    # Y la camara esta FIJA con el sujeto sentado, que es justo el caso en que
    # un ancla global vale: lo que cambia entre escenas es el gesto, no la
    # posicion. El recorrido se toma como el mayor medido en el muestreo, asi
    # que la proteccion de «el sujeto no puede salirse» sigue en pie —con un
    # margen mas conservador, no menos.
    ap.add_argument("--ancla-global", action="store_true")
    args = ap.parse_args()

    plan = json.load(open(args.plan, encoding="utf-8"))
    escenas = plan["escenas"]

    probe = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height", "-of", "json", args.source],
        capture_output=True, text=True).stdout)
    sw, sh = probe["streams"][0]["width"], probe["streams"][0]["height"]
    # El movil graba vertical con metadato de rotacion: ffmpeg lo endereza al
    # decodificar, asi que el frame real es el alto por el ancho.
    if sw > sh:
        sw, sh = sh, sw

    # Pares muy juntos (0,4 s): a mayor separacion el sujeto se ha desplazado
    # tanto que la diferencia marca dos posiciones, no una.
    def ancla_en(t0, t1):
        """Ancla medida SOLO dentro de esa escena."""
        pasos = max(3, min(6, int((t1 - t0) / 0.5)))
        ts = []
        for k in range(pasos):
            t = t0 + (t1 - t0) * (k + 0.5) / pasos
            ts += [t, t + 0.35]
        fr = sample_frames(args.source, ts)
        return find_anchor(fr) if len(fr) >= 2 else (0.5, 0.30)

    # Tope fisico del recorrido de una persona SENTADA en 3 s, en fraccion de
    # cuadro. Por encima de esto no se ha movido el sujeto: se ha movido la
    # medida. Es el mismo criterio del filtro de plausibilidad de la voz —si el
    # numero esta fuera del rango fisico de lo que mide, el numero esta mal
    # antes que el mundo.
    RECORRIDO_MAX = 0.22

    def recorrido(t0, t1):
        """
        Cuanto se MUEVE el sujeto dentro de la escena.

        Un recorte se calcula sobre una posicion media, pero el sujeto se
        desplaza: si el recorrido es grande y el encuadre cerrado, se sale del
        cuadro. Verificado — en un render el sujeto quedaba fuera al segundo 9.

        Se mide con el **rango intercuartilico**, no con maximo menos minimo.
        En reel-04 el max-min daba 870 px de desplazamiento horizontal en tres
        segundos: eso no lo hace nadie sentado en un sillon, lo hace el husky
        cruzando el plano. Una sola ventana en la que el perro domina el
        movimiento se lleva el maximo, el control de encuadre concluye que el
        sujeto no cabe y **abre los dos planos a cuadro completo** — justo el
        encuadre que se acaba de arreglar. El IQR no se deja arrastrar por una
        ventana suelta.
        """
        pasos = max(3, min(6, int((t1 - t0) / 0.5)))
        xs, ys = [], []
        for k in range(pasos):
            t = t0 + (t1 - t0) * (k + 0.5) / pasos
            fr = sample_frames(args.source, [t, t + 0.35])
            if len(fr) < 2:
                continue
            a, b = find_anchor(fr)
            xs.append(a); ys.append(b)
        if len(xs) < 2:
            return 0.0, 0.0
        dx = float(np.percentile(xs, 75) - np.percentile(xs, 25))
        dy = float(np.percentile(ys, 75) - np.percentile(ys, 25))
        crudo_x = max(xs) - min(xs)
        crudo_y = max(ys) - min(ys)
        if max(crudo_x, crudo_y) > RECORRIDO_MAX:
            print(f"     ojo: recorrido crudo {crudo_x:.2f}x{crudo_y:.2f} fuera de "
                  f"rango fisico — se usa el IQR {dx:.2f}x{dy:.2f}")
        return min(dx, RECORRIDO_MAX), min(dy, RECORRIDO_MAX)

    # **Un ancla POR FUENTE, no una por pieza.**
    #
    # Es el aprendizaje 20 llevado a su conclusión: de tarde Jaime está más
    # cerca y más alto en cuadro, de noche reclinado y más lejos — la coronilla
    # va de 0,229 a 0,431 según la sesión. Un ancla común para material de dos
    # grabaciones encuadra mal el de una de las dos, y **sin avisar**.
    #
    # Con el ancla por fuente, una pieza puede usar material de varias cintas y
    # cada escena se encuadra con la medida de la suya. Es lo que faltaba para
    # que el corpus entero fuera utilizable.
    def fuente_de(e):
        f = e.get("fuente")
        if not f:
            return args.source
        return os.path.join(os.path.dirname(args.source), f"{f}.mp4")

    anclas = {}
    global_ancla = None
    if args.ancla_global:
        for fuente in sorted({fuente_de(e) for e in escenas}):
            suyas = [e for e in escenas if fuente_de(e) == fuente]
            ts, xs, ys = [], [], []
            for e in suyas:
                m = (e["origen_desde"] + e["origen_hasta"]) / 2
                ts += [m, m + 0.35]
            fr = sample_frames(fuente, ts)
            for a, b in zip(fr[::2], fr[1::2]):
                if a.shape != b.shape:
                    continue
                ax_, ay_ = find_anchor([a, b])
                xs.append(ax_)
                ys.append(ay_)
            if xs:
                anclas[fuente] = (
                    (float(np.median(xs)), float(np.median(ys))),
                    min(float(np.percentile(xs, 75) - np.percentile(xs, 25)),
                        RECORRIDO_MAX),
                    min(float(np.percentile(ys, 75) - np.percentile(ys, 25)),
                        RECORRIDO_MAX))
            else:
                anclas[fuente] = ((0.5, 0.30), 0.0, 0.0)
            (gx, gy), gdx, gdy = anclas[fuente]
            marca = "" if len(suyas) == len(escenas) else \
                f"  [{os.path.basename(fuente)[:15]}, {len(suyas)} escenas]"
            print(f"  ancla global {gx:.3f},{gy:.3f} "
                  f"· recorrido {gdx:.3f}x{gdy:.3f} (n={len(xs)}){marca}")
        propia = anclas.get(args.source) or anclas[list(anclas)[0]]
        global_ancla, dxg, dyg = propia

    idx = 0
    for i, e in enumerate(escenas):
        if e.get("hereda_encuadre") and i > 0:
            prev = escenas[i - 1]
            e.update({k: prev[k] for k in ("encuadre", "crop", "filtro", "reescalado")})
            print(f"  {i} {prev['encuadre']:12} (hereda, {e['duracion']:.1f}s)")
            continue

        t0, t1 = e["origen_desde"], e["origen_hasta"]
        if global_ancla is not None:
            ax, ay = global_ancla
            dx, dy = dxg, dyg
        else:
            ax, ay = ancla_en(t0, t1)
            dx, dy = recorrido(t0, t1)
        if args.anchor_x is not None: ax = args.anchor_x
        if args.anchor_y is not None: ay = args.anchor_y

        nombre, frac = ENCUADRES[idx % len(ENCUADRES)]
        if nombre == "completo":
            frac = frac_completo(ay)
        idx += 1

        # **El sujeto no puede salirse. Nunca.**
        #
        # Si el recorrido dentro de la escena no cabe con margen en el recorte,
        # se ABRE el encuadre hasta que quepa. Antes que un plano bonito que
        # pierde al sujeto, un plano mas abierto que lo sostiene.
        abierto = False
        for _ in range(6):
            x, y, cw, ch = crop_rect(frac, (ax, ay), sw, sh)
            cabe_x = dx * sw < cw * 0.30
            cabe_y = dy * sh < ch * 0.22
            if (cabe_x and cabe_y) or frac >= 1.0:
                break
            frac = min(1.0, frac * 1.18)
            abierto = True

        x, y, cw, ch = crop_rect(frac, (ax, ay), sw, sh)
        escala = 1080 / cw
        e["encuadre"] = nombre
        e["crop"] = {"x": x, "y": y, "w": cw, "h": ch}
        e["filtro"] = f"crop={cw}:{ch}:{x}:{y},scale=1080:1920:flags=lanczos"
        e["reescalado"] = round(escala, 2)
        e["recorrido"] = {"x": round(dx, 3), "y": round(dy, 3)}

        # Destino del acercamiento, si la escena lo pide.
        #
        # Se calcula con el MISMO anclaje a la cabeza que cualquier encuadre.
        # Acercarse manteniendo el centro del recorte hacia subir la cara y la
        # cortaba por arriba — verificado en render. El eje es la cabeza tambien
        # durante el movimiento, no solo en los extremos.
        if e.get("zoom"):
            frac_fin = frac * e["zoom"]["hasta"]
            # **El acercamiento no puede desplazar la cara.**
            #
            # Antes se calculaba el rectangulo final con `crop_rect` y se
            # interpolaban x, y, w y h por separado. Cuando uno de los dos
            # rectangulos toca un borde —y con el sujeto descentrado toca casi
            # siempre— el punto de la cara NO cae en el mismo sitio de los dos,
            # asi que durante el zoom deriva en diagonal. Con la escala
            # cambiando a la vez, eso se ve como un movimiento circular y
            # desordenado, no como un acercamiento.
            #
            # Ahora el destino se deriva de la posicion EN PANTALLA del punto
            # fijo: se calcula donde cae en el recorte inicial y se obliga a que
            # caiga exactamente igual en el final. Deriva cero por construccion,
            # con borde o sin el.
            #
            # Y el punto fijo son **los ojos**, no la coronilla. El ancla mide el
            # borde superior del movimiento; los ojos caen algo mas abajo, y son
            # los que el espectador sigue.
            ojos_y = ay + OJOS_BAJO_CORONILLA
            px, py = ax * sw, ojos_y * sh
            # Posicion normalizada de los ojos dentro del recorte inicial.
            u = (px - x) / cw
            v = (py - y) / ch
            fcw = int(round(cw * frac_fin / frac))
            fch = int(round(ch * frac_fin / frac))
            fx = int(round(px - u * fcw))
            fy = int(round(py - v * fch))
            # Si el destino se sale, se acerca menos en vez de desplazarse: un
            # plano algo mas abierto es preferible a una cara que viaja.
            fx = max(0, min(fx, sw - fcw))
            fy = max(0, min(fy, sh - fch))
            e["zoom"]["crop_final"] = {"x": fx, "y": fy, "w": fcw, "h": fch}
            deriva_u = abs((px - fx) / fcw - u)
            deriva_v = abs((py - fy) / fch - v)
            print(f"     zoom -> {fcw}x{fch} en ({fx},{fy}) · "
                  f"deriva {deriva_u*100:.1f}%x{deriva_v*100:.1f}%")

        nota = ""
        if abierto:
            nota = f"  <-- ABIERTO a {frac:.2f}: el sujeto se movia {dx*sw:.0f}px"
        if escala > 1.15:
            nota += "  <-- se estira"
        print(f"  {i} {nombre:12} {cw}x{ch} en ({x},{y}) · esc {escala:.2f}x"
              f" · mov {dx*sw:.0f}x{dy*sh:.0f}px{nota}")

    json.dump(plan, open(args.plan, "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"\nplan actualizado → {args.plan}")
