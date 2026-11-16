"""El estado de una pieza, en un fichero que se puede leer y escribir.

Jaime, 7-9-2026, sobre por qué la línea no anda sola: *«el que hace que avance es
el agente en bash, está mal; debe avanzar por etiquetas que activen procesos y
agentes. Se necesita un JSON por vídeo que diga el estado, y que cada agente
pueda modificarlo conforme avanza: un proceso completado, un cambio de estado; un
cambio de estado activa un nuevo proceso. Inteligencia artificial sólo cuando sea
necesario»*.

## Qué cambia respecto de lo que había

El estado ya existía —`video_fase` en la base— y por eso esto **no lo sustituye:
lo publica**. La diferencia no es dónde se guarda, es **quién puede tocarlo**.

Los dos oficios de la línea trabajan con `Read` y `Write` y nada más: no tienen
con qué abrir la base, a propósito. Así que hasta hoy un agente terminaba su
trabajo y **no podía decirlo** — hacía falta alguien en medio que leyera su
respuesta y moviera la pieza. Ese alguien era yo, y por eso la línea no andaba
sin mí.

Un fichero por pieza cierra ese hueco: el que termina escribe que terminó, y el
cambio es lo que enciende el paso siguiente.

## Y no decide nada

Esto no elige la etapa siguiente ni ejecuta nada: **dice dónde está la pieza y
qué la espera**. `dominio/fase.py` sigue siendo el camino y `avanzar.py` sigue
siendo quien recorre. Aquí sólo se escribe lo que ya pasó, y en un sitio donde lo
lea quien no puede abrir la base.

    from dominio import estado
    estado.escribe("reel-03")          # vuelca lo que dice la base
    estado.marca("reel-03", "disenado", "hecho", quien="disenador")
"""
from __future__ import annotations

import datetime
import json
import os

#: La carpeta `mi-video`, sacada de este fichero y no del cwd — tres
#: `dirname`, y se cuentan: `scripts/dominio/estado.py`.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

#: Dónde vive el estado de cada pieza. Junto a su EDL, que es el otro artefacto
#: que la describe: quien mira la carpeta de una pieza ve las dos cosas.
def ruta(slug):
    return os.path.join(RAIZ, "ads", slug, "estado.json")


