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

# **El spec se hace una vez PORQUE nada de lo que lee va a cambiar.** Si el EDL
# de una pieza es mas nuevo que su plan, dentro de `montar.sh` se van a rehacer
# las escenas y los subtitulos — y el spec construido aqui, antes, queda viejo.
#
# Paso el 7-9-2026 con reel-03: se le cambio el gancho, el plan salio bien y el
# video se pego en el orden nuevo, pero el spec traia los subtitulos y el rotulo
# del corte anterior. La pieza se renderizo entera y **abria con el gancho de
# antes**, sin que fallara nada. Cuesta una hora de render y no se ve hasta que
# se mira el fotograma.
#
# Cuando hay una pieza asi, el atajo no vale: cada `montar.sh` hace su propio
# spec —y entonces van de una en una, porque tres escribiendo `reels.json` a la
# vez lo parten.
VIEJAS=()
for n in "${PIEZAS[@]}"; do
  r=$(printf %02d "$n")
  if [ "ads/reel-$r/edl-sell.json" -nt "work/scenes/reel-$r/plan-full.json" ]; then
    VIEJAS+=("$r")
  fi
done
if [ ${#VIEJAS[@]} -gt 0 ]; then
  echo "== ${VIEJAS[*]} traen EDL nuevo: cada una hace su spec, y de una en una =="
  A_LA_VEZ=1
  SALTA=""
else
  echo "== spec para el lote, una sola vez =="
  REELS_PEDIDOS="${PIEZAS[*]}" node scripts/reels-spec.mjs
  SALTA="1"
fi

# **El interprete se resuelve, no se nombra.** Esto murio con `xargs: failed to
# run command 'bash': No such file or directory` y TODO lo demas en verde: el
# antivirus se llevo `usr/bin/bash.exe` de la instalacion de Git y no deja
# reponerlo ni con permisos. `sh.exe` es el mismo binario de 2,4 MB y estaba ahi
# al lado. Nombrar el interprete a mano es apostar a que exista; preguntarle al
# sistema cual hay cuesta lo mismo y no se cae.
SH=$(command -v bash || command -v sh)

echo "== montando ${#PIEZAS[@]} pieza(s), $A_LA_VEZ a la vez =="
printf '%s\n' "${PIEZAS[@]}" | SH="$SH" xargs -P "$A_LA_VEZ" -I{} \
  "$SH" -c 'SALTA_SPEC="$SALTA" "$SH" scripts/montar.sh {} > "work/montaje-{}.log" 2>&1 \
           && echo "  R{} listo" || echo "  R{} FALLO — mira work/montaje-{}.log"'

echo "== hecho: los registros en work/montaje-N.log =="
