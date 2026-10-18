#!/usr/bin/env bash
# Copia los brutos de Google Drive a disco local.
#
# Cada corte busca y decodifica 4K HEVC; sobre Drive eso convierte un reel de
# treinta escenas en media hora. En local es otra cosa. Jaime: «la próxima lo
# hacemos en local — los copias y los pegas, es más eficiente que modificarlo
# desde la red».
#
# Solo las siete tomas que se usan, no la carpeta entera (hay 72 GB, de los que
# 33 son material que no entra en ningún reel).
set -e
# Todo sale de rutas.json: de donde se trae (fuentes.drive) y a donde va
# (origen). Cambiar de disco es editar ese fichero, no este script.
ORIGEN=$(node -e "console.log(JSON.parse(require('fs').readFileSync('rutas.json','utf8')).fuentes.drive)")
DESTINO=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.origen))")
mapfile -t TOMAS < <(node -e "console.log(Object.values(JSON.parse(require('fs').readFileSync('rutas.json','utf8')).tomas).join('
'))")
mkdir -p "$DESTINO"
for t in "${TOMAS[@]}"; do
  if [ -f "$DESTINO/$t.mp4" ]; then
    echo "ya está: $t"
    continue
  fi
  # **Cada lote vive en su subcarpeta** (`Brutos/10 16 26`): se busca la toma,
  # no se supone en la raiz. Suponerla dejaba fuera el ciclo W40 (C-548).
  SRC=$(find "$ORIGEN" -name "$t.mp4" -print -quit 2>/dev/null)
  if [ -z "$SRC" ]; then
    echo "traer-brutos: $t no esta en $ORIGEN ni en sus subcarpetas" >&2
    exit 1
  fi
  echo "copiando $t desde ${SRC#$ORIGEN/} …"
  cp "$SRC" "$DESTINO/$t.mp4"
done
echo "brutos en $DESTINO"
