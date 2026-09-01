/**
 * **Qué se le pregunta al servicio para describir una pieza.**
 *
 * Es la segunda de las cuatro condiciones que el proyecto pone a un paso de IA:
 * *«la entrada la genera código: la etapa, su función en el frame, el párrafo
 * del libreto y lo que de verdad se dijo. Siempre el mismo formato»*. Vivía
 * dentro de `describir.mjs`, mezclada con el bucle del lote y con el guardado —
 * tres cosas de tamaños muy distintos en 380 líneas.
 *
 * Aquí está lo que decide **qué entra en la pregunta**, y sólo eso. Quién la
 * contesta y qué se hace con la respuesta es del paso.
 *
 * ## La unidad de la llamada es la PIEZA, no la etapa
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
 *
 * Y sale mas barato: seis llamadas en vez de cincuenta y cuatro.
 */
import fs from "node:fs";

import { sql } from "./consulta.mjs";

/** El prompt vive en el repositorio y se manda literal. No se improvisa. */
export const PROMPT = fs.readFileSync("scripts/describir.prompt.md", "utf8");

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

export function sinAfinar(slug) {
  const cob = JSON.parse(sql("cc_afinado", [slug]));
  return Object.entries(cob)
    .filter(([, v]) => v < AFINADO_MINIMO)
    .map(([b, v]) => `e${b} ${Math.round(v * 100)}%`);
}

/**
 * Cual es la portada ya esta decidido —es la etapa que abre— y no se renegocia
 * aqui: se le dice, para que la describa como gancho.
 *
 * Sin EDL todavia no hay portada marcada, y no pasa nada: el paso de seleccion
 * la marcara y `trato.py` la impone despues.
 */
function portadaDe(slug) {
  try {
    const edl = JSON.parse(
      fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"),
    );
    const portada = edl.detalle?.find((d) => d.trato === "portada")?.beat;
    return portada ?? null;
  } catch {
    return null;
  }
}

/**
 * La pregunta entera de una pieza: sus etapas en orden, con las cuatro cosas
 * que el prompt necesita de cada una.
 */
export function entradaDe(slug, filas) {
  const portada = portadaDe(slug);
  return [
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
        // **Y la escena que YA se aprobo, si la hay.** Jaime: *«lo que ya se
        // aprobo no se vuelve a discutir: se revisa que este como se dijo»*.
        //
        // El dato viajaba desde `encargo.por_describir` y aqui se tiraba: esta
        // funcion arma la prosa y solo imprimia libreto y montaje. Asi que
        // quien describe escribia **desde cero** cada vuelta aunque la escena
        // estuviera decidida, y dos lecturas del mismo material daban dos
        // escenas distintas sin que hubiera cambiado nada salvo el enfoque.
        //
        // Es la averia de siempre: el dato existe y el consumidor no lo lee.
        ...(f.ya_dicho
          ? [
            "",
            "YA APROBADA — esto no se rehace, se revisa. Se escribio sobre este texto:",
            f.ya_dicho.sobre_texto || "(no consta)",
            "Y dice:",
            JSON.stringify(
              Object.fromEntries(
                Object.entries(f.ya_dicho).filter(([k]) => k !== "sobre_texto"),
              ),
              null,
              1,
            ),
            "Compara ese texto con el de arriba: si lo que cambio no toca lo que",
            "la escena ensena, devuelvela tal cual. Rehaz solo lo que el cambio",
            "invalido.",
          ]
          : []),
        "",
      ].join("\n"),
    ),
  ].join("\n");
}

/**
 * La entrada de una pieza, o un fallo si el CC todavia no esta afinado.
 *
 * La puerta va **antes** de construir nada a proposito: preguntar sobre el
 * barrido barato sale igual de caro que preguntar sobre el bueno, y la
 * respuesta habla de palabras que nadie dijo.
 */
export function pedidoDe(slug, filas) {
  const falta = sinAfinar(slug);
  if (falta.length) {
    throw new Error(
      `el CC no esta afinado (${falta.join(", ")}). El barrido caro va ANTES` +
        ` de componer: node/python scripts/transcribir.py --elegidos ${
          Number(slug.slice(-2))}`,
    );
  }
  return entradaDe(slug, filas);
}
