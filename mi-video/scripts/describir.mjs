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

/**
 * **El contrato del servicio, el mismo que usan redundancia y revalidar.**
 *
 *     work/servicio/describir/<slug>.pedido.json      lo que el paso pregunta
 *     work/servicio/describir/<slug>.respuesta.json   lo que contesta el servicio
 *
 * Antes este paso llamaba al CLI y, sin credencial, moria. Lo que pasaba
 * entonces esta escrito arriba: la descripcion se hacia «en sesion» y se
 * cargaba a mano. Eso no es un paso manual, es **el paso saltado** — 54 escenas
 * cargadas en 37 segundos, ninguna anclada al montaje, y la puerta comprobando
 * un texto que ninguna linea de codigo mantenia.
 *
 * Con el contrato, la sesion contesta **por el mismo sitio que el CLI** y pasa
 * por la misma validacion. Quien conteste cambia; lo que se exige, no.
 */
const DIR = "work/servicio/describir";
const rutaPedido = (slug) => `${DIR}/${slug}.pedido.json`;
const rutaRespuesta = (slug) => `${DIR}/${slug}.respuesta.json`;

function dejaPedido(slug, entrada) {
  fs.mkdirSync(DIR, { recursive: true });
  fs.writeFileSync(
    rutaPedido(slug),
    JSON.stringify({ paso: "describir", slug, prompt: PROMPT, datos: entrada },
                   null, 1),
  );
}

function leeRespuesta(slug) {
  if (!fs.existsSync(rutaRespuesta(slug))) return null;
  const arr = JSON.parse(fs.readFileSync(rutaRespuesta(slug), "utf8"));
  if (!Array.isArray(arr)) throw new Error("la respuesta no es un array");
  return arr;
}

/**
 * El CLI, si tiene credencial aqui. `null` si no la tiene: **eso no es un
 * fallo, es una espera**, y el motor distingue las dos cosas. Un fallo del
 * prompt si sube, porque ese hay que arreglarlo.
 */
