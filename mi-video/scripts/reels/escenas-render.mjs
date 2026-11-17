/**
 * Lo que comparten el render y los efectos cuando van escena a escena (C-749,
 * C-753): de qué tramos se compone la pieza y cómo se une el audio de sus
 * tramos sin que el relleno de cada uno descuadre las costuras.
 */
import fs from 'fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';

/** `[{a, b, huella}]` de la pieza, de `dominio/fotograma.py :: tramos_de_render`. */
export const tramosDe = (n) => JSON.parse(execFileSync('python',
  ['scripts/dominio/fotograma.py', '--render', String(n)],
  {encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8'}}));

const ff = (args) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args],
  {stdio: ['ignore', 'inherit', 'inherit']});
const barra = (x) => path.resolve(x).split(path.sep).join('/');

/** Une el audio de `[{f, dura}]` en PCM, cortado a la muestra, y devuelve el wav. */
export const unirAudio = (hechos, tmp) => {
  fs.mkdirSync(tmp, {recursive: true});
  hechos.forEach((h, i) => ff(['-i', h.f, '-vn', '-af', `apad,atrim=0:${h.dura.toFixed(6)}`,
    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', path.join(tmp, `a${i}.wav`)]));
  fs.writeFileSync(path.join(tmp, 'a.txt'),
    hechos.map((_, i) => `file '${barra(path.join(tmp, `a${i}.wav`))}'`).join('\n') + '\n');
  ff(['-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'a.txt'), '-c', 'copy',
    path.join(tmp, 'a.wav')]);
  return path.join(tmp, 'a.wav');
};

/** Une sólo la pista de vídeo de cada tramo, sin recodificar. */
export const unirVideo = (hechos, tmp) => {
  fs.mkdirSync(tmp, {recursive: true});
  hechos.forEach((h, i) => ff(['-i', h.f, '-map', '0:v', '-c', 'copy', path.join(tmp, `v${i}.mp4`)]));
  fs.writeFileSync(path.join(tmp, 'v.txt'),
    hechos.map((_, i) => `file '${barra(path.join(tmp, `v${i}.mp4`))}'`).join('\n') + '\n');
  ff(['-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'v.txt'), '-map', '0:v', '-c', 'copy',
    path.join(tmp, 'v.mp4')]);
  return path.join(tmp, 'v.mp4');
};

/** Sólo los tramos de hoy en su carpeta: lo de escenas que ya no están, sale. */
export const limpia = (dir, hechos) => {
  for (const viejo of fs.readdirSync(dir)) {
    if (!hechos.some((h) => path.basename(h.f) === viejo)) fs.rmSync(path.join(dir, viejo), {force: true});
  }
};

export {ff};
