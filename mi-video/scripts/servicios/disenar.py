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
from dominio import dibujable as _dib  # noqa: E402  C-562

from contrato.marca import ENTRADA_GANCHO, ESTILO, PRIORIDAD  # noqa: E402,F401

from dominio import abierto as _abierto, quitada as _quitada  # noqa: E402
import fotogramas as _fotogramas  # noqa: E402
from dominio import remate as _remate  # noqa: E402
from dominio.mudo import sin_copy as _sin_copy  # noqa: E402
from dominio.arco import arco  # noqa: E402
from dominio.encargo import (guardar_tablero as _guardar,  # noqa: E402
                             tablero_desfasado as _desfasado)

from .base import Pieza, Resultado, Servicio  # noqa: E402
from escucha import bordes_medidos as _oye_los_cortes  # noqa: E402
from .marca import (_canon, _canon_escrito, _laminas, _sonidos,  # noqa: E402
                    _topes)
from .caja import (COMO_COMBINAR, CORRECCION, VERSE, catalogo_de_piezas,  # noqa: E402
                   placas_que_existen, tres_dimensiones,
                   figuras_que_se_trazan, volumenes_que_se_animan,
                   mando_de_camara,
                   que_leer_para_componer, voz_en_el_remate, ya_en_pantalla)

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

#: Lo de presentación que el diseñador declara a veces junto a `kind` y que el
#: render lee de `props` (C-418).
# `anclas`, `ventana` y `sujeto_desde` también: el diseñador de reel-15 puso
# `anclas` junto a `cubre` y el tablero entró con reloj fijo (C-458).
PRESENTACION = ("sujeto", "sujeto_forma", "sujeto_color", "cubre", "familia",
                "placa", "recorte", "anclas", "ventana", "sujeto_desde")


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c




#: El oficio del reel comercial, y el filtro de marca que lo acota.
#:
#: Jaime: *«el contrato del disenador tiene que conocer los efectos y las
#: practicas mas comunes en reels comerciales, pero los efectos deben ser
#: coherentes con la marca»*. Sin la primera mitad se compone como un carrusel
#: quieto; sin la segunda se acaba en la plantilla que hace todo el mundo.
OFICIO_REEL = {
    "lo_que_funciona": [
        "El primer segundo decide: algo se mueve antes del frame 12.",
        "Tipografia cinetica: el texto ENTRA, no aparece. Y entra con ritmo, palabra a palabra o bloque a bloque, siguiendo la voz.",
        "Capas sobre el plano: el rotulo puede nacer detras de la cara y acomodarse delante. Da profundidad y es lo que separa un reel de un video.",
        "Punch-in: el encuadre se acerca en el remate. Corta el aburrimiento sin cortar la frase.",
        "Pattern interrupt cada 3-5 s: algo cambia —encuadre, color, capa— antes de que el pulgar decida.",
        "El subtitulo es capa portante y elemento de diseno, no un pie: se compone, se mueve y pesa en el cuadro.",
        "El sonido marca el movimiento: cada entrada fuerte tiene su acento.",
        "Freeze o corte seco para sostener una cifra: se para el mundo un instante y se lee.",
    ],
    "lo_que_NO_es_esta_marca": [
        "Figuras redondeadas en pastel, iconografia amable, blobs.",
        "El minimalismo simplon que todo el mundo hace para lucir caro: mucho aire, una linea fina y una palabra en el centro.",
        "Plantillas de moda ajenas al proyecto: si se reconoce la plantilla antes que el mensaje, esta mal.",
        "Adorno sin funcion: rebote, confeti, wiggle, particulas.",
    ],
    "el_filtro": "Todo lo de la primera lista vale SI pasa por el canon neoconstructivista de las 26 laminas. La tecnica es de reel; la forma es de esta marca. Jaime: «no es una figura redondeada color pastel… ni un estilo minimalista simplon o el que todo el mundo hace para lucir caro».",
}

