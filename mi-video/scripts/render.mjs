/**
 * Renderiza las piezas por la API de Remotion, no por el CLI.
 *
 * **Por que, y es una sola cosa:** al lado del mp4 queda `reel-RN.mp4.huella`,
 * el sha1 del spec que ese fichero dibujo. `_render_caduco()` la exige para dar
 * la pieza por montada, y el CLI no la escribe. Sin ella toda pieza salia
 * caduca, el despachador relanzaba el montaje, y el video entregado seguia
 * siendo el de antes — tres dias el mismo video.
 *
 * De paso el bundle se rehace en una carpeta limpia, que es lo que el CLI
 * cachea, y se hace UNA vez para todas las piezas que se le pidan.
 *
 * **La codificacion NO va por GPU, y conviene tenerlo escrito.** Este fichero
 * traia un `ffmpegOverride` que cambiaba `libx264` por `h264_amf`. El ffmpeg
 * que Remotion trae dentro se compila con `--disable-encoders` y solo habilita
 * `h264_nvenc` y `hevc_nvenc`: no existe AMF. El render moria en el frame 0
 * —«Unrecognized option 'qp_i'»— asi que el banco de 30 s que medio 10,3 s
 * contra 6,4 s midio un ffmpeg distinto del que renderiza.
 *
 * Y no se pierde casi nada: la codificacion es el 14 % del render. Produciendo
 * 3.300 frames a 12,5/s son ~264 s por pieza, de los que ~38 s codifican. El
 * 86 % esta en producir los frames. Ver `docs/rendimiento.md`.
 */
import fs from 'fs';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import {rutas} from './rutas.mjs';

const piezas = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
if (piezas.length === 0) {
  console.error('uso: node scripts/render.mjs 1 2 3 …');
  process.exit(1);
}

/**
 * **Un temporal propio por proceso, y fuera de C:.**
 *
 * Dos renders a la vez se mataron entre ellos: Remotion mezcla el audio en
 * `os.tmpdir()/remotion-<version>-assets<hash>/remotion-audio-mixing/`, y la
 * limpieza de un proceso borro la carpeta que el otro estaba usando —«Error
 * opening output ... 1.wav: No such file or directory»—. Cuatro piezas de
 * siete se cayeron por eso, no por su contenido.
 *
 * El `bundle` ya se aislaba por PID; el temporal de assets no, porque lo elige
 * Remotion leyendo el entorno. Aqui se le dice cual.
 *
 * Y de paso lo saca de C:, que es el gotcha 1 del proyecto: el disco de
 * arranque lo llena un render a 1080x1920 y el aviso que da entonces habla de
 * Chrome, no del disco. `rutas.temporal` ya vive en F:.
 */
const TMP = path.join(rutas.temporal, `render-${process.pid}`);
fs.mkdirSync(TMP, {recursive: true});
process.env.TMPDIR = TMP;
process.env.TEMP = TMP;
process.env.TMP = TMP;

const t0 = Date.now();
console.log('empaquetando una vez para todas…');
// **El bundle se hace SIN cache, y esa es la palanca buena.**
//
// `src/reels.json` se importa dentro del bundle, asi que lo que el render dibuja
// es la copia COMPILADA del spec, no el fichero de disco.
//
// Esto estaba resuelto borrando la carpeta de salida con `fs.rmSync`, y era
// peor que no hacer nada: la cache de webpack **no vive ahi** —vive en
// `node_modules/.cache/webpack`— asi que sobrevivia al borrado, webpack daba
// todo por emitido y no escribia `bundle.js`. La segunda corrida moria con
// un ENOENT sobre ese `bundle.js` despues de anunciar «bundle listo en 3,6 s»,
// en 3,6 s», que es lo que tarda no hacer nada.
//
// `enableCaching: false` es la opcion que el propio bundler expone. Cuesta ~8 s
// mas por corrida y quita una clase entera de fallo: lo que se dibuja no puede
// ser mas viejo que lo que se compuso.
// Carpeta propia por corrida: `avanzar.py --despachar --hilos 4` monta cuatro
// piezas a la vez y dos procesos empaquetando en la misma carpeta se pisan los
// ficheros. Con la cache apagada eso deja de ser lentitud y pasa a ser un
// bundle a medias, que es de lo que veniamos.
const dirBundle = path.join(rutas.temporal ?? 'F:/tmp-video',
                            `bundle-${process.pid}`);
const servedUrl = await bundle({
  entryPoint: path.resolve('src/index.ts'),
  outDir: dirBundle,
  enableCaching: false,
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
    // **Concurrencia 4, no 16.** Con 16 el render muere en un frame cualquiera
    // —«waiting for the page to render the React component at frame 1387
    // failed»— y el propio paso ya lo sabia: reintentaba con 4 diciendo *«mas
    // lento y aguanta»*. Un reintento que siempre se dispara no es un reintento:
    // es el valor bueno escrito en el sitio equivocado.
    //
    // Y con la capa grafica compuesta cada frame cuesta mas que antes, asi que
    // 16 pestanas compitiendo por la GPU es justo lo que lo tumba.
    concurrency: 4,
    offthreadVideoThreads: 4,
    logLevel: 'error',
  });
  // **Y el fichero queda estampado con lo que dibujo.**
  //
  // Jaime: *«con una que no cuadre es suficiente para saber que eso no es lo que
  // se mando a render»*. Esto es lo que lo hace comprobable de una sola vez: al
  // lado del mp4 queda la huella del spec que se acaba de dibujar. Si la huella
  // del disco no es la del spec de ahora, el video NO es lo que se compuso — sin
  // deducirlo de fechas, sin mirar siete frames, sin discutir.
  const suyo = JSON.parse(fs.readFileSync('src/reels.json', 'utf8'))
    .find((x) => x.id === id);
  if (suyo?.huella) fs.writeFileSync(salida + '.huella', suyo.huella);
  const seg = (Date.now() - t) / 1000;
  console.log(`${id}: ${seg.toFixed(1)} s  ->  ${salida}`);
}

fs.rmSync(dirBundle, {recursive: true, force: true});

// El temporal propio se recoge, como el bundle.
try { fs.rmSync(TMP, {recursive: true, force: true}); } catch {}
