/**
 * **Lo que hay en el disco**, leido una sola vez y por su nombre.
 *
 * Este modulo no decide nada: abre ficheros y devuelve lo que dicen. Esta
 * separado porque mezclar lectura con decision es lo que hace que nadie sepa de
 * donde sale un dato — y la pregunta que ordena todo el proyecto es **«¿de donde
 * lo lee el que monta?»**.
 */
import fs from "fs";
import { execFileSync } from "child_process";

/**
 * **La marca de humanidad y el reparto de beats**, declarados en
 * `ads/frames.json`.
 *
 * Tasa de la marca: **una o dos por minuto**, y en piezas de 80-90 s eso es UNA.
 * Por eso `senala` es un objeto y no una lista.
 */
export const FRAMES = JSON.parse(fs.readFileSync("ads/frames.json", "utf8"));

export const marcoDe = (slug) => FRAMES.reels[slug];

/**
 * **El id de render de una pieza, y la pieza de un id. Con las dos cifras.**
 *
 * Se sacaban del ULTIMO digito (`slug.slice(-1)`) en cinco sitios: con reel-10
 * el id seria «Reel-R0» y reel-11 chocaria con reel-01 — la huella de una
 * casaria con el render de la otra. Python ya usa `int(slug[-2:])`; esto es la
 * misma regla, escrita una vez.
 */
export const idDe = (slug) => `Reel-R${Number(String(slug).slice(-2))}`;
export const slugDe = (id) =>
  `reel-${String(Number(String(id).replace(/\D+/g, ""))).padStart(2, "0")}`;

export const planDe = (slug) =>
  JSON.parse(fs.readFileSync(`work/scenes/${slug}/plan-full.json`, "utf8"));

