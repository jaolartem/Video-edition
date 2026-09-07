"""La redundancia, que la decide el modelo de lenguaje y no Python.

Regla de Jaime, y cierra el diseño de este paso:

    *«La redundancia no es algo que se pueda inferir con código fácilmente.
    Necesitaríamos un modelo probabilístico de predicción de lenguaje, que es
    exactamente lo que tenemos contigo. No está en la capacidad de Python ni de
    ninguna de sus dependencias.»*

Está comprobado y costó tres intentos. Un trigrama no ve que «de cada 100
dólares que él» y «100 dólares que él recibe él» son la misma frase empezada dos
veces: **no comparten ningún trigrama**. Ni que «pero que el sistema se quedó» y
«pero que el sistema capturó» dicen lo mismo con otro verbo. Eso es comprender,
no comparar cadenas, y el último intento —`partir_por_repeticion`— dejó la pieza
más larga que antes.

## El reparto, y por qué es limpio

**Se queda en `depurar.py`** lo que de verdad es mecánico y se mide: el aire —un
hueco sin una sola palabra— y el tartamudeo —la misma palabra pegada a sí misma.

**Viene aquí** todo lo que necesita entender la frase: la misma idea dicha dos
veces con otras palabras, el arranque abortado, la cola que no cierra, el dato
repetido.

## Cómo funciona

Este script no decide nada. Prepara el **dossier** —el texto de la pieza montada,
por etapas, con la entrega medida al lado— y carga de vuelta los cortes que el
modelo devuelve, que entran en `revision` como notas `cortar` **ancladas al
texto**. Anclarlas al texto y no al segundo es lo que hace que sobrevivan a que
la pieza se vuelva a montar (C-79).

    python scripts/redundancia.py 2               # el dossier del reel 2
    python scripts/redundancia.py --cargar 2 c.json  # los cortes que devolvio
"""
import argparse
import json
import os
import re
import sqlite3 as _sq3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import registro  # noqa: E402
import revision  # noqa: E402
import servicio  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

PROMPT = os.path.join(os.path.dirname(__file__), "redundancia.prompt.md")

REGLA = ("la repeticion del bruto es un abanico para elegir, no basura que"
         " recortar: sobra UNA version, la que mas comunique. Reconocerlo es"
         " prediccion de lenguaje, no coincidencia de n-gramas: por eso vive en"
         " el paso de IA y no en Python.")


# Cuantas palabras de contexto se dan a cada lado de un borde.
#
# Empezo en ocho, por no convertir el dossier en la cinta entera. Se quedaba
# corta justo donde mas se necesita: en reel-05 b6 la pieza dice «mil dolares de
# impuesto adicional» sin el numero, y el numero cae **fuera** de las ocho —lo
# que se ve es «mientras que las cosas que las cosas no»—, asi que la cifra que
# sostiene toda la incomodidad del SELL parecia irrecuperable cuando estaba a un
# par de palabras.
#
# Y hay un segundo caso que la ventana corta no sabe resolver: en b5, `antes`
# acaba en «el no tuvo un no tuvo un mes» y no se puede saber si ese «no» es de
# esta frase o de la anterior. Un «no» de mas invierte la etapa igual que uno de
# menos, asi que con la duda no se toca — y la duda la crea la ventana.
#
# Dieciseis sigue siendo una mirada y cubre las dos cosas.
VECINAS = 16


def _vecinas(palabras, borde, lado):
    """Las palabras de la cinta pegadas a un borde del corte, por fuera.

    Es lo que el montaje **dejo fuera** justo ahi. Un borde que decapita una
    cifra o se come un «no» solo se reconoce mirando esto: por dentro el texto
    parece una frase entera.

    **Cada palabra va con su segundo**, y esa es la mitad util. Sin el tiempo
    solo se puede decir «falta una palabra delante» y hay que estimar donde
    empieza — y un borde estimado es el mismo defecto otra vez: se pasa de largo
    y se lleva la cola de la toma fallida de antes. Paso en reel-01 b7, donde lo
    que hay pegado al borde no es la palabra que falta sino un intento roto que
    termina en «hasta 500», una cifra que contradice a la buena.

    Con el segundo delante, proponer el borde deja de ser un calculo: es copiar
    el `en` de la primera palabra que hay que recuperar.
    """
    if lado == "antes":
        fuera = [w for w in palabras if w["end"] <= borde + 1e-3][-VECINAS:]
    else:
        fuera = [w for w in palabras if w["start"] >= borde - 1e-3][:VECINAS]
    return [[round(w["start"], 3), round(w["end"], 3), w["text"].strip()]
            for w in fuera]