#: El paso que faltaba: entender antes de dibujar.
ANTES_DE_DIBUJAR = {
    "1_que_quiere_decir": "Escribe en una linea que entiende el espectador DESPUES de esta etapa y no antes. Esa es la funcion del tablero.",
    "2_no_lo_ilustres_literal": "Si el hablante usa un simil —«el contador es como un medico que firma una incapacidad»— la figura NO dibuja al medico. Dibuja lo que el simil viene a explicar: que se actua tarde y sobre el sintoma.",
    "3_ejemplo_de_jaime": "Sobre un panel de palitos y bolitas: «pueden ser signos de dolares, o una grafica bajando, o algo que represente tributacion subiendo, o filas de monedas que crecen: algo que realmente tenga que ver con lo que se dice FIGURATIVAMENTE. Se trata de entender la intencion narrativa, no de repetir literalmente lo que se dice.»",
    "4_complemento_no_eco": "El tablero complementa lo que se oye. Si repite la frase con otras letras, sobra.",
}




def _pide_tablero(fila):
    """¿Esta etapa lleva tablero? Lo dijo el paso que planea, no éste.

    Dos maneras de haberlo dicho, y las dos son declaraciones suyas: nombrar un
    `componente`, o describir un `grafico` tipográfico. La segunda es la que se
    caía — el gancho de reel-04 pide tipo con `componente` en `ninguno`, así que
    ninguna comprobación lo alcanzaba y la etapa salía sin copy.
    """
    if fila["componente"]:
        return True
    # **Y una etapa que YA tiene tablero montado lleva tablero.** Parece una
    # perogrullada y era el agujero: reel-05 e2 tenía uno declarado —mudo, ver
    # `_sin_copy`— y su `grafico` describe fichas, así que ni nombraba
    # `componente` ni sonaba a tipografía. Con las dos preguntas de abajo daba
    # **False**, o sea «esta etapa no lleva tablero», con un tablero puesto.
    #
    # Consecuencia: no entraba nunca al encargo, ni para revisarlo ni para
    # corregirlo, y los 13,6 s de la etapa 2 se quedaron con tres paralelogramos
    # de 40 px durante cinco ciclos. El filtro de `encargos()` sigue decidiendo
    # si hay algo que pedir; esto sólo deja de mentir sobre si hay tablero.
    if fila.get("tablero"):
        return True
    # **Y el gancho siempre lleva, lo diga o no.**
    #
    # Es la etapa 1 y es la unica que no puede quedarse sin composicion: los
    # rotulos que salian en pantalla venian de un literal de `reels-spec.mjs`
    # —o sea de codigo, no del disenador— y su figura la deducia una expresion
    # regular de la prosa. Nadie lo habia disenado nunca, y por eso las seis
    # piezas fallan la misma comprobacion: *«el gancho lleva 2 entradas y
    # necesita 3»*.
    #
    # Jaime, sobre el primer render: *«el hook tiene que ser mucho mas movido»*.
    # Eso no se arregla con un umbral: se arregla componiendolo.
    if int(fila["etapa_orden"]) == 1:
        return True
    g = (fila["grafico"] or "").lower()
    return any(p in g for p in TIPO)


