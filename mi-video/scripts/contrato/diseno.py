"""4 · DISEÑO — el que monta lo que el anterior definió, y las reglas de la marca.

Regla de Jaime, y es la que parte la composición en dos: *«las escenas y
tableros las debe hacer un agente especializado en diseño; eso es editorial,
no sale con código»*, *«ese agente no tiene contrato, y es trabajo crear ese
contrato en la composición»*, *«entonces un agente se dedica a planear y
verificar y otro agente a diseñar»*, *«son dos tareas diferentes»*, *«uno
define lo que va a haber y el otro lo monta»*, *«una cadena de producción
agéntica»*.

Y los dos niveles, que es la corrección que evita el reparto fácil: *«no,
ambos son de pieza y de tablero»*. El que define ve la pieza para saber
cuántos tableros lleva y en qué orden; el que monta ve la pieza para que los
tableros no se parezcan entre sí ni gasten el oro tres veces.

**Qué agujero cierra.** `escena_desc.tablero` tiene fuente única declarada en
`verdad.py`, lo escribe `guardar_escena` y lo dibuja `reels-spec` — y ninguna
clave de ningún contrato se lo pedía a nadie. Un dato con dueño, con lector y
sin contrato es un dato que nadie produce: los seis ganchos tienen `tablero`
vacío, y por eso el bloque tipográfico acababa repitiendo la primera línea del
rótulo encima del rótulo.

`MARCA` vive aquí y no en `comun.py` porque es de este contrato solo: la parte
fija del encargo del diseñador, no algo que vaya en los cuatro.
"""
from .aguja import Aguja, Prompt
from .material import CAMARA, CAMPOS, LO_DICHO, VOZ
from .comun import CUMPLIMIENTO, REDUNDANCIA
from .marca import MARCA
from .piezas import Campo, Clave, Contrato, Momento

# ═════════════════════════════════════════════════════════════════════════════
# La parte FIJA del contrato del diseñador: las reglas de la marca
# ═════════════════════════════════════════════════════════════════════════════
#
# Jaime, definiendo la forma del contrato: *«el contrato del diseñador tiene dos
# partes: una variable, que es la que da el compositor, y otra fija, que son las
# reglas de la marca personal»*.
#
# La variable es `encargo` —un tablero concreto, escrito por quien planeó—. Ésta
# es la fija, y por eso es un `Bloque` y no prosa dentro del prompt: se escribe
# una vez, viaja con su huella, y si alguien edita la copia el build lo dice. La
# marca no se renegocia por pieza.
#
# **Lo que NO va aquí:** los valores concretos. La paleta y los topes se leen del
# repositorio en cada pedido (`_canon()`, `_topes()`), porque un hex citado de
# memoria es un hex que se desvía. Aquí van las reglas, que son las que no
# cambian aunque cambie un token.


