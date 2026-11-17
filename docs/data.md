# Data

The product (recordings, decisions, intermediate files, renders) never goes to
git. In production it lives under `<root>/datos` and is linked into
`<root>/codigo/mi-video/` so every script uses the same relative paths it uses in
development (`ads/decisiones.db` is always `ads/decisiones.db`).

## Production layout

```
<root>/
  codigo/                      machine commit + configuration commit (see architecture.md)
    mi-video/
      DESPLIEGUE               JSON: deployed commit, configuration commit, branch, date, checked
      ads/      -> datos/ads   (directory junction)
      work/     -> datos/work
      out/      -> datos/out
      public/   -> datos/public
      node_modules/ -> nodo/node_modules
      <linea.compartido entries, e.g. whisper.cpp/>
      src/reels.json   (hard link to datos/reels.json)
      src/ganchos.json (hard link to datos/ganchos.json)
  datos/
    ads/ work/ out/ public/
    reels.json ganchos.json
    despliegue.manifiesto.json   every path the last deploy wrote
  nodo/
    node_modules/ package.json package-lock.json
```

In a development checkout the same folders exist under `mi-video/` and are
git-ignored.

## `ads/`: decisions

| Path | Contents |
|---|---|
| `ads/decisiones.db` | The SQLite base: the project's memory. Opened through `scripts/basedatos.py`, which declares timeouts. Agents read it only with `?mode=ro`. |
| `ads/frames.json` | Per piece: the structure (frame) it executes, the function of each stage, `formato` (`vertical` / `horizontal`), and `deriva_de` when a piece reuses another's tape |
| `ads/glosario.json` | Domain terms used to correct transcripts |
| `ads/estado.json` | Per-beat verdicts (`aprobado`, `recortar`, `rechazado`, `pendiente`) kept by `scripts/estado.py`: an approved beat is never re-chosen by the montage |
| `ads/fondos.json` | Which background plates exist, what each draws, and which one each piece uses |
| `ads/<slug>/edl-sell.json` | The cut: segments in order with their tape and ranges |
| `ads/<slug>/estado.json` | The piece's state document (the "marker"): current phase, open tickets, and per-segment labels. Written by `dominio/estado.py` whenever a phase changes; trades propose a label for a segment inside their response, never by editing this file |

Slugs are `reel-NN`; Remotion composition ids are `Reel-RN`. Piece numbers are
passed to scripts as plain integers (`arrancar.sh 1 2`).

### The base

The full schema is in `scripts/esquema.sql`, `scripts/esquema-modelo.sql` and
`scripts/migraciones.py`. The tables an operator meets most:

| Table / view | What it holds |
|---|---|
| `video`, `fase`, `video_fase` | Pieces, the phase catalogue (migrated from `CICLO`), and every phase change with its reason. A repeated identical wait is counted in `veces` instead of written again |
| `version`, `aprobacion` | A version is a **cut** (fingerprint of ranges and tapes), not a render. Approvals point to a version |
| `segmento` | Per-segment review and approval, stamped against the cut it was approved on |
| `libreto`, `estructura`, `etapa*` | The script stage by stage, the frame structures and stage catalogues |
| `escena_desc` | Per-stage description: the composer's fields and the designer's board, each owned by one step (`dominio/escena.py`) |
| `revision` | Cuts annotated by redundancy and review, anchored to text so they survive a re-cut, with their state |
| `ticket` | Observations on one piece, with the second they refer to and the answer when closed |
| `instruccion` | Batch-wide criteria, with how many times each was given and the guard that makes it unnecessary to repeat |
| `dato`, `precio` | Figures with source, validity and conditions; current prices |
| `medicion`, `tipo_medicion` | Audio and other measurements per piece |
| `gasto` | Agent cost per piece, collected from transcripts by `monitor.py --recoger` |
| `despliegue` | One row per deploy |
| `v_verdad`, `v_pendiente`, `v_plan`, `v_memoria` | Views: live decisions with their single source, pending work, plan, request memory |

`python scripts/donde.py` reconstructs where every piece is (version and whether
the cut changed, approval, audio, publication, pending items, whether it would
pass verification now) from the base and the disk only. If it answers, no
conversation context is needed.

## `work/`: intermediates and requests

| Path | Contents |
|---|---|
| `work/servicio/<mailbox>/<slug>.pedido.json` | Open request of an LLM step |
| `work/servicio/<mailbox>/<slug>.prompt.md` | The same request's prompt, as readable text (the contract sections that step reads, after the shared floor) |
| `work/servicio/<mailbox>/<slug>.respuesta.json` | The answer. The **only** file in the line an agent may write |
| `work/servicio/<mailbox>/<slug>.<k>[.<mark>].{pedido,respuesta}.json` | Archived pairs: consumed (`k` numbered), `rechazada` (unreadable or failed schema), `sin_json` (state document incomplete), or stale |
| `work/scenes/<slug>/` | Per-piece plan (`plan-full.json`), face, gaps, background, spec fingerprint |
| `work/subs/<slug>.json` | Subtitles |
| `work/still/guia/<slug>/<fingerprint>/` | Guide-sheet frames, one per second |
| `work/bundle/` | Reused Remotion bundle |
| `work/*.log` | Trigger and assembly logs |

### Request and response files

A request is JSON with, at the top level: `paso` (the mailbox), `slug`,
`prompt` (a reference to the `.prompt.md` beside it), the common context built
by `servicio.contexto()` (date, sourced figures, standing instructions, prices,
tickets on the piece, decisions already taken, the piece's facts, the state
document), `huecos` when some context could not be built, and `datos`, the
step-specific payload. Field names are Spanish; read them in the request.

Rules the protocol enforces:

- A request is rewritten only when its question changed, so a response older
  than its request is known to answer an earlier question and is archived.
- Without the full state document, no request is issued.
- `recoger()` accepts a bare list or the wrapped `{"pieza", "elementos"}` form.
- Response keys that stop a piece for a human (`sube`, `rotulo_falso`) are
  turned into notes at the single entry point, `servicio._escala`.
- Changing a contract (`*.prompt.md`) makes requests in flight stale; that is
  why deploys refuse while requests are pending.

## `out/`: results

| Path | Contents |
|---|---|
| `out/reels/reel-RN.mp4` | Montage render, with `reel-RN.mp4.huella`: the fingerprint of the spec it drew |
| `out/entrega/reel-RN.mp4` | Delivery file (clean voice, effects, music, levelled) |
| `out/guia/<slug>/` | Guide contact sheets for human approval |
| `out/audio-voz/`, `out/audio-puro/` | Voice and effects stems, exported raw voice |
| `out/revision/` | Review material |

Second numbers differ between `out/reels` (montage time) and `out/entrega`
(delivery time, which can be sped up). When recording feedback, say which one
was watched: `ticket.py … --de montaje` or `--de entrega`.

## `public/`

What Remotion serves: the cut of each piece (`public/<slug>.mp4`) and other
generated media. Backgrounds and textures under `public/fondos/` and
`public/canto-*.png` are configuration; everything else here is product.

## Working disk

All of the above, and every temporary file, belongs on the working disk
declared in `rutas.json`, never on the system disk. Intermediates are not left
on the archive disk: only finished pieces go there.
