#!/usr/bin/env bash
#
# Monta los reels de punta a punta. Las carpetas salen de `rutas.json`.
#
#   bash scripts/montar.sh                 # los seis
#   bash scripts/montar.sh 2 5             # sólo esos
#   VIDEO_DESTINO=/otra/carpeta bash scripts/montar.sh
#   bash scripts/montar.sh --origen D:/brutos
#
# Ninguna ruta va escrita aquí dentro: se declaran una vez y se preguntan.
set -e
cd "$(dirname "$0")/.."

# Remotion escribe sus frames temporales en el TEMP del sistema, que aqui vive
# en C: y se queda sin sitio a 1800x3200 — Chrome rechaza la peticion y el
# render muere con «Failed to fetch … disk space is low», que no dice que el
# problema sea el disco del sistema. Se manda el temporal al disco del proyecto.
#
# **Y la ruta NO puede llevar espacios.** Estuvo en «F:/Edicion de video/tmp» y
# Remotion siguio escribiendo en C: pese a las tres variables: es el gotcha 1
# del proyecto. La señal es que el error de disco aparece con sitio de sobra en
# el disco declarado.
# **La consola de Windows es cp1252 y los scripts imprimen en UTF-8.**
# `candidatos.py` reventaba al imprimir una flecha —`UnicodeEncodeError`— con el
# fichero ya escrito: el trabajo estaba hecho y el paso salia con error. Es el
# gotcha 1 del proyecto por otra puerta: el entorno no es el que el codigo supone.
#
# **Y la ruta ya no se escribe aquí.** Se declara en `rutas.json` y la pone
# `entorno.sh`, que ademas se planta si apunta a C:. Tenerla escrita en este
# fichero significaba que cualquier paso lanzado por fuera de `montar.sh`
# —un render suelto, una prueba— volvia a producir en el disco del sistema, y
# ahi es donde murieron dos renders con el disco al 96%.
source "$(dirname "$0")/entorno.sh"

# **Las correcciones, antes que nada.** Cada entrada de `docs/correcciones.md`
# declara el fichero y el trozo de código donde quedó imposible repetirla; si
# una reescritura se lo llevó por delante, el montaje para aquí en vez de
# reproducir el defecto en las seis piezas. Es barato —lee ficheros— y va
# primero justo por eso.
# **Y en la entrega para aprobacion NO paran: levantan ticket.**
#
# Jaime, el 1 de septiembre: *«en este paso no deben parar por guardas; la guarda
# levanta tickets que se resuelven en el renderizado final»*.
#
# Y tiene razon en lo que separa: una aguja rota dice que un mecanismo cambio de
# sitio, no que la pieza este mal. Parar la entrega por eso es no dejar ver el
# video por un problema del codigo — hoy una sola aguja tuvo cinco piezas
# paradas mientras dos ya habian renderizado.
#
# En el render FINAL siguen parando, y ahi es donde tienen que hacerlo: es lo
# ultimo antes de publicar, y una correccion perdida ahi sale al mundo.
_guardas() {
  local salida
  salida=$(node scripts/guardas.mjs 2>&1) || {
    echo "$salida"
    if [ "$FINAL" = "1" ]; then return 1; fi
    # **Una aguja rota es UN ticket, no siete por corrida.**
    #
    # Esto abria uno por pieza cada vez que corria, y `montar.sh` corre una vez
    # por pieza: siete piezas x siete tickets = 49 por vuelta, con el mismo
    # texto. Medido el 7-9-2026: **98 de los 206 tickets abiertos** eran esto,
    # de solo SIETE agujas distintas — C-170 sola habia abierto 35.
    #
    # El dano no es el ruido: es que 98 pendientes falsos entierran los 108 de
    # verdad, y una lista en la que no se puede confiar deja de leerse. Ahora se
    # abre uno por aguja rota, con su codigo en el texto, y no se repite si ya
    # hay uno abierto por esa misma.
    PYTHONIOENCODING=utf-8 python - "$salida" <<'TICKET'
import re
import sys

sys.path.insert(0, "scripts")
from dominio import ticket as tk

salida = " ".join(sys.argv[1].split())
codigos = dict.fromkeys(re.findall(r"C-\d+", salida)) or {"": None}
abiertos = " ".join(t["dijo"] or "" for t in tk.abiertos())
for c in codigos:
    if c and c in abiertos:
        continue
    tk.abrir("reel-01",
             f"una guarda de codigo no se sostiene y la entrega salio igual"
             f"{' (' + c + ')' if c else ''}: {salida[:600]}",
             None, "dato", vuelve_a="", cierra_con="guardas")
TICKET
    echo "montar.sh: guarda rota anotada como ticket; la entrega sigue."
  }
  return 0
}
# **Lo que es del lote se paga una vez, no una por pieza.**
#
# `dominio/fase.py` monta llamando `montar.sh {n}` **por pieza**, y
# `montar-lote.sh` reparte tres a la vez: las comprobaciones de aqui abajo
# —guardas, verdad, contratos, techo, la puerta de `verificar.py`, el lint, la
# bitacora y la verificacion final— miran el proyecto entero y corrian **siete
# veces** para mirar siete veces lo mismo. Solo el lint son 9,6 s por pieza.
#
# Es el mismo patron que ya existia con `SALTA_SPEC`, y por el mismo motivo:
# quien reparte las piezas sabe lo que ya hizo para todas. Sin la variable
# —`montar.sh 3` a mano, o la fase `montado` de una pieza suelta— no cambia
# nada: se comprueba todo, como hasta hoy.
del_lote() { [ -n "${EN_LOTE:-}" ]; }

