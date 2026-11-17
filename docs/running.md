# Running the line

Commands run from `mi-video/` unless stated. In production that is
`<root>/codigo/mi-video`; in development, the checkout's `mi-video/`.

## 1. Install (development checkout)

```bash
git clone https://github.com/jaolartem/Video-edition.git
cd Video-edition/mi-video
npm ci
python -m pip install numpy scipy opencv-python mediapipe Pillow pyflakes
node scripts/setup-whisper.mjs        # whisper.cpp (CPU build) + model, once
python scripts/gpu.py                 # which whisper / decoder will be used, in one line
```

Then provide a configuration (see [configuration.md](configuration.md)) and copy
it in:

```bash
python scripts/separacion.py --configurar
python scripts/separacion.py --comprobar
npm run lint                           # eslint + tsc: fails without the brand modules
```

Notes on tools:

- Use a **multilingual** whisper model (`medium` or `large-v3`). `.en` models do
  not understand Spanish.
- The binary that transcribes is `whisper-cli.exe`. `main.exe` is a deprecated
  stub that exits successfully without transcribing.
- A GPU build of whisper.cpp, if you have one, goes in `whisper.cpp/`; the CPU
  release goes in its own subfolder, because a GPU build loads any `ggml-*.dll`
  next to it. `scripts/gpu.py` asks each binary and decides; `VIDEO_GPU=0`
  forces CPU.
- Video is decoded on the GPU when available (`gpu.decodifica()`); `-hwaccel`
  must come before `-i`, and the output pixel format is declared explicitly so
  frames are identical either way.

## 2. Paths and disks

- Declare every path in `rutas.json`. Copy raw recordings to a local disk
  (`origen`); cloud-synced folders are slow to read. `bash scripts/traer-brutos.sh`
  copies from `fuentes.drive`.
- The temporary folder (`temporal`) must have **no spaces** and must not be on
  the system disk. Remotion's bundle, Chrome's profile and ffmpeg intermediates
  all go there; `scripts/temporal.mjs` applies it for the CLI
  (`remotion.config.ts`), the Node API (`render.mjs`) and shell scripts
  (`entorno.sh`). `npm run tmp` prints the folder and its free space.
- A batch of five pieces needs about 40 GB free on the temp disk.
- If the repository path has spaces, expect tools that do not quote paths to
  break; keep heavy tools in a path without spaces and link them with
  `rutas.json → linea.compartido`.

## 3. Deploy

The line never runs from the git checkout.

```bash
python scripts/desplegar.py --ver                   # what would change, touches nothing
python scripts/desplegar.py                         # deploy HEAD, checked
python scripts/desplegar.py --raiz <other-root>     # an isolated line, e.g. for tests
python scripts/desplegar.py --aunque-haya-pedidos   # deploy although requests are pending
python scripts/desplegar.py --sin-comprobar         # emergency; recorded in DESPLIEGUE
```

