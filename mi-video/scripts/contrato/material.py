"""4b · Lo que el diseñador manda sobre el MATERIAL, no sobre el tablero.

Dos familias y el mismo motivo: son decisiones sobre la toma —cómo es el plano
de debajo y qué se lee de lo que se oye—, no sobre el gráfico que va encima. Las
claves de `diseno.py` dicen **qué se dibuja**; éstas, **sobre qué**.

Jaime, al leer `docs/composicion.md`: *«dale herramientas al diseñador para que
pueda tocar todo eso, que no quede otra vez el mismo error de declarar sin
implementar, que ha sido la constante en este proyecto»*. O sea: al ver un
documento que nombra tipos de plano y transiciones sin que hubiera por dónde
pedirlos.

Vive aparte de `diseno.py` porque es otra responsabilidad. Las claves de allí
dicen **qué se dibuja encima**; éstas dicen **cómo es el plano de debajo** —de
qué habla el encuadre, cómo se mueve, qué media la costura—, y eso ya existía
en código antes de que nadie pudiera pedirlo.

**El vocabulario no se escribe aquí.** `scripts/camara.mjs` lo lee de quien lo
ejecuta —los cinco encuadres salen del propio `punch-ins.py`— y `--comprobar`
abre las líneas que lo consumen: un verbo ofrecido sin implementar sale como
fallo, que es la avería que estas tres claves vienen a cerrar y no a repetir.
Las listas de abajo son lo único duplicado, y son las que `contratos.py`
compara.
"""
from .aguja import Aguja, Prompt
from .piezas import Campo, Clave

#: Las tres, en el orden en que se componen: primero de qué habla el plano,
#: luego cómo se mueve, y por último cómo se entra en él.
CAMARA = (
    Clave("camara.encuadre",
              dispara=(Aguja("scripts/plan-reel.mjs", "encuadre: cam.encuadre,"),
                       Aguja("scripts/punch-ins.py", 'pedido = e.get("encuadre")'),),
              efecto="de qué habla el plano de esa etapa",
              lista=("completo", "medio", "pecho", "primer plano", "primerisimo"),
              sin_valor="se reparten en rueda",
              nota="**Los cinco llevaban construidos desde el principio.**"
                   " `punch-ins.py` saca cinco encuadres del mismo 4K —recortar"
                   " no cuesta nitidez con 2× de margen— y los repartía con"
                   " `ENCUADRES[idx % len]`: cinco planos hechos y ninguno"
                   " elegible, así que un primer plano caía donde tocara y no"
                   " donde la etapa lo pedía. La lista sale de `camara.mjs`, que"
                   " la lee del cropper: el menú no puede prometer un recorte"
                   " que no se sepa hacer."),
        Clave("camara.movimiento",
              dispara=(Aguja("scripts/plan-reel.mjs", "zoom: movimientoDe(cam.movimiento),"),
                       Aguja("scripts/camara.mjs", "export const movimientoDe = (nombre) => {"),),
              efecto="cómo se mueve el cuadro dentro de la escena, sin cortar",
              lista=("acercar", "entrar", "alejar", "quieto"),
              sin_valor="acercar",
              nota="Estaba clavado en 0,88 para las escenas de las siete piezas."
                   " La calibración es buena —no se nota mientras pasa y sí al"
                   " comparar el principio con el final— pero era la misma en el"
                   " gancho, en la explicación y en el cierre, y un movimiento"
                   " único no es tener movimiento. `acercar` sigue siendo ese"
                   " 0,88, así que lo no declarado sale igual que ayer."),
        Clave("camara.transicion",
              dispara=(Aguja("scripts/reels-spec.mjs", "cortinillas: cortinillasDe(slug, reloj, marco),"),
                       Aguja("scripts/reels/capas.mjs", "export function cortinillasDe(slug, reloj, marco) {"),
                       Aguja("scripts/reels/imagen.mjs", "export function filetesDe(reloj) {"),
                       Aguja("src/components/Filete.tsx", "export const Filete: React.FC<{"),),
              efecto="qué media la costura de entrada de esa etapa",
              lista=("corte", "glitch", "filete"),
              sin_valor="corte",
              nota="El componente escrito, el hueco en el spec y `Reel.tsx`"
                   " dibujándolo — y `cortinillas: []` fijo desde que se"
                   " probaron en TODAS las costuras y quedaron mal. La"
                   " conclusión correcta era «no en todas»; la que se aplicó fue"
                   " «en ninguna», y con ella se perdió la pieza entera. Una"
                   " máscara que se pone siempre deja de ser máscara; una que no"
                   " se puede poner nunca no es una decisión, es una ausencia."
                   " `filete` es la tercera vía, y es la que Jaime pidió por su"
                   " nombre: *«que haga una animación en esa transición»*."),
        Clave("camara.virado",
              dispara=(Aguja("scripts/plan-reel.mjs", "virado: cam.virado,"),
                       Aguja("scripts/reels/imagen.mjs", "export function viradosDe(reloj) {"),
                       Aguja("src/Ad.tsx", "const virado = virados.find("),),
              efecto="con qué color sale el plano de esa etapa",
              lista=("sepia", "navy", "duro"),
              sin_valor="el plano sale como se grabó",
              nota="Jaime: *«que me ponga en sepia… ya tiene más herramientas de"
                   " diseño, está muy mediocre el diseñador»*. Lo único que"
                   " teñía el plano era `desatura` —el blanco y negro de la"
                   " marca de humanidad—, que **no es del diseñador**: lo coloca"
                   " `marcaDeHumanidad` pegado a la corrección de lo dicho. O"
                   " sea que el canon nombra el virado y no había por dónde"
                   " pedirlo. La familia sale del canon y no del gusto: paleta"
                   " oscura y desaturada con el oro como único tono vivo, así"
                   " que el virado dorado no entra —es oro decorativo— y el"
                   " blanco y negro tampoco, porque ya tiene dueño."),
)


