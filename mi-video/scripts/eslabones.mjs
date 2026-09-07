/**
 * **Lo declarado tiene que producirlo alguien.**
 *
 * `cadena.py` declara los trece eslabones de la linea con el script que produce
 * cada uno. Dos de ellos —`huecos` y `trasfondo`, las dos entradas del spec—
 * estuvieron declarados durante dias y **ninguna linea los ejecutaba**: el spec
 * se comia el fichero que hubiera en disco, de otro montaje o de ninguno.
 *
 * Es la misma averia que una aguja rota y que un verbo ofrecido al disenador sin
 * implementacion, y por eso lo cuenta `guardas.mjs` en el mismo sitio: algo
 * escrito que nadie ejecuta. Vive aparte porque es otra responsabilidad —y
 * porque el techo de 300 lineas es un contrato (C-154).
 *
 * Se mira que el productor **aparezca** en la linea, no que funcione: eso lo
 * dice el montaje. Los productores sin extension —«revision --aplicar», que es
 * prosa— se saltan, igual que hace `cadena.py :: _codigo`.
 */
import fs from "node:fs";
import path from "node:path";

// **La raiz se resuelve como en `guardas.mjs`, desde el cwd.** Con
// `import.meta.url` la ruta llega **con los espacios en %20** —este proyecto
// vive en «F:/Edicion de video»— y el fichero no existe con ese nombre: es el
// gotcha 1 del proyecto por la puerta de Node.
const RAIZ = path.resolve(process.cwd(), "..");

export const comprobar = () => {
  const cadena = fs.readFileSync(path.join(RAIZ, "mi-video/scripts/cadena.py"), "utf8");
  const linea =
    fs.readFileSync(path.join(RAIZ, "mi-video/scripts/montar.sh"), "utf8") +
    fs.readFileSync(path.join(RAIZ, "mi-video/scripts/montar-lote.sh"), "utf8") +
    fs.readFileSync(path.join(RAIZ, "mi-video/scripts/dominio/fase.py"), "utf8");
  const sueltos = [];
  // Los eslabones se declaran como tuplas: (nombre, artefacto, quien, come_de).
  for (const [, nombre, quien] of cadena.matchAll(
    /\(\s*"([a-z]+)",\s*"[^"]+",\s*"([^"]+)"/g,
  )) {
    for (const parte of quien.split("·")) {
      const script = parte.trim().split(/\s+/)[0];
      if (!script.includes(".")) continue;
      if (!linea.includes(script))
        sueltos.push(
          `cadena.py declara el eslabon «${nombre}» y lo produce ${script}, ` +
            `que no lo llama ni montar.sh ni el ciclo de fases. Declarado y no ` +
            `producido: lo que lo consuma se comera el fichero de otro montaje.`,
        );
    }
  }
  return sueltos;
};
