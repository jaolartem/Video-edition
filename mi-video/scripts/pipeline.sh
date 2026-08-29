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

paso "0 · guardas y modelo de datos"
# Lo unico que corre siempre y antes que nada: si una correccion perdio su
# mecanismo o al modelo le falta una tabla del ciclo, lo que venga despues no
# tiene donde registrarse.
node scripts/guardas.mjs || exit 1
PYTHONIOENCODING=utf-8 python scripts/modelo.py || exit 1

paso "el motor: cada etiqueta llama a su servicio"
# **La linea dejo de ser una secuencia.** Jaime: *«las fases y los estados son
# etiquetas que llaman servicios; si una etiqueta esta en un paso, entonces
# avanza automaticamente en ese paso, y si no avanza pues para eso es el log»*.
#
# El orden ya no vive aqui: vive en la tabla `fase`, con el servicio que mueve
# cada etiqueta. Anadir un paso es insertar una fila, no editar este fichero.
# Y una pieza atascada ya no arrastra a las demas — la unidad es la pieza.
PYTHONIOENCODING=utf-8 python scripts/avanzar.py "${REELS[@]}" || fallo=1

paso "incidencias de esta corrida"
PYTHONIOENCODING=utf-8 python scripts/registro.py


