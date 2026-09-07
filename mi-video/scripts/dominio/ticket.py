"""Lo que Jaime observa de UNA pieza, con su segundo y su respuesta.

**Por qué es distinto de `instruccion.py`.** Aquello guarda criterios que valen
para todo el lote —«C: no se toca», «máximo 300 líneas»—. Esto guarda lo otro,
que él precisó así: *«mis consideraciones con cada video… como el vídeo X tiene
problemas en el segundo Y y no me gusta X; una línea de tickets y de respuestas a
objeciones»*.

Son dos cosas de naturaleza distinta y por eso no comparten tabla: un criterio se
cumple siempre; una objeción se contesta una vez, sobre una pieza y casi siempre
sobre un instante concreto.

## El segundo es el dato que lo hace utilizable

*«En el segundo 30 el tablero se queda sin sonido»* no se puede atender sin saber
qué etapa cae en el segundo 30. Por eso el ticket guarda `segundo` y sabe
traducirlo a beat con el EDL de la pieza: así el paso que decide recibe **la
objeción colocada en su etapa**, no una frase suelta que alguien tendría que
volver a situar.

Y guarda el segundo **de la pieza montada**, no de la cinta: es lo que Jaime ve
cuando mira el vídeo, y traducirlo es trabajo de la máquina, no suyo.

## Una objeción sin respuesta es una objeción perdida

El estado por defecto es `abierto`, y `contestar()` exige texto. Un ticket que se
cierra sin decir qué se hizo deja a Jaime sin saber si se atendió o se ignoró —
que es exactamente lo que pasa hoy cuando una observación vive sólo en el chat.

**Y `descartado` es una respuesta legítima**, con su porqué: «no se puede, la toma
no existe» es información. Lo que no vale es que desaparezca.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

#: La carpeta `mi-video`, sacada de este fichero y **no del cwd**.
#:
#: `beat_en` abria `ads/<pieza>/edl-sell.json` en relativo, asi que llamado
#: desde cualquier otro directorio devolvia `None` — y `recolocar` escribia ese
#: `None` encima del beat bueno. Lo llama `servicio._tickets` en CADA pedido de
#: CADA paso, con el cwd que traiga quien lance el proceso: medido el 1 de
#: septiembre, los cinco tickets abiertos de reel-01 se quedaban con `beat`
#: NULL, y un ticket sin etapa ni se coloca en el pedido ni entra en ningun
#: cierre por medida. Tres `dirname`, y se cuentan: `scripts/dominio/ticket.py`.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ticket (
  id        INTEGER PRIMARY KEY,
  cuando    TEXT NOT NULL,
  pieza     TEXT NOT NULL,
  segundo   REAL,                    -- en la pieza montada, no en la cinta
  beat      INTEGER,                 -- se deriva del segundo, si se puede
  dijo      TEXT NOT NULL,           -- sus palabras, sin resumir
  tipo      TEXT NOT NULL DEFAULT 'objecion'
            CHECK (tipo IN ('objecion','falta','sobra','suena','dato','gusto')),
  estado    TEXT NOT NULL DEFAULT 'abierto'
            CHECK (estado IN ('abierto','contestado','arreglado','descartado')),
  respuesta TEXT,
  quien     TEXT,
  cerrado   TEXT,
  vuelve_a   TEXT,                   -- la fase que sabe atenderlo
  cierra_con TEXT,                   -- la UNICA medida que puede cerrarlo sola
  devuelto   TEXT                    -- cuando se mando la pieza atras por el
)
"""

#: **Las columnas que hacen del ticket algo con dueno.** Se anaden en caliente
#: porque la tabla ya existe con filas dentro; `CREATE TABLE IF NOT EXISTS` no
#: las mete en una tabla vieja y quedarse sin ellas es quedarse sin mecanismo.
NUEVAS = ("vuelve_a", "cierra_con", "devuelto", "huella")

