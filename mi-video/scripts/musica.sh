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
#: Nivel de la cama, en LUFS. **-24.** Jaime, tras oir el lote a -20: *«la musica
#: muy alta, a este le conviene -24… bajemos la musica a -24 en todos»*, y sobre
#: el numero exacto: *«aca me dejo guiar por lo que la recomendacion tecnica diga»*.
#:
#: La recomendacion: la voz va a -14 LUFS integrados, asi que -24 la deja 10 LU
#: por debajo, que es donde una cama acompana sin competir. A -20 quedaban 6 y se
#: comia la frase.
#:
#: El -32 del principio era otra cosa: ahi la musica no se oia, y hacia falta
#: porque el ducking la aplastaba en TODO el espectro. Con la banda tallada
#: (`TALLA_*`) el sitio de la voz ya esta libre, asi que -24 se oye y no estorba.
#: **-17, y el numero esta medido en la entrega.** Jaime, oyendo reel-01 ya
#: montada: *«la musica no se escucha»*. Y no se escuchaba: en los silencios
#: REALES de la voz la cama estaba a -29,3 dBFS contra los -11,1 de la voz.
#: **Dieciocho decibelios**, cuando un lecho bajo palabra vive entre 12 y 16.
#:
#: (Mi primera medida dio 10 dB y era falsa: tome por «huecos» el quintil mas
#: flojo de la voz, que incluye respiraciones y finales de frase. El silencio
#: real se busca por umbral, no por percentil.)
#:
#: -17 deja el pasaje mas fuerte 3 LU bajo la voz y la cama tipica unos 13 dB
#: por debajo. No tapa: la banda donde vive la voz sigue recortada 18-23 dB por
#: `TALLA_BANDAS`, asi que lo que sube es el cuerpo y el aire de la obra, no lo
#: que compite con la palabra.
#: **Y -15, que es el «poquito» que pidio despues.** Jaime, sobre la cama ya
#: subida: *«hay que subirle un poquito a la musica»*. De -22 a -17 fue lo que
#: la medida pedia —de 18 dB bajo la voz a 13—; los dos ultimos los pone su
#: oido, que es el que manda, y dejan la cama unos 11 dB por debajo.
#:
#: Es el borde alto de lo que aguanta un lecho bajo palabra, y aguanta por una
#: razon concreta: la banda de la voz sigue recortada 18-23 dB. Sin ese recorte,
#: -15 seria musica encima de la frase.
# **Y se puede fijar desde fuera.** Un solo numero no puede servir a siete obras
# distintas: medido, -15 dio de 2,3 a 19,7 dB de separacion de la voz segun la
# obra —a reel-06 le «lastimaba», en reel-03 «no se escuchaba»—. Lo que gobierna
# es la DISTANCIA a la voz, y hasta que ese bucle viva aqui, `MUSI` se puede
# poner por pieza desde fuera en vez de editar el fichero.
MUSI_FIJO="${MUSI:-}"
#: Donde y cuanto se le quita a la musica para que no pise la voz.
#: 300 Hz son los armonicos que enturbian; 2 kHz, las consonantes.
# ── la talla: bajar SOLO las frecuencias que compiten con la voz ─────────────
#
# Jaime: *«bajale a las frecuencias que compiten con mi voz tambien, eso es bien
# importante (no agregues efectos o mascaras al sonido, solo baja el volumen a
# esas frecuencias y ya)»*. Asi que aqui no hay sidechain, ni ducking, ni
# compresor: son campanas fijas. La musica suena igual todo el rato, solo que
# con menos energia donde estorba.
#
# **Y las bandas estan MEDIDAS, no sacadas de un manual.** Espectro de su voz
# (`reel-02-voz.wav`) contra el de la musica, por bandas de tercio de octava,
# ambos normalizados a su propio maximo:
#
#      banda Hz     VOZ   MUSICA
#      125-200     -3.3     -1.6   <- barro debajo de la voz
#      200-315     -1.1     -5.6
#      315-500      0.0     -0.3   <- PICO de su voz y casi el de la musica
#      500-800     -6.0     -2.9   <- cuerpo
#      800-1250   -16.0     -4.3
#     1250-2000   -11.9      0.0   <- PICO de la musica sobre su segundo formante
#
# Las dos campanas que habia —300 Hz y 2000 Hz, anchos 1.0 y 0.9— caian al lado:
# estrechas, y la de 2000 por encima de donde la musica pica de verdad. Estas
# cuatro cubren las cuatro colisiones con su profundidad proporcional al choque.
#
# El ancho va en octavas (`t=o`): una campana de 1 octava a 400 Hz cubre de 280
# a 570, que es la banda entera y no un punto.
#
# **La cama sube y la talla baja, y no es contradictorio: es el arreglo.** Jaime,
# despues de oir la primera version tallada: *«eso es igual para todas las
# piezas, a -22 pero con las frecuencias que compiten bien abajo»*.
#
# Bajar la musica entera para que no tape la voz cuesta lo que la musica venia a
# aportar: a -26 la cama aporta poco fuera de la voz tambien. Subiendola a -22 y
# hundiendo SOLO las cuatro bandas del choque, la musica recupera cuerpo donde no
# estorba —el grave por debajo de 125 y el brillo por encima de 2,5k— y sale de
# en medio donde si. Es la misma idea que la talla, llevada hasta el final: no se
# decide cuanta musica hay, se decide DONDE la hay.
TALLA_BANDAS="160:1.2:-20 400:1.3:-20 700:1.1:-18 1600:1.4:-23"
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
# **El limitador va SOBREMUESTREADO, y es la diferencia entre pasar y clipear.**
#
# `alimiter` sujeta el pico de MUESTRA; lo que se publica se mide en pico REAL
# —entre muestras— y encima el AAC a 160k reconstruye por encima de lo que
# entro. Con la musica sumada (`amix=normalize=0`) el margen se come del todo:
# reel-06 salio a **+0,2 dBTP** y reel-02 a -0,5, las dos por encima del -1,5
# que exige la entrega, con el limitador puesto y trabajando.
#
# Medido sobre reel-06, misma fuente y mismo AAC:
#
#     alimiter a secas                 -> pico -1,7 dBFS
#     a 192 kHz, limitar, y volver     -> pico -1,4 dBFS   (mismo -14,8 LUFS)
#
# Limitar a 4x captura los picos que caen entre muestras, y no cuesta nivel: la
# integrada no se mueve. Es el mismo truco que usa cualquier limitador de
# masterizado, escrito con lo que hay.
# **Y la entrega va a 192k, no a 160.** Es la unica razon por la que el pico se
# pasaba, y costo encontrarla porque el limitador era inocente. Medido sobre
# reel-06, misma fuente y mismo filtro, midiendo ANTES y DESPUES de codificar:
#
#     antes de codificar          -2,0 dBFS   <- el limitador cumple
#     AAC 160k (por defecto)      +0,2 dBFS   <- CLIPEA
#     AAC 160k `aac_coder=fast`   -1,2 dBFS
#     AAC 192k                    -1,8 dBFS   <- pasa, mismo -14,7 LUFS
#     AAC 256k                    -1,9 dBFS
#
# El codificador RECONSTRUYE por encima de lo que entra —2,2 dB aqui— porque el
# material sale del limitador denso y a tope. Es la sobreoscilacion conocida del
# AAC a bajo bitrate, y no se arregla limitando mas: eso cuesta un LU de nivel y
# sigue dependiendo del contenido. Se arregla dandole bits.
#
# Reel-02 salio a -0,5 dBTP y reel-06 a +0,2 por esto, con el limitador puesto
# y trabajando. La guarda los paro — que es lo unico que funciono aqui.
I=-14; TP=-1.5; LRA=11

