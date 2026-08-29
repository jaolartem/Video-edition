/**
 * Renderiza el gancho aplicando un encuadre distinto a cada escena.
 *
 * Toma el plan que produjeron `scene-plan.mjs` y `punch-ins.py`, y monta el
 * gancho cortando cada 3 segundos con un recorte distinto del MISMO plano fijo.
 * El resultado es cambio de plano real sin cambiar de cámara — y con
 * continuidad perfecta, porque es literalmente la misma toma.
 *
 * Cada escena se extrae por separado con `-ss` antes de `-i` y luego se
 * concatenan sin recodificar. Ver el comentario largo más abajo: hacerlo en un
 * solo grafo de filtros obligaba a decodificar el fichero entero y costaba
 * veinte minutos por pieza; así cuesta menos de dos.
 *
 * Uso:
 *   node scripts/render-hook.mjs --source "G:/.../X.mp4" \\
 *        --plan work/scenes/reel-01/plan.json --out public/hook-reel-01.mp4
 */
import { execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const arg = (n, d) => {
  const i = process.argv.indexOf(`--${n}`);
  return i === -1 ? d : process.argv[i + 1];
};

const source = arg("source");
const planPath = arg("plan");
const out = arg("out", "public/hook.mp4");
/**
 * Resolucion del corte intermedio: **1800×3200, no 1080×1920**.
 *
 * El bruto es 4K (2160×3840) y los punch-ins recortan hasta el 46% del cuadro.
 * Bajando el intermedio a 1080 se tiraba resolucion que los encuadres abiertos
 * todavia tenian, y los cambios de escena perdian nitidez — lo noto Jaime.
 *
 * A 1800 el encuadre abierto (1952 px de ancho de origen) se reescala 0,92x en
 * vez de 0,55x. **Los mas cerrados si se interpolan** —el primer plano son 1123
 * px de origen— pero interpolar un plano cerrado se nota menos que tirar detalle
 * en todos.
 */
// **1080, no 1800.** La ventaja del 4K es el margen de recorte de los
// punch-ins, y ese margen se gasta AL RECORTAR: lo que sale del recorte ya no
// gana nada por guardarse mas grande. Medido: a 1800 el render de Remotion
// tarda 2,8x mas por pixeles que la entrega no usa.
const ANCHO = Number(arg("ancho", "1080"));
const ALTO = Math.round((ANCHO * 16) / 9);

/**
 * Tarjeta gráfica para decodificar y codificar. `--cpu` la desactiva.
 *
 * Medido sobre una escena de 3 s del bruto 4K HEVC:
 *
 *   CPU entera                        14,7 s
 *   decodifica GPU + codifica x264     8,1 s   (1,8×)
 *   decodifica GPU + codifica AMF      5,1 s   (2,9×)
 *
 * **La decodificación es la mitad del ahorro**: el bruto es 4K HEVC y
 * descomprimirlo por CPU cuesta más que todo lo demás junto. Por eso el corte
 * tardaba lo que tardaba.
 *
 * `qp 18` en AMF es visualmente transparente, y este fichero es intermedio —
 * Remotion lo vuelve a codificar después—, así que conviene que salga limpio y
 * rápido más que pequeño.
 */
/**
 * Velocidad del montaje. 1,15× por defecto.
 *
 * Jaime: *«el video se siente muy poco dinámico… ponlo a 1.1X o a 1.2X»*. No es
 * un truco de duración: el habla explicativa grabada sin público va más lenta de
 * lo que aguanta el scroll, y acelerar un 15% se nota en el pulso y no en el
 * timbre. Por encima de 1,25 la voz empieza a sonar a ardilla.
 *
 * Se aplica al FINAL, sobre el montaje ya concatenado: si se aplicara por
 * escena, los tiempos de cada corte dejarían de casar con el EDL.
 */
const VELOCIDAD = Number(arg("velocidad", "1"));

const GPU = !process.argv.includes("--cpu");
const DECODE = GPU ? ["-hwaccel", "d3d11va"] : [];
const ENCODE = GPU
  ? ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp",
     "-qp_i", "18", "-qp_p", "18"]
  : ["-c:v", "libx264", "-preset", "medium", "-crf", "20"];

if (!source || !planPath) {
  console.error("Uso: node scripts/render-hook.mjs --source <mp4> --plan <plan.json> [--out <mp4>]");
  process.exit(1);
}

const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
const escenas = plan.escenas ?? [];
/** El bruto de esta escena: el suyo si lo declara, el del reel si no. */
const fuenteDe = (e) =>
  e.fuente ? path.join(path.dirname(source), `${e.fuente}.mp4`) : source;
