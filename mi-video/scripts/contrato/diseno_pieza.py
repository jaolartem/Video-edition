"""**Lo que sólo se ve mirando todas las etapas juntas.**

Las claves de nivel PIEZA del contrato de diseño. Jaime lo dijo al partir la
composición en dos: *«no, ambos son de pieza y de tablero»* — el que monta ve la
pieza entera para que los tableros no se parezcan entre sí ni gasten el oro tres
veces, y para poder pararla si no cuadra.

Viven fuera de `diseno.py` porque son un asunto entero y porque aquel fichero
llegó a su techo de 300 líneas. La regla de la casa: una cosa nueva no añade un
fichero al lado, saca uno. Salieron éstas, que ya estaban agrupadas bajo su
propio encabezado.
"""
from .aguja import Aguja
from .piezas import Clave

NIVEL_PIEZA = (
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
              dispara=(Aguja("scripts/servicios/disenar.py", 'return devuelve(pieza, "diseño · la escena no cuadra:", por_que)',),),
              efecto="devuelve la escena al compositor, con tiquet, si no cuadra (C-387)",
              obligatoria=True,
              lista=("monta", "rota"),
              nota="El que monta también puede parar: tres tableros seguidos con"
                   " la misma forma, o el oro gastado en todo, no es un defecto de"
                   " un tablero — es de la pieza, y no se ve mirando uno."),
    Clave("portada",
              dispara=(Aguja("scripts/servicios/portada.py", "def guardar(slug, respuesta):"),
                       Aguja("scripts/servicios/disenar.py", "    _portada(pieza.slug, respuesta)"),
                       Aguja("scripts/publicar.py", "subir(png, os.path.join(raiz, f\"{pieza}-portada.png\"), seco)"),),
              efecto="la imagen que se ve ANTES de darle al play",
              obligatoria=True,
              nota="**Lo único que se ve sin reproducir, y no lo tenía nadie.**"
                   " Jaime, 16-9-2026: *«no me dejaste la portada»*, y dónde"
                   " vive la decisión: *«inclúyela en el contrato del"
                   " diseñador»*. Hasta entonces sólo la tenía reel-13, hecha a"
                   " mano — que es lo que pasa con un dato que tiene lector"
                   " (`reels-spec` lo lee de `frames.json`) y no tiene"
                   " contrato: nadie lo produce.\n\n"
                   "                   Cuatro campos. `titulo` y `subtitulo`"
                   " salen del libreto y de su rótulo declarado: **no se"
                   " inventan**, y la portada es donde más tienta hacerlo"
                   " porque es lo único que se ve antes del play. `en` es el"
                   " segundo del MONTAJE, elegido de entre los que ya mira en"
                   " `documento`; el fichero lo saca la máquina del"
                   " bruto —3840×2160 contra los 1080 del corte, así que"
                   " acercarse no lo deshace— porque él trabaja con Read y"
                   " Write y no puede exportar una imagen. Y `por_que`, como"
                   " todo lo demás.\n\n"
                   "                   Y puede variar de una pieza a otra:"
                   " Jaime, el mismo día, *«la portada puede ser variable»*. La"
                   " de reel-13 —su cara, el rótulo en oro y una línea debajo—"
                   " es una forma que funcionó, no la única.\n\n"
                   "                   **Y desde el 20-10-2026 es obligatoria.**"
                   " Jaime, viendo FINALES: *«eso debe salir siempre con todos"
                   " los videos»*. Si una pieza llega a publicarse sin ella,"
                   " `publicar.py` la encarga al diseñador y no la sube (C-618)."),
)
