"""El que monta lo que el paso anterior definió. Segundo eslabón de la cadena.

Regla de Jaime, dicha en cinco mensajes seguidos y son uno solo: *«las escenas y
tableros las debe hacer un agente especializado en diseño; eso es editorial, no
sale con código»*, *«ese agente no tiene contrato, y es trabajo crear ese
contrato en la composición»*, *«un agente se dedica a planear y verificar y otro
agente a diseñar»*, *«son dos tareas diferentes»*, *«uno define lo que va a haber
y el otro lo monta»*, *«una cadena de producción agéntica»*.

## Por qué son dos pasos y no uno con dos sombreros

`descrito` decide **qué etapas componen y qué tiene que quedar dicho** en cada
una — eso se ve mirando el argumento entero, y es planificación. Este paso decide
**cómo se dibuja**: qué componente, con qué copy, con qué familia. Son dos
oficios y juntarlos hace que el segundo se coma al primero: la descripción acaba
siendo la prosa que justifica un tablero ya imaginado.

## Y los dos trabajan en los dos niveles

Corrección de Jaime, y evita el reparto fácil —«el que planea ve la pieza, el que
diseña ve el tablero»—: *«no, ambos son de pieza y de tablero»*.

El que monta necesita la pieza entera porque **la coherencia visual no cabe en un
tablero**: las dos familias se alternan, el oro dice «mira aquí» y deja de
decirlo si está en todo, y tres tableros seguidos con la misma forma son un
tablero repetido tres veces aunque cada uno esté bien.

## Lo que este servicio NO hace

No dibuja, no elige copy y no deduce nada de la prosa del encargo. Hubo una
versión que sacaba la palabra del gancho con una expresión regular sobre
`grafico` y Jaime la paró en el sitio: eso es código decidiendo qué dice el plano
que compite contra el pulgar. Aquí sólo se arma el pedido, se recoge la respuesta
y se guarda donde el render la lee.
"""
import json
import os
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402

# **Tres niveles, no dos.** Este fichero vive en `scripts/servicios/`, así que
# subir dos veces deja `RAIZ` en `scripts/` y no en el proyecto. Con eso, las
# tres rutas que salen de aquí apuntaban a sitios que no existen:
# `scripts/scripts/disenar.prompt.md`, `scripts/src/brand/tokens.ts` y
# `scripts/src/brand/copy.ts`.
#
# **Y ninguna de las tres fallaba.** El prompt se leía con un `if os.path.exists`
# que devuelve cadena vacía, y el canon con un `try/except` que devuelve un
# diccionario con `error` dentro. O sea que el paso del diseñador ha estado
# corriendo **sin su encargo y sin la paleta**, contestando igual, sin que nadie
# lo contara. Es el mismo fallo que C-146 —una ruta con un nivel de más— en el
# sitio donde más caro sale.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT = os.path.join(RAIZ, "scripts", "disenar.prompt.md")
BASE = "ads/decisiones.db"

#: Un `grafico` que pide tipografía en vez de figura. Mismo vocabulario que
#: `caminos.mjs`, y vive en los dos porque son dos lenguajes; si divergen, el
#: contrato lo dice al comprobar la aguja.
TIPO = ("versales", "el tipo es", "la frase entera", "solo texto", "nada mas")


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def _canon():
    """La paleta y las prohibiciones, del repositorio y no de memoria.

    Se leen los tokens de verdad: un canon citado de memoria es un canon que se
    desvía sin que nadie lo note, y aquí el color es lo que dice dónde mirar.
    """
    # **Se leen todos los ficheros de marca, no uno.** Esto miraba sólo
    # `tokens.ts`, y el día que la paleta se mudó a `paleta.ts` empezó a
    # devolver **cero colores en silencio** — un `{}` que el prompt del
    # diseñador recibe como «no hay canon» sin que nada falle. Es el fallo que
    # el propio docstring de arriba dice que no puede pasar, cometido por una
    # ruta escrita a mano.
    #
    # Leer la carpeta entera no es un parche más ancho: es que el canon **es**
    # `src/brand/`, no un fichero concreto de dentro. Que mañana se parta otra
    # vez no vuelve a romper esto.
    import glob
    import re

    t = ""
    for f in sorted(glob.glob(os.path.join(RAIZ, "src", "brand", "*.ts"))):
        try:
            t += open(f, encoding="utf-8").read() + "\n"
        except OSError:
            continue
    if not t:
        return {"error": "no se pudo leer src/brand/"}
    colores = dict(re.findall(r"(\w+):\s*\"(#[0-9a-fA-F]{3,8})\"", t))
    # Y si no sale ni un color, **se dice**: un canon vacío no es un canon.
    if not colores:
        return {"error": "src/brand/ no declara ningun color: el canon no llega"}
    return {
        "colores": colores,
        "tipografia": {
            "titulares y cifras": "Anton, versales",
            "texto sobre video": "Montserrat 700-900",
            "datos y cabeceras": "JetBrains Mono, versales, tracking amplio",
            "prohibida": "cualquier serif: se emborrona con la compresion",
        },
        "prohibido": [
            "sombras, degradados suaves, backdrop-filter, esquinas Material",
            "rebote, confeti, wiggle, Easing.back",
            "ilustracion amable: blobs, dibujitos, iconografia redondeada",
            "fotografia de familia sonriente de stock",
            "el oro decorando: si hay tres cosas en oro, dos sobran",
        ],
        "familias": {
            "cargada": "fotomontaje a sangre, punto de fuga, geometria rota;"
                       " para el golpe y el concepto",
            "tranquila": "negro o navy liso, geometria plana a escuadra;"
                         " para las cifras que hay que leer",
        },
    }


