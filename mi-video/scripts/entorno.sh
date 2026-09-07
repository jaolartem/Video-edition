#!/usr/bin/env bash
#
# Todo se produce en el disco del proyecto. Se declara aquí y no se repite.
#
# Regla de Jaime: *«todo debe ser producido en F:»*. Y no es una preferencia de
# orden: **C: estaba al 96%** y el render de dos piezas murió con «Failed to
# fetch … disk space is low», que es el gotcha 1 del proyecto por enésima vez —
# el error no menciona el disco del sistema, así que se busca donde no es.
#
# Lo que escribe fuera si no se le dice nada:
#
#   Remotion   el bundle de webpack y los assets, vía `os.tmpdir()`
#   Chrome     su caché y su user-data-dir, que salen del mismo sitio
#   ffmpeg     los intermedios, si el script no declara dónde
#
# En Windows `os.tmpdir()` lee TEMP y TMP; los procesos POSIX leen TMPDIR. Se
# ponen los tres porque la cadena mezcla node, python y bash, y basta con que uno
# no lo vea para que vuelva a C:.
#
# La ruta sale de `rutas.json` —`temporal`—, que además avisa de lo otro: **sin
# espacios**, porque una ruta con espacios rompe los subprocesos que no
# entrecomillan y Remotion se vuelve a C: sin decir nada.
#
#   source scripts/entorno.sh     # desde la raíz de mi-video

# **Y la pone `scripts/temporal.mjs`, no este fichero.**
#
# Aqui se leia `rutas.json` a mano con un `node -e`, con `F:/tmp-video` escrito
# de reserva y **sin mirar `VIDEO_TMP`**: la variable que las dos copias de
# `rutas` declaran como la que gana sobre todo se perdia justo en el guion que
# monta. Y la comprobacion de «sin espacios» y de «no en el disco de arranque»
# vivia SOLO aqui — o sea, solo para lo que se lanza desde un guion. Asi es como
# `C:` llego a 0 bytes dos veces el 6 de septiembre con un `npx remotion still`
# escrito a mano: 119 directorios y 27 GB en el TEMP del sistema.
#
# Ahora la regla vive en un modulo y la llaman los tres caminos: este fichero
# —para ffmpeg, python y el perfil de Chrome—, `remotion.config.ts` —todo lo que
# entra por el CLI— y `scripts/render.mjs` —la API de Node, donde el fichero de
# configuracion no aplica—.
#
# Se para si no se pudo: sin temporal declarado no se empieza a producir.
_EXPORTA=$(node scripts/temporal.mjs --exportar) || {
  echo "entorno.sh: el temporal no se pudo aplicar (el motivo, arriba)." >&2
  return 1 2>/dev/null || exit 1
}
eval "$_EXPORTA"
_TMP_PROY="$TMPDIR"

