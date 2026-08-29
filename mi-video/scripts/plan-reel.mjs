/**
 * Plan de escenas para el REEL ENTERO, no solo el gancho.
 *
 * Toma `segmentos` del EDL —que es la fuente de verdad del montaje— y lo parte
 * en escenas de ~3 s para que `punch-ins.py` les asigne encuadre. Dos reglas:
 *
 * - **Una escena nunca cruza un corte del EDL.** El corte ya cambia de plano;
 *   meter ademas un cambio de encuadre encima seria un salto doble.
 * - **Nada por debajo de `MINIMO`.** Un resto de 0,4 s lee como parpadeo; se
 *   funde con la escena anterior en vez de crear un plano nuevo.
 *
 * **El orden de `segmentos` es el de la línea de tiempo, no el del bruto.** El
 * reel 5 abre en frío con una frase del minuto 682: ordenar por tiempo de origen
 * la manda al medio de la pieza. Aquí se recorre tal cual viene.
 *
 * NO vuelve a montar. `build-reel.mjs` reejecuta `assemble.py` y eso pisaria las
 * correcciones hechas a mano sobre el EDL —la cifra del reel 2, la fecha, las
 * zonas—. Aqui el EDL entra como dato, no como algo a recalcular.
 *
 *   node scripts/plan-reel.mjs --reel 3
 */
import fs from "fs";
import { bruto } from "./rutas.mjs";

/**
 * Silencio interno que se quita. Por debajo de esto es respiración y se queda:
 * quitarla toda deja el habla pegada y suena a locutor de radio.
 */
const AIRE = 0.25;
/** Margen que se deja a cada lado del habla para no comerse la consonante. */
const MARGEN = 0.06;

/**
 * Interseca un tramo del EDL con los tramos de habla medidos.
 *
 * **Esto faltaba y es el aprendizaje 3 del proyecto**, que estaba escrito y se
 * perdió al reescribir el montaje por beats: *«los tiempos del EDL están en la
 * línea del bruto, así que un enunciado que cruza aire muerto lo reintroduce al
 * renderizar»*. Costaba 6–13 s de silencio por reel, y es la mitad de por qué
 * el montaje se sentía «poco dinámico».
 *
 * Ahora importa más que antes: los candidatos son **intentos enteros de una sola
 * toma** —Jaime: *«puedes borrar silencios intermedios pero no puedes cambiar de
 * toma»*—, así que llevan pausas dentro por definición. Sin esta intersección,
 * elegir la frase entera y buena costaría tres segundos de aire.
 */
function conHabla(a, b, runs) {
  const trozos = [];
  for (const [ra, rb] of runs) {
    const x = Math.max(a, ra - MARGEN);
    const y = Math.min(b, rb + MARGEN);
    if (y - x <= 0.05) continue;
    const ult = trozos[trozos.length - 1];
    // Dos tramos separados por menos de AIRE se unen: esa pausa se respeta.
    if (ult && x - ult[1] < AIRE) ult[1] = y;
    else trozos.push([x, y]);
  }
  return trozos.length ? trozos : [[a, b]];
}

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i === -1 ? d : process.argv[i + 1];
};

/**
 * **Una escena por tramo, no una cada 3 s.**
 *
 * Jaime: *«los cortes de imagen son muy fuertes, pasan de un punto al otro; el
 * cambio debería ser continuo, progresivo, no ese cambio tan cortante»*. Y era
 * literal: la escena 9 iba a un recorte de 994 px y la 10 saltaba a 1744. Seis
 * recortes fijos pegados dentro de un mismo beat, cada frontera un salto.
 *
 * La regla de los 3 s sigue siendo el pulso del CORTE —y el corte cae donde
 * cambia la idea, que es la frontera del beat—. Dentro del beat no se corta: se
 * mueve. Por eso `CADA` es enorme por defecto: un tramo, una escena.
 */
const CADA = Number(arg("cada", "999"));
const MINIMO = 1.2;

const slug = `reel-${String(arg("reel")).padStart(2, "0")}`;
/** La toma del reel, para poder leer sus tramos de habla. */
const tomaDe = (sl) =>
  JSON.parse(fs.readFileSync("rutas.json", "utf8")).tomas[sl];
const edl = JSON.parse(fs.readFileSync(`ads/${slug}/edl-sell.json`, "utf8"));

const runs = JSON.parse(
  fs.readFileSync(`work/cuts/${edl.toma ?? tomaDe(slug)}.json`, "utf8"),
).segmentos;