# **La velocidad del montaje se pregunta, no se escribe aqui.** Vive en
# `beats.VELOCIDAD` —«estaba repetido en seis ficheros, que es como se acaba
# teniendo dos velocidades distintas en el mismo montaje»— y este paso la
# necesita para una sola cosa: saber si existe un acelerado que leer.
VELOCIDAD=$(python -c "import sys; sys.path.insert(0,'scripts'); import beats; print(beats.VELOCIDAD)" 2>/dev/null || echo 1.0)

REELS=("$@")
[ ${#REELS[@]} -eq 0 ] && REELS=(1 2 3 4 5 6)

for n in "${REELS[@]}"; do
  # **Lee lo que dejo la aceleracion, no el render.**
  #
  # El diseno esta escrito dos pasos mas arriba, en `voz-limpia.py`: se acelera
  # la pieza con su voz y **la musica entra despues, a su velocidad natural,
  # sobre el resultado**. Pero esto leia `out/reels/` —el render a velocidad
  # normal— y escribia en `out/entrega/`, o sea encima del acelerado: lo
  # deshacia.
  #
  # Se veia en las duraciones y en nada mas: R1 salia a 93,1 s cuando el paso
  # habia dicho 80,97, y R3 a 49,5 que si era la buena. Dependia de cual corriera
  # ultima, asi que la misma corrida entregaba unas aceleradas y otras no.
  #
  # **Y se lee el acelerado SOLO SI la aceleracion existe.** La condicion era
  # `-f`: que hubiera entrega. Como este mismo paso escribe en `out/entrega/`,
  # en cuanto habia una el paso pasaba a leerse a si mismo **para siempre**, y
  # el render fresco de `out/reels/` no se volvia a abrir nunca.
  #
  # Cuando Jaime revoco la aceleracion —`beats.VELOCIDAD` es 1, y
  # `voz-limpia._acelerar` ya no escribe nada— eso dejo de ser una preferencia y
  # paso a ser un congelador: las siete entregas se quedaron en la version de
  # 1,15x. Medido el 4 de septiembre, entrega/render = 0,870 en las siete, que
  # es 1/1,15 clavado. Se remasterizaba, se median los LUFS, pasaba la guarda —
  # y lo que Jaime revisaba era la pieza de antes, estirada.
  #
  # La pregunta no es si hay entrega: es si alguien la genero, y eso lo dice la
  # misma velocidad que la genera. Fecha no sirve —este paso la deja siempre mas
  # nueva que el render.
  RENDER="out/reels/reel-R$n.mp4"
  SRC="$RENDER"
  if awk -v v="$VELOCIDAD" 'BEGIN{exit !(v > 1.0)}' \
     && [ -f "out/entrega/reel-R$n.mp4" ]; then
    # **El nivel de la cama es POR PIEZA, y sale de su fichero.**
  #
  # Un solo numero no puede servir a siete obras distintas: con -15 en todas, la
  # separacion real entre la cama y su voz salio entre 2,3 y 19,7 dB. Para
  # dejarlas todas a 14 dB —donde esta reel-04, la unica que nunca levanto
  # queja— reel-02 necesita -0,2 y reel-03 necesita -20,8. Veintiun decibelios
  # entre dos piezas del mismo lote.
  #
  # `MUSI` desde fuera sigue mandando: sirve para tantear una pieza sin tocar el
  # fichero. Lo que ya no vale es el numero escrito aqui dentro.
  # **Y se le pregunta a `cama.py`, no se abre el JSON aqui.** Un `json.load`
  # escrito en la linea de ordenes es una segunda lectura del mismo fichero, y
  # dos lecturas es como `objetivo_db` pudo decir 16 mientras el bucle que
  # mezcla apuntaba a 14.
  MUSI="${MUSI_FIJO:-$(python scripts/cama.py --nivel "$(printf 'reel-%02d' "$n")" 2>/dev/null || echo -15)}"
  # **Y se mezcla sobre el ACELERADO SIN MUSICA, nunca sobre la entrega.**
  #
  # Esto tomaba `out/entrega` —que ya lleva musica— asi que cada corrida le
  # sumaba otra capa, y `loudnorm` devolvia la voz a -14 mientras la cama se
  # acumulaba debajo. Medido en reel-06 con el MISMO valor declarado: **27,1 dB
  # de separacion con una capa y 13,6 en la entrega que Jaime oyo**. Trece
  # decibelios y medio sin tocar el numero — esa es la causa real de «la musica
  # sigue muy fuerte», y no el nivel.
  #
  # Peor: invalidaba la medida. Los siete valores de `cama.json` se calibraron
  # sobre mezclas apiladas, o sea contra un fantasma.
  #
  # `voz-limpia` deja aqui la pieza acelerada y todavia muda de musica. Si no
  # esta, se guarda ahora desde la entrega — es la unica vez que se puede dar
  # por buena, y a partir de ahi mezclar es idempotente.
  SINMUS="out/entrega/.sin-musica"
  mkdir -p "$SINMUS"
  [ -f "$SINMUS/reel-R$n.mp4" ] || cp "out/entrega/reel-R$n.mp4" "$SINMUS/reel-R$n.mp4"
  SRC="$SINMUS/reel-R$n.mp4"
  fi
  MP3="public/musica/reel-0$n.mp3"
  [ -f "$SRC" ] || { echo "R$n: falta $SRC"; continue; }
  # **Sin musica tambien hay que masterizar.** Antes se saltaba la pieza entera
  # si faltaba el mp3, asi que se quedaba sin entrega — y el paso de audio no es
  # opcional: la voz se nivela y se lleva a -14 LUFS igual.
  # **Ya no hay puerta de aprobacion.** Jaime: *«nos ahorramos el proceso de
  # aprobacion, de una renderizas con todas las indicaciones»*, y despues:
  # *«simplificamos puerta de aprobacion»*. Antes esto partia la linea en dos
  # caminos —entrega para aprobar sin musica, y final con ella— y ese desdoble
  # era la mitad de las ramas de este paso y del spec.
  #
  # Ahora la unica condicion es la que siempre tuvo sentido: **que exista el
  # mp3 de la pieza**. Sustituye a la regla anterior, no la incumple: aquella
  # existia para no masterizar musica sobre un corte que podia cambiar, y el
  # decidio pagar eso a cambio de una sola pasada.
  CONMUSICA=1
  [ -f "$MP3" ] || CONMUSICA=0
  # **El sello sale de lo que se hizo, no de lo que se pensaba hacer.** Estaba
  # puesto a «musica tallada» ANTES de mirar si la pieza estaba aprobada, asi
  # que una entrega sin musica se anunciaba con musica. El audio salia bien y
  # la linea de parte decia otra cosa: es la averia de siempre —la etiqueta
  # contra el artefacto— en el sitio donde se informa.
  # El sello dice lo que el filtro HACE. Decia «tallada 180-4000 Hz» cuando
  # el tallado se habia quitado y solo quedaba el ducking.
  if [ "$CONMUSICA" = "1" ]; then
    SELLO="musica con su pasaje mas fuerte a ${MUSI} LUFS, tallada en ${TALLA_BANDAS}";
  else SELLO="sin musica (no hay mp3 para esta pieza)"; fi

  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SRC")

  # ── cuanto hay que subir la musica ──────────────────────────────────────
  #
  # **Se mide y luego se aplica**, en dos pasadas, igual que la sonoridad de la
  # entrega (aprendizaje 51). `loudnorm` de una sola pasada trabaja a ciegas y
  # se adapta despacio: sobre una pieza clasica —que es dinamica por
  # definicion— un pasaje flojo se queda flojo. Medido en el reel 1: el tramo
  # del segundo 47 esta a -35 dB en el mp3 y `loudnorm=I=-26` lo dejaba en -29.
  #
  # **Y se ancla en el PASAJE MAS FUERTE, no en la media.** Aqui estaba el fallo
  # que Jaime oia: *«no creo que este a -24, revisa bien»*. Tenia razon por los
  # dos lados y ninguno era el que parecia.
  #
  # Medido sobre las piezas de hoy, con la cadena entera:
  #
  #     integrada real   -27,3  -28,0  -27,7 LUFS   <- 3,5 dB BAJO lo declarado
  #     pasaje mas fuerte -23,9  -25,0             <- pegado al objetivo
  #     rango              6,7   11,8 dB
  #
  # O sea: la media caia por debajo de `MUSI` —la talla de frecuencias se aplica
  # DESPUES de la ganancia y baja otros 3,5 dB— y aun asi los crescendos
  # aterrizaban en -24. Con la ganancia atada a la media, una pieza clasica deja
  # sus pasajes fuertes donde caigan, y eso es lo que se oye encima de la voz.
  # Un promedio no lo puede evitar: describe el conjunto, no el momento.
  #
  # Ahora se mide el **maximo de sonoridad a corto plazo (S) ya con la talla
  # puesta**, y la ganancia lleva ESE punto a `MUSI`. La dinamica se conserva
  # entera —no hay compresor de por medio, solo un desplazamiento— y lo que se
  # garantiza es el techo, que es lo que compite con la voz.
  TALLA=$(for B in $TALLA_BANDAS; do
      IFS=: read -r HZ ANCHO DB <<< "$B"
      printf "equalizer=f=%s:t=o:w=%s:g=%s," "$HZ" "$ANCHO" "$DB"
    done | sed 's/,$//')
  # **Y de que minuto de la obra se saca.** Fijar el climax en `MUSI` garantiza
  # un techo y no un suelo: una sinfonia con doce decibelios entre su reposo y
  # su crescendo pasa casi todo el tiempo muy por debajo del numero declarado, y
  # eso es lo que Jaime oyo como *«la musica no se escucha»*.
  #
  # La salida no es comprimir —*«no agregues efectos o mascaras al sonido»*—
  # sino **elegir el tramo**: una obra dura entre cinco y once minutos y aqui
  # hacen falta ochenta segundos. `cama.py` busca el pasaje que se queda quieto,
  # y sobre ese la misma regla del techo deja tambien un suelo alto.
  DESDE=$(python scripts/cama.py "$MP3" "$DUR" "$TALLA" 2>/dev/null || echo 0)
  FUERTE=$(ffmpeg -hide_banner -nostats -ss "${DESDE:-0}" -i "$MP3" -t "$DUR" -af "${TALLA},ebur128" -f null - 2>&1     | sed -n 's/.*S: *\(-\?[0-9.]*\).*//p' | awk '$1 > -70 { if (m == "" || $1 > m) m = $1 } END { if (m != "") printf "%.1f", m }')
  if [ -n "$FUERTE" ]; then
    GAIN=$(awk -v a="$MUSI" -v b="$FUERTE" 'BEGIN{ printf "%.1f", a - b }')
  else
    # Respaldo: si `ebur128` no contesta, la media de siempre. Peor, pero no
    # deja la pieza sin musica ni con ganancia 0, que seria dejarla a tope.
    MEDIA=$(ffmpeg -hide_banner -i "$MP3" -t "$DUR" -af "loudnorm=print_format=json" -f null - 2>&1 | grep '"input_i"' | cut -d'"' -f4)
    GAIN=$(awk -v a="$MUSI" -v b="${MEDIA:-$MUSI}" 'BEGIN{ printf "%.1f", a - b }')
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
  #
  # ── y el remate, que SI lleva tratamiento y lo pidio el ──────────────────
  #
  # Jaime: *«que cambie mi voz en los punchlines»*. Es lo contrario de lo de
  # arriba y por tres motivos, no por capricho: **va sobre un tramo declarado**
  # —1,2 s de una pieza de noventa—, **lo pidio el con esas palabras**, y **es un
  # recurso, no una correccion**: se tiene que notar, que es medio efecto.
  #
  # Y no choca con *«no agregues efectos o mascaras al sonido, solo baja el
  # volumen a esas frecuencias»*: aquello es de la MUSICA y de las bandas que
  # compiten con la voz, y sigue vivo tal cual en `TALLA_BANDAS`.
  #
  # Se aplica AQUI porque aqui vive la mezcla —lo mismo que la musica, y por lo
  # mismo: Remotion no tiene la voz como senal separada—. Cada filtro sale con
  # `enable='between(t,a,b)'`, asi que fuera de la ventana esta en derivacion y
  # la pista pasa sin tocar. **Sin declaracion contesta `anull`**, o sea la
  # cadena exacta de antes de que esto existiera: quitar la declaracion devuelve
  # la voz intacta sin que nadie deshaga nada.
  #
  # `--velocidad` porque `SRC` puede ser el acelerado: las ventanas salen del
  # reloj del montaje y ahi ya no son las mismas.
  VOZ=$(python scripts/dominio/remate.py "$n" --filtro --velocidad "$VELOCIDAD") \
    || VOZ="anull"
  [ -z "$VOZ" ] && VOZ="anull"
  # **Y el sello lo dice**, por la misma razon que dice si lleva musica: el
  # renglon de parte tiene que describir el fichero que salio, no la intencion.
  # Se cuentan las VENTANAS —cada trato son tres o cuatro filtros con el mismo
  # `enable`— para no anunciar cuatro remates donde hay uno.
  TRATADOS=$(printf '%s' "$VOZ" | grep -oE "between\(t,[0-9.]+," | sort -u | wc -l | tr -d ' ')
  if [ "${TRATADOS:-0}" -gt 0 ]; then
    SELLO="$SELLO · voz tratada en $TRATADOS remate(s)"
  fi

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
  # **Se le baja la banda de la voz, y NO se le hace nada mas.** Jaime:
  # *«bajandole el volumen a las frecuencias que compiten con mi voz (no
  # haciendo ningun efecto solo bajando esas frecuencias)»*.
  #
  # Asi que el `sidechaincompress` sale: agachar la musica cada vez que el
  # habla es un efecto —se oye respirar— y ademas trabaja en todo el espectro,
  # cuando el estorbo esta en dos franjas concretas. Con EQ fija la cama suena
  # igual de alta todo el rato y simplemente no ocupa el sitio de la voz.
  #
  # Dos campanas, medidas contra SU voz: la fundamental esta en 90 Hz, asi que
  # los armonicos que enturbian caen sobre 300; y la inteligibilidad —las
  # consonantes— vive entre 1,5 y 4 kHz, con el centro en 2.
  FILTRO="
    [1:a]atrim=0:${DUR},volume=${GAIN}dB,${TALLA}[mus];
    [0:a]${VOZ}[dicho];
    [dicho][mus]amix=inputs=2:normalize=0,
      loudnorm=I=${I}:TP=${TP}:LRA=${LRA},aresample=192000,alimiter=limit=-2dB:level=disabled,aresample=48000[out]
  "
  # **Y la musica entra por donde `cama.py` dijo.** Medir el tramo elegido y
  # luego mezclar desde el segundo cero seria elegir un pasaje y usar otro: la
  # ganancia saldria calculada sobre musica que no suena. Es la averia de este
  # proyecto en pequeno —un dato que se calcula y no llega a donde se usa— y por
  # eso el `-ss` va aqui tambien, pegado a la misma variable.
  ENTRADAS=(-i "$SRC" -ss "${DESDE:-0}" -i "$MP3")
  else
  FILTRO="[0:a]${VOZ},loudnorm=I=${I}:TP=${TP}:LRA=${LRA},aresample=192000,alimiter=limit=-2dB:level=disabled,aresample=48000[out]"
  ENTRADAS=(-i "$SRC")
  fi

  # **Por temporal: la fuente y el destino son el mismo fichero.**
  #
  # Desde que la musica lee el acelerado —que ya vive en `out/entrega/`—
  # escribir ahi directamente es leer y escribir el mismo mp4, y ffmpeg lo
  # rechaza con «Output same as Input». Se escribe al lado y se mueve encima.
  ffmpeg -v error -y "${ENTRADAS[@]}" \
    -filter_complex "$FILTRO" -map 0:v -map "[out]" \
    -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart \
    "$TMPDIR/r$n-mus.mp4" \
    && mv -f "$TMPDIR/r$n-mus.mp4" "out/entrega/reel-R$n.mp4"

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

  # ── segunda pasada: se MIDE y se corrige, no se supone ──────────────────
  #
  # `loudnorm` de una sola pasada trabaja a ciegas y se queda corto en material
  # comprimido. Este fichero ya lo sabia —lo dice arriba, sobre la musica, y por
  # eso la cama se calcula midiendo primero— y la ENTREGA seguia con una sola
  # pasada: reel-02 salia a -15,1 LUFS con el objetivo en -14, fuera de la
  # tolerancia de 1 LU, y el paso terminaba con exito.
  #
  # Con la integrada ya medida arriba, corregir es una ganancia lineal. No se
  # vuelve a normalizar —eso reabriria el mismo problema—: se desplaza, que es
  # exacto y no toca la dinamica. El limitador se mantiene por si el
  # desplazamiento acerca algun pico.
  if [ -n "$INT" ]; then
    FALTA=$(awk -v i="$INT" -v o="$I" 'BEGIN{ d=o-i; printf "%.2f", d }')
    SUBE=$(awk -v d="$FALTA" 'BEGIN{ print (d>0.3 || d<-0.3) ? 1 : 0 }')
    if [ "$SUBE" = "1" ]; then
      ffmpeg -y -v error -i "out/entrega/reel-R$n.mp4"         -af "volume=${FALTA}dB,aresample=192000,alimiter=limit=-2dB:level=disabled,aresample=48000"         -c:v copy -c:a aac -b:a 192k "$TMPDIR/r$n-nivel.mp4"         && mv -f "$TMPDIR/r$n-nivel.mp4" "out/entrega/reel-R$n.mp4"         && echo "R$n  segunda pasada: ${FALTA} dB para llegar a ${I} LUFS"
      MED=$(ffmpeg -hide_banner -nostats -i "out/entrega/reel-R$n.mp4" -af ebur128=peak=true -f null - 2>&1)
      INT=$(echo "$MED" | grep -A4 "Integrated loudness" | grep "I:" | tail -1 | awk '{print $2}')
    fi
  fi
  LRA=$(echo "$MED" | grep -A4 "Loudness range" | grep "LRA:" | tail -1 | awk '{print $2}')
  # **`PICO`, no `TP`.** Esta linea reasignaba `TP` —que es el OBJETIVO, -1.5,
  # declarado arriba— con el pico medido. Y la comprobacion de abajo recibia
  # `lim="$TP"`, o sea el pico comparado consigo mismo: `0.2 > 0.2 + 0.5`,
  # siempre falso. La guarda del numero que define la entrega **no podia saltar
  # nunca**, y reel-06 salio a +0,16 dBTP sin que nadie lo dijera.
  PICO=$(echo "$MED" | grep -oE "Peak: *-?[0-9]+\.[0-9]" | tail -1 | awk '{print $2}')
  # **Y si el pico real se pasa, se BAJA — no se avisa y se muere.**
  #
  # `alimiter` sujeta el pico de MUESTRA y lo que se publica se mide en pico
  # REAL: entre dos muestras cabe una cresta mas alta que las dos. Con la voz
  # tratada eso deja de ser teorico —el realce de +5,9 dB en 1,4-2 kHz de
  # `megafono` fabrica justo esas crestas— y reel-05 salio a **+0,3 dBTP**,
  # clipeando.
  #
  # Habia maquinaria para esto y solo se usaba con la sonoridad: se mide, se
  # corrige, se vuelve a medir. Se le da tambien al pico, que es el otro numero
  # que define la entrega.
  SOBRA=$(awk -v p="${PICO:-999}" -v t="$TP" 'BEGIN{ if (p != 999 && p > t) printf "%.1f", p - t }')
  if [ -n "$SOBRA" ]; then
    ffmpeg -y -v error -i "out/entrega/reel-R$n.mp4"       -af "volume=-${SOBRA}dB,aresample=192000,alimiter=limit=${TP}dB:level=disabled,aresample=48000"       -c:v copy -c:a aac -b:a 192k "$TMPDIR/r$n-pico.mp4"       && mv -f "$TMPDIR/r$n-pico.mp4" "out/entrega/reel-R$n.mp4"       && echo "R$n  pico: -${SOBRA} dB para bajar de ${TP} dBTP"
    MED=$(ffmpeg -hide_banner -nostats -i "out/entrega/reel-R$n.mp4" -af ebur128=peak=true -f null - 2>&1)
    INT=$(echo "$MED" | grep -oE "I: *-?[0-9]+\.[0-9]" | tail -1 | awk '{print $2}')
    PICO=$(echo "$MED" | grep -oE "Peak: *-?[0-9]+\.[0-9]" | tail -1 | awk '{print $2}')
  fi
  ST=$(echo "$MED" | grep -oE "S: *-?[0-9]+\.[0-9]" | sed 's/S: *//' | sort -g | tail -1)
  CLIP=$(ffmpeg -hide_banner -i "out/entrega/reel-R$n.mp4" -af volumedetect -f null - 2>&1 | grep -oE "histogram_0db: [0-9]+" | awk '{print $2}')

  echo "R$n  ${INT:-?} LUFS  corto ${ST:-?}  LRA ${LRA:-?}  pico ${PICO:-?} dBTP  · $SELLO ($GAIN dB)"
  # **Y la integrada y el pico, que es lo que define la entrega.**
  #
  # Aqui se vigilaba el corto plazo y el recorte de grabacion, pero no los dos
  # numeros que la entrega tiene que cumplir. Reel-01 salio a -9,88 LUFS con
  # pico +0,19 dBTP —cuatro LU de mas y clipeando por encima de cero— y ningun
  # aviso lo dijo: se juzgo la pieza con el audio reventado.
  #
  # Se mide la ENTREGA y se PARA, no se avisa. Un nivel mal no se ve en el
  # parte: se oye tarde, cuando alguien ya la aprobo o la publico.
  # Va con `print` y no con `printf`: un salto de linea escapado dentro de las
  # comillas, escrito como salto real, aborta
  # awk con «unterminated string», y con `set -e` eso se lleva por delante el
  # resto del paso. Es la misma nota que ya esta en `montar.sh`.
  awk -v i="${INT:-999}" -v tp="${PICO:-999}" -v obj="$I" -v lim="$TP" 'BEGIN{
    mal = 0
    if (i != 999 && (i - obj > 1 || obj - i > 1)) {
      print "    FUERA: la entrega esta a " i " LUFS y el objetivo es " obj " (tolerancia 1 LU)."
      mal = 1
    }
    if (tp != 999 && tp > lim + 0.5) {
      print "    FUERA: pico real " tp " dBTP, por encima de " lim "."
      mal = 1
    }
    if (mal) {
      print "    La entrega no paso por el nivelado, o algo la toco despues."
      exit 1
    }
  }' || MALAS="$MALAS R$n"
  # **Una pieza mala no se lleva por delante a las que faltan.** Con `set -e`,
  # el `exit 1` de esa comprobacion abortaba el bucle: reel-05 clipeo y reel-06
  # y reel-07 se quedaron **sin masterizar**, o sea al nivel del corte. Es el
  # mismo defecto que ya cerre en `voz-limpia` —el paso que solo sabe terminar
  # el caso bueno deja el malo a medias, y de paso a los que venian detras—.
  # Se apunta cual fallo, se sigue con las demas, y se falla al final.
  # El maximo de corto plazo por encima de la integrada + 5 LU: la pieza cumple
  # de media y grita en algun tramo.
  awk -v st="${ST:-999}" -v i="$I" 'BEGIN{
    if (st != 999 && st > i + 5)
      print "    ojo: corto plazo " st " LUFS, " st - i " LU por encima del objetivo. R 128 s1 admite +5."
  }'
  # ── la cola: la pieza no se corta encima de la ultima palabra ───────────
  #
  # Jaime, sobre reel-06: *«al final dice el link esta a...»*. No era el corte:
  # era que **la pieza se acaba mientras el todavia habla**. Medido sobre las
  # siete entregas, el ultimo sonido estaba a **0,02 s del final** en seis de
  # ellas y a 0,26 en la otra. Cero cola.
  #
  # Y no es de una pieza: le pasa a cualquiera cuyo ultimo tramo acabe donde
  # acaba la voz, que es siempre — el corte se hace pegado a la palabra a
  # proposito. Asi que se arregla aqui, para todas.
  #
  # Se congela el ultimo frame y se anade silencio: la imagen no parpadea y la
  # frase termina de sonar. Es lo que hace cualquier montaje, y lo que faltaba.
  COLA=$(python scripts/cama.py --cola 2>/dev/null || echo 0.6)
  ffmpeg -y -v error -i "out/entrega/reel-R$n.mp4"     -filter_complex "[0:v]tpad=stop_mode=clone:stop_duration=${COLA}[v];[0:a]apad=pad_dur=${COLA}[a]"     -map "[v]" -map "[a]" -c:v h264_amf -b:v 12M -c:a aac -b:a 192k     "$TMPDIR/r$n-cola.mp4" 2>/dev/null     && mv -f "$TMPDIR/r$n-cola.mp4" "out/entrega/reel-R$n.mp4"     && echo "R$n  cola de ${COLA}s: la ultima palabra termina de sonar"

  # ── y la separacion de la cama, que es la decision que se declara ───────
  #
  # **`objetivo_db` se declaraba y no se comprobaba nunca.** El fichero decia 16
  # y la entrega media otra cosa, porque `MUSI` es un NIVEL y la separacion es
  # un RESULTADO: la ganancia lleva el pasaje mas fuerte de la obra al numero
  # declarado sin mirar la voz, asi que dos obras con el mismo `MUSI` salen a
  # distancias distintas. Medido hoy con -19 para las dos: reel-04 a 15,8 dB y
  # reel-06 a 28,8. Doce decibelios de diferencia con el mismo numero puesto.
  #
  # Es la averia de siempre —lo declarado en un sitio y lo entregado en otro—, y
  # la unica forma de que no vuelva es medir la ENTREGA y decirlo. No para el
  # lote: una pieza fuera es una pieza que hay que oir, no un fallo de build.
  OBJ=$(python scripts/cama.py --objetivo 2>/dev/null || echo "")
  SEP=$(python -c "import sys;sys.path.insert(0,'scripts');import remezclar as R;d=R.distancia('out/entrega/reel-R$n.mp4',R.voz_de('reel-%02d'%$n)[0]);print('' if d is None else round(d,1))" 2>/dev/null || echo "")
  awk -v s="${SEP:-}" -v o="${OBJ:-}" -v n="$n" 'BEGIN{
    if (s == "" || o == "") { print "    ojo: NO SE PUDO MEDIR la separacion de la cama — casi siempre es que el stem de voz es de otro corte, y entonces la medida se niega a contestar en vez de dar un numero falso (C-243). Mira las duraciones antes de tocar el nivel."; exit }
    d = s - o; if (d < 0) d = -d
    printf "R%s  cama a %s dB de la voz (objetivo %s)%s\n", n, s, o,
      (d > 1.5 ? "  · FUERA: sube o baja su MUSI en src/brand/cama.json" : "")
  }'

  awk -v c="${CLIP:-0}" 'BEGIN{
    if (c > 5000) {
      print "    ojo: " c " muestras pegadas a 0 dB. Es RECORTE DE GRABACION."
      print "         No se reconstruye: adeclip probado dos veces, no cambia una muestra."
      print "         Se arregla bajando la ganancia del micro hasta picos sobre -6 dBFS."
    }
  }'
done

# **Y al final se dice, con nombres.** Apuntar cual fallo y salir 0 seria la
# peor de las dos: el paso diria que si y la pieza saldria al nivel del corte.
# `voz-limpia.py` ya comprueba que el nivelado conteste por todas, asi que aqui
# basta con no callarlo y devolver el codigo.
if [ -n "$MALAS" ]; then
  echo ""
  echo "musica: fuera de rango:$MALAS. Las demas quedaron bien."
  exit 1
fi
