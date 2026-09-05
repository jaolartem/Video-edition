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
