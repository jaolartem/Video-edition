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

# **Este fichero tambien SE EJECUTA, no solo se importa.** `python
# scripts/dominio/ticket.py reel-03 30 "..."` es el camino que CLAUDE.md le da
# a Jaime para abrir un tiquet, y corriendo asi no hay paquete: cada `from .
# import ...` de aqui abajo revienta. Se lo tragaban dos `except` y costo las
# dos mitades del tiquet — el sello del corte (C-344) y **la puerta que manda
# la pieza al paso que lo atiende**, o sea que el tiquet existia y no movia
# nada. Declarar el paquete lo arregla en un sitio y para los tres vecinos.
if not __package__:
    __package__ = "dominio"

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
    # Lo que sobra lo corta el servicio de redundancia (C-643); `cosido` no
    # corta, y con él el tiquet paraba la pieza en `repasado` para siempre.
    "sobra":    ("sin_redundancia", "texto"),
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
#: Lo que era de aquí y hoy es del reloj. Se reexporta porque medio
#: proyecto lo pide como `ticket.SIN_EDL`, y mover una constante no tiene
#: por qué romper a sus lectores.
from .reloj import SIN_EDL, a_montaje, beat_en  # noqa: E402,F401


def _beat(pieza, segundo):
    """El beat si se pudo medir; `None` si no cae y `None` si no se pudo leer."""
    b = beat_en(pieza, segundo)
    return None if b is SIN_EDL else b


#: Las dos escalas en que puede venir un segundo dictado, y cuánto vale cada
#: una en tiempo de montaje —que es la escala del EDL, del plan y de `beat_en`.
#:
#: **La entrega va acelerada y el montaje no.** Medido sobre las siete piezas:
#: el corte declarado y el fichero entregado se llevan un factor de 1,13 a 1,20
#: (reel-04: 79,2 s de corte, 68,5 s entregados). Así que «el segundo 30» no
#: quiere decir lo mismo mirando `out/entrega` que mirando `out/reels`, y la
#: diferencia crece hacia el final de la pieza, que es donde vive el CTA.
#:
#: Jaime, 14-9-2026, al preguntarle qué mira cuando dicta un segundo: *«unas
#: veces una y otras otra»*. Con eso, adivinarlo es apostar: se declara.
ESCALAS = {"entrega": None, "montaje": 1.0}


class SinEscena(Exception):
    """Un tiquet que no dice a que escena va. Ver `abrir`."""


