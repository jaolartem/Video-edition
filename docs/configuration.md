# Configuration

The machine is generic; what makes it produce *your* ads is the configuration:
the visual identity, the contracts the agents follow, the operator's
instructions and the paths. None of it is in this repository. This page
describes the expected layout and what each file is for, so you can write your
own.

## Where it lives

The configuration is a folder with **its own git repository**, laid out with the
**same relative paths** the files would have in the machine tree
(`docs/canon.md` stays `docs/canon.md`). Its location:

| Context | Location |
|---|---|
| Default | `<main checkout>/<raiz_configuracion>`, where `raiz_configuracion` comes from `separacion.json` (default `configuracion`). It is resolved from the main checkout (the one holding `.git`), so every worktree reads the same configuration. The folder is git-ignored by the machine. |
| Override | Environment variable `VIDEO_CONFIG=<path>` |

Its own `README.md`, `.gitignore` and `.gitattributes` belong to the
configuration repo and are never composed into the tree.

## How it gets in

| Where | How | Command |
|---|---|---|
| Development | Copied into the working tree **read-only**. A copy edited in the tree would be lost on the next copy, so it is protected, and `--comprobar` fails if it differs from the source. Edit in the configuration folder, then copy again. A tree copy newer than the source is not overwritten (reported as a clash). | `python mi-video/scripts/separacion.py --configurar` |
| Production | `desplegar.py` composes the machine commit with the configuration's `HEAD` (which must have no uncommitted changes). If both trees contain the same path, the deploy stops. | `python mi-video/scripts/desplegar.py` |
| Check | Fails if git tracks a configuration or product path, if the configuration has a file the manifest does not declare, if a declared file is missing from the tree or differs, or if `.gitignore` lacks the generated block. Runs on every deploy. | `python mi-video/scripts/separacion.py --comprobar` |
| `.gitignore` block | Regenerated from the manifest between `# >>> separacion.json` and `# <<< separacion.json`. | `python mi-video/scripts/separacion.py --gitignore` |

## The manifest: `separacion.json`

```json
{
  "raiz_configuracion": "configuracion",
  "configuracion": {
    "estilo":        ["<globs>"],
    "contratos":     ["<globs>"],
    "instrucciones": ["<globs>"],
    "rutas":         ["mi-video/rutas.json"]
  },
  "producto": ["<globs>"]
}
```

Anything not matched by `configuracion` or `producto` is machine and goes to git.
Globs support `*` (within a path segment), `**` and `?`. Keys starting with `_`
are comments.

## Style (`estilo`)

How the pieces look. The Remotion components import these modules directly, so
**the project does not compile without them**.

### TypeScript modules in `mi-video/src/brand/`

The machine's own `tokens.ts`, `lienzo.ts`, `gancho.ts`, `franja.ts`, `cc.ts`,
`horario.ts`, `tiempo.ts`, `sfx.ts` and `LienzoContexto.tsx` re-export or
consume these. Each must provide the named exports listed (that is the
interface; the values are yours).

| File | Purpose | Exports the code imports |
|---|---|---|
| `paleta.ts` | Palette and colour modes: what colour each thing is and who is speaking | `color`, `viz`, `mode`, `tone`, `accentChoice`; types `Mode`, `ModeTokens`, `Tone`, `Accent` |
| `tipografia.ts` | Type scale: size, line height, tracking and weight per register | `size`, `lineHeight`, `videoText`, `tracking`, `weight` |
| `fonts.ts` | Loads the font families (e.g. through `@remotion/google-fonts`) | `fontFamily` |
| `medida.ts` | Text measurement: how wide a line is and which size fits a gap | `avance`, `cuerpoQueCabe`, `masLarga`; types `Registro`, `Hueco` |
| `copy.ts` | On-screen text limits per role | `limit`, `assertShort`; type `CopyRole` |