#: **A que paso vuelve la pieza y que medida puede cerrar el ticket, por tipo.**
#:
#: Se DECLARA al abrirlo, no se deduce del texto: deducir la intencion de una
#: frase es lo que puso la «Y» flotando sobre el plano de reel-01 (C-168). Quien
#: abre el ticket sabe de que habla y lo dice; esto es solo el valor por defecto
#: de cada tipo, escrito una vez.
#:
#: `""` significa **nadie**, y es un caso honesto, no un hueco: «el panel es
#: figurativo» no lo arregla ningun paso solo. Por eso un ticket sin ruta no
#: para el render —Jaime quiere ver la pieza— pero si **para la publicacion
#: final** y sale en `donde.py`.
RUTA = {
    "suena":    ("cosido", "bordes"),
    "sobra":    ("cosido", "texto"),
    "falta":    ("cosido", ""),
    "objecion": ("disenado", ""),
    "dato":     ("", ""),
    "gusto":    ("", ""),
}


#: Las fases que son un SERVICIO —alguien fuera de la linea contesta— y la
#: carpeta donde ese servicio deja su recibo: el pedido que se le escribio y la
#: respuesta que devolvio.
#:
#: Existe porque el 7-9-2026 me salte el conducto entero. Cerre los tiquets de
#: `descrito` y `disenado` de reel-01, reel-03 y reel-05 llamando a la API a
#: mano, sin escribir un solo pedido y sin recoger una sola respuesta — y la
#: linea no dijo nada. Jaime lo vio en la pieza: *«habia un compositor para
#: arreglar el tramo que faltaba, y habia un disenador para recibir las ordenes
#: del compositor y para revisar todo»*. Al ir por fuera, la orden del
#: compositor nunca existio y el disenador nunca tuvo que mirar: reel-03 se
#: entrego dos veces mal, la segunda con el oro cruzandole el pecho.
#:
#: El pedido y la respuesta no son papeleo: son **el sitio donde la decision de
#: un paso se hace visible al siguiente**. Sin ellos los dos papeles se
#: colapsan en uno y la revision deja de tener entrada.
RECIBO = {"descrito": "describir", "disenado": "disenar"}


class SinRecibo(Exception):
    """Un tiquet de servicio que se cierra sin que el servicio haya contestado.

    Es `CierreAjeno` un piso mas abajo. Aquel impide que una medida ajena cierre
    un tiquet; este impide que lo cierre **nadie**: que quien lo cierra diga que
    hubo un paso que en realidad no corrio.

    Como alli, para el paso en vez de dejarlo pasar. Un tiquet cerrado sin que
    su servicio contestara es indistinguible de uno atendido, y es la forma en
    que una revision se salta sin que quede rastro.
    """


class CierreAjeno(Exception):
    """Una medida intenta cerrar un ticket que no declaro que la mide.

    **Para el paso, y a proposito.** Es la averia que Jaime pago dos noches: el
    repaso cerraba el ticket #17 —«la Y que aparece sobre el plano no es un
    panel»— con el texto «la etapa ya no tiene ningun borde sucio: medido, no
    opinado». Una queja grafica cerrada por una medida de bordes de audio, que
    ademas daba el resultado contrario. La pieza salia con el defecto y la lista
    decia que se habia atendido, que es la unica forma de perder una correccion
    sin que nadie lo note.
    """


def _con():
    cx = basedatos.abrir()
    cx.row_factory = sqlite3.Row
    basedatos.esquema(cx, ESQUEMA)
    hay = {r["name"] for r in cx.execute("pragma table_info(ticket)")}
    if not all(c in hay for c in NUEVAS):
        for col in NUEVAS:
            if col not in hay:
                cx.execute(f"alter table ticket add column {col} TEXT")
        cx.commit()
    return cx


#: «No pude mirar», que no es «no cae en ninguna etapa». Ver `beat_en`.
SIN_EDL = object()


def _por_el_plan(pieza, segundo):
    """El beat según **el plan**, que es la línea que se renderiza.

    Devuelve `None` si no hay plan que leer, para que el EDL siga de respaldo.
    """
    ruta = os.path.join(RAIZ, "work", "scenes", pieza, "plan-full.json")
    if not os.path.exists(ruta):
        return None
    try:
        escenas = json.load(open(ruta, encoding="utf-8")).get("escenas") or []
    except (OSError, ValueError):
        return None
    for e in escenas:
        a = float(e.get("montado_desde", 0.0))
        if a <= segundo < a + float(e.get("duracion", 0.0)):
            b = e.get("beat", e.get("etapa_orden"))
            return None if b is None else int(b)
    return None


