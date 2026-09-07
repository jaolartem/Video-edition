#!/usr/bin/env bash
#
# Renderiza y mezcla una pieza. **La entrada segura para hacerlo suelto.**
#
# Existe porque el fallo vino de ahí: `montar.sh` sí declaraba el temporal en el
# disco del proyecto, pero un `npx remotion render` lanzado a mano no, y Chrome
# se fue a C: —al 96%— y dos piezas murieron con «Failed to fetch … disk space
# is low». Regla de Jaime: *«todo debe ser producido en F:»*.
#
# Así que el entorno no se pasa: se hereda de `entorno.sh`, que lo lee de
# `rutas.json` y se planta si apunta al disco del sistema.
#
#   bash scripts/render.sh 3        # renderiza y mezcla el reel 3
#   bash scripts/render.sh 3 --solo-render
set -e
cd "$(dirname "$0")/.."
source scripts/entorno.sh

n="${1:?falta el numero de reel}"
DESTINO=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.destino))")
mkdir -p "$DESTINO/reels"

echo "── render Reel-R$n → $DESTINO/reels ──"
# **Por `render.mjs`, no por el CLI. Una sola puerta al render.**
#
# Esto llamaba al CLI por su cuenta: otra concurrencia, otro bundle y —lo que
# de verdad costaba— **sin escribir `reel-RN.mp4.huella`**, que es lo que
# `_render_caduco()` exige para dar la pieza por montada. Una pieza
# renderizada por esta puerta salia caduca para siempre y el montaje
# siguiente la rehacia entera: una puerta produciendo trabajo para la otra.
#
# Aqui queda lo que esta entrada aporta y el motor no: comprobar el render
# contra el plan y encadenar la mezcla.
node scripts/render.mjs "$n"

# **Se comprueba que salió, y que dura lo que el plan dice.** El render puede
# fallar dejando el fichero anterior en su sitio: entonces la mezcla toma el
# viejo y la pieza entregada es la de antes sin que nadie lo note. Paso justo
# esto con los reels 2 y 3.
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DESTINO/reels/reel-R$n.mp4")
PLAN=$(node -e "const d=JSON.parse(require('fs').readFileSync('work/scenes/reel-$(printf %02d "$n")/plan-full.json','utf8'));console.log(d.escenas.reduce((s,e)=>s+e.duracion,0).toFixed(1))" 2>/dev/null || echo 0)
echo "  dura ${DUR}s (el plan dice ${PLAN}s)"
awk -v d="$DUR" -v p="$PLAN" 'BEGIN{ if (p>0 && (d-p>3 || p-d>3)) { print "  OJO: el render no cuadra con el plan — puede ser el fichero anterior"; exit 1 } }'

[ "${2:-}" = "--solo-render" ] && exit 0
# El interprete se pregunta, no se nombra: `bash.exe` puede no estar (el
# antivirus se lo llevo de la instalacion de Git) y `sh.exe` es el mismo binario.
"$(command -v bash || command -v sh)" scripts/musica.sh "$n"
