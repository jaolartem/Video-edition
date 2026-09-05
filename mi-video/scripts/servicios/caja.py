"""La caja de herramientas visual: las primitivas con que se compone.

Jaime, corrigiendo que sólo se le mandaran los siete efectos de sonido: *«no son
sólo 7; busca en este momento los efectos visuales que más que tendencia sean
**institucionales**, es decir que sean la caja de herramientas básica, que él
pueda combinar y crear nuevos, pero siguiendo estrictamente los parámetros
anteriores»*.

## Por qué institucional y no tendencia

Una tendencia caduca y se reconoce: *«si se reconoce la plantilla antes que el
mensaje, está mal»*. Una primitiva no — trasladar, escalar, revelar por máscara y
dibujar un trazo son las cuatro cosas que hace el motion design desde que existe,
y con ellas se construye tanto lo de hace veinte años como lo de mañana.

Así que aquí no hay «efectos»: hay **verbos**. El diseñador los combina y de esa
combinación sale el efecto, que es suyo y no de una plantilla.

## Y cada uno dice si existe

`ya_existe` apunta al fichero que lo hace. `por_construir` es una primitiva que
el sistema todavía no tiene: se puede pedir, pero hay que saber que cuesta código
antes de que se vea. Un catálogo que no distingue las dos cosas es un catálogo
que promete lo que no puede dar — que es exactamente lo que pasó con las figuras
de `Pictograma`.
"""
import os


def _raiz():
    """La carpeta `mi-video`. Tres `dirname`: este fichero cuelga de
    `scripts/servicios/`."""
    return os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))


def catalogo_de_piezas():
    """El catalogo indexado, LEIDO de `src/components/`.

    Aqui habia una lista de primitivas escrita a mano. Jaime: *«es un catalogo
    indexado, o esa era mi intencion con esos elementos; no se por que nunca se
    utilizo»*. La respuesta era que nadie lo indexaba — los veinte componentes
    estaban ahi, cada uno con su proposito en su cabecera, y ningun paso los
    leia. Una lista paralela escrita aqui habria sido la segunda copia de
    siempre.
    """
    import json
    import subprocess

    raiz = _raiz()
    try:
        # `encoding="utf-8"` y no el del sistema: en Windows `text=True`
        # decodifica en cp1252 y la primera tilde de una cabecera revienta
        # la lectura. El `except` de abajo lo convertia en un catalogo
        # con `error` dentro, o sea el paso corriendo sin sus piezas.
        out = subprocess.run(["node", "scripts/catalogo.mjs", "--json"],
                             capture_output=True, text=True,
                             encoding="utf-8", cwd=raiz,
                             check=True).stdout
        return json.loads(out)
    except Exception:                              # noqa: BLE001
        return {"error": "no se pudo leer el catalogo de piezas"}


#: Cómo se usa la caja. Sin esto es una lista de piezas sueltas.
COMO_COMBINAR = {
    "la_regla": "Un efecto es una COMBINACIÓN de estos verbos, no un elemento de"
                " catálogo. «El rótulo nace detrás de la cara, se acomoda delante"
                " y una banda de oro lo subraya» son tres primitivas y es un"
                " efecto propio.",
    "el_limite": "Todo lo que combines pasa por los tres criterios en orden:"
                 " carga cognitiva, coherencia visual, objetivo emocional. Y por"
                 " el canon de las 26 láminas: la técnica es de reel, la forma es"
                 " de esta marca.",
    "si_pides_algo_por_construir": "Puedes pedirlo. Dilo claro en `por_que` para"
                                   " que se sepa que esa pieza cuesta código"
                                   " antes de verse — no se descarta, se agenda.",
    "cuantas": "En el gancho, seis entradas mínimo. Fuera del gancho, algo cambia"
               " cada tres a cinco segundos. Jaime: «mucho movimiento, mucha"
               " dopamina» — pero cada cosa que se mueve deja algo entendido.",
}


