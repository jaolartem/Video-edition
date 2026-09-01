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
 * La placa asignada a un beat en `ads/fondos.json`.
 *
 * El fichero se lee una vez: se preguntaba por cada tablero y por cada CTA, o
 * sea que se parseaba treinta veces por corrida para contestar lo mismo.
 */
const PLACAS = JSON.parse(fs.readFileSync("ads/fondos.json", "utf8")).placas;

export const placaDe = (slug, beat) =>
  Object.keys(PLACAS).find((k) =>
    (PLACAS[k].sirve ?? []).includes(`${slug}:${beat}`),
  );

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
export const precioVigente = () => {
  try {
    return JSON.parse(
      execFileSync("python", ["scripts/consulta.py", "precio_vigente", "[]"],
                   { encoding: "utf8" }),
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