def abrir(pieza, dijo, segundo=None, tipo="objecion",
          vuelve_a=None, cierra_con=None, etapa=None, de="montaje"):
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
    # **Ni uno de `cosido` que no se pueda medir** (C-626). `cosido` no mueve
    # bordes —`costuras.py` deja `bordes` fuera, es criterio— y sólo cierra lo
    # que mide en su segundo (`cierre.cierra_los_suyos`) o por texto. reel-18,
    # 20-10: el visto mandó ahí «el tramo acaba en una «y» que no es suya», sin
    # segundo, y `vencidas` paró la pieza en `repasado` en cada vuelta. Dónde
    # empieza y acaba un tramo lo declara el compositor, como el #536.
    va = por_defecto[0] if vuelve_a is None else vuelve_a
    if va == "cosido" and segundo is None and (cierra_con or por_defecto[1]) != "texto":
        vuelve_a = "descrito"
    # **Y no se abre un tiquet sin decir a que escena va.** Jaime, 7-9-2026:
    # *«cada tiquet va ligado a la escena y el compositor solo ve esa escena»*.
    # Sin escena nadie puede acotar: el #282 salio asi y el pedido pidio las
    # ocho etapas de reel-01 para arreglar una palabra.
    #
    # Se admiten las tres formas de decirlo —el segundo, el numero en el texto,
    # o «la pieza entera» a proposito— y **no se admite el silencio**, que era
    # lo unico que no se distinguia de un descuido. La pieza entera es legitima:
    # «no explica el mecanismo» no es de una escena.
    # **El segundo se trae a la escala del montaje antes de buscar su etapa.**
    # La columna dice «en la pieza montada» y `beat_en` busca en el reloj del
    # plan, que es esa escala; lo que Jaime dicta suele ser de la entrega, que
    # va acelerada. Sin esta linea el tiquet se archivaba en la etapa de al
    # lado y el pedido de diseno abria la lamina equivocada.
    segundo, movido = a_montaje(segundo, de, pieza)
    if movido:
        print(f"  {pieza}: el segundo dictado sobre la {de} cae en el"
              f" {segundo:.1f} del montaje ({movido:+.1f}s)")
    beat = _beat(pieza, segundo)
    if beat is None or beat is SIN_EDL:
        from . import abierto as _ab
        # **Y la etapa que se le pasa, se le pone** (C-593): el visto devolvía
        # escenas y el tiquet quedaba sin etapa si el texto no decía «eN».
        beat = int(etapa) if str(etapa).isdigit() else _ab.etapa_de(dijo)
    if beat is None and str(etapa).lower() not in ("pieza", "0", "todas"):
        raise SinEscena(
            f"{pieza}: un tiquet dice a que escena va. Pasa `segundo=`, nombra"
            f" la etapa en el texto («e7», «etapa 7»), o declara"
            f" `etapa=\"pieza\"` si de verdad es de la pieza entera.")
    cx = _con()
    # **Y lo mismo dicho dos veces es un tiquet, no dos.** Un paso que vuelve a
    # correr vuelve a decir lo que ya dijo: reel-20 y reel-22 llevaban cinco
    # pares identicos (#516/#525…), y cada copia pide su propia atencion y su
    # propio cierre (C-548). Se devuelve el abierto que ya lo dice.
    ya = cx.execute(
        "select id from ticket where estado = 'abierto' and pieza = ?"
        " and dijo = ? and coalesce(segundo, -1) = coalesce(?, -1)",
        (pieza, dijo, segundo)).fetchone()
    if ya:
        cx.close()
        return ya[0]
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    cur = cx.execute(
        "insert into ticket (cuando, pieza, segundo, beat, dijo, tipo,"
        " vuelve_a, cierra_con, huella) values (?,?,?,?,?,?,?,?,?)",
        (ahora, pieza, segundo, beat if beat is not SIN_EDL else None,
         dijo, tipo,
         por_defecto[0] if vuelve_a is None else vuelve_a,
         por_defecto[1] if cierra_con is None else cierra_con,
         _huella(pieza, beat if beat is not SIN_EDL else None)))
    cx.commit()
    ident = cur.lastrowid
    # **Abrir el tiquet ES el evento.** Jaime: *«el tiquet abierto abre una
    # puerta y un camino»*. La puerta vivia en el despachador, o sea en una
    # patrulla que recorria las siete piezas preguntando si habia algo nuevo —
    # y lo nuevo acaba de pasar aqui. Se enciende donde ocurre, no se busca.
    try:
        from . import puertas
        for linea in puertas.del_tiquet([int(str(pieza)[-2:])]):
            print(linea)
    except Exception as e:                         # noqa: BLE001
        print(f"  ticket #{ident}: la puerta no abrio ({e}) — la pieza NO ha"
              f" vuelto al paso que lo atiende")
    return ident


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