def encargos(slug):
    """Las etapas que llevan tablero y todavía no lo tienen **o están mal**.

    La segunda mitad faltaba, y es por donde se perdían las correcciones
    gráficas de Jaime. Este paso sólo preguntaba por lo que **no existía**: una
    etapa con su tablero puesto ya no entraba en el encargo, aunque él hubiera
    dicho que ese tablero está mal.

    Medido el 5 de septiembre: cuatro piezas devueltas a `disenado` con tiquets
    suyos abiertos —el tiempo de lectura de reel-01, el abuso del glitch de
    reel-05, el tramo leído de reel-07— y **ningún pedido escrito**, porque los
    tableros ya estaban montados. La pieza atravesaba el paso sin preguntar
    nada y salía igual. Es su queja exacta: *«siempre estoy repitiendo las
    mismas correcciones porque nunca llegan las indicaciones»*.

    Un tiquet suyo sobre una etapa la vuelve a poner en el encargo. No la
    rehace: la abre para que el que compone la mire con su corrección delante.

    **Y un tablero mudo también la abre.** Ver `_sin_copy`: una etapa con la
    columna `tablero` puesta y sin una línea de copy dentro no dibuja nada, y
    para este paso era indistinguible de una etapa resuelta.
    """
    con = _con()
    filas = [dict(r) for r in con.execute(
        "select etapa_orden, que_pasa, emocion, componente, grafico, color,"
        " sonido, plano, tablero, tablero_propuesto from escena_desc"
        " where video_slug = ?"
        " order by etapa_orden", (slug,))]
    con.close()
    # **Y un tiquet abre su etapa aunque no lleve tablero.** El #297 de reel-07
    # pedía corregir el precio en e7, que no tiene tablero, y la pieza cruzaba
    # este paso sin pedido: lo que se atiende puede ser `corrige`, `voz` o
    # `camara`, que `aplicar` ya sabe escribir sin `kind`.
    # Un segmento aprobado contra su corte no vuelve al diseñador, salvo tiquet.
    from dominio.segmento import Segmento

    aprobados = {s.n for s in Segmento.de(slug) if s.aprobado}
    # **Y lo que se mandó quitar no se encarga** (C-628): reel-21, 20-10, la
    # etapa 5 —el aviso, fuera por decisión de Jaime— seguía pidiendo tablero y
    # `verificar` le abría un tiquet que paraba la final.
    return [f for f in filas if int(f["etapa_orden"]) not in _quitada.todas(slug)
            if (int(f["etapa_orden"]) not in aprobados and _pide_tablero(f)
                and (not f["tablero"] or _sin_copy(f) or _desfasado(f)))
            or _abierto.abre(slug, "disenado", f)]


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
            # **Y si habia un pedido abierto, se retira.**
            #
            # La puerta cuenta los pedidos sin contestar por el fichero que hay
            # en disco, no por si queda trabajo. Cuando `describir` trae ya el
            # tablero, este paso se queda sin nada que componer y el pedido de la
            # vuelta anterior se quedaba ahi: la puerta paraba el render pidiendo
            # una respuesta que nadie necesitaba y que nadie iba a escribir.
            #
            # Un paso que deja de necesitar su pregunta tiene que retirarla. Si
            # no, la pregunta pasa a ser un bloqueo sin dueno — que es la forma
            # que tiene un pedido de convertirse en deuda.
            _retira_pedido(pieza.slug)
            return Resultado(True, salida="ningun tablero por montar")

        resumen = resumen_pieza(pieza.slug)
        # **Lo que ya se ve en cada etapa.** Jaime: *«ya las escenas estan
        # escogidas, asi que... pues que agregue lo B que falta»*. Sin esto el
        # pedido describe cada etapa como si la pieza estuviera en blanco, y no
        # lo esta: lo que se pide es el material B sobre una linea A cerrada.
        hay = ya_en_pantalla(pieza.slug)
        # La ultima prueba se hace MIRANDO: el dossier dice lo que se pidio y
        # el frame lo que salio. El porque vive en `fotogramas.py`.
        mirar, _ = _fotogramas.sacar(pieza.n)
        from dominio.documento import Documento as _Documento
        # **Si la pieza muestra su cara en todo tablero** (T-06): el prop
        # `cara: "siempre"` del marco. Sin esto el diseñador compondría a pleno
        # sin él y la línea se lo pararía después, cuando ya no puede corregir.
        payload = {
            "pieza": pieza.slug,
            # Y las formas que a pleno le dejan la columna (C-562): con su cara
            # en todo tablero, una forma de fuera va en `cubre: panel` o `banda`.
            **_dib.de_la_pieza(pieza),
            "documento": _Documento(pieza.slug, mirar, None, "disenar").escribe(),  # C-594
            # **Y como suena cada corte.** Jaime, 7-9-2026: *«ambos que vean y
            # oigan; con eso el compositor sabe si estoy leyendo en una toma»*.
            # Vale para los dos oficios y por el mismo motivo: leer se ve en la
            # mirada baja Y se oye en la entrega plana, y con media senal cada
            # uno decide con la mitad. El que dibuja tambien lo necesita —una
            # etapa leida lleva tablero obligatorio, porque su cara no sale a
            # camara limpia mientras lee.
            #
            # Va medido, no en wav: el oficio lee texto e imagenes. Ver
            # `escucha.py :: envolvente`.
            "oye_los_cortes": _oye_los_cortes(pieza.slug),
            # **El arco, que es lo que deja hacer un gancho de verdad.** Sin el,
            # el que monta disena tableros correctos que no saben donde caen.
            "arco": arco(pieza.slug),
            "otras_etapas": resumen,
            "canon": _canon(),
            # El documento entero, no solo los tokens: las reglas de
            # composicion viven ahi y no viajaban.
            "canon_escrito": _canon_escrito(),
            "laminas": _laminas(),
            "placas": placas_que_existen(pieza.slug),
            "estilo": ESTILO,
            "antes_de_dibujar": ANTES_DE_DIBUJAR,
            "sonidos": _sonidos(),
            "oficio_reel": OFICIO_REEL,
            "prioridad": PRIORIDAD,
            "piezas": catalogo_de_piezas(),
            "como_combinar": COMO_COMBINAR,
            "figuras": figuras_que_se_trazan(),
            # **Y las animaciones de panel que existen.** Sin la lista, el que
            # compone no puede elegir: es lo mismo que paso con las diez figuras
            # y con las catorce placas. La regla del 5-9 estaba escrita y los
            # tres paneles de reel-01 salieron siendo tres rotulos quietos.
            "volumenes": volumenes_que_se_animan(),
            "correccion": CORRECCION,
            "verse": VERSE,
            "tres_d": tres_dimensiones(),
            "camara": mando_de_camara(),
            # **Y cómo suena él en el remate**, que es la otra mitad de mandar
            # sobre el material. Jaime: *«que cambie mi voz en los punchlines»*.
            # Va en el pedido porque una herramienta que no está en el pedido no
            # existe para quien compone: es lo que pasó con los cinco encuadres
            # y con las catorce placas.
            "voz": voz_en_el_remate(),
            "composicion": que_leer_para_componer(),
            "topes": _topes(),
            "tableros": [{
                "etapa_orden": f["etapa_orden"],
                # Lo que escribio quien planea: dice que tiene que quedar
                # dicho. **Es una propuesta, no un encargo cerrado.** Jaime:
                # *«el disenador puede respetar el tablero o no»*. Si cumplirlo
                # al pie carga al espectador, se cambia — y se dice por que.
                # Antes decia aqui que no se reinterpretaba, y eso es lo que
                # producia ilustraciones literales del simil. Este paso
                # decide como se dibuja.
                "encargo": f["grafico"],
                "que_pasa": f["que_pasa"],
                "emocion": f["emocion"],
                "color": f["color"],
                "sonido": f["sonido"],
                "plano": f["plano"],
                "componente_sugerido": f["componente"],
                # **Lo que propuso quien describio, y es propuesta.** Sin esto
                # el que compone empieza de cero y pierde lo que ya se penso;
                # con esto, y sabiendo que puede cambiarlo entero, compone.
                "propuesta": _propuesta(f["tablero_propuesto"]),
                # **Donde cae la etapa en la pista.** Jaime: *«sobre todo que el
                # tablero que quede sincronice con lo que la pista da»*. Un
                # tablero se compone contra un tiempo real —cuando se dice y
                # cuanto dura—, no contra una idea de cuanto deberia durar.
                "en_la_pista": _en_la_pista(pieza.slug).get(f["etapa_orden"]),
                # Lo que el gancho exige y las demas no. Va en la etapa, no en
                # una nota aparte, para que quien compone no tenga que acordarse.
                "ya_en_pantalla": hay.get(int(f["etapa_orden"]),
                                          ["NADA: cara y subtitulo, nada mas"]),
                **({"es_el_gancho": ENTRADA_GANCHO}
                   if int(f["etapa_orden"]) == 1 else {}),
            } for f in pendientes],
        }
        prompt = (open(PROMPT, encoding="utf-8").read()
                  if os.path.exists(PROMPT) else "")
        # **El contrato tiene dos capas y esta es la segunda.** Las
        # capacidades no cambian —son lo que sabe hacer—; lo que cambia es el
        # encargo. El porque, con sus palabras, vive en `dominio/abierto.py`.
        # **El taller es igual para todas las piezas: va por referencia**
        # (C-564). Eran 100 KB en cada pedido, leidos una vez por pieza; ahora
        # se escriben una vez en `_comun/` y el lote los lee una vez por ronda.
        payload["taller"] = _dib.taller(payload)
        prompt, payload = _abierto.modo(prompt, payload, pieza.slug, "disenado")
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
    # **Y sin haber MIRADO no se aprueba.** Jaime: *«el tablero no se puede leer
    # bien y el fondo blanco no se entiende; parece que el disenador no reviso
    # esto antes de salir. La revision es parte del proceso normal y debe ser
    # antes de cada aprobacion»*.
    #
    # Los fotogramas ya viajaban en su pedido, y mirarlos era voluntario: la
    # respuesta se aceptaba igual sin haberlos abierto. Un requisito que se pide
    # en la prosa y no se comprueba en la puerta es una sugerencia.
    #
    # No se comprueba que mire —eso no se puede—: se le exige **decir que vio en
    # cada escena**. Escribirlo obliga a haberlo mirado, y ademas deja el dato
    # donde se puede releer cuando algo salga mal.
    visto = (respuesta.get("mirado") if isinstance(respuesta, dict) else None)
    if not visto:
        return Resultado(
            False,
            motivo="la respuesta no trae «mirado»: hay que revisar los"
                   " fotogramas de cada escena ANTES de aprobar y decir que se"
                   " vio — letras que no se leen, colores que no se ven,"
                   " composicion rota. Es parte del proceso, no un extra.")
    # **Lo que no se puede dibujar vuelve ahora, no al montar** (C-562). Es la
    # misma regla que `rompe` (`formas.revisarTablero` + `sinSujeto`); dicha
    # tres pasos tarde costo 18 vueltas a reel-19 y reel-21 el 18-10.
    vuelta = _dib.puerta(pieza, tableros)
    if vuelta:
        return vuelta
    if veredicto == "rota":
        # **Y la escena vuelve a quien la decide** (C-387). Jaime, 11-9-2026:
        # *«lo que el compositor decide es la escena; si la escena no cuadra y el
        # diseñador lo nota, la devuelve»*. Esto paraba la pieza con el motivo y
        # nadie se lo decía al compositor: se quedaba atascada en `disenado`.
        from .base import devuelve

        por_que = (respuesta.get("pieza") or {}).get("por_que") or "sin motivo"
        return devuelve(pieza, "diseño · la escena no cuadra:", por_que)
    # Su cara en un tablero es el hablando: `servicios/pegatina.py` (C-490).
    from . import pegatina as _peg
    quietos = _peg.quietas(tableros)
    if quietos:
        return Resultado(False, motivo=_peg.motivo(quietos))

    # La portada es de la pieza y no de una etapa: `servicios/portada.py`.
    from .portada import guardar as _portada
    _portada(pieza.slug, respuesta)
    con = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    puestos, encuadrados, corregidos = 0, 0, 0
    retirados, componentes, sin_copy = 0, 0, []
    tratadas, destratadas, voz_mal = 0, 0, []
    for t in tableros:
        beat = t.get("etapa_orden")
        if beat is None:
            continue
        # **La camara va primero y va sola.** Una etapa puede pedir encuadre y
        # transicion sin llevar tablero —de hecho la mayoria son asi: cara y
        # subtitulo—, asi que guardarla dentro del `if` del tablero la habria
        # dejado inalcanzable justo para las etapas donde mas manda.
        if isinstance(t.get("camara"), dict) and t["camara"]:
            con.execute(
                "update escena_desc set camara = ?, fecha = ?"
                " where video_slug = ? and etapa_orden = ?",
                (json.dumps(t["camara"], ensure_ascii=False), ahora,
                 pieza.slug, int(beat)))
            encuadrados += 1
        # **Y la correccion de lo dicho, que tampoco tenia por donde pedirse.**
        #
        # `corrige_dice` / `corrige_es` existian en `escena_desc`, los dibuja
        # `Corregida` y los declaraba el contrato del COMPOSITOR — no el de
        # quien compone el grafico, que es justo el que tiene delante la cifra
        # de la voz y la cifra respaldada.
        #
        # Jaime, al ver el caso: *«si se puede corregir en pantalla si queda
        # explicito el error»*, *«pero explicito no es»* —de una nota al pie— y
        # la forma exacta: *«no decir "aca hay un error", sino que el error se
        # enfatice en el numero bueno, o el nombre bueno»*. Que es literalmente
        # lo que hace `Corregida`: la palabra mala se SUSTITUYE por la buena, y
        # la buena crece, se pone en oro y late.
        # **`componente` tambien se aplica.** El contrato lo declara como clave
        # del disenador —`Clave("componente")` en `contrato/diseno.py`, con su
        # aguja en `caminos.mjs`— y `aplicar()` no lo escribia: sale de
        # `escena_desc.componente`, no del tablero, asi que quien lo declaraba
        # veia su decision desaparecer sin aviso. Es la misma forma de siempre:
        # una clave con contrato, con lector, y sin nadie que la guarde.
        # **Y el lado del subtítulo, por la misma puerta** (C-633): una
        # columna, un valor suyo.
        cc = t["cc"] if isinstance(t.get("cc"), dict) else {}
        for col, v in (("componente", t.get("componente")), ("cc_lado", cc.get("lado"))):
            if isinstance(v, str) and v.strip() and (col != "cc_lado" or v in ("der", "izq")):
                con.execute(f"update escena_desc set {col} = ?, fecha = ?"
                            " where video_slug = ? and etapa_orden = ?",
                            (v.strip(), ahora, pieza.slug, int(beat)))
                componentes += col == "componente"
        # **Y cómo suena él en el remate de esa etapa.** Jaime: *«que cambie mi
        # voz en los punchlines»*.
        #
        # Se guarda con `"voz" in t` y no con `t.get("voz")` porque las dos
        # respuestas son distintas y las dos son suyas: no decir nada es dejarlo
        # como está, y decir `null` es **retirarlo**. Sin esa diferencia el
        # tratamiento se podría poner y no quitar, que es la mitad de una
        # herramienta y la mitad que convierte una decisión en permanente.
        #
        # Y se valida ANTES de escribir: un trato que no existe guardado en la
        # base sale como falta en cada corrida del paso de audio para siempre.
        # Lo mismo que hace `figuras_que_se_trazan` por el lado visual.
        if "voz" in t:
            v, mal = t["voz"], ""
            if isinstance(v, dict) and v:
                r = _remate.Remate.de_declaracion(beat, v)
                mal = r.falta() if r else "no dice `trato`"
            if mal:
                voz_mal.append(f"e{beat}: {mal}")
            else:
                con.execute(
                    "update escena_desc set voz = ?, fecha = ?"
                    " where video_slug = ? and etapa_orden = ?",
                    (json.dumps(v, ensure_ascii=False) if v else None,
                     ahora, pieza.slug, int(beat)))
                if v:
                    tratadas += 1
                else:
                    destratadas += 1
        # Una o varias: una lista va a las mismas columnas (C-465).
        from dominio.escena import columnas_de_corrige
        c_dice, c_es, c_marca = columnas_de_corrige(t.get("corrige"))
        if c_dice:
            con.execute(
                "update escena_desc set corrige_dice = ?, corrige_es = ?, corrige_marca = ?,"
                " fecha = ? where video_slug = ? and etapa_orden = ?",
                (c_dice, c_es, c_marca, ahora, pieza.slug, int(beat)))
            corregidos += 1
        # **Y un tablero se puede RETIRAR, no solo escribir.**
        #
        # `aplicar` solo sabia poner. Un disenador que decide que una etapa esta
        # mejor sin tablero —reel-06 e7: 5,13 s de negro rotulando «21 DE
        # SEPTIEMBRE» mientras el subtitulo decia lo mismo tres renglones arriba,
        # con la fecha ya derivada en la tarjeta once segundos despues— no tenia
        # forma de decirlo: escribia su decision en `por_que` y el tablero seguia
        # saliendo. Es declarar sin poder aplicar, otra vez.
        #
        # `retirar: true` lo borra de `escena_desc`, que es su unica fuente.
        if t.get("retirar"):
            con.execute(
                "update escena_desc set tablero = null, fecha = ?"
                " where video_slug = ? and etapa_orden = ?",
                (ahora, pieza.slug, int(beat)))
            retirados += 1
            continue
        kind, props = t.get("kind"), t.get("props")
        if not kind and not props and (t.get("camara") or c_dice or comp
                                       or "voz" in t):
            continue          # etapa que solo pide camara: es una entrega valida
        if not kind or not isinstance(props, dict) or not props:
            sin_copy.append(beat)
            continue
        # **`fuente` ES la linea del pie, y por eso entra como `pie`.**
        #
        # Entraba como `props.source` y cada componente decidia si la dibujaba y
        # como: cinco pies distintos en la misma pieza, y en cinco tableros del
        # lote un parrafo de tres y cuatro renglones dentro de la lamina. Desde
        # la instruccion de Jaime del 6-9-2026 el pie va **fuera de la zona
        # segura y en UNA linea**, la dibuja `PieTablero` y el destino es uno.
        #
        # `source` se sigue escribiendo porque es lo declarado y hay filas
        # antiguas que solo lo tienen; `scripts/reels/cifras.mjs` lee los dos.
        if t.get("fuente") and t["fuente"] != "sin cifra":
            props = {**props, "source": t["fuente"], "pie": t["fuente"]}
        # **Y lo de presentación entra en `props` venga donde venga.** reel-08
        # e3 trajo `sujeto` junto a `kind`, no dentro de `props`: se perdió su
        # cara y el render se paró por T-06 (12-9, C-418).
        props = {**{k: t[k] for k in PRESENTACION if k in t}, **props}
        # **Y se guarda CONTRA QUÉ encargo se compuso.** La huella va dentro de
        # la misma escritura —`guardar_tablero`— porque separarlas es cómo se
        # olvida: un tablero sin huella es un tablero que nadie puede saber si
        # está desfasado. Ver `dominio/encargo.py`.
        _guardar(con, pieza.slug, int(beat), kind, props, ahora)
        puestos += 1
    con.commit()
    con.close()
    if sin_copy:
        return Resultado(
            False,
            motivo=f"etapa(s) {sin_copy} volvieron sin `kind` o sin `props`:"
                   f" un tablero sin copy no se puede montar")
    hecho = f"{puestos} tablero(s) montado(s)"
    if encuadrados:
        hecho += f" · {encuadrados} etapa(s) con camara declarada"
    if corregidos:
        hecho += f" · {corregidos} correccion(es) de lo dicho"
    if retirados:
        hecho += f" · {retirados} tablero(s) retirado(s)"
    if componentes:
        hecho += f" · {componentes} componente(s)"
    if tratadas:
        hecho += f" · {tratadas} remate(s) con tratamiento de voz"
    if destratadas:
        hecho += f" · {destratadas} remate(s) devuelto(s) a la voz de siempre"
    if voz_mal:
        hecho += " · voz NO declarada en " + "; ".join(voz_mal)
    _archiva_respuesta(pieza.slug)
    # **El que arregla el tiquet lo cierra.** Componia y dejaba la nota abierta,
    # asi que la linea volvia a pararse por una correccion ya hecha — y la unica
    # forma de sacarla de ahi era cerrarla a mano contra la base, que es
    # exactamente como se pierde el estado. El porque del cierre es la respuesta
    # que acaba de aplicarse, no una opinion.
    # **Y sólo los que la respuesta dice haber atendido.** Ver `abierto.cerrar`:
    # cerrarlos todos hizo desaparecer el tiquet del gancho de reel-07 dentro de
    # una respuesta que sólo tocaba dos paneles.
    cerrados = _abierto.cerrar(
        pieza.slug, "disenado", f"lo compuso: {hecho}",
        (respuesta.get("tiquets") if isinstance(respuesta, dict) else None))
    return Resultado(True, salida=hecho + (f" · tiquets {cerrados} cerrados"
                                           if cerrados else ""))


