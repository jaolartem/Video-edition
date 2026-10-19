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
import textwrap

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


def de_la_escena(slug, etapa, cuantos=CUANTOS):
    """De 3 a 5 fotogramas repartidos **a lo largo de la escena**, no de la ventana.

    Jaime, 10-9-2026: *«el compositor tiene que ver que no haya escenas leyendo a
    la hora de escogerlas, que no haya duplicacion o cosas mal seleccionadas;
    tiene que utilizar la herramienta de renderizar 3 a 5 frames de cada escena
    — ojo, frames, no segundos, centesimas o video: 3 a 5 fotos estaticas
    repartidas a lo largo de la escena para ver su estetica y continuidad»*.

    **Y estaban repartidos por la ventana de busqueda, que es otra cosa.**
    Medido en el pedido de reel-03 del 10-9: los cinco fotogramas del beat 1
    salian en los segundos 66,2 · 125,8 · 185,4 · 245,0 · 304,6 de la cinta —
    un minuto entre uno y otro— mientras los tramos que esa etapa monta de
    verdad son 28,5-33,5, 39,3-42,4 y 340,6-342,2. Ninguno de los cinco caia
    dentro de la escena. Se le pedia que dijera si estaba leyendo AHI mirando
    fotos de cuatro minutos de distancia.

    Los tramos salen del segmento, que es la unidad, y el reparto es por tiempo
    de escena: un tramo que dura el doble se lleva el doble de fotos, porque lo
    que se juzga es la continuidad de lo que se ve, no cuantos trozos hay.
    """
    from dominio.segmento import Segmento

    seg = next((x for x in Segmento.de(slug) if x.n == int(etapa)), None)
    if not seg or not seg.tramos:
        return []
    total = sum(b - a for a, b in seg.tramos) or 1.0
    cuantos = max(3, min(int(cuantos), CUANTOS))
    fuera, toma = [], _toma_de(slug, seg.n)
    if not toma:
        return []
    for a, b in seg.tramos:
        # Al menos uno por tramo: un trozo corto tambien puede tenerlo leyendo.
        cuota = max(1, round(cuantos * (b - a) / total))
        fuera += de_la_cinta(toma, a, b, cuantos=cuota, etiqueta=f"e{seg.n}")
    return fuera[:CUANTOS]