def beat_en(pieza, segundo):
    """Qué etapa cae en ese segundo de la pieza montada.

    ## El reloj es el del PLAN, no el del EDL

    Se recorría el EDL sumando duraciones, y el EDL **no es el reloj de la
    pieza**: `plan-reel` le quita el aire a cada corte antes de repartirlo en
    escenas —regla de Jaime, *«lo de los silencios también puede ser
    aritmético»*— así que la imagen corre sobre una línea más corta. Está medido
    en `reels/reloj.mjs`: 6,83 s en reel-01, y **el desfase crece hacia el
    final**.

    Consecuencia, medida el 6-9-2026 al abrir tres tickets sobre reel-07: el del
    segundo 38 se archivó en la etapa 3 teniendo que ser la 4, y el del 63 en la
    5 teniendo que ser la 6. Dos de tres, y las dos al final de la pieza, que es
    donde vive el CTA.

    Y no es un error de etiqueta: `dominio/abierto.py` empareja ticket y etapa
    **por beat**, así que un ticket mal colocado abre en el pedido de diseño la
    lámina de al lado. Es justo lo que este fichero declara que viene a evitar —
    *«atender la objeción en la etapa equivocada es peor que no atenderla»*— y
    lo hacía con la lista equivocada. Aprendizaje 33 otra vez: **manda la que se
    renderiza**.

    El EDL se queda de respaldo para la pieza que todavía no tiene plan: ahí es
    la única referencia que hay, y una aproximación declarada vale más que un
    `None`.

    **Y distingue dos «no» que no son el mismo.** `None` es «ese segundo no cae
    en ninguna etapa», que es una respuesta; `SIN_EDL` es «no pude leer el EDL»,
    que no lo es. Confundirlos es lo que hacia que `recolocar` borrase el beat
    bueno de cinco tickets por abrir un fichero en la ruta equivocada: borrar un
    dato porque no se pudo comprobar es peor que no comprobarlo.
    """
    if segundo is None:
        return None
    porPlan = _por_el_plan(pieza, segundo)
    if porPlan is not None:
        return porPlan
    ruta = os.path.join(RAIZ, "ads", pieza, "edl-sell.json")
    if not os.path.exists(ruta):
        return SIN_EDL
    try:
        edl = json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return SIN_EDL
    t = 0.0
    for (a, b), det in zip(edl.get("segmentos", []), edl.get("detalle", [])):
        dur = float(b) - float(a)
        if t <= segundo < t + dur:
            return det.get("beat")
        t += dur
    return None


def _beat(pieza, segundo):
    """El beat si se pudo medir; `None` si no cae y `None` si no se pudo leer."""
    b = beat_en(pieza, segundo)
    return None if b is SIN_EDL else b


class SinEscena(Exception):
    """Un tiquet que no dice a que escena va. Ver `abrir`."""


def abrir(pieza, dijo, segundo=None, tipo="objecion",
          vuelve_a=None, cierra_con=None, etapa=None):
    """Apunta una observación suya, **con quién la atiende y quién la cierra**.

    Los dos se declaran aquí y no se deducen después: un ticket sin paso al que
    volver es un ticket que nadie ejecuta, y uno sin medida declarada es un
    ticket que cualquier medida puede cerrar por su cuenta. Los dos fallos se
    pagaron el 1 de septiembre, en la misma pieza y el mismo día.

    Quien no diga nada se queda con el valor de su tipo, que está en `RUTA`.
    """
    # **Y no se abre un ticket que nadie pueda cerrar.** Con `cierra_con` vacio,
    # `contestar` lo rechaza siempre: el defecto se arregla en la pieza y el
    # ticket se queda abierto para siempre, diciendo que falta algo que ya esta.
    # Paso con el #240. Si el tipo no trae medida por defecto, la medida es el
    # nombre del tipo — que es peor que una buena y mucho mejor que ninguna.
    por_defecto = RUTA.get(tipo, ("", ""))
    if cierra_con is None and not por_defecto[1]:
        cierra_con = tipo
    # **Y no se abre un tiquet sin decir a que escena va.** Jaime, 7-9-2026:
    # *«cada tiquet va ligado a la escena y el compositor solo ve esa escena»*.
    # Sin escena nadie puede acotar: el #282 salio asi y el pedido pidio las
    # ocho etapas de reel-01 para arreglar una palabra.
    #
    # Se admiten las tres formas de decirlo —el segundo, el numero en el texto,
    # o «la pieza entera» a proposito— y **no se admite el silencio**, que era
    # lo unico que no se distinguia de un descuido. La pieza entera es legitima:
    # «no explica el mecanismo» no es de una escena.
    beat = _beat(pieza, segundo)
    if beat is None or beat is SIN_EDL:
        from . import abierto as _ab
        beat = _ab.etapa_de(dijo)
    if beat is None and str(etapa).lower() not in ("pieza", "0", "todas"):
        raise SinEscena(
            f"{pieza}: un tiquet dice a que escena va. Pasa `segundo=`, nombra"
            f" la etapa en el texto («e7», «etapa 7»), o declara"
            f" `etapa=\"pieza\"` si de verdad es de la pieza entera.")
    cx = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    cur = cx.execute(
        "insert into ticket (cuando, pieza, segundo, beat, dijo, tipo,"
        " vuelve_a, cierra_con, huella) values (?,?,?,?,?,?,?,?,?)",
        (ahora, pieza, segundo, beat if beat is not SIN_EDL else None,
         dijo, tipo,
         por_defecto[0] if vuelve_a is None else vuelve_a,
         por_defecto[1] if cierra_con is None else cierra_con,
         _huella(pieza)))
    cx.commit()
    return cur.lastrowid


