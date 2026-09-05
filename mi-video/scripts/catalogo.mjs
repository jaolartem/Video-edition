/**
 * El catálogo indexado de piezas visuales, **leído de los componentes**.
 *
 * Jaime, al ver que se le mandaba una lista de primitivas escrita a mano:
 * *«bueno, todas ésas están más o menos mal; tiene que revisarlas, arreglarlas y
 * actualizarlas, además de dejarlas guardadas y ordenadas como clases… es decir,
 * es un catálogo indexado, o ésa era mi intención con esos elementos. No sé por
 * qué nunca se utilizó.»*
 *
 * La respuesta a por qué nunca se utilizó: **nadie lo indexaba**. Los veinte
 * componentes de `src/components/` existían, cada uno con su propósito escrito
 * en su cabecera, y ningún paso los leía. El diseñador componía sin saber qué
 * piezas tenía, así que pedía cosas que no existen y no pedía las que sí.
 *
 * ## Por qué se lee y no se escribe
 *
 * Una lista de componentes escrita a mano es una segunda copia: el día que
 * alguien añade un componente, el catálogo no se entera y sigue prometiendo lo
 * de antes. Aquí el índice **es** la carpeta — se leen los ficheros, se saca la
 * primera línea de su cabecera y se agrupan por clase.
 *
 * Lo único declarado a mano son las CLASES, porque eso sí es una decisión: qué
 * familia de trabajo hace cada pieza. Y `sinClase()` denuncia al componente que
 * no está en ninguna, para que un componente nuevo no se quede fuera en
 * silencio.
 *
 *   node scripts/catalogo.mjs           # el índice, legible
 *   node scripts/catalogo.mjs --json    # el índice, para el contrato
 */
import fs from "node:fs";
import path from "node:path";

const DIR = "src/components";

/**
 * Las clases y su orden de composicion. **Los nombres son lo unico declarado**
 * —son cinco palabras del dominio, no datos— y quien pertenece a cada una lo
 * dice el propio componente con `@clase` en su cabecera.
 *
 * Jaime: *«si trabajamos con POO lo obvio es no escribir o dejar nada a mano»*.
 * Aqui habia la lista de los veinte repartida por clase, escrita en este
 * fichero: una segunda copia que se desviaba el dia que alguien anadiera un
 * componente. Ahora el objeto declara lo que es y esto solo lo recoge.
 */
export const ORDEN = {
  tablero: "ocupa el cuadro y explica",
  capa: "se apila sobre el plano",
  transicion: "media entre dos cosas",
  superficie: "lo que hay debajo",
  sistema: "se usa dentro de las demas",
};

