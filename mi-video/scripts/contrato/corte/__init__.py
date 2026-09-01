"""1 · CORTE — el paso que se repite hasta que pase.

Aquí se colapsan `sin_redundancia` (5) y `revalidado` (5.5). No son dos pasos:
son la misma pregunta —¿el corte dice lo que tiene que decir, entero y una sola
vez?— hecha en dos puntos donde el corte ya cambió, con dos esquemas que no se
parecen y que por eso se contradicen:

  · redundancia ve `antes`/`despues` con sus segundos —los recibe desde
    ccef7c5— y su esquema sólo sabe cortar. Ve el borde roto y la única salida
    que tiene es cortar más.
  · revalidar puede mover tramos y no puede decir de qué cinta son.
Y las dos cuentan «pasa» distinto. Un contrato, dos momentos.

**Y `repasado` (6.5) estuvo aquí y ya no está.** Era el tercero de los tres, y
salió el 1 de septiembre cuando dejó de editar: ahora mira y devuelve tickets,
que es otra pregunta y otro esquema. Está en `contrato/repaso.py`, y sacarlo es
la mitad de por qué el reproceso se ve — un paso que no corta no cabe en un
contrato cuyas claves son todas formas de cortar.

Aquí quedan los tres momentos y cómo se repite, que es lo propio de este paso.
Lo que viaja está en `pedido.py` y lo que se contesta en `respuesta.py`: es el
único de los cuatro contratos que no cabe en un fichero, precisamente porque
colapsa tres fases y lleva el triple de campos.
"""
from ..aguja import Aguja
from ..comun import CUMPLIMIENTO, REDUNDANCIA
from ..piezas import Contrato, Momento, Repeticion
from .pedido import CAMPOS
from .respuesta import CLAVES

CORTE = Contrato(
    paso="corte",
    prompt="scripts/corte.prompt.md",
    unidad="trozo de montaje (una fila por trozo del EDL, en orden de montaje)",
    llave="beat",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/servicio.py", "def recoger(",
                 pendiente="validar la respuesta contra contratos.por_paso(paso)"
                           " antes de devolverla; hoy el docstring promete «la"
                           " valida contra el esquema del paso» y hace json.load"),
    momentos=(
        Momento("sin_redundancia", 5.0,
                trae=("montaje", "texto", "antes", "despues", "voz", "tono"),
                no_trae=("se_ve", "onda", "candidatas", "historial"),
                nota="Sobre el corte recién depurado: es cuando la repetición es"
                     " más barata de quitar."),
        Momento("revalidado", 5.5,
                trae=("candidatas", "historial", "saltos", "flojo", "intensidad"),
                no_trae=("se_ve",),
                nota="`escena_desc` todavía no existe —`descrito` es la 7—, así"
                     " que aquí no se puede decidir nada que se escriba ahí. Es"
                     " el no-op de `compone`, que cuenta como aplicado y toca"
                     " cero filas."),
    ),
    campos=CAMPOS,
    claves=CLAVES,
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=Repeticion(
        vuelve_a="cosido",
        cuenta=Aguja("scripts/avanzar.py", 'atras.setdefault(siguiente["nombre"], []).append('),
        tope=3,
        puerta=Aguja("scripts/verificar.py", "def revisar("),
        pasa_si=("propuestos == 0",
                 "sube == 0",
                 "pieza.veredicto == 'limpia'",
                 "la puerta no devuelve motivos"),
        no_pasa_por=("aplicados == 0",),
        contadores=("propuestos", "aplicados", "no_aplicados", "sube"),
        nota="`no_aplicados` —anclas que no resuelven, tramos que `declarar`"
             " rechaza, bordes sin toma— NO es silencio: es el peor caso, y hoy"
             " se cuenta igual que la pieza limpia. Sube.",
    ),
)
