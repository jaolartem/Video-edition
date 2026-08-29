#!/usr/bin/env bash
#
# Monta los reels de punta a punta. Las carpetas salen de `rutas.json`.
#
#   bash scripts/montar.sh                 # los seis
#   bash scripts/montar.sh 2 5             # sólo esos
#   VIDEO_DESTINO=/otra/carpeta bash scripts/montar.sh
#   bash scripts/montar.sh --origen D:/brutos
#
# Ninguna ruta va escrita aquí dentro: se declaran una vez y se preguntan.
set -e
cd "$(dirname "$0")/.."

# Remotion escribe sus frames temporales en el TEMP del sistema, que aqui vive
# en C: y se queda sin sitio a 1800x3200 — Chrome rechaza la peticion y el
# render muere con «Failed to fetch … disk space is low», que no dice que el
# problema sea el disco del sistema. Se manda el temporal al disco del proyecto.
#
# **Y la ruta NO puede llevar espacios.** Estuvo en «F:/Edicion de video/tmp» y
# Remotion siguio escribiendo en C: pese a las tres variables: es el gotcha 1
# del proyecto. La señal es que el error de disco aparece con sitio de sobra en
# el disco declarado.
# **La consola de Windows es cp1252 y los scripts imprimen en UTF-8.**
# `candidatos.py` reventaba al imprimir una flecha —`UnicodeEncodeError`— con el
# fichero ya escrito: el trabajo estaba hecho y el paso salia con error. Es el
# gotcha 1 del proyecto por otra puerta: el entorno no es el que el codigo supone.
export PYTHONIOENCODING=utf-8

export TMPDIR="F:/tmp-video"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
mkdir -p "$TMPDIR"

# **Las correcciones, antes que nada.** Cada entrada de `docs/correcciones.md`
# declara el fichero y el trozo de código donde quedó imposible repetirla; si
# una reescritura se lo llevó por delante, el montaje para aquí en vez de
# reproducir el defecto en las seis piezas. Es barato —lee ficheros— y va
# primero justo por eso.
node scripts/guardas.mjs

ORIGEN=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.origen))")
DESTINO=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.destino))")
echo "origen  $ORIGEN"
echo "destino $DESTINO"

REELS=()
for a in "$@"; do
  [[ "$a" == --* ]] && continue
  REELS+=("$(printf %02d "$a")")
done
[ ${#REELS[@]} -eq 0 ] && REELS=(01 02 03 04 05 06)

# **Paso 1: los subtitulos de toda la cinta, y van delante de todo.** El montaje
# leia una sola pasada de whisper y la trataba como verdad; el modelo se come
# frases, se queda pegado y con `-ml 1 -sow` borra la puntuacion, asi que el
# catalogo daba unidades de 98 s y la seleccion no podia elegir (C-54). Esto no
# depende de que quien lanza el montaje se acuerde del orden: `exigir()` para el
# resto si falta, y aqui se encadena para que no haga falta llegar a ese error.
for r in "${REELS[@]}"; do
  TOMA=$(node -e "console.log(JSON.parse(require('fs').readFileSync('rutas.json','utf8')).tomas['reel-$r']||'')")
  if [ -n "$TOMA" ] && ! grep -q '"pasadas"' "work/transcripts/$TOMA.json" 2>/dev/null; then
    echo "══ subtitulos reel-$r ══ (varias pasadas; es el paso 1)"
    python scripts/transcribir.py --toma "$((10#$r))"
  fi
done

for r in "${REELS[@]}"; do
  SRC=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.bruto('reel-$r')))")
  # **Ya se puede cortar material de varias cintas.** Estuvo frenado porque el
  # corte abria un solo `-i` y `punch-ins.py` calculaba un ancla por fichero —
  # con dos sesiones el encuadre salia descuadrado sin avisar (aprendizaje 20).
  # Ahora la escena declara su `fuente`, el ancla se mide **por fuente** y cada
  # escena abre su propio bruto: no hay dos fuentes en un corte, hay dos cortes.
  echo "══ corte reel-$r ══"
  # **Si el EDL cambio, el plan esta viejo.** El corte no lee el EDL: lee
  # `plan-full.json`, que `plan-reel.mjs` derivo de el en su dia. Asi que editar
  # el EDL —anadir un cierre, recortar una entrada— **no cambiaba nada y no lo
  # decia nadie**: el montaje salia identico y con exito. Es el aprendizaje 44
  # por el otro lado: alli un paso invalidaba lo que produjo otro; aqui el
  # consumidor no se entera de que su fuente cambio.
  #
  # Se compara por fecha de modificacion, que es la unica senal que hay.
  if [ "ads/reel-$r/edl-sell.json" -nt "work/scenes/reel-$r/plan-full.json" ]; then
    echo "  (el EDL es mas nuevo que el plan: regenerando escenas)"
    node scripts/plan-reel.mjs --reel "$r" 2>&1 | tail -1
  fi
  # `plan-reel.mjs` regenera el plan SIN encuadres —los calcula `punch-ins.py`—
  # asi que si el plan viene pelado hay que volver a medirlos. Antes esto no
  # estaba encadenado y el corte fallaba con «El plan no tiene encuadres».
  if ! node -e "process.exit(JSON.parse(require('fs').readFileSync('work/scenes/reel-$r/plan-full.json','utf8')).escenas[0].crop?0:1)"; then
    echo "  (recalculando encuadres)"
    python scripts/punch-ins.py --source "$SRC"       --plan "work/scenes/reel-$r/plan-full.json" --ancla-global 2>&1 | grep -E "ancla global"
  fi
  node scripts/render-hook.mjs --source "$SRC" \
    --plan "work/scenes/reel-$r/plan-full.json" \
    --out "public/reel-$r.mp4" 2>&1 | grep -E "escenas ·|listo"
  python scripts/subtitular.py "$r"
