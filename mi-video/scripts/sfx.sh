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
#   bash scripts/sfx.sh
set -e
cd "$(dirname "$0")/.."
OUT=public/sfx
mkdir -p "$OUT"

# ── mark ─────────────────────────────────────────────────────────────────
# Un bloque que aterriza, un marcador que aparece. Ruido rosa con ataque
# instantaneo y caida de 90 ms: el golpe seco del papel contra la superficie.
# Sin cola, o suena a platillo.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.14:c=pink:a=0.9:r=48000"   -af "highpass=f=320,lowpass=f=5200,afade=t=out:st=0.012:d=0.11:curve=exp,volume=0.55"   -ac 1 "$OUT/mark.wav"

# ── land ─────────────────────────────────────────────────────────────────
# El remate que aterriza: la consecuencia, la cifra. Mas grave y algo mas largo
# que `mark` — pesa mas, asi que suena mas abajo.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.26:c=brown:a=0.9:r=48000"   -af "lowpass=f=900,afade=t=out:st=0.02:d=0.22:curve=exp,volume=0.6"   -ac 1 "$OUT/land.wav"

# ── draw ─────────────────────────────────────────────────────────────────
# Una linea que se traza: conector, rail, la raya del umbral. Continuo y corto,
# sin ataque marcado — no aterriza nada, se esta dibujando.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.22:c=white:a=0.7:r=48000"   -af "bandpass=f=2600:width_type=o:w=1.4,afade=t=in:st=0:d=0.05,afade=t=out:st=0.12:d=0.09,volume=0.3"   -ac 1 "$OUT/draw.wav"

# ── fork ─────────────────────────────────────────────────────────────────
# La bifurcacion abriendose. Dos trazos casi simultaneos: es un movimiento que
# se parte en dos y el sonido lo dice.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.30:c=white:a=0.7:r=48000"   -af "bandpass=f=1900:width_type=o:w=1.8,afade=t=in:st=0:d=0.04,afade=t=out:st=0.18:d=0.11,volume=0.34"   -ac 1 "$OUT/fork.wav"

# ── type ─────────────────────────────────────────────────────────────────
# Texto que aparece letra a letra. Solo si el texto efectivamente se teclea.
ffmpeg -v error -y -f lavfi -i "anoisesrc=d=0.05:c=white:a=0.9:r=48000"   -af "highpass=f=1800,afade=t=out:st=0.004:d=0.04:curve=exp,volume=0.28"   -ac 1 "$OUT/type.wav"

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