def _archiva_respuesta(slug: str) -> None:
    """Retira la respuesta ya consumida: existir tiene que significar pendiente.

    `verificar.py` para la linea cuando encuentra `<slug>.respuesta.json`, y con
    razon —*«una composicion escrita y sin aplicar es otro diseno compitiendo»*—,
    pero nadie la retiraba al aplicarla, asi que el aviso salta **para siempre**
    despues de un exito. Hoy paro el montaje de reel-02, reel-04 y reel-07 con
    los tres disenos ya dentro de la base, comprobado etapa por etapa.

    Es la averia del proyecto por el otro lado: alli el dato no llegaba, aqui la
    senal no se apaga. Acaban igual — una comprobacion que grita donde no hay
    problema se deja de mirar, y entonces no comprueba nada.
    """
    import shutil

    import servicio as contrato

    r = contrato.ruta_respuesta("disenar", slug)
    if not os.path.exists(r):
        return
    d = os.path.join(os.path.dirname(r), "usadas")
    os.makedirs(d, exist_ok=True)
    try:
        shutil.move(r, os.path.join(d, f"{slug}.aplicada.respuesta.json"))
    except OSError:
        pass


def _retira_pedido(slug: str) -> None:
    """Archiva el pedido de diseno que ya no tiene trabajo detras."""
    import shutil

    import servicio as contrato

    p = contrato.ruta_pedido("disenar", slug)
    if not os.path.exists(p):
        return
    d = os.path.join(os.path.dirname(p), "usadas")
    os.makedirs(d, exist_ok=True)
    try:
        shutil.move(p, os.path.join(
            d, f"{slug}.sin-trabajo-detras.pedido.json"))
    except OSError:
        pass


