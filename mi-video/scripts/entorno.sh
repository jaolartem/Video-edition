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
# Python imprime en UTF-8 aunque la consola sea cp1252 (gotcha 1, otra puerta).
export PYTHONIOENCODING=utf-8
mkdir -p "$_TMP_PROY"

# Y se comprueba: si el temporal no está en el disco del proyecto, se para. Un
# render que empieza mal tarda veinte minutos en fallar.
case "$_TMP_PROY" in
  [Cc]:*|/c/*)
    echo "entorno.sh: el temporal apunta a C: ($_TMP_PROY) y todo se produce" \
         "en el disco del proyecto. Corrige 'temporal' en rutas.json." >&2
    return 1 2>/dev/null || exit 1
    ;;
esac
