"""El contrato con los servicios de IA. Nadie decide fuera de la línea.

Regla de Jaime, y es de arquitectura, no de detalle:

> *«Y tú, aunque seas el que ejecuta, te vas a mover dentro del pipeline
> reemplazando a la IA que se conecta por tokens o por bash. Vamos a simular un
> programa: nunca puedes tomar decisiones por fuera de la línea. Y vamos a hacer
> una arquitectura modular, articulada por servicios, pero un pipeline en toda
> regla.»*

## Por qué existe esto

Hasta ahora los pasos de IA se resolvían de dos maneras según el día: si el CLI
tenía credencial, corrían solos; si no, **yo leía el dossier y editaba la base o
el EDL a mano**. Eso no es un pipeline con un paso manual: es un pipeline con un
agujero, y por ese agujero se coló todo lo que salió mal hoy — cortes aplicados
sin quedar registrados, descripciones que dejaron de corresponder, decisiones
tomadas fuera de la línea que ningún paso posterior podía ver.

Con esto, un paso de IA es **una función con firma**: entra un fichero, sale un
fichero, y el paso siguiente lee la salida. Da igual quién la escriba —el CLI,
una API, o yo respondiendo como el servicio— porque **el contrato es el mismo**.
Lo que ya no se puede hacer es saltarse el fichero.

## El contrato

    work/servicio/<paso>/<slug>.pedido.json     lo que el paso pregunta
    work/servicio/<paso>/<slug>.respuesta.json  lo que el servicio contesta

`pedir()` escribe el pedido e intenta el CLI. Si el CLI no está, **deja el
pedido puesto y devuelve `None`**: el paso lo dice y la línea sigue o para,
pero nadie improvisa. Cuando la respuesta aparece —la escriba quien la escriba—
`recoger()` la valida contra el esquema del paso y la entrega.

## Lo que esto impide, a propósito

- Que yo toque `escena_desc` o el EDL directamente: sólo escribo respuestas.
- Que una decisión exista sin quedar registrada: el fichero **es** el registro.
- Que un paso posterior no sepa de dónde salió un dato: sale del contrato.

    python scripts/servicio.py            # que pedidos hay sin contestar
"""
import argparse
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

RAIZ = "work/servicio"


# Entre el piso y el contrato del paso, para que se lean como dos bloques.
SEPARA = chr(10) * 2 + "---" + chr(10) * 2

PISO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "docs", "piso.md")
_piso_cache = None


def _piso():
    """El minimo que toda pieza tiene que cumplir, para todos los pasos.

    Se lee del fichero y no se copia: un criterio que vive en cinco sitios es
    cinco criterios en cuanto alguien toca uno.
    """
    global _piso_cache
    if _piso_cache is None:
        try:
            _piso_cache = io.open(PISO, encoding="utf-8").read().strip()
        except OSError:
            _piso_cache = ""
    return _piso_cache


#: Los campos del pedido que hoy NO se pudieron construir, con por qué.
#: Se vacía al empezar cada `contexto()` y viaja dentro del pedido.
_HUECOS: dict = {}


def _falta(nombre, e, vacio):
    """Apunta el hueco y devuelve el vacío. La regla vive en `docs/piso.md`.

    **Un productor que disfraza su fallo de dato legítimo.** `onda`, `se_ve` y
    `cierres_en_corpus` mandaban `[]` cuando la consulta reventaba; `precio`
    mandaba `None` tanto si no hay escalón como si la llamada falla. Quien
    contesta no puede distinguir «no hay» de «no se pudo mirar», y las dos
    llevan a decisiones opuestas: con lo primero se sigue, con lo segundo hay
    que parar.

    No son seis arreglos: es un mecanismo, y vive aquí porque `pedir()` es la
    única puerta por la que pasa todo pedido — igual que `docs/piso.md` se
    antepone aquí para que el criterio siga siendo uno.
    """
    _HUECOS[nombre] = f"{type(e).__name__}: {e}"[:160]
    return vacio


def _marcador(slug):
    """Donde esta la pieza y en que fichero lo escribe quien la mueve.

    Lo publica `dominio/estado.py`; aqui solo se lleva al pedido **con su
    ruta**, porque un oficio que solo tiene `Read` y `Write` necesita saber que
    fichero abrir. La ruta es relativa a `mi-video`, que es el `cwd` con el que
    se le llama (ver `dominio/oficio.py :: CASA`).

    `etapa` y `abiertos` los reescribe la base en cada vuelta. **Lo del que
    trabaja son los `segmentos`**: ahi propone la etiqueta de cada uno
    (`propone` + `por`), y `estado.aplica` la lleva a la base.

    Llevaba `hecho` y no `segmentos`, y los dos contratos trabajan sobre
    `marcador.segmentos`: el oficio anotaba `hecho` a mano —con horas
    inventadas— creyendo cerrar su turno, y el turno lo cierra la respuesta.
    Medido el 10-9-2026 en reel-01, 03, 04 y 05.
    """
    try:
        from dominio import estado

        d = estado.lee(slug)
        return {"fichero": os.path.relpath(estado.ruta(slug),
                                           estado.RAIZ).replace("\\", "/"),
                "etapa": d.get("etapa"), "abiertos": d.get("abiertos") or [],
                "segmentos": d.get("segmentos") or []}
    except Exception as e:                        # noqa: BLE001
        return _falta("marcador", e, None)


def _dir(paso):
    d = os.path.join(RAIZ, paso)
    os.makedirs(d, exist_ok=True)
    return d