def _propuesta(crudo):
    """Lo que dejo quien describio, ya como objeto. `None` si no dejo nada."""
    if not crudo:
        return None
    try:
        return json.loads(crudo)
    except (TypeError, ValueError):
        return None


def _en_la_pista(slug: str) -> dict:
    """Cuando suena cada etapa en la pieza montada: `{beat: [desde, hasta]}`.

    Son segundos de la PIEZA, no de la cinta — que es lo que la pista de audio
    sigue y lo que el espectador oye. Un tablero que se compone contra los
    segundos de la cinta se coloca donde nadie lo esta mirando.

    **Y se lo pregunta a `remate.ventanas`, que ya contestaba esto.** Aqui habia
    una segunda respuesta a la misma pregunta, sumando `tr.dura` sobre los tramos
    del EDL — y el EDL no es el reloj de la pieza: `plan-reel` le quita el aire a
    cada corte antes de repartirlo en escenas, y `reels/reloj.mjs` lo tiene
    medido, **6,83 s en reel-01 y creciendo hacia el final**. O sea que el
    diseñador componia contra un reloj que se iba, y justo en el cierre.

    `src/reels.json` es lo que el render dibujo, asi que sus segundos son los que
    el espectador oye. Dos listas describiendo la misma pieza es el aprendizaje
    33: manda la que se renderiza.
    """
    return {b: [a, z] for b, (a, z) in _remate.ventanas(slug).items()}