def situar(id_, segundo):
    """Declara **en que segundo de la pieza** cae un tiquet abierto sin el.

    Hermana de `medir`, y por el mismo motivo: `abrir` acepta un tiquet sin
    segundo —hay objeciones que son de la pieza entera— pero entonces se queda
    sin `beat`, y sin beat no se puede acotar. El 7-9-2026 el #282 salio asi y
    el pedido del compositor pidio las ocho escenas de reel-01 para arreglar
    una palabra.

    No es una puerta trasera: **deja el segundo escrito** y el beat se deriva
    como en cualquier otro, con `beat_en`.
    """
    cx = _con()
    cx.execute("update ticket set segundo = ?, beat = ? where id = ?",
               (float(segundo), _beat(
                   cx.execute("select pieza from ticket where id = ?",
                              (id_,)).fetchone()["pieza"], float(segundo)), id_))
    cx.commit()
    return segundo


def medir(id_, medida):
    """Declara **qué medida cierra** un ticket que se abrió sin decirlo.

    Un ticket con `cierra_con` vacío no lo puede cerrar nada: `contestar` lo
    rechaza, y con razón —ver `CierreAjeno`—. Pero eso deja tickets muertos, y
    pasó: el #240 —«bootcamp en viu» por «en vivo»— quedó arreglado en la pieza
    y sin forma de darlo por cerrado, porque su tipo no traía medida por defecto
    en `RUTA`.

    Esto no es una puerta trasera: **declara la medida y la deja escrita**, que
    es justo lo que faltó al abrirlo. Cerrar sigue exigiendo que coincida.
    """
    if not str(medida).strip():
        raise CierreAjeno(f"ticket #{id_}: una medida sin nombre no cierra nada")
    cx = _con()
    cx.execute("update ticket set cierra_con = ? where id = ?", (medida, id_))
    cx.commit()
    return medida


def _huella(pieza):
    """La huella del corte sobre el que se abre el ticket. `None` si no se sabe."""
    try:
        from . import version
        return version.huella_edl(pieza)
    except Exception:
        return None