def _topes():
    """Los topes de texto, que **fallan el render** en vez de avisar."""
    ruta = os.path.join(RAIZ, "src", "brand", "copy.ts")
    try:
        t = open(ruta, encoding="utf-8").read()
    except OSError:
        return {"error": "no se pudo leer src/brand/copy.ts"}
    import re

    return {k: int(v) for k, v in re.findall(r"(\w+):\s*(\d{2,3})\b", t)}


def _pide_tablero(fila):
    """¿Esta etapa lleva tablero? Lo dijo el paso que planea, no éste.

    Dos maneras de haberlo dicho, y las dos son declaraciones suyas: nombrar un
    `componente`, o describir un `grafico` tipográfico. La segunda es la que se
    caía — el gancho de reel-04 pide tipo con `componente` en `ninguno`, así que
    ninguna comprobación lo alcanzaba y la etapa salía sin copy.
    """
    if fila["componente"]:
        return True
    g = (fila["grafico"] or "").lower()
    return any(p in g for p in TIPO)


def encargos(slug):
    """Las etapas que llevan tablero y todavía no lo tienen montado."""
    con = _con()
    filas = [dict(r) for r in con.execute(
        "select etapa_orden, que_pasa, emocion, componente, grafico, color,"
        " sonido, plano, tablero from escena_desc where video_slug = ?"
        " order by etapa_orden", (slug,))]
    con.close()
    return [f for f in filas if _pide_tablero(f) and not f["tablero"]]


def arco(slug):
    """El arco narrativo y el emocional, en orden. Los da el compositor.

    Regla de Jaime, y es la que sube el techo de este paso: *«el compositor puede
    darle informacion respecto al arco narrativo y al arco emocional al
    disenador; el disenador puede hacer un gancho visual mucho mas potente, por
    ejemplo»*.

    Sin esto el que monta ve un encargo por tablero y nada mas, asi que disena
    tableros correctos que **no saben donde caen**: el gancho no sabe que tiene
    que abrir, el cierre no sabe que tiene que rematar, y el tablero del medio no
    sabe si esta en la subida o en la caida. Con el arco delante, la forma puede
    acompanar al argumento en vez de ilustrarlo.

    Son dos arcos y no uno:

    - **narrativo** — que funcion cumple cada etapa en el frame, en orden. Es la
      estructura del argumento.
    - **emocional** — que siente el espectador en cada etapa. Jaime lo describio
      como onda: *«arriba, luego abajo, luego arriba»*.
    """
    con = _con()
    filas = [dict(r) for r in con.execute(
        "select e.orden, ec.nombre funcion, e.mensaje_esperado, e.obligatorio,"
        "       d.emocion, d.que_pasa, d.trato"
        "  from etapa e join video v on v.id = e.video_id"
        "  left join etapa_canonica ec"
        "         on ec.estructura_id = e.estructura_id"
        "        and ec.orden = e.etapa_orden"
        "  left join escena_desc d on d.video_slug = v.slug"
        "   and d.etapa_orden = e.orden"
        " where v.slug = ? order by e.orden", (slug,))]
    con.close()
    return {
        # **La intención narrativa de CADA segmento, no la de la pieza.** Jaime:
        # *«el segundo recibe la intención narrativa y el arco emocional de cada
        # segmento; con eso puede potenciarlo con diseño»*. Saber que la etapa 4
        # es la revelación y tiene que decir tal cosa es lo que deja diseñar
        # para eso, en vez de ilustrar la frase que se oye.
        "narrativo": [{"etapa": f["orden"], "funcion": f["funcion"],
                       "tiene_que_decir": f["mensaje_esperado"],
                       "obligatoria": bool(f["obligatorio"])}
                      for f in filas],
        # Y la onda: arriba, abajo, arriba. Con el tratamiento que ya lleva, que
        # es lo que dice si ese punto pide sostener o golpear.
        "emocional": [{"etapa": f["orden"], "emocion": f["emocion"],
                       "trato": f["trato"],
                       "que_pasa": (f["que_pasa"] or "")[:120]}
                      for f in filas],
    }