# Lo que hace que una frase sea un cierre: manda a algun sitio. No es una lista
# de palabras bonitas, son las cuatro formas en que este proyecto pide la accion
# —el link, la descripcion, inscribirse, el cupo— y estan tomadas de lo que
# Jaime dice de verdad en las cintas, no inventadas.
# Quitar tildes lo hace `dominio.texto`, que es su dueño. Estaba copiado aquí
# palabra por palabra.
from dominio.texto import _sin_tildes  # noqa: E402


CIERRE = re.compile(
    r"(link|enlace|descripci|inscri|registrar|apunt|cupo|reserv|primer comentario)")


def material_para(slug, faltan, ventana=14, cuantas=6):
    """Ventanas del corpus que podrian cumplir una etapa que se quedo sin voz.

    ## Por que esto tiene que ser un dato y no una busqueda mia

    Tres pasos distintos dieron por no grabado material que si estaba. La etapa
    5 de reel-01 —el mecanismo, «como sacar plata de su negocio para pasarla a
    su bolsillo»— esta en **cuatro cintas**; el mecanismo del umbral de reel-05
    esta en la suya y ademas **ya montado** en el corte EDUCATE de la misma
    pieza. Ninguno de los tres lo encontro, y no por criterio: porque nadie les
    enseño mas que su propia cinta.

    Cuando se busco a mano aparecio en minutos. Y ahi esta la trampa: buscarlo a
    mano y declararlo yo lo arregla una vez y deja el agujero abierto. Jaime lo
    corto en tres palabras — *«siempre dentro del pipeline»*. Asi que el corpus
    entra como `material_en_corpus` en el pedido, con sus segundos, y **elige el
    paso**, igual que ya elige entre los cierres.

    Es la generalizacion de `cierres_en_corpus`: alli se buscaba una funcion
    concreta —mandar a algun sitio— y aqui la funcion la define el libreto de la
    etapa que falta.

    `faltan` son los ordenes de etapa sin material. Se puntua por palabras de
    contenido compartidas con su libreto, que es lo que el paso 2 ya hace para
    elegir: no se decide nada aqui, se ordena lo que hay.
    """
    import rutas as _ru

    con = basedatos.abrir("ads/decisiones.db")
    con.row_factory = _sq3.Row
    libretos = {r["orden"]: r["texto"] for r in con.execute(
        "select l.orden, l.texto from libreto l join video v on v.id = l.video_id"
        " where v.slug = ?", (slug,))}
    con.close()

    # Palabras que no distinguen nada: si puntuaran, ganaria la ventana mas
    # larga en vez de la que dice lo mismo.
    VACIAS = set("de la que el en y a los las un una es no se lo por con su del"
                 " al para mas o si le me ya son como pero esta este esa ese"
                 " sus te tu yo he ha han hay muy tan todo toda".split())

    def claves(t):
        return {w for w in _sin_tildes(t or "").split()
                if len(w) > 3 and w not in VACIAS}

    # **Las candidatas se construyen sobre tramos de habla, no sobre ventanas
    # de N palabras.** Cortar cada 14 palabras parte frases por la mitad: la
    # mejor candidata de reel-01 e5 salia como «hacer es ensenarle como sacar
    # plata de su empresa para meterla en su bolsillo», sin cabeza ni cierre.
    #
    # Un tramo de habla ya es una unidad: empieza y acaba donde el hablante
    # calla. Se juntan los consecutivos hasta `LARGO` para que quepa una idea
    # entera, y el resultado son frases que se pueden montar tal cual.
    LARGO = 13.0
    fuera = {}
    for beat in faltan:
        obj = claves(libretos.get(beat, ""))
        if not obj:
            continue
        marcadas = []
        for toma in _ru.material():
            ft = os.path.join(_ru.TRABAJO, "transcripts", f"{toma}.json")
            fc = os.path.join(_ru.TRABAJO, "cuts", f"{toma}.json")
            if not (os.path.exists(ft) and os.path.exists(fc)):
                continue
            try:
                ws = json.load(open(ft, encoding="utf-8")).get("segmentos") or []
                voz = json.load(open(fc, encoding="utf-8"))["segmentos"]
            except (OSError, KeyError, json.JSONDecodeError):
                continue
            grupos, act = [], []
            for x, y in voz:
                if act and y - act[0][0] > LARGO:
                    grupos.append((act[0][0], act[-1][1]))
                    act = []
                act.append((x, y))
            if act:
                grupos.append((act[0][0], act[-1][1]))
            for a, b in grupos:
                tro = [w for w in ws if transcribir.suena(w, a, b)]
                if len(tro) < 4:
                    continue
                txt = " ".join(w["text"] for w in tro).strip()
                punto = len(obj & claves(txt))
                if punto < 2:
                    continue
                marcadas.append({
                    "beat": beat, "toma": toma, "punto": punto,
                    "desde": round(tro[0]["start"], 3),
                    "hasta": round(tro[-1]["end"], 3),
                    "texto": txt,
                    "palabras": [[round(w["start"], 3), round(w["end"], 3),
                                  w["text"].strip()] for w in tro],
                })
        marcadas.sort(key=lambda x: (-x["punto"], x["hasta"] - x["desde"]))
        fuera[beat] = marcadas[:cuantas]
    return fuera