def _huella(pieza, etapa=None):
    """La huella del corte sobre el que se abre el ticket. `None` si no se sabe.

    **Con etapa, la de SU etapa: `e<n>:<huella del segmento>`** (C-659). Con la
    de la pieza entera, un borde movido en e3 mataba los tiquets de e5: W40
    descartó así 176 de 476, casi todos de etapas que nadie había tocado. Un
    tiquet habla de su etapa, y caduca cuando su etapa cambia.

    **Y se busca por los dos caminos, porque el que la usa es el CLI.** Este
    fichero se importa como `dominio.ticket` desde la linea y se EJECUTA como
    `python scripts/dominio/ticket.py`, que es el camino que CLAUDE.md le da a
    Jaime para abrir un tiquet. Corriendo como script no hay paquete, `from .
    import version` revienta, el `except` lo daba por «no se sabe» y el tiquet
    nacia sin sello — para morir en el `caducar` siguiente.

    Medido el 9-9-2026: 268 de los 288 tiquets no tienen huella, y **los 41 que
    se han descartado alguna vez con «Caducado con el corte» son los 41 sin
    sello**. Ni uno se descarto por venir de un montaje distinto: se
    descartaron por no poder decir de cual venian.
    """
    try:
        from . import segmento, version
        return segmento.sello(pieza, etapa) if etapa is not None else version.huella_edl(pieza)
    except Exception:                              # noqa: BLE001
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
    # **Sin sello no es viejo: es que no se supo decir de que corte venia.** La
    # regla mata al que demuestra ser de otro montaje, y un `NULL` no demuestra
    # nada. Contarlo como prueba fue lo que se llevo los 41 —todos los que se
    # han caducado en la vida del proyecto— y entre ellos los que Jaime abrio
    # desde el CLI, que es justo el camino que CLAUDE.md le ofrece.
    # Y el de una etapa se compara con su etapa, no con la pieza (C-659).
    viejos = [dict(r) for r in cx.execute(
        "select id, dijo, huella from ticket where pieza = ? and respuesta is null"
        " and huella is not null and huella <> ?", (pieza, h))]
    from .segmento import sigue
    viejos = [v for v in viejos if not sigue(pieza, v["huella"])]
    if viejos:
        ahora = datetime.datetime.now().isoformat(timespec="seconds")
        cx.executemany(
            # `descartado` y no `caducado`: el esquema declara los cuatro
            # estados posibles y anadir uno pide migrar la tabla. Lo que
            # distingue a estos lo dice su respuesta, que es donde se lee.
            "update ticket set respuesta = ?, estado = 'descartado', quien ="
            " 'la linea', cerrado = ? where id = ?",
            [(f"Caducado con el corte: su etapa ya no es la que habia (hoy {h})."
              " Regla de Jaime: «los anteriores se mueren cuando la composicion"
              " se muere». Si el defecto sigue, vuelve a salir.", ahora, v["id"])
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
    q = ("select id, pieza, cuando, vuelve_a, cerrado, quien from ticket"
         " where estado <> 'abierto' and vuelve_a in (?, ?)")
    args = list(RECIBO)
    if pieza:
        q += " and pieza = ?"
        args.append(pieza)
    filas = cx.execute(q + " order by id", args).fetchall()
    cx.close()
    from .autor import Autor  # lo que cierra una persona no pide recibo (C-415)
    return [dict(f) for f in filas
            if not recibo(f["pieza"], f["vuelve_a"], f["cuando"])
            and getattr(Autor.de(f["quien"] or ""), "tipo", None) != "persona"]


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
    # **Sin segundo no hay nada que recolocar** (C-593): su etapa la dijo quien
    # lo abrió, y `beat_en(…, None)` la borraba en cada pedido (#671, #695, #698).
    for f in cx.execute("select id, segundo from ticket where pieza = ?"
                        " and estado = 'abierto' and segundo is not null",
                        (pieza,)).fetchall():
        b = beat_en(pieza, f["segundo"])
        if b is SIN_EDL:
            continue
        cx.execute("update ticket set beat = ? where id = ?", (b, f["id"]))
        n += 1
    cx.commit()
    return n


def encaminar(id_, fase, avisar=True):
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
    if not avisar:      # lo recoge `puertas.del_tiquet` en la vuelta (C-691)
        return
    from dominio import puertas  # reencaminar también es el evento (C-411)
    puertas.del_tiquet_de(id_)


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
    # **De cuál de las dos piezas es el segundo.** No hay valor por defecto a
    # propósito: la entrega va acelerada y el montaje no —medido en las siete,
    # factor 1,13 a 1,20— así que «el segundo 30» son dos sitios distintos y la
    # diferencia crece hacia el final. Jaime, al preguntárselo: *«unas veces una
    # y otras otra»*. Lo que no se puede adivinar se declara, igual que la
    # escena.
    ap.add_argument("--de", choices=("entrega", "montaje"), default=None,
                    help="de qué vídeo es el segundo: la entrega (out/entrega,"
                         " acelerada) o el montaje (out/reels)")
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
    if a.segundo is not None and a.de is None:
        ap.error("di de qué vídeo es el segundo: `--de entrega` (lo que se"
                 " publica, acelerado) o `--de montaje` (out/reels). Se llevan"
                 " un 15%, y a los 60 s son 9 segundos de diferencia.")
    seg = float(str(a.segundo).replace(",", ".")) if a.segundo else None
    i = abrir(a.pieza, a.dijo, seg, a.tipo, vuelve_a=a.paso, de=a.de or "montaje")
    t = [x for x in historia(a.pieza) if x["id"] == i][0]
    print("apuntado:")
    print(_texto(t))
    # **Lo que dice el reabre su segmento, no la pieza** (C-605). La puerta no
    # reabre lo aprobado y su tiquet se quedaba en «sube a Jaime».
    if t.get("beat") is not None:
        from .segmento import reabre
        reabre(a.pieza, t["beat"])


if __name__ == "__main__":
    main()