# **Le pregunta a la cadena, y un ERROR no es «al dia».**
#
# `cadena.py --hay-que` contesta con el codigo de salida, y hasta ahora tenia
# dos: 0 «rehazlo» y 1 «esta al dia». El problema es que un eslabon mal escrito
# tambien salia con 1 — el mismo codigo—, asi que una errata se leia como «no
# hace falta» y el paso se saltaba **sin una linea de aviso**. Es la forma de
# fallar mas cara que tiene esta linea: hacia menos trabajo y decia que todo iba
# bien.
#
# Ahora hay un tercero, el 2, y aqui se trata como lo que es: si la cadena no
# pudo contestar, no se decide por ella.
#
# El `|| c=$?` no es adorno: con `set -e`, la salida 1 de un comando suelto
# mataria el guion antes de poder mirarla.
_hay_que() {
  local c=0
  python scripts/cadena.py --hay-que "$1" "$2" || c=$?
  if [ "$c" -gt 1 ]; then
    echo "montar.sh: la cadena no pudo contestar por «$1» (codigo $c)."
    echo "  No se sigue: un error leido como «al dia» salta el paso en silencio."
    exit 1
  fi
  return "$c"
}

#: `--solo-lote`: solo la mitad que mira el proyecto entero. Ver la nota
#: donde este fichero se parte, mas abajo.
SOLO_LOTE=0
case " $* " in *" --solo-lote "*) SOLO_LOTE=1 ;; esac
solo_lote() { [ "$SOLO_LOTE" = 1 ]; }

del_lote || _guardas || exit 1
# **Y la fuente de verdad de cada decision, comprobada.** Jaime: *«deja clara
# en codigo la fuente de verdad»*. Una correccion que se escribe en una copia y
# un render que lee la otra no falla al corregir: falla al entregar, y calla.
# Va aqui, al lado de las guardas, y por el mismo motivo — lee ficheros y es
# barato, asi que se paga antes de gastar el peldano caro.
del_lote || python scripts/verdad.py
# **Y los contratos, que son el corazon de la maquina.** Declaran que dato
# viaja a cada paso de IA, que frase del prompt no se puede contestar sin el, y
# que linea de codigo ejecuta lo que se contesta. Sin comprobarlo, un contrato
# es una promesa: el payload cambia de forma, la aguja sigue apuntando a la
# vieja y el paso sigue corriendo con un campo que ya no llega.
#
# No corria en ninguna parte, y ademas resolvia mal todas sus rutas —asi que
# las 83 agujas daban «no esta» y el parte no lo miraba—. Va aqui por lo mismo
# que las otras dos: lee ficheros y es barato.
del_lote || python scripts/contratos.py
# **Y con que se comprueba cada decision, que es lo que faltaba.** Jaime:
# *«para tomar decisiones utilizan solo un mecanismo, los CC por ejemplo, y no
# el sonido, que es el indicador mas claro de que el CC esta mal puesto»*.
#
# `verdad.py` dice de donde sale cada decision y `contratos.py` que dato viaja a
# cada paso; faltaba la tercera: con que se comprueba lo decidido, y que sea con
# OTRA señal. Falla si una comprobacion declarada ya no esta en el codigo y
# avisa de las que no tienen ninguna — la lista de huecos es trabajo pendiente,
# no un defecto de esta corrida. Va aqui por lo mismo que las otras dos: lee
# ficheros y cuesta menos de un segundo.
del_lote || python scripts/comprobado.py --solo-huecos

# **El techo de 300 lineas, y aqui porque es donde para.** Jaime: *«maximo 300
# lineas; 1000 lineas es espagueti»*. Esto imprimia «33 ficheros pasan del
# techo» y salia con codigo 0, o sea que el techo no existia — la misma averia
# que `contratos.py` tuvo hasta ayer. Ahora la deuda esta declarada en
# `docs/tamano-deuda.txt`, **solo puede bajar**, y un fichero nuevo por encima
# del techo no nace. Cuesta menos de un segundo: solo cuenta lineas.
# **Y su mensaje NO va a /dev/null.** Con la salida silenciada, un fichero por
# encima del techo mataba el montaje sin decir una palabra: `set -e` y a callar.
# Se pierden dos corridas averiguando que fue eso. Se guarda y se enseña solo
# cuando falla, que es cuando hace falta leerlo.
_techo() {
  local salida
  if ! salida=$(python scripts/tamano.py 2>&1); then
    echo "$salida" | tail -5
    return 1
  fi
}
del_lote || _techo || exit 1

# **Un nombre que no existe no llega a un render.**
#
# C-349 puso `rutas.interprete()` en `servicios/base.py` y no puso su `import`.
# El humo pasaba —16 de 16— porque esa linea solo corre cuando un paso `.sh`
# se ejecuta de verdad, y hasta que reel-05 llego a `montado` no se ejecuto
# ninguno: `NameError: name 'rutas' is not defined`, la corrida entera perdida
# y la pieza parada en `verificado`. La averia de la casa —declarado y no
# ejercitado— con otra cara.
#
# `pyflakes` lo dice en dos segundos sobre los 90 ficheros, sin correr nada.
# Solo los nombres sin definir: lo demas es estilo y no tumba una corrida.
_nombres() {
  local salida
  salida=$(python -m pyflakes scripts/ 2>&1 | grep "undefined name") || return 0
  [ -z "$salida" ] && return 0
  echo "NOMBRES QUE NO EXISTEN - esto revienta cuando esa linea se ejecute:"
  echo "$salida"
  return 1
}
del_lote || _nombres || exit 1

