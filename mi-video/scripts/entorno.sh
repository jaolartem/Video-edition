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

_TMP_PROY=$(node -e "console.log(JSON.parse(require('fs').readFileSync('rutas.json','utf8')).temporal)" 2>/dev/null)
: "${_TMP_PROY:=F:/tmp-video}"

export TMPDIR="$_TMP_PROY"
export TEMP="$_TMP_PROY"
export TMP="$_TMP_PROY"

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
mkdir -p "$_TMP_PROY"

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
case "$_TMP_PROY" in
  [Cc]:*|/c/*)
    echo "entorno.sh: el temporal apunta a C: ($_TMP_PROY) y todo se produce" \
         "en el disco del proyecto. Corrige 'temporal' en rutas.json." >&2
    return 1 2>/dev/null || exit 1
    ;;
esac

# **Y se mira el espacio de C:, aunque no produzcamos ahi.**
#
# La guarda de arriba comprueba que el temporal APUNTE a F:, y eso ya estaba
# puesto y pasaba. Aun asi el montaje murio: dos piezas de seis se cayeron con
# «Chrome rejecting the request because the disk space is low» con 252 GB libres
# en F: y **21 GB en C:, al 96%**. Chrome escribe su perfil y sus cachés en
# `%LOCALAPPDATA%`, que no lo mueve `TEMP`, asi que el disco del sistema sigue
# siendo un limite aunque el proyecto no produzca ahi.
#
# Jaime lo ha dicho treinta veces —*«todo debe guardar en F:, C: no se toca»*— y
# la guarda comprobaba la mitad: la ruta, no el sitio. Un render tarda veinte
# minutos en fallar por esto, asi que se mide ANTES de empezar.
_LIBRE_C=$(df -m /c 2>/dev/null | awk 'NR==2 {print $4}')
if [ -n "$_LIBRE_C" ] && [ "$_LIBRE_C" -lt 30000 ]; then
  echo "entorno.sh: quedan $((_LIBRE_C / 1024)) GB en C: y Chrome escribe su" \
       "perfil ahi pase lo que pase con TEMP. Por debajo de 30 GB el render" \
       "muere a mitad con un error que habla de disco sin decir cual." >&2
  echo "  AVISA, no para. De seis piezas con 21 GB libres renderizaron cuatro," \
       "y las dos que cayeron eran las dos mas largas: el mensaje de disco" \
       "puede estar tapando otra cosa. Parar aqui seria bloquear la linea por" \
       "un diagnostico sin probar — y ya lo hizo una vez." >&2
fi
