/**
 * **El contrato del servicio, del lado de node.** El gemelo de `servicio.py`.
 *
 *     work/servicio/<paso>/<slug>.pedido.json      lo que el paso pregunta
 *     work/servicio/<paso>/<slug>.respuesta.json   lo que contesta el servicio
 *
 * Antes esto vivía dentro de `describir.mjs`, que llamaba al CLI y, sin
 * credencial, moría. Lo que pasaba entonces: la descripción se hacía «en
 * sesión» y se cargaba a mano. Eso no es un paso manual, es **el paso saltado**
 * — 54 escenas cargadas en 37 segundos, ninguna anclada al montaje, y la puerta
 * comprobando un texto que ninguna línea de código mantenía.
 *
 * Con el contrato, la sesión contesta **por el mismo sitio que el CLI** y pasa
 * por la misma validación. Quien conteste cambia; lo que se exige, no.
 *
 * ## Por qué está aquí y no dentro del paso
 *
 * Porque no es de `describir`: es del **contrato**, y el contrato es uno para
 * los cuatro pasos de IA (`scripts/contratos.py`). Escrito dentro del paso, el
 * segundo paso de node que lo necesitara habría hecho su copia — que es la
 * avería más cara de este proyecto: no falla, diverge.
 *
 * Las rutas y los nombres son los mismos que en `servicio.py` a propósito. Dos
 * lenguajes, un solo sitio donde está escrito qué fichero se lee.
 */
import { execFileSync } from "node:child_process";
import fs from "node:fs";

/** La raíz del contrato. Misma cadena que `servicio.RAIZ` en Python. */
export const RAIZ = "work/servicio";

export const rutaPedido = (paso, slug) =>
  `${RAIZ}/${paso}/${slug}.pedido.json`;
export const rutaRespuesta = (paso, slug) =>
  `${RAIZ}/${paso}/${slug}.respuesta.json`;

/**
 * Deja escrita la pregunta entera —prompt incluido— antes de preguntar.
 *
 * Va **siempre** antes de la llamada: si el CLI no contesta, lo que queda en
 * disco es la pregunta completa y cualquiera puede contestarla después sin
 * reconstruir nada.
 */
export function dejaPedido(paso, slug, prompt, datos) {
  fs.mkdirSync(`${RAIZ}/${paso}`, { recursive: true });
  fs.writeFileSync(
    rutaPedido(paso, slug),
    JSON.stringify({ paso, slug, prompt, datos }, null, 1),
  );
}

/** Lo que el servicio dejó contestado, o `null` si todavía no hay nada. */
export function leeRespuesta(paso, slug) {
  const r = rutaRespuesta(paso, slug);
  if (!fs.existsSync(r)) return null;
  const arr = JSON.parse(fs.readFileSync(r, "utf8"));
  if (!Array.isArray(arr)) throw new Error("la respuesta no es un array");
  return arr;
}

/** Guarda la respuesta como la respuesta del paso. Ver `describir.mjs`. */
export function guardaRespuesta(paso, slug, arr) {
  fs.mkdirSync(`${RAIZ}/${paso}`, { recursive: true });
  fs.writeFileSync(rutaRespuesta(paso, slug), JSON.stringify(arr, null, 1));
}

/**
 * El CLI, si tiene credencial aqui. `null` si no la tiene: **eso no es un
 * fallo, es una espera**, y el motor distingue las dos cosas. Un fallo del
 * prompt si sube, porque ese hay que arreglarlo.
 *
 * El CLI usa **la credencial de la terminal que lo lanza**: lanzado desde la
 * terminal de Jaime funciona; lanzado desde un shell abierto dentro de una
 * sesión de Claude Code dice `Not logged in`. Ver la cabecera de
 * `describir.mjs`, que es donde está la instrucción de qué hacer entonces.
 */
export function porCli(prompt, entrada) {
  let salida;
  try {
    salida = execFileSync(
      "claude",
      ["-p", `${prompt}\n\n---\n\n${entrada}\nResponde SOLO el array JSON.`,
       "--output-format", "json"],
      { encoding: "utf8", maxBuffer: 16 * 1024 * 1024,
        stdio: ["ignore", "pipe", "pipe"] },
    );
  } catch {
    return null;                       // ni siquiera arranco: no hay CLI aqui
  }
  const d = JSON.parse(salida);
  const txt = String(d.result ?? "");
  if (d.is_error) {
    if (/revoked|authenticat|401|not logged in|please run \/login/i.test(txt)) {
      return null;
    }
    throw new Error(txt.slice(0, 200));
  }
  const m = txt.match(/\[[\s\S]*\]/);
  if (!m) throw new Error("el CLI no devolvio un array JSON");
  const arr = JSON.parse(m[0]);
  if (!Array.isArray(arr)) throw new Error("la respuesta no es un array");
  return arr;
}
