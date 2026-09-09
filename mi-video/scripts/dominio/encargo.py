"""Qué etapas hay que describir, y con qué delante.

El listado sale de la **estructura** —las etapas que el frame define— y no del
montaje, porque el montaje es justo lo que puede haber perdido una. Pero lo que
se describe es el montaje, así que cada fila viaja con las dos mitades: la
función que la etapa cumple y lo que de verdad se dice ahí hoy.

**Sin filtro en SQL.** Antes se excluía aquí toda etapa ya descrita, y por eso una
descripción caducada no se volvía a pedir: el paso decía «nada que describir» y
la puerta paraba la pieza sin que nadie supiera qué faltaba. Ahora se traen todas
y se descartan abajo las que siguen hablando de su texto — que es una comparación
de textos y no cabe en el WHERE.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from .montaje import Montaje  # noqa: E402
from .texto import dice_lo_mismo  # noqa: E402
from .pieza import Pieza  # noqa: E402
from .repetido import repetido  # noqa: E402
from .alcance import Alcance  # noqa: E402

ETAPAS = """
    select v.slug, e.orden, ec.nombre as etapa, es.nombre as estructura,
           e.mensaje_esperado as mensaje, l.texto as libreto,
           (select group_concat(u.texto, ' ') from eleccion el
              join fragmento f on f.id = el.fragmento_id
              join fragmento_unidad fu on fu.fragmento_id = f.id
              join unidad u on u.id = fu.unidad_id
             where el.etapa_id = e.id) as dicho
      from etapa e
      join video v on v.id = e.video_id
      join estructura es on es.id = e.estructura_id
      left join etapa_canonica ec
             on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
      left join libreto l on l.video_id = v.id and l.orden = e.orden
     where l.texto is not null {donde}
     order by v.slug, e.orden