def _toma_de(slug, etapa):
    """De que cinta sale esa etapa, segun el EDL."""
    import json as _j

    try:
        edl = _j.load(open(os.path.join("ads", slug, "edl-sell.json"),
                           encoding="utf-8"))
    except OSError:
        return None
    for d in edl.get("detalle", []):
        if d.get("beat") == int(etapa) and d.get("toma"):
            return d["toma"]
    return None


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
        import rutas  # el interprete se resuelve, no se hereda: C-349, C-548
        r = subprocess.run([rutas.interprete(), "scripts/mirar.sh", str(n), str(cuantos)],
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


class Hoja:
    """**La hoja de contacto: la pieza en un documento, no en un video.** C-584.

    Jaime, 19-10-2026: *«hacer hojas de contacto antes de presentar el video;
    con eso los agentes no tienen que ver los videos sino que trabajan con algo
    mas facil, un documento»*, y *«de facil lectura»*.

    El visto abria un fotograma por etapa, uno a uno: entre 9 y 23 imagenes y
    hasta 28 llamadas por pieza (W40, 18-10). Dos hojas, segun quien mira:

    - **La del render** (`del_render`): un fotograma por escena —el del medio,
      que es el estado estable—, rotulado con su etapa, su escena y su segundo,
      y debajo lo que se dice en ese momento. Los cinco de cada escena siguen en
      disco: se abren solo los de la escena que dude.
    - **La de la cinta** (`de_la_cinta`): los cinco de una etapa en una fila,
      que es como el que compone ve si esta leyendo —la mirada baja a ratos—.

    **Y legible antes que pequena.** Cada hoja cabe en `TOPE_PX`, que es lo que
    el modelo ve sin reducir la imagen: mas grande, la encoge el y el rotulo
    deja de leerse. Por eso van `POR_HOJA` fotogramas como mucho.
    """

    POR_HOJA = 6
    TOPE_PX, LADO = 1_150_000, 1568
    CABEZA, BANDA = 30, 78         # la etapa encima; lo que se dice, debajo

    def __init__(self, slug, tiros, nombre="hoja", en_fila=False):
        self.slug, self.nombre, self.en_fila = slug, nombre, en_fila
        #: `(rotulo, segundo, fichero, pie)`, en el orden en que se leen.
        self.tiros = list(tiros)
        self.banda = self.BANDA if any(t[3] for t in self.tiros) else 0

    #: Lo que el spec pinta encima del plano: no puede quedar sin fotograma.
    CAPAS = ("boards", "paneles", "recortes")

    @classmethod
    def del_render(cls, slug, hechas, etapas=None, nombre="hoja") -> "Hoja":
        """Un fotograma por escena del render, con lo que se dice debajo.

        **Por escena, no por etapa.** La primera medida (reel-21, 19-10) iba con
        uno por etapa, no vio «ESCRIBA RETIRO.» —vive en la escena 10, una de
        las dos de e5— y el visto devolvio la pieza por un rotulo que estaba.
        La escena es la unidad del montaje; y si un tablero, un panel o un
        recorte cae entre los fotogramas elegidos, se anade el suyo.
        """
        escs = [e for e in hechas or []
                if e.get("mira") and (etapas is None or e.get("etapa") in etapas)]

        def en(e, k):
            return e["mira"][k].get("en", (e["desde"] + e["hasta"]) / 2)

        dicho, capas = cls._spec(slug)
        elegidos = {(e["escena"], len(e["mira"]) // 2): e for e in escs}
        for a, b in capas:
            if any(a <= en(e, k) <= b for (_n, k), e in elegidos.items()):
                continue
            mitad = (a + b) / 2
            e = next((x for x in escs if x["desde"] <= mitad < x["hasta"]), None)
            if e:
                k = min(range(len(e["mira"])), key=lambda i: abs(en(e, i) - mitad))
                elegidos[(e["escena"], k)] = e
        tiros = []
        for (_n, k), e in sorted(elegidos.items(), key=lambda x: en(x[1], x[0][1])):
            t = en(e, k)
            pie = " / ".join(x for a, b, x in dicho if a <= t < b) or "(sin subtitulo)"
            tiros.append((f"e{e.get('etapa')} · esc {e['escena']}", t, e["mira"][k]["fichero"], pie))
        return cls(slug, tiros, nombre=nombre)

    @classmethod
    def de_la_cinta(cls, slug, etapa, fotos) -> "Hoja":
        """Los fotogramas de una etapa en la cinta, en una fila. Ver `de_la_escena`."""
        return cls(slug, [(f"e{etapa} cinta", x.get("en", 0), x["fichero"], "")
                          for x in fotos or []], nombre=f"cinta-e{etapa}", en_fila=True)

    @classmethod
    def _spec(cls, slug):
        """Del spec que se renderizo: los subtitulos y las capas, en segundos."""
        try:
            n = int(slug.split("-")[1])
            spec = json.load(open("src/reels.json", encoding="utf-8"))
            r = next((x for x in spec if x.get("id") == f"Reel-R{n}"), {})
        except (OSError, ValueError, IndexError):
            return [], []
        tramo = lambda c: (c["at"] / 30, (c["at"] + c["duration"]) / 30)  # noqa: E731
        dicho = [(*tramo(c), c.get("text", "")) for c in r.get("captions") or []
                 if "at" in c and "duration" in c]
        capas = [tramo(c) for k in cls.CAPAS for c in r.get(k) or []
                 if isinstance(c, dict) and "at" in c and "duration" in c]
        cta = r.get("cta")
        if isinstance(cta, dict) and "at" in cta and "dur" in cta:
            capas.append((cta["at"], cta["at"] + cta["dur"]))
        return dicho, capas

    def _ancho(self, k):
        """`(columnas, ancho)`: el reparto que deja cada fotograma mas grande."""
        def cabe(cols, w):
            alto = -(-k // cols) * (w * 16 / 9 + self.CABEZA + self.banda)
            return cols * w * alto <= self.TOPE_PX and max(cols * w, alto) <= self.LADO

        return max(((c, max([w for w in range(120, 541, 4) if cabe(c, w)] or [120]))
                    for c in ([k] if self.en_fila else range(1, k + 1))), key=lambda x: x[1])

    def escribe(self) -> list:
        """Las hojas en disco, con su ruta absoluta. `[]` si no hay que mirar."""
        from PIL import Image, ImageDraw, ImageFont

        def letra(tam, negrita=False):
            try:
                return ImageFont.truetype("arialbd.ttf" if negrita else "arial.ttf", tam)
            except OSError:
                return ImageFont.load_default()

        rutas_, n = [], len(self.tiros)
        os.makedirs(SALIDA.format(slug=self.slug), exist_ok=True)
        hojas = 1 if self.en_fila else -(-n // self.POR_HOJA)
        for i in range(hojas if n else 0):          # repartidas: 9 son 4 y 5, no 6 y 3
            lote = self.tiros[i * n // hojas:(i + 1) * n // hojas]
            cols, w = self._ancho(len(lote))
            h = round(w * 16 / 9)
            celda = h + self.CABEZA + self.banda
            hoja = Image.new("RGB", (cols * w, -(-len(lote) // cols) * celda), "white")
            pinta = ImageDraw.Draw(hoja)
            for j, (rotulo, en, fichero, pie) in enumerate(lote):
                x, y = (j % cols) * w, (j // cols) * celda
                pinta.rectangle((x, y, x + w - 1, y + self.CABEZA), fill="black")
                pinta.text((x + 8, y + 4), f"{rotulo} · {en:.1f} s".replace(".", ","),
                           fill="white", font=letra(20, True))
                try:
                    hoja.paste(Image.open(fichero).convert("RGB").resize((w, h)),
                               (x, y + self.CABEZA))
                except OSError:
                    pinta.text((x + 8, y + h // 2), "sin fotograma", fill="black", font=letra(18))
                for k, renglon in enumerate(textwrap.wrap(pie, max(12, w // 10))[:3]):
                    pinta.text((x + 6, y + self.CABEZA + h + 4 + 24 * k), renglon,
                               fill="black", font=letra(18))
                pinta.rectangle((x, y, x + w - 1, y + celda - 1), outline="black")
            nombre = self.nombre if self.en_fila else f"{self.nombre}-{i + 1}"
            ruta = os.path.abspath(os.path.join(SALIDA.format(slug=self.slug), f"{nombre}.jpg"))
            hoja.save(ruta, quality=88)
            rutas_.append(ruta.replace("\\", "/"))
        return rutas_


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--cuantos", type=int, default=CUANTOS)
    # La hoja de la pieza entera, a mano: lo que hacia `hoja-contacto.sh`.
    ap.add_argument("--hoja", action="store_true")
    a = ap.parse_args()
    total = 0
    import rutas
    for n in (a.reels or rutas.piezas()):
        hechas, mal = sacar(n, a.cuantos)
        if mal:
            print(f"  reel-{n:02d}: {mal}")
            continue
        if a.hoja:
            print("\n".join(Hoja(f"reel-{n:02d}", hechas).escribe()))
        tiros = sum(len(e["mira"]) for e in hechas)
        total += tiros
        print(f"  reel-{n:02d}: {len(hechas)} escena(s), {tiros} fotograma(s)"
              f" -> {SALIDA.format(slug=f'reel-{n:02d}')}")
    print(f"\nfotogramas: {total} para mirar")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
