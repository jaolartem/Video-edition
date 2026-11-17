---
name: video-edition
description: Operate the Video-edition batch pipeline (Remotion + Python) that edits short talking-head ads from long raw recordings, scene by scene. Use it whenever you have to start or watch that line, answer one of its step requests (a `work/servicio/<mailbox>/<slug>.pedido.json` waiting for its `.respuesta.json`), record what the person says about a piece, approve a guide sheet on their behalf with their words, or fix and deploy the pipeline's code. Do not use it to edit a video by hand outside the line.
---

# Operating the video-edition machine

This is not a program you run and walk away from, and it is not an editor you
replace. It is a production line that you operate. Scripts **measure what is
measurable, remember what was decided and repeat what was agreed**. Where a
step needs understanding, it asks, and the answer is a file the next step
reads.

You have exactly two roles. There is no third.

| Role | What you do | What you never do |
|---|---|---|
| **Maintain the machine** | Fix what breaks in the code or configuration, close gaps where a decision gets lost, put into code what only lived in someone's head, keep the documentation current; then check and deploy | Patch the running line, the database or a piece's files to get past an error |
| **Act as a cog** | When a step asks (a `.pedido.json`), answer it as the service would: write the `.respuesta.json` that step reads, with the batch instruction `cola.py` prints, verbatim | Decide outside the line, compose your own instruction, or answer a question nobody asked |

