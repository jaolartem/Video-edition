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
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { comprobar as comprobarCamara } from "./camara.mjs";
import { comprobar as comprobarEslabones } from "./eslabones.mjs";

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

/**
 * **Dos entradas con el mismo numero, y las citas que apuntan a ellas.**
 *
 * Lo pidio Jaime despues de fusionar dos ramas: *«cada C-NN citado en docs/
 * tiene que existir; es la misma idea que guardas.mjs ya aplica a los ficheros,
 * aplicada a los numeros»*.
 *
 * Y hay que mirar las dos cosas, porque la cara es la primera. Las dos ramas
 * partieron de un log que llegaba a C-81 y las dos escribieron un **C-82
 * distinto**: la colision existia antes de renumerar, y si hubiera fallado el
 * build ahi, no habria hecho falta perseguir punteros despues.
 *
 * Lo que hace cara a la segunda es lo que dijo el: *«no son enlaces muertos,
 * son enlaces a otra cosa que tambien parece plausible»*. Un puntero a C-82 que
 * sobrevive a la renumeracion sigue resolviendo — a la correccion equivocada, y
 * sin romper nada. Por eso la cita muerta se denuncia y la viva no se puede
 * comprobar sola: lo unico que la evita es no dejar que dos entradas compartan
 * numero.
 */
{
  const vistos = new Map();
  for (const e of entradas) {
    if (vistos.has(e.num)) {
      fallos.push(
        `C-${e.num} esta dos veces en el log: «${vistos.get(e.num)}» y ` +
          `«${e.titulo}». Renumera una y mueve lo que la cite: mientras ` +
          `compartan numero, cada puntero apunta a las dos.`,
      );
    }
    vistos.set(e.num, e.titulo);
  }

  const sitios = [LOG, path.join(RAIZ, "docs")];
  const ficheros = [];
  for (const sitio of sitios) {
    if (!fs.existsSync(sitio)) continue;
    if (fs.statSync(sitio).isDirectory()) {
      for (const f of fs.readdirSync(sitio)) {
        if (f.endsWith(".md")) ficheros.push(path.join(sitio, f));
      }
    } else ficheros.push(sitio);
  }
  for (const f of new Set(ficheros)) {
    const txt = fs.readFileSync(f, "utf8");
    for (const m of txt.matchAll(/C-(\d{2,3})/g)) {
      if (!vistos.has(m[1])) {
        fallos.push(
          `${path.relative(RAIZ, f)} cita C-${m[1]} y esa correccion no ` +
            `existe en el log.`,
        );
      }
    }
  }
}

/**
 * **Dos funciones con el mismo nombre en un fichero: la segunda tapa a la
 * primera y Python no dice nada.**
 *
 * `costuras.py` definia `palabras_enteras` dos veces —una saca el corte de
 * dentro de la palabra, la otra alarga la salida por sonido— y la segunda
 * borraba a la primera. Asi que la garantia «ningun corte cae dentro de una
 * palabra» **no corria ni en el paso ni en la puerta**: `revisada.LosCortes` la
 * pide por ese nombre y recibia la otra. `reel-03` llego a Jaime con tres
 * entradas cortadas a mitad de palabra y `costuras.py 3 --ver` contestaba cero.
 *
 * Es la averia de un fichero que crece: se anade al final y el nombre ya estaba
 * arriba, a trescientas lineas de donde se lee. No da error en ninguna parte —
 * solo deja de existir una de las dos.
 */
{
  const anda = (d) => {
    for (const f of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, f.name);
      if (f.isDirectory()) {
        if (f.name !== "__pycache__") anda(p);
        continue;
      }
      if (!f.name.endsWith(".py")) continue;
      const cuenta = new Map();
      for (const [, n] of fs.readFileSync(p, "utf8").matchAll(/^(?:def|class)[ \t]+([A-Za-z_]\w*)/gm))
        cuenta.set(n, (cuenta.get(n) ?? 0) + 1);
      for (const [n, c] of cuenta)
        if (c > 1)
          fallos.push(
            `${path.relative(RAIZ, p)} define «${n}» ${c} veces: la ultima ` +
              `tapa a las demas y quien la llame por ese nombre recibe otra ` +
              `cosa, sin error. Ponles nombres distintos.`,
          );
    }
  };
  anda(path.join(process.cwd(), "scripts"));
}

