# Architecture

The machine turns long raw recordings into short ads, in batches. Every ad is an
instance of the same Remotion composition with different props; if a piece ever
needs an `if (slug === …)`, a prop is missing.

## Principles that shape the code

| Principle | What it means in practice |
|---|---|
| Scripts measure, remember and repeat | A script never decides something that requires understanding a sentence. It measures (silences, loudness, overlap, edges), stores what was decided, and re-applies what was agreed. |
| An LLM only where understanding is needed | Recognising that two sentences say the same thing, choosing between two takes that both fulfil a stage, deciding what a board shows. Everything else is code. |
| Approved means verified, not re-asked | Asking again is asking for another opinion, and models are not deterministic. A fingerprint (hash) of an approved stage tells whether it is unchanged without reading it again. |
| The segment is the unit | A segment is one stage of the approved script joined with the takes that cover it. Reviews, tickets and approvals are per segment; a correction touches only its segments. |
| One owner per decision | `scripts/verdad.py` declares the single source of each live decision and fails if code reads a second copy. |

## Layers

```
raw recordings (long takes, 4K)
      |
      |  transcribir.py        multi-pass transcription of the whole tape
      v
SQLite base (ads/decisiones.db)  <--- every decision, with its evidence
      |
      |  phases in CICLO        code steps + LLM mailboxes
      v
ads/<slug>/edl-sell.json         the cut (edit decision list)
      |
      |  plan-reel.mjs, punch-ins.py, render-hook.mjs, subtitular.py ...
      v
src/reels.json                   the spec Remotion draws (reels-spec.mjs)
      |
      |  guia.py                  per-second guide sheet, human approval
      |  render.mjs / montar.sh   Remotion render, loudness, mix
      v
out/reels/, out/entrega/         montage render and delivery file
```

`scripts/cadena.py` declares the artefact chain (EDL, plan, framing, cut,
subtitles, face, gaps, background, spec, render, effects, delivery), who
produces each link and what it depends on. It answers "from which link must
this piece be re-run?" by comparing content, not by re-running everything.

## The cycle of phases

The phases are declared in `mi-video/scripts/dominio/fase.py` as `CICLO`, are
migrated into the `fase` table, and are read back by `camino()`. A phase label
names a step **already done**; the service listed is what moves the piece to the
next label. A piece can go back to an earlier label without the engine knowing
anything about the path.

| Order | Label | Moved by | Kind |
|---|---|---|---|
| 1 | `catalogado` | `transcribir.py --barato` | code: whole-tape transcription |
| 2 | `elegido` | `seleccionar.py {n} --edl` | code: take selection, writes the EDL |
| 2.5 | `fijado` | `fijar.py --aplicar {n}` | code: re-applies pinned ranges after selection |
| 3 | `afinado` | `transcribir.py --elegidos {n}` | code: refined transcription of chosen takes |
| 4 | `depurado` | `depurar.py {n}` | code: false starts, dirty edges |
| 5 | `sin_redundancia` | `redundancia.py {n}` | LLM mailbox `redundancia`: annotates what is said twice |
| 5.2 | `recortado` | `revision.py --aplicar {n}` | code: applies annotated cuts to the EDL |
| 5.5 | `revalidado` | service | LLM mailbox `revalidar`: delivery and rhythm on the trimmed cut |
| 6 | `cosido` | `costuras.py {n}` | code: seams between takes |
| 6.5 | `repasado` | service | LLM mailbox `repaso`: last redundancy and consistency pass |
| 7 | `descrito` | `describir.mjs {n}` | LLM mailbox `describir`: what each stage must say and show; writes the designer's brief |
| 7.5 | `disenado` | service | LLM mailbox `disenar`: boards, copy and graphic family |
| 8 | `cortado` | `cortar.py {n}` | code: cuts the montage |
| 10 | `verificado` | `verificar.py {n}` | code: gate checks |
| 11 | `montado` | `montar.sh {n}` | code: guide sheet, then render |
| 11.2 | `nivelado` | `sonoridad.sh {n}` | code: loudness normalisation |
| 11.4 | `medido` | `suena.py {n} --guardar` | code: audio measurements into `medicion` |
| 11.6 | `visto` | service | LLM mailbox `visto`: the designer reviews what was rendered |
| 12 | `revisado` | service | review notes (mailbox `revisar`) |
| 13 | `aprobado` | human | only a person approves (`aprobar.py`) |
| 13.5 | `voz_entregada` | `voz-limpia.py --exportar {n}` | code: exports the raw voice of the approved cut |
| 14 | `voz_limpia` | `voz-limpia.py {n}` | code: brings back the cleaned voice |
| 15 | `masterizado` | `musica.sh {n}` | code: music bed and final mix |
| 15.5 | `respaldado` | service | LLM mailbox `fuentes`: a source for every figure |
| 16 | `publicado` | `publicar.py --finales {n}` | code: publishes finals |