def cierres_en_corpus(margen=14):
    """Los cierres grabados en **todas** las cintas, con su cinta y sus segundos.

    ## Por que esto tiene que estar en el dossier

    El repaso ve el montaje y ~16 palabras a cada lado de cada corte. Con eso
    puede arreglar un borde, y **no puede arreglar una pieza sin CTA**: tres
    agentes distintos devolvieron la misma frase —«no puedo proponer un cierre
    de otra toma»— y tenian razon, porque el contrato no les enseñaba ninguna.

    Y el material estaba. Jaime lo dijo antes de que se midiera: *«hay varios,
    todo eso se grabo; la pregunta es por que no se esta encontrando o por que
    no se esta buscando»*. Medido despues: **seis de las siete cintas** tienen
    un cierre entero. Las dos piezas sin CTA fallaban por razones distintas —
    reel-02 lo tiene en su propia cinta y no se encontro; reel-04 no lo tiene en
    la suya y esta en otras cuatro, y ahi no se buscaba.

    Que una etapa pueda venir de otra cinta no es una excepcion: es la unidad de
    analisis del proyecto. *«La unidad basica es la seccion de frame, y eso sale
    de la union de la teorica —el libreto— con la practica —la grabacion»*. El
    modelo lo permite y `fijar` lo aplica; lo unico que faltaba era **enseñarlo
    a quien decide**.
    """
    import rutas as _ru

    out = []
    for toma in _ru.material():
        f = os.path.join(_ru.TRABAJO, "transcripts", f"{toma}.json")
        if not os.path.exists(f):
            continue
        try:
            ws = json.load(open(f, encoding="utf-8")).get("segmentos") or []
        except (OSError, json.JSONDecodeError):
            continue
        vistos = set()
        for i, w in enumerate(ws):
            if not CIERRE.search(_sin_tildes(w.get("text") or "")):
                continue
            a, b = max(0, i - margen), min(len(ws), i + margen + 1)
            # Un cierre se dice varias veces seguidas al grabar; la ventana de
            # la segunda solapa con la de la primera y seria la misma frase dos
            # veces. Se queda una por region.
            if any(a < y and x < b for x, y in vistos):
                continue
            vistos.add((a, b))
            out.append({
                "toma": toma,
                "desde": round(ws[a]["start"], 3),
                "hasta": round(ws[b - 1]["end"], 3),
                "texto": " ".join(x["text"].strip() for x in ws[a:b]),
                # **Con sus tiempos por palabra, como `antes` y `despues`.**
                # Sin ellos un cierre del corpus solo se puede tomar entero, y
                # los de verdad vienen con dos arranques pegados o con un «el
                # link esta abajo» de mas. Tres piezas se quedaron sin poder
                # meter el escalon del precio por esto —«viene sin tiempos de
                # palabra, no puedo recortarlo sin estimar»— teniendo el
                # material delante. Es C-118 otra vez: cuando un paso tiene que
                # devolver segundos, los segundos tienen que estar en lo que se
                # le da.
                "palabras": [[round(x["start"], 3), round(x["end"], 3),
                              x["text"].strip()] for x in ws[a:b]],
            })
    return out