/**
 * **El rebote, que estaba prohibido por escrito y no lo miraba nadie.**
 *
 * *«Nada de rebote, confeti, wiggle ni micro-animación juguetona»* lleva en el
 * canon desde el principio, con su nombre, y es de las cinco que el proyecto
 * declara innegociables. Como todas las que sólo están escritas, se cumplía de
 * media: la comprobación no existía, así que un `Easing.back` en un componente
 * nuevo habría entrado sin que nadie se enterara hasta verlo en la entrega — y
 * el gancho ya enseñó lo que cuesta eso, cuatro instrucciones sobre la misma
 * lámina.
 *
 * Se busca por nombre y en el código, no en la prosa: los comentarios de
 * `Capas.tsx` y `Reparto.tsx` citan `Easing.back` **para prohibirlo**, y un
 * guarda que no distingue una cita de una llamada obliga a dejar de escribir el
 * porqué, que es lo contrario de lo que hace falta.
 *
 * `spring` no está prohibido: lo que rebota es un `spring` que se pasa de su
 * destino. Así que se admite con `overshootClamping: true` declarado, y sin eso
 * se dice — porque el valor por defecto es el que rebota.
 */
{
  const REBOTES = ["Easing.back", "Easing.elastic", "overshootClamping: false"];
  const sinProsa = (t) =>
    t.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/^[ \t]*\/\/.*$/gm, " ");
  const anda = (d) => {
    for (const f of fs.readdirSync(d, { withFileTypes: true })) {
      const p = path.join(d, f.name);
      if (f.isDirectory()) {
        anda(p);
        continue;
      }
      if (!/\.(tsx?|mjs)$/.test(f.name)) continue;
      const codigo = sinProsa(fs.readFileSync(p, "utf8"));
      const rel = path.relative(RAIZ, p).replace(/\\/g, "/");
      for (const r of REBOTES) {
        if (codigo.includes(r))
          fallos.push(
            `${rel} usa «${r}»: es rebote, y el canon lo prohíbe por nombre —` +
              ` «nada de rebote, confeti ni micro-animación juguetona». Esto es` +
              ` un asesor financiero hablando a dueños de negocio.`,
          );
      }
      for (const m of codigo.matchAll(/\bspring\s*\(/g)) {
        const trozo = codigo.slice(m.index, m.index + 320);
        if (!trozo.includes("overshootClamping: true"))
          fallos.push(
            `${rel} llama a \`spring(\` sin \`overshootClamping: true\`: por` +
              ` defecto se pasa de su destino y vuelve, que es rebote. Declara` +
              ` el tope o usa \`Easing.out\`, que es masa frenando.`,
          );
      }
    }
  };
  anda(path.join(process.cwd(), "src"));
}

/**
 * Y lo que se le OFRECE al diseñador también tiene que existir.
 *
 * Jaime: *« que no quede otra vez el mismo error de declarar sin implementar,
 * que ha sido la constante en este proyecto»*. Una corrección sin aguja y un
 * verbo ofrecido sin línea que lo consuma son la misma avería por dos puertas:
 * algo escrito que nadie ejecuta. Se comprueban en el mismo sitio.
 */
// Lo declarado en `cadena.py` que no corre nadie. El texto del fallo viene ya
// escrito de alli: quien sabe que falta sabe como decirlo.
for (const f of comprobarEslabones()) fallos.push(f);

for (const r of comprobarCamara())
  fallos.push(
    `camara.mjs ofrece «${r.verbo}» y ${r.fichero} ya no tiene ` +
      `«${r.aguja}»: el diseñador lo verá en su menú y no hará nada.`,
  );

console.log(
  `guardas: ${entradas.length} correcciones · ${comprobadas} agujas · ` +
  `${fallos.length ? `${fallos.length} ROTAS` : "todas en pie"}`,
);
for (const f of fallos) console.error(`  ${f}`);
// **Y queda fila.** Jaime: *«no solo necesito que pare, necesito un log»*.
// Parar se ve en la terminal de quien estaba mirando; el log es lo unico que
// deja verlo despues, y sobre todo cuantas veces — que es donde se nota la
// diferencia entre una guarda que salto una vez y una que lleva semanas
// saltando sin que nadie la mire.
//
// Por la CLI de `registro.py` y no con otro escritor: la tabla ya existe con
// 41.396 filas y 23 scripts escribiendo en ella, y un segundo camino hasta la
// misma tabla es la averia que este proyecto paga mas cara.
if (fallos.length) {
  spawnSync("python", [
    "scripts/registro.py", "--anota", "error", "guardas", "agujas rotas",
    `${fallos.length}: ${fallos.join(" | ")}`,
  ], { stdio: "ignore" });
  process.exit(1);
}