def _ahora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def lee(slug):
    """Lo que hay escrito, o el esqueleto si todavía no hay nada."""
    r = ruta(slug)
    if os.path.exists(r):
        try:
            return json.load(open(r, encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"pieza": slug, "etapa": None, "desde": None, "espera": None,
            "abiertos": [], "hecho": [], "log": []}


def _guarda(slug, d):
    r = ruta(slug)
    os.makedirs(os.path.dirname(r), exist_ok=True)
    # **El log sólo baja de tamaño por el final.** Es el recorrido de la pieza y
    # es lo que se mira cuando algo salió mal; recortarlo por arriba perdería
    # justo el principio, que es donde empieza la explicación.
    log = d.get("log", [])
    d["log"] = log[:1] + log[-59:] if len(log) > 60 else log
    with open(r, "w", encoding="utf-8", newline="\n") as h:
        json.dump(d, h, ensure_ascii=False, indent=1)
    return d


def escribe(slug):
    """Vuelca a disco lo que la base dice hoy de esa pieza.

    Es el puente de una sola dirección: la base manda, esto la publica. Se llama
    cuando la pieza se mueve, para que el fichero no envejezca — un estado viejo
    es peor que no tenerlo, porque parece verdad.
    """
    from . import fase as _f
    from . import ticket as _t

    d = lee(slug)
    # **Lo que no se pudo publicar se dice, todo** (C-714). Tres `except: pass`
    # dejaban el JSON con cara de entero: el pedido salía y el oficio trabajaba
    # sobre un documento hueco sin saberlo. Si esto no queda vacío, el pedido
    # no sale (`exige_entero`).
    faltas = []
    try:
        con = _f._con()
        r = con.execute(
            "select f.nombre, vf.entro from video_fase vf"
            " join fase f on f.id = vf.fase_id join video v on v.id = vf.video_id"
            " where v.slug = ? order by vf.entro desc, vf.rowid desc limit 1",
            (slug,)).fetchone()
        con.close()
        if r:
            if d.get("etapa") != r["nombre"]:
                d.setdefault("log", []).append(
                    {"cuando": r["entro"], "etapa": r["nombre"], "que": "entra"})
            d["etapa"], d["desde"] = r["nombre"], r["entro"]
    except Exception as e:                         # noqa: BLE001
        faltas.append(f"la fase: {e}")
    try:
        d["abiertos"] = [
            {"id": t["id"], "va_a": t.get("vuelve_a") or "", "beat": t.get("beat"),
             "dice": " ".join((t.get("dijo") or "").split())[:200]}
            for t in _t.abiertos(slug)]
    except Exception as e:                         # noqa: BLE001
        faltas.append(f"los tiquets abiertos: {e}")
    # **Y si llego al final, se cierra en vez de guardarse.** Ver `cierra`.
    try:
        from .fase import CICLO
        if d.get("etapa") and d["etapa"] == CICLO[-1][1]:
            cierra(slug, "llego al final del camino")
            return d
    except Exception:                              # noqa: BLE001
        pass
    # **Y los segmentos, que son la unidad con la que se revisa.** Jaime,
    # 10-9-2026: *«en el Json van los segmentos del video, y van los que estan
    # aprobados y los que no; cada segmento con su propia etiqueta»*. Van aqui
    # y no en un fichero aparte porque este es el documento que el oficio puede
    # abrir: sin ellos dentro, el que trabaja no sabe que puede tocar.
    try:
        from . import segmento as _sg

        # **Y lo que un oficio propuso y aún no entró, se queda** (C-714): esto
        # corre ahora en cada pedido, y publicar no puede pisar una propuesta.
        # Contra el mismo corte; si el corte cambió, la propuesta era de otro.
        antes = {(x.get("etapa"), x.get("huella")): x for x in d.get("segmentos") or []
                 if isinstance(x, dict) and x.get("propone")}
        d["segmentos"] = []
        for x in _sg.Segmento.de(slug):
            j = x.como_json()
            p = antes.get((j["etapa"], j["huella"]))
            if p and p["propone"] != j["etiqueta"]:
                j.update(propone=p["propone"], por=p.get("por") or j["por"])
            if j.get("falta"):
                faltas.append(f"e{j['etapa']}: {j['falta']}")
            d["segmentos"].append(j)
        # **Y si la base decidió escenas y el JSON no publica ninguna, está
        # hueco** aunque nada haya fallado: es lo que pasó con reel-23 hasta
        # C-713, 18 cortes sin un elemento decidido y ningún error.
        n = _sg.decididas(slug)
        if n and d["segmentos"] and not any(k in j for j in d["segmentos"]
                         for k in ("trato", "plano", "tablero", "camara", "voz")):
            faltas.append(f"la base tiene {n} escenas decididas y el JSON no"
                          " publica ninguna")
        d["aprobada"] = _sg.aprobada(slug)
        # **Y las etapas del guion que no tienen toma, dichas** (C-713). Un
        # segmento que no está en el EDL desaparecía del JSON sin rastro:
        # reel-23 e17, «Starting with tax season», se quedó en `sin_toma` por
        # lectura plana y nadie que abriera el marcador podía saber que faltaba.
        # Sin EDL todavía no hay cortes ni etapas sin toma: no es un hueco.
        r = os.path.join(RAIZ, "ads", slug, "edl-sell.json")
        edl = json.load(open(r, encoding="utf-8")) if os.path.exists(r) else {}
        d["sin_toma"] = [{"etapa": h.get("beat"), "motivo": h.get("motivo"),
                          "libreto": h.get("libreto"),
                          "obligatorio": h.get("obligatorio")}
                         for h in edl.get("sin_toma") or []]
    except Exception as e:                         # noqa: BLE001
        # Y lo que no se pudo publicar se dice: un JSON sin segmentos que no
        # avisa es igual que uno vacío, y lo trata igual quien lo lee.
        faltas.append(f"los segmentos: {e}")
    # Se pone y se quita en cada vuelta: un `falta` que se queda de una vuelta
    # vieja pararía la pieza por algo que ya no pasa.
    d.pop("falta", None)
    if faltas:
        d["falta"] = "; ".join(faltas)[:400]
    d["visto_por_ultima_vez"] = _ahora()
    return _guarda(slug, d)


def para_pedido(slug):
    """**El marcador como viaja en un pedido: publicado ahora y entero** (C-714).

    Jaime, 15-11-2026: *«el json tiene toda la información de cada corte y de
    cada elemento sobre el que se ha decidido»*, y *«¿por qué no se usó?»*. Se
    publicaba sólo cuando la pieza cambiaba de fase (`fase.py`), así que con
    reel-23 nueve vueltas en `repasado` el pedido de las 23:32 llevó el JSON de
    las 20:36: dieciocho cortes sin un solo elemento decidido. Ahora cada pedido
    lo publica antes de llevárselo, y lleva también lo que antes se quedaba en
    el fichero: `sin_toma`, `aprobada` y `falta`.
    """
    # Un pedido con sufijo o de prueba no es una pieza del ciclo: se lee, como
    # siempre, sin publicar una carpeta nueva al lado de las piezas.
    import re
    d = escribe(slug) if re.fullmatch(r"reel-\d+", slug or "") else lee(slug)
    m = {"fichero": os.path.relpath(ruta(slug), RAIZ).replace("\\", "/"),
         "publicado": d.get("visto_por_ultima_vez"), "etapa": d.get("etapa"),
         "abiertos": d.get("abiertos") or [], "segmentos": d.get("segmentos") or [],
         "sin_toma": d.get("sin_toma") or [], "aprobada": d.get("aprobada")}
    return {**m, **({"falta": d["falta"]} if d.get("falta") else {})}


def exige_entero(marcador, slug):
    """**Sin el JSON entero, el pedido no sale** (C-714).

    Jaime: *«que me digas que un JSON está vacío es porque no se ha seguido el
    protocolo»*. Un pedido con el marcador hueco no es un pedido incompleto: es
    una pregunta distinta, y el oficio la contesta a ciegas —el diseñador de
    reel-23 escribió «las props completas a ciegas» y redactó una fuente—. El
    paso se para aquí con el motivo, y se reintenta en la vuelta siguiente.

    La regla de qué cuenta como hueco vive en `escribe`; esto y
    `servicio.mjs :: dejaPedido` sólo la obedecen.
    """
    falta = (marcador or {}).get("falta") if marcador else "no se pudo publicar"
    if falta:
        raise RuntimeError(f"el JSON de {slug} no está entero y el pedido no"
                           f" sale: {falta}"[:400])


#: Que permiso hace falta para poner cada etiqueta. Lo que no esta aqui pide
#: «decidir criterio», que es lo que tienen los oficios —los unicos que
#: escriben el marcador—.
#:
#: **Pedia «medir», y eso cerraba la puerta a quien la usa.** «medir» es de los
#: pasos (tabla `agencia`), que etiquetan por `Segmento.mueve` y nunca por aqui;
#: los oficios tienen «decidir criterio». Medido el 10-9-2026: ninguna propuesta
#: de un oficio entraba en la base. Jaime: *«pueden etiquetar»*, todo menos
#: `aprobado`, que sigue siendo suyo.
PIDE = {"aprobado": "aprobar"}
POR_DEFECTO = "decidir criterio"


def _admite(quien, etiqueta):
    """¿Ese autor puede poner esa etiqueta **por el marcador**? Y por que no.

    Dos reglas, y la segunda es la que cierra la puerta de verdad:

    1. El autor tiene que existir y tener el permiso que la etiqueta pide.
    2. **Por el marcador no actua una persona.** El fichero lo escriben los
       oficios, y un fichero no prueba quien lo escribio: si bastara con poner
       `"por": "jaime"`, la firma no valdria nada. Una persona aprueba en su
       terminal —`aprobar.py`—, que es el unico sitio donde su identidad no la
       declara el que escribe.
    """
    from .autor import Autor

    a = Autor.de(quien)
    if a is None:
        return False, f"«{quien}» no es un autor declarado"
    permiso = PIDE.get(etiqueta, POR_DEFECTO)
    if not a.puede(permiso):
        return False, f"{a} no tiene el permiso «{permiso}»"
    if a.tipo == "persona":
        return False, ("una persona no actua por el marcador: el fichero lo"
                       " escribe un oficio y no puede firmar por ella")
    return True, ""


def _rechaza(slug, etapa, etiqueta, quien, por_que):
    """Un rechazo se cuenta. Callarlo seria peor que aceptarlo."""
    d = lee(slug)
    d.setdefault("log", []).append(
        {"cuando": _ahora(), "etapa": d.get("etapa"),
         "que": f"RECHAZADO del marcador: e{etapa} -> «{etiqueta}»"
                f" firmado por «{quien}»: {por_que}"})
    _guarda(slug, d)
    try:
        import registro

        registro.aviso("marcador", "modificacion sin permiso",
                       detalle=f"{slug} e{etapa} «{etiqueta}» por «{quien}»:"
                               f" {por_que}"[:250], eco=False)
    except Exception:                              # noqa: BLE001
        pass


def aplica(slug, quien="el marcador"):
    """Lo que se escribio en el marcador **entra en la base**.

    Jaime, 10-9-2026: *«los contratos y el disparador, todo basado en el Json;
    modifican el Json y este modifica a la base de datos»*. `escribe()` era la
    mitad que iba de la base al fichero; esta es la que faltaba, y sin ella un
    oficio con `Read`/`Write` podia anotar y nadie se enteraba.

    **Solo se leen los campos del que trabaja.** El volcado es dueno de donde
    esta la pieza, de sus tramos y de su huella; el oficio lo es de la etiqueta
    de cada segmento. Si esto leyera todo, una vuelta del volcado pisaria lo que
    el agente acaba de anotar — y al reves, el agente reescribiria el corte.

    Devuelve los segmentos que de verdad se movieron.
    """
    from . import segmento as _sg

    d = lee(slug)
    puestos = {x.n: x for x in _sg.Segmento.de(slug)}
    movidos = []
    for fila in d.get("segmentos") or []:
        # **Se propone en `propone`, no en `etiqueta`.** `etiqueta` es lo
        # que ya paso la puerta y lo publica el volcado; si el que
        # escribe pudiera tocar ese campo, proponer y decidir serian
        # el mismo gesto.
        n, nueva = fila.get("etapa"), (fila.get("propone") or "").strip()
        seg = puestos.get(n)
        if seg is None or not nueva or nueva == seg.etiqueta:
            continue
        # **Contra su corte, no contra cualquiera.** Un marcador de hace dos
        # montajes trae etiquetas de tramos que ya no existen: aplicarlas seria
        # dar por bueno lo que nadie vio.
        if fila.get("huella") and fila["huella"] != seg.huella:
            continue
        # **Y no entra sin permiso.** Jaime, 10-9-2026: *«la guarda es el Json,
        # y lo que verifica y garantiza integridad es que solo se pueda
        # modificar con los permisos»*.
        #
        # Esto aceptaba el autor que el propio fichero declaraba. Un oficio
        # tiene `Write` sobre el marcador, asi que podia escribir
        # `{"etiqueta": "aprobado", "por": "jaime"}` y entraba como una
        # aprobacion suya: **un fichero no puede probar quien lo escribio**. El
        # detector de copias que discrepan habria visto el destrozo despues; lo
        # que impide que ocurra es esto.
        firma = fila.get("por") or quien
        vale, por_que = _admite(firma, nueva)
        if not vale:
            _rechaza(slug, n, nueva, firma, por_que)
            continue
        seg.mueve(nueva, firma)
        movidos.append((n, nueva))
    if movidos:
        d.setdefault("log", []).append(
            {"cuando": _ahora(), "etapa": d.get("etapa"),
             "que": "del marcador a la base: "
                    + ", ".join(f"e{n}->{e}" for n, e in movidos)})
        _guarda(slug, d)
    return movidos


def cierra(slug, por_que="el proceso termino"):
    """Borra el estado de una pieza. **Es memoria de trabajo, no archivo.**

    Jaime, 7-9-2026: *«que se borre cuando se cierre, o cuando se termine el
    proceso»*. Es la misma regla con la que trata el disco: F: es memoria de
    trabajo y al cerrar se vacia; lo que queda es lo final.

    Y no se pierde nada: el recorrido esta en `video_fase`, los tiquets en su
    tabla y las versiones selladas en `version`. Esto era **la vista de lo que
    esta en vuelo**, y una pieza terminada ya no vuela — dejarla ahi convierte
    el tablero en una lista de lo que hubo, que es justo lo que no se mira.
    """
    r = ruta(slug)
    try:
        if os.path.exists(r):
            os.remove(r)
            return True
    except OSError:
        pass
    return False


def espera(slug, quien, que):
    """Deja escrito **a quién espera** la pieza y para qué.

    Es la mitad que faltaba para que un turno pedido se distinga de un atasco.
    El despachador ya lo decía por consola —«espera agente -> disenar/reel-04»—
    y por consola no lo lee nadie dos minutos después.
    """
    d = lee(slug)
    d["espera"] = {"quien": quien, "que": que, "desde": _ahora()}
    d.setdefault("log", []).append(
        {"cuando": _ahora(), "etapa": d.get("etapa"), "que": f"espera a {quien}"})
    return _guarda(slug, d)


def marca(slug, paso, resultado, quien="la linea", nota="", dispara=True):
    """**Un proceso completado, escrito por quien lo completó.**

    Aquí es donde un agente que sólo tiene `Read` y `Write` puede por fin decir
    que terminó. Antes su respuesta se quedaba en un fichero que sólo la línea
    sabía leer, y hacía falta alguien en medio.

    No mueve la pieza: escribir que un paso acabó y decidir cuál viene después
    son dos cosas, y la segunda es de `fase.py`. Lo que esto hace es que la
    primera **deje rastro** — y un rastro es lo que puede disparar la segunda.
    """
    d = lee(slug)
    # **La espera la pone el paso y la quita quien termina.** `turno.py` la
    # escribe con el nombre del buzon y esto solo miraba el del oficio: no
    # casaban nunca, y reel-04 «esperaba» desde el 7-9 a un paso contestado.
    if (d.get("espera") or {}).get("quien") in (quien, paso):
        d["espera"] = None
    fila = {"paso": paso, "resultado": resultado, "quien": quien,
            "cuando": _ahora()}
    if nota:
        fila["nota"] = nota[:400]
    d["hecho"] = [h for h in d.get("hecho", []) if h.get("paso") != paso]
    d["hecho"].append(fila)
    d.setdefault("log", []).append(
        {"cuando": fila["cuando"], "etapa": d.get("etapa"),
         "que": f"{paso}: {resultado} ({quien})"})
    _guarda(slug, d)
    # **Y el cambio enciende el paso siguiente.** Jaime: *«un proceso
    # completado, un cambio de estado; un cambio de estado activa un nuevo
    # proceso»*. Ver `dominio/disparo.py` — un salto, y sin agente en medio:
    # los 18 pasos de codigo del ciclo se encadenan sin encender un modelo.
    if dispara and resultado not in ("fallo", "espera"):
        try:
            from . import disparo
            disparo.dispara(slug, f"{paso} lo dejo en «{resultado}»")
        except Exception:                          # noqa: BLE001
            pass
    return lee(slug)


def todas(piezas):
    """El estado de varias piezas, para mirarlas de una vez."""
    return {s: lee(s) for s in piezas}
