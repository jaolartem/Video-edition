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
import { createHash } from "crypto";
import path from "path";
import { lienzoDePieza } from "./lienzo.mjs";
import { angulo, cinta } from "./rutas.mjs";

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
// **Y el cuadro es el de la pieza** (C-671): el alto sale de la proporcion de
// su lienzo, no de un 16/9 escrito para el vertical. De que pieza es lo dice la
// ruta del plan, igual que en `compas`.
const LIENZO = lienzoDePieza(path.basename(path.dirname(arg("plan") ?? "")));
const ANCHO = Number(arg("ancho", String(LIENZO.width)));
const ALTO = Math.round((ANCHO * LIENZO.height) / LIENZO.width);

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
/**
 * **Un fotograma clave cada medio segundo (`-g 15`), y no cada cuatro.**
 *
 * Este fichero es lo que Remotion lee frame a frame, y Chrome no lo pide en
 * orden: cada peticion fuera de sitio paga decodificar desde el keyframe
 * anterior. El corte salia con 24 keyframes en 99 s —uno cada 4,1 s de media,
 * alguno a 8 s— y en el banco de 300 frames eso eran 33,4 s contra 27,5 s con
 * keyframes densos: **un 18% del render, sin tocar un pixel de lo que se ve**.
 *
 * No es bajar la calidad: `qp 18` sigue igual. Es como se ORGANIZA el fichero,
 * que es justo lo que la nota del 1 de septiembre dejo escrito como lo unico
 * que se podia cambiar sin perder informacion. Pesa algo mas en disco y es un
 * intermedio que se borra.
 */
const ENCODE = GPU
  ? ["-c:v", "h264_amf", "-quality", "quality", "-rc", "cqp",
     "-qp_i", "18", "-qp_p", "18", "-g", "15"]
  // `crf 18`, no 20, y por lo que dice el parrafo de arriba: este fichero es
  // INTERMEDIO y Remotion lo vuelve a codificar, asi que la perdida se paga
  // dos veces. El camino de GPU ya iba a `qp 18`; los dos listones tenian que
  // ser el mismo y no lo eran.
  : ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "15"];

if (!source || !planPath) {
  console.error("Uso: node scripts/render-hook.mjs --source <mp4> --plan <plan.json> [--out <mp4>]");
  process.exit(1);
}

const plan = JSON.parse(fs.readFileSync(planPath, "utf8"));
const escenas = plan.escenas ?? [];

/**
 * **Las pausas que hacen que la pieza baile con su cancion.**
 *
 * Jaime, 17-9-2026: *«quiero que algunas tomas inicien dentro del beat de la
 * cancion, que el reel baile con la musica»*. Las costuras estan donde el habla
 * las deja, asi que no se mueven; lo que se mueve es lo que hay entre ellas.
 * Una pausa congela el ultimo frame de la escena y calla — la imagen se queda
 * quieta justo en el golpe — y con eso la costura siguiente cae en el beat.
 *
 * **Y se oyen a proposito.** Su regla al fijar cuanto: *«por eso es que baila
 * porque se oye, por eso resalta porque se oye»*. Una pausa de 80 ms alinea el
 * numero y no alinea nada que alguien perciba.
 *
 * Se declaran en `src/brand/compas.json` por indice de escena, con su fase y su
 * porque, y se miden contra la rejilla de SU cancion. Aqui solo se aplican.
 */
const compas = (() => {
  try {
    const j = JSON.parse(fs.readFileSync("src/brand/compas.json", "utf8"));
    // **De que pieza es lo dice la RUTA del plan**, `work/scenes/reel-14/…`: el
    // plan no lleva slug dentro y anadirselo obligaria a regenerar los veinte.
    const slug = path.basename(path.dirname(planPath));
    return j[slug] || null;
  } catch { return null; }
})();
const pausaDe = (e) => Number(compas?.pausas?.[String(e.indice)] ?? 0) || 0;
/**
 * El bruto de esta escena: el suyo si lo declara, el del reel si no.
 *
 * **Y la grabación puede ser una carpeta** (C-672): el `<toma>.mp4` junto al
 * del reel sólo existe cuando las dos son ficheros sueltos. Si no está, se le
 * pregunta a `rutas.cinta`, que sabe de carpetas y de su ángulo principal.
 */