Ordering rules that are deliberate:

- Annotated cuts are applied (`recortado`) **before** the second assessment, so
  it judges the piece without what is superfluous.
- Composition is two steps: `descrito` defines what there will be, `disenado`
  builds it. Both run before `cortado`, so design is not paid twice for a cut
  that can still move.
- Loudness and measurement run before human review: human judgement is the most
  expensive filter and is spent once, on something that passed the cheap ones.
- The clean voice is exported **after** approval, so the exported audio matches
  the cut that will be delivered.

If a piece is at `montado` or later but its render is older than its cut (by the
spec fingerprint stored next to the file in `reel-RN.mp4.huella`, or by the
chain), the engine moves it back to `verificado` with the reason. A piece signed
off by a human is not moved back by a date.

## The engine and the trigger

| File | Responsibility |
|---|---|
| `scripts/avanzar.py` | Walks one piece along the path until it reaches the end, waits for someone, or a service fails. Those three stops are different and are logged differently. Everything inside is wrapped at the router boundary so no failure escapes without a log line. |
| `scripts/disparador.py` | Stays running and calls one round of `avanzar` every `--cada` seconds (default 30) over the given pieces, `--hilos` pieces in parallel. A round that finds nothing costs no tokens. |
| `scripts/planificador.py` | Grants the single "house turn" only to steps that rewrite a tape; LLM steps pass without a lock. |
| `scripts/servicios/` | One class per service. Adding a step is inserting a row and registering an object; the engine does not know which scripts sit underneath. |
| `scripts/dominio/` | Domain nouns (`Pieza`, `Cinta`, `Tramo`, `Palabra`, `Segmento`, `Version`, `Ticket`, `Lienzo`, `Idioma`, …). Each owns its truth; questions about a tape are asked to the tape. |

When the same waiting state repeats, it is counted (`veces`) instead of being
written again, and a warning is raised at 6, 12, 24, 48 and 96 identical rounds.

## Mailboxes and trades

An LLM step is a function with a signature: a file goes in, a file comes out.

```
work/servicio/<mailbox>/<slug>.pedido.json      what the step asks
work/servicio/<mailbox>/<slug>.prompt.md        the same prompt, readable line by line
work/servicio/<mailbox>/<slug>.respuesta.json   what the service answers
```

`servicio.pedir()` writes the request and, if allowed, tries the Claude CLI. If
the CLI is not available it leaves the request in place and returns nothing: the
step says so and nobody improvises. `servicio.recoger()` reads the response
whoever wrote it, validates it, and passes it on. An unreadable response is
archived as rejected and the request goes back into the queue.

Two trades answer all mailboxes, split by **criterion**, not by step: a composer
(editorial criterion) and a designer (aesthetic criterion). They share the same
tools (`scripts/consulta.py` verbs); what separates them is the criterion, not
the information. The mapping lives in `scripts/dominio/oficio.py`, `BUZONES`:

| Mailbox | Trade | Phase it moves |
|---|---|---|
| `describir` | `compositor` | `descrito` |
| `disenar` | `disenador` | `disenado` |
| `visto` | `disenador` | `visto` |
| `redundancia` | `compositor` | `sin_redundancia` |
| `revisar` | `compositor` | `revisado` |
| `revalidar` | `compositor` | `revalidado` |
| `repaso` | `compositor` | `repasado` |
| `fuentes` | `compositor` | `respaldado` |
| `guia` | none (a human) | gate before the render |

Trade names are the agent names in `.claude/agents/` (configuration). Each
request carries a common context built in one place (`servicio.contexto`):
today's date, sourced figures, standing batch-wide instructions, open tickets
for the piece placed at their stage, what is already decided, the piece's own
facts, and its state document. Fields that could not be built travel in
`huecos`, so "there is nothing" and "the lookup failed" never look the same.
Requests carry only the segments that changed since the last accepted answer
(`dominio/memoria.py`), and only the contract sections that step reads
(`dominio/pliego.py`).

Who writes the answer:

- **The CLI**, through `claude --agent <trade>` launched from `mi-video/`, when
  `OFICIOS_POR_BASH` is not `0` and the CLI has a credential in that terminal.
- **Session agents** (`arrancar.sh … --agentes`): the session runs
  `python scripts/dominio/cola.py --lote <pieces>`, which prints one ready-made
  instruction per mailbox and round, and launches one agent per mailbox with that
  instruction **verbatim**. The agent reads the contract once, then answers each
  request in turn.

## The guide sheet

