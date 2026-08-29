/**
 * Describe cada escena, desde el pipeline y siempre igual.
 *
 * Jaime: *«acá el punto no es puntuar, el punto es tener una descripción de la
 * escena»*, y *«si lo puedes dejar en código mejor, como por ejemplo ejecutando
 * Claude Code desde el bash»*.
 *
 * **Sólo Claude, y ninguna API de terceros.** Hubo una versión que caía a la
 * API de Google si el CLI fallaba; Jaime la descartó —*«no quiero a Google»*—
 * y además esa clave devolvía `PERMISSION_DENIED`, así que el respaldo era
 * teórico. Un segundo motor que no se puede probar no es un respaldo: es código
 * que nadie sabe si funciona.
 *
 * ## Desde qué terminal se lanza, que no es un detalle
 *
 * El CLI usa **la credencial de la terminal que lo lanza**. Lanzado desde la
 * terminal de Jaime funciona; lanzado desde un shell abierto dentro de una
 * sesión de Claude Code dice `Not logged in`, y da igual cómo lo llame el
 * script: se probó como argumento, por stdin, desprendido con `start /b` y
 * limpiando las variables `CLAUDE_*`. No hay fichero de credencial en
 * `~/.claude/` que el hijo pueda leer.
 *
 * Así que la regla es corta: **`bash scripts/pipeline.sh` desde su terminal** y
 * este paso corre solo. Si lo conduce la sesión, aplica lo de abajo.
 *
 * ## Si este paso falla, se hace en sesión y se carga por migración
 *
 * Instrucción de Jaime, y es la que evita que el montaje se quede parado por
 * una credencial: *«ahora mismo déjalo para los siguientes, y deja la
 * instrucción: si ese paso falla, lo hacemos por acá y llenamos la base por
 * migración»*. Y el porqué de que se pueda: *«tú eres muy superior, y no tengo
 * que hacer llamadas a API»*.
 *
 * O sea: el asistente describe las escenas leyendo los libretos, y se cargan con
 *
 *     python scripts/consulta.py guardar_escena '["reel-03", 2, {...}]'
 *
 * La tabla es la misma y el resto del montaje no se entera de quién la escribió;
 * sólo la columna `quien` dice si fue el CLI o la sesión.
 *
 * El CLI devolvió `OAuth access token has been revoked`. Se arregla con
 * `claude setup-token` — que **imprime el token una sola vez**, así que si se ve
 * en pantalla hay que rotarlo — y ojo con `ANTHROPIC_BASE_URL` puesta y
 * **vacía**, que rompe la autenticación por sí sola.
 *
 * ## Las cuatro condiciones que el proyecto pone a un paso de IA
 *
 * Las mismas del paso 2, porque es la misma clase de decisión —*«lo que es por
 * IA debe tener un mecanismo para que siempre lo hagas exactamente igual»*—:
 *
 * 1. **El prompt vive en el repositorio** (`describir.prompt.md`) y se manda
 *    literal. No se improvisa por sesión.
 * 2. **La entrada la genera código**: la etapa, su función en el frame, el
 *    párrafo del libreto y lo que de verdad se dijo. Siempre el mismo formato.
 * 3. **La salida es un esquema fijo**, validado aquí al recibirla. Lo que no
 *    encaja se rechaza; no se arregla a mano.
 * 4. **Se guarda.** Decidido una vez, se reutiliza: `escena_desc` es la memoria
 *    de esta decisión y no se vuelve a pedir salvo con `--rehacer`.
 *
 * Y una quinta que sale de la experiencia de este proyecto: **si no se puede
 * describir, se dice y no se rellena con un valor por defecto.** Un `dejar`
 * puesto por si acaso es indistinguible de un `dejar` decidido, y eso convierte
 * la descripción en un adorno.
 *
 *   node scripts/describir.mjs            # las etapas sin describir
 *   node scripts/describir.mjs 3          # solo ese reel
 *   node scripts/describir.mjs --rehacer  # vuelve a pedir todo
 */
import { execFileSync } from "child_process";
import fs from "fs";

const PROMPT = fs.readFileSync("scripts/describir.prompt.md", "utf8");

/** Las claves que la descripción tiene que traer, y sus valores admitidos. */
const CAMPOS = {
  etapa_orden: null,
  que_pasa: null,
  trato: ["portada", "tablero", "cercano", "metafora", "diapositiva"],
  trato_porque: null,
  prioridad: ["entrega", "limpieza"],
  integridad: null,
  remedio: ["recuperar", "tablero", "cortar", "ninguno"],
  emocion: null,
  componente: ["CausalChain", "TwoPaths", "BeliefSwap", "ThenNow",
               "EvidenceCard", "ComparisonTable", "ninguno"],
  grafico: null,
  color: ["avivar", "apagar", "dejar"],
  sonido: null,
  plano: ["en cuadro", "cerrado", "fuera"],
};

const sql = (q, args = []) =>
  execFileSync("python", ["scripts/consulta.py", q, JSON.stringify(args)], {
    encoding: "utf8", maxBuffer: 32 * 1024 * 1024,
  });

/** El esquema se comprueba aquí: lo que no encaja se rechaza. */
function valida(d) {
  for (const [k, admitidos] of Object.entries(CAMPOS)) {
    if (!(k in d)) throw new Error(`falta «${k}»`);
    if (admitidos && !admitidos.includes(d[k])) {
      throw new Error(`«${k}» = ${JSON.stringify(d[k])} no es de la lista`);
    }
  }
  return d;
}