def mando_de_camara():
    """El mando de la camara: encuadre, movimiento y transicion por etapa.

    Jaime: *«dale herramientas al disenador para que pueda tocar todo eso, que
    no quede otra vez el mismo error de declarar sin implementar, que ha sido la
    constante en este proyecto»*.

    Lo pide a `camara.mjs` en vez de escribirlo aqui por la razon de siempre: el
    vocabulario tiene que ser el de quien lo ejecuta. Los cinco encuadres los
    lee del propio `punch-ins.py`, asi que el menu no puede prometer un recorte
    que el cropper no sepa hacer.

    Y **comprueba antes de ofrecer**: si un verbo perdio la linea que lo
    consume, sale como aviso en el pedido en vez de como una promesa muerta.
    Es exactamente el fallo que este bloque viene a cerrar.
    """
    import json
    import subprocess

    def _mjs(bandera):
        return subprocess.run(["node", "scripts/camara.mjs", bandera],
                              capture_output=True, text=True,
                              encoding="utf-8", cwd=_raiz())

    # `OSError` si no hay node; `ValueError` si contesta algo que no es JSON.
    # Un `except Exception` a secas se tragaba tambien el `NameError` de un
    # `json` sin importar, y el paso corria sin su mando sin decir por que.
    try:
        out = _mjs("--json")
        if out.returncode:
            return {"error": "no se pudo leer el vocabulario de camara",
                    "por": (out.stderr or "").strip()[:200]}
        voc = json.loads(out.stdout)
    except (OSError, ValueError) as e:
        return {"error": "no se pudo leer el vocabulario de camara",
                "por": str(e)[:200]}
    rotas = _mjs("--comprobar")
    if rotas.returncode:
        voc["OJO"] = ("hay verbos ofrecidos SIN implementar; no los uses:\n"
                      + rotas.stdout.strip())
    return voc


def voz_en_el_remate():
    """El tratamiento de voz del punchline, con sus dos sabores y sus limites.

    Jaime: *«que cambie mi voz en los punchlines»*. Es una herramienta suya y
    hasta ahora no existia: la voz salia igual de principio a fin en las siete
    piezas.

    El menu se lo pide a `dominio/remate.py`, que es quien lo APLICA, por la
    razon de siempre —la de `mando_de_camara` y la de `figuras_que_se_trazan`—:
    un menu escrito aqui seria una segunda copia, y el dia que un trato cambiara
    de nombre el pedido ofreceria un sabor que la mezcla no sabe hacer.
    """
    import sys

    sys.path.insert(0, os.path.join(_raiz(), "scripts"))
    try:
        from dominio import remate
    except ImportError:
        return {"error": "no se pudo leer el vocabulario de voz"}
    return remate.menu()


def que_leer_para_componer():
    """El documento de composicion: planos, animaciones, mascaras y formatos.

    Jaime: *«busca los tipos de animaciones, efectos, mascaras, etc. basicos,
    documentalos, los tipos de plano… y que el pueda ver ese catalogo cuando
    necesite entender como representar una idea, o un arco narrativo o
    emocional»*.

    Viaja la RUTA y el indice, no el texto entero: son ~180 lineas y el pedido
    ya lleva catorce bloques. Lo que va aqui es lo que hace falta para saber que
    esta ahi y cuando abrirlo — que es la diferencia entre un documento que
    existe y uno que se lee.
    """
    ruta = os.path.join(_raiz(), "..", "docs", "composicion.md")
    if not os.path.exists(ruta):
        return {"error": "falta docs/composicion.md"}
    import re

    t = open(ruta, encoding="utf-8").read()
    return {
        "donde": "docs/composicion.md",
        "que_es": "el vocabulario del oficio: de que habla cada tipo de plano,"
                  " las cuatro familias de animacion, para que sirve una"
                  " mascara, las zonas seguras del vertical y COMO SE"
                  " REPRESENTA una idea sin ilustrar la palabra.",
        "cuando_abrirlo": "cuando no sepas como representar una idea, un arco"
                          " narrativo o un arco emocional. No es teoria de"
                          " adorno: la seccion 5 es el paso previo a dibujar.",
        "secciones": re.findall(r"^## (.+)$", t, re.M),
    }


