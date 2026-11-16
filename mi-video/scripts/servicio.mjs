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
  // **Sin el JSON entero no sale el pedido** (C-714). La regla de qué cuenta
  // como hueco vive en `dominio/estado.py :: escribe`; aquí se obedece, igual
  // que en `servicio.py :: pedir`. El compositor de reel-23 recibió a las 23:32
  // el JSON de las 20:36, dieciocho cortes sin un elemento decidido.
  const ctx = contexto(paso, slug);
  const falta = ctx.marcador ? ctx.marcador.falta : "no se pudo publicar";
  if (falta) {
    // Y el pedido viejo, si nadie lo contestó, se retira: es el hueco, y en pie
    // un agente lo contestaría igual.
    if (fs.existsSync(rutaPedido(paso, slug)) && !fs.existsSync(rutaRespuesta(paso, slug))) {
      archivaUsado(paso, slug);
    }
    throw Object.assign(
      new Error(`el JSON de ${slug} no está entero y el pedido no sale: ${falta}`),
      { noSale: true });
  }
  fs.mkdirSync(`${RAIZ}/${paso}`, { recursive: true });
  // El prompt también en su fichero, por renglones: en el JSON es una línea
  // de 46.000 caracteres y se leía cortado (C-445).
  fs.writeFileSync(`${RAIZ}/${paso}/${slug}.prompt.md`, String(prompt ?? ""));
  fs.writeFileSync(
    rutaPedido(paso, slug),
    // El contrato va por referencia, como en `servicio.py` (C-550, C-563):
    // dentro del JSON se leia dos veces.
    JSON.stringify({ paso, slug, prompt: `en ${slug}.prompt.md, junto a este pedido`,
                     ...ctx, datos }, null, 1),
  );
}

/**
 * **Lo que viaja con todo pedido sale de un solo sitio: `servicio.contexto`.**
 *
 * Aquí sólo se metía el marcador, así que el pedido de `describir` llegaba sin
 * lo ya decidido, sin el precio vigente y sin las instrucciones de Jaime —
 * lo que `servicio.py` sí manda a los demás pasos. Copiar la lista aquí sería
 * la segunda versión que diverge; se le pregunta a la primera. C-395.
 */
function contexto(paso, slug) {
  try {
    // **La ultima linea, no toda la salida** (C-563): un `registro.aviso`
    // imprime antes por stdout, el JSON no parseaba y el catch dejaba el pedido
    // de describir sin instrucciones, tiquets ni precio desde el 16-10.
    return JSON.parse(execFileSync("python", ["-c",
      "import sys,json;sys.path.insert(0,'scripts');import servicio;"
      + "print(json.dumps(servicio.contexto(sys.argv[1],sys.argv[2]),ensure_ascii=False))",
      paso, slug], { encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" },
      maxBuffer: 64 * 1024 * 1024 }).trim().split("\n").pop());
  } catch (e) {
    // **Y si no se pudo armar, no se rellena con el fichero tal cual** (C-714):
    // ese fichero es el de la última vez que la pieza cambió de fase, y un
    // pedido con él sale con cara de entero. Se dice, y `dejaPedido` para.
    return { marcador: { falta: `no se pudo armar el contexto: ${String(e.message).slice(0, 160)}` } };
  }
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
export function leeRespuesta(paso, slug, abiertos = []) {
  const r = rutaRespuesta(paso, slug);
  if (!fs.existsSync(r)) return null;
  const hecha = desenvuelve(JSON.parse(fs.readFileSync(r, "utf8")));
  // **Y la que no nombra los tiquets abiertos de su paso contesta a otra
  // pregunta** (C-487). reel-12, 13-9: el #457 la mandó a «descrito» y aquí
  // esperaba la respuesta del 12-9, anterior al tiquet. Se aplicó, la pieza
  // siguió y el tiquet quedó varado. Se aparta y se vuelve a preguntar.
  // Los ids viajan como `457` en la respuesta y como `t457` en el pedido (los
  // de la tabla `ticket`), así que se comparan por su número.
  const num = (t) => String(typeof t === "object" ? t?.id : t).replace(/\D/g, "");
  const cubre = new Set(hecha.flatMap((d) => d?.tiquets ?? []).map(num));
  if (abiertos.some((i) => !cubre.has(num(i)))) {
    apartaRespuesta(paso, slug, "desfasada");
    return null;
  }
  return hecha;
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
export function apartaRespuesta(paso, slug, marca = "rechazada") {
  const dir = `${RAIZ}/${paso}/usadas`;
  const r = rutaRespuesta(paso, slug);
  if (!fs.existsSync(r)) return null;
  fs.mkdirSync(dir, { recursive: true });
  let n = 1;
  while (fs.existsSync(`${dir}/${slug}.${n}.${marca}.json`)) n += 1;
  const destino = `${dir}/${slug}.${n}.${marca}.json`;
  fs.renameSync(r, destino);
  return destino;
}

/** Guarda la respuesta como la respuesta del paso. Ver `describir.mjs`. */
export function guardaRespuesta(paso, slug, arr) {
  fs.mkdirSync(`${RAIZ}/${paso}`, { recursive: true });
  fs.writeFileSync(rutaRespuesta(paso, slug), JSON.stringify(arr, null, 1));
}
// **`porCli` se fue, y con ella la unica puerta que se saltaba el
// interruptor.** Lanzaba `claude -p` generico —sin `--agent`, sin el contrato
// del compositor y sin la capa de tiquets— y **no miraba `POR_BASH`**, que es
// la decision de Jaime del 11-9 despues de quedarse sin tokens: *«los pasos de
// los agentes no los mandemos por bash, sino por agentes»*. El lado Python si
// lo respeta (`servicio.py :: pedir`), asi que los dos protocolos decidian
// distinto sobre lo mismo y el que no lo respetaba era el que podia gastar.
//
// No la llamaba nadie: `describir.mjs` dejo de usarla cuando el paso paso a
// dejar la pregunta escrita y pararse. Eran 37 lineas que solo podian hacer
// dano.

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