# **Y el conducto es una guarda, igual que el techo.** Un tiquet que vuelve a
# `descrito` o a `disenado` lo atiende un servicio, y ese servicio deja recibo:
# el pedido que se le escribio y la respuesta que devolvio. Cerrarlo sin eso es
# decir que hubo un paso que no corrio — y el 7-9-2026 fue exactamente asi como
# reel-03 salio dos veces mal: sin pedido no hubo orden del compositor, y sin
# respuesta el disenador no tuvo nada que revisar. La deuda vieja esta declarada
# en `docs/recibo-deuda.txt` y solo baja; uno nuevo para el montaje.
# Va con la misma forma que el techo: mira los tiquets del proyecto entero, no
# los de esta pieza, asi que el lote lo paga una vez (C-313).
_recibos() {
  local salida
  if ! salida=$(PYTHONIOENCODING=utf-8 python scripts/recibos.py 2>&1); then
    echo "$salida" | tail -12
    return 1
  fi
}
del_lote || _recibos || exit 1

ORIGEN=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.origen))")
DESTINO=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.rutas.destino))")
echo "origen  $ORIGEN"
echo "destino $DESTINO"

REELS=()
#: Los mismos numeros SIN las banderas. `verificar.py` los parsea con argparse y
#: una bandera que no conoce lo mata con codigo 2 — o sea que la puerta daria
#: «no pasa» por un `--solo-lote` que no habla de ninguna pieza.
PIEZAS_ARG=()
for a in "$@"; do
  [[ "$a" == --* ]] && continue
  PIEZAS_ARG+=("$a")
  REELS+=("$(printf %02d "$a")")