# **Y lo que dejaron las corridas que murieron a medias, se barre.**
#
# El temporal llego a **51 GB**: quince bundles de Remotion de 1,6 GB —cada uno
# con su copia entera de `public/`—, cuatro carpetas de `sfx` de 1,7 GB y una
# cola de assets de Remotion. Todas son carpetas por PID, y todas se borran al
# terminar; lo que no se borra es lo de la corrida que se interrumpio, y eso no
# lo recoge nadie porque el que tenia que hacerlo es el que murio.
#
# Tres cinturones, porque esto borra:
#
#   - **Solo dentro del temporal declarado**, que las comprobaciones de mas
#     abajo ya se encargan de que no sea C:.
#   - **Solo los prefijos que produce la linea** — `render-`, `bundle-`, `sfx-`,
#     `seg-` y los `remotion-*` que crea el propio renderer.
#   - **Solo si llevan mas de dos dias sin tocarse.** Ninguna corrida dura dos
#     dias, asi que no puede llevarse por delante nada vivo. Un montaje entero
#     son cuarenta minutos.
#
# Y **una vez al dia, no en cada guion**: esto lo sourcean treinta scripts y
# recorrer el temporal en cada uno seria pagar la limpieza treinta veces para no
# encontrar nada. La marca es un fichero vacio con su fecha.
# La guardia del `-n`: sin temporal, `_BARRIDO` seria «/.barrido» y el `: >`
# de abajo escribiria en la raiz. No puede pasar —`temporal.mjs` se planta
# antes—, pero una redireccion sobre una ruta que sale de una variable se
# comprueba, que es la mitad del trabajo de este fichero.
_BARRIDO="$_TMP_PROY/.barrido"
if [ -n "$_TMP_PROY" ] && [ -z "$(find "$_BARRIDO" -newermt '-1 day' 2>/dev/null)" ]; then
  _VIEJAS=$(find "$_TMP_PROY" -maxdepth 1 -type d -mtime +2     \( -name 'render-*' -o -name 'bundle-*' -o -name 'sfx-*'        -o -name 'seg-*' -o -name 'remotion-*' \) 2>/dev/null | wc -l)
  if [ "$_VIEJAS" -gt 0 ]; then
    find "$_TMP_PROY" -maxdepth 1 -type d -mtime +2       \( -name 'render-*' -o -name 'bundle-*' -o -name 'sfx-*'          -o -name 'seg-*' -o -name 'remotion-*' \)       -exec rm -rf {} + 2>/dev/null
    echo "entorno.sh: barridas $_VIEJAS carpeta(s) temporales de corridas muertas" >&2
  fi
  : > "$_BARRIDO"
fi

# **Y el perfil de Chrome, que TEMP no mueve.**
#
# Chrome escribe su perfil y sus caches en `%LOCALAPPDATA%`, no en `TEMP`: por
# eso mover lo temporal a F: no bastaba y el disco del sistema seguia siendo el
# limite. Con C: al 97% —16 GB— el render muere con «Compositor exited with code
# 3» y «Timed out while setting up the headless browser», un error que no habla
# de disco en ninguna de sus dos lineas.
#
# Es una variable de entorno de ESTE proceso: no toca la instalacion de nadie ni
# mueve un solo fichero del usuario. Cumple la regla de Jaime —*«todo debe
# guardar en F:, C: no se toca»*— en el unico sitio donde faltaba.
export LOCALAPPDATA="$_TMP_PROY/localappdata"
export APPDATA="$_TMP_PROY/appdata"
mkdir -p "$LOCALAPPDATA" "$APPDATA" 2>/dev/null || true

# **Y el perfil de Chrome, que NO lo mueve `TEMP`.**
#
# Regla de Jaime, dicha treinta veces: *«todo debe guardar en F:, C: no se
# toca»*, *«C no se debe utilizar»*.
#
# Las tres variables de arriba llevaban puestas semanas y aun asi el disco del
# sistema seguia siendo un limite: Chrome escribe su perfil, su cache de GPU y
# sus volcados en `%LOCALAPPDATA%`, que es una ruta distinta y no la toca
# `TMPDIR`. Por eso la guarda de «el temporal apunta a C:» pasaba y el montaje
# se caia igual.
#
# Se redirigen para los procesos que lanza la linea y **solo para ellos**: esto
# es un `export` de este shell, asi que no cambia nada del sistema ni de las
# otras aplicaciones. Chrome sigue ejecutandose desde donde este instalado; lo
# unico que se mueve es lo que escribe.
export LOCALAPPDATA="$_TMP_PROY/appdata/local"
export APPDATA="$_TMP_PROY/appdata/roaming"
mkdir -p "$LOCALAPPDATA" "$APPDATA"
# Python imprime en UTF-8 aunque la consola sea cp1252 (gotcha 1, otra puerta).
export PYTHONIOENCODING=utf-8

