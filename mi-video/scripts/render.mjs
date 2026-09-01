/**
 * Renderiza las piezas por la API de Remotion, no por el CLI.
 *
 * **Por qué, y son dos cosas medidas.**
 *
 * 1. **La codificación puede ir por GPU y no iba.** El flag
 *    `--hardware-acceleration` de Remotion no tiene rama AMD: en
 *    `get-codec-name.js` elige `videotoolbox` en Apple y `nvenc` en Windows, y
 *    si no hay ninguno cae a `libx264` por CPU. Esta máquina tiene una Radeon RX
 *    5600 XT con `h264_amf`, `hevc_amf` y `av1_amf`. Medido sobre 30 s reales a
 *    1080x1920: libx264 10,3 s · h264_amf 6,4 s · hevc_amf 3,4 s.
 *
 *    `ffmpegOverride` es el punto de extensión soportado —recibe la lista final
 *    de argumentos antes de ejecutarla— y sobrevive a un `npm install`, que es
 *    lo que no hace parchear `node_modules`.
 *
 * 2. **El bundle se hace UNA vez para las siete piezas.** El CLI lo rehace en
 *    cada invocación: son los ~6 s de arranque por pieza que se veían en el
 *    parte, pagados siete veces por nada.
 *
 * **Lo que esto NO arregla, y conviene tenerlo escrito:** la codificación es el
 * 14 % del render. Produciendo 3.300 frames a 12,5/s son ~264 s por pieza, de
 * los que ~38 s codifican. Esto ahorra 15-20 s por pieza y se hace porque es
 * gratis, no porque resuelva. El 86 % está en producir los frames, y ahí el
 * sospechoso medido es el intermedio: H.264 a 33 Mbps con GOP largo,
 * decodificado 3.300 veces. Ver `docs/rendimiento.md`.
 */
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import {rutas} from './rutas.mjs';

/** Calidad del codificador de AMD, en la escala que entiende. */
const QP = 18;

/**
 * Cambia el codificador de CPU por el de la tarjeta.
 *
 * AMF no entiende `-crf`: su control de calidad es `-rc cqp` con `-qp_i` y
 * `-qp_p`. Si se dejara el `-crf` dentro, ffmpeg lo ignora en unos builds y
 * revienta en otros — y «funciona en mi máquina» es exactamente lo que este
 * proyecto no puede permitirse. Así que se quita explícitamente.
 */
const porGPU = ({args}) => {
  const fuera = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-crf') {
      i++; // y su valor
      continue;
    }
    fuera.push(args[i]);
  }
  const k = fuera.indexOf('libx264');
  if (k === -1) return fuera; // no era el paso de vídeo: se deja igual
  fuera[k] = 'h264_amf';
  fuera.splice(k + 1, 0,
    '-rc', 'cqp', '-qp_i', String(QP), '-qp_p', String(QP),
    '-quality', 'quality');
  return fuera;
};

const piezas = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
if (piezas.length === 0) {
  console.error('uso: node scripts/render.mjs 1 2 3 …');
  process.exit(1);
}

const t0 = Date.now();
console.log('empaquetando una vez para todas…');
const servedUrl = await bundle({
  entryPoint: path.resolve('src/index.ts'),
  onProgress: () => {},
});
console.log(`bundle listo en ${((Date.now() - t0) / 1000).toFixed(1)} s`);

for (const n of piezas) {
  const id = `Reel-R${n}`;
  const salida = path.join(rutas.destino, 'reels', `reel-R${n}.mp4`);
  const t = Date.now();
  const composition = await selectComposition({serveUrl: servedUrl, id});
  await renderMedia({
    composition,
    serveUrl: servedUrl,
    codec: 'h264',
    outputLocation: salida,
    // La composición ya iba por GPU con `--gl=angle`: Chrome dibuja por D3D11 y
    // no por software. Se conserva tal cual.
    chromiumOptions: {gl: 'angle'},
    concurrency: 16,
    offthreadVideoThreads: 8,
    ffmpegOverride: porGPU,
    logLevel: 'error',
  });
  const seg = (Date.now() - t) / 1000;
  console.log(`${id}: ${seg.toFixed(1)} s  ->  ${salida}`);
}