def resumen_pieza(slug):
    """La pieza entera, resumida. Es el nivel de PIEZA del que monta.

    Sin esto no se puede alternar las dos familias, ni repartir el oro, ni ver
    que tres tableros seguidos tienen la misma forma. Todo eso es invisible
    mirando un tablero solo, que es exactamente por lo que va en el pedido.
    """
    con = _con()
    filas = [dict(r) for r in con.execute(
        "select etapa_orden, que_pasa, emocion, componente, grafico, plano,"
        " tablero from escena_desc where video_slug = ? order by etapa_orden",
        (slug,))]
    con.close()
    out = []
    for f in filas:
        ya = None
        if f["tablero"]:
            try:
                ya = json.loads(f["tablero"]).get("kind")
            except (TypeError, ValueError):
                ya = "?"
        out.append({"etapa": f["etapa_orden"],
                    "que_pasa": (f["que_pasa"] or "")[:160],
                    "emocion": f["emocion"],
                    "plano": f["plano"],
                    "lleva_tablero": bool(_pide_tablero(f)),
                    "ya_montado": ya})
    return out


class ServicioDisenar(Servicio):
    nombre = "disenado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import servicio as contrato

        pendientes = encargos(pieza.slug)
        if not pendientes:
            return Resultado(True, salida="ningun tablero por montar")

        resumen = resumen_pieza(pieza.slug)
        payload = {
            "pieza": pieza.slug,
            # **El arco, que es lo que deja hacer un gancho de verdad.** Sin el,
            # el que monta disena tableros correctos que no saben donde caen.
            "arco": arco(pieza.slug),
            "otras_etapas": resumen,
            "canon": _canon(),
            "topes": _topes(),
            "tableros": [{
                "etapa_orden": f["etapa_orden"],
                # El encargo es lo que escribio quien planea. **No se
                # reinterpreta**: dice que tiene que quedar dicho, y este paso
                # decide como se dibuja.
                "encargo": f["grafico"],
                "que_pasa": f["que_pasa"],
                "emocion": f["emocion"],
                "color": f["color"],
                "sonido": f["sonido"],
                "plano": f["plano"],
                "componente_sugerido": f["componente"],
            } for f in pendientes],
        }
        prompt = (open(PROMPT, encoding="utf-8").read()
                  if os.path.exists(PROMPT) else "")
        r = contrato.pedir("disenar", pieza.slug, prompt, payload)
        if r is None:
            return Resultado(
                False,
                motivo="espera diseno -> "
                       + contrato.ruta_pedido("disenar", pieza.slug))
        return aplicar(pieza, r)


def aplicar(pieza: Pieza, respuesta) -> Resultado:
    """Guarda cada tablero donde el render lo lee, y sólo ahí.

    `escena_desc.tablero` es la fuente única declarada en `verdad.py`. Escribirlo
    en otro sitio —o dejar que el render caiga a un literal— es el fallo que
    costó cuatro entregas idénticas (C-142).
    """
    import datetime

    # El veredicto de pieza puede parar, y es del que monta: tres tableros con
    # la misma forma no es un defecto de ninguno de los tres.
    tableros = respuesta
    veredicto = None
    if isinstance(respuesta, dict):
        tableros = respuesta.get("tableros") or []
        veredicto = (respuesta.get("pieza") or {}).get("veredicto")
    if veredicto == "rota":
        por_que = (respuesta.get("pieza") or {}).get("por_que") or "sin motivo"
        return Resultado(False, motivo=f"el diseno para la pieza: {por_que}")

    con = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    puestos, sin_copy = 0, []
    for t in tableros:
        beat = t.get("etapa_orden")
        if beat is None:
            continue
        kind, props = t.get("kind"), t.get("props")
        if not kind or not isinstance(props, dict) or not props:
            sin_copy.append(beat)
            continue
        if t.get("fuente") and t["fuente"] != "sin cifra":
            props = {**props, "source": t["fuente"]}
        con.execute(
            "update escena_desc set tablero = ?, fecha = ?"
            " where video_slug = ? and etapa_orden = ?",
            (json.dumps({"kind": kind, "props": props}, ensure_ascii=False),
             ahora, pieza.slug, int(beat)))
        puestos += 1
    con.commit()
    con.close()
    if sin_copy:
        return Resultado(
            False,
            motivo=f"etapa(s) {sin_copy} volvieron sin `kind` o sin `props`:"
                   f" un tablero sin copy no se puede montar")
    return Resultado(True, salida=f"{puestos} tablero(s) montado(s)")
