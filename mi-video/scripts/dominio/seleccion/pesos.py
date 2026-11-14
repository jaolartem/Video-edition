"""Los números con los que se corta, juntos y a la vista.

**Por qué tienen fichero propio.** Estaban en la cabecera de `seleccionar.py`,
noventa líneas antes de la primera función y mil quinientas antes del final, y
por eso pudo pasar esto:

- `PESO_CUELGA` valía **0,5** contra un `PESO_CUBRE` de 2,0, así que una ventana
  que empezaba a mitad de frase perdía 0,2 y ganaba hasta 2,0 por cubrir:
  cubrir compraba el corte. Al revisar el lote entero contra el libreto,
  **trece de las dieciocho roturas de argumento eran extremos partidos**. No
  eran dieciocho defectos: era este número.
- `PESO_REPE = 0.7` estuvo declarado y **nunca aplicado**. Un peso que no
  multiplica nada no avisa de que no multiplica nada; se lee en la cabecera, se
  cuenta en la documentación y no existe. Se ha ido.

Un número suelto dentro de una función es la misma avería en pequeño: los
márgenes de recorte —0,06 antes y 0,10 después— estaban escritos cinco veces a
mano, y el umbral de «esto es la misma frase», dos. Aquí se declaran una vez y
se dicen por su nombre.
"""
from __future__ import annotations


# ── qué es un enunciado ──────────────────────────────────────────────────────
#: Por debajo no hay enunciado, hay una palabra suelta.
MIN_VOZ = 1.8
#: Por encima no es una etapa, son varias.
MAX_VOZ = 26.0

# ── lo que suma ──────────────────────────────────────────────────────────────
#: **El mensaje manda sobre la ejecución.** Los castigos de extremo —costura,
#: cuelga, solape— suman hasta 1,5, y con la cobertura contando 1 borraban
#: diferencias de mensaje enormes: en el reel 1 ganó una ventana que cubre 0,22
#: frente a otra de 0,51 porque entraba más limpia. Un extremo sucio se recorta;
#: lo que no se dice no se recupera con nada.
PESO_CUBRE = 2.0
#: El dato declarado pesa más que el parecido con el párrafo.
PESO_DICE = 0.6

# ── lo que resta ─────────────────────────────────────────────────────────────
#: Por segundo de silencio interno. El silencio se descuenta, no se prohíbe: una
#: pausa de pensar es aceptable, treinta segundos de nada no.
PESO_AIRE = 0.03
#: Un extremo es limpio si detrás hay un hueco de verdad. La frontera sale de
#: los datos: de los 885 huecos medidos del lote, p70 = 1,29 s y p80 = 2,58 s —
#: ahí están las dos poblaciones, la pausa de pensar y el final. Por debajo de
#: esto la ventana está cortando dentro de una frase, que es de donde salió
#: «...preguntado al contador por».
COSTURA = 1.3
PESO_COSTURA = 0.45
#: Por debajo de esto el hueco es respiración, no frontera: la idea sigue del
#: otro lado aunque el detector de silencio marque un tramo. Medido sobre las
#: pausas de estas seis cintas.
PAUSA_IDEA = 0.55
#: Un hueco grande no garantiza que ahí acabe la idea. En el reel 3 hay 3,79 s
#: de silencio tras «...preguntado al contador por» y lo que viene después es
#: «al contador por qué y es que...»: Jaime se paró y **reempezó la frase**. Eso
#: no lo ve la pausa; lo delata que la cola de la ventana reaparezca al
#: principio del tramo siguiente. Lo mismo al revés — «de más, usted ya lleva
#: años pagando de más» empieza con la cola de la idea anterior.
PESO_SOLAPE = 0.55
#: Palabras de contenido que se comparan en cada extremo.
COLA = 4
#: **Un extremo roto cuesta más que lo que cubrir puede pagar.** A 2,6 una
#: ventana rota por un extremo pierde 1,3 y sólo gana si la alternativa cubre
#: mucho peor — que es exactamente cuándo se acepta un corte feo: cuando lo otro
#: no dice lo que hay que decir. Ver la cabecera: a 0,5 se comía trece cortes.
PESO_CUELGA = 2.6
#: Lo que cuesta comerse el arranque de la etapa siguiente. Va alto a propósito:
#: una ventana larga gana cobertura para SU etapa y deja a la de al lado sin
#: material — y una etapa obligatoria vacía rompe la estructura entera.
PESO_INVADE = 1.5