function porCli(entrada) {
  let salida;
  try {
    salida = execFileSync(
      "claude",
      ["-p", `${PROMPT}\n\n---\n\n${entrada}\nResponde SOLO el array JSON.`,
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
const KIND_DE = {
  TwoPaths: "comparacion",
  ComparisonTable: "comparacion",
  CausalChain: "causal",
  BeliefSwap: "comparacion",
  ThenNow: "comparacion",
  EvidenceCard: "acumulacion",
};

function valida(d) {
  for (const [k, admitidos] of Object.entries(CAMPOS)) {
    if (!(k in d)) throw new Error(`falta «${k}»`);
    if (admitidos && !admitidos.includes(d[k])) {
      throw new Error(`«${k}» = ${JSON.stringify(d[k])} no es de la lista`);
    }
  }
  /**
   * **Un componente sin `tablero` es una etapa que no va a cambiar nunca.**
   *
   * El contenido del tablero vivía en un literal por pieza y la descripción no
   * lo tocaba: cuatro entregas idénticas, y Jaime contándolas una a una. Ahora
   * el campo existe (`escena_desc.tablero`) y lo lee el render — pero si este
   * paso no lo escribe, la etapa se queda con lo que hubiera, que es
   * exactamente el mismo agujero por dentro.
   *
   * Así que se exige donde tiene sentido exigirlo: si la etapa declara un
   * componente, tiene que traer su contenido.
   */
  if (d.componente && d.componente !== "ninguno") {
    const t = d.tablero;
    if (!t || typeof t !== "object" || !t.props) {
      throw new Error(
        `«tablero» falta y la etapa declara componente «${d.componente}»:` +
        ` sin él, el tablero se queda con lo que ya hubiera y la descripción` +
        ` no llega a la pantalla`);
    }
    if (!t.kind) t.kind = KIND_DE[d.componente] ?? "comparacion";
  }
  /**
   * **Y la composición TIPOGRÁFICA es un tablero, aunque no lleve componente.**
   *
   * El gancho de reel-04 pide tipo —su `grafico` dice «una sola palabra, y es
   * la que se oye: INMIGRANTE en Anton versales»— y `componente` es `ninguno`,
   * así que la exigencia de arriba no le tocaba y la etapa salía sin copy. El
   * render entonces rellenaba el bloque con `lineas[0]`, la primera línea del
   * rótulo, y el segundo gancho visual **repetía el primero** encima de él, en
   * el único segundo que compite contra el pulgar.
   *
   * No se arregla deduciendo la palabra de la prosa: eso sería código decidiendo
   * el copy. Se arregla exigiéndolo aquí, que es donde el diseño entrega.
   */
  const ES_TIPO = /versales|el tipo es|la frase entera|solo texto|nada mas/i;
  if (ES_TIPO.test(d.grafico ?? "")) {
    const t = d.tablero;
    const txt = t?.props?.texto ?? t?.props?.titulo ?? t?.texto;
    if (typeof txt !== "string" || !txt.trim()) {
      throw new Error(
        `«tablero» falta y el gráfico de esta etapa es tipográfico: di qué dice` +
        ` en \`tablero.props.texto\`. Si no, el render no tiene copy y la capa` +
        ` no entra — o peor, repite el rótulo`);
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
/**
 * **El barrido caro es la ENTRADA de este paso, no un acabado posterior.**
 *
 * Jaime: *«la idea del barrido caro es que el agente de IA tenga el CC correcto,
 * y pueda tomar decisiones sobre el, eliminar redundancia y componer las
 * escenas»*.
 *
 * Sin esa comprobacion, este paso compone sobre el texto del barrido barato
 * —que sirve para localizar donde se dice algo y no para saber que se dijo— y
 * decide con palabras que nadie pronuncio. Medido: cuatro de las seis piezas
 * llegaron a montarse con el 0% del montaje afinado.
 *
 * No se avisa: se para. Un aviso en un lote de 16-50 se ignora.
 */
const AFINADO_MINIMO = 0.95;

function sinAfinar(slug) {
  const cob = JSON.parse(sql("cc_afinado", [slug]));
  return Object.entries(cob)
    .filter(([, v]) => v < AFINADO_MINIMO)
    .map(([b, v]) => `e${b} ${Math.round(v * 100)}%`);
}

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
        // **Lo que dice el montaje, no lo que se eligio.** Son cosas
        // distintas en cuanto un recorte posterior toca la etapa, y describir
        // una mientras la puerta verifica la otra es como se llego a tener
        // seis piezas descritas contra un texto que ya no existia.
        "Lo que de verdad se dijo:",
        f.montaje || f.dicho ||
          "(esta etapa no tiene toma: va con tablero o tarjeta)",
        "",
      ].join("\n"),
    ),
  ].join("\n");

  // `quien` tiene que decir QUIEN contesto. Puso «gemini» cuando esa via ni
  // existia, y decir «cli» de lo que contesto la sesion es el mismo error con
  // otro nombre: el campo esta para poder auditar de donde salio una decision.
  const falta = sinAfinar(slug);
  if (falta.length) {
    throw new Error(
      `el CC no esta afinado (${falta.join(", ")}). El barrido caro va ANTES` +
        ` de componer: node/python scripts/transcribir.py --elegidos ${
          Number(slug.slice(-2))}`,
    );
  }
  const ya = leeRespuesta(slug);
  if (ya) return ya.map(valida).map((d) => ({ ...d, quien: "servicio" }));
  // El pedido se deja SIEMPRE antes de preguntar: si el CLI no contesta, lo que
  // queda escrito es la pregunta entera —prompt incluido— y cualquiera puede
  // contestarla despues sin reconstruir nada.
  dejaPedido(slug, entrada);
  const arr = porCli(entrada);
  if (!arr) return null;
  /**
   * **Una respuesta a medias no se guarda como la respuesta.**
   *
   * Esto la escribia en `<slug>.respuesta.json` sin mirar si cubria lo pedido,
   * y a partir de ahi `leeRespuesta` la devolvia en CADA vuelta: el paso
   * repetia el mismo hueco para siempre. reel-01 contesto 1 de 4 dos veces
   * seguidas y reel-06 dio cuatro vueltas con la etapa 7 — el mismo motivo
   * cada vez, que es justo lo que `avanzar` detecta como bucle y no podia
   * arreglar, porque el arreglo estaba aqui.
   *
   * Regla de Jaime: *«si sale error, paras, reparas el pipeline, no un parche;
   * el problema resuelto y vuelves a correr»*. La reparacion es no cachear una
   * respuesta incompleta: el pedido ya esta escrito -`dejaPedido` va antes de
   * preguntar- asi que dejandolo abierto cualquiera puede contestarlo, que es
   * la via que ya existe para cuando el CLI no puede.
   */
  const pedidas = new Set(filas.map((f) => Number(f.orden)));
  const traidas = new Set(arr.map((d) => Number(d.etapa_orden)));
  const faltan = [...pedidas].filter((o) => !traidas.has(o));
  if (faltan.length) {
    console.error(
      `  ${slug}: el CLI contesto ${traidas.size}/${pedidas.size} —` +
        ` faltan las etapas [${faltan.join(", ")}]. La respuesta parcial NO se` +
        ` guarda: el pedido queda abierto.`,
    );
    return null;
  }
  fs.writeFileSync(rutaRespuesta(slug), JSON.stringify(arr, null, 1));
  return arr.map(valida).map((d) => ({ ...d, quien: "cli" }));
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
const esperan = [];
// Agrupadas por pieza: la unidad de la llamada es el video, no la etapa.
const porPieza = new Map();
for (const f of filas) {
  if (!porPieza.has(f.slug)) porPieza.set(f.slug, []);
  porPieza.get(f.slug).push(f);
}
for (const [slug, suyas] of porPieza) {
  try {
    const ds = describePieza(slug, suyas);
    if (!ds) {
      esperan.push(slug);
      continue;
    }
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
    // Un fallo de credencial ya no llega aqui: `porCli` lo devuelve como
    // espera. Lo que llegue es un fallo de verdad —esquema, JSON roto— y ese
    // se dice por pieza sin parar el lote.
    console.error(`  ${slug}: ${String(e.message).slice(0, 160)}`);
  }
}

console.log(`${ok}/${filas.length} descritas y guardadas`);
if (esperan.length) {
  console.error(
    "\nEl CLI no contesta aqui (usa la credencial de la terminal que lo lanza).\n" +
      "  claude setup-token   token de larga duración para scripts\n" +
      "  /login               dentro de una sesión interactiva\n" +
      "Y revisa ANTHROPIC_BASE_URL: puesta y vacía rompe la auth.\n" +
      "Mientras tanto contesta el pedido: mismo esquema, misma validación.",
  );
  // La ULTIMA linea es la que el motor guarda como motivo en `video_fase`, asi
  // que tiene que decir que falta y donde se contesta.
  console.error(
    `espera respuesta del servicio -> ${esperan.map(rutaPedido).join(" ")}`);
  process.exit(1);
}
