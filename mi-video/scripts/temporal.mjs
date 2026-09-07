#!/usr/bin/env node
/**
 * **El temporal, aplicado por el proceso que renderiza.**
 *
 * La regla —*«todo debe ser producido en F:»*— vivia entera dentro de
 * `entorno.sh`, y una regla que vive dentro de un guion **solo protege a ese
 * guion**. `montar.sh` y `render.sh` la traian puesta; un `npx remotion still`
 * escrito a mano, no. El 6 de septiembre eso dejo **119 directorios y 27 GB** en
 * el TEMP del sistema y `C:` a **0 bytes** dos veces: la segunda se llevo por
 * delante `bash.exe`, o sea la herramienta con la que se arreglaba.
 *
 * Es la averia de siempre del proyecto: el conocimiento estaba en el
 * repositorio y **el camino que importaba no pasaba por ahi**.
 *
 * Asi que la regla baja un piso. Esto lo llaman los dos sitios por donde se
 * renderiza de verdad, y ninguno de los dos es un guion de shell:
 *
 *   `remotion.config.ts`   todo lo que entra por el CLI —`render`, `still`,
 *                          `bundle`, `studio`—, se lance como se lance
 *   `scripts/render.mjs`   la API de Node, donde el fichero de configuracion
 *                          **no aplica** (lo dice la cabecera del propio config)
 *
 * `entorno.sh` sigue existiendo para lo que no es Remotion —ffmpeg, python, el
 * perfil de Chrome— y **pregunta aqui** en vez de repetir la comprobacion.
 *
 * ## De donde sale, y por que no se escribe
 *
 * De `rutas.temporal`, que ya resuelve `--tmp` → `VIDEO_TMP` → `rutas.json` en
 * ese orden. **Ninguna ruta se escribe aqui dentro**: si aparece una constante
 * con `F:/` en este fichero, la decision volvio a estar en dos sitios.
 *
 * ## Lo que se comprueba, y por que para en vez de avisar
 *
 * 1. **Sin espacios.** Es el gotcha 1 del proyecto: la ruta estuvo en
 *    `F:/Edicion de video/tmp` y Remotion siguio escribiendo en `C:` **pese a
 *    las tres variables**, sin decir nada. El sintoma no habla del disco del
 *    sistema, asi que se busca donde no es.
 * 2. **No en el disco de arranque.** Que es lo que se viene a evitar.
 *
 * Las dos paran: un render tarda veinte minutos en fallar por esto, y el error
 * que da entonces habla de Chrome.
 *
 * El **sitio libre** solo avisa, y eso es deliberado: de seis piezas con 21 GB
 * en `C:` renderizaron cuatro. Parar ahi seria bloquear la linea por un
 * diagnostico sin probar.
 *
 *   node scripts/temporal.mjs              # dice donde esta y cuanto queda
 *   eval "$(node scripts/temporal.mjs --exportar)"   # lo que hace `entorno.sh`
 */
import fs from "node:fs";
import path from "node:path";
import { rutas } from "./rutas.mjs";

/**
 * El suelo del **disco del sistema**, en GB.
 *
 * Con 21 GB libres murieron dos piezas de seis con «Chrome rejecting the request
 * because the disk space is low», asi que el disco de arranque es un limite real
 * aunque el proyecto no produzca ahi.
 *
 * **Pero no porque Chrome escriba ahi**, que es lo que decia este comentario y
 * mandaba a buscar donde no era. Medido el 6-9-2026 sobre las siete piezas
 * enteras, de dos en dos: C: empezo en 47,1 GB y acabo en 47,1 GB — cero. Lo que
 * crecio fue `F:/tmp-video`: ~1,8 GB por render y ~1,6 GB por bundle.
 *
 * O sea que Chrome **mira** el disco del sistema y se niega si lo ve justo; no
 * lo llena. La diferencia importa cuando toca hacer sitio: no hay nada del
 * render que borrar en C:, hay que averiguar de quien es lo que lo ocupa. Aqui
 * eran 22,9 GB de cache de CapCut.
 */
const SUELO_SISTEMA_GB = 30;

/**
 * El suelo del **disco del temporal**, en GB.
 *
 * Sale de una cuenta, no de un numero redondo: cada `remotion still` o `bundle`
 * copia `public/` entero —los siete mp4, ~1,7 GB— a su carpeta (gotcha 9), y el
 * lote son siete piezas. Una tanda entera son ~12 GB solo de bundles, sin
 * contar los frames. Por debajo de 20 GB la tanda no cabe.
 */
const SUELO_TEMPORAL_GB = 20;

const barras = (p) => p.split(path.sep).join("/").replace(/\/+$/, "");

/** El disco de arranque, preguntado y no supuesto. `C:` en esta maquina. */
const discoSistema = () =>
  process.env.SystemDrive ? `${process.env.SystemDrive}\\` : path.parse(process.cwd()).root;