Fonts must cover every glyph of the production languages (for Spanish:
accented vowels, `ñ`, `¿`, `¡`). A missing glyph falls back silently to a system
font.

### JSON files in `mi-video/src/brand/`

Each number lives in one file and is read from there by every side (Python,
Node, React). Keys starting with `_` are explanations and are ignored.

| File | Purpose | Read by |
|---|---|---|
| `lienzos.json` | Canvas per format (`vertical`, `horizontal`): size, crop ratio, protected bands | `src/brand/lienzo.ts`, `scripts/lienzo.mjs`, `dominio/lienzo.py`, `punch-ins.py` |
| `gancho.json` | The hook title: where it sits, how it enters, how long subtitles stay quiet | `src/brand/gancho.ts`, `reels/rotulo.mjs`, `reels/portada.mjs`, `dominio/sujeto.py`, `punch-ins.py` |
| `franja.json` | The subtitle band: floor, height, body size | `src/brand/franja.ts`, `scripts/franja.mjs` |
| `lectura.json` | Reading speed (words per second, minimum frames) used to give text time on screen | `reels/lectura.mjs`, `dominio/documento.py`, `emision.py` |
| `pie.json` | Caption/footnote limits (gap, maximum characters, floor) | `reels/cifras.mjs`, `contrato/diseno.py` |
| `cc.json` | Colour-correction treatments per shot and their thresholds | `src/brand/cc.ts`, `reels/cc.mjs` |
| `figuras.json` | Catalogue of figure types a board can draw | `escena.mjs`, `formas.mjs`, `reels/tableros.mjs` |
| `volumenes.json` | Catalogue of panel animations | `reels/paneles.mjs`, `reels/tableros.mjs` |
| `apoyo.json` | Library of support/B-roll clips by id | `apoyo.py`, `reels/apoyo.mjs`, `reels/monitor.mjs` |
| `cama.json` | Music bed level, default and per piece | `cama.py`, `remezclar.py`, `calibrar-cama.py` |
| `compas.json` | Per-piece beat alignment and pauses, by scene index | `compas.py`, `reels/reloj.mjs`, `render-hook.mjs` |
| `sfx-picos.json` | Measured peak of each sound effect | written by `sfx.sh`, read by `src/brand/sfx.ts` |

### Other style files

| Path | Purpose |
|---|---|
| `mi-video/public/fondos/**` | Background plates used behind boards |
| `mi-video/public/canto-*.png` | Edge textures used for cut-out shapes |
| `docs/canon.md` | The written visual canon (palette use, typography, boards, safe zones, forbidden ornaments). Agent contracts point to it. |
| `docs/ejemplos/**` | Reference plates: the visual authority the canon describes |
| `skills/<board-skill>/**` | A skill with the canon translated into board code |

## Contracts (`contratos`)

What the agents are asked and how they must answer.

| Path | Purpose |
|---|---|
| `mi-video/scripts/describir.prompt.md` | Composer contract for `describir` (what each stage says and shows; writes the designer brief) |
| `mi-video/scripts/disenar.prompt.md` | Designer contract for `disenar` and `visto` (also read by `servicios/portada.py`) |
| `mi-video/scripts/redundancia.prompt.md` | Composer contract for `redundancia` |
| `mi-video/scripts/revalidar.prompt.md` | Composer contract for `revalidar` |
| `mi-video/scripts/repaso.prompt.md` | Composer contract for `repaso` |
| `mi-video/scripts/fuentes.prompt.md` | Composer contract for `fuentes` (sources of figures) |
| `mi-video/scripts/revisar.prompt.md` | Composer contract for `revisar` |
| `docs/piso.md` | The floor: prepended to **every** prompt by `servicio.pedir()`, so a rule that applies to all steps lives in one place. It also declares the shared toolbox (`scripts/consulta.py`). |
| `.claude/agents/compositor.md`, `.claude/agents/disenador.md` | Agent definitions. Names must match the trades in `dominio/oficio.py → BUZONES`. They need `tools: Read, Write, Bash` (Bash for `consulta.py`). They are invoked as `claude --agent <name>` from `mi-video/`. |
| `docs/playbook.md`, `docs/copy.md`, `docs/montaje.md`, `docs/composicion.md`, `docs/caminos.md`, `docs/libretos*.md`, `docs/tomas.md`, `docs/encargo-biblioteca.md`, `docs/prompts-fondos.md` | Editorial rules the contracts cite: scripts and frames, copy, editing treatments, composition, render paths, takes, prompts for generated backgrounds |
| `skills/<editing-skill>/**` | An editing skill specific to the configuration |