const fuenteDe = (e) => {
  if (!e.fuente) return source;
  const plano = path.join(path.dirname(source), `${e.fuente}.mp4`);
  return fs.existsSync(plano) ? plano : cinta(e.fuente);
};
/** De dónde sale la IMAGEN: el ángulo que pidió la escena, con su reloj. */
const imagenDe = (e) => {
  if (!e.angulo) return null;
  const a = angulo(e.fuente, e.angulo);
  return { fichero: a.fichero, desde: Math.max(0, e.origen_desde - a.desfase) };
};
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
// **La carpeta ya no se borra: cada trozo es una escena con su huella** (C-567).
// Re-cortar el 4K de las 29 escenas porque cambio una costaba ~65 s por montaje;
// un trozo cuyos parametros no cambiaron se reutiliza, y al final se quitan los
// que ya no salen en la lista.
fs.mkdirSync(tmp, { recursive: true });
fs.mkdirSync(path.dirname(out), { recursive: true });

const total = escenas.reduce((n, e) => n + e.duracion, 0);
console.error(
  `${escenas.length} escenas · ${total.toFixed(1)}s → ` +
    `${(total / VELOCIDAD).toFixed(1)}s a ${VELOCIDAD}× · ${GPU ? "GPU" : "CPU"}`,
);

const trozos = [];
let reutilizados = 0;
escenas.forEach((e, i) => {
  const img = imagenDe(e);
  const clave = createHash("sha1").update(JSON.stringify([fuenteDe(e), e.origen_desde,
    e.duracion, filtroDe(e), pausaDe(e), DECODE, ENCODE,
    ...(img ? [img] : [])])).digest("hex").slice(0, 16);
  const f = path.join(tmp, `${clave}.mp4`);
  if (fs.existsSync(f)) { trozos.push(f); reutilizados += 1; return; }
  const z = e.zoom ? `  zoom a ${e.zoom.hasta}` : "";
  console.error(
    `  ${e.indice} ${e.encuadre.padEnd(12)} ${e.duracion.toFixed(1)}s${z}`,
  );
  execFileSync("ffmpeg", [
    "-v", "error", "-y",
    ...DECODE,
    "-ss", String(e.origen_desde),
    // **El `-t` va ANTES del `-i`: acota la ENTRADA, no la salida.** Estaba
    // detras, y ahi limita lo que se escribe pero no hace que el material se
    // acabe — asi que `tpad`, que clona el ultimo frame cuando la entrada
    // termina, no se disparaba nunca y la pausa salia de cero segundos.
    "-t", String(e.duracion),
    // **Cada escena abre SU fichero.** El corte abría uno solo para toda la
    // pieza, y por eso el material grabado en otra sesión estaba frenado. No
    // hay dos fuentes en un corte: hay dos cortes.
    "-i", fuenteDe(e),
    // **Otro ángulo: la imagen de ahí, la voz de aquí** (C-672). Cortar audio y
    // vídeo del ángulo dejaba la etapa sin voz: la cámara B del CV es la
    // grabación de pantalla.
    ...(img
      ? ["-ss", img.desde.toFixed(3), "-t", String(e.duracion), "-i", img.fichero,
         "-map", "1:v:0", "-map", "0:a:0"]
      : []),
    ...(pausaDe(e)
      ? ["-t", (e.duracion + pausaDe(e)).toFixed(3),
         "-vf", `${filtroDe(e)},tpad=stop_mode=clone:stop_duration=${pausaDe(e).toFixed(3)}`]
      : ["-vf", filtroDe(e)]),
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
    // El fundido de salida va donde acaba la VOZ, no donde acaba la escena: con
    // pausa detras, el silencio ya esta callado y fundir ahi no tapa nada.
    "-af", `afade=t=in:st=0:d=0.03,afade=t=out:st=${Math.max(0, e.duracion - 0.03).toFixed(3)}:d=0.03`
           + (pausaDe(e) ? `,apad=pad_dur=${pausaDe(e).toFixed(3)}` : ""),
    "-c:a", "aac", "-b:a", "160k", "-r", "30",
    "-video_track_timescale", "30000",
    f,
  ], { stdio: ["ignore", "inherit", "inherit"] });
  trozos.push(f);
});

// Se unen sin recodificar: los trozos salieron con los mismos parametros.
for (const viejo of fs.readdirSync(tmp)) {
  if (viejo.endsWith(".mp4") && !trozos.includes(path.join(tmp, viejo))) {
    fs.rmSync(path.join(tmp, viejo), { force: true });
  }
}
if (reutilizados) console.error(`  ${reutilizados} escena(s) sin cambios: se reutilizan`);
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
// **Y la carpeta se queda** (C-594): este borrado final deshacia C-567 y cada
// montaje volvia a cortar todas las escenas. Los trozos que ya no salen se
// quitan arriba, antes de unir.

console.error("\nlisto → " + out);