/**
 * Describe **la pieza entera de una vez**, no etapa a etapa.
 *
 * Jaime, corrigiendo la version anterior: *«el tablero no exige una lectura
 * plana, la tolera, la permite; es alternativa cuando no hay una opcion mejor.
 * La decision se da en funcion de dos variables, complejidad y necesidad del
 * video, y por eso la debe tomar un LLM, porque el contexto es el video en
 * general; la idea es que el LLM construya un video coherente con lo que hay»*.
 *
 * La segunda variable —lo que la pieza necesita— **no existe a nivel de etapa**.
 * Preguntando de una en una, el modelo no puede saber que ya hay dos tableros
 * cerca ni que lleva seis planos hablados seguidos, asi que no puede alternar.
 * Por eso la unidad de esta llamada es la pieza.
 *
 * Y sale mas barato: seis llamadas en vez de cincuenta y cuatro.
 */
function describePieza(slug, filas) {
  // Cual es la portada ya esta decidido —es la etapa que abre— y no se
  // renegocia aqui: se le dice, para que la describa como gancho.
  let portada = null;
  try {
    const edl = JSON.parse(
      fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"),
    );
    portada = edl.detalle?.find((d) => d.trato === "portada")?.beat ?? null;
  } catch {
    // Sin EDL todavia no hay portada marcada, y no pasa nada: el paso de
    // seleccion la marcara y `trato.py` la impone despues.
  }

  const entrada = [
    `Reel: ${slug} — ${filas.length} etapas, en orden.`,
    portada === null ? "" : `La etapa ${portada} es la PORTADA (el gancho).`,
    "",
    ...filas.map((f) =>
      [
        `## Etapa ${f.orden} de «${f.estructura}»: ${f.etapa}`,
        `Funcion: ${f.mensaje ?? "(no declarada)"}`,
        "Libreto:",
        f.libreto,
        "Lo que de verdad se dijo:",
        f.dicho || "(esta etapa no tiene toma: va con tablero o tarjeta)",
        "",
      ].join("\n"),
    ),
  ].join("\n");

  const salida = execFileSync(
    "claude",
    ["-p", `${PROMPT}\n\n---\n\n${entrada}\nResponde SOLO el array JSON.`,
     "--output-format", "json"],
    { encoding: "utf8", maxBuffer: 16 * 1024 * 1024,
      stdio: ["ignore", "pipe", "pipe"] },
  );
  const d = JSON.parse(salida);
  if (d.is_error) throw new Error(String(d.result).slice(0, 200));
  const m = String(d.result).match(/\[[\s\S]*\]/);
  if (!m) throw new Error("el CLI no devolvio un array JSON");
  const arr = JSON.parse(m[0]);
  if (!Array.isArray(arr)) throw new Error("la respuesta no es un array");
  return arr.map(valida);
}

const rehacer = process.argv.includes("--rehacer");
const reels = process.argv.slice(2).filter((x) => /^\d$/.test(x));
const filas = JSON.parse(sql("escenas_por_describir", [reels, rehacer]));
if (!filas.length) {
  console.log("nada que describir (usa --rehacer para volver a pedirlo)");
  process.exit(0);
}
console.log(`${filas.length} escenas a describir`);

let ok = 0;
let sinAuth = null;
// Agrupadas por pieza: la unidad de la llamada es el video, no la etapa.
const porPieza = new Map();
for (const f of filas) {
  if (!porPieza.has(f.slug)) porPieza.set(f.slug, []);
  porPieza.get(f.slug).push(f);
}
for (const [slug, suyas] of porPieza) {
  try {
    const ds = describePieza(slug, suyas);
    const porOrden = new Map(ds.map((d) => [Number(d.etapa_orden), d]));
    for (const f of suyas) {
      const d = porOrden.get(Number(f.orden));
      if (!d) {
        console.error(`  ${slug} e${f.orden}: no vino en la respuesta`);
        continue;
      }
      sql("guardar_escena", [slug, f.orden, d]);
      ok++;
      console.log(
        `  ${slug} e${f.orden} ${String(f.etapa).slice(0, 20).padEnd(20)} ` +
          `${String(d.trato).padEnd(11)} ${String(d.plano).padEnd(9)} ` +
          `${(d.grafico || "").slice(0, 40)}`,
      );
    }
  } catch (e) {
    const msg = String(e.message);
    // Insistir contra una credencial revocada no la arregla.
    // «Not logged in» sale con exit 0 y como texto dentro del JSON, asi que
    // llegaba aqui disfrazado de «Command failed» y no se reconocia. Un fallo
    // de credencial tiene que decir que es de credencial: si no, se confunde
    // con un fallo del prompt y se pierde media hora buscando donde no es.
    if (/revoked|authenticat|401|not logged in|please run \/login/i.test(msg)) {
      sinAuth = msg.slice(0, 120);
      break;
    }
    console.error(`  ${slug}: ${msg.slice(0, 160)}`);
  }
}

if (sinAuth) {
  console.error(
    `\nEl CLI no está autenticado: ${sinAuth}\n` +
      "  claude setup-token   token de larga duración para scripts\n" +
      "  /login               dentro de una sesión interactiva\n" +
      "Y revisa ANTHROPIC_BASE_URL: puesta y vacía rompe la auth.\n" +
      "Mientras tanto, la descripción se hace en sesión y se carga con\n" +
      "  python scripts/consulta.py guardar_escena '[\"reel-0N\", M, {...}]'",
  );
  process.exit(1);
}
console.log(`${ok}/${filas.length} descritas y guardadas`);
