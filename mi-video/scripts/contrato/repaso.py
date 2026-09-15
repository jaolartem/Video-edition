"""5 · REPASO — el control de calidad del corte, que ya no corta.

**Por qué es un contrato aparte, y antes no lo era.** `repasado` vivía dentro del
contrato de CORTE, como el tercero de tres momentos de la misma pregunta —«¿el
corte dice lo que tiene que decir, entero y una sola vez?»—. Dejó de serlo el 1
de septiembre, cuando Jaime le quitó las tijeras:

> *«Que repasar revise los cortes y el sonido, nada más. Que revise que estén
> bien, y si no, que lo devuelva con ticket al anterior.»*

Y el porqué, en la misma conversación:

> *«No podemos tener un reproceso en un repaso.»*
> *«Ya hubo una revisión anterior. La IA no es determinista, siempre va a
> encontrar opiniones distintas dependiendo del enfoque, pero no vamos a parar
> hasta que exista un producto perfecto: eso no existe.»*

Los otros dos momentos de CORTE **proponen y aplican**: cortan, mueven tramos,
declaran. Éste ya no. Devuelve tickets con un segundo, la pieza vuelve una vez al
paso que cosió, y **no se vuelve a preguntar**: los tickets los cierra la máquina
midiendo con `bordes_sucios`, que es el mismo detector que ve una palabra
partida y no cuesta un token.

Medido antes de este cambio: 34 vueltas de IA gastadas en tres pasos y **20
respuestas terminadas y tiradas** por llegar desfasadas. Un contrato que
comparte esquema con dos pasos que sí editan no puede expresar «este no edita»,
y por eso el reproceso no se veía: estaba declarado como normal.
"""
from .aguja import Aguja, Prompt
from .comun import CUMPLIMIENTO
from .piezas import Campo, Clave, Contrato, Momento, Repeticion

CAMPOS = (
    Campo("montaje",
          manda=Aguja("scripts/servicios/repaso.py", "filas = redundancia.dossier(pieza.slug)"),
          exige=(Prompt("scripts/repaso.prompt.md", "Miras el montaje trozo a trozo"),),
          nota="Lo único que se juzga. Es también lo único que invalida una"
               " respuesta ya dada: ver `servicio.CONTEXTO`."),
    Campo("onda",
          manda=Aguja("scripts/servicios/repaso.py", "curva = consulta.onda(pieza.slug)"),
          exige=(Prompt("scripts/repaso.prompt.md", "Está medido sobre la onda"),),
          condicional="si la consulta falla llega []",
          si_falta=Prompt("scripts/repaso.prompt.md", "Si `onda` llega vacía"),
          nota="La mitad de «suena bien». El texto da palabras; un trozo con"
               " cinco segundos mudos dentro se lee como una frase entera."),
    Campo("lo_que_cambio",
          manda=Aguja("scripts/servicios/repaso.py", 'cambio = Vuelta("repaso", pieza.slug, filas,'),
          exige=(Prompt("scripts/repaso.prompt.md", "Sólo miras lo que cambió"),),
          condicional="vacío en la primera vuelta, y entonces se mira todo",
          nota="Lo que hace que la vuelta 2 no sea la vuelta 1 otra vez. Trae"
               " las etapas cambiadas, las que cambiaron sin pedirlo, la huella"
               " de las quietas y la suerte de lo que se pidió."),
)

CLAVES = (
    Clave("beat",
          dispara=(Aguja("scripts/servicios/repaso.py", 'tipo = str(x.get("tipo") or "corte")'),),
          efecto="coloca el ticket en su etapa",
          nota="No obligatoria: un ticket sin etapa sigue siendo un ticket, y"
               " `ticket.beat_en` lo recoloca desde el segundo en cada corrida."),
    Clave("segundo",
          dispara=(Aguja("scripts/dominio/reloj.py", "def beat_en(pieza, segundo):"),),
          efecto="traduce a la etapa donde cae hoy, aunque el corte cambie",
          nota="El segundo de la pieza MONTADA, que es lo que se ve. Es el dato"
               " que hace utilizable la objeción: sin él hay que volver a"
               " buscar dónde pasaba."),
    Clave("dijo",
          dispara=(Aguja("scripts/dominio/ticket.py", "def abrir(pieza, dijo, segundo=None, tipo=\"objecion\","),),
          efecto="abre el ticket con el texto tal cual",
          obligatoria=True,
          nota="Sin texto no hay ticket: `abrir` lo salta. Describe el EFECTO"
               " —qué oye quien mira la pieza—, no la solución."),
    Clave("tipo",
          dispara=(Aguja("scripts/servicios/repaso.py", 'if tipo not in ("corte", "suena", "dato"):'),),
          efecto="`corte` y `suena` devuelven la pieza al paso que cosió;"
                 " `dato` sólo se anota para Jaime y no la para",
          sin_valor="corte",
          nota="La diferencia importa: `dato` es lo que este paso ve y NO es su"
               " trabajo. Se dice una vez y no se corta."),
    Clave("por_que",
          dispara=(Aguja("scripts/servicios/repaso.py", 'porque = str(x.get("por_que") or "")[:400]'),),
          efecto="se pega al texto del ticket, para el paso que lo arregla",
          adjunta_a="dijo",
          nota="De dónde viene el fallo. Es lo que convierte un rescate en un"
               " arreglo: sin ello, el paso que cose vuelve a cometerlo."),
)

REPASO = Contrato(
    paso="repaso",
    prompt="scripts/repaso.prompt.md",
    unidad="ticket (uno por cosa que suena mal, con su segundo)",
    llave="segundo",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/servicio.py", "def recoger(",
                 pendiente="validar la respuesta contra contratos.por_paso(paso)"
                           " antes de devolverla"),
    momentos=(
        Momento("repasado", 6.5,
                trae=("montaje", "onda", "lo_que_cambio"),
                no_trae=("candidatas", "historial", "libreto", "se_ve"),
                nota="Último punto donde el texto está cerrado. Y el único paso"
                     " de IA que NO edita: mira, y si algo suena mal lo devuelve"
                     " al que lo hizo."),
    ),
    campos=CAMPOS,
    claves=CLAVES,
    bloques=(CUMPLIMIENTO,),
    repite=Repeticion(
        vuelve_a="cosido",
        cuenta=Aguja("scripts/servicios/repaso.py", "def _ya_pregunto(slug: str) -> bool:"),
        tope=1,
        puerta=Aguja("scripts/servicios/repaso.py", "def _cerrar_tickets(pieza)"),
        pasa_si=("no se abrió ningún ticket de corte ni de sonido",
                 "o los que se abrieron ya no se miden como bordes sucios"),
        no_pasa_por=("un ticket que no se puede medir: se queda abierto y viaja"
                     " con la pieza hasta Jaime",),
        contadores=("abiertos", "para_jaime", "cerrados", "quedan"),
        nota="**Tope 1, y es el punto entero.** Se pregunta una vez por pieza."
             " Cuando la pieza vuelve, `_cerrar_tickets` comprueba MIDIENDO, no"
             " preguntando. Un segundo pase de IA sobre un corte que acaba de"
             " cambiar no confirma nada: encuentra otra opinión.",
    ),
)