done

REELS_PEDIDOS="${REELS[*]}" node scripts/reels-spec.mjs
# El parte de trabajo se reescribe solo: los números de `docs/bitacora.md` salen
# del spec recién generado. Un número copiado a mano se queda viejo en el primer
# render, y entonces la bitácora miente justo cuando hace falta.
node scripts/bitacora.mjs
npm run lint

for r in "${REELS[@]}"; do
  n=$((10#$r))
  echo "── render Reel-R$n ──"
  # **A resolución nativa, y con la GPU donde de verdad se puede.**
  #
  # `--hardware-acceleration` NO sirve en esta máquina, y conviene saber por
  # qué: Remotion elige **`h264_nvenc`**, el codificador de NVIDIA, y aquí hay
  # una **Radeon RX 5600 XT**. Revienta al instante con «write EOF».
  #
  # Y estuvo a punto de colarse como mejora: en un banco anterior daba 14 s
  # frente a 68 s, pero **era un fallo rápido, no un render rápido** — se medía
  # el tiempo sin comprobar que el fichero existiera. Un banco que no verifica
  # la salida mide lo que tarda en fallar.
  #
  # Lo que sí acelera:
  #
  #   sin `--scale`     La composición ya se maqueta a 1080x1920, que es lo que
  #                     se entrega. Subirla a 1800x3200 eran 2,8x más píxeles
  #                     para tirarlos después.
  #   `--gl=angle`      Chrome compone por D3D11 y no por software.
  #   concurrencia      El cuello es pintar frames, no codificarlos.
  #   h264_amf (abajo)  La entrega, ésa sí por el codificador de AMD.
  # **Lo que no paso la puerta no se renderiza, y el resto sigue.** El peldaño
  # caro solo sobre lo que ya sabemos que esta bien.
  MOTIVOS=$(node -e "const s=JSON.parse(require('fs').readFileSync('src/reels.json','utf8'));const r=s.find(x=>x.id==='Reel-R$n');console.log((r&&r.bloqueado||[]).join(' | '))")
  if [ -n "$MOTIVOS" ]; then
    echo "── Reel-R$n NO se renderiza ──"
    echo "   $MOTIVOS"
    continue
  fi
  npx remotion render "Reel-R$n" "$DESTINO/reels/reel-R$n.mp4"     --gl=angle --concurrency=16 --offthread-video-threads=8 --log=error
  # **La entrega NO recorta.** Jaime: *«respeta el guion; si hay necesidad de
  # recortar lo definimos al final»* y *«el ajuste de tiempo lo hacemos al final
  # con el reel montado»*.
  #
  # Antes se capaba con `-t` a 89,9 s. Eso es una decisión de montaje tomada por
  # una resta, y en silencio: la pieza salía cortada a mitad de frase sin que
  # nadie lo hubiera decidido. Ahora se entrega entera y **se reporta** contra la
  # indicación de su formato, que es lo que hace falta para decidir después.
  #
  # Las indicaciones, no topes: **ad 120 s · reel 90 s**, y varían según lo que
  # la pieza tenga que decir.
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DESTINO/reels/reel-R$n.mp4")
  LIMITE=${LIMITE:-120}
  # Va con `print`, no con `printf`, y a propósito: `printf` necesita un salto
  # de línea escapado dentro de las comillas y, escrito como salto real, awk
  # aborta con «unterminated string». Con `set -e` eso **se lleva por delante el
  # resto del paso** — el render quedaba escrito y las copias de entrega y de
  # revisión no llegaban a generarse, con el script saliendo 0. `print` no
  # necesita salto, así que el fallo no puede volver.
  awk -v d="$DUR" -v l="$LIMITE" -v n="$n" 'BEGIN{
    if (d > l)
      print "  ojo: R" n " dura " int(d*10)/10 "s, " int((d-l)*10)/10 "s sobre la indicacion de " l "s. NO se recorta: se decide al final."
    else
      print "  R" n " " int(d*10)/10 "s, dentro de la indicacion de " l "s"
  }'

  # **El paso 7 va aqui, no aparte.** La entrega y la copia de revision las
  # escribe `musica.sh`, que es donde vive la mezcla: la voz se nivela, la
  # musica se talla en la banda de la voz y las dos salen a -14 LUFS / -1 dBTP.
  #
  # Estuvo suelto y por eso las entregas salian mudas de musica: un paso que hay
  # que acordarse de correr no es un paso del proceso, es una intencion. Si
  # falta el mp3 de la pieza, masteriza solo la voz y lo dice.
  bash scripts/musica.sh "$n"
  echo "R$n $(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$DESTINO/entrega/reel-R$n.mp4")"
done
# **La verificacion va DESPUES de entregar, y la llama el runner.** No la
# llamaba nadie: los `Reel-RN.verification.md` eran restos de una corrida
# manual, y describian el corte anterior — el del reel 1 decia 82,2 s cuando el
# fichero entregado duraba 101,4. Un documento de verificacion que no cuadra con
# lo que se entrega es peor que no tenerlo, porque se firma igual. Es el
# aprendizaje 24: arreglar el generador no arregla lo generado.
node scripts/verificacion.mjs
echo "MONTAJE COMPLETO"