def _hoy():
    """La fecha de hoy, para poder juzgar si una fecha ya paso."""
    import datetime

    return datetime.date.today().isoformat()


def _tickets(slug):
    """Las objeciones abiertas de esa pieza, recolocadas en su etapa de hoy."""
    try:
        from dominio import ticket

        ticket.recolocar(slug)
        return _lo_dicho(ticket.abiertos(slug))  # sin la fila de la base: C-585
    except Exception as e:                        # noqa: BLE001
        return _falta("tiquets", e, [])


def _decididos(slug):
    """Lo ya decidido de esa pieza —sus tiquets cerrados, con lo que se hizo— y,
    si deriva, lo de su origen puesto en sus etapas.

    Jaime, 11-9-2026: *«que viajen las decisiones cerradas»*. Sólo viajaban los
    abiertos, así que el #282 —*«el semanales se mantiene»*— dejó de existir
    para quien revisaba en cuanto se cerró, y la revisión mandó cortarlo.
    """
    try:
        from dominio import ticket
        from dominio.libreto import origen_de

        def de(s, mapa=None):
            return [{"id": t["id"], "segundo": t["segundo"],
                     "etapa": t["beat"] if mapa is None else mapa.get(t["beat"]),
                     "dijo": (t["dijo"] or "")[:400],
                     "se_hizo": (t["respuesta"] or "")[:200]}
                    for t in ticket.historia(s)
                    if t["estado"] in ("arreglado", "contestado")
                    and (mapa is None or t["beat"] is None or t["beat"] in mapa)]

        origen, mapa = origen_de(slug)
        return _sin_repetir(de(slug) + (de(origen, mapa) if origen else []))  # C-585
    except Exception as e:                        # noqa: BLE001
        return _falta("lo_ya_decidido", e, [])


def _precio():
    """El escalon abierto hoy, ya redactado. Ver `consulta.precio_vigente`."""
    try:
        import consulta

        return consulta.precio_vigente()
    except Exception as e:                        # noqa: BLE001
        return _falta("precio_vigente", e, None)


#: Para no repetir el aviso en cada pedido de la misma corrida.
_dicho = False


def _instrucciones(paso, slug):
    """Lo que Jaime dijo y sigue aplicando a este paso y esta pieza."""
    global _dicho
    try:
        from dominio import instruccion

        # **Y una etiqueta que no apunta a ningun paso se dice, no se arregla
        # sola.** 22 instrucciones llevan `paso` con nombres que no son los de
        # ningun paso de servicio —`montaje`, `corte`, `audio`, `revalidado`—,
        # asi que el filtro por paso no se puede encender sin dejarlas sin
        # destinatario. Juntar los dos vocabularios es una decision; que el
        # desajuste no se vea, no.
        if not _dicho:
            _dicho = True
            h = instruccion.etiquetas_huerfanas()
            if h:
                import registro

                registro.aviso(
                    "instruccion", "etiqueta de paso que no existe",
                    detalle=", ".join(f"{k}: {v}" for k, v in sorted(h.items())))
        return instruccion.para(paso, slug)
    except Exception as e:                        # noqa: BLE001
        return _falta("instrucciones_de_jaime", e, [])


def _respaldos(slug):
    """Las cifras de la pieza con su fuente, su vigencia y sus condiciones.

    Sale de `dato` —86 filas— con su `fuente`. Sin esto, quien contesta ve una
    cifra en pantalla y no tiene contra que comprobarla, asi que la unica salida
    honesta que le queda es subirla a Jaime. Con esto, sube **la que de verdad
    no tiene respaldo**, que es una lista mucho mas corta y mucho mas util.

    `condiciones` dice ademas cuando una cifra es un supuesto de la pieza y no
    un dato medido, que es justo la distincion que hoy nadie podia hacer.
    """
    import sqlite3
    import basedatos

    ruta = os.path.join(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))), "ads", "decisiones.db")
    if not slug or not os.path.exists(ruta):
        return []
    try:
        cx = basedatos.abrir(ruta)
        cx.row_factory = sqlite3.Row
        filas = cx.execute(
            "select d.etapa_orden etapa, d.cifra, d.afirmacion, d.condiciones,"
            "       d.respalda, d.nota, f.rotulo, f.organismo, f.url,"
            "       f.vigencia, f.cita"
            "  from dato d join video v on v.id = d.video_id"
            "  left join fuente f on f.id = d.fuente_id"
            " where v.slug = ? order by d.etapa_orden", (slug,)).fetchall()
        cx.close()
    except sqlite3.Error:
        return []
    if not filas:
        # **Una derivada respalda con las cifras de su origen**, puestas en sus
        # etapas y sin las que quitó. reel-08 llegaba con cero y reel-01 con
        # ocho: el compositor vio «30 mil» sin fuente. C-396.
        from dominio.libreto import origen_de

        origen, mapa = origen_de(slug)
        if not origen:  # una historia respalda con las de su serie (C-419)
            serie = json.load(open("ads/frames.json", encoding="utf-8"))[
                "reels"].get(slug, {}).get("respalda_de")
            return [dict(f, etapa=None) for f in (_respaldos(serie) if serie else [])]
        return [dict(f, etapa=mapa.get(f.get("etapa")))
                for f in (_respaldos(origen) if origen else [])
                if f.get("etapa") is None or f.get("etapa") in mapa]
    return [{k: r[k] for k in r.keys() if r[k] is not None} for r in filas]


def ruta_pedido(paso, slug):
    return os.path.join(_dir(paso), f"{slug}.pedido.json")


