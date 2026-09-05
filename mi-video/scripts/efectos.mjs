/**
 * La pista de SOLO EFECTOS de una pieza, para poder recuperarla después.
 *
 * ## Por qué hace falta
 *
 * Los efectos viven dentro del render: son capas `MotionSound` que Remotion
 * mezcla con el audio del plano. Y `voz-limpia.integrar` sustituye la pista
 * entera por la voz de Adobe —`-map 0:v -map 1:a`—, así que **al meter la voz
 * limpia se van todos**. Jaime, viendo las seis entregadas: *«faltó la música…
 * igual que los efectos de sonido»*.
 *
 * No se pueden separar de lo entregado: el render trae voz y efectos ya
 * mezclados. Lo que sí se puede es **volver a renderizar la misma composición
 * con el plano mudo**, y eso deja los efectos solos.
 *
 * ## Cómo
 *
 * `volumen: 0` viaja por `inputProps`, que Remotion superpone a los
 * `defaultProps`. No se toca `src/reels.json`: si se tocara, cambiaría la huella
 * de la pieza y las siete quedarían caducas por sacar una pista auxiliar.
 *
 *   node scripts/efectos.mjs 1 2 3
 */
import fs from 'fs';
import path from 'node:path';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import {rutas} from './rutas.mjs';

const piezas = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
if (piezas.length === 0) {
  console.error('uso: node scripts/efectos.mjs 1 2 3 …');
  process.exit(1);
}

const spec = JSON.parse(fs.readFileSync('src/reels.json', 'utf8'));
const salidaDir = 'out/audio-voz';
fs.mkdirSync(salidaDir, {recursive: true});

const dirBundle = path.join(rutas.temporal ?? 'F:/tmp-video', `sfx-${process.pid}`);
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
  // Los efectos encendidos y el plano mudo: lo único que cambia.
  const inputProps = {spec: {...suyo, sonido: true, volumen: 0}};
  const salida = path.join(salidaDir, `reel-R${n}-efectos.wav`);
  const t = Date.now();
  const composition = await selectComposition({serveUrl: servedUrl, id, inputProps});
  await renderMedia({
    composition,
    serveUrl: servedUrl,
    codec: 'wav',
    outputLocation: salida,
    inputProps,
    logLevel: 'error',
  });
  console.log(`${id}: ${((Date.now() - t) / 1000).toFixed(1)} s  ->  ${salida}`);
}

fs.rmSync(dirBundle, {recursive: true, force: true});
