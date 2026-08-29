#!/usr/bin/env bash
# Hoja de contacto de un reel: un fotograma cada N segundos, en cuadricula.
#
# Es la forma barata de ver la pieza entera de un vistazo — encuadres, rotulo,
# subtitulos, y lo que ningun script detecta: si en algun plano Jaime esta
# leyendo la hoja. Se intento medirlo por altura de cabeza y no separaba
# (aprendizaje 7); mirarlo si.
set -e
f="$1"; cada="${2:-4}"; out="$3"
tmp=$(mktemp -d)
d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
n=$(python -c "print(int(float('$d')//$cada)+1)")
for i in $(seq 0 $((n-1))); do
  t=$(python -c "print($i*$cada)")
  ffmpeg -v error -y -ss "$t" -i "$f" -frames:v 1 -vf scale=200:-1 \
    "$tmp/$(printf %03d $i).png"
done
cols=6
rows=$(( (n + cols - 1) / cols ))
ffmpeg -v error -y -framerate 1 -i "$tmp/%03d.png" \
  -vf "tile=${cols}x${rows}:margin=4:padding=4" -frames:v 1 "$out"
rm -rf "$tmp"
echo "$out  ($n fotogramas cada ${cada}s)"
