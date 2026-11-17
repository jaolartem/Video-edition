# The cycle of phases

Declared in `mi-video/scripts/dominio/fase.py → CICLO`, migrated into the `fase`
table, read back by `camino()`. A label names a step **already done**; the
service is what moves the piece to the next label.

| Order | Label | Moved by | Who answers |
|---|---|---|---|
| 1 | `catalogado` | `transcribir.py --barato` | code |
| 2 | `elegido` | `seleccionar.py {n} --edl` | code |
| 2.5 | `fijado` | `fijar.py --aplicar {n}` | code |
| 3 | `afinado` | `transcribir.py --elegidos {n}` | code |
| 4 | `depurado` | `depurar.py {n}` | code |
| 5 | `sin_redundancia` | `redundancia.py {n}` | mailbox `redundancia` → `compositor` |
| 5.2 | `recortado` | `revision.py --aplicar {n}` | code |
| 5.5 | `revalidado` | service | mailbox `revalidar` → `compositor` |
| 6 | `cosido` | `costuras.py {n}` | code |
| 6.5 | `repasado` | service | mailbox `repaso` → `compositor` |
| 7 | `descrito` | `describir.mjs {n}` | mailbox `describir` → `compositor` |
| 7.5 | `disenado` | service | mailbox `disenar` → `disenador` |
| 8 | `cortado` | `cortar.py {n}` | code |
| 10 | `verificado` | `verificar.py {n}` | code |
| 11 | `montado` | `montar.sh {n}` | code; first the guide sheet, mailbox `guia` → the person |
| 11.2 | `nivelado` | `sonoridad.sh {n}` | code |
| 11.4 | `medido` | `suena.py {n} --guardar` | code |
| 11.6 | `visto` | service | mailbox `visto` → `disenador` |
| 12 | `revisado` | service | mailbox `revisar` → `compositor` |
| 13 | `aprobado` | `aprobar.py` | **the person only** |
| 13.5 | `voz_entregada` | `voz-limpia.py --exportar {n}` | code |
| 14 | `voz_limpia` | `voz-limpia.py {n}` | code (the cleaned voice comes back) |
| 15 | `masterizado` | `musica.sh {n}` | code |
| 15.5 | `respaldado` | service | mailbox `fuentes` → `compositor` |
| 16 | `publicado` | `publicar.py --finales {n}` | code |

## What each mailbox is for

| Mailbox | Trade | Question it answers |
|---|---|---|
| `redundancia` | compositor | What is said twice, inside a window, across a seam, or the same datum in two stages. Redundancy is **cut**, annotated with its anchor and reason |
| `revalidar` | compositor | On the trimmed cut: delivery and rhythm of each stage |
| `repaso` | compositor | Last pass on the stitched cut: repetitions that came back, consistency of figures, names and dates |
| `describir` | compositor | What each stage must say and show, seen against the whole argument; it also writes the designer's brief |
| `disenar` | disenador | Builds what the composer defined: form, copy and graphic family of each board, checked on frames |
| `visto` | disenador | Looks at what was actually rendered before the person does |
| `revisar` | compositor | Review notes |
| `fuentes` | compositor | Where each figure in the text comes from |
| `guia` | the person | Approves the per-second guide sheet before the full render |

## Stops

`avanzar.py` stops a piece for one of three reasons, and they are different:

1. **End of the path.**
2. **Waiting for someone**: a request without an answer, or a phase only the
   person moves (`aprobado`, the guide sheet).
3. **A service could not run**: the reason is the step's last stdout line,
   recorded in `video_fase.por_que`. Only this one is a failure.

A repeated identical wait is counted, and warned at 6, 12, 24, 48 and 96
rounds. A piece at `montado` or later whose render no longer matches its cut is
moved back to `verificado` by the engine itself (not by you); a piece signed off
by the person is not.