// Se comprueba `crop`, no `filtro`: el filtro ya no se lee del plan —se
// construye aqui con la resolucion de salida— asi que un plan valido puede no
// traerlo. El recorte es el dato que de verdad hace falta.
if (!escenas.length || !escenas[0].crop) {
  console.error("El plan no tiene encuadres. Ejecuta antes scripts/punch-ins.py");
  process.exit(1);
}

/**
 * Construye el filtro de recorte de una escena, con acercamiento si lo pide.
 *
 * El zoom se hace con expresiones de tiempo dentro de `crop`, no con `zoompan`:
 * zoompan trabaja sobre fotogramas ya escalados y produce temblor a
 * desplazamientos pequeños. Interpolando el rectangulo de recorte y escalando
 * despues, el movimiento es continuo y limpio.
 *
 * La curva es **lineal** a proposito: el sistema admite linear o ease-out y
 * nada mas, y un acercamiento que acelera lee como efecto, no como intencion.
 */
const filtroDe = (e) => {
  // El filtro se construye AQUI a partir de `crop`, no se lee de `e.filtro`.
  //
  // `punch-ins.py` guarda un `filtro` ya montado con la resolucion de salida
  // dentro, asi que al subir la salida a 1800 los planes viejos seguian
  // escalando a 1080 y el render salia en 1080 sin avisar. El recorte es dato;
  // la resolucion de salida es decision de quien renderiza.
  if (!e.zoom || !e.zoom.crop_final) {
    const c = e.crop;
    return `crop=${c.w}:${c.h}:${c.x}:${c.y},scale=${ANCHO}:${ALTO}:flags=lanczos`;
  }
  const c = e.crop;
  const f = e.zoom.crop_final;
  const ts = e.zoom.desde_s ?? 0;
  const dz = e.zoom.duracion_s ?? Math.max(0.5, e.duracion - ts);
  const k = `min(max((t-${ts})/${dz}\,0)\,1)`;
  return (
    `crop=w='${c.w}+(${f.w}-${c.w})*${k}':h='${c.h}+(${f.h}-${c.h})*${k}':` +
    `x='${c.x}+(${f.x}-${c.x})*${k}':y='${c.y}+(${f.y}-${c.y})*${k}',` +
    `scale=${ANCHO}:${ALTO}:flags=lanczos`
  );
};

/**
 * Cada escena se extrae POR SEPARADO y luego se concatenan.
 *
 * La version anterior metia las N escenas en un solo `filter_complex` con N
 * `trim`. ffmpeg entonces **decodifica el fichero entero**: para llegar al
 * `trim` que empieza en el minuto 9 hay que decodificar los nueve minutos
 * previos, y en 4K HEVC eso son diez minutos de reloj por pieza. Medido — y
 * medido tambien que **no era la red**: con el bruto copiado a disco local
 * tardaba exactamente igual.
 *
 * Con `-ss` ANTES de `-i`, ffmpeg salta al keyframe anterior y decodifica solo
 * lo que hace falta. Cada escena cuesta su propia duracion en vez de todo lo que
 * hay delante. Un reel de veinte escenas de tres segundos pasa de decodificar
 * diez minutos a decodificar uno.
 *
 * `-ss` antes de `-i` es exacto cuando se recodifica: ffmpeg descarta lo que
 * sobra entre el keyframe y el punto pedido.
 */
/**
 * Carpeta temporal **propia de cada salida**, no una compartida.
 *
 * Con una fija (`work/seg`) dos cortes solapados se pisaban, y si un proceso
 * quedaba vivo tras una interrupcion el siguiente moria con `EPERM: resource
 * busy` al intentar borrarla — un error que no dice nada del corte y manda a
 * mirar permisos. Con una por salida, un proceso zombi molesta a su propia
 * carpeta y a ninguna mas.
 */
const tmp = path.join(
  process.cwd(),
  "work",
  "seg-" + path.basename(out).replace(/\.\w+$/, ""),
);
try {
  fs.rmSync(tmp, { recursive: true, force: true });
} catch (e) {
  console.error(`  ojo: no se pudo limpiar ${tmp} (${e.code}); se reutiliza`);
}
fs.mkdirSync(tmp, { recursive: true });
fs.mkdirSync(path.dirname(out), { recursive: true });

const total = escenas.reduce((n, e) => n + e.duracion, 0);
console.error(
  `${escenas.length} escenas · ${total.toFixed(1)}s → ` +
    `${(total / VELOCIDAD).toFixed(1)}s a ${VELOCIDAD}× · ${GPU ? "GPU" : "CPU"}`,
);

