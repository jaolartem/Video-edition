#!/usr/bin/env bash
#
# Sintetiza los efectos de las animaciones. No se descarga nada: son
# transitorios cortos y salen mejor generados que buscados, porque así duran
# exactamente lo que dura el movimiento que los produce.
#
# La ley del proyecto es que **el sonido sigue al movimiento**: si un bloque se
# pega, suena el pegado; si algo cruza, suena el cruce. Nada de efectos sobre
# algo quieto.
#
# Los nombres los fija `src/brand/sfx.ts` (`sfxFile`), no este script: si no
# coinciden, `staticFile` pide un fichero que no existe y el efecto falla en
# silencio. Ya paso una vez — el script emitia «pegatina.wav» y el codigo pedia
# «mark.wav».
#
#
# **Los efectos de tablero son TONALES, no ruido.** Estaban sintetizados con
# `anoisesrc` y Jaime lo oyo en cuanto dejaron de estar por debajo del suelo:
# *«ese tablero que me muestras siempre se escucha con interferencia»*. Un
# pulso de ruido filtrado encima de la voz es interferencia por construccion.
# Un marcador que entra suena a golpe: senoide amortiguada, ataque instantaneo
# y caida exponencial. El ruido se queda solo donde el movimiento ES ruido —el
# barrido, que es aire, y el glitch, que es interferencia a proposito.
#
#   bash scripts/sfx.sh
set -e
cd "$(dirname "$0")/.."
OUT=public/sfx
mkdir -p "$OUT"

# ── mark ─────────────────────────────────────────────────────────────────
# Un bloque que aterriza, un marcador que aparece. Ruido rosa con ataque
# instantaneo y caida de 90 ms: el golpe seco del papel contra la superficie.
# Sin cola, o suena a platillo.
ffmpeg -v error -y -f lavfi -i "aevalsrc='exp(-t*38)*(0.75*sin(2*PI*1180*t)+0.25*sin(2*PI*2360*t))':d=0.10:s=48000" -af "highpass=f=260,volume=0.85" -ac 1 "$OUT/mark.wav"

# ── land ─────────────────────────────────────────────────────────────────
# El remate que aterriza: la consecuencia, la cifra. Mas grave y algo mas largo
# que `mark` — pesa mas, asi que suena mas abajo.
ffmpeg -v error -y -f lavfi -i "aevalsrc='exp(-t*13)*(0.8*sin(2*PI*168*t)+0.2*sin(2*PI*336*t))':d=0.30:s=48000" -af "lowpass=f=1400,volume=0.9" -ac 1 "$OUT/land.wav"

# ── draw ─────────────────────────────────────────────────────────────────
# Una linea que se traza: conector, rail, la raya del umbral. Continuo y corto,
# sin ataque marcado — no aterriza nada, se esta dibujando.
ffmpeg -v error -y -f lavfi -i "aevalsrc='exp(-t*16)*sin(2*PI*(620+900*t)*t)':d=0.20:s=48000" -af "highpass=f=300,lowpass=f=4200,volume=0.7" -ac 1 "$OUT/draw.wav"

# ── fork ─────────────────────────────────────────────────────────────────
# La bifurcacion abriendose. Dos trazos casi simultaneos: es un movimiento que
# se parte en dos y el sonido lo dice.
ffmpeg -v error -y -f lavfi -i "aevalsrc='exp(-t*46)*sin(2*PI*980*t)+(gt(t,0.06)*exp(-(t-0.06)*46)*sin(2*PI*1470*(t-0.06)))':d=0.24:s=48000" -af "highpass=f=240,volume=0.8" -ac 1 "$OUT/fork.wav"

# ── type ─────────────────────────────────────────────────────────────────
# Texto que aparece letra a letra. Solo si el texto efectivamente se teclea.
ffmpeg -v error -y -f lavfi -i "aevalsrc='exp(-t*120)*sin(2*PI*2100*t)':d=0.05:s=48000" -af "highpass=f=900,volume=0.8" -ac 1 "$OUT/type.wav"

# ── whoosh ───────────────────────────────────────────────────────────────
# La barra que cruza el cuadro, o un cambio de toma. Legitimo porque hay algo
# moviendose, que es la unica condicion: prohibido el sonido sin movimiento.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.24:c=white:a=0.8:r=48000"   -af "bandpass=f=1400:width_type=o:w=2,afade=t=in:st=0:d=0.06,afade=t=out:st=0.10:d=0.13,volume=0.32"   -ac 1 "$OUT/whoosh.wav"

# ── glitch ───────────────────────────────────────────────────────────────
# La distorsion que tapa un corte. Ruido de banda ancha, 90 ms, con un golpe
# grave debajo: es el chasquido de un televisor antiguo al cambiar de canal.
#
# Va CORTO a proposito. El corte que tapa dura tres frames; un efecto mas largo
# deja de esconder el corte y pasa a ser el corte.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.09:c=white:a=0.9:r=48000"   -af "highpass=f=600,afade=t=out:st=0.02:d=0.07:curve=exp,volume=0.34"   -ac 1 "$OUT/glitch.wav"

for f in "$OUT"/*.wav; do
  printf "%-26s %ss
" "$f"     "$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" | cut -c1-5)"
done

# ── el pico de cada efecto, medido y escrito ────────────────────────────────
#
# **La medida la hace quien genera el fichero, no quien lo usa.** Estaba
# copiada a mano en `src/brand/sfx.ts` y se quedo vieja en cuanto se
# regeneraron los efectos: los picos pasaron de -17,5/-7,4 a -2,4/-8,0 y la
# tabla del codigo seguia diciendo lo de antes, o sea que el nivel calculado
# era el de otros ficheros. Es el patron que costo el dia entero — la decision
# en dos sitios y el que lee no es el que se corrige.
#
# Se escribe aqui, se importa alli. Una fuente.
echo "{" > src/brand/sfx-picos.json
primero=1
for f in "$OUT"/*.wav; do
  n=$(basename "$f" .wav)
  pico=$(ffmpeg -hide_banner -i "$f" -af volumedetect -f null - 2>&1 \
         | grep -oE "max_volume: [-0-9.]+" | head -1 | grep -oE "[-0-9.]+$")
  [ -z "$pico" ] && pico=0
  [ $primero -eq 0 ] && echo "," >> src/brand/sfx-picos.json
  primero=0
  printf '  "%s": %s' "$n" "$pico" >> src/brand/sfx-picos.json
done
printf '\n}\n' >> src/brand/sfx-picos.json
echo "picos medidos -> src/brand/sfx-picos.json"
