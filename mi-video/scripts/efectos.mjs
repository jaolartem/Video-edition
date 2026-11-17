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
import {limpia, tramosDe, unirAudio} from './reels/escenas-render.mjs';

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
  const comun = {composition, serveUrl: servedUrl, codec: 'wav', inputProps, logLevel: 'error'};
  // **Escena a escena** (C-753): el mismo tramo y la misma huella que el
  // render (`tramos_de_render`); sólo se vuelve a sacar el de las escenas que
  // cambiaron, y se une en PCM cortado a la muestra.
  let tramos = [];
  try { tramos = tramosDe(n); } catch { tramos = []; }
  if (tramos.length < 2) {
    await renderMedia({...comun, outputLocation: salida});
  } else {
    const dir = path.join('work', 'efectos', `reel-${String(n).padStart(2, '0')}`);
    fs.mkdirSync(dir, {recursive: true});
    const hechos = [];
    let nuevos = 0;
    for (const tr of tramos) {
      const b = Math.min(tr.b, composition.durationInFrames);
      if (b <= tr.a) continue;
      const f = path.join(dir, `${tr.huella}.wav`);
      if (!fs.existsSync(f)) {
        await renderMedia({...comun, frameRange: [tr.a, b - 1], outputLocation: f + '.tmp.wav'});
        fs.renameSync(f + '.tmp.wav', f);
        nuevos += 1;
      }
      hechos.push({f, dura: (b - tr.a) / composition.fps});
    }
    limpia(dir, hechos);
    fs.copyFileSync(unirAudio(hechos, path.join(dirBundle, `a${n}`)), salida);
    console.log(`  efectos por escena: ${nuevos} tramo(s) nuevos, ${hechos.length - nuevos} sin cambios`);
  }
  console.log(`${id}: ${((Date.now() - t) / 1000).toFixed(1)} s  ->  ${salida}`);
}

fs.rmSync(dirBundle, {recursive: true, force: true});
