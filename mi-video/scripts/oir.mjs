/**
 * La pista de una pieza **con los efectos encendidos**, para oírla y decidir.
 *
 * Jaime: *«si me das el audio con el efecto no puedo pasarlo por Adobe Podcast,
 * aunque sí quiero oírlo»*. Son dos ficheros distintos y hasta ahora sólo había
 * uno, así que la regla de *«los videos para aprobación van sin música y sin
 * audio adicional»* le quitaba también la posibilidad de juzgar los efectos —
 * que es el ticket #2, el tablero del segundo 30 que se queda mudo.
 *
 * ## Por qué no basta con ffmpeg
 *
 * Los efectos no se pegan encima: viven **dentro** del render, en las capas
 * `MotionSound` que el spec enciende con `sonido`. Sin `sonido` no existen en el
 * mp4, así que no hay nada que subir de volumen después. Hay que renderizar.
 *
 * ## Y por qué no se toca `src/reels.json`
 *
 * Encender `sonido` en el spec cambiaría la huella de la pieza, o sea que las
 * siete quedarían caducas y habría que rehacer los vídeos para poder oír un
 * efecto. Se pasa por `inputProps`, que Remotion superpone a los `defaultProps`
 * de la composición: el fichero no se toca, la huella no se mueve y lo
 * entregado sigue siendo lo entregado.
 *
 * Sale sólo audio —`codec: "mp3"`—, así que no se pinta un solo frame: son
 * segundos por pieza en vez de los cuatro minutos de un render de vídeo.
 *
 *   node scripts/oir.mjs 1 2 3
 */
import fs from 'fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {rutas} from './rutas.mjs';

const piezas = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
if (piezas.length === 0) {
  console.error('uso: node scripts/oir.mjs 1 2 3 …');
  process.exit(1);
}

const spec = JSON.parse(fs.readFileSync('src/reels.json', 'utf8'));
const salidaDir = path.join(rutas.destino, 'revision');
fs.mkdirSync(salidaDir, {recursive: true});

// Misma carpeta por proceso y misma cache apagada que `render.mjs`: lo que se
// oye no puede ser mas viejo que lo que se compuso.
const dirBundle = path.join(rutas.temporal ?? 'F:/tmp-video', `oir-${process.pid}`);
console.log('empaquetando…');
const servedUrl = await bundle({
  entryPoint: path.resolve('src/index.ts'),
  outDir: dirBundle,
  enableCaching: false,
  onProgress: () => {},
});

for (const n of piezas) {
  const id = `Reel-R${n}`;
  const suyo = spec.find((x) => x.id === id);
  if (!suyo) {
    console.log(`${id}: no esta en el spec`);
    continue;
  }
  // **Esto es lo unico que cambia**: los efectos encendidos, en memoria.
  const inputProps = {spec: {...suyo, sonido: true}};
  const salida = path.join(salidaDir, `reel-R${n}-efectos.mp3`);
  const t = Date.now();
  const composition = await selectComposition({serveUrl: servedUrl, id, inputProps});
  await renderMedia({
    composition,
    serveUrl: servedUrl,
    codec: 'mp3',
    outputLocation: salida,
    inputProps,
    logLevel: 'error',
  });
  console.log(`${id}: ${((Date.now() - t) / 1000).toFixed(1)} s  ->  ${salida}`);
}

fs.rmSync(dirBundle, {recursive: true, force: true});
