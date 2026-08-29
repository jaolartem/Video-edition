#!/usr/bin/env bash
#
# Deja las piezas al nivel que esperan las plataformas y saca la entrega.
#
# ## Por qué existe
#
# Los seis salían a **−9,8 LUFS con pico real +0,1 dBTP**. Instagram, TikTok y
# YouTube normalizan a ~−14 LUFS, así que una pieza a −9,8 la bajan ellos: el
# nivel deja de ser una decisión del montaje y pasa a depender de la plataforma,
# y entre piezas del mismo lote suena distinto según dónde se publique.
#
# El pico por encima de 0 dBTP es lo otro: en reproducción con códec con pérdida
# los picos entre muestras se van por arriba y distorsionan. −1 dBTP es el
# margen habitual.
#
# ## Lo que esto NO arregla
#
# **La saturación viene de la grabación.** El bruto 4K tiene 29.281 muestras
# pegadas a 0 dB antes de que el pipeline lo toque; el corte y el render sólo la
# heredan. Una onda ya recortada no se reconstruye bajando el volumen — se oye
# más bajo, pero sigue recortada.
#
# Se probó `adeclip` y **no cambió nada**: 16.485 muestras a 0 dB antes y las
# mismas después. Se descarta en vez de dejar puesto un filtro que no filtra.
#
# El arreglo de verdad está en el rodaje: **bajar la ganancia del micro** hasta
# que los picos queden en −6 dBFS. Anotado en CLAUDE.md.
#
# ## Dos pasadas, no una
#
# `loudnorm` en una pasada trabaja a ciegas y comprime de más. Midiendo primero
# y aplicando los valores medidos después, el ajuste es una ganancia calculada y
# el rango dinámico se conserva.
#
#   bash scripts/sonoridad.sh          # los seis
#   bash scripts/sonoridad.sh 2 5      # sólo esos
set -e
cd "$(dirname "$0")/.."

export TMPDIR="F:/tmp-video"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
mkdir -p "$TMPDIR"

# Objetivo de plataforma. −14 LUFS es lo que normalizan Instagram, TikTok y
# YouTube; −1 dBTP deja margen para los picos entre muestras.
I=-14
# **-1,5 y no -1, igual que `musica.sh`.** La norma pide como maximo -1 dBTP y
# el limitador de `loudnorm` deja el pico justo por encima de lo que se le pide:
# pedido -1, la entrega medida daba -0,74. Los dos scripts tocan el mismo
# fichero y tenian objetivos distintos — el que pedia -1 se pasaba siempre.
TP=-1.5
LRA=11

REELS=("$@")
[ ${#REELS[@]} -eq 0 ] && REELS=(1 2 3 4 5 6)

mkdir -p out/entrega out/revision

for n in "${REELS[@]}"; do
  SRC="out/reels/reel-R$n.mp4"
  [ -f "$SRC" ] || { echo "R$n: falta $SRC — hay que renderizar antes"; continue; }

  # ── pasada 1: medir ────────────────────────────────────────────────────
  M=$(ffmpeg -hide_banner -i "$SRC" \
        -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" \
        -f null /dev/null 2>&1 | sed -n '/{/,/}/p')
  val() { echo "$M" | grep "\"$1\"" | sed 's/.*: *"\([^"]*\)".*/\1/'; }
  II=$(val input_i); ITP=$(val input_tp); ILRA=$(val input_lra)
  ITH=$(val input_thresh); OFF=$(val target_offset)

  # ── pasada 2: aplicar los valores medidos ──────────────────────────────
  AF="loudnorm=I=$I:TP=$TP:LRA=$LRA:measured_I=$II:measured_TP=$ITP:measured_LRA=$ILRA:measured_thresh=$ITH:offset=$OFF:linear=true"

  # El vídeo se COPIA: ya está codificado por GPU en el render y volver a
  # tocarlo sólo perdería calidad. Aquí sólo cambia el audio.
  ffmpeg -v error -y -i "$SRC" -af "$AF" \
    -c:v copy -c:a aac -b:a 160k -ar 48000 -movflags +faststart \
    "out/entrega/reel-R$n.mp4"

  # La copia de revisión sí se reescala, y ahí la GPU vuelve a trabajar.
  ffmpeg -v error -y -hwaccel d3d11va -i "$SRC" -af "$AF" \
    -vf scale=608:1080 \
    -c:v h264_amf -quality speed -rc cqp -qp_i 30 -qp_p 30 \
    -pix_fmt yuv420p -movflags +faststart \
    -c:a aac -b:a 96k "out/revision/reel-R$n.mp4"

  FINAL=$(ffmpeg -hide_banner -i "out/entrega/reel-R$n.mp4" \
            -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" \
            -f null /dev/null 2>&1 | sed -n '/{/,/}/p' \
            | grep '"input_i"' | sed 's/.*: *"\([^"]*\)".*/\1/')
  printf "R%s  %6s LUFS -> %6s   pico %5s -> %s dBTP\n" \
    "$n" "$II" "$FINAL" "$ITP" \
    "$(ffmpeg -hide_banner -i "out/entrega/reel-R$n.mp4" -af "loudnorm=I=$I:TP=$TP:LRA=$LRA:print_format=json" -f null /dev/null 2>&1 | sed -n '/{/,/}/p' | grep '"input_tp"' | sed 's/.*: *"\([^"]*\)".*/\1/')"
done