def caducar(pieza):
    """**Un ticket se muere cuando se muere la composición sobre la que se hizo.**

    Regla de Jaime, 7-9-2026, mirando los 31 que le quedaban de días anteriores:
    *«sólo quedaban abiertos los últimos que te hice; los anteriores se mueren
    cuando sí composición se muere»*.

    Y es la regla correcta, no una amnistía. Una queja dice «en el segundo 38 no
    termina la idea» **de un corte concreto**; cuando esa pieza se vuelve a
    montar, el segundo 38 es otra cosa y la queja no se puede ni comprobar ni
    aplicar. Dejarla abierta no la conserva: la convierte en un pendiente que
    nadie puede quitar y que tapa a los que sí valen. Si el defecto sigue, él lo
    vuelve a decir en la revisión siguiente — que es lo que hace en cada entrega.

    **Y por eso los tickets se estampan con la huella del corte al abrirlos**,
    como las notas de `revision` (C-238). Sin ese sello no había forma de saber
    de qué montaje hablaba cada uno, y por eso 31 quejas de tres cortes atrás
    seguían contándose como pendientes de hoy.

    No caducan los de la corrida en curso: llevan la huella de este mismo corte.
    """
    h = _huella(pieza)
    if not h:
        return []
    cx = _con()
    viejos = [dict(r) for r in cx.execute(
        "select id, dijo from ticket where pieza = ? and respuesta is null"
        " and (huella is null or huella <> ?)", (pieza, h))]
    if viejos:
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        cx.executemany(
            # `descartado` y no `caducado`: el esquema declara los cuatro
            # estados posibles y anadir uno pide migrar la tabla. Lo que
            # distingue a estos lo dice su respuesta, que es donde se lee.
            "update ticket set respuesta = ?, estado = 'descartado', quien ="
            " 'la linea', cerrado = ? where id = ?",
            [("Caducado con el corte: se abrio sobre un montaje que ya no existe"
              f" (el de hoy es {h}). Regla de Jaime: «los anteriores se mueren"
              " cuando la composicion se muere». Si el defecto sigue, vuelve a"
              " salir en la revision de la entrega nueva.", ahora, v["id"])
             for v in viejos])
        cx.commit()
    return [v["id"] for v in viejos]


def recibo(pieza, fase, desde):
    """La respuesta de ese servicio para esa pieza, **posterior a `desde`**.

    Devuelve el fichero o `None`. Lo que hace util a esta comprobacion es la
    fecha: una respuesta vieja —la de la vuelta anterior— esta en disco siempre,
    asi que sin comparar contra cuando se abrio el tiquet la guarda la pasaria
    cualquiera con solo tener historia. El recibo tiene que ser DE ESTE tiquet.

    Mira la carpeta del paso y su `usadas/`, que es donde el despachador archiva
    lo que ya consumio: un pedido atendido y archivado sigue siendo un recibo.
    """
    paso = RECIBO.get(fase or "")
    if not paso:
        return ""
    corte = datetime.datetime.fromisoformat(desde).timestamp() if desde else 0
    for d in (os.path.join(RAIZ, "work", "servicio", paso),
              os.path.join(RAIZ, "work", "servicio", paso, "usadas")):
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            if not (f.startswith(pieza + ".") and "respuesta" in f):
                continue
            if os.path.getmtime(os.path.join(d, f)) >= corte:
                return os.path.join(d, f)
    return None


def sin_recibo(pieza=None):
    """Los tiquets de servicio ya cerrados **sin que su servicio contestara**.

    Es la otra direccion de la misma pregunta, y hace falta porque la guarda de
    `contestar` solo puede impedir los proximos: los que ya se colaron siguen
    ahi, diciendo que se atendio algo que nadie miro. Los lee `recibos.py`.
    """
    cx = _con()
    q = ("select id, pieza, cuando, vuelve_a, cerrado from ticket"
         " where estado <> 'abierto' and vuelve_a in (?, ?)")
    args = list(RECIBO)
    if pieza:
        q += " and pieza = ?"
        args.append(pieza)
    filas = cx.execute(q + " order by id", args).fetchall()
    cx.close()
    return [dict(f) for f in filas
            if not recibo(f["pieza"], f["vuelve_a"], f["cuando"])]


