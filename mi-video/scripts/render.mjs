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
import {execFileSync} from 'node:child_process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import {rutas} from './rutas.mjs';
import {aplicar} from './temporal.mjs';

const piezas = process.argv.slice(2).filter((x) => /^\d+$/.test(x));
/**
 * **Empaquetar y no renderizar**, para que el lote pague el bundle una vez.
 *
 * Medido: `bundle()` sin cache cuesta **22,5 s**, y `montar.sh` llama a este
 * fichero con UNA pieza dentro de su bucle, asi que un lote de siete lo pagaba
 * siete veces — dos minutos y medio de empaquetar lo mismo. Este fichero ya
 * sabia hacerlo una vez para varias piezas (`for (const n of piezas)`); lo que
 * faltaba era una manera de que el lote lo empaquetara **antes** de repartir
 * las piezas y se lo pasara hecho.
 *
 * Imprime la ruta y sale. Quien la recibe la exporta en `BUNDLE_LOTE` y la
 * borra al terminar: el que no crea el bundle tampoco lo tira.
 */
const soloBundle = process.argv.includes('--solo-bundle');
if (piezas.length === 0 && !soloBundle) {
  console.error('uso: node scripts/render.mjs 1 2 3 …');
  console.error('     node scripts/render.mjs --solo-bundle   # imprime la ruta');
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
 * Chrome, no del disco.
 *
 * **Quien lo pone es `temporal.mjs`, y aqui hace falta llamarlo.** Este camino
 * entra por la API de Node, y `remotion.config.ts` —donde la regla vive para
 * todo lo que entra por el CLI— **no aplica a la API**: lo dice su propia
 * cabecera. Escrito a mano aqui, la comprobacion de «sin espacios» y el aviso
 * de sitio libre existian en un sitio y no en el otro.
 */
const TMP = aplicar(`render-${process.pid}`);
// **Y se recoge aunque el render muera** (C-575). Sólo se borraba al final del
// camino bueno: el 18-10 un render que fallaba en el fotograma 150 se reintento
// 38 veces y dejo 38 temporales de 4 GB, hasta llenar F: y romper la base con
// «disk I/O error». `exit` corre tambien cuando el proceso sale por un error.
process.on("exit", () => { try { fs.rmSync(TMP, {recursive: true, force: true}); } catch {} });

/**
 * Apunta lo que tardo el render, con sus banderas. **Nunca tumba el montaje.**
 *
 * La tabla `render` llevaba `frames`, `segundos` y `config` declarados desde el
 * esquema y **cero filas**, asi que «por que tarda una hora» solo se podia
 * contestar montando un banco a mano. Escribe `dominio/render.py`, que es la
 * puerta de la base — Node no abre `decisiones.db`.
 *
 * Si falla, se dice y se sigue: perder la medida es barato; perder el render
 * por no poder apuntarlo seria cambiar el precio de medir, y entonces se deja
 * de medir.
 */
const apuntar = (n, composition, seg) => {
  try {
    execFileSync(
      'python',
      [
        'scripts/dominio/render.py',
        `reel-${String(n).padStart(2, '0')}`,
        seg.toFixed(2),
        String(composition.durationInFrames),
        String(composition.width),
        String(composition.height),
        `concurrencia=${CONCURRENCIA} ovt=4 gl=angle codec=h264` +
          `${heredado ? ' bundle=lote' : ''}`,
      ],
      {stdio: 'ignore', env: {...process.env, PYTHONIOENCODING: 'utf-8'}},
    );
  } catch (e) {
    console.error(`  (no se pudo apuntar el render: ${e.message.split('\n')[0]})`);
  }
};

/** Pestanas de Chrome a la vez. Ver la nota larga en `renderMedia`. */
const CONCURRENCIA = Math.min(
  12,
  Math.max(1, Number(process.env.RENDER_CONCURRENCIA) || 8),
);

/**
 * **El render, escena a escena** (C-749). Jaime: *«haz la cadena por escena
 * también»*. Cada tramo —de una escena a la siguiente— se guarda en
 * `work/render/<pieza>/<huella>.mp4`, y su huella (`dominio/fotograma.py ::
 * tramos_de_render`) cambia sólo si cambia lo que se ve o se oye en él. Se
 * renderizan los que faltan, el vídeo se une sin recodificar y el audio se une
 * en PCM, cortado a la muestra, y se codifica una vez: así no se arrastra el
 * relleno del AAC de cada tramo en cada costura. Si algo falla, `false`: el
 * render entero de siempre.
 */
async function porEscena(n, composition, comun, salida) {
  let tramos;
  try {
    tramos = JSON.parse(execFileSync('python', ['scripts/dominio/fotograma.py',
      '--render', String(n)], {encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8'}}));
  } catch (e) {
    console.log(`  (por escena no: ${e.message.split('\n')[0]})`);
    return false;
  }
  if (!tramos || tramos.length < 2) return false;
  const total = composition.durationInFrames;
  const dir = path.join('work', 'render', `reel-${String(n).padStart(2, '0')}`);
  fs.mkdirSync(dir, {recursive: true});
  const hechos = [];
  let nuevos = 0;
  // Un navegador para todos los tramos: abrir uno por tramo son segundos cada vez.
  let navegador = null;
  for (const tr of tramos) {
    const b = Math.min(tr.b, total);
    if (b <= tr.a) continue;
    const f = path.join(dir, `${tr.huella}.mp4`);
    if (!fs.existsSync(f)) {
      navegador ??= await openBrowser('chrome', {chromiumOptions: {gl: 'angle'}});
      await renderMedia({...comun, frameRange: [tr.a, b - 1], enforceAudioTrack: true,
        puppeteerInstance: navegador, outputLocation: f + '.tmp.mp4'});
      fs.renameSync(f + '.tmp.mp4', f);
      nuevos += 1;
    }
    hechos.push({f, dura: (b - tr.a) / composition.fps});
  }
  if (navegador) await navegador.close({silent: true});
  for (const viejo of fs.readdirSync(dir)) {
    if (!hechos.some((h) => path.basename(h.f) === viejo)) fs.rmSync(path.join(dir, viejo), {force: true});
  }
  console.log(`  por escena: ${nuevos} tramo(s) renderizados, ${hechos.length - nuevos} sin cambios`);
  const tmp = path.join(TMP, `r${n}`);
  fs.mkdirSync(tmp, {recursive: true});
  const ff = (args) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...args], {stdio: ['ignore', 'inherit', 'inherit']});
  const barra = (x) => path.resolve(x).split(path.sep).join('/');
  // Sólo la pista de vídeo de cada tramo: unidos con su audio, el relleno del
  // AAC alarga cada tramo y el vídeo se descuadra una fracción en cada costura.
  hechos.forEach((h, i) => ff(['-i', h.f, '-map', '0:v', '-c', 'copy', path.join(tmp, `v${i}.mp4`)]));
  fs.writeFileSync(path.join(tmp, 'v.txt'),
    hechos.map((_, i) => `file '${barra(path.join(tmp, `v${i}.mp4`))}'`).join('\n') + '\n');
  ff(['-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'v.txt'), '-map', '0:v', '-c', 'copy', path.join(tmp, 'v.mp4')]);
  hechos.forEach((h, i) => ff(['-i', h.f, '-vn', '-af', `apad,atrim=0:${h.dura.toFixed(6)}`,
    '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', path.join(tmp, `a${i}.wav`)]));
  fs.writeFileSync(path.join(tmp, 'a.txt'), hechos.map((_, i) => `file '${barra(path.join(tmp, `a${i}.wav`))}'`).join('\n') + '\n');
  ff(['-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'a.txt'), '-c', 'copy', path.join(tmp, 'a.wav')]);
  ff(['-i', path.join(tmp, 'v.mp4'), '-i', path.join(tmp, 'a.wav'), '-map', '0:v', '-map', '1:a',
    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '320k', '-movflags', '+faststart', salida]);
  return true;
}

const t0 = Date.now();
// **En `--solo-bundle`, por la salida estandar va la ruta y NADA mas.**
//
// Quien la pide la captura con `$(...)`, asi que cualquier otra linea en stdout
// se le cuela dentro: el lote exportaria una ruta que no existe, cada pieza
// volveria a empaquetar por su cuenta y no fallaria nada — se perderia el
// ahorro en silencio, que es peor que un error. Lo informativo va a stderr, que
// es donde se lee igual.
const di = soloBundle ? console.error : console.log;
if (!process.env.BUNDLE_LOTE) di('empaquetando una vez para todas…');
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
// La carpeta sale del temporal ya aplicado y comprobado, no de `rutas.temporal`
// con una ruta escrita a mano de reserva: esa reserva era la sexta copia de una
// decision que solo vive en `rutas.json`.
//
// **Y el del lote se reutiliza, sin encender la cache.** `BUNDLE_LOTE` la pone
// `montar-lote.sh` despues de empaquetar una vez, antes de repartir las piezas:
// un solo escritor y N lectores de una carpeta estatica, que es seguro — lo que
// no lo era es dos procesos escribiendo la misma. La cache sigue apagada.
const prestado = process.env.BUNDLE_LOTE || '';
const heredado = prestado && fs.existsSync(path.join(prestado, 'index.html'));
// En `--solo-bundle` el bundle ES el temporal, no una carpeta dentro: asi la
// ruta que se imprime es exactamente la que hay que borrar despues, y no queda
// la carpeta padre vacia. Hay 22 GB de bundles huerfanos en `F:/tmp-video` de
// corridas que murieron a medias; no se añaden mas por comodidad de escritura.
const dirBundle = heredado ? prestado : soloBundle ? TMP : path.join(TMP, 'bundle');
const servedUrl = heredado
  ? prestado
  : await bundle({
      entryPoint: path.resolve('src/index.ts'),
      outDir: dirBundle,
      enableCaching: false,
      onProgress: () => {},
    });
di(
  heredado
    ? `bundle del lote: ${prestado}`
    : `bundle listo en ${((Date.now() - t0) / 1000).toFixed(1)} s`,
);

// `--solo-bundle`: la ruta por la salida estandar y nada mas. Quien la pidio se
// encarga de borrarla.
if (soloBundle) {
  console.log(dirBundle);
  process.exit(0);
}

for (const n of piezas) {
  const id = `Reel-R${n}`;
  const salida = path.join(rutas.destino, 'reels', `reel-R${n}.mp4`);
  const t = Date.now();
  const composition = await selectComposition({serveUrl: servedUrl, id});
  const comun = {
    composition,
    serveUrl: servedUrl,
    codec: 'h264',
    // La composición ya iba por GPU con `--gl=angle`: Chrome dibuja por D3D11 y
    // no por software. Se conserva tal cual.
    chromiumOptions: {gl: 'angle'},
    // **La concurrencia la reparte quien reparte las piezas, no este fichero.**
    //
    // Estaba fijada en 4, y con motivo: con 16 el render muere en un frame
    // cualquiera —«waiting for the page to render the React component at frame
    // 1387 failed»— y el paso anterior lo tapaba reintentando con 4. Un
    // reintento que siempre se dispara no es un reintento: es el valor bueno
    // escrito en el sitio equivocado.
    //
    // Pero 4 tambien era el valor de OTRO reparto: `montar-lote.sh` monta tres
    // piezas a la vez, o sea doce pestanas. Cuando la pieza va sola —que es lo
    // que hace `avanzar.py` en la fase `montado`— esas mismas doce caben, y
    // quedarse en cuatro es dejar la maquina parada. Medido sobre 300 frames:
    // 35,6 s a 4 · 33,4 s a 8 · 31,5 s a 16.
    //
    // Asi que el numero sale de `RENDER_CONCURRENCIA`, que el lote calcula
    // dividiendo su presupuesto entre las piezas que corren a la vez. Sin
    // variable, 8: una pieza sola. El tope sigue siendo el de siempre, doce.
    concurrency: CONCURRENCIA,
    offthreadVideoThreads: 4,
    // **El frame lento no mata el render.** El fallo del frame 1387 es un
    // plazo, no una excepcion: con mas pestanas compitiendo, pintar un frame
    // pasa de los 30 s por defecto y Remotion lo da por perdido. Subir el plazo
    // no lo hace mas rapido; hace que una pieza no se caiga entera por un frame
    // que tardo el doble.
    timeoutInMilliseconds: 120000,
    logLevel: 'error',
  };
  if (!(await porEscena(n, composition, comun, salida))) {
    await renderMedia({...comun, outputLocation: salida});
  }
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
  apuntar(n, composition, seg);
}

// El bundle prestado NO se borra: es del lote, y detras vienen mas piezas.
if (!heredado) fs.rmSync(dirBundle, {recursive: true, force: true});

// El temporal propio se recoge, como el bundle.
try { fs.rmSync(TMP, {recursive: true, force: true}); } catch {}