Doing the machine's work by hand (reading a dossier and editing the database,
the cut or a scene document directly) looks faster and is exactly how state is
lost: the decision exists, is not recorded, and the next step does not see it.
A lock hook makes it impossible; see [The lock](#the-lock).

## Vocabulary

| Term | Meaning |
|---|---|
| Piece | One ad. Slug `reel-NN`; scripts take the number (`3`) |
| Segment / scene / stage | One stage of the approved script joined with the takes that cover it. **The unit of analysis.** |
| Phase | The label of a piece in the database (`catalogado` … `publicado`), declared in `scripts/dominio/fase.py → CICLO`. It names a step already done |
| Mailbox (`buzón`) | Folder `work/servicio/<mailbox>/` where an LLM step leaves requests |
| Trade (`oficio`) | Who answers a mailbox: `compositor` (editorial criterion) or `disenador` (aesthetic criterion) |
| Request / response | `<slug>.pedido.json` / `<slug>.respuesta.json` in a mailbox |
| Ticket | An observation by the person on one piece, at one second |
| Guide sheet | One frame per second of the spec, approved by the person before the full render |
| `<root>` | The production root: `<root>/codigo` (deployed code), `<root>/datos` (data) |

Identifiers (phases, scripts, tables, fields) are Spanish. Use them as written.

## First thing in any session

The line does not live in the repository. It lives in `<root>`, read from
`mi-video/rutas.json → linea.raiz`. From `<root>/codigo/mi-video`:

```bash
python scripts/donde.py              # where every piece is, from the base and the disk
python scripts/monitor.py --recoger  # time, rounds, tickets and real agent cost per piece
python scripts/verdad.py             # where each decision comes from
python scripts/servicio.py           # requests waiting for an answer
```

If `donde.py` answers, you do not need any earlier conversation. If it does not
answer something, that gap is a defect of the machine: fix it in the repo.

## Starting the line

From a Git Bash terminal in `<root>/codigo/mi-video`, always naming the pieces:

```bash
bash scripts/arrancar.sh 1 2 3            # LLM steps answered by the Claude CLI
bash scripts/arrancar.sh 1 2 3 --agentes  # LLM steps answered by agents of this session
```

It checks bash, node, ffmpeg, whisper.cpp, disk space, tapes and the CLI
credential before moving anything. If something is missing it stops and says
what. Report that to the person; do not work around it. The CLI only has a
credential in a terminal where the person is logged in.

## Acting as a cog: answering requests

With `--agentes`, requests accumulate in `work/servicio/`. Each round:

1. Run `python scripts/dominio/cola.py --lote <pieces>`.
2. For every block it prints (`=== <trade>\t<mailbox>`), launch **one agent per
   mailbox**, of that trade (`compositor` or `disenador`), and give it the block's
   text **exactly as printed**. Do not rewrite, shorten or add to it: a
   hand-composed instruction is a different instruction every time.
3. Wait for the agents. Each one reads the contract once, then for each request
   reads it and writes its `.respuesta.json`.
4. The line picks the answers up on its next round. Run the queue again for the
   next round.

If you answer a request yourself (no sub-agents available), follow the same
instruction: read the contract (`<slug>.prompt.md` beside the request), the
request, its contact sheets; write the response; nothing else.

Rules for an answer:

- It is a **review** of what code already did, not a composition from scratch.
  If it complies, answer the minimum the contract admits and change only what
  does not comply.
- It concerns **only the segments in the request**. Requests carry only the
  segments that changed; approved segments are not reopened.
- Open tickets arrive inside the request, placed at their stage. With a ticket,
  the goal is the best segment with that problem solved and nothing else moved.
  Without one, the best piece with what there is.
- "Discarded: not possible, the take does not exist" is a valid answer.
  Disappearing is not.
- Anything that would change what the viewer understands (a figure without a
  source, a changed price or date, a stage left without material, anything
  presented as a real case) goes up to the person through the response keys the
  contract declares for that. Execution details are decided, not asked.

Details: [references/requests.md](references/requests.md).

## Scene by scene, joined at the end

- Work on segments, never on the whole piece. A correction is located in its
  segments and only those are resolved.
- Approval is per segment and against a specific cut. If a segment's range
  moves, what was approved was something else; if it does not move, it stays
  approved.
- The piece is the union of its segments, joined at the end by the line
  (`costuras.py`, `cortar.py`, `reels-spec.mjs`, the render).
- Before the full render, the line draws the guide sheet (`out/guia/<slug>/`) and
  waits in the `guia` mailbox. Only the person approves it. When they do, record
  it with their words:
  `python scripts/guia.py <n> --aprobar --de "<their words>"`.
  Approved seconds stay approved when the spec changes elsewhere.

## Recording what the person says

What the person says about a piece does not stay in the chat. Each observation
is a ticket with its second, and with which video they watched:

```bash
python scripts/dominio/ticket.py reel-03 30 "<their observation>" --de entrega
python scripts/dominio/ticket.py reel-03 30 "<their observation>" --de montaje
python scripts/dominio/ticket.py --ver reel-03
```

`--de entrega` is the published file; `--de montaje` is `out/reels`. The
delivery can be sped up, so the same second is a different place in each, and
the difference grows towards the end. There is no default on purpose. Record
the ticket **before** checking it; checking first and moving on loses it.

Tickets are closed by the person, not by you. If they say "leave it", record
that with `--de`; they run the close.

## Maintaining the machine

When something breaks:

1. If the line stops, it **stays stopped**. Tell the person what stopped and why
   (the reason is in `donde.py`, the logs under `work/`, or the step's last
   stdout line).
2. Fix the cause in the **repository**, not in `<root>`. Before writing code,
   look for the class or function that already does it, and put domain data in
   a class in `scripts/dominio/`.
3. Log the correction in the configuration's `docs/correcciones.md` with its
   guard: `**Guarda.** \`path\` :: \`needle\``.
4. Run the checks, commit, and deploy:
   `python scripts/desplegar.py` (from the repo's `mi-video/`, clean tree).
5. Run `python scripts/alcance.py`: if a small instruction touched many pieces'
   decisions with little code, you rebuilt instead of including it.

An instruction from the person **changes the machine; it does not rebuild it**.
Find the best place to include it.

Details: [references/maintaining.md](references/maintaining.md).

## The lock

`hooks/no-a-mano.py` runs before every `Write`, `Edit`, `Bash`, `PowerShell` or
terminal call. It protects **production, not tools**. Inside the line
(`<root>`), the database or piece/scene/script documents, only this passes:

- reading (SQLite only with `?mode=ro`);
- the line's own commands: `donde.py`, `monitor.py`, `verdad.py`, `cola.py`,
  `desplegar.py`, `arrancar.sh`, `consulta.py`, `tablero.py`, `ticket.py` (with
  `--de` or `--ver`), `guia.py` (`--aprobar` only with `--de`), `separacion.py`,
  `tamano.py`, `alcance.py`, `guardas.mjs`;
- writing a `work/servicio/<mailbox>/<slug>.respuesta.json`.

Everything else there is denied with exit code 2 and the reason, writing `git`
commands included. A denial is the answer, not an obstacle: do not look for
another way to do the same thing. In particular you never move a piece back a
phase, write to the database or `<root>`, close or reroute tickets, or approve
a version.

Code, configuration, instructions, documentation and the lock itself are tools:
you edit them in the repository or the configuration folder, and keeping the
documentation current is part of your job. They reach the line only through
`desplegar.py`, which runs `hooks/no-a-mano.py --probar`, so a weakened lock
fails the deploy.

Command reference: [references/commands.md](references/commands.md).

## Where the configuration is

The repository holds only the machine. The configuration (brand tokens in
`mi-video/src/brand/`, agent contracts `mi-video/scripts/*.prompt.md` and
`docs/piso.md`, agent definitions `.claude/agents/compositor.md` and
`disenador.md`, operator instructions such as `CLAUDE.md`, and
`mi-video/rutas.json`) is a separate folder with its own git and the same
relative paths, by default `<main checkout>/configuracion`, or `$VIDEO_CONFIG`.

- In development: `python mi-video/scripts/separacion.py --configurar` copies it
  into the tree read-only. Edit it in its own folder, never in the tree.
- In production: `desplegar.py` composes it with the machine commit.
- Read the configuration's `CLAUDE.md` and its playbook before judging content:
  priorities, compliance rules and the visual canon are the person's, not yours.

If there is no configuration, the line cannot run. Say so; do not invent one.

## Reporting to the person

- First what they need to decide or do. If nothing, say so in one line.
- At most three points. Concrete numbers ("CTA of 7.2 s"), not adjectives.
- No chronology of what you tried. What got fixed with no decision pending is
  recorded in the docs and not reported.
- Ask about what changes the message; decide what only changes the execution.
- If an order collides with a limit of the system, say it cannot be done and
  why, and let them redirect.

## References

- [references/phases.md](references/phases.md): the cycle of phases and which
  mailbox and trade move each one.
- [references/requests.md](references/requests.md): the request/response
  protocol in detail.
- [references/commands.md](references/commands.md): commands by task, and what
  the lock allows.
- [references/maintaining.md](references/maintaining.md): checks, guards,
  deploy.
