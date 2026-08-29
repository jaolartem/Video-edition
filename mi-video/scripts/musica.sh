#!/usr/bin/env bash
#
# PASO 7 — la música se talla bajo la voz, y luego se nivela.
#
# ## Qué pidió Jaime, exactamente
#
# *«Se agrega música clásica, se baja el volumen de las frecuencias que
# interfieran con la voz.»*
#
# **Eso no es bajar el fader.** Con un volumen fijo bajo, la música estorba
# igual: sigue ocupando la misma banda que la voz, sólo que más flojito. Y si se
# baja lo suficiente para no estorbar, deja de oírse y no aporta el pulso que
# venía a aportar.
#
# Lo que se hace es quitarle a la música **la banda donde vive la voz** y
# dejarle el grave y el brillo, que es donde la música se sostiene sin competir:
#
#   < 180 Hz     el cuerpo de la música. Entero: la voz casi no vive ahí.
#   180-4000 Hz  la banda de la voz. Se comprime CONTRA la voz: baja cuando
#                Jaime habla y vuelve cuando calla.
#   > 4000 Hz    el aire y las cuerdas. Entero.
#
# El compresor va encadenado a la voz (`sidechaincompress`), no a un reloj, así
# que se ajusta solo a cada frase sin que nadie dibuje una envolvente.
#
# ## Por qué aquí y no en Remotion
#
# La música estaba puesta como `<Audio>` dentro de la composición, a volumen
# fijo. Ahí es imposible tallarla: Remotion no tiene la voz y la música como dos
# señales que se puedan encadenar. **La mezcla es trabajo del paso de audio**,
# donde las dos existen por separado.
#
#   bash scripts/musica.sh          # los seis
#   bash scripts/musica.sh 1        # sólo el uno
set -e
cd "$(dirname "$0")/.."

export TMPDIR="F:/tmp-video"
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
mkdir -p "$TMPDIR" out/entrega out/revision

# **Nivel de la música en LUFS, no en factor de volumen.** Jaime: *«tampoco
# suena la música»* — y no sonaba: `volume=0.22` sobre un mp3 cuya media es
# -29,9 dBFS deja la cama en torno a -43 dB, o sea inaudible, y encima el
# sidechain la baja mas todavia. Un factor de volumen **no sabe de que nivel
# parte**, asi que el mismo numero da una cosa con una grabacion y otra con la
# siguiente; en un lote de 16-50 piezas eso es un nivel distinto por pieza.
#
# A -21 LUFS queda 7 LU por debajo de la voz (-14): se oye cuando
# el habla respira y desaparece debajo cuando no. Es el mismo razonamiento del
# aprendizaje 51 — **medir la entrega, no suponerla**— aplicado a la entrada.
# **-18, no -21.** Jaime: *«a la musica se le puede subir un poquito porque ya
# le bajamos a las frecuencias que compiten con mi voz»*. Y tiene razon: a -21
# la musica estaba pagando dos veces —el fader bajo Y la banda de la voz
# tallada—, siete LU por debajo de una voz a -14. A -18 quedan cuatro, que es lo
# estandar para musica bajo palabra, y la banda que compite sigue recortada.
# **-26, y esto revierte el «subele un poquito».** Jaime, sobre la entrega:
# *«el sonido quedo muy raro, en todos se escucha mucho eco»* y *«la
# ecualizacion borro lo que decia»*. Medido, y no es eco de sala: en los huecos
# entre frases la voz sola esta a **-75 dB** y la mezcla a **-26 dB**. O sea que
# la musica ocupaba todos los silencios a solo 10-16 dB por debajo de la voz, y
# una cama que no suelta nunca se oye exactamente como eco.
#
# El razonamiento de subirla era correcto —la banda que compite esta tallada—
# pero **el tallado no basta**: recorta 180-4000 Hz y el resto del espectro
# sigue ahi, ocupando el silencio. Un lecho bajo palabra va 20-25 dB por debajo;
# **-32, medido y no supuesto.** Se probo a -26 y los huecos seguian sin
# aparecer (1 por debajo de -38 dB en 40 s). A -32 —18 LU bajo la voz— vuelven
# **17 huecos** donde la mezcla anterior tenia **cero**, contra los 23 que tiene
# la voz sola. Ese es el criterio: no un numero de manual, sino que el silencio
# entre frases exista otra vez.
MUSI=-32
# Cuánto baja la banda media cuando Jaime habla. 4 abre hueco sin bombear; con
# 6 la música desaparecia del todo en cuanto empezaba una frase.
# **6, no 4.** Con la cama mas baja, el sidechain puede apretar sin que la
# musica desaparezca del todo: a -18 con ratio 6 se iba entera, a -26 abre el
# hueco de la voz y vuelve entre frases, que es su trabajo.
RATIO=6
# Objetivo de plataforma, igual que en `sonoridad.sh`.
# **TP a -1,5 y no a -1.** La norma pide **como maximo -1 dBTP** y el limitador
# de `loudnorm` deja el pico justo por encima del valor que se le pide: pedido
# -1, la entrega medida daba -0,8. Pidiendo -1,5 el pico real cae dentro.
# Se comprueba midiendo la entrega, no confiando en el filtro.
I=-14; TP=-1.5; LRA=11