`scripts/guia.py` draws one frame per second of the current spec from the
Remotion bundle (no render) via `mirar.sh --segundos`, and composes contact
sheets with the montage second printed on each frame (`out/guia/<slug>/`). The
piece then waits at the gate of the render with an open request in the `guia`
mailbox, which has no trade: a human answers it.

- Approval is recorded with the person's own words and the fingerprint of the
  spec they saw: `python scripts/guia.py <n> --aprobar --de "<what they said>"`.
- Each second has its own fingerprint (`dominio/fotograma.py`): the drawing code,
  the global spec (EDL, cuts, format), and only the timed elements on screen in
  that second (±1 s). Changing one board redraws only the seconds it touches;
  approved seconds stay approved.
- A piece already signed off does not ask for a guide sheet again.

## Deployment

Development happens in a git checkout; production runs from a deployed copy.

```
<root>/codigo/   the tree of one machine commit + one configuration commit
<root>/datos/    ads/, work/, out/, public/, reels.json: the line's memory
<root>/nodo/     node_modules, shared across deployments
```

`scripts/desplegar.py`:

1. Requires a clean working tree at the commit being deployed.
2. Runs the checks (`guardas.mjs`, `verdad.py`, `contratos.py`,
   `comprobado.py --solo-huecos`, `tamano.py`, `separacion.py --comprobar`,
   `hooks/no-a-mano.py --probar`, `npm run lint`) plus a `pyflakes` scan for
   undefined names. Any failure stops the deploy; the line keeps what it had.
3. Refuses if requests are pending in the line (a contract change would make
   them stale), unless `--aunque-haya-pedidos`.
4. Composes the machine tree (`git archive`) with the configuration tree (the
   configuration repo's `HEAD`, which must be clean). If both bring the same
   path, it stops: every path has one owner.
5. Writes only files whose content changed, with the current time, so the
   chain invalidates only what really changed. Removes files that left the
   tree, except data paths.
6. Links data into `codigo/mi-video/` with directory junctions (`ads`, `work`,
   `out`, `public`, `node_modules`, plus `linea.compartido` entries) and hard
   links `src/reels.json` and `src/ganchos.json`, so no script changes paths.
7. Rewrites `rutas.json → destino` to `<root>/datos/out`, runs `npm ci` only if
   the lockfile changed, writes `codigo/mi-video/DESPLIEGUE` (commits, branch,
   date, whether checked) and a row in the `despliegue` table.

If the trigger is running when code changes, it exits with code 75 and
`arrancar.sh` restarts it on the new code.

## The lock

`hooks/no-a-mano.py` is a `PreToolUse` hook. It works by **zones** and an allow
list: inside a zone, only what is declared passes.

Zones: the line root, the configuration folder, any `.db`, scene documents
(`/escenas/e…`), `pieza.json`, `guion.json`, `estado.json`, `frames.json`,
`glosario.json`, `decisiones.db`, `apoyo.json`, and the lock itself
(`hooks/no-a-mano.py`, `hooks/hooks.json`, `.claude/settings*.json`,
`.claude/hooks/`).

Allowed inside a zone:

| Action | Rule |
|---|---|
| Read | Any command without write signals; SQLite only with `mode=ro` |
| Line commands | Scripts in `PERMITIDOS`: `donde.py`, `monitor.py`, `verdad.py`, `cola.py`, `desplegar.py`, `arrancar.sh`, `consulta.py`, `tablero.py`, `ticket.py`, `guia.py`, `separacion.py`, `tamano.py`, `alcance.py`, `guardas.mjs` |
| Act as a cog | Write `work/servicio/<mailbox>/<slug>.respuesta.json` |
| Log a correction | Write `<config>/docs/correcciones.md` |

Explicitly denied even with an allowed script: `--volver` (moving a piece back),
`ticket.py --cerrar/--ruta/--estado` (closing or rerouting tickets), `ticket.py`
without `--de` or `--ver`, `guia.py --aprobar` without `--de`, SQL writes, and
importing `servicios` by hand. Exit code 2 with the reason on stderr means
denied. `python hooks/no-a-mano.py --probar` runs its test cases (`CASOS`), and
the deploy runs them too.

## Formats and languages

- **Format** is a property of the piece (`formato` in `ads/frames.json`;
  default vertical). Sizes, safe bands and crop ratios live only in the
  configuration's `src/brand/lienzos.json`, read by `dominio/lienzo.py`,
  `scripts/lienzo.mjs` and `src/brand/lienzo.ts`.
- **Language** is a property of the tape (`rutas.json → idiomas`, tape → code;
  default Spanish). `dominio/idioma.py` reads the per-language rules in
  `scripts/idiomas/<code>.json` (whisper language, function words, etc.).
  Content is written natively in the language produced, never translated.