def _suena(toma, a, b, hueco=0.35):
    """Cuanto se OYE en ese tramo, medido sobre la onda y no sobre el texto.

    Regla de Jaime: *«escuchalo tambien, con el whisper no sabes si hay o no
    sonido»*. Y tiene razon en lo literal: el transcript da palabras, asi que un
    tramo con cinco segundos mudos dentro se lee como una frase entera. Es lo
    que dejo el tablero de reel-01 sin explicacion en el segundo 30 y lo que
    hundio tres etapas en C-114 — el mismo error por dos puertas.

    Lo que mide el hecho es el detector de voz, que corre sobre la onda y vive
    en `work/cuts/<toma>.json`. De ahi salen tres cosas que el texto no puede
    dar: cuanto se habla, cuanto se calla, y **donde** estan los huecos, que es
    lo unico que permite decir «aqui no dice nada» sin oirlo.

    Solo se cuentan los huecos de mas de `hueco` segundos: por debajo de eso es
    respiracion, no silencio.
    """
    import rutas as _ru

    f = os.path.join(_ru.TRABAJO, "cuts", f"{toma}.json")
    if not os.path.exists(f):
        return None
    try:
        tramos = json.load(open(f, encoding="utf-8"))["segmentos"]
    except (OSError, KeyError, json.JSONDecodeError):
        return None
    dentro = sorted((max(a, x), min(b, y)) for x, y in tramos
                    if min(b, y) - max(a, x) > 0.01)
    habla = sum(y - x for x, y in dentro)
    huecos, cursor = [], a
    for x, y in dentro:
        if x - cursor > hueco:
            huecos.append([round(cursor - a, 2), round(x - a, 2)])
        cursor = max(cursor, y)
    if b - cursor > hueco:
        huecos.append([round(cursor - a, 2), round(b - a, 2)])
    return {"habla_s": round(habla, 2), "mudo_s": round((b - a) - habla, 2),
            "huecos": huecos}