def ruta_respuesta(paso, slug):
    return os.path.join(_dir(paso), f"{slug}.respuesta.json")


def contexto(paso, slug):
    """Lo que viaja con TODO pedido, lo arme Python o JavaScript.

    Una sola lista: `servicio.mjs` la pide aqui en vez de armar la suya, que
    es como el pedido de `describir` se quedo sin lo ya decidido, sin el
    precio y sin las instrucciones (C-395).

    **Y lo que no se pudo construir viaja dicho, en `huecos`.** Un `[]` que
    significa «no hay» y un `[]` que significa «revento la consulta» son
    decisiones opuestas para quien contesta, y hasta ahora llegaban con la
    misma cara. Ver `_falta` y `docs/piso.md`.
    """
    _HUECOS.clear()
    d = {"hoy": _hoy(), "datos_respaldados": _respaldos(slug),
             # **Lo que Jaime ya dijo, para que no tenga que decirlo otra vez.**
             # Guardarlo y no llevarlo al paso que debe obedecerlo es
             # archivarlo. Ver `dominio/instruccion.py`.
             "instrucciones_de_jaime": _instruccion.por_ambito(
                 _instrucciones(paso, slug)),
             # **El precio vigente, en TODOS los pasos.** Llegaba solo a
             # `repaso`, y los que no lo tenian dedujeron la ventana de las
             # fechas de `datos_respaldados` — y se quedaron con la fila del
             # Early Bird, que vence el 28 de agosto. **Tres agentes distintos
             # cometieron el mismo error**, asi que no eran ellos: era el dato.
             #
             # El precio es cumplimiento y no puede depender de que paso lo
             # mire.
             "precio_vigente": _precio(),
             # **Lo que Jaime ha dicho de ESTA pieza, colocado en su etapa.**
             # Una objecion suya —«en el segundo 30 el tablero se queda sin
             # sonido»— no se puede atender si el paso no sabe que etapa cae en
             # el segundo 30. Ver `dominio/ticket.py`.
             "lo_que_dijo_jaime_de_la_pieza": _tickets(slug),
             # **Y lo que ya se decidió, que no se rediscute.** Ver
             # `_decididos`: cerrado, el #282 dejaba de viajar.
             "lo_ya_decidido_de_la_pieza": _decididos(slug),
             # **El marcador que viaja con la pieza.** Jaime, 9-9-2026: *«los
             # agentes deben poder leer y escribir en el Json, es lo que permite
             # ver la etiqueta, y es lo que articula todo lo de la base de
             # datos; el json debe ser el documento que se mueve por la cinta y
             # mantiene el marcador»*.
             #
             # `dominio/estado.py` lo publica desde la base desde el 7-9 —con su
             # frase: *«se necesita un JSON por video que diga el estado, y que
             # cada agente pueda modificarlo conforme avanza»*— y **no llegaba
             # al que trabaja**: `estado.marca` no la llamaba nadie y `hecho`
             # estaba vacio en las siete piezas. Declarado y no implementado.
             "marcador": _marcador(slug)}
    return {**d, **({"huecos": dict(_HUECOS)} if _HUECOS else {})}


from dominio import instruccion as _instruccion, pliego as _pliego  # noqa: E402  C-564
from dominio.volcado import _lo_dicho, _referencia, _sin_repetir, _volcar  # noqa: E402


def _prompt_aparte(paso, slug, prompt):
    """`<slug>.prompt.md` junto al pedido: el mismo prompt, legible por renglones."""
    try:
        os.makedirs(_dir(paso), exist_ok=True)
        with open(os.path.join(_dir(paso), f"{slug}.prompt.md"), "w",
                  encoding="utf-8") as f:
            f.write(prompt)
    except OSError:
        pass


