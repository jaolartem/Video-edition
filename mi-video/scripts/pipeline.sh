#!/usr/bin/env bash
# El único camino. Un comando, todos los pasos, tantas veces como haga falta.
#
# Regla de Jaime: *«la idea es generar un sistema cerrado que tenga un solo
# camino y que repita los mismos pasos las veces que sean necesarias»*.
#
# Antes había nueve scripts y `montar.sh` encadenaba cuatro; el resto dependía de
# que alguien recordara el orden. Eso no es un pipeline, es una intención — y ya
# costó dos fallos: editar un EDL no regeneraba el plan (C-32) y la verificación
# describía el corte anterior porque nadie la llamaba (C-60).
#
# ## Lo que lo hace repetible
#
# **Cada paso decide solo si tiene que correr**, mirando el estado y no la
# memoria de nadie:
#
#   transcribir   salta la cinta que ya tiene su sello de varias pasadas
#   catalogar     salta la toma cuyas unidades ya están
#   seleccionar   corre siempre: es barato y depende de todo lo anterior
#   depurar       corre siempre: solo mira la elegida, cuesta segundos
#   describir     salta la escena ya descrita
#   cortar        salta el fragmento cuya huella no cambió
#   montar        regenera el plan si el EDL es más nuevo, y así en cadena
#
# Correrlo dos veces seguidas no rehace nada. Cambiar una cosa rehace **esa** y
# lo que dependa de ella. Eso es lo que convierte «corregir un segmento» en algo
# que cuesta un segmento y no un montaje.
#
# ## Y lo que no se salta nunca
#
# Las guardas van primero y **paran el lote**: si una corrección perdió su
# mecanismo en una reescritura, mejor no montar seis piezas con el defecto
# dentro. Es barato —lee ficheros— y por eso va delante.
#
#   bash scripts/pipeline.sh            # los seis, de punta a punta
#   bash scripts/pipeline.sh 3          # solo el reel 3
#   bash scripts/pipeline.sh --sin-render   # hasta el corte, sin Remotion
set -uo pipefail
cd "$(dirname "$0")/.."

REELS=()
SIN_RENDER=0
for a in "$@"; do
  case "$a" in
    --sin-render) SIN_RENDER=1 ;;
    --*) ;;
    *) REELS+=("$a") ;;
  esac