def contestar(id_, respuesta, estado="contestado", quien="la linea", medida=""):
    """Cierra un ticket **diciendo qué se hizo, y con qué medida**.

    Sin texto no se cierra, y **la máquina no cierra sin nombrar la medida**:
    `medida` tiene que ser la que el ticket declaró en `cierra_con` al abrirse.
    Si no coincide, esto revienta el paso en vez de dejar pasar el cierre —ver
    `CierreAjeno`—, porque un ticket cerrado en falso es indistinguible de un
    ticket atendido, y es lo que hace que la pieza salga con el defecto.

    Una persona (`quien="Jaime"`) cierra lo que quiera: el criterio humano no
    necesita medida, es la medida.
    """
    if not (respuesta or "").strip():
        raise ValueError("un ticket no se cierra sin decir que se hizo")
    cx = _con()
    if quien == "la linea":
        fila = cx.execute("select cierra_con, dijo from ticket where id = ?",
                          (id_,)).fetchone()
        suya = (fila["cierra_con"] or "") if fila else ""
        if not medida or medida != suya:
            raise CierreAjeno(
                f"ticket #{id_} se cierra con «{suya or 'nadie'}» y lo intenta"
                f" «{medida or 'una medida sin nombre'}»:"
                f" {(fila['dijo'] if fila else '')[:80]}")
        # **Y el servicio tiene que haber contestado.** Ver `SinRecibo`.
        suyo = cx.execute("select pieza, cuando, vuelve_a from ticket"
                          " where id = ?", (id_,)).fetchone()
        if suyo and (suyo["vuelve_a"] or "") in RECIBO:
            if not recibo(suyo["pieza"], suyo["vuelve_a"], suyo["cuando"]):
                raise SinRecibo(
                    f"ticket #{id_} vuelve a «{suyo['vuelve_a']}» y no hay"
                    f" respuesta de ese servicio para {suyo['pieza']} posterior"
                    f" a {suyo['cuando']}. Se cierra cuando el paso conteste,"
                    f" no cuando alguien lo de por contestado.")
    cx.execute("update ticket set respuesta = ?, estado = ?, quien = ?,"
               " cerrado = ? where id = ?",
               (respuesta, estado, quien,
                datetime.datetime.now().isoformat(timespec="seconds"), id_))
    cx.commit()


def abiertos(pieza=None):
    """Los que siguen sin contestar, ya colocados en su etapa."""
    cx = _con()
    if pieza:
        filas = cx.execute(
            "select * from ticket where estado = 'abierto' and pieza = ?"
            " order by segundo, id", (pieza,)).fetchall()
    else:
        filas = cx.execute(
            "select * from ticket where estado = 'abierto'"
            " order by pieza, segundo, id").fetchall()
    cx.close()
    return [dict(f) for f in filas]


def recolocar(pieza):
    """Vuelve a traducir el segundo a etapa. **El corte cambia; el segundo no.**

    Un ticket apunta al segundo 30 de lo que Jaime vio. Si la pieza se recorta,
    ese segundo cae en otra etapa — y atender la objeción en la etapa equivocada
    es peor que no atenderla. Se recoloca en cada corrida.

    **Y no se escribe lo que no se pudo medir.** Si el EDL no se pudo leer, el
    beat que hay se queda como está: borrarlo deja el ticket sin etapa, y sin
    etapa no se coloca en el pedido ni entra en ningún cierre por medida.
    """
    cx = _con()
    n = 0
    for f in cx.execute("select id, segundo from ticket where pieza = ?"
                        " and estado = 'abierto'", (pieza,)).fetchall():
        b = beat_en(pieza, f["segundo"])
        if b is SIN_EDL:
            continue
        cx.execute("update ticket set beat = ? where id = ?", (b, f["id"]))
        n += 1
    cx.commit()
    return n


def por_atender(pieza):
    """`(fase, ids)` de los abiertos que declaran paso y no han vuelto ya.

    **Una vuelta por ticket, no una por corrida.** Es el mismo tope que el
    repaso: devolver la pieza cada vez que el ticket sigue abierto es un bucle
    que parece trabajo. Aquí se manda una vez, se anota que se mandó, y si el
    ticket vuelve abierto lo que corresponde es pararla y decirlo — no volver a
    mandarla.
    """
    abre = [t for t in abiertos(pieza)
            if (t.get("vuelve_a") or "") and not t.get("devuelto")]
    if not abre:
        return "", []
    fase = abre[0]["vuelve_a"]
    return fase, [t["id"] for t in abre if t["vuelve_a"] == fase]


def encaminar(id_, fase):
    """Dice a qué paso vuelve la pieza por este ticket. Vuelve a poder volver.

    **Por qué se puede cambiar y por qué se borra `devuelto`.** El destino de un
    ticket es ejecución, no mensaje: cuál de los pasos sabe arreglar una
    superposición de capas se decide mirando la máquina, y a veces se decide
    mal. Reencaminarlo le devuelve su turno — si no, corregir el destino sería
    dejar el ticket parado para siempre, que es peor que el destino equivocado.
    """
    cx = _con()
    cx.execute("update ticket set vuelve_a = ?, devuelto = null where id = ?",
               (fase or "", id_))
    cx.commit()