def figuras_que_se_trazan():
    """Los NOMBRES de figura que `Pictograma` sabe dibujar, leidos de la lista.

    Sin esto el disenador escribe la figura en prosa —«dos caminos: quien usa la
    estructura y quien no»— y `dibujable()` no la reconoce, asi que **la escena
    se monta sin figura y nadie se entera**: sale como falta al final de la
    corrida, cuando ya no hay quien la corrija.

    Paso tres veces en la ultima pasada (reel-01 e2 y e5, reel-06 e4). Y la
    causa es la de siempre: la lista existia en `escena.mjs` desde el principio
    y el pedido no la llevaba. No se puede elegir de un catalogo que no se ve.

    Se lee de `escena.mjs`, no se copia: una segunda lista se desvia el dia que
    alguien anada una figura, y entonces el menu promete un dibujo que no hay.
    """
    import re

    ruta = os.path.join(_raiz(), "scripts", "escena.mjs")
    try:
        t = open(ruta, encoding="utf-8").read()
    except OSError:
        return {"error": "no se pudo leer scripts/escena.mjs"}
    m = re.search(r"DIBUJAN = new Set\(\[(.*?)\]\)", t, re.S)
    return {
        "se_trazan": re.findall(r'"([^"]+)"', m.group(1)) if m else [],
        "la_regla": "Si tu escena pide una figura, ponla en **`props.figura`**"
                    " con UNO de esos nombres exactos. Es lo que lee"
                    " `figuraDe()` en `scripts/escena.mjs`. Descrita con tus"
                    " palabras no se dibuja: la escena sale sin figura y sin"
                    " aviso hasta el final de la corrida.",
        "no_en_grafico": "`grafico` es el ENCARGO en prosa y lo escribe el paso anterior, no tu. Poner ahi el nombre de la figura no la dibuja: el lector es `props.figura`.",
        "y_si_no_esta": "La forma que necesitas no esta en la lista: dilo en"
                        " `por_que` y sale como encargo de codigo. Es mejor que"
                        " forzar una de las diez que no significa lo que quieres.",
    }


