"""La parte FIJA del contrato del disenador: las reglas de la marca.

Jaime, definiendo la forma del contrato: *«el contrato del disenador tiene
dos partes: una variable, que es la que da el compositor, y otra fija, que
son las reglas de la marca personal»*.

Vive aparte de `diseno.py` porque es **prosa que no cambia con los campos**:
el fichero de al lado declara que se pide y quien lo lee, y esto declara
como se ve la marca. Mezclados, cada campo nuevo empujaba el techo de 300
lineas contra un texto que no tenia por que moverse.
"""
from .piezas import Bloque

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


#: **Sus palabras sobre la marca, donde vive la marca.**
#:
#: Jaime, 10-9-2026, sobre las tres frases que estaban en
#: `servicios/disenar.py` con la clave literal `"jaime"`: *«son parte del
#: contrato de marca»*.
#:
#: Estaban alli porque el pedido del disenador las lleva en `datos.estilo`,
#: `datos.prioridad` y `datos.entrada_gancho` — y el resultado eran **dos copias
#: de la marca**: este fichero por un lado y tres literales por otro, cada uno
#: creciendo por su cuenta. Y ademas indexadas por un nombre propio: el dia que
#: entre otra persona, `"jaime"` no cambia — se rompe.
#:
#: La clave dice **de que hablan**, no quien las dijo. Quien las dijo esta en
#: `persona.marca`, que apunta a este fichero.
PALABRA = {
    "estilo": "Respeto por la cuadricula si, pero tambien irrespeto con"
              " criterio. Manejo de la forma si, pero tambien encuadres"
              " caoticos. Mucho color: NO HAY PROHIBICIONES DE COLOR, hay"
              " prohibiciones de coherencia y composicion.",
    "prioridad": "El disenador puede respetar el tablero o no; debe primar la"
                 " reduccion de la carga cognitiva para el espectador, la"
                 " coherencia visual y el objetivo emocional, en ese orden."
                 " MUCHO MOVIMIENTO, MUCHA DOPAMINA.",
    "gancho": "espero animaciones mucho MAS FUERTES en todos los hooks: letras"
              " que entran DETRAS de mi cara y se acomodan, movimientos de"
              " subtitulos, cosas llamativas, con muchos efectos",
}


# ── El encargo de estilo, la prioridad y el gancho ──────────────────────
#
# Jaime, 10-9-2026: *«son parte del contrato de marca»*, y *«una vez algo
# queda hecho y en catalogo, el sistema queda actualizado y esa
# herramienta le sirve a todos»*.
#
# Estaban en `servicios/disenar.py`, que es el motor del paso: viajaban en
# su pedido como `datos.estilo`, `datos.prioridad` y `datos.entrada_gancho`.
# Declaracion dentro del motor — la mezcla que este mismo paquete existe
# para deshacer— y ademas dejaba el fichero clavado en el techo de 300.
# Aqui son contrato, y desde aqui las puede pedir cualquier paso.

#: El encargo de estilo. **No es una lista de prohibiciones**: eso es lo que
#: habia y produjo minimalismo corporativo, porque lo unico que no estaba
#: prohibido era no hacer nada.
ESTILO = {
    "que_es": "Neoconstructivista: el nieto millennial o alfa del constructivismo ruso. Emparentado con lo corporativo, pero lejos de el.",
    "la marca": PALABRA["estilo"],
    "la_vara": "Queremos dejar la sensacion de wow, y eso se consigue haciendonos entender. Un tablero que solo se lee no cumple; uno que se entiende de un vistazo, si.",
    "el_tablero_es": "Fundamentalmente IMAGEN, no texto. Es un elemento didactico, igual que el panel. Si lo que compones se puede leer en voz alta y no se pierde nada, no es un tablero: es un rotulo.",
}

#: Cuando dos criterios chocan, gana el de mas arriba. Palabras de Jaime.
PRIORIDAD = {
    "1_carga_cognitiva": "Reducir lo que el espectador tiene que procesar. Si el tablero propuesto obliga a leer tres cosas para entender una, se cambia.",
    "2_coherencia_visual": "Que la pieza se vea de una sola mano y del canon de las 26 laminas.",
    "3_objetivo_emocional": "Que la etapa deje la emocion que le toca.",
    "la marca": PALABRA["prioridad"],
    "y_si_lo_cambias": "Dilo en `por_que`: que proponia el encargo, que compusiste y por cual de los tres criterios.",
}

#: Lo que el gancho tiene que cumplir, y lo comprueba `gancho.mjs`.
ENTRADA_GANCHO = {
    "entradas_minimo": 6,
    "por_que": "el primer segundo decide si alguien sigue mirando; el maximalismo aqui es DENSIDAD DE ENTRADAS, no adorno",
    "la marca": PALABRA["gancho"],
    # **Esto TODAVIA NO SE PUEDE.** Se ofrecia como si estuviera hecho y no
    # lo esta: `scripts/text-behind.py` saca el recorte del sujeto y
    # funciona, pero ningun paso del render lo consume. Es la avería que
    # Jaime nombro —*«que no quede otra vez el mismo error de declarar sin
    # implementar»*— en el mismo bloque donde la nombro. Vive en
    # `camara.por_construir`, que es donde se piden las cosas que cuestan
    # codigo, y aqui se dice lo que hay.
    "letras_detras": "POR CONSTRUIR, no lo compongas como si estuviera: el rotulo naciendo detras de la cara es lo que mas subiria el gancho y hoy no hay capa que lo dibuje. Si tu gancho lo pide, pidelo en `por_que` y se agenda. Ver `camara.por_construir`.",
    "el_subtitulo_se_mueve": "En el gancho el subtitulo no solo aparece: entra, se asienta, acompana. Fuera del gancho se queda quieto.",
    "exige": "una figura dibujable declarada o una composicion tipografica; no vale prosa, porque nadie la dibuja",
    "prohibido": "rebote, confeti, wiggle y cualquier micro-animacion juguetona: esto es un asesor financiero hablando a duenos de negocio. Fuerte no es gracioso.",
}
