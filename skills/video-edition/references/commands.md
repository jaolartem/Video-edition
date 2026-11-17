# Commands by task

Run from `<root>/codigo/mi-video` for the line, or from the repository's
`mi-video/` for development.

## Look

| Task | Command |
|---|---|
| Where every piece is | `python scripts/donde.py` |
| Cost, time, rounds, tickets per piece | `python scripts/monitor.py --recoger`, then `python scripts/monitor.py [reel-NN]` |
| Source of each decision | `python scripts/verdad.py` |
| Pending requests | `python scripts/servicio.py` |
| Queue for session agents | `python scripts/dominio/cola.py --lote <n…>` (one block per mailbox) or without `--lote` (one line per request) |
| A fact the line knows | `python scripts/consulta.py <verb> '<json args>'` |
| A piece's tickets | `python scripts/dominio/ticket.py --ver reel-NN` |
| Read the base | `python -c "import sqlite3; c = sqlite3.connect('file:ads/decisiones.db?mode=ro', uri=True); ..."` (the lock requires `mode=ro`) |

## Run

| Task | Command |
|---|---|
| Start the line | `bash scripts/arrancar.sh <n…> [--agentes]` (Git Bash, a terminal where the CLI is logged in unless `--agentes`) |
| Ask for / pass the guide sheet | `python scripts/guia.py <n>` |
| Record the person's approval of the guide sheet | `python scripts/guia.py <n> --aprobar --de "<their words>"` |
| Record an observation | `python scripts/dominio/ticket.py reel-NN <second> "<text>" --de entrega\|montaje` |
| Deploy the repository's HEAD | `python scripts/desplegar.py` (`--ver` to preview) |

## Only the person

`aprobar.py` (approve or send back a version), `ticket.py --cerrar` (close a
ticket), and any decision that changes the message. You record their words; they
run the close.

## What the lock allows inside a zone

Zones are production only: the line root (`rutas.json → linea.raiz`) and,
inside the machine project or the line, any `*.db`, `escenas/e*`, `pieza.json`,
`guion.json`, `estado.json`, `frames.json`, `glosario.json`, `apoyo.json`.
Code, configuration, documentation and the lock itself are not zones: edit them
in the repository or the configuration folder; they reach the line through
`desplegar.py`, which fails if `--probar` does.

| Passes | Denied |
|---|---|
| Commands without write signals (`ls`, `tail`, `cat`, …) | `cp`, `mv`, `rm`, `tee`, `touch`, `mkdir`, `sed -i`, `ffmpeg`, redirections `>`, PowerShell write cmdlets |
| SQLite with `mode=ro` | Any SQL write, any non-`mode=ro` connection, `basedatos.abrir` |
| The listed line scripts | Any other script or interpreter run against the line (`avanzar.py`, ad-hoc Python, `import servicios`) |
| `ticket.py --de …`, `ticket.py --ver` | `ticket.py --cerrar/--ruta/--estado`, `ticket.py` without `--de` |
| `guia.py --aprobar --de …` | `guia.py --aprobar` without `--de` |
| Writing `work/servicio/<mailbox>/<slug>.respuesta.json` | Writing any other file in a zone |
| Reading git (`status`, `log`, `diff`, …) | Writing git (`apply`, `checkout`, `restore`, `reset`, `rm`, `mv`, `clean`, `stash`, `am`, `cherry-pick`, `merge`, `pull`, `commit`, `switch`, `rebase`) |
| | `--volver` anywhere (moving a piece back a phase) |

Inline code with `python -c` / `node -e` passes only if it shows no write
signals. `python hooks/no-a-mano.py --probar` runs the lock's own test cases.
