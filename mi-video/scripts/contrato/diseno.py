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
from .comun import CUMPLIMIENTO, REDUNDANCIA
from .piezas import Bloque, Campo, Clave, Contrato, Momento

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
MARCA = Bloque(
    "marca",
    texto="""
**Estas reglas son de la marca, no de la pieza. No se negocian por encargo.**

La autoridad visual son las 26 láminas de `docs/ejemplos/`: nieto Gen Z del
constructivismo ruso — huesos constructivistas, piel nativa digital.

**El oro dice «mira aquí», y sólo eso.** Si en un tablero hay tres cosas en oro,
dos sobran: el ojo no sabe dónde ir y el recurso deja de significar nada. La
paleta es corta a propósito —oscura y desaturada, con el oro como único tono
vivo—; un color nuevo entra con el valor y la saturación de esa familia, nunca
como código de estado.

**Dos familias, y se alternan.** *Cargada*: fotomontaje a sangre, punto de fuga,
geometría rota — para el golpe y el concepto. *Tranquila*: negro o navy liso,
geometría plana a escuadra — para las cifras que hay que leer. Una tabla sobre
fotomontaje no se lee; una tesis sobre negro liso es una diapositiva.

**Prohibido, y no es cuestión de gusto:** sombras, degradados suaves,
`backdrop-filter`, esquinas redondeadas Material — los bloques se separan con
filetes de un píxel. Rebote, confeti, wiggle, `Easing.back` o cualquier
micro-animación juguetona: esto es un asesor financiero hablando a dueños de
negocio. Ilustración amable, blobs, iconografía redondeada. Fotografía de familia
sonriente de stock. Serif de cualquier clase: se emborrona con la compresión.

**Una idea por tablero.** Si hacen falta dos, son dos tableros.

**La duración la decide la lectura, no un número redondo.** 0,75 s por bloque más
medio segundo de respiro. Un dato que no da tiempo a leer no está en la pieza
aunque esté en el frame — la web es autopaso y el vídeo no.

**El sonido va en el frame del movimiento.** No está prohibido el whoosh: está
prohibido el sonido sin movimiento que lo justifique.

**Y las formas no están limitadas al catálogo que hoy existe.** Si lo que el
encargo pide se dibuja mejor con una forma que no está construida, nómbrala: sale
como encargo de código, no como un tablero peor. Elegir entre ocho cajas cuando
la idea pedía una novena es dejar que el catálogo mande sobre el diseño.
""",
)


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
                trae=("encargo", "canon", "otras_etapas", "topes"),
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
                no_trae=("encargo", "canon", "otras_etapas", "topes"),
                nota="Aquí no recibe encargos: recibe **el artefacto medido** —lo"
                     " que dura, dónde calla, qué costuras se oyen, qué dice dos"
                     " veces y qué hay en pantalla sobre qué texto— y contesta"
                     " una sola cosa: si esto se le puede enseñar a Jaime. Todos"
                     " los momentos anteriores juzgan lo que se va a montar;"
                     " éste es el único que mira lo que salió."),
    ),
    campos=(
        # ── el encargo, que viene del paso anterior ──────────────────────────
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
              exige=(Prompt("scripts/disenar.prompt.md", "las dos familias se alternan"),),
              nota="El nivel de PIEZA del que monta. Sin esto no se puede alternar"
                   " cargada y tranquila, ni repartir el oro, ni evitar tres"
                   " tableros seguidos con la misma forma."),
        Campo("canon",
              manda=Aguja("scripts/servicios/disenar.py", '"canon": _canon(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "la paleta es corta a propósito"),),
              nota="Los tokens y las prohibiciones, del repositorio y no de"
                   " memoria: nada de rebote, sombras, degradados ni ilustración"
                   " amable."),
        Campo("topes",
              manda=Aguja("scripts/servicios/disenar.py", '"topes": _topes(),'),
              exige=(Prompt("scripts/disenar.prompt.md", "un copy que se pasa no sale feo, no sale"),),
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
        Clave("tablero.props",
              dispara=(Aguja("scripts/reels-spec.mjs", "...pieDe(slug, b.beat)"),
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
              dispara=(Aguja("scripts/gancho.mjs", "const tipo = esTipografico(desc?.grafico);"),),
              efecto="dónde cae el gráfico respecto a la cara",
              lista=("en cuadro", "cerrado", "fuera"),
              nota="Es lo que decide si él sale en pantalla en ese beat, así que"
                   " manda sobre la regla de las tres apariciones."),
        Clave("tablero.fuente",
              dispara=(Aguja("scripts/reels/base.mjs", "select f.rotulo, d.condiciones from dato d"),),
              efecto="el pie del tablero cuando rotula una cifra",
              sin_valor="sin cifra",
              nota="Cumplimiento: una cifra en pantalla sin fila en `dato` la para"
                   " la puerta. `sin_valor` distingue «no lleva cifra» de «lleva y"
                   " no dijo de dónde sale»."),
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