const escenas = [];
let montado = 0;
let aireQuitado = 0;
// Cada segmento del EDL se parte en los trozos que SÍ tienen voz.
/**
 * **Cada escena sabe de dónde viene.** Regla de Jaime: *«cada parte o cada
 * fragmento debe guardarse por separado, e identificarse por separado… de esa
 * manera el segmento queda relacionado a un vídeo, pero también a un frame, y
 * también a una intención comunicativa o libreto»*.
 *
 * Son las tres relaciones y van juntas: el **vídeo** (el reel), la **etapa del
 * frame** (qué función cumple en la estructura) y el **mensaje esperado** (qué
 * tenía que decir ahí el libreto). Sin ellas una escena es un rango anónimo
 * dentro de un JSON y no hay forma de decir «esta parte no sirve» sin contar
 * cortes con el dedo.
 *
 * La etapa sale del `detalle` del EDL **por el corte del que nace la escena**,
 * no por tiempo: el reparto puede ir fuera de orden (aprendizaje 35).
 */
const conVoz = edl.segmentos.flatMap(([a, b], iSeg) => {
  const t = conHabla(a, b, runs);
  aireQuitado += b - a - t.reduce((n, [x, y]) => n + (y - x), 0);
  const d = (edl.detalle || [])[iSeg] || {};
  return t.map(([x, y]) => [x, y, d.beat ?? iSeg + 1, d.etapa || "", d.texto || ""]);
});

for (const [a, b, beat, etapa, dicho] of conVoz) {
  const dur = b - a;
  // Cuantas escenas caben; el resto se reparte para que ninguna quede corta.
  const n = Math.max(1, Math.round(dur / CADA));
  const paso = dur / n;
  for (let k = 0; k < n; k++) {
    const ini = a + paso * k;
    const fin = k === n - 1 ? b : a + paso * (k + 1);
    if (fin - ini < MINIMO && escenas.length) {
      // Se funde con la anterior en vez de crear un plano de parpadeo.
      const prev = escenas[escenas.length - 1];
      if (Math.abs(prev.origen_hasta - ini) < 1e-6) {
        prev.origen_hasta = fin;
        prev.duracion = Number((fin - prev.origen_desde).toFixed(3));
        montado += fin - ini;
        continue;
      }
    }
    escenas.push({
      indice: escenas.length,
      // De qué sección de frame nace esta escena, y qué dijo ahí. Sin esto la
      // escena es un rango anónimo y no hay forma de decir «esta parte no
      // sirve» sin contar cortes con el dedo.
      beat,
      etapa,
      dicho: dicho.slice(0, 160),
      montado_desde: Number(montado.toFixed(3)),
      origen_desde: Number(ini.toFixed(3)),
      origen_hasta: Number(fin.toFixed(3)),
      duracion: Number((fin - ini).toFixed(3)),
      modo: k === 0 ? "cut" : "chain",
      hereda_encuadre: false,
      /**
       * **El movimiento dentro de la escena.** `punch-ins.py` calcula el
       * recorte final con los OJOS como punto fijo (aprendizaje 27), así que
       * el acercamiento no deriva en diagonal aunque el recorte toque un borde.
       *
       * 0,88 son doce puntos de recorrido repartidos por toda la escena. En un
       * beat de 15 s eso es 0,8 %/s: **no se nota mientras pasa, se nota al
       * comparar el principio con el final**, que es la calibración correcta.
       */
      zoom: { hasta: 0.88, desde_s: 0.3 },
    });
    montado += fin - ini;
  }
}

const plan = {
  source: bruto(slug),
  gancho_s: Number(montado.toFixed(3)),
  cambio_cada_s: CADA,
  escenas,
};
const out = `work/scenes/${slug}/plan-full.json`;
// **La carpeta se crea aquí.** Nunca se creaba: existía de corridas anteriores,
// así que el fallo sólo aparece arrancando de cero — y arrancar de cero es
// justo lo que hay que poder hacer. Un paso que depende de que alguien haya
// corrido otro antes no es un paso, es una suposición.
fs.mkdirSync(`work/scenes/${slug}`, { recursive: true });
fs.writeFileSync(out, JSON.stringify(plan, null, 1));
console.log(
  `${slug}: ${escenas.length} escenas · ${montado.toFixed(1)}s ` +
  `(quitados ${aireQuitado.toFixed(1)}s de silencio interno) → ${out}`,
);