Requirements: clean working tree at the commit being deployed, all checks green
(see [architecture.md](architecture.md#deployment)), a committed configuration,
and no requests pending in the line (or the explicit flag).

## 4. Start the line

From a Git Bash terminal, in `<root>/codigo/mi-video`, naming the pieces:

```bash
bash scripts/arrancar.sh 1 2 3             # LLM steps answered by the Claude CLI
bash scripts/arrancar.sh 1 2 3 --agentes   # LLM steps answered by session agents
```

Before moving anything, `arrancar.sh` sources `scripts/entorno.sh` and checks:

| Check | If it fails |
|---|---|
| `bash`, `node`, `ffmpeg`, `ffprobe` on `PATH` (and `claude` unless `--agentes`) | Install or fix `PATH`. If `bash.exe` disappeared, reinstall Git for Windows |
| `whisper.cpp/whisper-cli.exe` and `whisper.cpp/ggml-medium.bin` | Run `setup-whisper.mjs` or link the folder |
| `DISPARO_APAGADO` not set | `unset DISPARO_APAGADO` |
| At least 40 GB free in the temp disk | Free space |
| Each piece's tape present in `origen` | It tries `traer-brutos.sh` first |
| The Claude CLI really answers (`claude -p ok`), unless `--agentes` | The CLI only has a credential in a terminal where you are logged in; launch from there |

If anything is missing it stops and lists what to do; it never starts half-way.
Otherwise it runs `disparador.py <pieces> --hilos <count>` in a loop, restarting
it when it exits with code 75 (code changed after a deploy).

### Answering LLM steps with session agents

With `--agentes`, requests are left in `work/servicio/`. The operating session
then runs:

```bash
python scripts/dominio/cola.py --lote 1 2 3
```

It prints one block per mailbox (`=== <trade>\t<mailbox>`) with the complete
instruction for that round. Launch **one agent per mailbox and round**, using the
trade's agent definition and the printed instruction **verbatim**. Each agent
reads the contract once and then, for each listed request, reads it and writes
its `.respuesta.json`. Without `--lote`, `cola.py` prints one line per request.

## 5. Each session

```bash
python scripts/donde.py             # where every piece is, from the base and disk
python scripts/monitor.py --recoger # time, rounds, tickets and real agent cost per piece
python scripts/verdad.py            # the single source of each decision; fails on a second copy
python scripts/servicio.py          # requests without an answer
python scripts/cadena.py 3         # from which artefact piece 3 must be re-run
```

## 6. Recording what a human says

Observations about a piece become tickets, with the second they refer to and
which video was watched (the delivery file can be sped up relative to the
montage, so the same second is two different places):

```bash
python scripts/dominio/ticket.py reel-03 30 "the board has no sound" --de entrega
python scripts/dominio/ticket.py reel-03 12 "..." --de montaje
python scripts/dominio/ticket.py --ver reel-03
```

`--de` has no default on purpose. Open tickets travel in the requests of their
piece, already placed at their stage. A ticket is closed only by the person,
with what was done (`--cerrar <id> "<what was done>"`); "discarded, not
possible" is a valid answer.

Guide sheet and approval:

```bash
python scripts/guia.py 3                                   # asks for it, or lets it pass
python scripts/guia.py 3 --aprobar --de "<the person's words>"
python scripts/aprobar.py 3                                # human approval of a version
python scripts/aprobar.py 3 --rehacer "<reason>"           # send it back with a reason
```

The lock lets an agent run `ticket.py` (with `--de` or `--ver`) and
`guia.py --aprobar --de …`; it does not let an agent close tickets, approve
versions, or move pieces back.

## Environment variables

| Variable | Effect |
|---|---|
| `VIDEO_ORIGEN`, `VIDEO_DESTINO`, `VIDEO_TMP` | Override `rutas.json` paths for one run |
| `VIDEO_CONFIG` | Location of the configuration folder |
| `VIDEO_GPU=0` | Do not use the GPU for whisper or decoding |
| `OFICIOS_POR_BASH=0` | Do not call the Claude CLI for LLM steps; leave requests for session agents (set by `--agentes`) |
| `DISPARO_APAGADO` | Disables the trigger's calls to trades; `arrancar.sh` refuses to start while it is set |
| `TEMP`, `TMP`, `TMPDIR` | Set by `entorno.sh` / `temporal.mjs` from `rutas.json → temporal` |

## Known pitfalls

| Symptom | Cause |
|---|---|
| "disk space is low" from Chrome during a render, with space on the declared disk | Something is writing to the system temp; the temp path probably has spaces |
| `remotion still` fills the disk | Each call copies `public/` into a new bundle. Bundle once (`npx remotion bundle src/index.ts --out-dir=work/bundle`) and render stills from it; `mirar.sh` does this |
| `--scale` aborts the render | Remotion checks integer equality; use the exact float (e.g. `1.6666666666666667` for 1080→1800) |
| A script crashes printing an arrow on Windows | Console encoding; scripts run with `PYTHONIOENCODING=utf-8` |
| `set -e` hides why a shell step died | The engine reads the last stdout line as the reason; scripts use `&&` chains and a `trap`, not `set -e` |
| The hook denies a command you expected to pass | Inside a zone only declared line commands pass; run `python ../hooks/no-a-mano.py --probar` to see the rules hold, and read the reason on stderr |
