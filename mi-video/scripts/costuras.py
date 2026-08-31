"""Las costuras: buscar el mejor corte y, si no lo hay, marcarla para disimular.

Regla de Jaime, y trae las dos mitades: *«busca los mejores cortes posibles, y si
no, utiliza la transición del glitch, con ésa se disimula — glitch y cambio de
cámara, más cerca o más lejos»*.

Y antes había dado el diagnóstico: *«si notas que los cortes de tono o de ritmo
son muy profundos, sabes que se va a notar en vídeo, por lo que puedes escoger o
buscar otro fragmento que puntúe mejor»*.

## Por qué el glitch no puede ir en todas

Iba en todas. Y una máscara que se pone siempre deja de ser máscara: se convierte
en el efecto, y entonces el corte limpio y el corte malo se ven igual de raros.
Jaime ya lo había acotado en su día — *«el glitch para cambios de escena o en
cortes de escena que quedan mal»*—: **donde quedan mal**, no en todas.

## El orden, que importa

1. **Mover el corte.** Casi siempre hay una frontera de palabra a medio segundo
   que empalma mejor. Es gratis y no se nota nada, porque no se añade: se elige.
2. **Si no la hay, disimular.** Glitch **y cambio de encuadre a la vez** — el ojo
   perdona un salto de voz cuando el plano también cambió, porque le da un
   motivo. Uno solo de los dos no basta.

## Qué es una costura dura

Sólo cuenta donde **se quitaron palabras**. Si entre un trozo y el siguiente sólo
se fue silencio, la voz continúa: el cambio de tono es prosodia, no empalme.

Los umbrales están medidos sobre estas seis cintas y son los de percepción, no de
manual: por debajo de `TONO_OK` semitonos y `RITMO_OK` palabras por segundo, la
unión no se oye.

    python scripts/costuras.py            # el informe de las seis
    python scripts/costuras.py --arreglar 2   # mueve lo que se pueda y marca el resto
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import registro  # noqa: E402
import transcribir  # noqa: E402
import rutas  # noqa: E402

# Por debajo de esto la costura no se oye. Medido sobre el lote.
TONO_OK = 2.5
RITMO_OK = 3.0
# Cuánto se puede mover un extremo buscando un empalme mejor. Medio segundo es
# una palabra corta: más allá se empieza a cambiar lo que se dice.
MARGEN = 0.6


def _pal(toma, cache):
    if toma not in cache:
        try:
            cache[toma] = transcribir.exigir(toma)["segmentos"]
        except SystemExit:
            cache[toma] = []
    return cache[toma]


def dura(salto):
    """¿Se va a oír esta unión?"""
    return (salto.get("tono") or 0) > TONO_OK or (salto.get("ritmo") or 0) > RITMO_OK


def medir(edl, i, cache):
    """El salto de la costura entre el segmento i y el i+1, o None si no es empalme."""
    (a0, b0), (a1, _) = edl["segmentos"][i], edl["segmentos"][i + 1]
    t0 = edl["detalle"][i].get("toma")
    t1 = edl["detalle"][i + 1].get("toma")
    if t0 != t1:
        # Cambio de cinta: el plano cambia entero, no hay costura que disimular.
        return None
    ws = _pal(t0, cache)
    # Sólo es empalme si entre los dos trozos había palabras.
    if not [w for w in ws if b0 <= w["start"] and w["end"] <= a1]:
        return None
    return beats.salto(t0, b0, t1, a1, ws)


def mejor(edl, i, cache):
    """Busca una frontera de palabra cercana que empalme mejor.

    Se prueban los finales de palabra dentro de `MARGEN` antes de `b0` y los
    comienzos dentro de `MARGEN` después de `a1`. **No se inventa un corte a
    mitad de palabra**: sólo se eligen fronteras que ya existen.

    Devuelve `(b0, a1, salto)` de la mejor combinación, que puede ser la actual.
    """
    (a0, b0), (a1, b1) = edl["segmentos"][i], edl["segmentos"][i + 1]
    t0 = edl["detalle"][i].get("toma")
    ws = _pal(t0, cache)
    finales = [b0] + [w["end"] for w in ws
                      if b0 - MARGEN <= w["end"] <= b0 and w["end"] - a0 > 0.8]
    inicios = [a1] + [w["start"] for w in ws
                      if a1 <= w["start"] <= a1 + MARGEN and b1 - w["start"] > 0.8]
    # **Mover el corte no puede costar voz.** Jaime, sobre el objetivo de todo
    # esto: *«el punto es transmitir mas emocion»*. Un optimizador que solo
    # minimiza el salto acaba eligiendo el trozo mas plano, porque lo plano
    # empalma con todo — y eso es exactamente lo contrario de lo que la pieza
    # necesita.
    #
    # Asi que la entrega es una **restriccion**, no un termino mas: una
    # alternativa que baje la expresividad por debajo de la actual se descarta
    # aunque empalme perfecto. Si ninguna la respeta, la costura se disimula con
    # glitch — mejor un corte tapado que una entrega aplanada.
    voz0 = (float(beats.expresividad(t0, a0, b0))
            + float(beats.expresividad(t0, a1, b1))) / 2
    coste = None
    elegido = (b0, a1, None)
    for f in sorted(set(round(x, 3) for x in finales)):
        for n in sorted(set(round(x, 3) for x in inicios)):
            if n <= f:
                continue
            voz = (float(beats.expresividad(t0, a0, f))
                   + float(beats.expresividad(t0, n, b1))) / 2
            if voz < voz0 - 0.15:          # pierde entrega: no compensa
                continue
            s = beats.salto(t0, f, t0, n, ws)
            c = (s.get("tono") or 0) / TONO_OK + (s.get("ritmo") or 0) / RITMO_OK
            if coste is None or c < coste:
                coste, elegido = c, (f, n, s)
    return elegido


# Lo que hace que un borde sea limpio. Jaime: *«muy importante que los cortes
# sean finos, que no queden inicios con palabras anteriores»*.
#
# `AIRE` es el silencio que basta para que el oido oiga una frontera; por debajo
# de eso el corte entra pegado a la palabra de antes y se oye el empalme o se
# come el arranque. `BUSCA` es cuanto se mira a cada lado antes de rendirse.
AIRE = 0.30
BUSCA = 2.0


# Palabras con las que una frase **no puede acabar**: articulos, preposiciones y
# conectores. Si el ultimo trozo de una etapa muere en una de estas, la idea se
# quedo sin objeto.
COLGANTES = {"y", "o", "u", "pero", "porque", "que", "cuando", "si", "de", "del",
             "la", "el", "los", "las", "un", "una", "unos", "unas", "en", "a",
             "al", "con", "para", "por", "su", "sus", "se", "le", "les", "lo",
             "me", "te", "nos", "es", "son", "mi", "tu", "como", "sin", "sobre",
             "entre", "hasta", "desde", "muy", "mas", "más", "ya", "no"}


def _colgante(txt):
    return txt.strip(".,¿?¡!;:").lower() in COLGANTES


def _fronteras(ws):
    """Los sitios donde una frase puede empezar o acabar de verdad.

    Dos senales, y las dos salen de la transcripcion buena:

    - **La puntuacion.** El barrido de cuatro pasadas devuelve puntos e
      interrogantes, asi que se sabe donde cierra una idea sin adivinar.
    - **El aire.** Un hueco de `AIRE` entre dos palabras es una frontera aunque
      no lleve punto: el hablante respiro ahi.
    """
    ini, fin = [], []
    for k, w in enumerate(ws):
        antes = ws[k - 1] if k else None
        if antes is None or w["start"] - antes["end"] >= AIRE or \
           antes["text"].strip().endswith((".", "?", "!")):
            ini.append(w["start"])
        sig = ws[k + 1] if k + 1 < len(ws) else None
        if sig is None or sig["start"] - w["end"] >= AIRE or \
           w["text"].strip().endswith((".", "?", "!")):
            fin.append(w["end"])
    return sorted(set(ini)), sorted(set(fin))


ATAQUE = 0.08


def _fuera_de_palabra(x, ws, hacia):
    """Saca un corte de dentro de una palabra. `hacia` es 'ini' o 'fin'.

    Regla de Jaime mirando el primer render: *«muy importante que los cortes
    sean finos»*, y dos ejemplos suyos de lo que pasa cuando no lo son — en el
    segundo 58 se oye «30, much» y en el 1:15 queda «rente», la cola de
    «diferente». Las dos son el mismo fallo: **el corte cayo en mitad de una
    palabra**.

    Un corte dentro de una palabra no se arregla con criterio: se saca. Al
    entrar, a donde empieza la palabra si se oye mas de media, o a donde acaba
    si no; al salir, al reves. Es aritmetica, y por eso puede correr siempre.
    """
    for w in ws:
        if not (w["start"] < x < w["end"]):
            continue
        dentro = (x - w["start"]) / max(w["end"] - w["start"], 1e-6)
        # **Al borde exacto, sin margen.** Con ±0,02 el corte salia de una
        # palabra y entraba en la de al lado —el transcript las da pegadas, sin
        # hueco entre el final de una y el principio de la siguiente—, asi que
        # el arreglo oscilaba y nunca convergia: once cortes «arreglados» en
        # cada pasada, indefinidamente. En el borde justo no esta dentro de
        # ninguna, y el margen para no comerse la consonante ya lo pone
        # `plan-reel` al cortar.
        if hacia == "ini":
            # **Un respiro no es un corte a medias.** `ataques` retrocede 80 ms
            # para que se oiga la consonante con la que arranca la primera
            # palabra, y ese retroceso cae dentro de la palabra ANTERIOR porque
            # el transcript las da pegadas. Sin esta salvedad, la pasada
            # siguiente lo empujaba de vuelta al borde justo y los dos pasos se
            # deshacian el trabajo uno al otro — la misma oscilacion que ya
            # costo once cortes «arreglados» en cada pasada.
            #
            # Se distingue por lo que es: si lo que queda por delante de la
            # palabra siguiente cabe en un ataque, esto es un respiro puesto a
            # proposito y se deja.
            if w["end"] - x <= ATAQUE + 0.005:
                return x
            return w["start"] if dentro < 0.5 else w["end"]
        return w["end"] if dentro > 0.5 else w["start"]
    return x


def palabras_enteras(slug, ver=False):
    """Ningun corte de la pieza cae dentro de una palabra."""
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    cache, tocados = {}, 0
    for i, ((a, b), det) in enumerate(zip(edl["segmentos"], edl["detalle"])):
        t = det.get("toma")
        if t not in cache:
            try:
                cache[t] = transcribir.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        ws = cache[t]
        if not ws:
            continue
        na = round(_fuera_de_palabra(a, ws, "ini"), 3)
        nb = round(_fuera_de_palabra(b, ws, "fin"), 3)
        if nb - na < 0.3:
            continue
        if abs(na - a) > 0.001 or abs(nb - b) > 0.001:
            if ver:
                print(f"  {slug} e{det.get('beat')}: [{a:.2f}-{b:.2f}] ->"
                      f" [{na:.2f}-{nb:.2f}]")
            edl["segmentos"][i] = [na, nb]
            tocados += 1
    if tocados and not ver:
        edl["duracion_s"] = round(sum(y - x for x, y in edl["segmentos"]), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {tocados} corte(s) sacados de dentro de una palabra")
    return tocados


# Lo que hace falta para que se oiga la consonante con la que arranca una
# palabra. Por debajo de 60 ms la primera silaba entra descabezada y por encima
# de 120 se cuela el final de lo anterior; 80 es el centro de esa ventana.


def ataques(slug, ver=False):
    """Ningun corte entra pisando la primera palabra.

    Jaime, oyendo el reel-01: *«el "no es mala suerte" se entrega sin alma,
    falta el "eso"»*. Y el «eso» estaba: el corte empezaba en 93,44, que es
    exactamente lo que el transcript da como arranque de esa palabra.

    **El transcript no sirve para medir un ataque.** Whisper reparte las marcas
    sin dejar hueco entre palabras, asi que estira la anterior por encima del
    silencio: aqui «suerte,» figura de 92,01 a 93,44 cuando el detector de voz
    dice que la voz se corta en 92,29 y vuelve en 92,89. El arranque real de la
    frase esta medio segundo antes de donde el texto lo pone, y entrar por el
    texto entra con la palabra ya empezada.

    La vara buena es el audio, que ya esta medido en `work/cuts`: se retrocede
    hasta `ATAQUE` **sin cruzar el final del tramo de voz anterior** —para no
    traerse la cola de lo de antes— ni el final del trozo anterior del montaje.

    Es aritmetica y por eso corre sola: no decide que entra, solo hace que lo
    que ya entra se oiga entero. Medido en el lote: 42 cortes empezaban justo
    en el ataque.
    """
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    cache, vad, tocados = {}, {}, 0
    for i, ((a0, b0), d) in enumerate(zip(segs, det)):
        toma = d.get("toma")
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
            try:
                vad[toma] = json.load(
                    open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]
            except Exception:                      # noqa: BLE001
                vad[toma] = []
        prim = next((w for w in cache[toma] if w["end"] > a0 + 0.001), None)
        if not prim or abs(prim["start"] - a0) > 0.02:
            continue                    # no entra pisando nada: se deja
        suelo = a0 - ATAQUE
        previos = [y for x, y in vad[toma] if y <= a0 + 0.001]
        if previos:
            suelo = max(suelo, max(previos) + 0.01)
        if i and det[i - 1].get("toma") == toma:
            suelo = max(suelo, segs[i - 1][1] + 0.01)
        if a0 - suelo < 0.01:
            continue
        if ver:
            print(f"  {slug} e{d.get('beat')}: {a0:.3f} -> {suelo:.3f}"
                  f" para que se oiga {prim['text']!r}")
        else:
            segs[i] = [round(suelo, 3), b0]
        tocados += 1
    if tocados and not ver:
        edl["duracion_s"] = round(sum(y - x for x, y in segs), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {tocados} corte(s) respiran el ataque")
    return tocados


# Lo que se deja despues de la ultima palabra: el aire justo para que la frase
# cierre sin sonar cortada. Mas que esto ya es silencio, y el silencio se declara.
COLA = 0.25


def colas(slug, ver=False):
    """Ningun trozo entra antes de hablar ni se queda despues de callar.

    Jaime, sobre las piezas largas: *«ve cortando silencios entre frases, que
    quede todo muy justo»*, y luego la prediccion: *«eso da unos segundos
    siempre»*. Lo medi antes de tocar nada y el aire **no estaba entre frases**
    —`plan-reel` ya corta cualquier hueco de mas de 0,16 s— sino en los bordes de
    cada trozo, y concentrado en unos pocos:

        reel-06 e3   5,40 s despues de la ultima palabra
        reel-06 e5   3,12 s antes de la primera
        reel-05 e9   4,82 s despues de callar

    En el lote son 15,4 s en reel-06 y 9,1 en reel-05: la primera baja de 129 a
    114 **sin tocar una sola idea**. Tenia razon en que siempre da segundos, y
    daba mas de los que parecia.

    Es aritmetica —un trozo que no dice nada en sus extremos no dice nada— y por
    eso corre sola. Con dos respetos:

    - **La pausa declarada no se toca.** Regla suya: quitar aire es aritmetica,
      *conservarlo* es una decision, y se declara con `[pausa]` en el libreto de
      esa etapa. Ahi el silencio es el trabajo del beat.
    - **El ataque tampoco.** Por delante se deja `ATAQUE`, que es lo que hace que
      se oiga la consonante con la que arranca la palabra (C-101).
    """
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    try:
        import consulta

        pausas = {int(k) for k in (consulta.pausas(slug) or {})}
    except Exception:                              # noqa: BLE001
        pausas = set()
    cache, ganado, tocados = {}, 0.0, 0
    for i, ((a0, b0), d) in enumerate(zip(segs, det)):
        if d.get("beat") in pausas:
            continue
        toma = d.get("toma")
        if toma not in cache:
            try:
                cache[toma] = sorted(transcribir.exigir(toma)["segmentos"],
                                     key=lambda w: w["start"])
            except SystemExit:
                cache[toma] = []
        ws = [w for w in cache[toma] if transcribir.suena(w, a0, b0)]
        if not ws:
            continue
        na = max(a0, ws[0]["start"] - ATAQUE)
        nb = min(b0, ws[-1]["end"] + COLA)
        if (na - a0) + (b0 - nb) < 0.15:
            continue
        ganado += (na - a0) + (b0 - nb)
        tocados += 1
        if ver:
            print(f"  {slug} e{d.get('beat')}: [{a0:.2f}-{b0:.2f}] ->"
                  f" [{na:.2f}-{nb:.2f}]  (-{(na - a0) + (b0 - nb):.2f}s)")
        else:
            segs[i] = [round(na, 3), round(nb, 3)]
    if tocados and not ver:
        edl["duracion_s"] = round(sum(y - x for x, y in segs), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {tocados} trozo(s) ajustados al habla, -{ganado:.1f}s")
    return tocados


def mudos(slug, ver=False):
    """Fuera los trozos que no dicen ni una palabra entera.

    Los deja el propio ajuste de bordes: al mover una entrada o cerrar una cola
    puede quedar un resto de dos o tres decimas con media palabra dentro. Medido
    en el lote: cinco trozos de 0,26 a 0,57 s **sin una sola palabra completa**.

    Es aritmetica —un segmento sin palabras no dice nada— asi que se quita solo.
    Y quitarlo aprieta el montaje: son restos que suenan a chasquido.
    """
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    cache, fuera = {}, []
    for i, ((a, b), d) in enumerate(zip(segs, det)):
        if b - a >= 0.7:
            continue
        t = d.get("toma")
        if t not in cache:
            try:
                cache[t] = transcribir.exigir(t)["segmentos"]
            except SystemExit:
                cache[t] = []
        if not [w for w in cache[t] if transcribir.suena(w, a, b)]:
            fuera.append(i)
            if ver:
                print(f"  {slug} e{d.get('beat')}: fuera [{a:.2f}-{b:.2f}]"
                      f" ({b - a:.2f}s sin una palabra)")
    if fuera and not ver:
        edl["segmentos"] = [x for k, x in enumerate(segs) if k not in fuera]
        edl["detalle"] = [x for k, x in enumerate(det) if k not in fuera]
        edl["duracion_s"] = round(sum(y - x for x, y in edl["segmentos"]), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {len(fuera)} trozo(s) mudos fuera")
    return len(fuera)


def sin_solapes(slug, ver=False):
    """Dos trozos de la misma cinta no pueden pisarse: eso es audio repetido.

    Salio de una nota de Jaime sobre el primer render —«segundo 8 repite "eso no
    es"»— y al medirlo eran cinco solapes en el lote, uno de **10,4 segundos** en
    `reel-01`: la convocatoria entera sonando dos veces.

    Los produce mover bordes: al estirar una entrada hacia atras para devolverle
    la cabeza a la frase, esa entrada puede meterse dentro del trozo anterior. La
    guarda de `bordes` miraba el trozo anterior **en el orden de la lista**, y
    tras reordenar por beat ese ya no era el que estaba antes en la cinta.

    Se arregla por lo que significa: si los dos trozos son de la **misma etapa**,
    son el mismo tramo partido y se funden; si son de etapas distintas, el
    segundo empieza donde acaba el primero.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    segs, det = edl["segmentos"], edl["detalle"]
    orden = sorted(range(len(segs)),
                   key=lambda i: (det[i].get("toma") or "", segs[i][0]))
    fuera, tocados = set(), 0
    for k in range(len(orden) - 1):
        i, j = orden[k], orden[k + 1]
        if i in fuera or (det[i].get("toma") != det[j].get("toma")):
            continue
        if segs[j][0] >= segs[i][1] - 0.05:
            continue
        tocados += 1
        if det[i].get("beat") == det[j].get("beat"):
            segs[i][1] = max(segs[i][1], segs[j][1])       # se funden
            fuera.add(j)
            if ver:
                print(f"  {slug} e{det[i].get('beat')}: fundidos en"
                      f" [{segs[i][0]:.2f}-{segs[i][1]:.2f}]")
        else:
            if ver:
                print(f"  {slug} e{det[j].get('beat')}: entrada {segs[j][0]:.2f}"
                      f" -> {segs[i][1]:.2f} (pisaba a e{det[i].get('beat')})")
            segs[j][0] = segs[i][1]
    if tocados and not ver:
        edl["segmentos"] = [x for k, x in enumerate(segs) if k not in fuera]
        edl["detalle"] = [x for k, x in enumerate(det) if k not in fuera]
        edl["duracion_s"] = round(sum(y - x for x, y in edl["segmentos"]), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {tocados} solape(s) resueltos")
    return tocados


def bordes(slug, ver=False):
    """Lleva cada entrada y cada salida a la frontera de frase mas cercana.

    **No cambia lo que la etapa dice**: mueve el corte al silencio que ya existe,
    dentro de `BUSCA` segundos. Si el borde ya esta limpio, no lo toca; si no hay
    frontera cerca, lo deja y lo dice — mover mas de dos segundos si cambiaria lo
    que se oye, y eso es otra decision.

    Medido antes de esto: 27 de 85 entradas del lote entraban con menos de 0,2 s
    de aire. `reel-06` e6 empezaba en «anos» cuando lo anterior era «En 10», y e5
    en «mil» dejando fuera el «30»: el corte se comia la cifra.
    """
    import transcribir

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0, 0
    edl = json.load(open(ruta, encoding="utf-8"))
    cache = {}
    movidos, sucios = 0, 0
    for i, ((a, b), det) in enumerate(zip(edl["segmentos"], edl["detalle"])):
        t = det.get("toma")
        if t not in cache:
            try:
                ws = transcribir.exigir(t)["segmentos"]
            except SystemExit:
                ws = []
            cache[t] = (ws, _fronteras(ws)) if ws else ([], ([], []))
        ws, (ini, fin) = cache[t]
        if not ws:
            continue
        na = min((x for x in ini if abs(x - a) <= BUSCA),
                 key=lambda x: abs(x - a), default=None)
        nb = min((x for x in fin if abs(x - b) <= BUSCA),
                 key=lambda x: abs(x - b), default=None)
        # **Dos guardas, y las dos salen de verlo fallar.** Sin la primera, un
        # borde se iba 1,9 s y el segmento pasaba a decir otra cosa; sin la
        # segunda, la entrada de una etapa se metia dentro de la salida de la
        # anterior y los dos trozos se solapaban en el montaje.
        antes_fin = None
        for j in range(i - 1, -1, -1):
            if edl["detalle"][j].get("toma") == t:
                antes_fin = edl["segmentos"][j][1]
                break
        palabras = [w for w in ws if transcribir.suena(w, a, b)]

        def _mantiene(x, y):
            if not palabras:
                return True
            quedan = sum(1 for w in palabras if transcribir.suena(w, x, y))
            return quedan >= max(1, int(len(palabras) * 0.8))

        # **Y si no hay frontera cerca, se le devuelve la cabeza de la frase.**
        #
        # Una entrada pegada a la palabra anterior sin pausa a la vista no se
        # arregla moviendola: se arregla **incluyendo** lo que le falta. La
        # senal es la puntuacion: si la palabra de antes cierra con punto, esta
        # entrada ya es principio de frase y solo suena pegada; si no cierra,
        # entonces la frase empezo antes y el corte se comio la cabeza.
        #
        # Medido: `reel-06` e5 entraba en «mil dolares al año» con el «30» fuera,
        # y `reel-05` e7 en «activo esa tasa» con el «no» fuera —que invierte la
        # frase—. Estirar hacia atras hasta la frontera devuelve la cifra y la
        # negacion.
        if na is None or abs(na - a) > BUSCA:
            k = next((j for j, w in enumerate(ws)
                      if w["start"] >= a - 0.001), None)
            if k:
                j = k
                while j > 0:
                    ant = ws[j - 1]
                    # La coma cuenta como frontera **solo aqui**, al estirar
                    # hacia atras: buscamos la cabeza de ESTA frase, no la
                    # anterior entera. Con el punto solo, `reel-03` se traia
                    # «usted tiene un contador» dos veces.
                    if ws[j]["start"] - ant["end"] >= AIRE or                        ant["text"].strip().endswith((".", "?", "!", ",")):
                        break
                    j -= 1
                cand = round(max(0.0, ws[j]["start"] - 0.08), 3)
                # **La cabeza que se devuelve no puede ser un arranque en
                # falso.** Si lo que hay delante repite lo que la etapa ya dice
                # —«esto es diferente, esto es diferente»— no es la cabeza de la
                # frase: es el intento anterior, y meterlo es meter tartamudeo.
                def _norm(x):
                    return "".join(c for c in x.lower() if c.isalnum())

                cabeza = [_norm(w["text"]) for w in ws[j:k] if _norm(w["text"])]
                primeras = {_norm(w["text"]) for w in ws[k:k + 5]}
                repite = sum(1 for x in cabeza if x in primeras)
                if j < k and (antes_fin is None or cand >= antes_fin - 0.001)                    and a - cand <= 4.0 and len(cabeza) >= 2 and repite <= 1:
                    edl["segmentos"][i][0] = cand
                    if ver:
                        print(f"  {slug} e{det.get('beat')}: cabeza devuelta"
                              f" [{a:.2f} -> {cand:.2f}] «"
                              + " ".join(w["text"] for w in ws[j:k]) + "»")
                    movidos += 1
                    continue

        # **Y la cola tampoco puede quedar colgando.** Mismo problema por el
        # otro extremo: `reel-02` acababa una etapa en «se queda con» —sin la
        # cifra— y otra en «voy a» —sin el verbo—. Una frase que muere en una
        # preposicion no dice nada, y el espectador se queda esperando.
        ult = [w for w in ws if transcribir.suena(w, a, b)]
        # **El conector volando: la primera palabra de la frase siguiente que se
        # colo al final.** Jaime lo vio en el primer render —«hay un conector
        # volando (y cuando)»—. Se reconoce porque va en mayuscula o porque lo
        # anterior cerro con punto: no es que falte el objeto, es que sobra la
        # palabra. Esa no se extiende: se corta.
        if len(ult) >= 2 and _colgante(ult[-1]["text"]):
            prev = ult[-2]["text"].strip()
            if ult[-1]["text"].strip()[:1].isupper() or                prev.endswith((".", "?", "!")):
                cand = round(ult[-2]["end"], 3)
                if cand - edl["segmentos"][i][0] > 0.8:
                    edl["segmentos"][i][1] = cand
                    if ver:
                        print(f"  {slug} e{det.get('beat')}: conector suelto"
                              f" fuera «{ult[-1]['text']}»")
                    movidos += 1
                    continue
        if ult and _colgante(ult[-1]["text"]):
            k2 = ws.index(ult[-1])
            j2 = k2
            while j2 + 1 < len(ws):
                sig = ws[j2 + 1]
                if sig["start"] - ws[j2]["end"] >= AIRE:
                    break
                j2 += 1
                if ws[j2]["text"].strip().endswith((".", "?", "!", ",")) and                    not _colgante(ws[j2]["text"]):
                    break
            cand = round(ws[j2]["end"], 3)
            if j2 > k2 and cand - b <= 3.0:
                edl["segmentos"][i][1] = cand
                if ver:
                    print(f"  {slug} e{det.get('beat')}: cola cerrada"
                          f" [{b:.2f} -> {cand:.2f}] «"
                          + " ".join(w["text"] for w in ws[k2 + 1:j2 + 1]) + "»")
                movidos += 1
                continue
            # **Si completar la frase costaria mas de tres segundos, se corta la
            # palabra que cuelga.** Mejor una etapa que acaba un poco seca que
            # una que acaba en «voy a» — y mejor eso que alargar la pieza tres
            # segundos por una preposicion.
            if len(ult) >= 2:
                corte = round(ult[-2]["end"], 3)
                if corte - edl["segmentos"][i][0] > 0.8:
                    edl["segmentos"][i][1] = corte
                    if ver:
                        print(f"  {slug} e{det.get('beat')}: cola cortada"
                              f" «{ult[-1]['text']}»")
                    movidos += 1
                    continue

        cambia = False
        if na is not None and abs(na - a) > 0.01 and (nb or b) - na > 0.8:
            cand = round(max(0.0, na - 0.08), 3)
            if (antes_fin is None or cand >= antes_fin - 0.001) and                _mantiene(cand, b):
                # Se entra un pelin antes de la primera palabra, para no comerse
                # el ataque de la consonante.
                edl["segmentos"][i][0] = cand
                cambia = True
        if nb is not None and abs(nb - b) > 0.01 and nb - edl["segmentos"][i][0] > 0.8:
            cand = round(nb + 0.12, 3)
            if _mantiene(edl["segmentos"][i][0], cand):
                edl["segmentos"][i][1] = cand
                cambia = True
        if cambia:
            movidos += 1
            if ver:
                print(f"  {slug} e{det.get('beat')}: [{a:.2f}-{b:.2f}] ->"
                      f" [{edl['segmentos'][i][0]:.2f}-{edl['segmentos'][i][1]:.2f}]")
        elif na is None:
            sucios += 1
    if not ver and movidos:
        edl["duracion_s"] = round(sum(y - x for x, y in edl["segmentos"]), 2)
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    print(f"{slug}: {movidos} borde(s) llevados a frontera de frase"
          f"{f' · {sucios} sin frontera cerca' if sucios else ''}")
    return movidos, sucios


def arreglar(slug, ver=False):
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return
    edl = json.load(open(ruta, encoding="utf-8"))
    cache = {}
    movidas, duras, total = 0, [], 0
    for i in range(len(edl["segmentos"]) - 1):
        s = medir(edl, i, cache)
        if s is None:
            continue
        total += 1
        if not dura(s):
            continue
        # **Una costura declarada no se mueve.** Mover el empalme es el trabajo
        # de este paso y esta bien hecho —busca el par de bordes que suena
        # menos a pegote—, pero lo hace recortando una palabra a cada lado, y
        # cuando el tramo viene declarado eso **deshace una decision en
        # silencio**.
        #
        # Medido en reel-01 e2: la segunda valoracion declaro 118,20-134,35 y
        # 220,35-224,85 justo para que entraran «estructura» al cerrar y «y
        # los» al abrir, que son lo que hace que la frase siga. `arreglar` los
        # volvio a quitar buscando una costura mas limpia, y la pieza quedo
        # diciendo «una cierta | que usan esa estructura». Jaime ya lo habia
        # nombrado: *«se recortaron pasos intermedios entre secciones»*.
        #
        # La costura sigue siendo dura, y para eso esta el glitch: se disimula
        # en vez de recortarse. Disimular no cuesta palabras.
        if (edl["detalle"][i].get("fijado")
                or edl["detalle"][i + 1].get("fijado")):
            duras.append(i)
            continue
        f, n, s2 = mejor(edl, i, cache)
        if s2 and not dura(s2):
            if not ver:
                edl["segmentos"][i][1] = f
                edl["segmentos"][i + 1][0] = n
                edl["detalle"][i]["end"] = f
                edl["detalle"][i + 1]["start"] = n
            movidas += 1
            print(f"  {slug} costura {i}: movida — tono {s['tono']}→{s2['tono']}"
                  f" · ritmo {s['ritmo']}→{s2['ritmo']}")
        else:
            duras.append(i)
    # **Antes del glitch, el B-roll.** Jaime: *«otra forma de hacer transiciones
    # es hacer B-rolls con pedazos del video donde yo salgo en silencio… es una
    # alternativa al glitch»*. Y es mejor alternativa: el glitch tapa la costura
    # con un efecto, el B-roll la resuelve con material real y ademas da el
    # espacio para pensar cuando lo anterior pesaba.
    #
    # El orden queda en tres escalones, de menos a mas intervencion:
    #   1. mover el corte —gratis, no se anade nada—
    #   2. B-roll mudo de la misma cinta —se anade material que ya existe—
    #   3. glitch y cambio de encuadre —se anade un efecto—
    if duras:
        try:
            import consulta as _cs

            # «Un par de segundos», que es lo que Jaime pidio: mas que eso deja de
            # ser una transicion y se convierte en una pausa.
            libres = _cs.brolls(1.8, 3.0, cintas=sorted(
                {d.get("toma") for d in edl["detalle"] if d.get("toma")}))
        except Exception:                          # noqa: BLE001
            libres = []
        # **El B-roll no se asigna aqui: se propone.** Jaime, cuando le puse
        # cuatro y luego dos: *«no tantas, es una herramienta de enfasis o de
        # separacion»*, *«idealmente una por video, y cuando sea necesario»*, y
        # lo que lo zanja: *«por eso se piensa bien en la composicion»*.
        #
        # O sea que esto es un detector, no un decisor —la misma regla que ya
        # costo una correccion (C-88)—. Se apuntan las costuras que **podrian**
        # llevarlo, con su razon, y quien compone elige si alguna lo necesita.
        # Cero es una respuesta buena.
        TOPE = 3
        det = edl["detalle"]
        compone = set()
        try:
            import sqlite3

            cx = sqlite3.connect("ads/decisiones.db")
            compone = {r[0] for r in cx.execute(
                "select etapa_orden from escena_desc where video_slug = ?"
                " and componente is not null", (slug,))}
            cx.close()
        except Exception:                          # noqa: BLE001
            pass
        posibles = []
        for i in duras:
            if i + 1 >= len(det):
                continue
            b_ant, b_sig = det[i].get("beat"), det[i + 1].get("beat")
            if b_ant == b_sig:
                continue                 # dentro de una etapa: no separa nada
            posibles.append((i, b_ant, b_sig,
                             "enfasis" if b_ant in compone else "separacion"))
        posibles.sort(key=lambda x: 0 if x[3] == "enfasis" else 1)
        edl["brolls_posibles"] = [
            {"costura": i, "entre": [b_ant, b_sig], "razon": razon,
             "toma": b0["toma"], "desde": b0["desde"], "hasta": b0["hasta"],
             "dura": b0["dura"]}
            for (i, b_ant, b_sig, razon), b0 in zip(posibles[:TOPE], libres)]
        edl.pop("brolls", None)
        if not ver and edl["brolls_posibles"]:
            print(f"  {slug}: {len(edl['brolls_posibles'])} costura(s) admiten"
                  f" B-roll — lo decide la composicion")

    # **Lo que no tuvo arreglo ni B-roll se marca para disimular**, y el spec
    # pone ahi el glitch y el cambio de encuadre. Los dos juntos: el ojo perdona
    # un salto de voz cuando el plano tambien cambio, porque le da un motivo.
    if not ver:
        edl["costuras_duras"] = duras
        json.dump(edl, open(ruta, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        if duras:
            registro.nota("costuras", "costuras que se disimulan",
                          detalle=f"{slug}: {len(duras)} de {total}")
    print(f"{slug}: {total} empalmes · {movidas} movidas · {len(duras)} a disimular")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--bordes", action="store_true",
                    help="lleva entradas y salidas a la frontera de frase")
    ap.add_argument("--palabras", action="store_true",
                    help="saca los cortes de dentro de una palabra")
    a = ap.parse_args()
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        if a.palabras:
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
            mudos(slug, ver=a.ver)
        elif a.bordes:
            bordes(slug, ver=a.ver)
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
        else:
            # **El paso completo, que es lo que corre la fase `cosido`.**
            #
            # Estaba a medias: la fase solo movia costuras, y las garantias
            # —que ningun corte caiga dentro de una palabra, que dos trozos no
            # se pisen, que no quede un resto sin palabras— solo corrian si
            # alguien las lanzaba a mano. O sea que **no corrian**: el remate
            # del gancho de reel-01 volvio a quedar cortado dentro de «suerte»
            # despues de cada arreglo, y habia que descubrirlo mirando.
            #
            # Van antes del optimizador y en este orden: primero se deja el
            # corte sano, luego se busca que la union suene bien. Al reves, el
            # optimizador afina una costura que despues se mueve.
            # **`bordes` NO va aqui, y es a proposito.** Decide —si la palabra
            # de delante es la cabeza que falta o la cola de otra idea— y eso
            # es criterio: Jaime lo saco del automatismo *«el detector apunta y
            # tu decidas caso a caso»*. Metido en la fase, deshacia las
            # decisiones del paso anterior: devolvia «Yo conte» al gancho y
            # «500,» al beat del precio, y la pieza volvia a repetirse.
            #
            # Aqui solo lo que es aritmetica y no puede equivocarse.
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
            # Despues de cuadrar los bordes a palabra entera, porque es ese
            # ajuste el que deja el corte pegado al ataque.
            ataques(slug, ver=a.ver)
            # Y fuera el aire de los bordes, que es donde estaba.
            colas(slug, ver=a.ver)
            mudos(slug, ver=a.ver)
            arreglar(slug, ver=a.ver)


if __name__ == "__main__":
    main()
