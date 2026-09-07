"""Cinco fotogramas por escena, para que la revisión final se haga MIRANDO.

Jaime: *«el diseñador, como parte de la última prueba, siempre va a coger cada
escena y va a tomar 5 fotogramas repartidos de la escena, va a verlos, y con
esos decide que todo está bien o si algo se rompió; incluso puede optimizar
algo, aunque sólo si es un cambio urgente»*.

## Por qué mirar y no razonar

Los dos pasos que juzgan la pieza —el que compone y el que la da por vista—
trabajaban con el dossier: qué tablero se declaró, en qué segundo, con qué
props. Eso dice **lo que se pidió**, no lo que salió.

Y la diferencia no es teórica. El 5 de septiembre las piezas entregadas llevaban
escritas en pantalla las palabras «FUSION», «DESVIO», «LISTANUMERADA» y
«EVIDENCECARD» —el nombre interno de la forma, porque diecinueve `kind` caían en
un componente que rotula lo que no sabe dibujar—, dos tarjetas de `$44` y `$46`
superpuestas, y tres líneas encimadas sobre la cara. **Nada de eso aparece en el
dossier**: ahí todo estaba declarado correctamente.

Un frame lo enseña en un segundo.

## Cinco, y repartidos

Uno solo cae donde caiga: en la entrada del tablero, cuando aún está entrando, o
en la salida. Cinco repartidos por la escena —sin los bordes, que son la
animación— muestran el estado estable, y bastan para ver un solape, un texto
cortado, un rótulo de diagnóstico o un elemento fuera de cuadro.

## Y lo que se puede tocar con ellos delante

Lo dijo con su límite puesto: **sólo un cambio urgente**. Esto es la última
prueba, no otra ronda de diseño; lo que sale de aquí es «está bien», «esto se
rompió» o «esto hay que cambiarlo ya y por esto».

    python scripts/fotogramas.py 3        # los saca para reel-03
    python scripts/fotogramas.py          # las siete
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

#: Cuántos por escena. Los pone Jaime.
CUANTOS = 5

#: Qué fracción de la escena se ignora en cada extremo. Los bordes son la
#: animación —el tablero entrando o saliendo— y ahí todo parece medio roto.
#: Lo que se juzga es el estado estable.
MARGEN = 0.12

SALIDA = "work/fotogramas/{slug}"
RENDER = "out/reels/reel-R{n}.mp4"


def escenas(slug):
    """Las escenas de la pieza con su tramo en el montaje, o `[]`."""
    f = f"work/scenes/{slug}/plan-full.json"
    if not os.path.exists(f):
        return []
    with open(f, encoding="utf-8") as fh:
        plan = json.load(fh)["escenas"]
    fuera, t = [], 0.0
    for i, e in enumerate(plan, 1):
        dura = e["origen_hasta"] - e["origen_desde"]
        fuera.append({"n": i, "desde": t, "hasta": t + dura,
                      "etapa": e.get("etapa_orden") or e.get("beat")})
        t += dura
    return fuera


def cuando(escena, cuantos=CUANTOS):
    """Los segundos donde mirar, repartidos y sin los bordes."""
    a, b = escena["desde"], escena["hasta"]
    dura = b - a
    if dura <= 0:
        return []
    borde = dura * MARGEN
    a, b = a + borde, b - borde
    if b <= a:                                     # escena muy corta: su centro
        return [(escena["desde"] + escena["hasta"]) / 2]
    return [a + (b - a) * k / (cuantos - 1) for k in range(cuantos)]


def de_la_cinta(toma, desde, hasta, cuantos=CUANTOS, etiqueta=""):
    """Cinco fotogramas de un tramo de CINTA, para verlo antes de elegirlo.

    Jaime, despues de que la deteccion por texto fallara: *«no, esos ojos no
    sirven, ya han fallado. Que tome cinco fotogramas repartidos por toda la
    escena y mire la foto»*.

    La diferencia con `sacar()` es cuando: aquella saca del render —lo que ya
    salio— y esta saca de la cinta, **antes de elegir**. El que compone escoge
    entre tomas que todavia no existen como montaje, asi que la unica manera de
    que vea si esta leyendo es enseñarle el bruto en esos segundos.

    Y por que la foto y no la medida: leer se ve —los ojos bajan— y no se
    deduce. La literalidad del texto decia que si lo hacia, y fallo: una toma
    puede repetir el libreto de memoria y otra improvisar leyendo a ratos.
    """
    import rutas

    # `rutas.cinta()` sabe resolver los dos casos: la cinta suelta y la carpeta
    # con angulos, donde el principal es el primero por orden alfabetico. No se
    # arma la ruta aqui: es la clase de literal que este proyecto cobra caro.
    mp4 = rutas.cinta(toma)
    if not mp4 or not os.path.exists(mp4):
        return []
    fuera = os.path.join("work", "fotogramas", "cinta", toma)
    os.makedirs(fuera, exist_ok=True)
    dura = max(0.0, hasta - desde)
    if dura <= 0:
        return []
    borde = dura * MARGEN
    a, b = desde + borde, hasta - borde
    if b <= a:
        a = b = (desde + hasta) / 2
    tiros = []
    for k in range(cuantos):
        t = a if cuantos < 2 else a + (b - a) * k / (cuantos - 1)
        jpg = os.path.join(fuera, f"{etiqueta or 'x'}-{t:.1f}.jpg")
        r = subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", mp4,
             "-frames:v", "1", "-q:v", "4", "-vf", "scale=640:-2", jpg],
            capture_output=True)
        if r.returncode == 0 and os.path.exists(jpg):
            tiros.append({"en": round(t, 2), "fichero": jpg.replace("\\", "/")})
    return tiros


def _del_still(slug):
    """Los fotogramas que dejo `mirar.sh`, en la forma que devuelve `sacar`.

    Misma forma para las dos procedencias —del video o del bundle— porque quien
    los mira no tiene por que saber de donde salieron: son las mismas escenas y
    los mismos cinco momentos.
    """
    import glob

    fuera = []
    for e in escenas(slug):
        tiros = []
        for jpg in sorted(glob.glob(os.path.join(
                "work", "still", slug, f"e{e['n']:02d}-*"))):
            tiros.append({"fichero": jpg.replace("\\", "/")})
        if tiros:
            fuera.append({"escena": e["n"], "etapa": e["etapa"],
                          "desde": round(e["desde"], 2),
                          "hasta": round(e["hasta"], 2), "mira": tiros,
                          "de": "stills del bundle, la pieza aun no esta montada"})
    return fuera


def sacar(n, cuantos=CUANTOS):
    """Deja los fotogramas en disco y devuelve qué sacó, escena por escena."""
    slug = f"reel-{n:02d}"
    mp4 = RENDER.format(n=n)
    # **Si no hay video, se renderizan los CINCO FOTOGRAMAS, no el video.**
    #
    # Jaime, 7-9-2026: *«ahora si es montaje nuevo o remontaje si renderiza esos
    # 5 frames, no mas»*. Y el 6-9, dando el criterio: *«si pueden renderizar
    # solo cinco fotogramas o tres por escena, es lo que necesitamos... con eso
    # pueden ver que lo que estan haciendo tiene sentido estetico y que esta
    # bien; unos minutos mas, pero muchos menos que cuando sale mal»*.
    #
    # Las dos mitades ya existian y no se hablaban: `mirar.sh` sabe sacar stills
    # del bundle —1,9 s cada uno reutilizando un solo Chrome— y esto se rendia
    # con «no esta el mp4». Asi que para que alguien pudiera MIRAR una pieza
    # habia que renderizarla entera antes, que es el orden al reves: se mira
    # para decidir si merece renderizarse.
    #
    # Lo que sale del render existente se saca con ffmpeg, que es medio segundo;
    # esto es lo otro — ver lo que todavia no existe.
    if not os.path.exists(mp4):
        r = subprocess.run(["bash", "scripts/mirar.sh", str(n), str(cuantos)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return None, (f"no esta {mp4} y no se pudieron renderizar los"
                          f" {cuantos} fotogramas: "
                          + (r.stderr or "")[-160:].strip())
        return _del_still(slug), None
    fuera = os.path.join(*SALIDA.format(slug=slug).split("/"))
    os.makedirs(fuera, exist_ok=True)
    hechas = []
    for e in escenas(slug):
        tiros = []
        for k, t in enumerate(cuando(e, cuantos), 1):
            jpg = os.path.join(fuera, f"e{e['n']:02d}-{k}.jpg")
            r = subprocess.run(
                ["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", mp4,
                 "-frames:v", "1", "-q:v", "3", jpg],
                capture_output=True)
            if r.returncode == 0 and os.path.exists(jpg):
                tiros.append({"en": round(t, 2), "fichero": jpg.replace("\\", "/")})
        hechas.append({"escena": e["n"], "etapa": e["etapa"],
                       "desde": round(e["desde"], 2),
                       "hasta": round(e["hasta"], 2), "mira": tiros})
    return hechas, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--cuantos", type=int, default=CUANTOS)
    a = ap.parse_args()
    total = 0
    for n in (a.reels or range(1, 8)):
        hechas, mal = sacar(n, a.cuantos)
        if mal:
            print(f"  reel-{n:02d}: {mal}")
            continue
        tiros = sum(len(e["mira"]) for e in hechas)
        total += tiros
        print(f"  reel-{n:02d}: {len(hechas)} escena(s), {tiros} fotograma(s)"
              f" -> {SALIDA.format(slug=f'reel-{n:02d}')}")
    print(f"\nfotogramas: {total} para mirar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
