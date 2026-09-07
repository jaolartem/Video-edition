#!/usr/bin/env bash
#
# Fotogramas de una pieza SIN renderizar el video, reutilizando el bundle.
#
#   bash scripts/mirar.sh 2                # 3 por escena de reel-02
#   bash scripts/mirar.sh 2 5              # 5 por escena
#   bash scripts/mirar.sh 2 3 494 863      # solo ese tramo de frames
#   bash scripts/mirar.sh --tableros       # 2 por TABLERO, las 24 laminas
#   bash scripts/mirar.sh --tableros 5 7   # solo los de esas piezas
#
# **Y el modo `--tableros` existe porque las 24 laminas se miraban a mano.** El
# lote del 6-9-2026 se juzgo sobre `work/still/tableros/`, una carpeta que no la
# escribia ningun guion: los fotogramas se sacaron a mano de `out/reels/`, o sea
# de renders de las 02:00 con codigo de las 11:55. Sobre esa hoja de contacto
# «sobra negro en las 24» era cierto y ya estaba arreglado en `Fondo.tsx` —seis
# horas antes—, y el pie de cuatro renglones tambien. Mirar lo viejo cuesta lo
# mismo que mirar lo de hoy y decide al reves.
#
# Un tablero se mira en DOS frames y no en uno: al 40% ya entro y al 85% esta
# entero, y la diferencia entre los dos es lo unico que dice si la lamina se
# construye o si ya estaba puesta.
#
# **Por que existe.** Jaime, 6-9-2026: *«si pueden renderizar solo cinco
# fotogramas o tres fotogramas por escena, es lo que necesitamos… con eso pueden
# ver que lo que estan haciendo tiene sentido estetico y que esta bien; unos
# minutos mas, pero muchos menos que cuando sale mal»*.
#
# El coste estaba en el sitio equivocado: `remotion still` **reconstruye el
# bundle en cada llamada** —40 s por fotograma— asi que mirar salia carisimo y se
# dejaba de mirar. Construyendolo UNA vez y reutilizandolo, cada fotograma baja a
# ~7 s. Tres por escena en una pieza de 20 escenas: 7 minutos, no 40.
#
# Y no confundir con mirar lo que YA existe: para eso no se renderiza nada, se
# sacan los fotogramas del render o del bruto con ffmpeg, que es medio segundo.
# Esto es para ver lo que todavia no existe.
set -euo pipefail
cd "$(dirname "$0")/.."

BUNDLE=work/bundle

bundle() {
  # El bundle se rehace solo si lo que dibuja es mas nuevo: es lo caro de todo
  # esto.
  #
  # **Y `src/reels.json` cuenta.** El filtro miraba `*.ts*` y `*.mjs`, o sea el
  # codigo, y el spec es lo que dice QUE se dibuja: se regenera con
  # `node scripts/reels-spec.mjs` y el bundle se quedaba con el de antes. Medido
  # el 6-9-2026: se recompusieron cuatro laminas de reel-07, el spec las traia,
  # y los fotogramas salieron con el `desvio` y la `ListaNumerada` viejos — con
  # el nombre NUEVO en el fichero, que es la peor forma de equivocarse porque
  # parece que se miro lo de hoy. Es el mismo fallo que se estaba corrigiendo:
  # decidir sobre un render viejo.
  if [ ! -d "$BUNDLE" ] || [ -n "$(find src scripts -newer "$BUNDLE" \
       \( -name '*.ts*' -o -name '*.mjs' -o -name '*.json' \) 2>/dev/null | head -1)" ]; then
    echo "== bundle (una sola vez) =="
    npx remotion bundle src/index.ts --out-dir "$BUNDLE" 2>&1 | tail -1
  fi
}

if [ "${1:-}" = "--tableros" ]; then
  shift
  bundle
  SALIDA=work/still/tableros
  mkdir -p "$SALIDA"
  # Los tableros salen de `src/reels.json`, que es lo que el render dibuja: el
  # mismo sitio del que sale la pieza, no una segunda lista de donde caen.
  PYTHONIOENCODING=utf-8 python - "$@" <<'PY' | while read -r comp nombre frame; do
import json, sys
piden = {int(x) for x in sys.argv[1:]}
for p in json.load(open("src/reels.json", encoding="utf-8")):
    n = int(p["id"].replace("Reel-R", ""))
    if piden and n not in piden:
        continue
    for i, b in enumerate(p.get("boards", [])):
        for k, q in enumerate((0.40, 0.85), 1):
            f = b["at"] + round(b["duration"] * q)
            print(f'{p["id"]} R{n}-{i}-{b["kind"]}-{k} {f}')
PY
    npx remotion still "$BUNDLE" "$comp" "$SALIDA/$nombre.png" --frame="$frame" \
      >/dev/null 2>&1 && printf '.' || printf 'x'
  done
  echo ""
  echo "== en $SALIDA =="
  exit 0
fi

N="${1:?pieza}"; POR_ESCENA="${2:-3}"; DESDE="${3:-}"; HASTA="${4:-}"
SLUG=$(printf 'reel-%02d' "$N")
PLAN="work/scenes/$SLUG/plan-full.json"
SALIDA="work/still/mirar/$SLUG"

bundle

mkdir -p "$SALIDA"
FRAMES=$(PYTHONIOENCODING=utf-8 python - "$PLAN" "$POR_ESCENA" "$DESDE" "$HASTA" <<'PY'
import json, sys
plan, por, d, h = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
es = json.load(open(plan, encoding="utf-8"))["escenas"]
d = float(d) if d else None
h = float(h) if h else None
t = 0.0
out = []
for e in es:
    dur = e["origen_hasta"] - e["origen_desde"]
    for k in range(por):
        f = round((t + dur * (k + 1) / (por + 1)) * 30)
        if (d is None or f >= d) and (h is None or f <= h):
            out.append(f)
    t += dur
print(" ".join(str(f) for f in out))
PY
)

echo "== $(echo "$FRAMES" | wc -w) fotogramas de $SLUG =="
for f in $FRAMES; do
  npx remotion still "$BUNDLE" "Reel-R$N" "$SALIDA/f$f.png" --frame="$f" >/dev/null 2>&1 \
    && printf '.' || printf 'x'
done
echo ""
echo "== en $SALIDA =="
