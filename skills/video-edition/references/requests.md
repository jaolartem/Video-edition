# Requests and responses

An LLM step is a function with a signature: a file goes in, a file comes out,
and the next step reads the output. It does not matter who writes the answer;
the file is the contract and the record.

## Files

```
work/servicio/<mailbox>/<slug>.pedido.json      the request
work/servicio/<mailbox>/<slug>.prompt.md        its prompt as readable text
work/servicio/<mailbox>/<slug>.respuesta.json   the answer you write
```

Paths inside a request are relative to `mi-video/`; work from there.

## What a request carries

- `paso` (the mailbox), `slug`, and `prompt`, which points to the
  `.prompt.md` beside it. That prompt is the shared floor (`docs/piso.md`, the
  same for every step) followed by only the contract sections this step reads.
- The common context: today's date, figures with their sources, standing
  batch-wide instructions, current prices, the person's open tickets on the
  piece placed at their stage, what is already decided, the piece's own facts,
  and the state document (`marcador`) with per-segment labels.
- `huecos`, when part of the context could not be built. "Could not look" is
  not "there is nothing": do not decide as if it were.
- `datos`: the step-specific payload. Only the segments that changed since the
  last accepted answer are included.
- Contact sheets (`hoja`): one readable image per scene with the chosen frames,
  plus what is said and how it sounds at each of them. Look at those, not at
  the video.

Field names are Spanish; read them in the request and the contract.

## How to answer

1. Read the contract once per round (`.prompt.md`), and the shared files the
   requests name once.
2. Per request: read it, its contact sheets, and at most a couple of single
   frames of a scene you doubt. Then one write: the response.
3. Use the response shape the contract declares. A bare list, or the wrapped
   form `{"pieza": …, "elementos": [...]}`, are both accepted.
4. To propose a segment label, use the `segmentos` part of the response as the
   contract describes; the line applies it to the base. Do not edit the state
   document.
5. If you need a fact, ask the line: `python scripts/consulta.py <verb> '<json args>'`
   (read-only verbs, declared in `docs/piso.md`). Do not open the database or
   other files, and do not search the tree.
6. If what you have is not enough, say so in that response and move on to the
   next request.

## What the line does with it

- `servicio.recoger()` reads and validates it. An unreadable or invalid response
  is archived as rejected and the request returns to the queue.
- A request is rewritten only when its question changed. A response older than
  its request answered an earlier question and is archived as stale.
- Keys whose declared effect is to stop the piece for the person (for example
  `sube`, `rotulo_falso`) become notes at that single entry point.
- After acceptance, the pair is archived with a number and the step's memory
  records what was asked per segment, so it is not asked again unless that
  segment changes.

## What not to do

- Do not answer a request that is not in the current queue, or rewrite one.
- Do not "improve" segments the request did not include.
- Do not compose the agent instruction yourself: use the block from
  `cola.py --lote` verbatim.
- Do not re-ask something approved. If it is in a ticket, execute it; if it is
  not, it is not yours to reopen.