# **Ninguna ruta del proyecto vive en C:, y se comprueba TODAS.**
#
# Jaime lo ha dicho treinta veces: *«todo debe guardar en F:, C: no se toca»*,
# *«C no se debe utilizar, para eso está F»*. Esto comprobaba sólo `temporal`,
# así que la regla se cumplía en una ruta de cinco y las otras cuatro pasaban
# sin que nadie mirara. Media regla comprobada es media regla.
#
# Se para, no se avisa: un render que empieza mal tarda veinte minutos en
# fallar, y el error que da habla de disco sin decir cuál.
_EN_C=$(node -e "
  const r = JSON.parse(require('fs').readFileSync('rutas.json','utf8'));
  const mal = Object.entries(r)
    .filter(([k, v]) => typeof v === 'string' && !k.startsWith('_'))
    .filter(([, v]) => /^[Cc]:|^\/c\//.test(v))
    .map(([k, v]) => k + '=' + v);
  console.log(mal.join(' '));
" 2>/dev/null)
if [ -n "$_EN_C" ]; then
  echo "entorno.sh: hay rutas en C: y aqui no se produce en C: -> $_EN_C" >&2
  echo "  Se corrigen en rutas.json. Todo el proyecto vive en F:." >&2
  return 1 2>/dev/null || exit 1
fi
# **Que el temporal no apunte a C: y que quede sitio, lo comprueba
# `temporal.mjs`** — y ya se ha ejecutado arriba, asi que aqui no se repite.
#
# Estaba escrito dos veces, en dos idiomas: un `case` de shell para la ruta y un
# `df -m /c` para el sitio. Las dos comprobaciones son buenas y por eso importa
# donde viven: escritas aqui protegian solo a quien pasara por este fichero, que
# es exactamente el hueco por el que `C:` se lleno con un `npx remotion still`
# suelto. En el modulo protegen a los tres caminos, y el que no para —el sitio
# libre— sigue sin parar, por el mismo motivo de siempre: de seis piezas con 21
# GB libres renderizaron cuatro, y parar ahi seria bloquear la linea por un
# diagnostico sin probar.

# **Y el interprete tambien se declara aqui, por el mismo motivo que las rutas.**
#
# `npm` en Git Bash no es un binario: es un guion con `#!/usr/bin/env bash`. El
# antivirus se llevo `usr/bin/bash.exe` de la instalacion y no deja reponerlo ni
# con permisos, asi que **cualquier `npm run` moria** con
# `/usr/bin/env: 'bash': No such file or directory`. El lote entero se caia en el
# `npm run lint` de `montar.sh`, con las cinco puertas en verde y el render sin
# empezar — y desde PowerShell el mismo comando pasaba, porque alli npm usa
# `cmd`. O sea que el fallo solo aparecia por el camino que importa.
#
# `sh.exe` es el mismo binario de 2,4 MB con otro nombre, asi que aqui se pone
# una copia llamada `bash` en el temporal del proyecto —en F:, nunca en C:— y se
# antepone al PATH. Es una muleta, no el arreglo: el arreglo es sacar `bash.exe`
# de la cuarentena o reinstalar Git. Se rehace sola si el temporal se vacia.
if ! command -v bash >/dev/null 2>&1; then
  _SH=$(command -v sh)
  _BIN="${TMPDIR:-/tmp}/bin"
  _BIN=$(cygpath -u "$_BIN" 2>/dev/null || echo "$_BIN")
  mkdir -p "$_BIN"
  [ -x "$_BIN/bash.exe" ] || cp "$_SH" "$_BIN/bash.exe"
  PATH="$_BIN:$PATH"
  export PATH
  echo "entorno.sh: no hay bash; se usa una copia de sh en $_BIN (el antivirus se llevo el original)" >&2
fi
# npm arranca cada script con `$SHELL`, y Git Bash lo deja apuntando al fichero
# que ya no esta.
SHELL=$(command -v bash || command -v sh)
export SHELL