done
[ ${#REELS[@]} -eq 0 ] && REELS=(01 02 03 04 05 06)

# **Lo que no se renderiza se cuenta al final, y el paso falla.**
#
# Una pieza bloqueada se saltaba con un aviso y el script salia con exito, asi
# que `avanzar.py` la marcaba `montado` **sin que existiera el video**: reel-01
# quedo en `montado` con el mp4 de las 00:38, de antes de la vuelta. Es la forma
# exacta de perder el estado que este proyecto persigue — la fase dice hecho y
# el artefacto no esta.
#
# Las demas siguen renderizando: bloquear el lote por una pieza es lo contrario
# del embudo. Lo que cambia es que al final se dice cuales faltan y se sale con
# error, para que la fase no avance sobre un hueco.
BLOQUEADAS=()
#: Piezas cuyo render salio byte a byte igual que el anterior.
IDENTICAS=()

# **Paso 1: los subtitulos de toda la cinta, y van delante de todo.** El montaje
# leia una sola pasada de whisper y la trataba como verdad; el modelo se come
# frases, se queda pegado y con `-ml 1 -sow` borra la puntuacion, asi que el
# catalogo daba unidades de 98 s y la seleccion no podia elegir (C-54). Esto no
# depende de que quien lanza el montaje se acuerde del orden: `exigir()` para el
# resto si falta, y aqui se encadena para que no haga falta llegar a ese error.
# **La puerta, y va aqui para que no se pueda saltar.** Jaime: *«el camino es
# obligatorio siempre, ninguno de esos videos es siquiera util»*.
#
# Las comprobaciones existian sueltas y dependian de que alguien se acordara de
# correrlas — o sea que no existian. Aqui corren como conjunto y paran el
# montaje: mejor no renderizar que renderizar seis piezas inservibles.
# **La ULTIMA linea tiene que decir QUE falta, no firmar.**
#
# El motor guarda como motivo la ultima linea que imprime el paso, y esto acababa
# con «no se renderiza nada hasta resolver lo de arriba»: cierto, y sin una sola
# pista de que es «lo de arriba». En el log del despachador las siete piezas
# decian lo mismo y ninguna decia por que — que es el mismo fallo que ya costo un
# dia con el aviso de disco, sólo que ahora la frase inutil la escribimos aqui.
#
# Se repite el primer motivo real al final. Lo de arriba sigue entero para quien
# mire la salida completa; la ultima linea deja de mentir por omision.
_puerta() {
  local salida
  salida=$(PYTHONIOENCODING=utf-8 python scripts/verificar.py "$@" 2>&1) || {
    echo "$salida"
    echo "montar.sh: $(printf '%s
' "$salida" | grep -m1 '·' | sed 's/^ *· *//')"
    return 1
  }
  printf '%s
' "$salida"
}
del_lote || _puerta "${PIEZAS_ARG[@]}" || exit 1

# **Las dos vueltas de abajo son de la PIEZA, y en `--solo-lote` no corren.**
# Se recorre una lista vacia en vez de meter cien lineas dentro de un `if`:
# el diff de indentar es mas grande que el cambio, y lo que se lee peor se
# rompe antes.
PIEZAS_CORTE=("${REELS[@]}")
solo_lote && PIEZAS_CORTE=()

for r in "${PIEZAS_CORTE[@]}"; do
  TOMA=$(node -e "console.log(JSON.parse(require('fs').readFileSync('rutas.json','utf8')).tomas['reel-$r']||'')")
  if [ -n "$TOMA" ] && ! grep -q '"pasadas"' "work/transcripts/$TOMA.json" 2>/dev/null; then
    echo "══ subtitulos reel-$r ══ (varias pasadas; es el paso 1)"
    python scripts/transcribir.py --toma "$((10#$r))"
  fi
done

for r in "${PIEZAS_CORTE[@]}"; do
  SRC=$(node -e "import('./scripts/rutas.mjs').then(m=>console.log(m.bruto('reel-$r')))")
  # **Ya se puede cortar material de varias cintas.** Estuvo frenado porque el
  # corte abria un solo `-i` y `punch-ins.py` calculaba un ancla por fichero —
  # con dos sesiones el encuadre salia descuadrado sin avisar (aprendizaje 20).
  # Ahora la escena declara su `fuente`, el ancla se mide **por fuente** y cada
  # escena abre su propio bruto: no hay dos fuentes en un corte, hay dos cortes.
  echo "══ corte reel-$r ══"
  # **El cosido, y va AQUI: antes del plan y despues del EDL.**
  #
  # `cadena.py` ya lo declaraba —el eslabon `edl` se despierta con «revision
  # --aplicar · depurar · costuras» y el `plan` viene detras—, pero la linea no
  # lo corria: estaba solo en la tabla `fase`, o sea en el camino de
  # `avanzar.py`. Una pieza montada a mano con `montar.sh` se saltaba el paso
  # entero, y `verificar.py` se limitaba a **recomendarlo en un mensaje**. Un
  # paso que hay que acordarse de correr no es un paso del proceso: asi llego
  # `reel-03` a Jaime con tres entradas cortadas a mitad de palabra.
  #
  # Va antes del `if` de abajo a proposito: edita el EDL, asi que al tocarlo deja
  # el plan viejo y la propia comparacion de fechas lo regenera. Al reves se
  # cortaria con el plan de antes del cosido.
  PYTHONIOENCODING=utf-8 python scripts/costuras.py "$((10#$r))" 2>&1 | grep -vE ": 0 " || true
  # **Si el EDL cambio, el plan esta viejo.** El corte no lee el EDL: lee
  # `plan-full.json`, que `plan-reel.mjs` derivo de el en su dia. Asi que editar
  # el EDL —anadir un cierre, recortar una entrada— **no cambiaba nada y no lo
  # decia nadie**: el montaje salia identico y con exito. Es el aprendizaje 44
  # por el otro lado: alli un paso invalidaba lo que produjo otro; aqui el
  # consumidor no se entera de que su fuente cambio.
  #
  # Se compara por fecha de modificacion, que es la unica senal que hay.
  #
  # **Y el productor cuenta como fuente, no solo el EDL.** C-233 arreglo
  # `plan-reel.mjs` —recortaba cada escena con los silencios de otra cinta— y
  # este `if` siguio diciendo que el plan estaba al dia, porque el EDL no se
  # habia movido. O sea que `montar.sh 6` corria entero, salia con exito, y
  # entregaba la pieza construida con el productor de antes de la correccion.
  # Un eslabon tiene dos fuentes: lo que come y quien lo cocina (C-234).
  if [ "ads/reel-$r/edl-sell.json" -nt "work/scenes/reel-$r/plan-full.json" ]      || [ "scripts/plan-reel.mjs" -nt "work/scenes/reel-$r/plan-full.json" ]; then
    echo "  (el EDL o plan-reel.mjs son mas nuevos que el plan: regenerando escenas)"
    node scripts/plan-reel.mjs --reel "$r" 2>&1 | tail -1
  fi
  # `plan-reel.mjs` regenera el plan SIN encuadres —los calcula `punch-ins.py`—
  # asi que si el plan viene pelado hay que volver a medirlos. Antes esto no
  # estaba encadenado y el corte fallaba con «El plan no tiene encuadres».
  if ! node -e "process.exit(JSON.parse(require('fs').readFileSync('work/scenes/reel-$r/plan-full.json','utf8')).escenas[0].crop?0:1)"; then
    echo "  (recalculando encuadres)"
    python scripts/punch-ins.py --source "$SRC"       --plan "work/scenes/reel-$r/plan-full.json" --ancla-global 2>&1 | grep -E "ancla global"
  fi
  # **El corte se rehace si hace falta, y lo dice `cadena.py`.**
  #
  # Corria SIEMPRE: 29 escenas del bruto 4K HEVC a 2,26 s cada una son 65 s
  # medidos por pieza, en cada montaje, hubiera cambiado el plan o no. Y la
  # respuesta ya estaba escrita: `cadena.py` declara los trece eslabones con
  # lo que come cada uno y con su productor como fuente. Lo unico que le
  # faltaba era que alguien le preguntara — se le citaba tres veces en este
  # fichero, siempre dentro de un comentario.
  if _hay_que corte "$((10#$r))"; then
    node scripts/render-hook.mjs --source "$SRC" \
      --plan "work/scenes/reel-$r/plan-full.json" \
      --out "public/reel-$r.mp4" 2>&1 | grep -E "escenas ·|listo"
  fi
  # **Donde esta su cara se mide sobre ESTE corte, no sobre el de antes.**
  # `cadena.py` declara `cara` colgando de `corte` desde el principio, y sin
  # embargo `montar.sh` no corria `sujeto.py` en ningun sitio: cada re-corte
  # dejaba `cara.json` de la version anterior y el render colocaba la banda de
  # subtitulos, la ventana de las placas y los paneles con la coronilla en otro
  # sitio. Es de lo que Jaime se quejo —*«y esas guardas de que protegen, si lo
  # que hacen es poner mi cara debajo de los titulos?»*— y la respuesta era que
  # median bien un corte que ya no existia.
  #
  # **Y corre SIEMPRE, no solo cuando el corte es mas nuevo que `cara.json`.**
  # El mismo paso produce los recortes con alfa, y esos no dependen del corte
  # sino de lo que se DECLARA: un tablero nuevo que lo lleva dentro (`sujeto`)
  # pide un recorte que antes no existia, con el corte sin tocar. Con la
  # condicion puesta el paso se saltaba, el recorte no se producia y la pieza
  # salia sin el — declarado y no producido, la averia de la casa (C-256).
  # No cuesta: `de_la_pieza` son cuatro fotogramas de MediaPipe y
  # `recortes_de_la_pieza` ya salta por si solo lo que esta al dia.
  PYTHONIOENCODING=utf-8 python scripts/dominio/sujeto.py "$((10#$r))" 2>&1 | tail -1
  # **Las otras dos medidas del corte, declaradas y sin correr.** `cadena.py`
  # cuelga `huecos` y `trasfondo` del corte y los declara como las DOS
  # entradas del spec; ninguna linea los ejecutaba, asi que `reels-spec.mjs`
  # se comia el fichero que hubiera en disco — de otro montaje o de ninguno.
  # Declarado y no producido, la averia de la casa (C-256).
  #
  # A diferencia de `sujeto.py`, estas dos solo miran el video: si el corte no
  # se movio la medida vale, y por eso van con la pregunta delante.
  if _hay_que huecos "$((10#$r))"; then
    PYTHONIOENCODING=utf-8 python scripts/dominio/hueco.py "$((10#$r))" 2>&1 | tail -1
  fi
  if _hay_que trasfondo "$((10#$r))"; then
    PYTHONIOENCODING=utf-8 python scripts/dominio/trasfondo.py "$((10#$r))" 2>&1 | tail -1
  fi
  python scripts/subtitular.py "$r"
  # **Y el subtitulo, cruzado con el libreto. Aqui, no cuando alguien se acuerde.**
  #
  # Pregunta de Jaime sobre el cc de reel-05: *«"una futura situacion gratuita"
  # dicen los subtitulos, composicion no los revisa de cara al libreto?»*. No los
  # revisaba nadie: `subtitular.py` corrige contra la cinta —y no ve nada cuando
  # las dos pasadas se equivocan igual— y aplica el glosario, que solo caza lo
  # que alguien ya noto una vez y escribio. Una palabra nueva mal oida pasaba
  # entera hasta que el la leia en pantalla.
  #
  # Va pegado a `subtitular.py` y no aparte por lo de siempre: un paso que hay
  # que acordarse de correr no es un paso del proceso. `costuras.py` estuvo asi
  # y costo tres entradas cortadas a mitad de palabra en reel-03 (C-197).
  #
  # **Avisa y no para.** Es una lista para mirar, no un corte: casi todo lo que
  # sale son parafrasis del hablante, porque en este proyecto el libreto no se
  # toma literal. Plantar el lote por una parafrasis seria cambiar un problema
  # por otro, y una lista que bloquea deja de leerse.
  PYTHONIOENCODING=utf-8 python scripts/oido.py "$((10#$r))" || true
done

# **El spec se puede saltar, y hace falta para montar en paralelo.**
#
# `reels-spec.mjs` escribe UN fichero para las siete —`src/reels.json`—, asi que
# dos montajes a la vez se lo pisan: es lo unico compartido de toda la linea.
# Corriendolo una sola vez ANTES y saltandolo aqui, las piezas se pueden montar
# en paralelo sin tocarse, porque todo lo demas es de su pieza.
if [ -z "${SALTA_SPEC:-}" ]; then
  REELS_PEDIDOS="${REELS[*]}" node scripts/reels-spec.mjs
else
  echo "  (spec ya hecho para el lote: no se regenera)"
fi

# ── ¿llega al render lo que se declaro? ──────────────────────────────────────
#
# Jaime, despues de un dia entero de correcciones que no aparecian: *«las
# correcciones no estaban llegando a la renderizacion»*, *«eso es un problema que
# me obliga a retrabajar, a hacer dobles y triples procesos»*.
#
# Va AQUI y no al final: el spec ya esta armado —o sea, ya se sabe que va a
# dibujar el render— y todavia no se ha gastado un minuto de GPU. Una declaracion
# que no viaja se ve ahora, con su pieza y su etapa, en vez de cuando el vinculo
# llega a sus manos.
#
# Avisa y no para: hay faltas legitimas —una forma sin componente propio— y parar
# el lote por ellas seria cambiar un problema por otro. Lo que no puede pasar es
# que no se digan.
if ! del_lote && ! python scripts/llega.py 2>&1 | tail -20; then :; fi
# El parte de trabajo se reescribe solo: los números de `docs/bitacora.md` salen
# del spec recién generado. Un número copiado a mano se queda viejo en el primer
# render, y entonces la bitácora miente justo cuando hace falta.
del_lote || node scripts/bitacora.mjs
del_lote || npm run lint

# **Hasta aqui llega lo que es del lote.** `montar-lote.sh` corre esta mitad una
# vez —con `--solo-lote`— y luego reparte las piezas con `EN_LOTE=1`, que salta
# exactamente lo que acaba de correr. Ni se duplica el codigo ni se duplica el
# trabajo: es el mismo fichero, cortado por donde el trabajo deja de ser del
# proyecto y pasa a ser de la pieza.
if solo_lote; then
  echo "  (comprobaciones del lote: hechas)"
  exit 0
fi

for r in "${REELS[@]}"; do
  n=$((10#$r))
  echo "── render Reel-R$n ──"
  # **A resolución nativa, y con la GPU donde de verdad se puede.**
  #
  # `--hardware-acceleration` NO sirve en esta máquina, y conviene saber por
  # qué: Remotion elige **`h264_nvenc`**, el codificador de NVIDIA, y aquí hay
  # una **Radeon RX 5600 XT**. Revienta al instante con «write EOF».
  #
  # Y estuvo a punto de colarse como mejora: en un banco anterior daba 14 s
  # frente a 68 s, pero **era un fallo rápido, no un render rápido** — se medía
  # el tiempo sin comprobar que el fichero existiera. Un banco que no verifica
  # la salida mide lo que tarda en fallar.
  #
  # Lo que sí acelera:
  #
  #   sin `--scale`     La composición ya se maqueta a 1080x1920, que es lo que
  #                     se entrega. Subirla a 1800x3200 eran 2,8x más píxeles
  #                     para tirarlos después.
  #   `--gl=angle`      Chrome compone por D3D11 y no por software.
  #   concurrencia      El cuello es pintar frames, no codificarlos.
  #   h264_amf (abajo)  La entrega, ésa sí por el codificador de AMD.
  # **Lo que no paso la puerta no se renderiza, y el resto sigue.** El peldaño
  # caro solo sobre lo que ya sabemos que esta bien.
  # **El bloqueo va en el paso final, no aquí.** Regla de Jaime: *«pon el
  # bloqueo en el paso final, no acá»*, *«el render se necesita, quiero ver lo
  # que va a salir; no importan restricciones, quiero aprobarlo»*.
  #
  # La puerta existía para no gastar el peldaño caro —su atención— en una pieza
  # que no está. Pero cuando es él quien pide verla, la puerta deja de proteger
  # y sólo estorba: el criterio humano es el escalón más caro **porque es el que
  # manda**, no para que el código decida qué le deja mirar.
  #
  # Los motivos no se borran ni se callan: se imprimen aquí y viajan en
  # `bloqueado` hasta `publicar.py`, que es donde sí paran. Ver algo malo cuesta
  # dos minutos suyos; publicarlo cuesta la campaña.
  MOTIVOS=$(node -e "const s=JSON.parse(require('fs').readFileSync('src/reels.json','utf8'));const r=s.find(x=>x.id==='Reel-R$n');console.log((r&&r.bloqueado||[]).join(' | '))")
  if [ -n "$MOTIVOS" ]; then
    echo "── Reel-R$n se renderiza CON motivos abiertos ──"
    echo "   $MOTIVOS"
    BLOQUEADAS+=("R$n: $MOTIVOS")
  fi
  # **El render va por `scripts/render.mjs`, no por el CLI.**
  #
  # Es lo unico que estampa `reel-RN.mp4.huella` —el sha1 del spec que ese
  # fichero dibujo— y `_render_caduco()` la exige para dar la pieza por montada.
  # Con `npx remotion render` esa huella no se escribia nunca: **toda pieza
  # salia caduca**, el despachador relanzaba el montaje, y el video entregado
  # seguia siendo el de antes. El lector existia y el escritor no se ejecutaba.
  #
  # Ahi dentro van tambien el bundle limpio —el CLI sirve un spec cacheado— y la
  # concurrencia 4. El reintento a 16 se disparaba siempre, asi que 4 no era el
  # plan B: era el valor bueno escrito en el sitio equivocado.
  # **Y solo si hace falta.** Igual que el corte: `cadena.py` sabe si el
  # render de esta pieza corresponde al spec de ahora. Son 3,6 min medidos
  # por pieza, y el aviso «salio IDENTICA al render anterior» era exactamente
  # esto — la informacion correcta, cobrada despues de pagarla entera.
  #
  # **Y la huella tambien lo despierta.** Si el mp4 esta al dia pero le falta
  # su `.huella`, la pieza sale caduca para siempre —la escribe `render.mjs`
  # y no el CLI—, asi que rehacerla es la unica forma de que la linea
  # converja.
  RENDERIZADA=0
  if _hay_que render "$n" || [ ! -f "$DESTINO/reels/reel-R$n.mp4.huella" ]; then
    node scripts/render.mjs "$n"
    RENDERIZADA=1
  fi
  # **Y se comprueba que el render dejo su huella.**
  #
  # Aqui es donde se cerro la averia: `_render_caduco()` lleva dias exigiendo
  # `reel-RN.mp4.huella` y NADIE la escribia, porque el paso renderizaba por el
  # CLI. Toda pieza salia caduca, el despachador relanzaba el montaje, y el
  # video entregado seguia siendo el de antes. El lector existia y el escritor
  # no se ejecutaba: eso no se ve en ningun sitio, se ve en que nada converge.
  #
  # Se mira el artefacto y no el codigo, asi que da igual quien renderice
  # manana: si la huella no esta, la linea para aqui y no en la cuarta entrega.
  [ -f "$DESTINO/reels/reel-R$n.mp4.huella" ] || {
    echo "montar.sh: el render de R$n no dejo huella en"          "$DESTINO/reels/reel-R$n.mp4.huella."
    echo "  Sin ella la pieza sale caduca siempre y el montaje no converge."
    exit 1
  }
  # **La entrega NO recorta.** Jaime: *«respeta el guion; si hay necesidad de
  # recortar lo definimos al final»* y *«el ajuste de tiempo lo hacemos al final
  # con el reel montado»*.
  #
  # Antes se capaba con `-t` a 89,9 s. Eso es una decisión de montaje tomada por
  # una resta, y en silencio: la pieza salía cortada a mitad de frase sin que
  # nadie lo hubiera decidido. Ahora se entrega entera y **se reporta** contra la
  # indicación de su formato, que es lo que hace falta para decidir después.
  #
  # Las indicaciones, no topes: **ad 120 s · reel 90 s**, y varían según lo que
  # la pieza tenga que decir.
  DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$DESTINO/reels/reel-R$n.mp4")
  LIMITE=${LIMITE:-120}
  # Va con `print`, no con `printf`, y a propósito: `printf` necesita un salto
  # de línea escapado dentro de las comillas y, escrito como salto real, awk
  # aborta con «unterminated string». Con `set -e` eso **se lleva por delante el
  # resto del paso** — el render quedaba escrito y las copias de entrega y de
  # revisión no llegaban a generarse, con el script saliendo 0. `print` no
  # necesita salto, así que el fallo no puede volver.
  awk -v d="$DUR" -v l="$LIMITE" -v n="$n" 'BEGIN{
    if (d > l)
      print "  ojo: R" n " dura " int(d*10)/10 "s, " int((d-l)*10)/10 "s sobre la indicacion de " l "s. NO se recorta: se decide al final."
    else
      print "  R" n " " int(d*10)/10 "s, dentro de la indicacion de " l "s"
  }'

  # **El paso 7 va aqui, no aparte.** La entrega y la copia de revision las
  # escribe `musica.sh`, que es donde vive la mezcla: la voz se nivela, la
  # musica se talla en la banda de la voz y las dos salen a -14 LUFS / -1 dBTP.
  #
  # Estuvo suelto y por eso las entregas salian mudas de musica: un paso que hay
  # que acordarse de correr no es un paso del proceso, es una intencion. Si
  # falta el mp3 de la pieza, masteriza solo la voz y lo dice.
  # **Si el render sale IDENTICO al anterior, se dice.**
  #
  # Cuatro entregas iguales seguidas, y ninguna maquina lo noto: se re-cortaba,
  # se re-describia, se re-renderizaba, y el fichero salia byte a byte igual.
  # Jaime lo dijo cuatro veces —*«el mismo video»*, *«me has dado los mismos
  # videos 3 o 4 veces»*— y era el unico que lo estaba comprobando.
  #
  # Un render identico no es un error: es informacion. Significa que lo que se
  # cambio no llega a la pantalla, y eso es exactamente lo que hay que saber
  # ANTES de entregar, no despues de que alguien lo mire por cuarta vez.
  #
  # Se compara la huella del video, no la del fichero: los metadatos llevan
  # fecha y harian que dos renders identicos parecieran distintos.
  # Sin render nuevo no hay nada que comparar: el fichero es el mismo de
  # antes a proposito, y decir «IDENTICA» ahi seria una alarma falsa.
  if [ "$RENDERIZADA" = 1 ]; then
    HUELLA_ANTES=""
    [ -f "$DESTINO/reels/reel-R$n.sha" ] && HUELLA_ANTES=$(cat "$DESTINO/reels/reel-R$n.sha")
    HUELLA=$(ffmpeg -v error -i "$DESTINO/reels/reel-R$n.mp4" -map 0 -c copy -f hash -hash sha256 - 2>/dev/null | tail -1)
    echo "$HUELLA" > "$DESTINO/reels/reel-R$n.sha"
    if [ -n "$HUELLA_ANTES" ] && [ "$HUELLA" = "$HUELLA_ANTES" ]; then
      echo "  OJO: Reel-R$n sale IDENTICO al render anterior."
      echo "       Lo que se cambio no llega a la pantalla. No lo entregues como nuevo."
      IDENTICAS+=("R$n")
    fi
  fi

  # **Sin aprobar no lleva musica, igual que no lleva efectos.**
  #
  # Regla de Jaime, dicha dos veces: *«los videos para aprobacion van sin musica
  # y sin audio adicional, no los necesitamos y sera mas facil con el audio
  # final y definitivo, menos retrabajo»*, y hoy otra vez: *«renderiza sin
  # musica y sin efectos; va al paso intermedio, con Adobe Podcast»*.
  #
  # Los efectos ya salian mudos —`sonido: aprobadas.has(slug)` en
  # `reels-spec.mjs`— y la musica no: este paso corria siempre. O sea que la
  # mitad de la regla estaba puesta y la otra mitad no, que es la peor forma de
  # tenerla porque parece cumplida.
  #
  # **Y la pregunta se hace en un solo sitio.** `Pieza.aprobada` es la
  # definicion; preguntarla aqui con otro SQL seria una segunda copia de la
  # regla, que es como se separan las dos en cuanto una cambie.
  # **Y el audio SIEMPRE pasa por el paso 7, aprobada o no.**
  #
  # Aqui habia una rama que, sin aprobar, entregaba el render con `-c copy`.
  # Sin musica, si — esa es la regla de Jaime. Pero tambien **sin nivelar**, y
  # eso nadie lo pidio: la entrega de reel-01 salio a -9,88 LUFS con pico
  # +0,19 dBTP, o sea 4 LU de mas y clipeando por encima de cero. Se juzga una
  # pieza con el audio reventado y lo que se aprueba no es lo que se hizo.
  #
  # `musica.sh` ya distingue las dos cosas: pregunta si esta aprobada, quita la
  # musica si no lo esta, y masteriza la voz igual —lo dice su propio
  # comentario, *«sin musica tambien hay que masterizar»*—. La rama duplicaba
  # la pregunta y se llevaba por delante la mitad que no duplicaba.
  # **Y los efectos se sacan de ESTE render, no del de ayer.**
  #
  # `voz-limpia` sustituye la pista entera por la voz de Adobe, asi que los
  # efectos —que viven dentro del render— hay que recuperarlos de una pista
  # aparte. Esa pista la produce `efectos.mjs` y **`montar.sh` no lo llamaba en
  # ningun sitio**: reel-06 se entregaba con el `-efectos.wav` del 4 de
  # septiembre mezclado sobre el corte de hoy, o sea cada golpe sonando donde ya
  # no pasa nada. `cadena.py` lo declaraba colgando de `render` desde el
  # principio; lo que faltaba era que alguien lo corriera.
  if [ ! -f "out/audio-voz/reel-R$n-efectos.wav" ] || [ "out/reels/reel-R$n.mp4" -nt "out/audio-voz/reel-R$n-efectos.wav" ]; then
    echo "  (el render es nuevo: rehaciendo la pista de efectos)"
    node scripts/efectos.mjs "$n" 2>&1 | tail -1
  fi
  # **Y la copia sin musica caduca con el render.**
  #
  # `musica.sh` mezcla sobre `out/entrega/.sin-musica/`, y eso es lo que hace la
  # mezcla idempotente (C-233). El precio es que esa copia, mientras exista, ES
  # la fuente: el paso deja de mirar el render. Medido el 6-9-2026, cuatro
  # entregas salian de una copia vieja — reel-01 a 1x con el corte a 1,15x, y
  # reel-04 nueve segundos y medio mas corta que su propio render.
  #
  # Una cache que hace idempotente un paso lo hace tambien inmune a las
  # correcciones. Toda cache tiene que saber de que cuelga.
  if [ -f "out/entrega/.sin-musica/reel-R$n.mp4" ] && [ "out/reels/reel-R$n.mp4" -nt "out/entrega/.sin-musica/reel-R$n.mp4" ]; then
    echo "  (el render es nuevo: la copia sin musica se rehace)"
    rm -f "out/entrega/.sin-musica/reel-R$n.mp4"
    python scripts/voz-limpia.py "$n" 2>&1 | grep -E "acelerada|sincronia" || true
  fi
  # El interprete se pregunta, no se nombra: el antivirus se llevo
  # `usr/bin/bash.exe` de la instalacion de Git y no deja reponerlo. `sh.exe` es
  # el mismo binario y estaba al lado, asi que la linea moria por el nombre.
  # **La mezcla tambien pregunta.** `cadena.py` declara la entrega colgando de
  # los efectos, que cuelgan del render: si nada de eso se movio, remezclar
  # produce el mismo fichero y cuesta las pasadas de `loudnorm` enteras.
  ENTREGA_NUEVA=0
  if _hay_que entrega "$n"; then
    ENTREGA_NUEVA=1
    "$(command -v bash || command -v sh)" scripts/musica.sh "$n"
  fi
  # **Y la entrega se sella: el montaje entero queda guardado.**
  #
  # Jaime, cuando su entrega aprobada no se pudo rehacer: *«no se trata de
  # commits, todo debia estar en base de datos, y nada se borra de la base de
  # datos; para eso esta»*. La tabla `version` guardaba una huella —con que
  # distinguir dos versiones, no con que reconstruir una—, asi que las siete
  # piezas del 4 de septiembre se volvieron irrepetibles esa misma noche.
  #
  # Va aqui, pegado a la entrega, y no en un paso aparte: un paso que hay que
  # acordarse de correr no es un paso, y ese error ya se pago con `costuras.py`.
  # **Y se mide cómo SUENA lo que se acaba de entregar.**
  #
  # `suena.py` llevaba días escrito y no lo llamaba nadie — uno de los cinco
  # seguros desconectados que salieron en la auditoría del 7-9-2026. Corrido a
  # mano ese día encontró **9 costuras audibles en reel-01 y 12 en reel-06**,
  # que es exactamente lo que Jaime describió de oído: *«los demás sí están
  # raros»*. Un seguro que existe y no corre es peor que no tenerlo: hace creer
  # que eso ya se mira.
  #
  # **No para y no abre tiquets**, y las dos cosas son a propósito. Lo dice su
  # propia cabecera —«nada de esto decide, informa»— y lo segundo lo enseñó
  # C-307: un aviso automático por pieza y por corrida entierra la lista. Se
  # imprime y se guarda en `medicion`, que es donde un número sobrevive a la
  # corrida.
  # Y solo cuando la entrega es nueva: medir dos veces el mismo fichero da el
  # mismo numero y cuesta las pasadas de ffmpeg enteras.
  if [ "$ENTREGA_NUEVA" = 1 ]; then
    python scripts/suena.py "$n" --guardar 2>&1 | sed 's/^/  /' || true
  fi
  python scripts/sellar.py "$n"
  echo "R$n $(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 "$DESTINO/entrega/reel-R$n.mp4")"
done
# **La verificacion va DESPUES de entregar, y la llama el runner.** No la
# llamaba nadie: los `Reel-RN.verification.md` eran restos de una corrida
# manual, y describian el corte anterior — el del reel 1 decia 82,2 s cuando el
# fichero entregado duraba 101,4. Un documento de verificacion que no cuadra con
# lo que se entrega es peor que no tenerlo, porque se firma igual. Es el
# aprendizaje 24: arreglar el generador no arregla lo generado.
del_lote || node scripts/verificacion.mjs
if [ ${#BLOQUEADAS[@]} -gt 0 ]; then
  echo "CON MOTIVOS ABIERTOS — ${#BLOQUEADAS[@]} pieza(s), renderizadas igual:"
  for b in "${BLOQUEADAS[@]}"; do echo "  · $b"; done
  echo "  Se pueden ver y aprobar. Lo que no se puede es publicarlas."
fi
if [ ${#IDENTICAS[@]} -gt 0 ]; then
  echo "SIN CAMBIOS EN PANTALLA — ${IDENTICAS[*]} salieron identicas al render anterior."
fi
echo "MONTAJE COMPLETO"