/** GB disponibles en el volumen de `dir`, o `null` si no se puede saber. */
const libresGB = (dir) => {
  try {
    const s = fs.statfsSync(dir);
    return (s.bsize * s.bavail) / 1e9;
  } catch {
    return null;
  }
};

/**
 * La base declarada, resuelta a absoluta y comprobada.
 *
 * Se comprueba la **absoluta** y no la escrita: `"tmp"` parece limpia y en este
 * repo resuelve a `F:/Edicion de video/mi-video/tmp`, que lleva espacios y es
 * justo lo que rompio. Chrome ve la absoluta; la guarda tambien.
 *
 * @throws si lleva espacios o cae en el disco de arranque.
 */
export function base() {
  const abs = path.resolve(rutas.temporal);
  if (/\s/.test(abs)) {
    throw new Error(
      `el temporal resuelve a «${abs}» y lleva espacios. Es el gotcha 1 del` +
        " proyecto: Remotion sigue escribiendo en el disco del sistema pese a" +
        " TMPDIR/TEMP/TMP y no lo dice. Se corrige `temporal` en rutas.json.",
    );
  }
  if (path.parse(abs).root.toLowerCase() === discoSistema().toLowerCase()) {
    throw new Error(
      `el temporal apunta a «${abs}», que es el disco de arranque, y aqui no` +
        " se produce ahi. Se corrige `temporal` en rutas.json.",
    );
  }
  return abs;
}

/** Se avisa una vez por proceso: el CLI carga esto en cada subcomando. */
let avisado = false;

/**
 * **Cuanto queda, antes de gastar veinte minutos.**
 *
 * Mira los dos discos porque los dos pueden pararlo: el del temporal, donde se
 * escribe, y el del sistema, que Chrome mira antes de dibujar. Avisa, no para —
 * ver la cabecera.
 */
export function sitio(dir) {
  if (avisado) return;
  avisado = true;
  const c = discoSistema();
  const libreC = libresGB(c);
  if (libreC !== null && libreC < SUELO_SISTEMA_GB) {
    console.warn(
      `temporal: quedan ${libreC.toFixed(1)} GB en ${c}. El render no escribe` +
        " ahi —lo suyo va al temporal— pero Chrome MIRA el disco del sistema y" +
        ` se niega si lo ve justo: por debajo de ${SUELO_SISTEMA_GB} GB muere a` +
        " mitad con un error que habla de disco sin decir cual. Hay que hacer" +
        " sitio con lo de otro; del render no hay nada que borrar ahi.",
    );
  }
  const libre = libresGB(dir);
  if (libre !== null && libre < SUELO_TEMPORAL_GB) {
    console.warn(
      `temporal: quedan ${libre.toFixed(1)} GB en ${dir}, y cada bundle copia` +
        ` public/ entero. Por debajo de ${SUELO_TEMPORAL_GB} GB la tanda no` +
        " cabe.",
    );
  }
}

/**
 * **Pone el temporal en ESTE proceso** y devuelve la carpeta aplicada.
 *
 * En Windows `os.tmpdir()` lee `TEMP` y `TMP`; los procesos POSIX leen
 * `TMPDIR`. Se ponen los tres porque la cadena mezcla node, python y bash, y
 * basta con que uno no lo vea para que vuelva a `C:`. Y Node los relee en cada
 * llamada, asi que ponerlos aqui alcanza a todo lo que venga despues —incluido
 * el `mkdtemp` con el que Remotion abre el perfil de Chrome.
 *
 * @param sub subcarpeta propia, para aislar corridas simultaneas.
 */
export function aplicar(sub = "") {
  const dir = sub ? path.join(base(), sub) : base();
  fs.mkdirSync(dir, { recursive: true });
  process.env.TMPDIR = dir;
  process.env.TEMP = dir;
  process.env.TMP = dir;
  sitio(dir);
  return barras(dir);
}

/**
 * Linea de comandos: `--exportar` escupe lo que `entorno.sh` mete en el shell,
 * para que la comprobacion viva en un solo sitio y no en dos idiomas.
 *
 * Se mira `process.argv[1]` y **no `import.meta`**: `remotion.config.ts` se
 * empaqueta con esbuild a CommonJS y se ejecuta con `eval`, donde `import.meta`
 * no existe. Escrito de la otra forma, importar esto reventaba el CLI entero.
 */
const invocado = (process.argv[1] ?? "")
  .split(path.sep)
  .join("/")
  .endsWith("scripts/temporal.mjs");
if (invocado) {
  const dir = aplicar();
  if (process.argv.includes("--exportar")) {
    for (const v of ["TMPDIR", "TEMP", "TMP"]) console.log(`export ${v}="${dir}"`);
  } else {
    const libre = libresGB(dir);
    console.log(
      `temporal: ${dir}` +
        (libre === null ? "" : `  (${libre.toFixed(1)} GB libres)`),
    );
  }
}