#: Como suena el en el remate de una etapa. Misma familia que la camara y por
#: el mismo motivo: es una decision sobre el MATERIAL —la toma que se oye—, no
#: sobre lo que se dibuja encima.
VOZ = (
    Clave("voz.trato",
          dispara=(Aguja("scripts/servicios/disenar.py", 'if "voz" in t:'),
                   Aguja("scripts/dominio/remate.py", "def filtro(self, ventana) -> str:"),
                   Aguja("scripts/musica.sh", "VOZ=$(python scripts/dominio/remate.py"),),
          efecto="como suena la voz de Jaime en el remate de esa etapa",
          lista=("megafono", "cerca"),
          sin_valor="la voz sale sin tocar",
          nota="**La herramienta la pidio el y no existia.** Jaime: *«que"
               " cambie mi voz en los punchlines»*. No choca con *«no agregues"
               " efectos o mascaras al sonido, solo baja el volumen a esas"
               " frecuencias»*: aquello es de la MUSICA y de las bandas que"
               " compiten con la voz, y sigue vivo en `TALLA_BANDAS`. Esto va"
               " sobre un tramo declarado, lo pidio el, y **tiene que"
               " notarse**.\n\n"
               "                   Se aplica en `musica.sh`, que es donde viven"
               " las dos senales por separado — en Remotion la voz y la musica"
               " ya vienen sumadas y no hay nada que tratar aparte."),
    Clave("voz.sobre",
          dispara=(Aguja("scripts/dominio/remate.py", "def ventana(self, tramo) -> tuple:"),),
          efecto="donde cae la ventana dentro de la etapa",
          lista=("remate", "entrada"),
          sin_valor="remate",
          nota="No hay «la etapa entera» a proposito: un tratamiento que dura"
               " ocho segundos deja de marcar un remate y cambia el narrador."
               " La ventana se recorta DENTRO del beat, asi que no puede"
               " escaparse a la pista."),
    Clave("voz.dura",
          dispara=(Aguja("scripts/dominio/remate.py", "if not MINIMO <= self.dura <= TOPE:"),),
          efecto="cuantos segundos dura el tratamiento",
          sin_valor="1,2 s",
          nota="Entre 0,3 y 2,5 s. Por debajo la campana no se asienta y no se"
               " oye; por encima ya no es un remate. Fuera de ese rango la"
               " declaracion **se rechaza al guardarla y se dice**, en vez de"
               " quedarse en la base saliendo como falta en cada corrida."),
)