DISENO = Contrato(
    paso="disenar",
    prompt="scripts/disenar.prompt.md",
    unidad="tablero, con la pieza entera delante",
    llave="etapa_orden",
    envoltura=("pieza", "tableros"),
    valida=Aguja("scripts/reels/base.mjs", "for (const m of revisarTablero(b.kind, b.props))",
                 pendiente="mover la comprobacion al momento de RECOGER la"
                           " respuesta. Hoy corre al armar el spec, que es"
                           " mucho antes del render —y ahi ya evita la corrida"
                           " muerta— pero despues de que el diseñador se haya"
                           " ido: no puede corregir lo suyo, lo corrige quien"
                           " monta"),
    momentos=(
        Momento("disenado", 7.5,
                trae=("encargo", "canon", "otras_etapas", "topes", "camara",
                      "composicion", "figuras", "ya_en_pantalla",
                      "correccion", "placas", "voz"),
                no_trae=(),
                nota="Después de `descrito`, que es quien dice qué etapas llevan"
                     " tablero y qué tiene que quedar dicho en cada uno. Antes de"
                     " `cortado`: montar sobre un corte que aún puede moverse es"
                     " pagarlo dos veces."),
        # **Y el mismo diseñador cierra: revisa lo que salió y lo lanza.**
        #
        # Jaime, fijando el reparto entero: *«exacto, el de corte compone; éste
        # diseña y hace, revisa que todo esté bien y lo lanza a render»*, *«que
        # lo revise el diseñador como paso final»*.
        #
        # Compuso la pieza, así que es el único que puede decir si lo entregado
        # es lo que diseñó. Un revisor nuevo tendría que deducir la intención
        # desde el resultado, que es justo lo que no se puede hacer.
        Momento("visto", 11.6,
                trae=("dura", "aire", "costuras", "repetido", "se_ve",
                      "motivos_abiertos"),
                no_trae=("encargo", "canon", "otras_etapas", "topes", "camara",
                         "composicion", "figuras", "ya_en_pantalla",
                         "correccion", "placas", "voz"),
                nota="Aquí no recibe encargos: recibe **el artefacto medido** —lo"
                     " que dura, dónde calla, qué costuras se oyen, qué dice dos"
                     " veces y qué hay en pantalla sobre qué texto— y contesta"
                     " una sola cosa: si esto se le puede enseñar a Jaime. Todos"
                     " los momentos anteriores juzgan lo que se va a montar;"
                     " éste es el único que mira lo que salió."),
    ),
    campos=(
        # ── el encargo, que viene del paso anterior ──────────────────────────
        # **La intencion del gancho es un campo del contrato, no una nota.**
        #
        # Jaime: *«con el hook dejalo en el contrato: ese segmento del video
        # tiene esa intencion, tanto en composicion como en diseno»*. O sea que
        # no es una preferencia que se recuerda al componer — es lo que ese
        # tramo ESTA PARA HACER, y sale exigido igual que el libreto.
        #
        # Y tiene numero detras: el objetivo es **10 dolares por adquisicion**,
        # y en trafico frio un webinar de bajo ticket cuesta entre 15 y 50. A 10
        # solo se llega si el creativo hace la mitad del trabajo — o sea si el
        # gancho para el scroll. No es ambicion estetica, es la aritmetica de la
        # campana.
        Campo("intencion_del_gancho",
              manda=Aguja("scripts/contrato/marca.py", "ENTRADA_GANCHO = {"),
              exige=(Prompt("scripts/disenar.prompt.md", "parar el scroll"),),
              nota="Jaime: «que todos los hooks se revisen y se hagan animados"
                   " de verdad, que paren scroll». El gancho no compite contra"
                   " otro video, compite contra el pulgar, y pierde en tres"
                   " segundos. «De verdad» excluye lo que hay hoy: una entrada"
                   " de opacidad, un texto que aparece, una placa que cruza."),
        Campo("encargo",
              manda=Aguja("scripts/servicios/disenar.py", '"encargo": f["grafico"],'),
              exige=(Prompt("scripts/disenar.prompt.md", "el encargo no se reinterpreta"),),
              nota="**El contrato de este paso lo escribe el paso anterior.**"
                   " Jaime: *«el contrato del segundo lo crea el primero; el"
                   " segundo hace el diseño gráfico, de las escenas y del"
                   " tablero»*. O sea que esto no es un campo más del payload:"
                   " es el encargo concreto de ese tablero —qué tiene que quedar"
                   " dicho y con qué límites—, redactado por quien planeó y"
                   " guardado en `escena_desc.grafico`. Prosa a propósito: dice"
                   " QUÉ, nunca cómo."),
        Campo("arco",
              manda=Aguja("scripts/servicios/disenar.py", '"arco": arco(pieza.slug),'),
              exige=(Prompt("scripts/disenar.prompt.md", "el arco no es contexto: es material"),),
              nota="Jaime: *«el compositor puede darle información respecto al"
                   " arco narrativo y al arco emocional al diseñador; el diseñador"
                   " puede hacer un gancho visual mucho más potente»*. Son dos"
                   " arcos: el narrativo —qué función cumple cada etapa— y el"
                   " emocional —la onda, arriba y abajo—. Sin ellos el que monta"
                   " diseña tableros correctos que no saben dónde caen."),
        Campo("otras_etapas",
              manda=Aguja("scripts/servicios/disenar.py", '"otras_etapas": resumen,'),
              exige=(Prompt("scripts/disenar.prompt.md", "las dos familias se alternen"),),
              nota="El nivel de PIEZA del que monta. Sin esto no se puede alternar"
                   " cargada y tranquila, ni repartir el oro, ni evitar tres"
                   " tableros seguidos con la misma forma."),
        Campo("canon",
              manda=Aguja("scripts/servicios/disenar.py", '"canon": _canon(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "la paleta es corta a propósito"),),
              nota="Los tokens y las prohibiciones, del repositorio y no de"
                   " memoria: nada de rebote, sombras, degradados ni ilustración"
                   " amable."),
        Campo("laminas",
              manda=Aguja("scripts/servicios/disenar.py", '"laminas": _laminas(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "la autoridad visual"),),
              nota="Las 26 laminas de `docs/ejemplos/` con sus RUTAS y su"
                   " anatomia. Jaime: «al contrato del disenador le falto el"
                   " contexto de la imagen de marca; no vio los ejemplos». Sin"
                   " esto quien compone trabaja con una paleta y una lista de"
                   " prohibiciones, y sale minimalismo corporativo."),
        Campo("estilo",
              manda=Aguja("scripts/servicios/disenar.py", '"estilo": ESTILO,'),
              exige=(Prompt("scripts/disenar.prompt.md", "neoconstructivista"),),
              nota="El encargo, no la prohibicion. «Respeto por la cuadricula"
                   " si, pero tambien irrespeto con criterio… mucho color: no hay"
                   " prohibiciones de color, hay prohibiciones de coherencia y"
                   " composicion.»"),
        Campo("antes_de_dibujar",
              manda=Aguja("scripts/servicios/disenar.py", '"antes_de_dibujar": ANTES_DE_DIBUJAR,'),
              exige=(Prompt("scripts/disenar.prompt.md", "intención narrativa"),),
              nota="El paso que faltaba: entender que deja entendido la etapa"
                   " ANTES de dibujarla. Sin el salen ilustraciones literales del"
                   " simil —palitos y bolitas para «es como un medico»— en vez de"
                   " lo que el simil viene a explicar."),
        Campo("piezas",
              manda=Aguja("scripts/servicios/disenar.py", '"piezas": catalogo_de_piezas(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "no son efectos de catálogo"),),
              nota="El catalogo indexado de `src/components/`, leido de los"
                   " propios componentes: cada uno declara su clase con `@clase`"
                   " y su primera linea dice que hace. Jaime: «es un catalogo"
                   " indexado, o esa era mi intencion con esos elementos; no se"
                   " por que nunca se utilizo». Nadie lo indexaba."),
        Campo("prioridad",
              manda=Aguja("scripts/servicios/disenar.py", '"prioridad": PRIORIDAD,'),
              exige=(Prompt("scripts/disenar.prompt.md", "carga cognitiva"),),
              nota="El orden cuando dos criterios chocan: carga cognitiva,"
                   " coherencia visual, objetivo emocional. Y la licencia para"
                   " no respetar el tablero propuesto, que antes el contrato"
                   " prohibia expresamente."),
        Campo("oficio_reel",
              manda=Aguja("scripts/servicios/disenar.py", '"oficio_reel": OFICIO_REEL,'),
              exige=(Prompt("scripts/disenar.prompt.md", "tipografía cinética"),),
              nota="Las practicas del reel comercial y el filtro de marca:"
                   " ni pastel redondeado ni el minimalismo que todo el mundo"
                   " hace para lucir caro."),
        Campo("sonidos",
              manda=Aguja("scripts/servicios/disenar.py", '"sonidos": _sonidos(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "el nombre exacto de la lista"),),
              nota="Los siete efectos que existen, con lo que hace cada uno."
                   " Sin esto el disenador describia el sonido con sus palabras"
                   " —«un roce grave y arrastrado»— y la capa se montaba muda."),
        Campo("verse",
              manda=Aguja("scripts/servicios/disenar.py", '"verse": VERSE,'),
              exige=(Prompt("scripts/disenar.prompt.md", "míralo antes de contestar"),),
              nota="**Cómo verse antes de entregar**, con el comando exacto:"
                   " `npx remotion still`. Todo lo que salió mal en reel-06 —el"
                   " subtítulo sobre la cara, el panel flotando contra una pared"
                   " vacía, la placa enseñando las piernas, el copy del tablero"
                   " pisado por el cc— se ve en un fotograma, y ninguna se ve"
                   " leyendo el JSON de la respuesta, que es lo único que el"
                   " diseñador miraba. Jaime tuvo que mirarlo por él."),
        Campo("figuras",
              manda=Aguja("scripts/servicios/disenar.py", '"figuras": figuras_que_se_trazan(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "La biblioteca está cerrada"),),
              nota="Los nombres que `Pictograma` sabe trazar, leídos de"
                   " `escena.mjs`. Sin esto el diseñador la escribe en prosa y"
                   " la escena **se monta sin figura y sin aviso**: pasó tres"
                   " veces. Y desde el 6-9-2026 **la lista puede venir vacía**"
                   " —la biblioteca está cerrada—, y el pedido tiene que"
                   " DECIRLO: vacía y sin explicar se lee como un fallo."),
        Campo("volumenes",
              manda=Aguja("scripts/servicios/disenar.py", '"volumenes": volumenes_que_se_animan(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "no declares `props.figura` ni `props.volumen`"),),
              nota="Las animaciones de panel de `src/brand/volumenes.json`, hoy"
                   " vacías: la biblioteca se cerró el 6-9-2026. Y el prompt"
                   " seguía pidiendo `props.volumen` **mientras la puerta"
                   " paraba la pieza por declararlo**: la máquina mandaba una"
                   " cosa y comprobaba la contraria."),
        Campo("ya_en_pantalla",
              manda=Aguja("scripts/servicios/disenar.py", '"ya_en_pantalla": hay.get(int(f["etapa_orden"]),'),
              exige=(Prompt("scripts/disenar.prompt.md", "el material B sobre una línea A cerrada"),),
              nota="Qué hay HOY encima del plano en cada etapa, leído de"
                   " `src/reels.json` — o sea de lo que el render dibuja, no de"
                   " lo que se decidió. Jaime, al mandar las siete: *«ya las"
                   " escenas están escogidas, así que… pues que agregue lo B que"
                   " falta»*. Para agregar lo que falta hay que saber lo que hay,"
                   " y el pedido describía cada etapa como si la pieza estuviera"
                   " en blanco."),
        *CAMPOS,
        Campo("camara",
              manda=Aguja("scripts/servicios/disenar.py", '"camara": mando_de_camara(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "declarar es elegir, no rellenar"),),
              nota="El mando de la cámara —encuadre, movimiento, transición— con"
                   " sus valores LEÍDOS de quien los ejecuta, y con el aviso de"
                   " los verbos que se ofrecen sin implementar. Es la respuesta"
                   " a *«dale herramientas al diseñador para que pueda tocar"
                   " todo eso»*: el documento nombraba los tipos de plano y no"
                   " había por dónde pedirlos."),
        Campo("composicion",
              manda=Aguja("scripts/servicios/disenar.py", '"composicion": que_leer_para_componer(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "cómo se representa una idea"),),
              nota="La ruta y el índice de `docs/composicion.md`: de qué habla"
                   " cada tipo de plano, las cuatro familias de animación, para"
                   " qué sirve una máscara, las zonas seguras del vertical y el"
                   " paso previo a dibujar. Viaja la ruta y no el texto —son 180"
                   " líneas y el pedido ya lleva catorce bloques—, pero saber"
                   " que está y cuándo abrirlo es la diferencia entre un"
                   " documento que existe y uno que se lee."),
        Campo("topes",
              manda=Aguja("scripts/servicios/disenar.py", '"topes": _topes(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "Un copy que se pasa no sale feo: no sale"),),
              nota="Salen de `src/brand/copy.ts` y **fallan el render**, no avisan."
                   " Mandarlos es más barato que un render muerto."),
    ),
    claves=(
        # ── nivel TABLERO: lo que se monta ───────────────────────────────────
        Clave("tablero.kind",
              dispara=(Aguja("scripts/reels/base.mjs",
                             "return { beat: Number(f.etapa_orden), kind: t.kind, props: t.props };"),),
              efecto="qué forma lo dibuja",
              obligatoria=True,
              exige_ademas=("tablero.props",),
              nota="**Lista ABIERTA, y eso es deliberado.** Jaime: *«las"
                   " limitaciones de código se acaban de inmediato; las formas"
                   " ahora sí pueden ser variadas como se declaró al comienzo»*."
                   " Cerrarla a los ocho componentes que hoy existen convierte el"
                   " catálogo del render en el techo del diseño, que es al revés"
                   " de como tiene que ser: el diseño manda y el código lo"
                   " alcanza. Una forma que todavía no tiene componente sale como"
                   " falta con su nombre —encargo de código, no de diseño— en vez"
                   " de forzar al diseñador a elegir entre ocho cajas."),
        Clave("tablero.cubre",
              dispara=(Aguja("scripts/reels/capas.mjs", "export function repartirPorCubre(declarados) {"),
                       Aguja("src/components/TableroDeclarado.tsx", 'const acompana = cubre === "panel" || cubre === "banda";'),),
              efecto="si el elemento TOMA el cuadro, lo acompaña, o no existe",
              obligatoria=True,
              lista=("pleno", "panel", "banda", "cc"),
              nota="**El reparto lo fijó Jaime y es de tres:** *«tableros son"
                   " para contenido complejo o para tapar cortes muy fuertes;"
                   " panel para contenido complejo que requiere activación"
                   " emocional, o que no es tan complejo para un tablero; y cc"
                   " dinámico en el resto»*.\n\n"
                   "                   Y no es una preferencia de estilo: es lo que"
                   " decide si él sale en cuadro. Con seis tableros a `pleno`,"
                   " reel-01 quedó con **90 de sus 142,8 s tapados —el 63%— y"
                   " Jaime sin aparecer en el tercio de en medio**, así que la"
                   " puerta paró la pieza. Un tablero que no lleva contenido"
                   " complejo ni tapa un corte duro le está quitando el sitio a"
                   " la cara.\n\n"
                   "                   `cc` es la opción por defecto del resto, no"
                   " un hueco: el subtítulo dinámico ya lleva la idea."),
        # **Su lado, cuando el tablero lo lleva dentro** (T-06, C-383). Jaime,
        # 10-9-2026: *«ahora todos los tableros deben mostrar mi cara»*. Es
        # obligatoria a pleno cuando el pedido trae `cara_en_todo_tablero` —el
        # prop `cara: "siempre"` del marco—, y la para `formas.mjs ::
        # sinSujeto`; en las demás piezas es opcional. `abajo`, sólo en
        # `PanelDentro`. Va en dos líneas por el techo de este fichero.
        Clave("tablero.sujeto", dispara=(Aguja("src/components/Tablero.tsx", "<LadoDelSujeto.Provider value={conSujeto ? lado ?? null : null}>"), Aguja("scripts/formas.mjs", "export const sinSujeto = (kind, props) => {")), efecto="su recorte en el tablero y su columna libre", obligatoria=False, lista=("izquierda", "derecha", "abajo"), nota="T-06 (C-383): ver el comentario de encima."),
        Clave("tablero.volumen",
              dispara=(Aguja("scripts/reels/paneles.mjs", "export function faltaDelPanel(p) {"),
                       Aguja("src/components/SidePanel.tsx",
                             "<Escena3D nombre={volumen} lado={ladoVolumen ?? lado} hueco={hueco} />"),),
              efecto="la animación del panel: qué se mueve y con qué luz",
              obligatoria=True,
              nota="**Obligatoria cuando `cubre` es `panel`**; la banda queda"
                   " fuera. Jaime: *«las animaciones de bolitas y palitos y ultra"
                   " sencillas se acaban, quitan más de lo que dan; ahora sólo"
                   " complejas, con luz o movimiento, ojalá 3D, y en consonancia"
                   " con la idea del panel»*. Lo que la hace cumplible es que ya"
                   " hay dónde elegir y quién mire: `faltaDelPanel` para."),
        Clave("tablero.props",
              dispara=(Aguja("scripts/reels-spec.mjs", "props: pieDe(slug, b, faltas)"),
                       Aguja("scripts/escena.mjs", "export const copyDeclarado = (desc) => {"),),
              efecto="el copy que sale en pantalla, incluido el del gancho"
                     " tipográfico",
              obligatoria=True,
              nota="`copyDeclarado` es la mitad del gancho: sin esto la capa no"
                   " entra, que es mejor que entrar repitiendo el rótulo."),
        # ── la composición gráfica ENTERA, no sólo el tablero ───────────────
        #
        # Jaime: *«ojo, que no es sólo el tablero: es la composición gráfica de
        # la pieza, animaciones, hooks y paneles»*.
        #
        # De estos cuatro campos sale todo lo que se mueve en pantalla, y los
        # escribía el compositor: `figuraDe(grafico)` decide la figura que se
        # anima, `sonidoDe(sonido)` el movimiento que suena, `desaturaDe(color)`
        # si la escena se apaga, y `plano` dónde cae respecto a la cara. O sea
        # que el diseñador tenía el tablero y el compositor tenía las
        # animaciones, el gancho y los paneles — al revés de como debe ser.
        #
        # `grafico` se queda en el otro contrato a propósito: es el ENCARGO
        # —qué tiene que quedar dicho— y eso sí es de quien compone. El CÓMO es
        # de aquí.
        Clave("componente",
              dispara=(Aguja("scripts/caminos.mjs", "componente: desc?.componente ?? null,"),),
              efecto="qué forma dibuja la etapa, y si compone o va a plano seco",
              sin_valor="ninguno"),
        Clave("color",
              dispara=(Aguja("scripts/escena.mjs", "const desaturaDe = (color) =>"),),
              efecto="si la escena se aviva o se apaga bajo el gráfico",
              lista=("avivar", "apagar"),
              sin_valor="dejar"),
        Clave("sonido",
              dispara=(Aguja("scripts/escena.mjs", "export const sonidoDe = ("),),
              efecto="el movimiento que suena, en el frame en que se mueve",
              nota="Prohibido el sonido sin movimiento que lo justifique, y al"
                   " revés: prohibido inventarle sonido a un movimiento que la"
                   " escena no describió."),
        Clave("plano",
              # Apuntaba a la rama tipográfica del gancho, que era un proxy
              # flojo: aquella miraba `grafico`, no `plano`. Desde que el gancho
              # coloca su rótulo DESDE la coronilla que midió la pasada del
              # recorte, «dónde cae respecto a la cara» tiene un consumidor
              # literal, y es éste.
              dispara=(Aguja("scripts/reels/rotulo.mjs", "export function colocar("),),
              efecto="dónde cae el gráfico respecto a la cara",
              lista=("en cuadro", "cerrado", "fuera"),
              nota="Es lo que decide si él sale en pantalla en ese beat, así que"
                   " manda sobre la regla de las tres apariciones."),
        *CAMARA,
        *VOZ,
        *LO_DICHO,
        Clave("tablero.fuente",
              dispara=(Aguja("scripts/servicios/disenar.py", '"pie": t["fuente"]'),
                       Aguja("scripts/reels/puerta.mjs", "sinRespaldo(slug,"),),
              efecto="LA LÍNEA DEL PIE en pantalla", sin_valor="sin cifra",
              nota="**Ya no es un rótulo: es el texto que se dibuja** — fuera de"
                   " la zona segura, una línea, mono, afirmativo, tope 97 en"
                   " `src/brand/pie.json`; pasarse no abrevia: sale falta."),
        # ── nivel PIEZA: lo que sólo se ve mirándolos todos ──────────────────
        Clave("pieza.alternancia",
              dispara=(Aguja("scripts/reels/capas.mjs", "export function repartirPorCubre(declarados) {",
                             pendiente="leer la familia declarada por tablero en vez"
                                       " de dejar que cada uno salga con la suya"),),
              efecto="qué tableros van cargados y cuáles tranquilos",
              lista=("cargada", "tranquila"),
              nota="Una tabla sobre fotomontaje no se lee; una tesis sobre negro"
                   " liso es una diapositiva. La alternancia es de pieza, no de"
                   " tablero: por eso vive aquí."),
        Clave("pieza.veredicto",
              dispara=(Aguja("scripts/servicios/disenar.py", "return Resultado(False, motivo=",),),
              efecto="para la pieza si el conjunto no se sostiene",
              obligatoria=True,
              lista=("monta", "rota"),
              nota="El que monta también puede parar: tres tableros seguidos con"
                   " la misma forma, o el oro gastado en todo, no es un defecto de"
                   " un tablero — es de la pieza, y no se ve mirando uno."),
    ),
    bloques=(MARCA, REDUNDANCIA, CUMPLIMIENTO),
    repite=None,
    nota="Segundo eslabón de la cadena: el primero define lo que va a haber"
         " (`descrito`) y éste lo monta (`disenado`).",
)
