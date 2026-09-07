#!/usr/bin/env bash
#
# Monta VARIAS piezas en paralelo, que es lo unico que acorta la hora de render.
#
#   bash scripts/montar-lote.sh              # las siete, de tres en tres
#   bash scripts/montar-lote.sh 2 5 7        # solo esas
#   A_LA_VEZ=2 bash scripts/montar-lote.sh   # si la maquina va justa
#
# **Por que el spec va aparte.** `reels-spec.mjs` escribe `src/reels.json`, que
# es de las siete: dos montajes a la vez se lo pisan y el segundo se lleva por
# delante lo que escribio el primero. Es lo UNICO compartido de la linea — el
# plan, los encuadres, el corte, los subtitulos, la cara, el render y la entrega
# son ficheros de su pieza. Asi que se corre una vez aqui y `montar.sh` lo salta.
#
# **Y por que de tres en tres y no de siete.** El render va por GPU y escribe
# fotogramas temporales a disco; con siete a la vez el disco y la GPU se
# estrangulan y tarda mas que en serie. Hoy ya murio un render con C: lleno.
# Tres es lo que aguanta esta maquina; `A_LA_VEZ` lo baja si hace falta.
set -euo pipefail
cd "$(dirname "$0")/.."

PIEZAS=("$@")
[ ${#PIEZAS[@]} -eq 0 ] && PIEZAS=(1 2 3 4 5 6 7)
A_LA_VEZ="${A_LA_VEZ:-3}"

echo "== spec para el lote, una sola vez =="
REELS_PEDIDOS="${PIEZAS[*]}" node scripts/reels-spec.mjs

# **El interprete se resuelve, no se nombra.** Esto murio con `xargs: failed to
# run command 'bash': No such file or directory` y TODO lo demas en verde: el
# antivirus se llevo `usr/bin/bash.exe` de la instalacion de Git y no deja
# reponerlo ni con permisos. `sh.exe` es el mismo binario de 2,4 MB y estaba ahi
# al lado. Nombrar el interprete a mano es apostar a que exista; preguntarle al
# sistema cual hay cuesta lo mismo y no se cae.
SH=$(command -v bash || command -v sh)

echo "== montando ${#PIEZAS[@]} pieza(s), $A_LA_VEZ a la vez =="
printf '%s\n' "${PIEZAS[@]}" | SH="$SH" xargs -P "$A_LA_VEZ" -I{} \
  "$SH" -c 'SALTA_SPEC=1 "$SH" scripts/montar.sh {} > "work/montaje-{}.log" 2>&1 \
           && echo "  R{} listo" || echo "  R{} FALLO — mira work/montaje-{}.log"'

echo "== hecho: los registros en work/montaje-N.log =="