#: La correccion de lo dicho. Vive aqui y no en `diseno.py` por lo mismo:
#: no es un tablero, es una decision sobre la toma.
LO_DICHO = (
Clave("corrige",
          dispara=(Aguja("scripts/servicios/disenar.py", 'corr = t.get("corrige")'),
                   Aguja("src/components/captionBand/Corregida.tsx", "const { dice: palabra, es } = corrige;"),),
          efecto="pone la palabra buena donde suena la equivocada, y la"
                 " enfatiza",
          sin_valor="la voz se queda como está",
          nota="**La forma la fijó Jaime y excluye la nota al pie.** *«Sí se"
               " puede corregir en pantalla si queda explícito el error»*,"
               " *«pero explícito no es»* —de una línea en letra pequeña— y"
               " luego el cómo: *«no decir "
               "«acá hay un error», sino que el error se enfatice en el"
               " número bueno, o el nombre bueno»*, *«como con el ministerio"
               " de comercio»*. `Corregida` hace exactamente eso: la palabra"
               " mala se sustituye por la buena, que crece a 1,45x, se pone"
               " en oro y late tres golpes."),
)


#: Y el bloque del pedido que se lo explica. El campo va con su clave: si
#: viaja la instruccion y no hay donde declararla, es media herramienta.
CAMPOS = (
    Campo("placas",
          manda=Aguja("scripts/servicios/disenar.py", '"placas": placas_que_existen('),
          exige=(Prompt("scripts/disenar.prompt.md", "no es reinventar la rueda"),),
          nota="Las CATORCE placas de `public/fondos/` con lo que dibuja cada"
               " una y lo que provoca. Llevaban semanas en el repositorio y el"
               " diseñador no las había visto: el pedido mandaba las 26 láminas"
               " del canon —que son para mirar— y no las placas, que son las que"
               " se pueden usar. Jaime: *«que utilicen los fondos que ya existen,"
               " para generar texto encima de ellos, como lo muestran los"
               " ejemplos de carruseles; no es reinventar la rueda, es seguir la"
               " identidad gráfica»*, *«y que quede declarado el inventario»*."),
        Campo("voz",
          manda=Aguja("scripts/servicios/disenar.py", '"voz": voz_en_el_remate(),'),
          exige=(Prompt("scripts/disenar.prompt.md", "La voz en el remate"),),
          nota="Los dos tratos de voz que existen, con lo que suena cada uno,"
               " los limites de la ventana y lo que esta por construir. Se lo"
               " pide a `dominio/remate.py`, que es quien lo aplica: un menu"
               " escrito en el pedido seria la segunda copia de siempre, y"
               " ofreceria un sabor que la mezcla no sabe hacer. Jaime: *«que"
               " cambie mi voz en los punchlines»* — una herramienta que no"
               " esta en el pedido no existe para quien compone, que es lo que"
               " paso con los cinco encuadres y con las catorce placas."),
        Campo("correccion",
          manda=Aguja("scripts/servicios/disenar.py", '"correccion": CORRECCION,'),
          exige=(Prompt("scripts/disenar.prompt.md", "el número bueno se enfatiza"),),
          nota="Cómo se corrige en pantalla un dato que la voz dice mal."
               " El mecanismo llevaba construido desde el caso del"
               " ministerio de comercio —`Corregida` sustituye la palabra y"
               " enfatiza la buena— y su clave vivía en el contrato del"
               " COMPOSITOR: o sea en el único sitio donde no la tiene"
               " delante quien mira la cifra de la voz contra la"
               " respaldada."),
)
