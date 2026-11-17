# Maintaining the machine

## Where to change things

| You need to change | Where |
|---|---|
| How a step works | Its service class in `mi-video/scripts/servicios/`, or the script it calls |
| The order of steps, or a new step | A row in `CICLO` (`scripts/dominio/fase.py`) plus a service class; the engine stays untouched |
| What a domain object knows | Its class in `scripts/dominio/` |
| Which trade answers a mailbox | `scripts/dominio/oficio.py → BUZONES` |
| What the agent instruction says | `scripts/dominio/cola.py → LOTE` (the session uses it verbatim) |
| What the lock allows | `hooks/no-a-mano.py` — a change for the person to make; the lock refuses edits from a session |
| A brand number, a contract, a path | The configuration folder (not this repository); then `separacion.py --configurar` |

Before writing: search for the function or class that already does it. A second
version does not fail, it diverges. A domain datum travels as an object, not as
a bare `dict` or tuple. 300 lines per file is a ceiling, not a target.

## Checks, from `mi-video/`

```bash
node scripts/guardas.mjs \
  && python scripts/verdad.py \
  && python scripts/contratos.py \
  && python scripts/comprobado.py --solo-huecos \
  && python scripts/tamano.py \
  && python scripts/separacion.py --comprobar \
  && python ../hooks/no-a-mano.py --probar \
  && npm run lint \
  && python -m pyflakes scripts/
python scripts/humo.py       # smoke test of the line and of a piece's cut
python scripts/alcance.py    # mirror: did you include the change or rebuild around it?
```

Chain with `&&` and look at exit codes; `set -e` does not stop where you think.
One broken guard stops the whole line at deploy, so run them before merging.

## Logging a correction

Each correction goes into the configuration's `docs/correcciones.md`, with the
code that makes it impossible to repeat:

```markdown
## C-<number> What was fixed

What happened, measured, and why the fix is where it is.

**Guarda.** `mi-video/scripts/<file>` :: `<literal needle>`
```

- `::` the file must contain the needle; `!:` it must not.
- The needle is literal code (a function name, a constant), not prose.
- Never cite a correction number that does not exist: `guardas.mjs` fails on
  dead citations in `docs/*.md`, and on duplicate numbers.

## Deploying

From the repository's `mi-video/`, with a clean working tree at the commit:

```bash
python scripts/desplegar.py --ver   # what would change
python scripts/desplegar.py         # checks, then copies to <root>/codigo
```

It refuses if checks fail, if the configuration has uncommitted changes, if the
machine and the configuration bring the same path, or if requests are pending in
the line (answer them first; a contract change would make them stale). If the
trigger is running, it restarts itself on the new code.

## When the line stops

It stays stopped. Find the reason (`donde.py`, the step's last stdout line in
`video_fase`, `work/*.log`), tell the person in one line with the reason, and
fix the cause in the repository. Do not chase failures live, re-run steps by
hand, loosen a check to reach a render, or patch data in `<root>`. A safety
check that stops a piece is doing its job; the ticket goes to the step that
owns the decision.
