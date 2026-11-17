# Development

How the machine is changed without breaking what it already does.

## The rule behind every change

An instruction **changes the machine; it does not rebuild it**. Find the best
place to include what was asked. If correcting one small thing touches a dozen
files and regenerates every piece, the change was not included, it was rebuilt
around. `python scripts/alcance.py` shows this before you commit (see below).

Two steps before writing any line:

1. **Look for what exists.** Search for the class, function or rule that already
   does it. A second version of something does not fail; it **diverges**, and
   then both look correct.
2. **Check whether it fits in a class.** A domain datum does not travel as a
   bare list, `dict` or tuple. It travels as an object that can validate itself.
   Domain nouns live in `mi-video/scripts/dominio/` (`Palabra`, `Cinta`, `Tramo`,
   `Segmento`, `Version`, `Pieza`, `Ticket`, …), and each is the owner of its
   truth. If a new noun is needed, declare it there.

The proof a rule was followed: a new rule usually **removes** a file rather than
adding one next to it.

## Code rules

| Area | Rule |
|---|---|
| Size | 300 lines is a ceiling, not a target. `scripts/tamano.py` counts statements (not comments and blank lines) in `scripts/` and `src/` (`.py`, `.mjs`, `.sh`, `.tsx`, `.ts`). Existing debt is declared in `mi-video/docs/tamano-deuda.txt` and can only go down; a new file over the ceiling always fails. Split by responsibility (measure / decide / write), never by line count. |
| Numbers | Each number lives in one place (usually a configuration JSON in `src/brand/`) and every language reads it from there. |
| Paths | Only in `rutas.json`, read through `scripts/rutas.py` / `scripts/rutas.mjs`. |
| Pieces | No `if (slug === …)`. A difference between pieces is a prop or a declared field. |
| Steps | A phase is a row in `CICLO` plus a service class in `scripts/servicios/`. The engine (`avanzar.py`) knows neither. |
| LLM steps | Go through `servicio.pedir()` / `recoger()` only. A tool given to an agent (`scripts/contrato/piezas.py → Herramienta`) declares both what it finds (`halla`) and how the agent answers each finding (`responde`); either half missing fails the build. |
| Failures | A producer that fails must say so (`servicio._falta` → `huecos`), never return an empty value that looks like "nothing found". |
| Shell | Chain with `&&`; the engine reads the **last stdout line** as the reason a step stopped, so scripts print it (trap) instead of dying under `set -e`. |
| TypeScript | Strict, no `any`. Components are pure and deterministic (same props, same frame; no unseeded randomness or clock). Durations in frames. Brand values come from the token modules. Layout in 1080 and scaled up with `--scale`. |
| Python | 3.11. Database access through `scripts/basedatos.py`. |

## Checks

Run them from `mi-video/` and look at the exit code; one broken guard stops the
whole line at deploy time, so they are run before merging, not after.

| Command | What it checks |
|---|---|
| `node scripts/guardas.mjs` | Every correction in the log has a guard and every guard still holds (below); plus chain, shape and camera consistency checks |
| `python scripts/verdad.py` | Each live decision has one declared source, and nothing reads a second copy |
| `python scripts/contratos.py` | Each LLM step's contract: what is required and missing, what is declared but inert (`--prompts` renders shared blocks) |
| `python scripts/comprobado.py --solo-huecos` | Every decision is checked with a **different** signal than the one that produced it |
| `python scripts/tamano.py` | The size ceiling (`--todo` lists every file) |
| `python scripts/separacion.py --comprobar` | Machine, configuration and product are not mixed |
| `python ../hooks/no-a-mano.py --probar` | The lock's test cases (`CASOS`) all hold |
| `npm run lint` | `eslint src && tsc` |
| `python -m pyflakes scripts/` | No undefined names (the deploy fails only on those) |
| `python scripts/humo.py` | Smoke test of the line (marker, mailboxes, guards, engine) and, through `humo_del_corte.py`, of a piece's cut: signed cuts can be restored and still match their fingerprint, deriving the EDL twice changes nothing, and similar invariants. Exit 1 if anything is broken |
| `python scripts/alcance.py` | A mirror, not a gate: classifies uncommitted files as code (`/scripts/`, `/src/`), decisions (`/ads/`, `*.db`), documents (`docs/`, `*.md`, `skills/`) or other, and warns when three or more pieces' decisions changed with two or fewer code files, which is the pattern of rebuilding pieces instead of fixing the mechanism |

`desplegar.py` runs the first eight plus pyflakes and refuses to deploy if any
fails.

## The corrections log and its guards

Every error that cost time is logged in the configuration's
`docs/correcciones.md`, and every entry must name the code that makes it
impossible to repeat. An entry without a guard is a correction that was
described, not made.

Format:

```markdown
## C-<number> Short title of what was fixed

What happened, measured, and why the fix is where it is.

**Guarda.** `mi-video/scripts/some_file.py` :: `def the_function(`
```

- Headings are `## C-NN` or `### C-NN`; other headings are ignored.
- The guard line starts with `**Guarda.**` and holds one or more pairs
  `` `path` :: `needle` `` (path relative to the repository root).
- `::` means the file must contain the needle; `!:` means it must **not** (for
  corrections that consist of removing something).
- The needle is searched literally. Use something that cannot appear by
  accident and that changes when the mechanism changes: a function name, a
  constant, a specific expression. Not a sentence from a comment.

`guardas.mjs` fails when an entry has no guard, when a guard cannot be parsed,
when the file is gone, when a `::` needle is missing or a `!:` needle came back,
when two entries share a number, and when a correction number cited in
`docs/*.md` does not exist in the log (so never write a made-up `C-` plus digits
in a document, not even as an example). It also fails on Python files that
define the same name twice and on bouncy easing in components. If a guard breaks because code was renamed, update the guard;
if it broke because the mechanism was lost, restore the mechanism.

Code, configuration (this log included), documentation and the lock itself are
tools an agent edits in the repository or the configuration folder; the lock
only protects production (see [architecture.md](architecture.md#the-lock)).
Keeping the documentation current is part of every change.

## From change to production

```bash
cd mi-video
# change the code
node scripts/guardas.mjs && python scripts/verdad.py && python scripts/contratos.py \
  && python scripts/comprobado.py --solo-huecos && python scripts/tamano.py \
  && python scripts/separacion.py --comprobar && python ../hooks/no-a-mano.py --probar \
  && npm run lint && python scripts/alcance.py
# log the correction with its guard in <config>/docs/correcciones.md, commit it there
git commit ...                    # the machine change
python scripts/desplegar.py       # checked again, then copied to <root>/codigo
```

Changing a contract (`*.prompt.md`) in the configuration invalidates requests in
flight: deploy when no requests are pending, or answer them first.

## Testing in isolation

`python scripts/desplegar.py --raiz <test-root>` deploys a separate line with
its own data, so a change can be run end to end without touching production.