const trozos = [];
escenas.forEach((e, i) => {
  const f = path.join(tmp, `s${String(i).padStart(3, "0")}.mp4`);
  const z = e.zoom ? `  zoom a ${e.zoom.hasta}` : "";
  console.error(
    `  ${e.indice} ${e.encuadre.padEnd(12)} ${e.duracion.toFixed(1)}s${z}`,
  );
  execFileSync("ffmpeg", [
    "-v", "error", "-y",
    ...DECODE,
    "-ss", String(e.origen_desde),
    // **Cada escena abre SU fichero.** El corte abría uno solo para toda la
    // pieza, y por eso el material grabado en otra sesión estaba frenado. No
    // hay dos fuentes en un corte: hay dos cortes.
    "-i", fuenteDe(e),
    "-t", String(e.duracion),
    "-vf", filtroDe(e),
    ...ENCODE,
    /**
     * **La costura tambien se oye.** Jaime: *«los cortes se sienten muy
     * marcados, hay que suavizarlos no solo visualmente»*.
     *
     * Cada escena sale de un punto distinto de la toma, asi que al pegarlas la
     * forma de onda salta de golpe: eso es un chasquido, y el oido lo localiza
     * antes de que la imagen haya cambiado. Cincuenta milisegundos de entrada y
     * de salida lo quitan.
     *
     * **No es un fundido cruzado**, y no puede serlo: un `acrossfade` se come
     * el solape, la pista de audio queda mas corta que la de video y la voz se
     * despega de la boca — que es peor que el chasquido. Con fundidos por
     * escena la duracion no cambia ni un frame.
     *
     * 0,03 s. Estuvo en 0,05 y con un corte a mitad de frase el hueco se oia -es
     * parte de lo que Jaime llamo *«se escucha raro a veces»*-. A 30 ms el
     * chasquido sigue tapado y el bache deja de percibirse.
     */
    "-af", `afade=t=in:st=0:d=0.03,afade=t=out:st=${Math.max(0, e.duracion - 0.03).toFixed(3)}:d=0.03`,
    "-c:a", "aac", "-b:a", "160k", "-r", "30",
    "-video_track_timescale", "30000",
    f,
  ], { stdio: ["ignore", "inherit", "inherit"] });
  trozos.push(f);
});

// Se unen sin recodificar: los trozos salieron con los mismos parametros.
const lista = path.join(tmp, "lista.txt");
fs.writeFileSync(
  lista,
  trozos
    .map((f) => "file '" + f.split(path.sep).join("/") + "'")
    .join("\n") + "\n",
);
if (VELOCIDAD === 1) {
  // Sin cambio de velocidad se unen sin recodificar.
  execFileSync("ffmpeg", [
    "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
    "-c", "copy", "-movflags", "+faststart", out,
  ], { stdio: ["ignore", "inherit", "inherit"] });
} else {
  // `atempo` conserva el tono; `setpts` es el video. Los dos con el mismo
  // factor o la voz se despega de la imagen.
  execFileSync("ffmpeg", [
    "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lista,
    "-vf", `setpts=PTS/${VELOCIDAD}`,
    /**
     * **`rubberband`, no `atempo`.** Jaime: *«la voz se escucha robotica»*, y
     * era eso: `atempo` reasigna trozos de forma de onda y sobre voz deja el
     * artefacto metalico clasico. `rubberband` es un estirador de fase
     * vocoder con **preservacion de formantes**, que es justo lo que hace que
     * una voz siga sonando a esa persona al cambiarle el tempo.
     *
     * **`transients` por defecto (`crisp`), no `smooth`.** Lo puse en `smooth`
     * razonando que aqui no hay percusion que proteger, y estaba mal: **las
     * consonantes SON transitorios**. Suavizarlos emborrona las oclusivas y es
     * lo que quedaba sonando raro despues de arreglar lo demas.
     *
     * La referencia es la documentacion del propio filtro y el consenso de que
     * `atempo` no se usa para voz. Coste: es mas lento, y no importa —el corte
     * ya va por GPU y esto es una pista de audio.
     */
    "-af", `rubberband=tempo=${VELOCIDAD}:formant=preserved`,
    ...ENCODE, "-c:a", "aac", "-b:a", "160k",
    "-movflags", "+faststart", out,
  ], { stdio: ["ignore", "inherit", "inherit"] });
}
fs.rmSync(tmp, { recursive: true, force: true });

console.error("\nlisto → " + out);