"""


def quitadas(slug: str) -> set:
    """Las etapas que una nota de corte sacó de la pieza **a propósito**.

    Lo mismo que mira `verificar` para no contar como falta lo que alguien mandó
    quitar (C-106). Las dos preguntas son la misma: **una etapa ausente por
    decisión no es una etapa ausente por falta**.
    """
    try:
        con = basedatos.abrir()
        filas = con.execute(
            "select que from revision where video_slug = ? and accion='cortar'"
            " and estado='aplicada' and regla='seccion que sobra'",
            (slug,)).fetchall()
        con.close()
    except Exception:                              # noqa: BLE001
        return set()
    return {int(b) for (q,) in filas for b in re.findall(r"e(\d+)", q or "")}


class _DeLaPieza:
    """Lo que hay que calcular una vez por pieza, no una vez por etapa.

    `repetido` mide la entrega de cada aparición con el detector de F0: llamarlo
    dentro del bucle de filas lo repetía una vez por etapa —nueve veces la misma
    cuenta en reel-05— para tirar ocho de los nueve resultados.
    """

    def __init__(self, slug: str):
        m = Montaje(slug)
        self.texto = Pieza(int(slug.split("-")[1])).texto
        self.bordes = m.bordes_sucios()
        self.repetido = repetido(m)
        self.quitadas = quitadas(slug)
        self.en_la_cinta = _en_la_cinta(slug)
        #: Hasta donde llega el encargo de hoy en esta pieza.
        self.alcance = Alcance.de(slug, "descrito")


def _en_la_cinta(slug):
    """Donde vive cada etapa EN LA CINTA: `{beat: (toma, desde, hasta)}`.

    Hace falta para sacarle los cinco fotogramas a la toma, y sin esto no se
    sacaba ninguno. `describir.mjs` los pide fila a fila y se rinde en silencio
    si la fila no trae `toma`, `start` y `end` — que era siempre, porque esta
    consulta nunca los puso.

    El efecto: **el bloque que pregunta si esta LEYENDO nunca se ejecuto.** Esta
    escrito en `describir-pedido.mjs` con las palabras de Jaime dentro —«no, esos
    ojos no sirven, ya han fallado; que tome cinco fotogramas repartidos por toda
    la escena y mire la foto», «generalmente tengo el papel en las piernas,
    entonces estoy mirando hacia abajo»— y el compositor no ha visto un
    fotograma en su vida. Declarado, escrito, y sin el dato que lo enciende.

    Se toma el primer tramo del beat y el ultimo: es la ventana de la etapa en
    su cinta, que es lo que `fotogramas.de_la_cinta` necesita para repartir los
    cinco.
    """
    import json
    import os

    ruta = os.path.join("ads", slug, "edl-sell.json")
    if not os.path.exists(ruta):
        return {}
    try:
        edl = json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    fuera = {}
    for (a, b), d in zip(edl.get("segmentos", []), edl.get("detalle", [])):
        beat = d.get("beat")
        if beat is None:
            continue
        toma = d.get("toma") or edl.get("toma")
        if not toma:
            continue
        if beat in fuera:
            t, x, y = fuera[beat]
            fuera[beat] = (t, min(x, float(a)), max(y, float(b)))
        else:
            fuera[beat] = (toma, float(a), float(b))
    return fuera


def por_describir(reels=None, rehacer: bool = False) -> list:
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    donde, args = "", []
    if reels:
        donde = " and v.slug in (%s)" % ",".join("?" * len(reels))
        args = [f"reel-{int(r):02d}" for r in reels]
    con = basedatos.abrir()
    con.row_factory = sqlite3.Row
    # **«Nada que describir» y «esta pieza no está declarada» no son lo mismo.**
    #
    # reel-07 pasó por aquí con **cero etapas** —estaba en `ads/frames.json` con
    # sus ocho beats y la base no se había enterado— y esta consulta devolvió
    # una lista vacía, que el paso leyó como «ya está todo descrito» y dio por
    # bueno. La pieza siguió camino y sólo reventó tres fases más arriba, con un
    # mensaje que apuntaba a este paso: «sin descripción de escena, corre el
    # paso 4». Correrlo mil veces no habría arreglado nada.
    #
    # Una pieza sin etapas no es una pieza terminada: es una pieza sin declarar,
    # y decir «nada que hacer» es mentir en el único sitio donde alguien mira.
    for s in args:
        n = con.execute("select count(*) from etapa e join video v"
                        " on v.id = e.video_id where v.slug = ?", (s,)).fetchone()[0]
        if not n:
            con.close()
            raise ValueError(
                f"{s} no tiene ni una etapa declarada en la base. No es que no"
                f" haya nada que describir: es que no hay pieza. Corre"
                f" `python scripts/db.py migrar` para meter `ads/frames.json`.")
    filas = con.execute(ETAPAS.format(donde=donde), args).fetchall()
    # La caducidad se decide comparando textos, y en SQL no se puede porque el
    # montaje se calcula leyendo la cinta. Se trae lo escrito y se compara aquí.
    # **Y viaja la descripcion aprobada, no solo su fecha.** Jaime: *«lo que ya
    # se aprobo no se vuelve a discutir: se revisa que este como se dijo»*.
    # Trayendo unicamente `sobre_texto` sabiamos que estaba caducada y quien
    # contestaba la escribia **desde cero**, sin ver la que ya habia — asi que
    # dos vueltas seguidas podian describir la misma etapa de dos maneras sin
    # que nada hubiera cambiado salvo el enfoque de quien miraba.
    filas_desc = list(con.execute(
        "select video_slug, etapa_orden, sobre_texto, que_pasa, emocion,"
        # **Y el tablero, que es la mitad cara de la escena.** Se quedo
        # fuera de la primera version de `ya_dicho` y el efecto fue medio
        # arreglo: la descripcion llegaba aprobada y el tablero no, asi
        # que quien describe tenia que volver a inventarlo aunque la
        # escena no hubiera cambiado. Lo dijo el paso al contestar
        # reel-04: cinco etapas tipograficas rehechas por esto.
        " componente, grafico, color, sonido, plano, tablero"
        " from escena_desc"))
    guardado = {(r["video_slug"], r["etapa_orden"]): (r["sobre_texto"] or "")
                for r in filas_desc}
    aprobada = {(r["video_slug"], r["etapa_orden"]): dict(r) for r in filas_desc}
    con.close()

    fuera, piezas = [], {}
    for f in filas:
        d = dict(f)
        slug, orden = d["slug"], int(d["orden"])
        if slug not in piezas:
            piezas[slug] = _DeLaPieza(slug)
        p = piezas[slug]
        # **Lo que se dijo es lo que dice el montaje, no lo que se eligió.** El
        # `dicho` de la base queda como respaldo para la etapa que no tiene toma
        # —la que va a tablero—, porque ahí no hay montaje del que leer.
        d["montaje"] = p.texto.get(orden)
        # **Una etapa que no esta en la pieza no se describe.** Cuando una se
        # corta entera seguía pidiéndose: la puerta de composición reclamaba una
        # descripción de la etapa 5 del reel-01 después de que Jaime la mandara
        # sacar, y la pieza no podía avanzar por describir algo que ya no suena.
        #
        # **Y la diferencia es por qué no está, no que no esté.** Se cortó por
        # decisión —hay nota, y describirla es trabajo perdido— o nunca tuvo
        # material —reel-04 e5 tiene cero candidatas—, y ésa **sí** hay que
        # describirla, porque el frame la necesita y va a tablero. La primera
        # versión miraba si había `dicho`, y eso mezclaba las dos: dejaba sin
        # describir la etapa que más lo necesita.
        if not (d["montaje"] or "").strip() and orden in p.quitadas:
            continue
        # Los bordes y lo repetido van **con la etapa**, para que quien compone
        # los resuelva con el texto delante en vez de dejárselos a un umbral.
        # Lo aprobado y **sobre que texto se aprobo**, para poder comparar.
        ya = aprobada.get((slug, orden))
        if ya:
            d["ya_dicho"] = {k: v for k, v in ya.items()
                             if k not in ("video_slug", "etapa_orden")}
        # La clave de `bordes_sucios` es texto, siempre: viaja por JSON y ahi
        # deja de ser numero. Ver `Montaje.bordes_sucios`.
        # **Y donde esta esa etapa en la cinta**, que es lo unico que le
        # faltaba a los cinco fotogramas para existir. Ver `_en_la_cinta`.
        sitio = p.en_la_cinta.get(orden)
        if sitio:
            d["toma"], d["start"], d["end"] = sitio
        d["bordes"] = p.bordes.get(str(orden)) or []
        d["repetido"] = [r for r in p.repetido if r["etapa"] == orden]
        if not rehacer:
            # **Se describe UNA vez.** Jaime, el 1 de septiembre: *«solo
            # hacemos una descripcion y una sola composicion grafica; revisar es
            # despues de eso»*, y *«no se devuelve a hacer un reproceso por lo
            # mismo»*.
            #
            # Esto comparo primero cadenas exactas —una muletilla tiraba la
            # descripcion entera— y luego, mejor, por sentido (`dice_lo_mismo`).
            # Las dos versiones compartian el error de fondo: **volver a pedir**.
            # Describir es criterio estetico, y la IA no es determinista: la
            # segunda descripcion no es mejor que la primera, es otra. Con eso la
            # pieza no cierra nunca.
            #
            # Que el texto se haya movido sigue siendo un dato, y no se pierde:
            # `verificar` lo anota como ticket puntual con su etapa, y lo mira
            # quien revisa la pieza montada. Lo que no hace es rehacer el
            # trabajo. `--rehacer` sigue existiendo para pedirlo a mano.
            #
            # **Un tiquet suyo sobre una etapa la vuelve a poner en el encargo.
            # No la rehace: la abre para que la mire con su correccion
            # delante.** Es literalmente lo que hace el otro oficio —ver
            # `servicios/disenar.py :: encargos`, que lo tiene desde el 5 de
            # septiembre— y este paso no lo tenia: una etapa ya descrita no
            # volvia a pedirse nunca, asi que un tiquet de `descrito` dejaba la
            # pieza esperando a un oficio al que nadie preguntaba.
            #
            # Que sea una correccion y no un rediseno lo sostiene la otra mitad,
            # la capa de instruccion: `abierto.MODO` dice «hoy no compones la
            # pieza: arreglas estos tiquets» y `acotado` dice cuales son sus
            # etapas. Sin ella esto si seria volver a describir.
            if (guardado.get((slug, orden)) is not None
                    and not piezas[slug].alcance.abre(orden)):
                continue                 # ya descrita: no se vuelve a pedir
        fuera.append(d)
    return fuera


def huella_del_encargo(grafico):
    """La huella del `grafico` contra el que se compuso un tablero.

    Ata la lámina a la descripción que contesta, igual que `huella` ata una nota
    a su montaje (C-92). Sin ella el encargo se puede reescribir por debajo y el
    tablero se queda contestando a la pregunta de antes — **sin que nada falle**,
    que es la forma cara.
    """
    import hashlib

    t = " ".join((grafico or "").split())
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:12] if t else None


def tablero_desfasado(fila):
    """¿El tablero de esta etapa contesta a un `grafico` que ya no es el de hoy?

    Es la misma pregunta que `dice_lo_mismo` hace de la descripción, del lado del
    diseño, y **es el agujero que dejó reel-07 e6** (C-280): el paso de diseño
    sólo devolvía las etapas sin tablero, con el tablero mudo o con un tiquet
    abierto, así que una etapa re-descrita con su tablero ya puesto no volvía a
    entrar nunca y la descripción nueva no podía llegar a la pantalla.

    **Las filas sin huella no cuentan como desfasadas**: son las de antes de que
    esto existiera y darlas por caducadas devolvería el lote entero al paso de
    diseño de golpe.
    """
    import json

    if not fila.get("tablero"):
        return False
    try:
        guardada = (json.loads(fila["tablero"]) or {}).get("encargo")
    except (TypeError, ValueError):
        return False
    return bool(guardada) and guardada != huella_del_encargo(fila.get("grafico"))


def guardar_tablero(con, slug, beat, kind, props, ahora):
    """Escribe el tablero de una etapa **con la huella de su encargo dentro**.

    Las dos cosas van en la misma escritura porque separarlas es cómo se olvida:
    un tablero sin huella es un tablero del que nadie puede saber si sigue
    contestando a la descripción de hoy. La huella viaja fuera de `props`
    —hermana de `kind`— porque no es copy: `reels/base.mjs :: tablerosDe` lee
    `kind` y `props` y no la ve.
    """
    import json

    g = con.execute(
        "select grafico from escena_desc where video_slug = ? and etapa_orden = ?",
        (slug, beat)).fetchone()
    con.execute(
        "update escena_desc set tablero = ?, fecha = ?"
        " where video_slug = ? and etapa_orden = ?",
        (json.dumps({"kind": kind, "props": props,
                     "encargo": huella_del_encargo(g["grafico"] if g else None)},
                    ensure_ascii=False), ahora, slug, beat))