def pedir(paso, slug, prompt, payload, cli=True):
    """Deja el pedido y, si se puede, lo resuelve con el CLI.

    Devuelve la respuesta ya validada, o `None` si el servicio no contestó. En
    ese caso **el pedido queda escrito**: quien pueda contestarlo lo encuentra
    ahí, y el paso no inventa nada mientras tanto.
    """
    p = ruta_pedido(paso, slug)
    # **El pedido solo se reescribe si la pregunta cambio.** Parece un detalle
    # de eficiencia y no lo es: es lo que hace que la fecha del fichero
    # signifique algo. Reescribiendolo en cada corrida, el pedido era siempre
    # mas nuevo que cualquier respuesta y no habia forma de saber si la
    # respuesta contestaba a ESTA pregunta o a la de hace dos vueltas.
    # **El piso va delante de todo prompt, y por un solo sitio.**
    #
    # Jaime: *«redundancia y fuentes debe estar en todos los contratos»*. La
    # forma equivocada de hacer eso es copiar la prosa en los cinco ficheros:
    # se desincronizan, y entonces cinco pasos juzgan lo mismo con criterios
    # distintos — que es justo lo que el dijo que no puede ser estable.
    #
    # `docs/piso.md` es el minimo que no se puede evitar, con sus palabras, y se
    # antepone aqui. Cambiarlo cambia los cinco contratos a la vez, que es lo
    # unico que mantiene un criterio siendo uno.
    # **Y del contrato del paso, sólo los apartados que su momento lee**
    # (C-583, `dominio/pliego.py`). El piso va entero, como siempre.
    prompt = (_piso() + SEPARA if _piso() else "") + _pliego.para(paso, prompt)
    # **Lo que exigen los CUATRO contratos va por un solo sitio**, igual que el
    # piso. `contratos.py` lo lleva diciendo desde que existe: `hoy`, `evento` y
    # `datos_respaldados` figuran como exigidos en los cuatro y **no se enviaban
    # en ninguno**.
    #
    # Se paga en cada respuesta. Hoy los siete agentes tuvieron que deducir la
    # fecha para juzgar si un evento habia caducado, y **los cinco que miraron
    # cifras subieron «sin fuente»** — el 550 $ de reel-01, el 53,53 % de
    # reel-03, el 33 % de reel-07, las dos del ministerio de comercio en
    # reel-02. La tabla `dato` tiene 86 filas con su fuente, su vigencia y sus
    # condiciones, y hasta dice cuando una cifra es un supuesto y no un dato
    # medido. Nadie la estaba mirando porque no llegaba.
    #
    # Va al primer nivel del pedido y no dentro de `datos` a proposito: `datos`
    # es una lista en unos pasos y un diccionario en otros, y lo que vale para
    # todos no puede depender de esa forma.
    comun = contexto(paso, slug)
    # **Y el prompt, además, en su propio fichero con sus renglones.** Dentro
    # del JSON es una sola línea de 46.000 caracteres y quien contesta la leía
    # cortada a mitad del formato de respuesta (reel-08, reel-17, 12-9, C-445).
    _prompt_aparte(paso, slug, prompt)
    nuevo = _volcar({"paso": paso, "slug": slug,
                     "prompt": _referencia(slug, prompt),
                     **comun, "datos": payload})
    # **Y hay campos que cambian sin que cambie la pregunta.** `vuelta` cuenta
    # cuantas veces ha pasado la pieza por aqui, asi que sube cada vez que se
    # archiva un par — y con eso el pedido nunca era identico a si mismo, su
    # fecha se movia sola, y la guarda de C-122 rechazaba **todas** las
    # respuestas por «anteriores al pedido». Una pieza que convergia se quedaba
    # rebotando: contestaba bien tres veces y las tres se archivaban por
    # desfasadas.
    #
    # Se comparan las dos preguntas sin esos campos. Siguen viajando —quien
    # contesta necesita saber en que vuelta esta—, pero dejan de contar como
    # pregunta distinta.
    # **Y con ellos el precio y las instrucciones, por la misma razon y con una
    # diferencia que hay que decir.** Los tres son **contexto que acompana**, no
    # el material que se juzga: el corte, el texto y las candidatas son la
    # pregunta. Si cambia el contexto, la respuesta sobre los bordes sigue
    # valiendo.
    #
    # Lo que se pierde al no contarlos: una instruccion nueva de Jaime no tumba
    # las respuestas en vuelo. Se recoge en la ronda siguiente, que es cuando el
    # paso vuelve a preguntar. La alternativa era tirar siete respuestas ya
    # escritas cada vez que el dice algo, y eso convierte su criterio en un
    # castigo — que es lo contrario de lo que la tabla viene a hacer.
    # `hoy` viaja porque sin el no se puede juzgar si una fecha ya paso, pero
    # no cuenta como pregunta distinta: si contara, toda respuesta escrita
    # anoche seria «anterior a su pedido» esta manana, y volveria a preguntarse
    # lo mismo. Es el mismo caso que `vuelta`.
    # Y `marcador` con ellos, por lo mismo y de forma mas evidente: lleva la
    # etiqueta de la pieza, que **cambia justo porque el paso avanzo**. Si
    # contara como pregunta, cada pedido seria nuevo por haber contestado el
    # anterior — el bucle de C-122 con otra puerta.
    VOLATILES = ("vuelta", "hoy", "precio_vigente", "instrucciones_de_jaime",
                 "lo_ya_decidido_de_la_pieza",
                 "lo_que_dijo_jaime_de_la_pieza", "marcador")

    # **Y lo que es contexto tampoco cambia la pregunta.**
    #
    # Jaime: *«el analisis de cada video es caro, revisa que reprocesos hay y
    # los eliminamos»*. Medido el 1 de septiembre: **20 respuestas terminadas y
    # tiradas** por desfasadas —5 de repaso, 8 de redundancia, 7 de revalidar—,
    # cada una un analisis completo de una pieza.
    #
    # Y no se tiraban porque la pregunta cambiara: se tiraban porque cambiaba
    # **algo** del pedido. Las piezas comparten cintas, asi que cualquier paso
    # determinista de otra pieza reescribia la onda o el corpus de esta, y una
    # respuesta correcta sobre los cortes se iba a la basura porque el material
    # de apoyo se habia movido.
    #
    # Un dato que se manda **para poder contestar** no es la pregunta. Si cambia
    # la curva pero el corte es el mismo, la respuesta sobre ese corte sigue
    # siendo verdad. Cada paso declara aqui lo suyo; el que no declara nada
    # sigue comparandose entero, que es lo conservador.
    CONTEXTO = {
        # **El diseno contesta sobre los ENCARGOS.** Lo demas viaja para que
        # pueda componer: donde cae la etapa en la pista, lo que propuso quien
        # describio, el canon y los topes. Contarlo como parte de la pregunta
        # costo **cinco composiciones enteras**: se anadio `en_la_pista` y el
        # gancho al pedido despues de que los agentes contestaran, y las cinco
        # respuestas se archivaron como «desfasadas» — pagadas y tiradas.
        #
        # Un dato que se manda para poder contestar no es la pregunta. Es la
        # misma leccion que C-163 y la tercera vez que la cobro este mes.
        "disenar": ("arco", "otras_etapas", "canon", "topes",
                    # El encargo de estilo, las laminas, el catalogo de sonidos
                    # y el paso de entender antes de dibujar: todo eso viaja
                    # PARA PODER componer, no es lo que se juzga. Si contara
                    # como pregunta, cada retoque del brief tiraria las
                    # respuestas en vuelo — que es la leccion de C-163 y la que
                    # ya costo cinco composiciones enteras.
                    "laminas", "estilo", "antes_de_dibujar", "sonidos",
                    # **Y el resto del taller, por la misma razon y por cuarta
                    # vez.** Lo de arriba se declaro cuando la lista era otra;
                    # desde entonces al pedido le han entrado `verse`, `tres_d`,
                    # `camara`, `composicion`, `piezas`, `figuras`, `placas` y
                    # las tres constantes de oficio — todo material **con el que
                    # se compone**, ninguno la pregunta.
                    #
                    # El coste medido hoy: al arreglar un `NameError` que tumbaba
                    # el paso, `verse` y `tres_d` entraron al pedido por primera
                    # vez, la pregunta "cambio", y las dos composiciones que ya
                    # estaban escritas se archivaron por desfasadas. Jaime, sobre
                    # justo esto: *«otro reproceso, no me gusta nada»*.
                    #
                    # La pregunta del diseno es `tableros` —los encargos— y
                    # `pieza`. Nada mas. Cualquier cosa que se anada al taller
                    # tiene que caer aqui, o tirara el trabajo en vuelo.
                    "verse", "tres_d", "camara", "composicion", "piezas",
                    "figuras", "placas", "correccion", "como_combinar",
                    "oficio_reel", "prioridad"),
        # El repaso contesta sobre los cortes y el sonido, o sea sobre
        # `montaje`. Lo demas va para que pueda juzgarlo, no es lo juzgado.
        "repaso": ("onda", "se_ve", "etapas_sin_voz", "material_en_corpus",
                   "libreto", "evento", "estructura", "cierres_en_corpus"),
    }
    # **Y donde se sabe cual es la pregunta, se dice la pregunta — no el resto.**
    #
    # `CONTEXTO` lista lo que NO se juzga, y esa forma tiene un fallo que ya se
    # ha cobrado tres composiciones enteras: **cada herramienta nueva que se le
    # da al disenador entra al pedido como clave nueva**, no esta en la lista, y
    # cuenta como pregunta distinta. Paso hoy tres veces seguidas — al meter
    # `en_la_pista` y el gancho, al arreglar un `NameError` que metio `verse` y
    # `tres_d`, y al anadir `voz`. Las tres veces la respuesta ya estaba escrita
    # y se archivo por «anterior al pedido».
    #
    # Enumerar lo que hay que ignorar obliga a acordarse en el futuro. Enumerar
    # **lo que se pregunta** no: lo que se anada despues es contexto por
    # definicion, que es lo que de verdad es. Para el diseno la pregunta son los
    # encargos y la pieza; lo demas viaja para poder componer.
    PREGUNTA = {"disenar": ("tableros", "pieza")}
    # **Y cuando `datos` es una lista, lo que acompana a cada fila** (C-557).
    # `historial` de revalidar es la maquina midiendo otra vez el tramo: cambia
    # de una vuelta a otra sin que cambie el corte —o falla un temporal y trae
    # un error—, y con eso el pedido se reescribia mientras el agente
    # contestaba y su respuesta salia «anterior al pedido». reel-20 y reel-22,
    # 18-10: dos revisiones de 210 K tokens tiradas en doce minutos.
    POR_FILA = {"revalidar": ("historial",)}.get(paso, ())
    SOLO = PREGUNTA.get(paso)
    APOYO = CONTEXTO.get(paso, ())

    def _pregunta(txt):
        try:
            d = json.loads(txt)
        except (TypeError, json.JSONDecodeError):
            return None
        if isinstance(d.get("datos"), dict):
            def _cuenta(k):
                if SOLO is not None:
                    return k in SOLO
                return k not in VOLATILES and k not in APOYO

            d["datos"] = {k: v for k, v in d["datos"].items() if _cuenta(k)}
        elif isinstance(d.get("datos"), list) and POR_FILA:
            d["datos"] = [{k: v for k, v in f.items() if k not in POR_FILA}
                          if isinstance(f, dict) else f for f in d["datos"]]
        for k in VOLATILES:
            d.pop(k, None)
        # El contrato se compara por su huella: un pedido escrito antes de
        # C-550 lo traia entero y no por eso es otra pregunta.
        if "prompt" in d and not str(d["prompt"]).startswith("en "):
            d["prompt"] = _referencia(d.get("slug"), d["prompt"])
        return json.dumps(d, ensure_ascii=False, sort_keys=True)

    try:
        igual = _pregunta(io.open(p, encoding="utf-8").read()) == _pregunta(nuevo)
    except OSError:
        igual = False
    if igual and io.open(p, encoding="utf-8").read() != nuevo:
        # **Y el contexto se refresca aunque la pregunta sea la misma.** Sin
        # esto lo nuevo que viaja —lo ya decidido, un precio, una instruccion—
        # no llegaba nunca a un pedido ya escrito. Se reescribe y se le
        # devuelve su fecha, que significa cuando cambio la pregunta. C-395.
        t = os.path.getmtime(p)
        io.open(p, "w", encoding="utf-8").write(nuevo)
        os.utime(p, (t, t))
    if not igual:
        io.open(p, "w", encoding="utf-8").write(nuevo)
        # **Y si la pregunta ya se hizo antes, se conserva CUANDO se hizo.**
        #
        # Sin esto la guarda se muerde la cola: al consumirse una respuesta el
        # par se archiva, la vuelta siguiente reescribe el pedido —con fecha de
        # ahora aunque el texto sea identico— y la respuesta que acaba de
        # llegar queda «anterior a su pedido». Se archiva por desfasada, se
        # vuelve a preguntar lo mismo, y otra vez. reel-01 dio cuatro vueltas
        # asi con la respuesta correcta escrita en disco.
        #
        # La fecha del pedido tiene que significar **cuando cambio la
        # pregunta**, no cuando se escribio el fichero. Si el texto coincide
        # con una version ya archivada, esa es su fecha.
        arch = os.path.join(_dir(paso), "usadas")
        if os.path.isdir(arch):
            for f in sorted(os.listdir(arch)):
                if not (f.startswith(f"{slug}.") and f.endswith(".pedido.json")):
                    continue
                q = os.path.join(arch, f)
                try:
                    if io.open(q, encoding="utf-8").read() == nuevo:
                        t = os.path.getmtime(q)
                        os.utime(p, (t, t))
                        break
                except OSError:
                    continue
    # **El paso que tiene oficio no se contesta a si mismo.**
    #
    # `_por_cli` es `claude -p` generico: sin `--agent`, sin el contrato de ese
    # oficio y sin la capa de tiquets. Contestaba, y por eso el paso se daba por
    # hecho — pero la respuesta no declaraba `tiquets: [...]`, que es lo unico
    # que cierra un tiquet, asi que la pieza pasaba con su correccion abierta y
    # `vencidas` la devolvia. Tres vueltas la noche del 7 al 8 de septiembre.
    #
    # Donde hay oficio declarado, llamarle es del disparador y contestar es
    # suyo: una sola puerta. Donde no lo hay —redundancia, fuentes— el CLI sigue
    # siendo la unica forma de que ese pedido se conteste.
    from dominio.oficio import DE as _OFICIOS, POR_BASH
    if cli and POR_BASH and paso not in _OFICIOS and _hay_cli():
        r = _por_cli(prompt, payload)
        if r is not None:
            json.dump(r, open(ruta_respuesta(paso, slug), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            return r
    r = recoger(paso, slug)
    # **Y una respuesta mas vieja que su pedido no contesta a este pedido.**
    #
    # Los dos ficheros se emparejan por el nombre y nada mas, asi que una
    # respuesta escrita para la pregunta de hace dos vueltas entraba como si
    # fuera de esta. Paso con `describir` de reel-01: el agente describio las
    # etapas 2 y 3 —las que estaban caducadas cuando se escribio su pedido— y
    # para cuando contesto, la pieza se habia vuelto a cortar y las caducadas
    # eran la 6, la 7 y la 8. Aplicarla no arregla nada y **la puerta vuelve a
    # pedir lo mismo**: un bucle que no converge, y cada vuelta parece trabajo.
    #
    # Es C-92 otra vez —la huella que ata una nota a su montaje— en el otro
    # canal. Aqui la huella es la fecha, y solo sirve porque el pedido ya no se
    # reescribe cuando no cambia.
    if r is not None and os.path.exists(p):
        rp = ruta_respuesta(paso, slug)
        if os.path.getmtime(rp) < os.path.getmtime(p) - 1:
            # **Se archiva la respuesta y NO el pedido.** Son dos casos
            # opuestos: cuando una respuesta se consume, la pregunta ya esta
            # contestada y el par entero es historia; cuando llega desfasada,
            # **la pregunta sigue en pie** y es lo unico que hay. Llevarse el
            # pedido dejaba a quien tiene que contestar sin contrato —y sin
            # contrato lo correcto es no contestar, asi que la pieza se paraba
            # entera. Lo dijo el agente al que le toco: *«no lei ningun pedido;
            # un fichero inventado en esa ruta lo leeria el paso siguiente como
            # respuesta buena»*.
            # **Pero lo que el visto aprobó no caduca con el pedido.** Jaime,
            # 12-9: *«si un tramo esta bien nunca mas pasa por diseñador»*. Un
            # render nuevo reescribe el pedido y la respuesta se archivaba
            # entera: reel-09 y reel-11 aprobaron las mismas etapas dos veces
            # (C-441). La aprobación va firmada contra el corte de hoy, y si ese
            # corte cambia, caduca sola.
            if paso == "visto" and isinstance(r, dict) and r.get("aprueba"):
                from dominio.segmento import Segmento
                segs = {s.n: s for s in Segmento.de(slug)}
                for n in r["aprueba"]:
                    if str(n).isdigit() and int(n) in segs:
                        segs[int(n)].aprueba("disenador")
            # **Y lo que devolvió tampoco se pierde: pasa a tiquet.** reel-08,
            # 12-9: el visto devolvió e2 y e3, la línea volvió a renderizar
            # antes de leerlo y la devolución se archivó entera (C-455).
            if (paso == "visto" and isinstance(r, dict) and r.get("se_ensena") is False
                    and r.get("por_que")):
                try:
                    from dominio import ticket as _tq
                    _tq.abrir(slug, "visto (respuesta desfasada) · el diseñador no"
                              f" la enseña: {r['por_que'][:900]}", None, "objecion",
                              vuelve_a=r.get("vuelve_a") or "descrito", etapa="pieza")
                except Exception as e:  # noqa: BLE001 — se dice y se sigue
                    print(f"  visto/{slug}: la devolución desfasada no pudo"
                          f" abrirse como tiquet: {e}")
            _archivar(paso, slug, sufijo="desfasada", solo_respuesta=True)
            print(f"  {paso}/{slug}: la respuesta es anterior al pedido —"
                  f" contesta a otra pregunta. Se archiva y se vuelve a pedir.")
            return None
    if r is not None:
        # **Una respuesta se consume UNA vez.** El repaso es ciclico: aplica sus
        # cortes, manda la pieza a `cosido` y vuelve a pasar por aqui. Si la
        # respuesta sigue en su sitio, la segunda vuelta se come la misma otra
        # vez —y la tercera— y cada vuelta reinserta las mismas notas hablando
        # de un montaje que ya no existe.
        #
        # Medido: reel-04 tiene las notas #234-236 repetidas tres veces, y las
        # de la tercera vuelta ya llegaron marcadas «el texto ya no esta en la
        # pieza», que es como se ve desde dentro un bucle que se responde solo.
        # Peor que el ruido es lo que tapa: mientras el paso se contesta con lo
        # de antes, **nadie mira el corte de ahora**.
        #
        # Se archiva el par entero, no solo la respuesta: un pedido sin
        # respuesta se queda en la cola de `pendientes()` para siempre, y una
        # cola que miente sobre lo que falta es la misma averia por el otro
        # lado.
        _archivar(paso, slug)
        # **Y aqui es donde se sabe que el oficio termino.** Es el unico sitio
        # por el que la linea consume una respuesta, asi que es el que escribe
        # `hecho` y limpia la espera. `estado.marca` no la llamaba nadie y el
        # oficio lo anotaba a mano, con horas inventadas (10-9-2026).
        #
        # Sin disparar: esto corre DENTRO de un paso de `avanzar`, que sigue
        # recorriendo la pieza al volver; encender otro salto seria reentrar.
        try:
            from dominio import estado as _estado
            _estado.marca(slug, paso, "hecho",
                          quien=_OFICIOS.get(paso, "servicio"), dispara=False)
        except Exception:                          # noqa: BLE001
            pass
    return r


def _archivar(paso, slug, sufijo="", solo_respuesta=False):
    """Guarda el par pedido/respuesta ya consumido y lo saca de la cola.

    No se borra: el recorrido de una pieza es lo que explica por que quedo como
    quedo, y una vuelta del ciclo sin su pedido es una decision sin origen.
    """
    d = os.path.join(_dir(paso), "usadas")
    os.makedirs(d, exist_ok=True)
    marca = f".{sufijo}" if sufijo else ""
    n = 1
    while os.path.exists(os.path.join(d, f"{slug}.{n}{marca}.respuesta.json")):
        n += 1
    mover = [(ruta_respuesta(paso, slug), f"{slug}.{n}{marca}.respuesta.json")]
    if not solo_respuesta:
        mover.append((ruta_pedido(paso, slug), f"{slug}.{n}{marca}.pedido.json"))
    for orig, dest in mover:
        if os.path.exists(orig):
            os.replace(orig, os.path.join(d, dest))


def recoger(paso, slug):
    """La respuesta si existe, la escriba quien la escriba.

    **Y con envoltura o sin ella.** El contrato declara `("pieza",
    "elementos")` con su `valida` en `pendiente`, y los consumidores iteran una
    lista pelada. Los dos son defendibles; tener los dos a la vez no. Cada uno
    de los siete agentes de hoy gasto una parte de su turno en descubrir cual
    manda y en explicar por que eligio ese —«la envoltura esta declarada pero su
    valida sigue pendiente, asi que manda el consumidor»— y ese trabajo no
    produce ni un corte.

    Se acepta la forma envuelta y se desenvuelve aqui, en la puerta: quien
    contesta puede escribir cualquiera de las dos y ninguna se pierde. La
    ambiguedad se paga una vez, en un sitio, y no en cada respuesta.
    """
    p = ruta_respuesta(paso, slug)
    if not os.path.exists(p):
        return None
    try:
        # **Con `with`, y no es estilo.** `json.load(open(...))` deja el fichero
        # abierto cuando el JSON revienta —el `open` nunca se cierra—, y en
        # Windows un fichero abierto no se puede mover: el archivado de abajo
        # moria con `PermissionError` y se llevaba por delante al paso entero.
        # O sea que el arreglo del atasco causaba uno peor.
        with io.open(p, encoding="utf-8") as h:
            d = json.load(h)
    except json.JSONDecodeError:
        # **Una respuesta ilegible se aparta; no se deja donde esta.**
        #
        # Devolver `None` y dejar el fichero es la forma mas cara de fallar que
        # tiene este protocolo: `pendientes()` cuenta un pedido como servido
        # **porque existe su respuesta al lado**, no porque se pueda leer. Con
        # el JSON roto ahi, el pedido deja de salir en la cola, `turno.py` no lo
        # ofrece a nadie y `Oficio.de` no encuentra a quien llamar: **la pieza
        # queda esperando a nadie**, sin una linea que lo diga. Es exactamente
        # «lo lee y no hace nada».
        #
        # El mecanismo ya existia del otro lado —`servicio.mjs` la aparta como
        # `rechazada` cuando el esquema la tumba, y su comentario cuenta que
        # dejarla en su sitio tuvo a reel-03 y reel-05 dos dias parados—. Aqui
        # se hace lo mismo: se archiva solo la respuesta, el pedido se queda en
        # pie, y la pregunta vuelve a la cola de quien sabe contestarla.
        _archivar(paso, slug, "rechazada", solo_respuesta=True)
        return None
    if (isinstance(d, dict) and isinstance(d.get("elementos"), list)
            and set(d) <= {"pieza", "elementos"}):
        d = d["elementos"]
    # **Y lo que sube a Jaime se escribe aqui, no en los cinco consumidores.**
    #
    # Esta es la puerta por la que entra TODA respuesta, igual que `pedir()` es
    # la unica por la que sale todo pedido. Ponerlo en cada servicio son cinco
    # copias, y la que se olvide de copiarla deja pasar una cifra sin fuente.
    _escala(slug, d)
    return d


#: Las claves de respuesta cuyo efecto declarado es parar la pieza. `sube` lo
#: dice así —*«la pieza no pasa la puerta hasta que Jaime la mire»*— y
#: `rotulo_falso` lo dice más corto: *«para la pieza»*. Son el mismo hecho con
#: dos nombres, así que comparten camino en vez de tener dos puertas: un
#: rótulo que no es lo que dice la fuente cambia el mensaje, y lo que cambia el
#: mensaje lo decide Jaime.
PARAN = ("sube", "rotulo_falso")


def _escala(slug, datos) -> int:
    """Una nota por cada cosa que la respuesta manda a Jaime.

    **Va aquí y no en el dominio.** `Nota` sabe leer lo que subió
    —`Nota.subidas`—, pero escribirlo es del paso: C-198 sacó de `dominio/nota.py`
    el `import revision` precisamente para que el dominio no llamara al paso, y
    su guarda me paró al intentarlo. Medir y decidir es del dominio; escribir es
    de aquí.

    Y aquí dentro, en `recoger()`, porque es la puerta por la que entra TODA
    respuesta — igual que `pedir()` es la única por la que sale todo pedido.
    Repartido por los cinco servicios son cinco copias, y la que se olvide deja
    pasar una cifra sin fuente.

    Es idempotente sin esfuerzo: `revision.anotar` deduplica lo que sube por sus
    palabras de contenido, así que recoger dos veces no apila una segunda nota.
    """
    import revision

    n = 0
    for x in datos if isinstance(datos, list) else []:
        if not isinstance(x, dict):
            continue
        # **Y cada hallazgo dice de que clase es.** Los dos criterios no son
        # simetricos: lo de composicion casi siempre se puede contrastar —una
        # duracion, una repeticion, una cifra contra la tabla `dato`— y lo
        # estetico no. Sin marcarlo, la puerta trata igual «el tablero no
        # rotula su fuente», que se comprueba, y «tres tableros seguidos pesan»,
        # que es criterio y no lo contradice ninguna herramienta.
        #
        # Va delante del texto y no en una columna nueva: se lee de un vistazo
        # en la lista de lo que sube, y se cuenta con un `like`.
        clase = str(x.get("clase") or "").strip().lower()
        marca = f"[{clase}] " if clase in ("comprobable", "criterio") else ""
        for k in PARAN:
            que = str(x.get(k) or "").strip()
            if not que:
                continue
            revision.anotar(slug, "otro", None, None,
                            marca + (que if k == "sube" else f"{k}: {que}"),
                            estado="sube")
            n += 1
    return n


def _espera():
    """Cuánto se espera al CLI. La declara `dominio/oficio.py`, aquí se lee."""
    from dominio.oficio import ESPERA

    return ESPERA


def _hay_cli():
    """¿El CLI tiene credencial aquí?

    Se comprueba de verdad, no se supone: `claude -p` responde con código 0 y
    un JSON que dice `Not logged in` dentro, así que mirar el código de salida
    no vale. Y el resultado importa — el CLI usa la credencial de **la terminal
    que lo lanza**, y desde una sesión de Claude Code no hay ninguna (C-70).
    """
    try:
        out = subprocess.run(["claude", "-p", "ok", "--output-format", "json"],
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        d = json.loads(out.stdout or "{}")
        return not d.get("is_error")
    except Exception:                              # noqa: BLE001
        return False


def _por_cli(prompt, payload):
    try:
        out = subprocess.run(
            ["claude", "-p", "--output-format", "json"],
            input=f"{prompt}\n\n---\n\n{json.dumps(payload, ensure_ascii=False)}",
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            # La espera se declara una vez y la leen los dos sitios que llaman
            # al CLI. Ver `dominio/oficio.py :: ESPERA`.
            timeout=_espera())
        d = json.loads(out.stdout or "{}")
        if d.get("is_error"):
            return None
        txt = str(d.get("result") or "")
        i, j = txt.find("["), txt.rfind("]")
        if i < 0:
            i, j = txt.find("{"), txt.rfind("}")
        return json.loads(txt[i:j + 1]) if i >= 0 else None
    except Exception:                              # noqa: BLE001
        return None


def pendientes():
    """Pedidos escritos y sin respuesta, de una fase que su pieza no ha pasado."""
    from dominio.oficio import vigente

    out = []
    if not os.path.isdir(RAIZ):
        return out
    for paso in sorted(os.listdir(RAIZ)):
        d = os.path.join(RAIZ, paso)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".pedido.json"):
                continue
            slug = f[: -len(".pedido.json")]
            if not os.path.exists(ruta_respuesta(paso, slug)) and vigente(paso, slug):
                out.append((paso, slug, os.path.join(d, f)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    p = pendientes()
    if not p:
        print("servicio: no hay pedidos sin contestar")
        return
    print(f"servicio: {len(p)} pedido(s) esperando respuesta")
    for paso, slug, f in p:
        print(f"    · {paso} / {slug}   ->   {f}")
    print("\nLa respuesta va en el fichero .respuesta.json del mismo sitio."
          "\nNadie decide fuera de esto.")


if __name__ == "__main__":
    main()