export const edlDe = (slug) =>
  JSON.parse(fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"));

/**
 * Subtitulos: salen de `work/subs/todos.json`, que produce `subtitular.py`
 * transcribiendo el reel YA MONTADO.
 *
 * Antes se derivaban del transcript del bruto mapeado a la linea de tiempo, y
 * eso heredaba sus fallos: palabras estiradas que cruzan silencios eliminados y
 * tramos donde al transcript le faltan palabras. En el reel 6 se comia media
 * frase de apertura. Lo montado no tiene ese problema — es lo que se oye.
 */
const SUBS = fs.existsSync("work/subs/todos.json")
  ? JSON.parse(fs.readFileSync("work/subs/todos.json", "utf8"))
  : {};

export const subsDe = (slug) => SUBS[slug] ?? [];

/**
 * **La duracion sale del video cortado, no del EDL.**
 *
 * Eran dos fuentes para el mismo dato y se separaban en cuanto el EDL cambiaba
 * despues de cortar. La composicion pedia entonces frames que no existen, y
 * Remotion **no dice eso**: se queda esperando a que la pagina pinte un frame
 * imposible y aborta con un timeout de 33 s a mitad del render. Costo un lote
 * entero entender que el error no era de rendimiento.
 *
 * El video es la verdad —es lo que se va a ver— y el EDL, la intencion.
 */
export function duracionDelCorte(slug) {
  const mp4 = `public/${slug}.mp4`;
  if (!fs.existsSync(mp4)) {
    throw new Error(`falta ${mp4}: hay que cortar antes de generar el spec`);
  }
  return Number(
    execFileSync("ffprobe", [
      "-v", "error", "-show_entries", "format=duration",
      "-of", "csv=p=0", mp4,
    ]).toString().trim(),
  );
}

/**
 * **La placa de la pieza**, declarada en `ads/fondos.json`.
 *
 * Jaime, 6-9-2026: *«es un FONDO de tablero por reel»*. Esto preguntaba por
 * `pieza:beat` y devolvía una placa distinta según el beat, así que la misma
 * pieza cambiaba de suelo al pasar de un tablero al siguiente: R6 salió con
 * cuatro placas, R2 y R5 con tres. **El que elegía era el mapa, no nadie.**
 *
 * Ahora la asignación es de pieza y la respuesta no depende del beat. Un beat
 * que pida otra cosa se resuelve con la composición encima —masas, figura,
 * encuadre—, no cambiando el suelo.
 *
 * El fichero se lee una vez: se preguntaba por cada tablero y por cada CTA, o
 * sea que se parseaba treinta veces por corrida para contestar lo mismo.
 */
const PIEZAS = JSON.parse(fs.readFileSync("ads/fondos.json", "utf8")).pieza;

export const placaDe = (slug) => PIEZAS?.[slug]?.placa;

/**
 * **El recorte con alfa de una etapa**, si la pasada ya corrió.
 *
 * Lo produce `scripts/dominio/sujeto.py` llamando a `text-behind.py`, y el
 * nombre lo fija esa convención, no quien compone: un tablero que tuviera que
 * escribir la ruta a mano la escribiría mal el día que el corte cambie de
 * nombre. `null` si no está — y entonces quien lo pidió recibe una falta, que es
 * mejor que un `staticFile` de algo que no existe: eso mata el render entero con
 * un 404 en mitad de la pieza y el motivo que se lee habla de una URL.
 */
export const sujetoDe = (slug, beat) => {
  const src = `recorte/${slug}-e${beat}.webm`;
  return fs.existsSync(`public/${src}`) ? src : null;
};

/**
 * **El escalon de precio vigente hoy, preguntado a quien lo sabe.**
 *
 * La escalera vive en la tabla `precio` y el rotulo lo redacta
 * `consulta.precio_vigente` — aqui NO se vuelve a implementar. Dos formas de
 * redactar el mismo rotulo son dos rotulos en cuanto alguien toque una.
 *
 * `null` cuando ya cerro la inscripcion, y entonces **no se imprime precio**:
 * una tarifa cerrada en pantalla es peor que ninguna.
 */
/**
 * **Cuando es el evento, preguntado a quien lo sabe.**
 *
 * Jaime: *«simplifica las fuentes, solo queremos una fuente de verdad»*. El dia
 * estaba escrito a mano en `cta.mjs` y ademas era un hecho de la tabla `precio`
 * —el `hasta` del ultimo escalon, con la nota «cierra con el evento»—. Dos
 * copias del mismo dia, y la escalera se movio dos veces en una tarde.
 *
 * Devuelve `dice` («21 de septiembre», que es lo que la voz dice) y `con_ano`
 * («21 SEP 2026»), para lo que se queda colgado y hay que fechar.
 */
export const evento = () => {
  try {
    return JSON.parse(
      execFileSync("python", ["scripts/consulta.py", "evento", "[]"],
                   { encoding: "utf8" }),
    );
  } catch {
    return null;
  }
};

export const precioVigente = () => {
  try {
    return JSON.parse(
      // **`PYTHONIOENCODING` no es opcional.** Sin el, Python en Windows escribe
      // en la codificacion de la consola —cp1252— y aqui se lee como UTF-8: el
      // «·» del precio salia como «?» EN PANTALLA, en las siete piezas y en la
      // tarjeta de cierre. Se veia en la entrega y no en ninguna prueba, porque
      // todas las corridas a mano llevaban la variable puesta.
      execFileSync("python", ["scripts/consulta.py", "precio_vigente", "[]"],
                   { encoding: "utf8",
                     env: { ...process.env, PYTHONIOENCODING: "utf-8" } }),
    );
  } catch {
    return null;
  }
};

/**
 * **Las tarjetas del paso 2, si el paso 2 corrio.**
 *
 * El copy de las etapas que se quedan sin toma lo escribe la IA con su prompt
 * fijo, dentro de los topes de caracteres, y sale en
 * `work/asignacion/reel-NN.json`. Estaba escrito ahi y **no lo leia nadie**: las
 * tarjetas se declaraban a mano en el spec, asi que una etapa que el paso 2
 * mandaba a tarjeta se quedaba sin nada. Es el mismo eslabon roto de C-43, un
 * tramo mas abajo.
 *
 * **Una etapa declarada `omitir` no lleva tarjeta.** Una tarjeta no trae audio
 * propio: se pinta encima de lo que suena. Con una sola pasa desapercibida, pero
 * con dos o tres seguidas tapan las apariciones de Jaime y el montaje se para
 * —en el reel 3 se comian sus dos ultimas—. Cuando una etapa no tiene toma **y
 * no vale la pena regrabarla**, lo honesto es sacarla de la pieza y decirlo en
 * el frame, no darle una tarjeta que le quita el sitio a otra cosa.
 */
export const delPaso2 = (slug, estructura, beats) => {
  const f = `work/asignacion/${slug}.json`;
  if (!fs.existsSync(f)) return [];
  const d = JSON.parse(fs.readFileSync(f, "utf8"));
  return (d.tarjetas ?? [])
    .filter((t) => !beats[t.etapa_n - 1]?.omitir)
    .map((t) => ({
      beat: t.etapa_n,
      props: {
        framework: estructura,
        beat: [t.etapa_n, beats.length],
        bloques: t.bloques.map((texto) => ({ texto })),
        remate: t.remate,
        pie: t.pie,
      },
    }));
};

/**
 * **El hueco libre encima de su cabeza, y donde cae su cara.**
 *
 * Jaime: *«hay mucho espacio arriba de mi cabeza en esas tomas para poner cc y
 * letreros»*, y al confirmarlo: *«si, aprovechemos el espacio de la toma, que
 * para eso es; ademas es una toma muy bonita»*.
 *
 * Medido en las siete: la coronilla cae en 0,317-0,320 del cuadro y la zona
 * segura de Meta empieza en 0,14, asi que quedan **340-345 px sin usar** —un 18%
 * del cuadro— encima de el, dentro de zona legal. Debajo, en cambio, la banda de
 * subtitulos se toca con su menton.
 *
 * **Y sale de MEDIRLO, no de predecirlo.** La primera version lo derivaba del
 * ancla de `punch-ins.py`, que localiza al sujeto por el centroide del
 * movimiento. En el sofa tambien se mueven la cortina y la lampara, asi que el
 * ancla sube: declaraba 0,317-0,320 en las SIETE —o sea, devolvia la constante
 * `HEAD_POS`— cuando lo medido va de 0,149 a 0,447.
 *
 *     declaraba   0,317  0,320  0,320  0,320  0,320  0,318  0,320
 *     medido      0,235  0,168  0,227  0,433  0,149  0,447  0,240
 *
 * Se veia sin mirar el render: una medida de verdad varia entre piezas grabadas
 * en sesiones distintas, y aquella no variaba. Ahora lo mide `sujeto.py` sobre
 * el corte ya hecho —con MediaPipe, que sabe distinguir una persona de una
 * cortina— y lo deja en `work/scenes/<slug>/cara.json`.
 */
export const caraDe = (slug) => {
  const f = `work/scenes/${slug}/cara.json`;
  if (!fs.existsSync(f)) return null;
  const m = JSON.parse(fs.readFileSync(f, "utf8"));
  return {coronilla: m.coronilla, pies: m.pies, visto: m.visto};
};

/**
 * **El hueco que deja su cuerpo a cada lado, escena por escena.**
 *
 * Lo mide `scripts/dominio/hueco.py` en la banda de altura donde vive el volumen
 * de un panel, y hay que preguntárselo **por instante**: en un primerísimo no
 * queda un píxel libre y en un plano medio queda medio cuadro.
 *
 * Es la otra mitad de `caraDe`: aquélla dice a qué altura está él y ésta a qué
 * lado, y las dos existen por el mismo motivo. El lado salía de una sola cuenta
 * sobre el recorte de la PRIMERA escena, y con la cámara fija eso es una
 * constante disfrazada de medida — daba `der` en seis piezas de siete e `izq` en
 * reel-01, que es donde él está.
 *
 * Devuelve `null` si no está medido. Quien lo lea decide qué hacer con eso, que
 * es lo contrario de rellenarlo con un valor plausible.
 */
export const huecosDe = (slug) => {
  const f = `work/scenes/${slug}/huecos.json`;
  if (!fs.existsSync(f)) return null;
  return JSON.parse(fs.readFileSync(f, "utf8")).tramos ?? null;
};

/**
 * **Qué hay detrás del subtítulo, escena por escena.**
 *
 * Lo mide `scripts/dominio/trasfondo.py` en las tres bandas donde el cc puede
 * estar —la barbilla, el hueco de encima de su cabeza y la franja del gancho— y
 * con eso `reels/cc.mjs` decide si esa escena lleva caja, va limpia o va en
 * negativo. Jaime: *«hay varios que quedarían bien sin el cuadro, otras a las
 * que le queda bien y otras a las que le quedaría mejor negativo»*.
 *
 * Devuelve `null` si no está medido, igual que `huecosDe`: sin medida el cc sale
 * con el tratamiento por defecto —la caja— y eso se ve en el reparto, en vez de
 * apostar por el más bonito sobre un fondo que nadie ha visto.
 */
export const trasfondoDe = (slug) => {
  const f = `work/scenes/${slug}/trasfondo.json`;
  if (!fs.existsSync(f)) return null;
  return JSON.parse(fs.readFileSync(f, "utf8")).tramos ?? null;
};