# ── quién llega a competir ───────────────────────────────────────────────────
#: Cobertura mínima para ser candidata; por debajo no dice la etapa.
UMBRAL = 0.14
#: Y ni con el dato declarado se rescata a quien no dice nada. **Contener la
#: cifra no es decir la etapa:** el reel 1 eligió «estructura. 30.000 dólares no
#: de ventas de estructura.» —cobertura -0,07— por llevar el «30» que la etapa
#: exige, y dejó fuera la tirada entera.
SUELO_DICE = 0.05

# ── lectura y voz ────────────────────────────────────────────────────────────
#: Por encima de esto la toma reproduce el libreto palabra por palabra: es
#: lectura. No descalifica —descalifica leer **sin voz**— pero cambia el camino.
LEIDA = 0.60
#: Y la voz que la salva. **3,4 y no 4,3: cambió la unidad.** El umbral estaba
#: calibrado sobre el recorrido de F0 en semitonos; ahora la medida es la
#: intensidad —distancia a la neutralidad de la cinta, sin signo— y vive en otra
#: escala. Dejar el número viejo mandó cuatro etapas a tablero por «lectura
#: plana» que no eran planas, entre ellas los ganchos del reel 3 y del reel 6.
#: Se recalibra al mismo percentil, no al mismo número: 4,3 era el p15 de la
#: escala vieja y 3,4 es el p15 de la nueva.
VOZ_SALVA = 3.4

# ── lo que cuesta dejar una etapa vacía ──────────────────────────────────────
#: **Dejar una etapa sin toma cuesta.** Sin esto, saltársela valía cero y la
#: cadena prefería vaciarla antes que aceptar una ventana floja: el reel 2 salía
#: con 3 etapas de 10 teniendo candidatas en siete. Y van a la MISMA escala que
#: la cobertura: al subir `PESO_CUBRE` a 2, dejar una etapa vacía se abarató a
#: la mitad y el reel 5 perdió una obligatoria. Un premio que no escala con lo
#: que compite no premia nada.
PREMIO = 1.2
PREMIO_OBLIG = 2.4

# ── las varas que estaban escritas a mano dentro de las funciones ────────────
#: Dos textos que comparten esta fracción de sus palabras de contenido **dicen
#: lo mismo**. Estaba escrito dos veces dentro de `sin_repetir`, que es la forma
#: exacta en que dos mitades de una regla se separan.
IGUALES = 0.72
#: Lo que se deja antes del ataque de la primera palabra al recortar, y lo que
#: se deja caer después de la última. Estaban escritos cinco veces.
ATAQUE = 0.06
CAIDA = 0.10
#: Holgura con la que una palabra se considera dentro de la ventana. Es la vara
#: del recorte —palabra **entera** dentro—, distinta a propósito de la del oído
#: (`Palabra.suena_en`, que admite media): al recortar se decide qué texto
#: queda, y media palabra no es texto que quede.
HOLGURA = 0.01
#: El hueco que se declara cuando no hay vecino: no es que no haya silencio, es
#: que no hay nada que medir. Estaba escrito como `9.9` en cuatro sitios.
LEJOS = 9.9
#: Con cuánta holgura el centro de una palabra se cuenta dentro de un tramo de
#: habla. El detector de silencio y el modelo no miden lo mismo, y sin este roce
#: las palabras de los bordes no caen en ningún tramo.
ROCE = 0.25
#: Palabras de contenido mínimas para que un trozo sea un enunciado y no un
#: resto. Estaba escrito como `< 3` dentro del bucle que construye ventanas.
CONTENIDO_MIN = 3
#: Nunca se deja una ventana con menos de esto al recortarle los extremos: por
#: debajo deja de ser un enunciado. Estaba escrito como `< 4` y `> 3` en la
#: misma función, que son el mismo número dicho de dos maneras.
SUELO_PALABRAS = 3
#: Por debajo de esto no se busca repetición dentro: no cabe.
SUELO_PODA = 8
#: Y al partir por una repetición, lo que tiene que quedar a cada lado para que
#: los dos trozos sigan siendo frases.
POR_DELANTE = 2
POR_DETRAS = 4

