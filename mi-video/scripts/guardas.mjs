#!/usr/bin/env node
/**
 * **La guarda de las correcciones.**
 *
 * Regla de Jaime: *«cada corrección y error tiene que quedar en un log, y
 * dentro del mecanismo; las correcciones son estructurales»*. Y la columna que
 * decide si una entrada está cerrada es la del mecanismo: **si no apunta a un
 * fichero, la corrección no está hecha.**
 *
 * Hasta ahora eso era una convención de escritura, y una convención no
 * sobrevive a una reescritura. Ya pasó: el aprendizaje 3 —intersecar el EDL con
 * los tramos de habla— llevaba semanas documentado y se perdió al sustituir el
 * script donde vivía (C-02). El texto seguía ahí, correcto y muerto.
 *
 * Esto lo convierte en una comprobación. Cada entrada `### C-NN` de
 * `docs/correcciones.md` declara su guarda:
 *
 *     **Guarda.** `mi-video/scripts/beats.py` :: `def deBeat(`
 *
 * y aquí se verifica que el fichero existe y que la aguja sigue dentro. Dos
 * cosas fallan el build, no avisan:
 *
 * 1. **Una guarda rota** — alguien reescribió el fichero y se llevó el
 *    mecanismo por delante. Es exactamente C-02.
 * 2. **Una entrada sin guarda** — es una corrección contada, no hecha. Escribir
 *    el síntoma es la mitad barata del trabajo.
 *
 * La aguja se busca **literal**, no por regex: tiene que ser un trozo de código
 * que no se pueda escribir por casualidad —un nombre de función, una constante—
 * y no una frase del comentario, que se reescribe sin tocar la lógica.
 *
 *   node scripts/guardas.mjs
 */
import fs from "node:fs";
import path from "node:path";

const RAIZ = path.resolve(process.cwd(), "..");
const LOG = path.join(RAIZ, "docs/correcciones.md");

const texto = fs.readFileSync(LOG, "utf8");

/**
 * Cada entrada, con su número, su título y su cuerpo.
 *
 * **Se acepta `##` y `###`.** El log arrancó con `###` y desde C-77 se escribió
 * con `##`. Partiendo sólo por `###`, esas seis entradas no desaparecían —sus
 * agujas caían dentro del cuerpo de la entrada anterior y sí se comprobaban—
 * pero **se contaban y se reportaban con el número equivocado**: el verificador
 * decía «53 correcciones» habiendo 82, y una guarda rota de C-81 salía en
 * pantalla como «C-53». Un informe que señala la entrada que no es manda a
 * mirar el fichero que no es.
 *
 * El filtro de verdad no es el número de almohadillas, es que el título sea
 * `C-NN`; los encabezados de fecha caen solos.
 */
const entradas = [];
// `###` o `##`: el log usa los dos niveles y mirar solo uno dejaba 28
// entradas sin comprobar —y, peor, pegaba sus guardas al bloque anterior, asi
// que una rotura de C-81 se denunciaba como rotura de C-53.
for (const bloque of texto.split(/^#{2,3} /m).slice(1)) {
  const salto = bloque.indexOf("\n");
  const titulo = bloque.slice(0, salto).trim();
  const num = titulo.match(/^C-(\d+)/)?.[1];
  if (num) entradas.push({ num, titulo, cuerpo: bloque.slice(salto) });
}

/**
 * `ruta :: aguja` — tiene que estar. `ruta !: aguja` — **no puede estar**.
 *
 * La negativa hace falta para las correcciones que consisten en quitar algo:
 * C-15 no se cierra comprobando que `assemble.py` lleva un aviso, sino que
 * nadie lo ha vuelto a enganchar a la cadena viva. Una guarda que sólo sabe
 * mirar lo que hay no puede vigilar lo que se decidió no tener.
 */
const PAR = /`([^`]+)`\s*(::|!:)\s*`([^`]+)`/g;
const fallos = [];
let comprobadas = 0;

for (const e of entradas) {
  const linea = e.cuerpo
    .split("\n")
    .filter((l) => l.startsWith("**Guarda.**"))
    .join(" ");
  if (!linea) {
    fallos.push(`C-${e.num} no declara guarda. Una corrección sin fichero que ` +
      `la sostenga es una corrección contada, no hecha.`);
    continue;
  }
  const pares = [...linea.matchAll(PAR)];
  if (!pares.length) {
    fallos.push(`C-${e.num} declara guarda pero no se le entiende. La forma es ` +
      "`ruta` :: `aguja`.");
    continue;
  }
  for (const [, rel, signo, aguja] of pares) {
    comprobadas += 1;
    const f = path.join(RAIZ, rel);
    if (!fs.existsSync(f)) {
      fallos.push(`C-${e.num}: ${rel} no existe. El mecanismo vivía ahí.`);
      continue;
    }
    const hay = fs.readFileSync(f, "utf8").includes(aguja);
    if (signo === "::" && !hay) {
      fallos.push(
        `C-${e.num}: ${rel} ya no contiene «${aguja}». O el mecanismo se ` +
        `perdió en una reescritura, o cambió de nombre y la guarda está vieja ` +
        `— las dos cosas hay que mirarlas, ninguna se arregla sola.`,
      );
    }
    if (signo === "!:" && hay) {
      fallos.push(
        `C-${e.num}: ${rel} ha vuelto a contener «${aguja}», y esa corrección ` +
        `consistía precisamente en no tenerlo.`,
      );
    }
  }
}

/**
 * **C-44 en codigo, y no como disciplina.** Su guarda declaraba una aguja con
 * un salto de linea literal dentro, que el parser no puede leer: llevaba desde
 * entonces sin comprobar nada y solo se vio hoy, cuando otra guarda dejo de
 * fallar y esta salio detras.
 *
 * Lo que la correccion pedia es que `asignar.wf.js` no acabe en CRLF — el
 * lanzador de workflows rechaza el retorno de carro como caracter de control.
 * El resto del repo si es CRLF y da igual; esto es solo para ese fichero.
 */
{
  const f = "scripts/asignar.wf.js";
  if (fs.existsSync(f) && fs.readFileSync(f, "utf8").includes(String.fromCharCode(13))) {
    fallos.push(
      `C-44: ${f} volvio a tener retornos de carro. El lanzador de workflows ` +
        `los rechaza como caracteres de control — se escribe con newline "
".`,
    );
  }
}

console.log(
  `guardas: ${entradas.length} correcciones · ${comprobadas} agujas · ` +
  `${fallos.length ? `${fallos.length} ROTAS` : "todas en pie"}`,
);
for (const f of fallos) console.error(`  ${f}`);
if (fallos.length) process.exit(1);
