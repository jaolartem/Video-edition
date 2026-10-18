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
# Sin lista por defecto: la de aqui envejecio con el lote (1..6 cuando el vivo
# era 18..22). Las piezas se dicen; ver `arrancar.sh` (C-548).
[ ${#PIEZAS[@]} -eq 0 ] && { echo "montar-lote.sh: di que piezas"; exit 1; }
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

# **Lo que mira el proyecto entero, una vez.** `montar.sh --solo-lote` corre su
# primera mitad —guardas, verdad, contratos, techo, la puerta de `verificar.py`,
# el spec, `llega` y el lint— y se para justo donde el trabajo deja de ser del
# proyecto y pasa a ser de la pieza. Despues las piezas van con `EN_LOTE=1`, que
# salta exactamente eso.
#
# Corria siete veces para mirar siete veces lo mismo: solo el lint son 9,6 s por
# pieza. Y si la puerta dice que no, se sabe **antes** de repartir nada.
echo "== comprobaciones del lote, una sola vez =="
SALTA_SPEC="$SALTA" "$SH" scripts/montar.sh --solo-lote "${PIEZAS[@]}"

# **Un bundle para todas, y solo cuando el spec ya no se mueve.**
#
# Empaquetar cuesta 22,5 s medidos y se pagaba una vez por pieza. Pero el bundle
# lleva `src/reels.json` COMPILADO dentro —por eso la cache esta apagada—, asi
# que compartirlo solo vale si el spec del lote es el definitivo. Es la misma
# condicion que ya decide `SALTA`: cuando una pieza trae EDL nuevo, cada una
# rehace su spec y entonces cada una tiene que empaquetar el suyo.
BUNDLE_LOTE=""
if [ "$SALTA" = "1" ]; then
  BUNDLE_LOTE=$(node scripts/render.mjs --solo-bundle | tail -1)
  export BUNDLE_LOTE
  # Se borra pase lo que pase: hay 22 GB de bundles huerfanos en `F:/tmp-video`
  # de corridas que murieron a medias, cada uno con su copia de `public/`.
  trap 'rm -rf "$BUNDLE_LOTE"' EXIT
fi

# **La concurrencia del render la reparte quien reparte las piezas.**
#
# Estaba fijada en 4 dentro de `render.mjs`, y 4 era el numero de OTRO reparto:
# tres piezas a la vez, doce pestanas. Cuando el lote va de una en una —porque
# alguna trae EDL nuevo— esas doce siguen cabiendo y quedarse en cuatro es dejar
# la maquina parada. El presupuesto es doce y se divide; nunca sube de ahi, que
# es lo que tumbaba el render en el frame 1387. Y no baja de cuatro: por debajo
# de ahi una pieza tarda mas de lo que el paralelismo le ahorra al lote.
#
# **La cuenta no se repite aqui: se pregunta.** Escrita en bash protegia solo a
# este lanzador, y `avanzar.py --hilos` —el otro— no la conocia. Vive en
# `planificador.por_pieza`, que es de quien reparte piezas.
export RENDER_CONCURRENCIA=$(python scripts/planificador.py --por-pieza "$A_LA_VEZ")

export EN_LOTE=1
export SALTA
echo "== montando ${#PIEZAS[@]} pieza(s), $A_LA_VEZ a la vez, concurrencia $RENDER_CONCURRENCIA =="
printf '%s\n' "${PIEZAS[@]}" | SH="$SH" xargs -P "$A_LA_VEZ" -I{} \
  "$SH" -c 'SALTA_SPEC="$SALTA" "$SH" scripts/montar.sh {} > "work/montaje-{}.log" 2>&1 \
           && echo "  R{} listo" || echo "  R{} FALLO — mira work/montaje-{}.log"'

# **Y el parte, cuando ya estan todas.** La bitacora y la verificacion hablan de
# las siete: hacerlas por pieza era escribir seis veces un documento que la
# septima iba a reescribir. Aqui ademas cuadran con lo entregado, que es lo que
# se firma.
node scripts/bitacora.mjs
node scripts/verificacion.mjs

echo "== hecho: los registros en work/montaje-N.log =="