The machine checks contracts against code: `scripts/contrato/` declares, per
step, which prompt passages each requirement depends on
(`Prompt("scripts/<step>.prompt.md", "<literal passage>")`), and
`scripts/contratos.py` reports what is missing or inert. If you rewrite a
contract, keep those passages or update the declarations.

## Instructions (`instrucciones`)

What the operator agent is told, and the project's memory of its mistakes.

| Path | Purpose |
|---|---|
| `CLAUDE.md` | Operator instructions loaded by Claude Code in the project |
| `docs/estado.md` | Current state of work: what is open and how it is split |
| `docs/proceso.md`, `docs/entorno.md`, `docs/rendimiento.md` | Process, environment gotchas, performance measurements |
| `docs/aprendizajes.md` | Numbered lessons learned |
| `docs/correcciones.md` | **The corrections log.** Every entry declares its guard; `guardas.mjs` fails the deploy if a guard is missing or broken (see [development.md](development.md)). This is the one configuration file an agent may write. |
| `docs/redundancia.md`, `docs/revision.md`, `docs/bitacora.md`, `docs/duplicados.txt` | Audits, review notes, logbook |
| `docs/propuestas/**`, `mi-video/docs/propuestas/**` | Proposals |
| `mi-video/src/muestras.ts` | Sample props for Remotion Studio previews |

## Paths (`rutas`): `mi-video/rutas.json`

The only place a path is written. Read by `scripts/rutas.py` and
`scripts/rutas.mjs`. Precedence, strongest first: command-line flag
(`--origen`, `--destino`, `--tmp`), environment (`VIDEO_ORIGEN`,
`VIDEO_DESTINO`, `VIDEO_TMP`), then the file.

| Key | Type | Purpose |
|---|---|---|
| `origen` | path | Where the raw recordings are, on a local disk |
| `destino` | path | Output folder. Rewritten by the deploy to `<root>/datos/out` |
| `temporal` | path | Temporary folder for Remotion, Chrome and ffmpeg. **No spaces**, not on the system disk |
| `trabajo` | path | Work folder (default `work`) |
| `publico` | path | Remotion `public/` folder (default `public`) |
| `limpiar` | path | Where the exported raw voice is left for external cleaning, and picked up from |
| `fuentes` | object | Source folders: `drive` (synced raw material, copied to `origen` by `traer-brutos.sh`), `segmentos` and `finales` (publishing targets), `audio` (where cleaned voice may come back) |
| `tomas` | object | Piece slug → tape id (`YYYYMMDD_HHMMSS`, the camera name). A piece that derives from another (`deriva_de` in `ads/frames.json`) inherits its tape |
| `idiomas` | object | Tape id → language code (`es`, `en`); without an entry, Spanish |
| `monitores` | object | Tape id → `{x, y, w, h, cuadro}`: where a screen appears in that tape's frame |
| `linea` | object | `raiz`: the production root (`<root>`); `compartido`: name → path of heavy tools linked into each deployment (e.g. `whisper.cpp`) |
| `_*`, `herramientas` | — | Notes for humans; not read by code |

The lock (`hooks/no-a-mano.py`) reads `linea.raiz` to know which root to
protect, and `separacion.json → raiz_configuracion` to protect the
configuration folder.