def dossier(slug, con_voz=True):
    """El texto de la pieza montada, por trozos y en orden, con su entrega.

    Se recorre en **orden de montaje** porque es lo que el espectador oye, y con
    el texto de la cinta —cuatro pasadas— porque es el bueno. Los números de
    entrega van al lado para que la eleccion entre dos versiones no sea a ojo.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache, out, t = {}, [], 0.0
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        toma = det.get("toma") or rutas.TOMAS.get(slug)
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        # La vara de que palabra suena dentro del corte vive en
        # `transcribir.suena` (C-84): este era el tercer sitio que llevaba su
        # propia copia, y con la copia vieja el dossier de redundancia perdia
        # una palabra en cada borde — justo donde se ve si dos trozos dicen lo
        # mismo.
        ws = [w["text"] for w in cache[toma]
              if transcribir.suena(w, rango[0], rango[1])]
        dur = (rango[1] - rango[0]) / beats.VELOCIDAD
        if ws:
            fila = {"en": round(t, 1), "beat": det.get("beat"),
                    "etapa": det.get("etapa"), "texto": " ".join(ws),
                    # **Los segundos del trozo y su cinta.** Sin esto, quien lee
                    # el dossier puede senalar que un borde esta mal y no puede
                    # decir donde va: proponer un tramo exige saber de que
                    # segundo a que segundo va el que hay.
                    "toma": toma,
                    "desde": round(rango[0], 3), "hasta": round(rango[1], 3),
                    # **Y lo que quedo fuera a cada lado.** Este era el agujero
                    # que dos agentes en frio encontraron por separado: el
                    # dossier daba el texto cosido y nada del contexto, asi que
                    # se podia ver que una frase estaba decapitada —«mil dolares»
                    # sin la cifra, «de septiembre» sin el dia— y no se podia
                    # decir que palabra falta. Con el contexto, el borde roto
                    # deja de ser una sospecha y pasa a ser una propuesta.
                    "antes": _vecinas(cache[toma], rango[0], "antes"),
                    "despues": _vecinas(cache[toma], rango[1], "despues"),
                    # **Lo que se oye, medido sobre la onda.** Ver `_suena`.
                    "suena": _suena(toma, rango[0], rango[1]),
                    }
            # **El umbral es el de la medida, no uno propio.**
            #
            # Esto ponia 0,6 s y la medida necesita `beats.VENTANA_MIN`. Entre
            # los dos numeros hay una franja donde el codigo llamaba a medir,
            # `contorno` devolvia `None` por ventana corta y `expresividad`
            # aplanaba ese `None` en **0.0** — asi que el trozo viajaba al
            # contrato con «voz 0.0, tono 0.0», que es exactamente lo que se
            # manda cuando algo se dijo sin una gota de entrega. El agente no
            # tiene forma de distinguir «lo medi y esta muerto» de «no lo pude
            # medir», y el prompt le promete los numeros sin condiciones.
            #
            # El contrato ya lo tenia declarado —`condicional` y `si_falta` en
            # `montaje[].voz / .tono`— y era el codigo el que no lo cumplia. Con
            # `cabe()` el campo **no viaja** cuando no se puede medir, que es lo
            # que el contrato dice y lo unico honesto: un hueco se ve, un cero
            # inventado no.
            if con_voz and beats.cabe(rango[0], rango[1]):
                # Y el `except` deja de ser mudo: con la precondicion delante,
                # aqui ya no hay fallo esperado. Uno que salte es un fallo de
                # verdad y tiene que llegar al log, no morir en un `pass`.
                try:
                    fila["voz"] = round(
                        beats.expresividad(toma, rango[0], rango[1]) or 0.0, 2)
                    fila["tono"] = round(
                        beats.cambio_de_tono(toma, rango[0], rango[1]), 1)
                except Exception as e:             # noqa: BLE001
                    registro.aviso("redundancia", "no se pudo medir un trozo",
                                   detalle=f"{toma} {rango[0]:.2f}-{rango[1]:.2f}:"
                                           f" {type(e).__name__} {e}", eco=False)
            out.append(fila)
        t += dur
    return out


def cargar(slug, cortes, pasada=1):
    """Mete los cortes que devolvio el modelo como notas de revision.

    **No se aplican aqui.** Entran en `revision` con su ancla y su porque, y las
    aplica `revision.py` — que es quien sabe re-aplicarlas cuando la pieza se
    vuelve a montar. Un paso que corta por su cuenta se pisa con el otro.
    """
    n = 0
    for c in cortes:
        ancla = (c.get("ancla") or "").strip()
        if not ancla:
            continue
        revision.anotar(slug, "cortar", None, None,
                        c.get("por_que") or "redundancia",
                        regla=REGLA, pasada=pasada, ancla=ancla,
                        cual=int(c.get("cual") or 1))
        n += 1
    return n


def main():
    """Pide al servicio y carga lo que conteste. **No decide nada aqui.**

    Regla de Jaime: *«aunque seas el que ejecuta te vas a mover dentro del
    pipeline reemplazando a la IA que se conecta por tokens o por bash; nunca
    puedes tomar decisiones por fuera de la linea»*.

    Asi que este paso ya no imprime un dossier para que alguien lo lea y actue:
    **escribe un pedido y espera una respuesta**. La conteste el CLI o la
    conteste yo, el contrato es el mismo y queda registrada. Lo que se acabo es
    leer el dossier y editar la base a mano — por ese agujero se colo todo lo
    que salio mal.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true",
                    help="ensena el dossier sin pedir nada")
    a = ap.parse_args()
    prompt = open(PROMPT, encoding="utf-8").read()
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        filas = dossier(slug)
        if not filas:
            continue
        if a.ver:
            print("== " + slug + " ==")
            for f in filas:
                voz = (f"  [voz {f['voz']} · tono {f['tono']}]"
                       if "voz" in f else "")
                print(f"{f['en']:>6.1f}  b{f['beat']}{voz}")
                print("        " + f["texto"])
            continue
        r = servicio.pedir("redundancia", slug, prompt, filas)
        if r is None:
            print(f"{slug}: pedido puesto, sin respuesta todavia"
                  f" -> {servicio.ruta_pedido('redundancia', slug)}")
            continue
        print(f"{slug}: {cargar(slug, r)} corte(s) anotados por el servicio")


if __name__ == "__main__":
    main()
