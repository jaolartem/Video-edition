#!/usr/bin/env bash
# **La linea, de un tiron y desde cualquier sesion.** C-548.
#
#   bash scripts/arrancar.sh 18 19 20 21 22
#
# Jaime: *«que funcione en cualquier sesion, de un solo tiron y sin
# problemas»*. Lo que lo impedia no era un paso roto: eran cinco condiciones
# que solo sabia quien ya las habia sufrido —que bash.exe exista, que el CLI
# tenga credencial (solo la tiene en el panel Terminal), que el temporal no
# este en C:, que la cinta este copiada, que `DISPARO_APAGADO` no siga puesto—
# y cada una fallaba a mitad, con la pieza a medias y un motivo que no decia
# cual. Aqui se comprueban todas ANTES de mover nada, y si falta una se para
# con lo que hay que hacer. No se sigue a medias.
#
# Las piezas se dicen siempre: el lote vivo cambia, y una lista por defecto
# escrita aqui es la que envejecio en `pipeline.sh` y `montar-lote.sh`.
cd "$(dirname "$0")/.." || exit 1
# Con sus argumentos (C-569): pasaba sólo el codigo, y `cola.arranca` y la
# comprobacion de cintas recibian una lista vacia sin decir nada.
_py() { local c="$1"; shift; PYTHONIOENCODING=utf-8 python -c "import sys; sys.path.insert(0, 'scripts'); $c" "$@"; }

# **`--agentes`: los oficios los contesta la sesion, no el CLI por bash.**
# Jaime, 18-10-2026: *«reemplaza la accion del bash con agentes tuyos y limita
# el tope de tokens»*. Los pedidos quedan escritos y la sesion lanza un agente
# por buzon con `python scripts/dominio/cola.py --lote N…`, con el encargo de
# revision y su tope. Sin CLI no hace falta el panel Terminal (C-552).
# **Donde vaya, no sólo el primero** (C-675): `arrancar.sh 23 --agentes` se lo
# pasaba al disparador como si fuera una pieza, y moría con «unrecognized
# arguments» después de decir «todo en su sitio».
piezas=()
for a in "$@"; do
  if [ "$a" = "--agentes" ]; then export OFICIOS_POR_BASH=0; else piezas+=("$a"); fi
done
set -- "${piezas[@]}"
if [ $# -eq 0 ]; then
  echo "arrancar: di que piezas. Declaradas: $(_py 'import rutas; print(*rutas.piezas())')"
  exit 1
fi
# shellcheck disable=SC1091
source scripts/entorno.sh || { echo "arrancar: entorno.sh no pudo preparar el entorno"; exit 1; }

falta=()
command -v bash >/dev/null 2>&1 \
  || falta+=("no hay bash: el antivirus se llevo bash.exe; reinstala Git for Windows")
HERRAMIENTAS="node ffmpeg ffprobe"
[ "${OFICIOS_POR_BASH:-1}" = "0" ] || HERRAMIENTAS="$HERRAMIENTAS claude"
for h in $HERRAMIENTAS; do
  command -v "$h" >/dev/null 2>&1 || falta+=("no esta «$h» en el PATH")
done
[ -f whisper.cpp/whisper-cli.exe ] && [ -f whisper.cpp/ggml-medium.bin ] \
  || falta+=("falta whisper.cpp/whisper-cli.exe o ggml-medium.bin (docs/entorno.md)")
[ -n "$DISPARO_APAGADO" ] \
  && falta+=("DISPARO_APAGADO esta puesto: nadie llamaria a los oficios — unset DISPARO_APAGADO")
libre=$(df -BG --output=avail "$TMPDIR" 2>/dev/null | tail -1 | tr -dc 0-9)
[ -n "$libre" ] && [ "$libre" -lt 40 ] \
  && falta+=("solo quedan ${libre} GB en el disco del temporal; un lote de cinco pide unos 40")
# La cinta de cada pieza, en local. Si no esta y Drive si, se trae.
sin=$(_py "import rutas
for n in [int(x) for x in sys.argv[1:]]:
    t = rutas.TOMAS.get(f'reel-{n:02d}')
    if t and not rutas.angulos(t): print(t)" "$@" 2>/dev/null)
if [ -n "$sin" ]; then
  echo "arrancar: faltan en local: $sin — se traen de Drive"
  bash scripts/traer-brutos.sh || falta+=("no se pudieron traer de Drive: $sin")
fi
# La credencial, comprobada de verdad: `claude -p` contesta 0 aunque no tenga.
# Y lo que contesta se dice tal cual: «no tiene sesion» y «limite de uso hasta
# manana» piden cosas distintas, y el 18-10 el segundo se leyo como el primero.
[ "${OFICIOS_POR_BASH:-1}" = "0" ] || cli=$(claude -p ok --output-format json 2>/dev/null | _py "import json; d = json.loads(sys.stdin.read() or '{}'); print(d.get('result') or 'sin respuesta' if d.get('is_error', True) else '')" 2>/dev/null || echo "sin respuesta")
case "${cli:-}" in
  "") ;;
  *"Not logged in"*|*"sin respuesta"*)
    falta+=("el CLI de Claude no tiene sesion aqui ($cli). Lanzalo desde el panel Terminal de la app, dentro de Git Bash: & 'C:\Program Files\Git\bin\bash.exe' -lc 'cd \"$(pwd)\" && bash scripts/arrancar.sh $*'") ;;
  *) falta+=("el CLI de Claude contesta: $cli") ;;
esac

if [ ${#falta[@]} -gt 0 ]; then
  echo "arrancar: no se arranca, falta:"
  printf '  - %s\n' "${falta[@]}"
  exit 1
fi
echo "arrancar: todo en su sitio — disparador con $# pieza(s): $*"
[ "${OFICIOS_POR_BASH:-1}" = "0" ]   && echo "arrancar: oficios por la sesion — la cola: python scripts/dominio/cola.py --lote $*"
# Y si sale pidiendo rearranque, es que el codigo cambio: se vuelve a poner con
# el nuevo (C-629). Cualquier otra salida es la suya.
while :; do
  python scripts/disparador.py "$@" --hilos "$#"; rc=$?
  [ "$rc" -eq 75 ] || exit "$rc"
  echo "arrancar: el codigo cambio — disparador puesto otra vez"
done
