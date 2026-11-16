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
 * Eso ya no es un apaño: es **el contrato del servicio** (`servicio.mjs`), y la
 * sesión contesta por el mismo sitio que el CLI y pasa por la misma validación.
 * Quien conteste cambia; lo que se exige, no.
 *
 * El CLI devolvió `OAuth access token has been revoked`. Se arregla con
 * `claude setup-token` — que **imprime el token una sola vez**, así que si se ve
 * en pantalla hay que rotarlo — y ojo con `ANTHROPIC_BASE_URL` puesta y
 * **vacía**, que rompe la autenticación por sí sola.
 *
 * ## Las cuatro condiciones que el proyecto pone a un paso de IA
 *
 * Las mismas del paso 2, porque es la misma clase de decisión —*«lo que es por
 * IA debe tener un mecanismo para que siempre lo hagas exactamente igual»*—, y
 * **cada una vive donde se cumple**, que es lo que hace que no se puedan
 * incumplir por separado:
 *
 * 1. **El prompt vive en el repositorio** (`describir.prompt.md`) y se manda
 *    literal. No se improvisa por sesión. → `describir-pedido.mjs`
 * 2. **La entrada la genera código**: la etapa, su función en el frame, el
 *    párrafo del libreto y lo que de verdad se dijo. → `describir-pedido.mjs`
 * 3. **La salida es un esquema fijo**, validado al recibirla. Lo que no encaja
 *    se rechaza; no se arregla a mano. → `describir-esquema.mjs`
 * 4. **Se guarda.** Decidido una vez, se reutiliza: `escena_desc` es la memoria
 *    de esta decisión y no se vuelve a pedir salvo con `--rehacer`. → aquí.
 *
 * Y una quinta que sale de la experiencia de este proyecto: **si no se puede
 * describir, se dice y no se rellena con un valor por defecto.** Un `dejar`
 * puesto por si acaso es indistinguible de un `dejar` decidido, y eso convierte
 * la descripción en un adorno.
 *
 * Este fichero es **el paso**: recorre el lote, pregunta por cada pieza, mira si
 * la respuesta cubre lo pedido y la guarda.
 *
 *   node scripts/describir.mjs            # las etapas sin describir
 *   node scripts/describir.mjs 3          # solo ese reel
 *   node scripts/describir.mjs --rehacer  # vuelve a pedir todo
 */
import { sql } from "./consulta.mjs";
import { exigencias, valida } from "./describir-esquema.mjs";
import { PROMPT, pedidoDe } from "./describir-pedido.mjs";
import {
  apartaRespuesta, archivaUsado, dejaPedido, guardaRespuesta, leeRespuesta,
  rutaPedido,
} from "./servicio.mjs";
import { criterio as criterioDeFranja } from "./franja.mjs";
import fs from "node:fs";
import { execFileSync } from "node:child_process";

/** El paso al que pertenecen el pedido y la respuesta, dentro del contrato. */
const PASO = "describir";

/**
 * Describe **la pieza entera de una vez**, no etapa a etapa. `null` si nadie ha
 * contestado todavía — que es una espera, no un fallo.
 */
