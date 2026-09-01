"""2 · COMPONE — describir, con lo que `revalidar` decidía por duplicado.

`revalidar.camino` y `describir.trato` son la MISMA lista de cinco valores
decidida en dos pasos distintos: uno de los dos se tira (`camino` tiene cero
lecturas en todo el repo) y el otro se pide dos fases después. Aquí hay un
solo sitio donde se decide cómo se ve una etapa.
"""
from .aguja import NADIE, Aguja, Prompt
from .comun import CUMPLIMIENTO, REDUNDANCIA
from .piezas import Campo, Clave, Contrato, Momento

COMPONE = Contrato(
    paso="describir",
    prompt="scripts/describir.prompt.md",
    unidad="etapa, con la pieza entera delante",
    llave="etapa_orden",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/describir-esquema.mjs", "const CAMPOS = {"),
    momentos=(Momento("descrito", 7.0),),
    campos=(
        Campo("etapas",
              manda=Aguja("scripts/describir-pedido.mjs", "`Reel: ${slug} — ${filas.length} etapas, en orden.`"),
              exige=(Prompt("scripts/describir.prompt.md", "el contexto es el video en general"),),
              nota="La unidad de la llamada es la pieza porque la segunda variable"
                   " —lo que la pieza necesita— no existe a nivel de etapa."),
        Campo("portada",
              manda=Aguja("scripts/describir-pedido.mjs", 'portada = edl.detalle?.find((d) => d.trato === "portada")?.beat'),
              exige=(Prompt("scripts/describir.prompt.md", "el gancho"),),
              condicional="si el EDL no existe, el catch deja la línea vacía",
              si_falta=Prompt("scripts/describir.prompt.md", "sin portada marcada"),
              nota="Sin ella el modelo elige `trato:'portada'` a ciegas y `valida`"
                   " lo acepta en cualquier etapa o en ninguna."),
        Campo("libreto",
              manda=Aguja("scripts/describir-pedido.mjs", '"Libreto:",'),
              exige=(Prompt("scripts/describir.prompt.md", "la intención comunicativa"),),
              nota="Trae el `[pausa]`. Una etapa sin libreto no entra al paso:"
                   " `escenas_por_describir` filtra `where l.texto is not null`."),
        Campo("mensaje",
              manda=Aguja("scripts/describir-pedido.mjs", '`Funcion: ${f.mensaje ?? "(no declarada)"}`'),
              exige=(Prompt("scripts/describir.prompt.md", "qué función cumple cada una"),)),
        Campo("dicho",
              manda=Aguja("scripts/describir-pedido.mjs", '"Lo que de verdad se dijo:"'),
              exige=(Prompt("scripts/describir.prompt.md", "la intención comunicativa"),),
              nota="`montaje || dicho`: lo que el montaje dice hoy, no lo que se"
                   " eligió. Son cosas distintas en cuanto un recorte toca la etapa."),
        Campo("etapa",
              manda=Aguja("scripts/consulta.py", "def escenas_por_describir("),
              exige=(Prompt("scripts/describir.prompt.md", "qué función cumple cada una"),),
              nota="Puede llegar literalmente `null`: el LEFT JOIN a"
                   " `etapa_canonica` empareja por `ec.orden = e.etapa_orden`"
                   " mientras todo lo demás del paso usa `e.orden`."),
        Campo("bordes",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/describir.prompt.md", "Cada etapa puede traer una lista"),),
              nota="EXIGIDO Y NO ENVIADO, y el dato EXISTE: `escenas_por_describir`"
                   " lo calcula y lo adjunta a cada fila, y `describePieza` no lo"
                   " copia a `entrada`. La cadena `bordes` no aparece ni una vez"
                   " en describir.mjs. Coste pagado y tirado."),
        Campo("segundos",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/describir.prompt.md", "con los segundos exactos"),),
              nota="EXIGIDO Y NO ENVIADO. El payload no lleva un solo segundo: ni"
                   " inicio, ni fin, ni duración — y el prompt razona sobre tiempo"
                   " de lectura y pide devolver `tramos`."),
        Campo("candidatas",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/describir.prompt.md", "no se salta un peldaño"),),
              nota="EXIGIDO Y NO ENVIADO. `remedio: 'recuperar'` presupone saber"
                   " qué más se grabó y el payload manda un único texto por etapa."),
        Campo("cruces",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/describir.prompt.md", "Lo que se repite en la costura"),),
              nota="EXIGIDO Y NO ENVIADO. `consulta.cruces` existe y no viaja."),
        Campo("repetido",
              manda=Aguja("scripts/consulta.py", "def repetido(slug, n=3):"),
              exige=(),
              nota="INERTE: se calcula por etapa en cada corrida, `describePieza`"
                   " no lo copia y el prompt no lo nombra."),
    ),
    claves=(
        Clave("etapa_orden",
              dispara=(Aguja("scripts/describir.mjs", "new Map(ds.map((d) => [Number(d.etapa_orden), d]))"),),
              efecto="enruta el objeto a su fila",
              obligatoria=True,
              nota="No se guarda: la fila se escribe con `f.orden`, el número del"
                   " código."),
        Clave("que_pasa",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):"),),
              efecto="`escena_desc.que_pasa`, y de ahí al payload del corte",
              obligatoria=True),
        Clave("trato",
              dispara=(Aguja("scripts/trato.py", "select trato, trato_porque from escena_desc"),),
              efecto="impone el tratamiento del segmento por encima de la heurística",
              obligatoria=True,
              lista=("portada", "tablero", "cercano", "metafora", "diapositiva"),
              nota="Absorbe `revalidar.camino`, que es la misma lista y tiene cero"
                   " lecturas en el repo."),
        Clave("trato_porque",
              dispara=(Aguja("scripts/trato.py", "select trato, trato_porque from escena_desc"),),
              efecto="queda escrito para poder discutirlo después",
              adjunta_a="trato"),
        Clave("prioridad",
              dispara=(Aguja("scripts/dominio/seleccion/entrega.py",
                             'manda_limpieza = (prioridades or {}).get(s0 + 1) == "limpieza"'),),
              efecto="cambia qué toma gana en la selección",
              lista=("entrega", "limpieza"),
              nota="La clave con el efecto más fuerte sobre el corte final."),
        Clave("componente",
              dispara=(Aguja("scripts/caminos.mjs", "componente: desc?.componente ?? null,"),
                       Aguja("scripts/costuras.py", "and componente is not null")),
              efecto="pone el tablero en los props y marca qué etapas componen",
              lista=("CausalChain", "TwoPaths", "BeliefSwap", "ThenNow",
                     "EvidenceCard", "ComparisonTable"),
              sin_valor="ninguno",
              nota="`ninguno` se guarda como NULL, así que «no hace falta tablero»"
                   " y «no lo dijo» quedan indistinguibles en la base. `sin_valor`"
                   " tiene que guardarse como valor, no como ausencia."),
        Clave("grafico",
              dispara=(Aguja("scripts/escena.mjs", "export const figuraDe = (grafico) => {"),),
              efecto="la figura dibujable o la composición tipográfica; sin ella"
                     " el gancho falla",
              obligatoria=True),
        Clave("color",
              dispara=(Aguja("scripts/escena.mjs", "const desaturaDe = (color) =>"),),
              efecto="desatura la escena del tablero",
              lista=("avivar", "apagar"),
              sin_valor="dejar",
              nota="`dejar` por defecto era indistinguible de `dejar` decidido."),
        Clave("sonido",
              dispara=(Aguja("scripts/escena.mjs", "export const sonidoDe = ("),),
              efecto="el movimiento sonoro de la capa",
              nota="Texto libre: lo que `sonidoDe` no reconozca cae en silencio."
                   " O es lista cerrada, o `sonidoDe` avisa."),
        Clave("corrige",
              dispara=(Aguja("scripts/reels/base.mjs", "select corrige_dice, corrige_es from escena_desc"),
                       Aguja("scripts/fuentes.py", "d.corrige_dice, d.corrige_es")),
              efecto="coloca la corrección sobre la línea de CC y falla el build"
                     " si no encuentra las palabras",
              nota="NO ESTÁ EN `CAMPOS`: no se valida, no se exige, y una"
                   " respuesta sin `corrige` pasa la puerta sin aviso. Y es un"
                   " único par {dice, es}: dos contradicciones en la misma etapa"
                   " y la segunda se pierde."),
        Clave("integridad",
              dispara=(Aguja("scripts/verificar.py", "def revisar(",
                             pendiente="si `integridad` dice que el mensaje no"
                                       " llega, la etapa no se da por descrita:"
                                       " hoy se guarda y cuenta en `ok` igual"),),
              efecto="para la etapa cuando el mensaje no llega",
              nota="Hoy `verificar.py` la selecciona y no la usa."),
        Clave("remedio",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):"),),
              efecto="qué hacer con la etapa incompleta",
              lista=("recuperar", "tablero", "cortar"),
              sin_valor="ninguno",
              exige_ademas=("de_donde",),
              nota="`recuperar` sin `de_donde` es «esto se dijo en otra parte» sin"
                   " poder decir dónde. `revalidar` lo sobrescribe con"
                   " `coalesce(remedio,'tablero')` desde una fase anterior."),
        Clave("de_donde",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):",
                             pendiente="columnas `recupera_toma`, `recupera_desde`,"
                                       " `recupera_hasta` y declaración por `fijar`"),),
              efecto="de qué cinta y qué segundos se recupera",
              exige_ademas=("remedio",)),
        Clave("plano",
              dispara=(NADIE,),
              efecto="—",
              lista=("en cuadro", "cerrado", "fuera"),
              nota="INERTE: lista cerrada validada en `describir.mjs`, guardada en"
                   " la base y ninguna línea del proyecto la lee después."),
        Clave("emocion",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE: el prompt exige que sea concreta —«alarma contenida»,"
                   " no «negativa»— y nada comprueba ni consume esa concreción."),
        # ── el contrato del TABLERO ──────────────────────────────────────────
        #
        # Regla de Jaime, y es la que crea este nivel: *«las escenas y tableros
        # las debe hacer un agente especializado en diseno; eso es editorial, no
        # sale con codigo»*, *«ese agente no tiene contrato, y es trabajo crear
        # ese contrato en la composicion»*, *«pues un contrato por pieza, un
        # contrato por tablero»*.
        #
        # Lo que faltaba, literal: `escena_desc.tablero` tiene fuente unica
        # declarada en `verdad.py`, lo escribe `guardar_escena` y lo dibuja
        # `reels-spec`, y **ninguna clave de este contrato se lo pedia a nadie**.
        # Un dato con dueno, con lector y sin contrato es un dato que nadie
        # produce: los seis ganchos tienen `tablero` vacio, y por eso el bloque
        # tipografico acababa repitiendo la primera linea del rotulo.
        # Este paso PLANEA y VERIFICA el tablero; no lo dibuja. Y lo hace en los
        # dos niveles, que es la correccion de Jaime: *«no, ambos son de pieza y
        # de tablero»*. Un tablero no se planea solo —cuantos lleva la pieza y
        # en que orden es una propiedad del arco— y tampoco se verifica solo.
        Clave("tablero.hace_falta",
              dispara=(Aguja("scripts/caminos.mjs", "componente: desc?.componente ?? null,"),),
              efecto="si esta etapa lleva tablero, y por tanto si hay encargo"
                     " para el paso de diseno",
              obligatoria=True,
              nota="Es la mitad de `componente` que si es del planificador:"
                   " decidir QUE etapa compone se ve mirando la pieza entera."),
        Clave("tablero.dice",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):"),),
              efecto="que tiene que quedar dicho en ese tablero — el ENCARGO",
              adjunta_a="tablero.hace_falta",
              nota="Prosa a proposito: es lo que el disenador tiene que resolver,"
                   " no como. Se guarda en `grafico`, que es donde el paso de"
                   " diseno lo lee."),
        Clave("pieza.veredicto",
              dispara=(Aguja("scripts/describir.mjs", "process.exit(1)",
                             pendiente="un objeto de pieza: tres tableros seguidos"
                                       " o un orden que no sostiene el argumento"
                                       " no caben en un array por etapa"),),
              efecto="para la pieza entera",
              lista=("compone", "rota")),
    ),
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=None,
    nota="Lo único que para de verdad hoy es `sinAfinar` al 95%: el contenido no"
         " se juzga en ningún sitio, y una etapa con `integridad` diciendo que el"
         " mensaje no llega se cuenta en `ok` igual que una entera.",
)