def devolver(ids):
    """Anota que la pieza ya volvió atrás por estos tickets."""
    if not ids:
        return
    cx = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    cx.executemany("update ticket set devuelto = ? where id = ?",
                   [(ahora, i) for i in ids])
    cx.commit()


def reincidentes(pieza):
    """Los que ya hicieron volver la pieza y **siguen abiertos**.

    Son los que paran: el paso que sabía atenderlos ya tuvo su turno con el
    ticket delante y la objeción sigue ahí. Mandarla otra vez no la arregla.
    """
    return [t for t in abiertos(pieza)
            if (t.get("vuelve_a") or "") and t.get("devuelto")]


def historia(pieza):
    """Todo lo que ha dicho de esa pieza, contestado o no."""
    cx = _con()
    filas = [dict(f) for f in cx.execute(
        "select * from ticket where pieza = ? order by id", (pieza,))]
    cx.close()
    return filas


def _texto(t):
    """Una línea legible, con el segundo y la etapa donde cae hoy."""
    donde = ""
    if t.get("segundo") is not None:
        donde = f" s={t['segundo']:.0f}"
        donde += f" (b{t['beat']})" if t.get("beat") is not None else " (sin etapa)"
    marca = {"abierto": "·", "contestado": ">", "arreglado": "+",
             "descartado": "-"}.get(t["estado"], "?")
    # **A quien le toca, en la misma linea.** Un ticket sin paso al que volver
    # no es un ticket menos importante: es uno que nadie va a ejecutar, y eso
    # tiene que verse sin abrir la base.
    if t["estado"] == "abierto":
        donde += (f" -> {t['vuelve_a']}" if t.get("vuelve_a") else " -> SIN PASO")
        if t.get("devuelto"):
            donde += " (ya volvio)"
    linea = f"  {marca} #{t['id']:<3} {t['pieza']}{donde}  {t['dijo']}"
    if t.get("respuesta"):
        linea += f"\n        -> {t['respuesta']}"
    return linea


def main():
    """Para que Jaime abra y cierre tickets sin pasar por nadie.

        python scripts/dominio/ticket.py reel-03 30 "el tablero no suena"
        python scripts/dominio/ticket.py --ver reel-03
        python scripts/dominio/ticket.py --cerrar 4 "movido el borde a 31,2"
    """
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("pieza", nargs="?")
    ap.add_argument("segundo", nargs="?")
    ap.add_argument("dijo", nargs="?")
    ap.add_argument("--tipo", default="objecion")
    # **A que paso vuelve la pieza para atenderlo.** Sin esto, un ticket suyo
    # sobre lo que se ve se quedaba en la base sin nadie que lo ejecutara: el
    # render no conoce la palabra `ticket`. El valor de su tipo esta en `RUTA`;
    # `--paso ""` es decir a proposito que no lo arregla ningun paso.
    ap.add_argument("--paso", default=None, metavar="FASE")
    ap.add_argument("--ver", metavar="PIEZA", nargs="?", const="", default=None)
    ap.add_argument("--cerrar", nargs=2, metavar=("ID", "RESPUESTA"))
    ap.add_argument("--ruta", nargs=2, metavar=("ID", "FASE"))
    ap.add_argument("--estado", default="arreglado")
    a = ap.parse_args()

    if a.ruta:
        encaminar(int(a.ruta[0]), a.ruta[1])
        print(f"ticket #{a.ruta[0]}: lo atiende «{a.ruta[1] or 'nadie'}»")
        return
    if a.cerrar:
        contestar(int(a.cerrar[0]), a.cerrar[1], estado=a.estado, quien="Jaime")
        print(f"ticket #{a.cerrar[0]}: {a.estado}")
        return
    if a.ver is not None:
        filas = historia(a.ver) if a.ver else abiertos()
        if not filas:
            print("sin tickets")
            return
        for t in filas:
            print(_texto(t))
        return
    if not (a.pieza and a.dijo):
        # **El segundo es opcional, el texto no.** Un ticket sin sus palabras no
        # es un ticket: es una marca que nadie sabe atender.
        ap.error("hace falta la pieza y lo que dice; el segundo es opcional")
    seg = float(str(a.segundo).replace(",", ".")) if a.segundo else None
    i = abrir(a.pieza, a.dijo, seg, a.tipo, vuelve_a=a.paso)
    t = [x for x in historia(a.pieza) if x["id"] == i][0]
    print("apuntado:")
    print(_texto(t))


