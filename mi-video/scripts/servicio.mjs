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
    JSON.stringify({ paso, slug, prompt, marcador: marcador(slug), datos }, null, 1),
  );
}

/**
 * El marcador de la pieza, o `null` si todavía no hay.
 *
 * **Y por qué estaba en un solo lado.** Los pedidos se arman en dos sitios —
 * `servicio.py` para los pasos de Python y esto para `descrito`—, y sólo el
 * primero metía el marcador. Así que el compositor recibía `modo` y
 * `editables` y no el marcador, y el diseñador el marcador y no los tiquets:
 * cada oficio con media hoja, y ninguno de los dos con el documento entero.
 *
 * Jaime, 10-9-2026: *«los contratos y el disparador, todo basado en el Json»*.
 * Un solo documento, y los dos lo leen.
 */
export function marcador(slug) {
  try {
    return JSON.parse(fs.readFileSync(`ads/${slug}/estado.json`, "utf8"));
  } catch {
    return null;
  }
}

/** Lo que el servicio dejó contestado, o `null` si todavía no hay nada. */
export function leeRespuesta(paso, slug) {
  const r = rutaRespuesta(paso, slug);
  if (!fs.existsSync(r)) return null;
  return desenvuelve(JSON.parse(fs.readFileSync(r, "utf8")));
}

/**
 * **La respuesta es un array; si viene envuelta, se desenvuelve.**
 *
 * El 7-9-2026 dos de las tres respuestas del dia volvieron rechazadas por
 * «la respuesta no es un array», y las dos traian el trabajo entero: `{tiquets,
 * etapas}` en vez de la lista pelada. El rechazo era correcto y era inutil —
 * paraba por la forma del envoltorio, no por lo que decia dentro, y costaba una
 * vuelta completa del servicio cada vez.
 *
 * La forma del transporte no es una decision: se acepta y se sigue. Lo que si
 * se conserva es `tiquets`, que es lo unico del envoltorio que significa algo —
 * dice que correcciones se atienden— y sin el se cerraria ninguna.
 */
export function desenvuelve(d) {
  if (Array.isArray(d)) return d;
  const arr = d && (d.etapas || d.escenas || d.respuesta);
  if (!Array.isArray(arr)) throw new Error("la respuesta no es un array");
  const suyos = d.tiquets;
  if (Array.isArray(suyos) && suyos.length && arr.length
      && !arr.some((x) => x && x.tiquets)) {
    arr[0] = { ...arr[0], tiquets: suyos };
  }
  return arr;
}

/**
 * **Aparta una respuesta que el esquema tumbó, y deja el pedido abierto.**
 *
 * Una respuesta invalida no es una respuesta, pero mientras siga en su sitio lo
 * parece: `servicio.pendientes` deja de nombrar el pedido, asi que la pieza no
 * espera a nadie, el disparador no llama y el paso vuelve a rechazar el mismo
 * fichero en cada vuelta. Es un atasco silencioso — reel-03 y reel-05 lo
 * estuvieron dos dias.
 *
 * Se aparta con su marca para poder mirarla, y el pedido se queda: la pregunta
 * sigue siendo buena, lo que falló fue la contestación.
 */
export function apartaRespuesta(paso, slug) {
  const dir = `${RAIZ}/${paso}/usadas`;
  const r = rutaRespuesta(paso, slug);
  if (!fs.existsSync(r)) return null;
  fs.mkdirSync(dir, { recursive: true });
  let n = 1;
  while (fs.existsSync(`${dir}/${slug}.${n}.rechazada.json`)) n += 1;
  const destino = `${dir}/${slug}.${n}.rechazada.json`;
  fs.renameSync(r, destino);
  return destino;
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


/**
 * **Archiva el par pedido/respuesta cuando la respuesta ya se aplico.**
 *
 * `servicio.pedir` (Python) archiva en cuanto consume; este lado no lo hacia, y
 * el efecto tardo semanas en verse: las siete respuestas de `describir` seguian
 * en su carpeta desde las 15:05, ya aplicadas, y **parecian sin contestar para
 * siempre**. En cuanto el despachador aprendio a devolver una pieza al paso que
 * espera su respuesta, eso habria mandado las siete de vuelta a describir — el
 * reproceso completo, disparado por ficheros que sobraban.
 *
 * Una respuesta aplicada que se queda en la carpeta no es inofensiva: es una
 * peticion abierta que miente. Se numera para no pisar el archivo anterior, que
 * es lo que deja seguir la historia de una pieza vuelta a vuelta.
 */
export function archivaUsado(paso, slug) {
  const dir = `${RAIZ}/${paso}/usadas`;
  fs.mkdirSync(dir, { recursive: true });
  let n = 1;
  // **El hueco lo decide el PAR, no la respuesta.** Numerando solo por la
  // respuesta, un pedido archivado sin ella no ocupaba numero: el siguiente
  // archivado escribia encima y se perdia la pregunta anterior. Paso con los
  // pedidos que se archivaron sin contestar la noche del 7 de septiembre.
  while (fs.existsSync(`${dir}/${slug}.${n}.respuesta.json`)
         || fs.existsSync(`${dir}/${slug}.${n}.pedido.json`)) n += 1;
  for (const [cual, ruta] of [["pedido", rutaPedido(paso, slug)],
                              ["respuesta", rutaRespuesta(paso, slug)]]) {
    if (fs.existsSync(ruta)) {
      fs.renameSync(ruta, `${dir}/${slug}.${n}.${cual}.json`);
    }
  }
}
