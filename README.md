# Video-edition

A batch pipeline ("the machine") that edits short talking-head ads out of long
raw recordings. It is built on [Remotion](https://www.remotion.dev/) (React) for
composition and rendering, and on Python, Node and shell scripts for everything
around it: transcription, take selection, redundancy removal, cutting, sound,
verification and delivery. Pieces can be in Spanish or English, vertical (9:16)
or horizontal (16:9).

The machine is meant to be operated by an agent (it ships as a Claude Code
plugin with a skill), but it is not an autonomous editor. Scripts **measure what
is measurable, remember what was decided and repeat what was agreed**. A
language model is called only where a step needs understanding (is this the
same sentence said twice? which of two takes delivers better? what goes on this
board?), and its answer is written to a file that the next step reads. Anything
already approved is verified, never re-discussed.

## How it works, in one screen

- **A piece is a set of scenes.** The unit of analysis is the *segment*: one
  stage of an approved script, joined with the recorded takes that cover it.
  Every decision, review, ticket and approval is attached to a segment. The
  piece is the union of its segments, joined at the end.
- **A cycle of phases.** Each piece carries a phase label in a SQLite database.
  Each phase names the service that moves it to the next one
  (`mi-video/scripts/dominio/fase.py`, `CICLO`). A trigger loop
  (`disparador.py`) keeps moving labels; when a step cannot proceed it records
  why and waits.
- **LLM steps are mailboxes.** A step that needs judgement writes
  `work/servicio/<mailbox>/<slug>.pedido.json` and waits for a
  `<slug>.respuesta.json` next to it. Who writes the answer (the Claude CLI, an
  agent in a session, a person) does not matter: the file is the contract and
  the record.
- **A guide sheet before the render.** Before the full render, a per-second
  contact sheet is drawn from the Remotion bundle and approved by a human.
- **Production never runs from git.** `desplegar.py` copies a checked commit into
  `<root>/codigo`; data lives in `<root>/datos`. A lock hook prevents agents
  from editing the running line, its database, its documents or the
  configuration by hand.

See [docs/architecture.md](docs/architecture.md) for the full picture.

## Machine, configuration and product

This repository contains **only the machine**. Two other things are kept apart
on purpose, and `mi-video/scripts/separacion.py --comprobar` fails if they mix:

| | What it is | Where it lives |
|---|---|---|
| Machine | Code, schemas, checks, the lock, this documentation | This repository |
| Configuration | Brand/style tokens, agent contracts (`*.prompt.md`), agent definitions, operator instructions, `rutas.json` | A separate folder with its own git, same relative paths, composed in at deploy time |
| Product | Recordings, the decisions database, per-piece outputs, renders | `<root>/datos` on the production disk; never in git |

The declaration is `separacion.json` at the repository root. Without a
configuration the machine does not build or run: brand modules imported by the
Remotion components, the agent contracts and the paths are all configuration.
[docs/configuration.md](docs/configuration.md) lists what is expected and what
each file is for.

## Requirements

| Tool | Version / note |
|---|---|
| Windows + Git for Windows (Git Bash) | The shell scripts run under Git Bash; directory junctions are created with `mklink /J` |
| Python | 3.11, with `numpy`, `scipy`, `opencv-python`, `mediapipe`, `Pillow`, `pyflakes` |
| Node.js | 24 (Remotion 4.0.518, React 19) |
| ffmpeg / ffprobe | On `PATH` |
| whisper.cpp | `whisper.cpp/whisper-cli.exe` + a multilingual `ggml-*.bin` model (not a `.en` model) |
| Claude Code CLI | Only if LLM steps are answered by the CLI instead of session agents |

Temporary paths must not contain spaces (some subprocesses do not quote paths
and silently fall back to the system temp). Details in
[docs/running.md](docs/running.md).

## Documentation

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Phases, mailboxes, trades, the guide sheet, deploy, the lock |
| [docs/configuration.md](docs/configuration.md) | Expected configuration layout and the role of each file |
| [docs/data.md](docs/data.md) | Production data layout, the database, request/response files |
| [docs/running.md](docs/running.md) | Installing, deploying, starting the line, recording feedback |
| [docs/development.md](docs/development.md) | Code rules, checks, the corrections log and its guards |
| [skills/video-edition/SKILL.md](skills/video-edition/SKILL.md) | How an agent operates the machine |

Most code comments and identifiers are in Spanish (phase names, table names,
script names). The documentation translates the mechanics; the identifiers are
kept as they are because they are what you type.

## Install as a Claude Code plugin

```text
/plugin marketplace add jaolartem/Video-edition
/plugin install video-edition@video-edition
```

The plugin root is the repository root, so Claude Code discovers:

- `skills/` — the `video-edition` skill;
- `hooks/hooks.json` — the lock (`hooks/no-a-mano.py`) as a `PreToolUse` hook on
  `Write`, `Edit`, `MultiEdit`, `NotebookEdit`, `Bash`, `PowerShell` and terminal
  commands.

**The hook only acts inside a machine project** — a project whose root has
`separacion.json`. Anywhere else it lets everything through. Inside one, it
denies writes to the line root declared in `rutas.json`, the configuration
folder, and — within the project or the line — any `*.db`, `pieza.json`,
`guion.json`, `estado.json`, `frames.json`, `glosario.json`, `apoyo.json` or
`escenas/e*` file. It also refuses edits to itself and to the settings that wire
it. Inside this repository, `.claude/settings.json` wires the same hook through
`$CLAUDE_PROJECT_DIR`.

## Using it with other agents

`skills/video-edition/` follows the Agent Skills layout: a folder with a
`SKILL.md` (YAML frontmatter with `name` and `description`, then Markdown) and a
`references/` folder it links to. Agents that load that format can use the same
folder; check your agent's documentation for where it looks for skills.

ChatGPT does not load skills by itself. To use the same instructions there,
upload the files in `skills/video-edition/` (the `SKILL.md` and the
`references/*.md`) as project files, and put the body of `SKILL.md` in the
project instructions. That gives it the operating rules; it can only run the
commands if it has a shell on the machine where the line is deployed. This
setup has not been tested here.

## License

This project is licensed under the GNU General Public License v3.0; see
[LICENSE](LICENSE).

Remotion is not covered by that license. It has its own license, which requires
a paid company license for some organizations:
<https://www.remotion.dev/license>. Check it before using this pipeline
commercially.

Author: [jaolartem](https://github.com/jaolartem).