def ya_en_pantalla(slug):
    """Que hay HOY encima del plano en cada etapa, leido de la pieza montada.

    Jaime, al mandar las siete a diseno: *«ya las escenas estan escogidas, asi
    que... pues que agregue lo B que falta»*. Para agregar lo que falta hay que
    saber lo que hay, y el pedido no lo decia: el disenador recibia el encargo de
    cada etapa como si la pieza estuviera en blanco.

    Y no lo esta ni lo estara: la toma ya se eligio, el corte ya se hizo, y lo
    que se pide ahora es **el material B** —lo que tapa, explica y acompana—
    sobre una linea A que no se toca.

    Sale de `src/reels.json`, que es lo que el render dibuja de verdad. No de
    `escena_desc`: ahi esta lo que se decidio, y lo que hace falta saber aqui es
    **lo que llego a la pantalla**, que es lo que el espectador ve y lo unico
    contra lo que se puede decir «esto esta pelado».
    """
    import json

    ruta = os.path.join(_raiz(), "src", "reels.json")
    try:
        piezas = json.load(open(ruta, encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    pieza = next((x for x in piezas
                  if x.get("id") == f"Reel-R{int(slug[-2:])}"), None)
    if not pieza:
        return {}
    # Las capas por camino traen su beat; los tableros y las tarjetas tambien.
    # Lo que NO cuenta como material B: el punch, el rotulo y el subtitulo, que
    # los lleva cualquier plano por defecto — contarlos haria que una etapa
    # pelada pareciera vestida.
    DE_SERIE = {"punch", "rotulo", "subtitulo", "sonido"}
    fuera = {}
    for c in pieza.get("caminos") or []:
        b = c.get("beat")
        fuera.setdefault(b, set())
        if c.get("tipo") not in DE_SERIE:
            fuera[b].add(c["tipo"])
    for b in pieza.get("boards") or []:
        fuera.setdefault(b.get("beat"), set()).add("tablero")
    for t_ in pieza.get("tarjetas") or []:
        fuera.setdefault((t_.get("props") or {}).get("beat", [None])[0],
                         set()).add("tarjeta")
    return {b: (sorted(v) or ["NADA: cara y subtitulo, nada mas"])
            for b, v in fuera.items() if b is not None}


#: Como se corrige en pantalla algo que la voz dice mal.
#:
#: La regla la fijo Jaime en tres mensajes seguidos, y los tres acotan lo mismo:
#: *«si se puede corregir en pantalla si queda explicito el error»*, *«pero
#: explicito no es»* —de una nota al pie en letra pequena— y la forma exacta:
#: *«no decir "aca hay un error", sino que el error se enfatice en el numero
#: bueno, o el nombre bueno»*, *«como con el ministerio de comercio»*.
#:
#: El precedente que cita esta escrito en `Corregida.tsx` desde entonces: *«el
#: libreto dice la verdad, esta es una oportunidad para que el error se
#: manifieste: el subtitulo, cuando digo ministerio de comercio, dice la
#: informacion real palpitando o haciendola notar mas»*.
#:
#: **El mecanismo ya existia y el disenador no tenia por donde pedirlo.** Las
#: columnas estaban en `escena_desc`, `Corregida` las dibujaba y la clave vivia
#: en el contrato del COMPOSITOR — o sea en el unico sitio donde no la tiene
#: delante quien mira la cifra de la voz contra la cifra respaldada.
CORRECCION = {
    "cuando": "Cuando la voz dice un dato mal y el respaldado es otro: una cifra"
              " redondeada, un nombre de organismo cambiado, una fecha movida.",
    "como_se_pide": "Devuelve `corrige` en esa etapa:"
                    " `{\"dice\": \"<lo que se OYE, literal>\","
                    " \"es\": \"<lo bueno>\"}`. La palabra de `dice` tiene que"
                    " aparecer tal cual en algun subtitulo de esa etapa o la"
                    " correccion no se puede colocar y sale como falta.",
    "como_se_ve": "En el sitio de la palabra mala aparece LA BUENA, a 1,45x, en"
                  " oro y latiendo tres golpes. No hay tachado, ni asterisco, ni"
                  " nota al pie, ni una etiqueta que diga «error».",
    "lo_que_NO_es": "Una linea de letra pequena explicando la discrepancia. Eso"
                    " no es explicito: en video nadie para a leer el pie. Jaime:"
                    " «pero explicito no es».",
    "el_tono": "Puede ser una broma. Lo que no se negocia es que la correccion"
               " APAREZCA, porque el dato tiene fuente; el registro es libre.",
    "y_la_marca": "Va con el tramo en blanco y negro —la marca de humanidad— y"
                  " las dos son UNA sola marca, no dos. Una o dos por minuto:"
                  " en una pieza de estas, una.",
}


def placas_que_existen():
    """**El inventario de placas**, con lo que dibuja cada una y lo que provoca.

    Jaime, al elegir construir dos formas nuevas: *«que utilicen los fondos que
    ya existen, para generar texto encima de ellos, como lo muestran los
    ejemplos de carruseles; no es reinventar la rueda, es seguir la identidad
    grafica»*. Y acto seguido: *«que quede declarado el inventario»*.

    Las catorce placas viven en `public/fondos/` desde hace semanas, cada una
    con su `dice` y su `siente` escritos en `ads/fondos.json`, y **el disenador
    no las habia visto nunca**: el pedido llevaba las 26 laminas del canon —la
    autoridad visual, para mirar— y no las placas, que son las que se pueden
    usar. Componer una imagen desde cero teniendo `r1-mecanismo` —«un canal que
    lleva bloques hacia el punto de fuga y una derivacion que se los lleva fuera
    del cuadro»— es exactamente reinventar la rueda.

    `sirve` no es una asignacion cerrada: dice a que beats se penso, y por eso
    viaja. Una placa vale para otra etapa si lo que dibuja sostiene la idea.
    """
    import json

    ruta = os.path.join(_raiz(), "ads", "fondos.json")
    try:
        placas = json.load(open(ruta, encoding="utf-8"))["placas"]
    except (OSError, ValueError, KeyError):
        return {"error": "no se pudo leer ads/fondos.json"}
    return {
        "que_son": "Fotomontajes reales, con perspectiva y grano de papel. NO"
                   " son texturas: un corredor de archivadores con un solo cajon"
                   " enfrente ARGUMENTA. Se genero un collage por codigo una vez"
                   " y Jaime lo paro — «estaba muy feo» — por plano, mudo, de"
                   " textura falsa y sin sitio para el texto.",
        "como_se_usan": "Con el componente `Fondo`: `placa` (el nombre de esta"
                        " lista, sin extension), `recorte` (lleno · banda · cuna"
                        " · columna · esquina), `fuerza` para bajarla si el texto"
                        " no respira, y `deriva` para que no quede clavada.",
        "el_recorte_importa": "A sangre la placa deja de ser un elemento"
                              " compuesto y pasa a ser papel pintado. En el canon"
                              " la fotografia entra como FRAGMENTO de lados"
                              " rectos y el resto es plano de color: `lleno` se"
                              " reserva a las cortinillas, donde la placa ES el"
                              " plano.",
        "disponibles": {k: {"dibuja": v.get("dice"), "provoca": v.get("siente"),
                            "pensada_para": v.get("sirve")}
                        for k, v in placas.items()},
        "y_si_ninguna_sirve": "Dilo en `por_que`. Una placa nueva la genera"
                              " Jaime, no el codigo: es la parte del sistema"
                              " visual que no se procedimenta.",
    }


#: **Como VERSE antes de entregar.** Es la herramienta que faltaba.
#:
#: Todo lo que salio mal en reel-06 —el subtitulo encima de la cara, el panel
#: flotando contra una pared vacia, la placa ensenando las piernas, el copy del
#: tablero pisado por el cc— se ve en un fotograma. Ninguna se ve leyendo el
#: JSON de la respuesta, que es lo unico que el disenador miraba.
#:
#: Jaime tuvo que mirarlo por el. Con esto ya no.
VERSE = {
    "el_comando": "npx remotion still src/index.ts Reel-R<N> <salida>.png"
                  " --frame=<n> --gl=angle",
    "y_luego": "Abre el PNG y MIRALO. No es opcional: es el unico paso que ve lo"
               " que ve el espectador.",
    "que_frame": "El frame es a 30 fps sobre la pieza MONTADA: el segundo 6,5 es"
                 " --frame=195. Los `at` de tus tableros y paneles ya vienen en"
                 " frames en `src/reels.json`, asi que mira el centro de cada uno"
                 " y una costura entre dos.",
    "que_mirar": [
        "Su cara: ¿la tapa algo? ¿queda debajo de una capa de texto?",
        "Dos capas de texto en la misma franja: si compiten, una sobra ahi.",
        "El hueco de una placa: ¿ensena su cara o sus piernas?",
        "El copy del tablero contra la banda de subtitulos (55%-65% del cuadro).",
        "Lo que queda vacio: si un tercio del cuadro no hace nada, se esta"
        " desperdiciando la toma.",
    ],
    "antes_de_entregar": "Mira al menos DOS frames por pieza: uno con tablero a"
                         " cuadro completo y uno de plano limpio con subtitulo."
                         " Si algo se pisa, arreglalo antes de contestar.",
}


def tres_dimensiones():
    """El 3D, **y si de verdad se puede renderizar hoy**.

    Jaime instalo las skills de Three.js y pidio meterlas al contrato. Van solo
    cuatro de las diez: `geometry`, `materials`, `lighting` y `postprocessing`.
    Las otras seis —fundamentals, animation, loaders, interaction, shaders,
    textures— son de escenas interactivas, carga de modelos y controles de
    camara: un reel no tiene raton ni modelos que cargar, y meterlas hincha el
    pedido con lo que nadie va a usar.

    **Y se comprueba que los paquetes esten.** Declararlo disponible sin `three`
    ni `@remotion/three` instalados es la averia de todo el dia: el disenador
    pediria una escena 3D y saldria por `TableroDeclarado` como texto sobre
    negro. Aqui el bloque dice lo que hay, no lo que se espera que haya.
    """
    import subprocess

    raiz = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    def hay(m):
        try:
            return subprocess.run(
                ["node", "-e", f"require.resolve('{m}')"],
                cwd=raiz, capture_output=True).returncode == 0
        except OSError:
            return False
    listo = hay("three") and hay("@remotion/three")
    return {
        "se_puede": listo,
        "si_no": None if listo else
                 "AUN NO: faltan `three` y/o `@remotion/three`. No pidas una"
                 " escena 3D todavia — saldria como texto sobre negro. Nombrala"
                 " en `por_que` como encargo de codigo si la necesitas.",
        "para_que": "Una escena 3D dentro de la MISMA composicion, no un video"
                    " aparte: `<ThreeCanvas>` de `@remotion/three` se anima con"
                    " `useCurrentFrame()` como cualquier otra capa.",
        "cuando_vale": "Cuando la idea ES volumetrica y en plano no se entiende:"
                       " algo que atraviesa una compuerta y sale distinto, una"
                       " masa que crece en profundidad, dos caminos que se"
                       " separan EN EL ESPACIO. Para comparar dos cifras, no.",
        "las_cuatro": {
            "threejs-geometry": "las formas: cajas, extrusiones, mallas propias,"
                                " y repetir una forma mil veces sin coste",
            "threejs-materials": "como se ve la superficie: mate, metal, y"
                                 " shaders propios si hace falta",
            "threejs-lighting": "la luz y las sombras — lo que da el volumen",
            "threejs-postprocessing": "bloom, profundidad de campo y virado",
        },
        "el_limite": "El canon manda igual: nada de brillos, degradados suaves ni"
                     " esquinas redondeadas por venir de 3D. Constructivismo con"
                     " profundidad, no render de agencia.",
    }