function describePieza(slug, filas) {
  // **Si ya hay respuesta, no se vuelve a construir la pregunta.** Esto estaba
  // al final: para recoger una respuesta ya escrita se pagaba antes el pedido
  // entero —`escucha.py`, cinco fotogramas por etapa de la cinta 4K, el montaje
  // en fotogramas—, o sea minutos y decenas de subprocesos para un fichero que
  // ya estaba en disco. Recoger pasa a costar cero.
  const hecha = leeRespuesta(PASO, slug,
    JSON.parse(sql("tiquets_de", [slug, "descrito"]) || "[]").map((t) => t.id));
  if (hecha) return hecha.map(valida).map((d) => ({ ...d, quien: "servicio" }));
  // `quien` tiene que decir QUIEN contesto. Puso «gemini» cuando esa via ni
  // existia, y decir «cli» de lo que contesto la sesion es el mismo error con
  // otro nombre: el campo esta para poder auditar de donde salio una decision.
  // **La franja va en el encargo, no en la cabeza de quien compone.**
  //
  // Instruccion de Jaime (T-02): *«ningun tablero baja hasta esa franja»*. Una
  // regla que el que compone no ve en su pedido no existe para el — elige de la
  // carta que le damos, igual que le paso con la cortinilla retirada. Y el
  // numero sale de `franja.mjs`, que lo lee de `franja.json`: escribirlo aqui
  // seria la segunda copia, que es como `Comparacion` y `Acumulacion` acabaron
  // dibujando bajo la interfaz de la plataforma.
  // **La revisión del compositor va en su pedido, y es la SUYA, no la del que
  // dibuja.** Jaime: *«tanto el diseñador como el compositor tienen procesos
  // simplificados de revisión; por ejemplo el compositor tiene que escuchar los
  // bordes de las escenas para asegurarse de que no hay escenas cortadas a la
  // mitad, tiene que estar seguro de que los subtítulos dicen lo que el vídeo
  // dice, y de que lo que se dice es coherente con la intención»*.
  //
  // El diseñador mira cinco fotogramas por escena; esto es otra cosa: recortes
  // de audio en cada empalme y el libreto al lado del texto que sobrevivió al
  // corte. Por texto esos tramos parecían limpios — el defecto que él oyó en
  // reel-03, frases que se comen la primera palabra, **sólo se oye**.
  let escucha = null;
  try {
    escucha = JSON.parse(
      execFileSync("python", ["scripts/escucha.py", String(Number(slug.slice(-2)))],
                   { encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" } })
      && fs.readFileSync(`work/escucha/${slug}/revision.json`, "utf8"),
    );
  } catch { escucha = null; }
  // **Y los cinco fotogramas de cada toma, sacados de la cinta.**
  //
  // Jaime, tras rechazar la deteccion por texto: *«no, esos ojos no sirven, ya
  // han fallado. Que tome cinco fotogramas repartidos por toda la escena y mire
  // la foto»*. Salen de la CINTA porque cuando el que compone elige, el montaje
  // todavia no existe — y sin esto el bloque que los pide en el prompt seria
  // otra cosa declarada y no implementada, que es la averia de la casa.
  // **En una hoja, y con sus candidatas** (C-584, C-586). Jaime, 19-10-2026: los
  // agentes trabajan con un documento, no con el video. Y las candidatas son el
  // primer peldaño de su escalera: las buscaba a mano, 44 llamadas en reel-19.
  // Solo de lo que puede tocar: lo aprobado va de contexto.
  const editables = JSON.parse(sql("acotado", [slug, "descrito"]) || "null");
  const suya = (f) => !editables || editables.includes(Number(f.orden));
  const conFotos = filas.map((f) => {
    const c = suya(f) ? { candidatas: JSON.parse(sql("candidatas", [slug, f.orden]) || "[]") } : {};
    const d = (f.toma && f.start != null && f.end != null) ? f : null;
    if (!d) return { ...f, ...c };
    try {
      const j = JSON.parse(execFileSync("python", ["-c",
        "import sys,json;sys.path.insert(0,'scripts');import fotogramas as F;"
        + "f=F.de_la_escena(sys.argv[1],int(sys.argv[2]));print(json.dumps({'f':f,"
        + "'h':F.Hoja.de_la_cinta(sys.argv[1],int(sys.argv[2]),f).escribe()}))",
        slug, String(f.orden)],
        { encoding: "utf8", env: { ...process.env, PYTHONIOENCODING: "utf-8" } }));
      return { ...f, ...c, fotogramas: j.f, hoja: j.h };
    } catch { return { ...f, ...c }; }
  });
  // **Y el DESPUES: como quedo esa escena ya montada.** Jaime, 7-9-2026: *«el
  // compositor puede ver dos tipos de fotogramas, los del video base y las 3 o
  // 5 que genera por escena, en un antes y un despues»*.
  //
  // Los de la cinta dicen que se grabo; estos dicen que salio. Con uno solo se
  // juzga a ciegas la mitad del trabajo: si esta leyendo se ve en el bruto,
  // pero si el corte se comio la frase o el tablero le tapa la cara solo se ve
  // en el montaje. Si la pieza aun no esta montada, no hay despues y se calla.
  let despues = [];
  try {
    despues = JSON.parse(sql("montada_en_fotogramas", [slug]) || "[]");
  } catch { despues = []; }
  // **Y el despues, en el documento de revision** (C-594): sus hojas y, por
  // fotograma, lo que se dice, lo que hay en pantalla y lo que suena. Jaime,
  // 19-10-2026: las imagenes son el corazon del documento.
  let montada = {};
  try {
    montada = despues.length ? JSON.parse(execFileSync("python", ["-c",
      "import sys,json;sys.path.insert(0,'scripts');from dominio.documento import Documento as D;"
      + "print(json.dumps(D(sys.argv[1],json.load(sys.stdin),None,'montada').escribe(),ensure_ascii=False))",
      slug], { encoding: "utf8", input: JSON.stringify(despues),
               env: { ...process.env, PYTHONIOENCODING: "utf-8" } }).trim().split(String.fromCharCode(10)).pop()) : {};
  } catch { montada = {}; }
  // **`pedidoDe` devuelve UN TEXTO, no un objeto.** Esto lo esparcia con `...`,
  // y esparcir una cadena en un objeto la parte caracter a caracter: el pedido
  // de reel-03 salia con 3.420 claves —`"0": "R", "1": "e", "2": "e"…`— que son
  // casi todo su peso. No falla: se escribe, se valida y se manda, y quien
  // contesta tiene que reconstruir el texto letra a letra antes de empezar.
  // **Y las palabras de Jaime viajan DENTRO.** `acotado` dice que etapa mirar;
  // esto dice por que. Sin las dos el pedido llega recortado y mudo, y quien
  // contesta reconstruye el contexto por su cuenta antes de empezar.
  const tiquets = JSON.parse(sql("tiquets_de", [slug, "descrito"]) || "[]");
  // **Ve la pieza entera; toca sólo lo suyo.** Jaime, 7-9-2026: *«cada tiquet va
  // ligado a la escena y el compositor sólo ve esa escena»*, y en cuanto lo dijo
  // lo precisó: *«sí, pero que puedan ver el resto, aunque no editar»*. Las dos
  // mitades hacen falta y por motivos distintos: la coherencia no cabe en una
  // escena suelta —dos familias que se alternan, el oro que deja de señalar si
  // está en todo—, y a la vez lo aprobado no se vuelve a componer.
  //
  // `null` = la pieza entera es editable, que es el modo normal, el de componer
  // de cero. Una lista = sólo ésas; las demás van de contexto.
  // **Y el porqué del último rechazo viaja en el pedido siguiente** (C-707). El
  // esquema tumbó dos veces la misma respuesta de reel-23 —quitaba `beat` de una
  // Tarjeta— y el motivo sólo salía por la consola: quien volvía a contestar no
  // lo veía y repetía el mismo fallo, 80.000 tokens por vuelta.
  const rechazo = fs.existsSync(RECHAZO(slug)) ? fs.readFileSync(RECHAZO(slug), "utf8") : null;
  const entrada = { pedido: pedidoDe(slug, conFotos), franja: criterioDeFranja(),
                    revisa_oyendo: escucha, tiquets, editables,
                    ...(rechazo ? { ultimo_rechazo: rechazo } : {}),
                    // **Lo que la linea ya midio, delante de quien decide.**
                    // Jaime, 10-9-2026: «nada de lo que sucede de 1 a 6 llega
                    // como decision; el compositor ve todos estos datos y puede
                    // utilizar esas herramientas para estar seguro. El compositor
                    // es quien toma la decision». Un corte que se come una palabra
                    // se sabe en cuanto la pieza esta cosida, y se quedaba esperando
                    // a la fase 10 — o sea a despues de pagarle a el y al
                    // disenador. C-359.
                    la_linea_midio: JSON.parse(sql("lo_medido", [slug]) || "[]"),
                    ya_montada: montada };
  // **El contrato tiene dos capas y esta es la segunda.** Las capacidades no
  // cambian —son lo que sabe hacer—; lo que cambia es el encargo. El otro
  // oficio la pone con `abierto.modo` (`servicios/disenar.py`); aqui llega por
  // `consulta.py :: modo`, que es la unica puerta de node a la base.
  //
  // Sin ella los tiquets viajaban como dato y ninguna frase decia que el
  // encargo fuera ese: el 7-9-2026 el compositor recibio el t282 —una etapa— y
  // devolvio las ocho compuestas. El texto vive en `dominio/abierto.py :: MODO`.
  const instruccion = JSON.parse(sql("modo", [slug, "descrito"]) || '""');
  // **Y lo que el esquema rechaza va escrito en el contrato**, derivado de él:
  // ver `describir-esquema.mjs :: exigencias`. Sin esto el que contesta se
  // entera del requisito por el rechazo, y cada requisito cuesta una vuelta
  // entera del servicio — `componente: null` tumbó dos respuestas en dos días.
  const contrato = PROMPT + exigencias() + instruccion;
  const encargo = instruccion ? { ...entrada, modo: "tiquets" } : entrada;
  // El pedido se deja SIEMPRE antes de preguntar: si el CLI no contesta, lo que
  // queda escrito es la pregunta entera —prompt incluido— y cualquiera puede
  // contestarla despues sin reconstruir nada.
  // **El paso deja la pregunta escrita y se para. No la contesta él.**
  //
  // Aqui llamaba a `porCli`, que es `claude -p` generico: sin `--agent`, sin el
  // contrato del compositor y sin la capa de tiquets. Desde la terminal de
  // Jaime eso autentica y contesta, asi que el paso se daba por hecho — pero la
  // respuesta no venia del oficio y no declaraba `tiquets: [...]`, que es lo
  // unico que cierra un tiquet. La pieza pasaba, el tiquet seguia abierto y
  // `vencidas` la devolvia: tres vueltas la noche del 7 al 8 de septiembre.
  //
  // Contestar es del oficio, y llamarle es del disparador (`dominio/disparo.py`,
  // `dominio/oficio.py`). Con dos llamadores habia dos puertas para la misma
  // pregunta; ahora hay una.
  dejaPedido(PASO, slug, contrato, encargo);
  const arr = null;
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
  guardaRespuesta(PASO, slug, arr);
  return arr.map(valida).map((d) => ({ ...d, quien: "cli" }));
}

/** Lo que hay que describir, agrupado por pieza: la unidad de la llamada. */
function porPiezas(filas) {
  const m = new Map();
  for (const f of filas) {
    if (!m.has(f.slug)) m.set(f.slug, []);
    m.get(f.slug).push(f);
  }
  return m;
}

const rehacer = process.argv.includes("--rehacer");
// **Una pieza es un número, no un dígito.** Con `/^\d$/` el «12» no casaba, la
// lista salía vacía y el paso de reel-12 describía TODAS las piezas: esperaba
// los pedidos de las demás y reel-10 a reel-17 no pasaban de «repasado» (C-423).
const reels = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
const filas = JSON.parse(sql("escenas_por_describir", [reels, rehacer]));
if (!filas.length) {
  console.log("nada que describir (usa --rehacer para volver a pedirlo)");
  process.exit(0);
}
console.log(`${filas.length} escenas a describir`);

let ok = 0;
const esperan = [];
//: Las piezas cuya respuesta llego y el esquema tumbo. **No es lo mismo que una
//: espera y tampoco es un exito**: hay una respuesta escrita que no se puede
//: aplicar, y hasta que se rehaga la pieza no ha pasado este paso.
const rechazadas = [];
//: Las que no tienen el JSON entero: su pedido no sale (C-714).
const paradas = [];
/** Donde queda el porqué del último rechazo de una pieza, hasta que una respuesta entra (C-707). */
const RECHAZO = (slug) => `work/servicio/${PASO}/${slug}.rechazo.txt`;
/**
 * Y el pedido que ya está en pie lo lleva también: `dejaPedido` sólo corre al
 * abrirlo, así que sin esto el motivo esperaba a un pedido nuevo que no llegaba.
 */
const anotaRechazo = (slug) => {
  const rp = rutaPedido(PASO, slug);
  if (!fs.existsSync(RECHAZO(slug)) || !fs.existsSync(rp)) return;
  const motivo = fs.readFileSync(RECHAZO(slug), "utf8");
  const p = JSON.parse(fs.readFileSync(rp, "utf8"));
  if (p?.datos && p.datos.ultimo_rechazo !== motivo) {
    p.datos = { ...p.datos, ultimo_rechazo: motivo };
    fs.writeFileSync(rp, JSON.stringify(p, null, 1));
  }
};
//: Las que no pueden componerse todavia y saben desde donde se arregla. **Ni
//: espera ni rechazo**: no hay pedido escrito, asi que no hay a quien esperar.
const vuelven = [];
for (const [slug, suyas] of porPiezas(filas)) {
  const tocables = JSON.parse(sql("acotado", [slug, "descrito"]) || "null");
  try {
    const ds = describePieza(slug, suyas);
    if (!ds) {
      anotaRechazo(slug); // el pedido en pie lleva el porqué del último rechazo (C-707)
      esperan.push(slug);
      continue;
    }
    const porOrden = new Map(ds.map((d) => [Number(d.etapa_orden), d]));
    // Los `tramos` que decide quien compone se aplican como los de revalidar.
    const tramos = {};
    for (const f of suyas) {
      const d = porOrden.get(Number(f.orden));
      if (!d) {
        console.error(`  ${slug} e${f.orden}: no vino en la respuesta`);
        continue;
      }
      // **Y lo que no era suyo no se guarda.** Ver `editables`: una respuesta
      // que reescribe una etapa aprobada no es un error del que compone —tiene
      // la pieza entera delante a proposito— pero tampoco entra.
      if (tocables && !tocables.includes(Number(f.orden))) {
        // **Sube, no se aplica.** Jaime: *«ver y proponer cambios, no
        // generarlos»*. Tirarlo seria desperdiciar el unico par de ojos que
        // estaba mirando esa etapa; aplicarlo seria recomponer lo aprobado.
        sql("proponer", [slug, f.orden, "compositor",
                         JSON.stringify(d).slice(0, 900)]);
        console.log(`  ${slug} e${f.orden}: fuera de su encargo — SUBE como`
          + ` propuesta, no se aplica`);
        continue;
      }
      sql("guardar_escena", [slug, f.orden, d]);
      if (Array.isArray(d.tramos) && d.tramos.length) tramos[f.orden] = d.tramos;
      // **Y `cortar` saca la etapa, no sólo se apunta** (C-649). reel-22, 21-10:
      // Jaime pidió quitar «Soy Jaime Olarte» (#936), el compositor contestó
      // `remedio: cortar` y el tiquet se cerró con e10 sonando en el render.
      // Una obligatoria no sale por aquí: sube a Jaime como propuesta.
      if (d.remedio === "cortar") {
        const no = JSON.parse(sql("quitar_etapa",
          [slug, f.orden, d.por_que || "el compositor la corta"]) || "null");
        if (no) sql("proponer", [slug, f.orden, "compositor", `cortar: ${no}`]);
        console.log(`  ${slug} e${f.orden}: ${no ? `no sale — ${no}` : "sale de la pieza"}`);
      }
      ok++;
      console.log(
        `  ${slug} e${f.orden} ${String(f.etapa).slice(0, 20).padEnd(20)} ` +
          `${String(d.trato).padEnd(11)} ${String(d.plano).padEnd(9)} ` +
          `${(d.grafico || "").slice(0, 40)}`,
      );
    }
    // **Y lo que contestó sin que se le pidiera tampoco se tira** (C-640):
    // sube como propuesta, igual que lo de fuera de su encargo. reel-18, 20-10:
    // el compositor alargó e6 y e7 por un tiquet de Jaime de la pieza entera,
    // el pedido sólo traía e1 y e3, y las dos desaparecieron sin una línea.
    const pedidas = new Set(suyas.map((f) => Number(f.orden)));
    for (const d of ds.filter((x) => !pedidas.has(Number(x.etapa_orden)))) {
      sql("proponer", [slug, d.etapa_orden, "compositor", JSON.stringify(d).slice(0, 900)]);
      console.log(`  ${slug} e${d.etapa_orden}: no se pidió — SUBE como propuesta, no se aplica`);
    }
    if (Object.keys(tramos).length) sql("declarar_tramos", [slug, tramos]);
    // **Y los tiquets que la respuesta dice haber atendido se cierran aqui.**
    //
    // No los cerraba nadie. El otro oficio si —`servicios/disenar.py` llama a
    // `abierto.cerrar` con los numeros declarados—, y este paso guardaba la
    // descripcion y dejaba la correccion abierta: la pieza avanzaba, `vencidas`
    // la veia abierta con su paso ya detras y la devolvia. Tres vueltas la
    // noche del 7 al 8 de septiembre, sin que nadie se equivocara.
    //
    // La regla de que numeros se cierran vive en `abierto.cerrar` —solo los
    // declarados, y ahi esta el porque— y aqui solo se le pasa lo que la
    // respuesta declaro.
    const declarados = ds.flatMap((d) => d.tiquets || []);
    if (declarados.length) {
      const cerrados = JSON.parse(sql("cerrar_tiquets",
        [slug, "descrito", `descrito: ${ok} etapa(s) guardadas`, declarados])
        || "[]");
      if (cerrados.length) console.log(`  ${slug}: cerrados ${cerrados.join(", ")}`);
    }
    // **Y archivar va DENTRO, donde se sabe que se consumio.** Estaba en un
    // bucle de despues que archivaba toda pieza que no estuviera esperando, asi
    // que una excepcion a mitad de aplicar se llevaba el pedido Y la respuesta
    // a `usadas/`: el error se veia una vez y la prueba desaparecia.
    archivaUsado(PASO, slug);
    if (fs.existsSync(RECHAZO(slug))) fs.rmSync(RECHAZO(slug));
  } catch (e) {
    // **Sin el JSON entero no hay pedido, y no es una espera** (C-714): no hay
    // a quién esperar. Para la pieza con el motivo, sin llamar a ningún oficio.
    if (e.noSale) {
      console.error(`  ${slug}: ${String(e.message).slice(0, 300)}`);
      paradas.push(`${slug}: ${String(e.message).slice(0, 200)}`);
      continue;
    }
    if (e.volverA) {
      console.error(`  ${slug}: ${String(e.message).slice(0, 200)}`);
      vuelven.push({ slug, fase: e.volverA, por: String(e.message).slice(0, 120) });
      continue;
    }
    // Un fallo de credencial ya no llega aqui: `porCli` lo devuelve como
    // espera. Lo que llegue es un fallo de verdad —esquema, JSON roto— y ese
    // se dice por pieza sin parar el lote.
    console.error(`  ${slug}: ${String(e.message).slice(0, 160)}`);
    // El motivo, donde el pedido siguiente lo lee (C-707).
    fs.writeFileSync(RECHAZO(slug),
      `La respuesta anterior se rechazó por esto y se vuelve a pedir: ${String(e.message).slice(0, 400)}`);
    anotaRechazo(slug);
    // **Y la respuesta que no vale se aparta, para que se pueda volver a
    // preguntar.** Dejandola en su sitio el pedido deja de contar como abierto:
    // nadie espera a nadie, el disparador no llama y el paso rechaza el mismo
    // fichero en cada vuelta. Apartada, la pregunta vuelve a estar viva y el
    // oficio la contesta otra vez — ahora con las listas del esquema delante.
    const fuera = apartaRespuesta(PASO, slug);
    if (fuera) console.error(`  ${slug}: apartada en ${fuera}`);
    rechazadas.push(`${slug}: ${String(e.message).slice(0, 120)}`);
    esperan.push(slug);
  }
}

console.log(`${ok}/${filas.length} descritas y guardadas`);
// **La ultima linea dice adonde volver** y `servicios/base.py` la lee: es la
// misma via que `Resultado.volver_a`, para un paso que es un script (C-548).
if (vuelven.length) {
  console.log(`volver_a: ${vuelven[0].fase} — ${
    vuelven.map((v) => `${v.slug}: ${v.por}`).join(" | ")}`);
  process.exit(1);
}
if (paradas.length) {
  console.log(`no sale el pedido: ${paradas.join(" | ")}`);
  process.exit(1);
}
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
  //
  // **Y va por stdout.** `servicios/base.py` lo dice de si mismo: manda stdout,
  // y stderr solo si el paso no dijo nada. Por stderr, el motivo que quedaba
  // era «0/1 descritas y guardadas» — que no contiene la palabra «espera», asi
  // que `avanzar` no lo leia como espera y no le pedia al disparador que
  // llamara al oficio. La linea que pide el turno tiene que ir por el canal en
  // el que el motor escucha.
  // Y si alguna espera porque su respuesta se tumbo, el motivo lo dice: no es
  // lo mismo «nadie ha contestado» que «contesto y no valia».
  const por = rechazadas.length ? ` (rechazadas: ${rechazadas.join(" | ")})` : "";
  console.log(
    `espera respuesta del servicio${por} -> ${
      esperan.map((s) => rutaPedido(PASO, s)).join(" ")}`);
  process.exit(1);
}