/** Lo que un componente declara de si mismo: su clase y lo que hace. */
const ficha = (fichero) => {
  const t = fs.readFileSync(path.join(DIR, fichero), "utf8");
  const clase = t.match(/@clase\s+(\w+)/);
  // La primera linea de prosa de la cabecera, saltandose las etiquetas `@`:
  // sin eso, un componente cuya cabecera empieza por `@clase` se describia a si
  // mismo como «@clase capa», que es decir nada.
  const cabecera = (t.match(/\/\*\*([\s\S]*?)\*\//) || [, ""])[1]
    .split("\n")
    .map((l) => l.replace(/^\s*\*\s?/, "").trim())
    .find((l) => l && !l.startsWith("@"));
  return {
    clase: clase ? clase[1] : null,
    hace: cabecera || "",
  };
};

/** Los componentes que hay en disco, sin extensión. */
export const piezas = () =>
  fs.readdirSync(DIR).filter((f) => f.endsWith(".tsx")).map((f) => f.slice(0, -4));

/**
 * Las SUBCLASES: los `.tsx` que viven dentro de la carpeta de un componente.
 *
 * Jaime, al ver que `Corregida` —la pieza que enfatiza el dato bueno sobre la
 * palabra mal dicha— no aparecia por ninguna parte: *«se debe ajustar a cada
 * video para que se ajuste a la logica, pero ahi ya hay una clase o subclase»*.
 *
 * Y la relacion **no se declara: la declara la carpeta**. `captionBand/Corregida`
 * es una subclase de `CaptionBand` porque esta dentro de su carpeta, punto. Es
 * la misma regla que `@clase` —el objeto dice lo que es, esto solo lo recoge—
 * y evita el tag a mano que se desviaria el dia que alguien mueva un fichero.
 *
 * Nueve piezas vivian aqui sin llegar al disenador. `Corregida` es la que lo
 * hizo evidente: existe, la dibuja el render, y quien componia el grafico no
 * podia saber que estaba.
 */
export const subclases = () => {
  const fuera = {};
  for (const d of fs.readdirSync(DIR, { withFileTypes: true })) {
    if (!d.isDirectory()) continue;
    const hijos = fs
      .readdirSync(path.join(DIR, d.name))
      .filter((f) => f.endsWith(".tsx"));
    if (!hijos.length) continue;
    // El padre es el componente con el nombre de la carpeta, en mayuscula
    // inicial: `captionBand/` -> `CaptionBand`.
    const padre = d.name[0].toUpperCase() + d.name.slice(1);
    fuera[padre] = Object.fromEntries(
      hijos.map((f) => [f.slice(0, -4), ficha(`${d.name}/${f}`).hace]),
    );
  }
  return fuera;
};

/**
 * El indice: clase -> pieza -> lo que hace. Todo leido, nada escrito.
 *
 * `sin_clase` son los componentes que no declaran `@clase`. No es un aviso
 * decorativo: un componente sin clase no llega al disenador, asi que es una
 * pieza construida que nadie puede pedir — que es lo que le paso a este
 * catalogo entero.
 *
 * `sin_decir_que_hace` son los que no tienen primera linea de cabecera. Estan
 * en el indice pero llegan mudos, y eso hay que arreglarlo pieza a pieza segun
 * se vayan tocando.
 */
export const catalogo = () => {
  const idx = {};
  const sinClase = [];
  const mudos = [];
  for (const n of Object.keys(ORDEN)) idx[n] = {};
  for (const nombre of piezas()) {
    const f = ficha(`${nombre}.tsx`);
    if (!f.clase || !(f.clase in idx)) {
      sinClase.push(nombre);
      continue;
    }
    if (!f.hace) mudos.push(nombre);
    idx[f.clase][nombre] = f.hace;
  }
  return {
    clases: ORDEN,
    indice: idx,
    // Las variantes de cada familia: `CaptionBand` tiene Plana, Compuesta y
    // Corregida, y elegir entre ellas es composicion, no implementacion.
    subclases: subclases(),
    sin_clase: sinClase,
    sin_decir_que_hace: mudos,
  };
};

// Solo cuando se ejecuta directamente. `process.argv[1]` no existe si el
// modulo se importa desde `node -e`, y sin la guarda eso revienta al importar.
const _directo =
  process.argv[1] && import.meta.url.endsWith(path.basename(process.argv[1]));
if (_directo) {
  const c = catalogo();
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify(c, null, 1));
  } else {
    for (const [clase, piezas_] of Object.entries(c.indice)) {
      console.log(`\n${clase}`);
      for (const [n, q] of Object.entries(piezas_)) {
        console.log(`  ${n.padEnd(18)} ${q}`);
      }
    }
    for (const [padre, hijos] of Object.entries(c.subclases)) {
      console.log(`
${padre} — variantes`);
      for (const [n, q] of Object.entries(hijos)) {
        console.log(`  ${n.padEnd(18)} ${q}`);
      }
    }
    if (c.sin_clase.length) {
      console.log(`\nSIN CLASE — ${c.sin_clase.length}: ${c.sin_clase.join(", ")}`);
      console.log("  Un componente sin clase no llega al disenador.");
    }
    if (c.sin_decir_que_hace.length) {
      console.log(`\nMUDOS — ${c.sin_decir_que_hace.length}: `
        + c.sin_decir_que_hace.join(", "));
      console.log("  Estan en el indice pero no dicen que hacen:"
        + " se arregla al tocarlos.");
    }
  }
}
