"""3 · RESPALDO — fuentes, que además deja de ser un script que nadie llama.

`fuentes.py` no está en `CICLO` ni en la tabla `fase`, y no lo llama
`pipeline.sh` ni ningún otro script. Un paso de cumplimiento que no corre es
peor que no tenerlo: `reels-spec.mjs` deja el literal escrito a mano cuando no
hay `respalda='si'`, así que la ausencia se ve exactamente igual que el éxito.
"""
from .aguja import NADIE, Aguja, Prompt
from .comun import CUMPLIMIENTO, REDUNDANCIA
from .piezas import Campo, Clave, Contrato, Momento

RESPALDO = Contrato(
    paso="fuentes",
    prompt="scripts/fuentes.prompt.md",
    unidad="cifra en pantalla",
    llave="etapa",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/servicio.py", "def recoger(",
                 pendiente="misma validación que los demás pasos"),
    momentos=(Momento("respaldado", 7.5,
                      trae=("grafico", "trato"),
                      nota="Después de `descrito` porque necesita `grafico`, y"
                           " antes de `cortado` porque `respalda='si'` es lo que"
                           " enciende el pie del tablero."),),
    campos=(
        Campo("etapa",
              manda=Aguja("scripts/fuentes.py", '"etapa": f["orden"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "el número de etapa donde sale"),)),
        Campo("libreto",
              manda=Aguja("scripts/fuentes.py", '"libreto": f["libreto"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "lo que decía el libreto"),)),
        Campo("trato / grafico",
              manda=Aguja("scripts/fuentes.py", '"grafico": f["grafico"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "qué se va a dibujar"),),
              nota="Una cifra dibujada pesa más que una dicha: la del tablero se"
                   " queda en pantalla y se puede congelar y compartir."),
        Campo("cifras",
              manda=Aguja("scripts/fuentes.py", "for m in CIFRA.finditer(texto)"),
              exige=(Prompt("scripts/fuentes.prompt.md", "tal como sale en la pieza"),),
              nota="Derivada de un regex sobre libreto+grafico. El prompt pide la"
                   " cifra «tal como sale en la pieza» como si el modelo la"
                   " buscara, y `cargar` no comprueba que la devuelta estuviera"
                   " en la lista: en `dato` hay filas —«la mitad (50%)», «sin"
                   " cifra en pantalla (rotulo COMISION)»— que el regex no mandó."),
        Campo("dicho",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/fuentes.prompt.md", "tal como sale en la pieza"),),
              nota="EXIGIDO Y NO ENVIADO. Una cifra dicha y no rotulada no llega:"
                   " el propio `dato` id 6 lo registra —«en la toma se dice hasta"
                   " 550 dólares»— y esa cifra no estaba en el payload."),
        Campo("slug",
              manda=None,
              deuda="ver `nota`",
              exige=(),
              nota="NO ENVIADO Y NECESARIO: está en el `.pedido.json` y `_por_cli`"
                   " concatena sólo `prompt` + `datos`. El modelo no ve de qué"
                   " reel es lo que juzga."),
        Campo("provincia",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/fuentes.prompt.md", "provincia, tipo"),),
              nota="EXIGIDO Y NO ENVIADO. Va fijada como Ontario en el texto del"
                   " prompt, no como dato de la pieza — o sea, un `if (slug ===`"
                   " escrito en prosa."),
        Campo("caso_real",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/fuentes.prompt.md", "si no consta que sea real"),),
              nota="EXIGIDO Y NO ENVIADO. Ningún campo dice si el electricista de"
                   " Brampton está documentado; el modelo lo deduce del libreto."),
        Campo("ya_guardado",
              manda=None,
              deuda="ver `nota`",
              exige=(),
              nota="NO ENVIADO Y NECESARIO: el upsert sobrescribe, y en la base hay"
                   " filas de la misma pieza con fechas distintas y veredictos"
                   " distintos. Sin ver lo anterior no se puede saber si esto es"
                   " una corrección o una regresión."),
    ),
    claves=(
        Clave("etapa",
              dispara=(Aguja("scripts/reels/cifras.mjs", ".filter((r) => r.etapa == null || Number(r.etapa) === Number(beat))"),),
              efecto="engancha el pie al beat",
              obligatoria=True,
              nota="Si falta o no es número entra como 0: la fila se guarda, no"
                   " engancha con ningún beat y no salta nada."),
        Clave("cifra",
              dispara=(Aguja("scripts/fuentes.py", "insert into dato (video_id, etapa_orden, cifra, afirmacion,"),),
              efecto="parte de la clave única del dato y desempate del pie",
              obligatoria=True,
              nota="Se lee por índice, no con `.get`: si falta, KeyError a mitad"
                   " del bucle y se pierde la carga entera porque el commit es al"
                   " final."),
        Clave("principal",
              dispara=(Aguja("scripts/reels/cifras.mjs",
                             "const casan = filas.filter((f) => f.tokens.some((t) => pintadas.includes(t)));"),),
              efecto="cuál de las cifras de la etapa lleva el pie del tablero",
              nota="**La deuda que declaraba esta clave está pagada.** Decía"
                   " «ordenar por `principal` y no por longitud de la cadena», y"
                   " la longitud es lo que hacía: `order by length(d.cifra) desc`"
                   " elegía la fila cuyo texto ocupara más caracteres. En"
                   " reel-07 e3 eso saca «53.53% (corroboración independiente)»"
                   " debajo de un tablero que rotula 32 %. Ahora se busca la fila"
                   " cuya cifra APARECE en lo que el tablero pinta, y si no se"
                   " puede saber manda la que más necesita el pie: una proyección"
                   " (`respalda='parcial'`) tiene condiciones que hay que decir."),
        Clave("fuente",
              dispara=(Aguja("scripts/reels/cifras.mjs", "export function pieDe(slug, b, faltas) {"),),
              efecto="el pie del tablero en pantalla, sólo si `respalda='si'`",
              nota="El upsert es por `rotulo` UNIQUE: dos fuentes distintas con el"
                   " mismo rótulo se funden en una fila."),
        Clave("condiciones",
              dispara=(Aguja("scripts/reels/cifras.mjs", "export function pieDe(slug, b, faltas) {"),),
              efecto="`props.condicion` del tablero",
              nota="Prosa larga de comprobación entrando directa a un pie: en la"
                   " base hay `condiciones` de 400+ caracteres. O se corta aquí"
                   " con su límite declarado, o llega a pantalla."),
        Clave("respalda",
              dispara=(Aguja("scripts/reels/cifras.mjs", '.filter((f) => f.respalda === "si" || f.respalda === "parcial")'),
                       Aguja("scripts/fuentes.py", "def sin_respaldo(slug):")),
              efecto="enciende el pie y alimenta el listado de sin respaldo",
              obligatoria=True,
              lista=("si", "parcial", "no", "sin_fuente"),
              exige_ademas=("sube",),
              nota="`no` y `sin_fuente` caen en el mismo cubo y ninguno para nada,"
                   " y el propio prompt dice que `no` sube a Jaime. `parcial` es"
                   " invisible por los dos lados: no sale en el listado y no"
                   " imprime pie, así que el tablero se queda con el literal"
                   " escrito a mano sin que nadie lo vea. Por eso `respalda`"
                   " exige `sube`."),
        Clave("marcar_como",
              dispara=(Aguja("scripts/reels/cifras.mjs", "export function pieDe(slug, b, faltas) {",
                             pendiente="rotular HIPOTÉTICO / EJEMPLO en el tablero"
                                       " cuando el caso no está documentado"),),
              efecto="marca el caso en pantalla",
              lista=("real", "hipotetico", "ejemplo"),
              nota="Es cumplimiento —prioridad 1— y hoy sólo cabe como prosa"
                   " dentro de `condiciones` o `nota`."),
        Clave("rotulo_falso",
              dispara=(Aguja("scripts/servicio.py", 'PARAN = ("sube", "rotulo_falso")'),
                       Aguja("scripts/verificar.py", "for n in Nota.subidas(slug):")),
              efecto="para la pieza: nota `sube` y la puerta no deja pasar",
              nota="Registrado en `dato` id 4: «COMISION» donde la fuente dice"
                   " tarifa de gestión anual. La cifra se sostiene y el rótulo"
                   " miente, y no había clave para decirlo."),
        Clave("deriva_de",
              dispara=(Aguja("scripts/reels/cifras.mjs", "export function pieDe(slug, b, faltas) {",
                             pendiente="una cifra derivada hereda el pie de la"
                                       " cifra de la que sale"),),
              efecto="la cifra derivada comparte el pie de su origen",
              nota="`dato` id 6: 576 = 30.000/52, «el pie tiene que ser el mismo"
                   " que el de los 30.000». `fuente` es cadena o null y no puede"
                   " apuntar a otro `dato`."),
        Clave("afirmacion",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE: columna NOT NULL de la tabla, el sitio donde se explica"
                   " qué afirma la pieza, y ningún paso la lee. Es candidata a ir"
                   " al payload del corte con `datos_respaldados`."),
        Clave("organismo / url / vigencia / cita",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTES las cuatro. `url` es la prueba de «una URL que no"
                   " abriste no se declara comprobada» y no la comprueba ningún"
                   " paso ni la muestra ninguna pantalla; `vigencia` existe porque"
                   " «una tasa sin año caduca en silencio» y no hay guarda que la"
                   " compare con la fecha del render."),
        Clave("nota",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE, y es donde acaba todo lo que el esquema no tiene clave"
                   " para decir: rótulos falsos, riesgo reputacional, caducidades."
                   " El campo que más recibe y menos se lee. Se vacía repartiendo"
                   " su contenido en `rotulo_falso`, `marcar_como` y `sube`."),
    ),
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=None,
)