if __name__ == "__main__":
    main()


def cerrar_los_resueltos(pieza: str) -> int:
    """Cierra los tickets cuyo problema **ya no esta en la pieza**.

    **Por que existe.** Jaime, mirando el render: *«tampoco las correcciones ni
    los tickets»*. Y la pieza decia otra cosa: de las cinco cosas que habia
    senalado, cuatro ya no estaban — «eso, eso», la repeticion de «la mayoria de
    los emprendedores», la cola rota de la etapa 3—. Estaban arregladas y sus
    tickets seguian abiertos, asi que **la lista decia que no se habia hecho
    nada**.

    Un ticket que no se cierra solo obliga a alguien a repasar la pieza para
    saber si sigue vigente, y eso es justo lo que la lista tenia que ahorrar.

    Se cierra por lo que se puede medir: **el texto que el ticket cita entre
    comillas ya no esta en la pieza**. Lo que no cita nada se queda abierto —
    «el panel es figurativo», «el hook mas movido» no se comprueban contando, y
    cerrarlos por silencio seria peor que dejarlos.

    **Y «en la pieza» son las dos fuentes, no solo la voz.** Esto comparaba
    contra `Montaje.texto()`, que es lo HABLADO. El copy de los tableros no esta
    ahi —sale de `tarjeta`/`placa`, y lo que el render consumio esta en
    `src/reels.json`—, asi que un ticket como «el tablero dice «MISMA
    FACTURACION» y la voz ya no lo dice» daba todas las citas ausentes y se
    cerraba en la primera vuelta del despachador sin haber mirado el tablero. Se
    mira lo hablado **y** lo rotulado, que es donde puede estar lo que cito.
    """
    import re

    dice = _hablado(pieza) + " " + _rotulado(pieza)
    if not dice.strip():
        return 0
    n = 0
    for t in abiertos(pieza):
        citas = [c.strip() for c in re.findall(r"«([^»]{6,})»", t.get("dijo") or "")]
        # Se exige que TODAS las citas hayan desaparecido: un ticket que cita dos
        # cosas y solo pierde una sigue teniendo razon en la otra.
        if not citas or any(c.lower() in dice for c in citas):
            continue
        contestar(t["id"],
                  "cerrado midiendo: lo que citaba ya no esta en la pieza, ni"
                  " hablado ni rotulado ("
                  + "; ".join(f"«{c[:40]}»" for c in citas[:2]) + ")",
                  estado="arreglado", quien="la linea", medida="texto")
        n += 1
    return n


def _hablado(pieza: str) -> str:
    """Todo lo que se oye en el montaje de hoy, en minusculas."""
    from .montaje import Montaje

    try:
        m = Montaje(pieza)
        return " ".join((m.texto(tr) or "") for tr, _ in m.tramos()).lower()
    except Exception:                              # noqa: BLE001
        return ""


def _rotulado(pieza: str) -> str:
    """Todo lo que se lee en pantalla, **del spec que el render consumio**.

    De `src/reels.json` y no de la base: la base es lo que se pidio, el spec es
    lo que se dibujo. Es la misma distincion que ya hace `servicios/visto.py`.
    """
    try:
        n = int(str(pieza).split("-")[1])
        spec = json.load(open(os.path.join(RAIZ, "src", "reels.json"),
                              encoding="utf-8"))
    except (OSError, ValueError, IndexError):
        return ""
    r = next((x for x in spec if x.get("id") == f"Reel-R{n}"), None)
    if not r:
        return ""
    fuera = []

    def _hojas(x):
        if isinstance(x, str):
            fuera.append(x)
        elif isinstance(x, dict):
            for v in x.values():
                _hojas(v)
        elif isinstance(x, list):
            for v in x:
                _hojas(v)

    for cual in ("boards", "tarjetas", "paneles", "lineas", "cta"):
        _hojas(r.get(cual))
    return " ".join(fuera).lower()
