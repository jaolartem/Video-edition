"""Que hay DETRAS del subtitulo en cada escena: cuanta luz, cuanto grano y cuanto se mueve.

Jaime, 6-9-2026, viendo las siete con el cc puesto: *«los CC estan feos; pueden
ser a negativo solamente para variar el cuadro negro, es decir, unos CC que se
compongan mejor respecto a la composicion»*, y *«hay varios que quedarian bien
sin el cuadro, otras a las que le queda bien y otras a las que le quedaria mejor
negativo»*.

O sea que el cuadro negro deja de ser EL tratamiento y pasa a ser uno. Lo que
decide cual toca no es el gusto: es lo que hay detras en esa escena. Esto lo
mide; quien decide es `scripts/reels/cc.mjs` y quien lo dibuja,
`src/components/captionBand/Plana.tsx`.

## Que se mide, y por que estas tres

- **`luz`** — la luma media de la banda. Sobre un fondo claro el bloque negro no
  es un fondo, es un agujero.
- **`grano`** — la desviacion tipica DENTRO de la banda. Es «cargado» dicho con
  un numero: una pared lisa da poco aunque este muy iluminada, y una estanteria
  da mucho aunque este oscura. Sobre grano alto el contorno no basta.
- **`movimiento`** — cuanto cambia la banda de un fotograma al siguiente. Es la
  mitad que ninguna medida estatica ve, y es justo el argumento del negativo: un
  color elegido a mano vale para el fotograma en que se eligio.

## Donde se mide

En la banda que ocupa el cc **de esa pieza**, que no es siempre la misma:
`barbilla` (960-1160 px) es lo normal, `franja` es donde baja mientras el rotulo
del gancho esta en cuadro, y `cabeza` es el hueco de encima de su coronilla,
donde sube cuando de verdad cabe. Se miden las tres y quien decide elige;
adivinar aqui cual toca seria escribir la regla del sitio por segunda vez.

## Una sola pasada de decodificacion

Sacar cinco fotogramas por escena con `-ss` son ciento y pico invocaciones de
ffmpeg por pieza. Se decodifica **una vez** a `MUESTRAS` fps en gris y reducido,
y las escenas se reparten los fotogramas por su sitio en la linea montada. Y el
`format=gray` va DELANTE del `scale`: con aceleracion los frames vuelven en NV12
y sin declararlo el filtro los trata distinto (gotcha 5 de `docs/entorno.md`).

    python scripts/dominio/trasfondo.py 2      # solo reel-02
    python scripts/dominio/trasfondo.py        # las siete
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gpu  # noqa: E402

#: A que resolucion se mide. Un quinto del cuadro: la banda del cc sigue siendo
#: 40x190 px, de sobra para separar una pared lisa de una estanteria, y la
#: pasada entera cabe en memoria sin pelear.
ANCHO, ALTO = 216, 384

#: Fotogramas por segundo que se muestrean. Seis bastan para ver si la banda se
#: mueve —lo que buscamos es si CAMBIA, no seguir el movimiento— y dejan la
#: pasada en unos pocos megas.
MUESTRAS = 6

#: Lo minimo para poder decir algo de una escena. Con menos, `movimiento` no
#: existe: hace falta al menos un par de fotogramas para restar.
MINIMO = 2


def _marca():
    """Lo declarado: los suelos de las tres bandas, su alto y la regla de la cabeza.

    Las tres son la misma banda apoyada en tres sitios: el alto sale de
    `franja.json` —que es donde vive `layout.captionBand`— y el suelo de la
    franja tambien, porque es la banda de T-02 y ese numero tiene dueño.
    """
    raiz = os.path.join("src", "brand")
    with open(os.path.join(raiz, "cc.json"), encoding="utf-8") as f:
        cc = json.load(f)
    with open(os.path.join(raiz, "franja.json"), encoding="utf-8") as f:
        fr = json.load(f)
    return (fr["alto"],
            {"barbilla": cc["suelo_barbilla"], "franja": fr["suelo"]},
            cc["cabeza"])


def _escenas(n):
    """Los tramos del corte en la linea montada, del plan de la pieza."""
    plan = os.path.join("work", "scenes", f"reel-{n:02d}", "plan-full.json")
    if not os.path.exists(plan):
        return []
    with open(plan, encoding="utf-8") as f:
        escenas = json.load(f)["escenas"]
    t, tramos = 0.0, []
    for i, e in enumerate(escenas):
        dura = float(e.get("duracion") or 0)
        if dura > 0:
            tramos.append({"escena": i, "beat": e.get("beat"),
                           "desde": round(t, 3), "hasta": round(t + dura, 3)})
        t += dura
    return tramos


def _coronilla(n):
    """Donde cae su coronilla, medida por `sujeto.py`. `None` si no esta."""
    f = os.path.join("work", "scenes", f"reel-{n:02d}", "cara.json")
    if not os.path.exists(f):
        return None
    with open(f, encoding="utf-8") as g:
        return json.load(g).get("coronilla")


def _gris(video):
    """El video entero en gris y reducido, a `MUESTRAS` fps. `None` si falla."""
    import numpy as np

    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", *gpu.decodifica(), "-i", video,
         "-vf", f"fps={MUESTRAS},format=gray,scale={ANCHO}:{ALTO}",
         "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True).stdout
    n = ANCHO * ALTO
    if len(crudo) < n:
        return None
    return (np.frombuffer(crudo[:len(crudo) // n * n], dtype=np.uint8)
            .reshape(-1, ALTO, ANCHO).astype(np.float32) / 255.0)


def _medida(cubo, arriba, abajo):
    """Luz, grano y movimiento de esa banda, sobre los fotogramas dados."""
    import numpy as np

    a, b = int(round(ALTO * arriba)), int(round(ALTO * abajo))
    if b - a < 2 or len(cubo) < MINIMO:
        return None
    banda = cubo[:, a:b, :]
    porFrame = banda.reshape(len(banda), -1)
    return {
        "luz": round(float(porFrame.mean()), 4),
        "grano": round(float(porFrame.std(axis=1).mean()), 4),
        # Entre fotogramas MUESTREADOS, o sea a 1/6 de segundo. No es velocidad:
        # es cuanto ha cambiado lo que hay detras mientras se lee una linea.
        "movimiento": round(
            float(np.abs(np.diff(porFrame, axis=0)).mean()), 4),
        # **Lo que el negativo daria de verdad, y no se puede deducir de la luz.**
        #
        # `difference` con blanco devuelve `1 - fondo`, asi que el contraste
        # contra el fondo es |1 - 2L| **pixel a pixel**: maximo en el negro y en
        # el blanco, y CERO en el gris medio. Un fondo de luma 0,47 —la pared de
        # encima de su cabeza en reel-06— sale invertido a 0,53, o sea invisible.
        # Sin medir esto, «fondo claro -> negativo» manda el subtitulo justo al
        # unico sitio donde el negativo no existe.
        "contraste": round(float(np.abs(1.0 - 2.0 * porFrame).mean()), 4),
        "fotogramas": int(len(banda)),
    }


def de_la_pieza(n):
    """Mide las tres bandas de cada escena y lo deja donde el spec lo lee.

    Guarda `work/scenes/reel-NN/trasfondo.json`. La pasada de decodificacion
    cuesta unos segundos por pieza y el spec se arma muchas veces, asi que se
    guarda igual que `huecos.json`.

    Devuelve `None` si falta el video, el plan o ffmpeg: quien lo lea decide que
    hacer con eso, que es lo contrario de rellenarlo con un valor plausible.
    """
    video = f"public/reel-{n:02d}.mp4"
    tramos = _escenas(n)
    if not os.path.exists(video) or not tramos:
        return None
    cubo = _gris(video)
    if cubo is None:
        return None

    alto, suelos, cabeza = _marca()
    coronilla = _coronilla(n)
    if coronilla:
        # El cc que sube al hueco de encima de su cabeza se apoya un pelo por
        # debajo de su pelo, para no morderla. El margen lo declara `cc.json`.
        suelos = {**suelos, "cabeza": coronilla - cabeza["margen"] / 1920.0}
    salida = []
    for tr in tramos:
        i = int(tr["desde"] * MUESTRAS)
        j = max(i + MINIMO, int(tr["hasta"] * MUESTRAS))
        trozo = cubo[i:j]
        medidas = {k: _medida(trozo, max(0.0, s - alto), s)
                   for k, s in suelos.items()}
        medidas = {k: v for k, v in medidas.items() if v}
        if medidas:
            salida.append({**tr, "bandas": medidas})
    if not salida:
        return None
    d = os.path.join("work", "scenes", f"reel-{n:02d}")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "trasfondo.json"), "w", encoding="utf-8") as f:
        json.dump({"muestras_por_s": MUESTRAS, "coronilla": coronilla,
                   "tramos": salida}, f, ensure_ascii=False, indent=1)
    return salida


if __name__ == "__main__":
    piezas = [int(a) for a in sys.argv[1:]] or list(range(1, 8))
    for n in piezas:
        m = de_la_pieza(n)
        if not m:
            print(f"reel-{n:02d}: sin medir (falta video, plan o ffmpeg)")
            continue
        b = m[0]["bandas"]
        cual = "cabeza" if "cabeza" in b else "barbilla"
        luz = sum(t["bandas"][cual]["luz"] for t in m if cual in t["bandas"])
        print(f"reel-{n:02d}: {len(m)} escenas · banda {cual} ·"
              f" luz media {luz / len(m):.3f}")