done
[ ${#REELS[@]} -eq 0 ] && REELS=(1 2 3 4 5 6)

paso() { echo; echo "━━ $* ━━"; }
fallo=0
corre() {           # corre un paso y sigue: un paso caído no tumba el camino
  if ! "$@"; then
    echo "  (paso con fallo: $*)"
    fallo=1
  fi
}

paso "0 · guardas"
node scripts/guardas.mjs || exit 1

paso "1a · el barato: identificar TODO el material"
# **Todas las cintas, no los seis reels.** El corte cruza cintas y la busqueda
# por el corpus decide si una frase que falta se recupera o va a tablero; una
# cinta sin transcribir hace que esa busqueda conteste «no esta» sin mirar.
# Una cinta sin guion es material, no sobra (C-74).
#
# Pero se identifica con el BARATO. Correccion de Jaime: *«por que estas
# haciendo cuatro pasadas, ya identificaste el libreto?»* — y no, no lo habia
# identificado. Cuatro pasadas sobre una cinta que no se sabe que contiene es
# aplicarle lo mas caro a algo que todavia no ha pasado ningun filtro, que es
# exactamente lo que el embudo prohibe: *«no tiene sentido logico tener un
# funnel para aplicarle a todo lo mas caro»*.
#
# El barato dice QUE hay. Con eso se decide si esa cinta alimenta una pieza — y
# solo entonces se paga el caro. `exigir()` no deja montar con un transcript de
# una pasada, asi que el barato no puede colarse al montaje por accidente.
PYTHONIOENCODING=utf-8 corre python scripts/transcribir.py --barato



paso "2 · catalogar la cinta entera"
PYTHONIOENCODING=utf-8 corre python scripts/catalogar.py

paso "3 · elegir el segmento de cada etapa"
for n in "${REELS[@]}"; do
  PYTHONIOENCODING=utf-8 corre python scripts/seleccionar.py "$n" --edl
done

paso "3a · el caro: afinar SOLO los tramos elegidos"
# Aqui, y no en el paso 1. Jaime: *«las cuatro pasadas son antes de renderizar,
# como mecanismo para identificar redundancia, nunca para identificacion de la
# cinta; identificamos la redundancia en los lugares especificos, la eliminamos
# y renderizamos con eso»*.
#
# El barato dice que hay y la seleccion elige; el caro entra solo donde se va a
# usar, que es donde `depurar` necesita precision de palabra para ver la
# repeticion. Antes se pagaban cuatro pasadas sobre la cinta entera para acabar
# usando dos minutos de ella.
for n in "${REELS[@]}"; do
  PYTHONIOENCODING=utf-8 corre python scripts/transcribir.py --elegidos "$n"
done

paso "3b · borrar lo que no aporta de la toma elegida"
# **Solo sobre la elegida.** Jaime: *«el filtro de la redundancia se aplica
# despues de escoger la escena; lo que no aporte, o los segundos que no aporten,
# se deben borrar»*, y *«no tiene sentido logico tener un funnel para aplicarle a
# todo lo mas caro»*. Se va el aire sin una sola palabra y el tartamudeo; lo que
# se dice no se toca.
for n in "${REELS[@]}"; do
  PYTHONIOENCODING=utf-8 corre python scripts/depurar.py "$n"
done

paso "3c · la redundancia, que la decide el modelo y no Python"
# Jaime: *«la redundancia no es algo que se pueda inferir con codigo facilmente;
# necesitariamos un modelo probabilistico de prediccion de lenguaje, que es
# exactamente lo que tenemos contigo. No esta en la capacidad de Python ni de
# ninguna de sus dependencias»*.
#
# `depurar` se queda con lo mecanico —aire y tartamudeo— y esto saca el dossier
# para que el modelo elija que version de cada frase se queda. Los cortes vuelven
# como notas de `revision`, ancladas al texto.
for n in "${REELS[@]}"; do
  PYTHONIOENCODING=utf-8 corre python scripts/redundancia.py "$n"
done

paso "4 · describir cada escena"
# Si el CLI no tiene credencial, se avisa y se sigue: las escenas ya descritas
# valen y las que falten se cargan por migracion. No para el camino.
corre node scripts/describir.mjs "${REELS[@]}"

paso "5 · cortar cada fragmento a su fichero"
PYTHONIOENCODING=utf-8 corre python scripts/cortar.py "${REELS[@]}"

paso "5b · la puerta: nada se renderiza sin pasar por aqui"
# Corre el juego entero de comprobaciones, no una. El fallo que la creo fue
# cambiar un criterio y verificar solo ese criterio: `escena_desc` llevaba seis
# horas caducada mientras los EDL se regeneraban una docena de veces.
PYTHONIOENCODING=utf-8 python scripts/verificar.py "${REELS[@]}" || fallo=1

if [ "$SIN_RENDER" -eq 0 ] && [ "$fallo" -eq 0 ]; then
  paso "6 · montar, renderizar, masterizar y verificar"
  corre bash scripts/montar.sh "${REELS[@]}"
fi

paso "6b · la revision final: los cortes que Jaime pidio mirando la pieza"
# **Va aqui y no antes** porque sus tiempos son de la pieza montada, no de la
# cinta. Y se re-aplican en cada corrida: `seleccionar` regenera el EDL, asi que
# un corte dado por hecho desaparece a la siguiente.
for n in "${REELS[@]}"; do
  PYTHONIOENCODING=utf-8 corre python scripts/revision.py --aplicar "$n"
done
PYTHONIOENCODING=utf-8 python scripts/revision.py --ver "${REELS[@]}"

paso "7 · la tabla de colocacion"
PYTHONIOENCODING=utf-8 corre python scripts/colocar.py "${REELS[@]}"

paso "8 · fragmentos como se ven, para aprobar"
PYTHONIOENCODING=utf-8 corre python scripts/revisar.py "${REELS[@]}"

paso "9 · que falta para publicar"
PYTHONIOENCODING=utf-8 python scripts/publicar.py --ver

paso "incidencias de esta corrida"
PYTHONIOENCODING=utf-8 python scripts/registro.py

echo
if [ "$fallo" -eq 0 ]; then
  echo "CAMINO COMPLETO"
else
  echo "CAMINO COMPLETO CON FALLOS — mira los pasos marcados arriba"
fi
exit "$fallo"