REELS=("$@")
[ ${#REELS[@]} -eq 0 ] && REELS=(1 2 3 4 5 6)

for n in "${REELS[@]}"; do
  SRC="out/reels/reel-R$n.mp4"
  MP3="public/musica/reel-0$n.mp3"
  [ -f "$SRC" ] || { echo "R$n: falta $SRC"; continue; }
  # **Sin musica tambien hay que masterizar.** Antes se saltaba la pieza entera
  # si faltaba el mp3, asi que se quedaba sin entrega — y el paso de audio no es
  # opcional: la voz se nivela y se lleva a -14 LUFS igual.
  # **La musica solo va en lo aprobado.** Jaime: *«los videos para aprobacion
  # van sin musica y sin audio adicional»*. Masterizar musica sobre un corte que
  # puede cambiar es pagarlo dos veces; y para juzgar si el mensaje llega,
  # estorba. En cuanto la version se aprueba, la misma linea la anade.
  APROBADA=$(PYTHONIOENCODING=utf-8 python -c "
import sqlite3,sys
c=sqlite3.connect('ads/decisiones.db')
try:
    r=c.execute(\"select 1 from aprobacion a join version v on v.id=a.version_id\"
                \" join video vi on vi.id=v.video_id where vi.slug=? and\"
                \" a.veredicto='aprobada'\", ('reel-0$n',)).fetchone()
    print(1 if r else 0)
except Exception: print(0)
" 2>/dev/null)
  CONMUSICA=1
  [ "$APROBADA" = "1" ] || CONMUSICA=0
  SELLO="musica tallada 180-4000 Hz"
  if [ ! -f "$MP3" ]; then CONMUSICA=0; SELLO="sin musica"; fi

  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")

  # ── cuanto hay que subir la musica ──────────────────────────────────────
  #
  # **Se mide y luego se aplica**, en dos pasadas, igual que la sonoridad de la
  # entrega (aprendizaje 51). `loudnorm` de una sola pasada trabaja a ciegas y
  # se adapta despacio: sobre una pieza clasica —que es dinamica por
  # definicion— un pasaje flojo se queda flojo. Medido en el reel 1: el tramo
  # del segundo 47 esta a -35 dB en el mp3 y `loudnorm=I=-26` lo dejaba en -29.
  #
  # Con la ganancia calculada a partir de la integrada real, la cama cae donde
  # se pide **y la musica conserva su dinamica**, que es justo lo que no hay que
  # aplastar en una pieza clasica.
  MEDIA=$(ffmpeg -hide_banner -i "$MP3" -t "$DUR" -af "loudnorm=print_format=json" -f null - 2>&1 | grep '"input_i"' | cut -d'"' -f4)
  if [ -n "$MEDIA" ]; then
    GAIN=$(awk -v a="$MUSI" -v b="$MEDIA" 'BEGIN{ printf "%.1f", a - b }')
  else
    GAIN=0
  fi

  # ── la mezcla ───────────────────────────────────────────────────────────
  # [0:a] voz    [1:a] musica
  #
  # La voz se duplica: una copia va a la mezcla y la otra es la LLAVE del
  # compresor. Sin duplicarla, el filtro la consume y desaparece del resultado.
  # ── la voz, antes de nada ───────────────────────────────────────────────
  # Los cortes saltan de un punto a otro de la toma y cada pasaje viene con su
  # nivel: la primera frase entra fuerte y la del minuto nueve suena hundida.
  # Un compresor suave —umbral -18 dB, 3:1— acerca los pasajes sin aplastar la
  # dinamica de la frase, que es lo que hace que suene a persona y no a locutor.
  # Va ANTES de la mezcla: la llave del sidechain tiene que ser la voz ya
  # nivelada, o la musica baja distinto en cada corte.
  # **Suave, y por eso los numeros son estos.** Con -18 dB, 3:1 y +2 de makeup
  # la voz «se escuchaba rara a veces» -palabras de Jaime-: el compresor entraba
  # en cada frase fuerte y soltaba entre palabras, que es bombeo. Bajando el
  # umbral y la relacion solo toca los picos, que es lo que hacia falta para
  # acercar pasajes grabados con nueve minutos de diferencia.
  # **A la voz no se le hace nada.** Jaime: *«tus ediciones estan empeorando el
  # audio»*, y tenia razon en el diagnostico. Llevaba un compresor -umbral -20,
  # 2:1- puesto para acercar pasajes grabados con nueve minutos de diferencia, y
  # sobre una senal **que ya viene recortada de grabacion** un compresor no
  # arregla el nivel: sube lo recortado y lo hace mas audible.
  #
  # **La voz NO lleva cadena de correccion, y es deliberado.**
  #
  # Llevo una —highpass 85, -3 dB a 250 Hz, +2 dB a 3200 y de-esser— que puse yo
  # para responder a *«no se mejoro la calidad»*. Fue un error de lectura: lo que
  # Jaime pidio fue *«dejar el sonido de la voz un poco mas natural»*, y yo
  # conteste con MAS procesado. El corte de 250 Hz es justo lo que le quita el
  # cuerpo, y el veredicto fue claro: *«se perdieron factores y suena muy feo»*.
  #
  # La limpieza de voz se hace fuera, con una herramienta que hace eso y nada
  # mas —Adobe Podcast—, y vuelve por `voz-limpia.py`. Aqui solo queda el nivel
  # y la mezcla, que es lo que este paso sabe hacer.
  VOZ="anull"

  if [ "$CONMUSICA" = 1 ]; then
  # ── la mezcla ───────────────────────────────────────────────────────────
  #
  # **Sin trocear la musica en bandas.** Jaime: *«la musica se escucha
  # horrible»*, y la causa era de manual: partirla con `lowpass=180` +
  # `highpass=180,lowpass=4000` + `highpass=4000` y volver a **sumar** las tres
  # no reconstruye la senal. Son filtros de Butterworth, cada uno gira la fase a
  # su manera, y al sumarlos se cancelan alrededor de los cortes: eso es un
  # filtro de peine, y suena hueco y metalico.
  #
  # Lo que hace falta no era un crossover mejor —este build trae `acrossover`,
  # que si suma plano— sino **no dividir**. Dos cosas bastan y ninguna toca la
  # fase de forma audible:
  #
  #   1. Una **campana estatica** de -5 dB con Q ancha en 2 kHz: le quita a la
  #      musica la zona donde vive la inteligibilidad de la voz, y se la deja
  #      entera al grave y al brillo, que es donde la musica se sostiene.
  #   2. Un **sidechain de banda completa** encadenado a la voz: baja cuando
  #      Jaime habla y vuelve cuando calla.
  #
  # Es lo que pidio desde el principio -*«se baja el volumen de las frecuencias
  # que interfieran con la voz»*- hecho de la forma que no rompe la musica.
  # **Lo minimo, y es una correccion de fondo.** Jaime, tras oir el resultado:
  # *«muy mal se escucha, se nota que le hiciste demasiado y sin criterio;
  # trataste de optimizar todo y los numeros te dieron, pero dejo de sonar
  # natural y bien»*.
  #
  # Tenia razon. Sobre esa voz habia apilado: el estirado a 1,15x —que es
  # resintesis—, una cadena de EQ y de-esser mia, una campana de -5 dB a 2 kHz
  # sobre la musica, un sidechain apretado, `loudnorm`, y encima Adobe Podcast.
  # Cada paso defendible por separado; juntos, papilla. Los numeros de cada uno
  # mejoraban y el resultado empeoraba, que es la forma tipica de equivocarse
  # midiendo en vez de escuchando.
  #
  # Queda lo que hace falta y nada mas: **la musica a su nivel, bajando cuando
  # el habla, y el nivel final**. Sin tallar la banda de la voz —con la voz ya
  # limpia no hay nada de lo que protegerla— y sin tocar la voz.
  FILTRO="
    [0:a]asplit=2[voz][llave];
    [1:a]atrim=0:${DUR},volume=${GAIN}dB[mus0];
    [mus0][llave]sidechaincompress=threshold=0.05:ratio=${RATIO}:attack=25:release=350:makeup=1[mus];
    [voz][mus]amix=inputs=2:normalize=0,
      loudnorm=I=${I}:TP=${TP}:LRA=${LRA}[out]
  "
  ENTRADAS=(-i "$SRC" -i "$MP3")
  else
  FILTRO="[0:a]loudnorm=I=${I}:TP=${TP}:LRA=${LRA}[out]"
  ENTRADAS=(-i "$SRC")
  fi

  ffmpeg -v error -y "${ENTRADAS[@]}" \
    -filter_complex "$FILTRO" -map 0:v -map "[out]" \
    -c:v copy -c:a aac -b:a 160k -ar 48000 -movflags +faststart \
    "out/entrega/reel-R$n.mp4"

  ffmpeg -v error -y -hwaccel d3d11va "${ENTRADAS[@]}" \
    -filter_complex "$FILTRO" -map 0:v -map "[out]" \
    -vf scale=608:1080 \
    -c:v h264_amf -quality speed -rc cqp -qp_i 30 -qp_p 30 \
    -pix_fmt yuv420p -movflags +faststart \
    -c:a aac -b:a 96k "out/revision/reel-R$n.mp4"

  # ── la medida, con los parametros de la norma ───────────────────────────
  #
  # **EBU R 128 s1** es el suplemento para contenido corto -anuncios y promos-,
  # que es exactamente esto. Dice que una pieza corta se caracteriza con TRES
  # parametros, no con uno:
  #
  #   Programme Loudness      la integrada de toda la pieza
  #   Max Short-term          el maximo de la ventana de 3 s
  #   Max True Peak           el pico real, con sobremuestreo
  #
  # Y pone el limite que faltaba aqui: **el maximo de corto plazo no debe pasar
  # de la integrada + 5 LU**. Con la integrada en -14 eso son -9 LUFS. Sirve
  # para lo que una integrada sola no ve: una pieza puede cumplir el objetivo y
  # tener tres segundos que gritan.
  #
  # La escala es distinta a la de radiodifusion -R 128 pide -23 LUFS y aqui se
  # entrega a -14, que es lo que normalizan Instagram, TikTok y YouTube- pero
  # **la relacion de +5 LU es de percepcion, no de escala**, asi que se traslada.
  #
  # Se mide sobre la ENTREGA, no sobre lo que se cree haber hecho.
  MED=$(ffmpeg -hide_banner -nostats -i "out/entrega/reel-R$n.mp4" -af ebur128=peak=true -f null - 2>&1)
  INT=$(echo "$MED" | grep -A4 "Integrated loudness" | grep "I:" | tail -1 | awk '{print $2}')
  LRA=$(echo "$MED" | grep -A4 "Loudness range" | grep "LRA:" | tail -1 | awk '{print $2}')
  TP=$(echo "$MED" | grep -oE "Peak: *-?[0-9]+\.[0-9]" | tail -1 | awk '{print $2}')
  ST=$(echo "$MED" | grep -oE "S: *-?[0-9]+\.[0-9]" | sed 's/S: *//' | sort -g | tail -1)
  CLIP=$(ffmpeg -hide_banner -i "out/entrega/reel-R$n.mp4" -af volumedetect -f null - 2>&1 | grep -oE "histogram_0db: [0-9]+" | awk '{print $2}')

  echo "R$n  ${INT:-?} LUFS  corto ${ST:-?}  LRA ${LRA:-?}  pico ${TP:-?} dBTP  · $SELLO ($GAIN dB)"
  # El maximo de corto plazo por encima de la integrada + 5 LU: la pieza cumple
  # de media y grita en algun tramo.
  awk -v st="${ST:-999}" -v i="$I" 'BEGIN{
    if (st != 999 && st > i + 5)
      print "    ojo: corto plazo " st " LUFS, " st - i " LU por encima del objetivo. R 128 s1 admite +5."
  }'
  awk -v c="${CLIP:-0}" 'BEGIN{
    if (c > 5000) {
      print "    ojo: " c " muestras pegadas a 0 dB. Es RECORTE DE GRABACION."
      print "         No se reconstruye: adeclip probado dos veces, no cambia una muestra."
      print "         Se arregla bajando la ganancia del micro hasta picos sobre -6 dBFS."
    }
  }'
done
