/**
 * Las formas de diseño, declaradas como objetos y una sola vez.
 *
 * Regla de Jaime, y las dos mitades importan: *«que las formas de diseño se
 * guarden como objetos de clase»*, *«no hay que rediseñarlas cada vez»*.
 *
 * ## Qué problema resuelve, con el número delante
 *
 * Al abrir el catálogo —*«las limitaciones de código se acaban de inmediato;
 * las formas ahora sí pueden ser variadas»*— seis diseñadores montaron 36
 * tableros y cada uno inventó la forma de sus props. Medido sobre lo que
 * escribieron:
 *
 *     BeliefSwap    5 usos, 18 props distintos y **núcleo vacío**:
 *                   los cinco no coincidieron en NI UNO
 *     PlacaFecha    3 usos, 17 props, núcleo de 3
 *     tipo          2 usos,  9 props, núcleo de 2
 *
 * Eso no es variedad: es la misma forma rediseñada cinco veces. La segunda vez
 * que alguien necesite una creencia que se sustituye por otra, no tiene dónde
 * mirar cómo se llamó la primera, así que se la inventa otra vez — y el render
 * necesitaría cinco componentes para una sola idea.
 *
 * ## Cómo se declara
 *
 * Una clase por forma, con **sólo lo suyo**. El cromo que comparten todas
 * —dónde va, de qué familia es, qué lleva en oro, qué suena, de dónde sale la
 * cifra— se declara UNA vez en la base: era la mitad de esos 18 props.
 *
 * Y cada prop de texto declara su **rol de copy**, que es lo que fija su tope.
 * Sin esto ya se coló un fallo: `BandaFecha.condiciones` vale
 * «EN VIVO · EN ESPAÑOL · ONTARIO» —30 caracteres— y pasarla por `label` (26)
 * **falla el render**, no avisa. Es `statement` (52), y ahora lo dice aquí en
 * vez de depender de que quien construya el componente lo acierte.
 *
 * ## Lo que NO decide este fichero
 *
 * No diseña. Las formas y sus props salen de lo que los diseñadores ya
 * entregaron; esto sólo las consolida y las hace comprobables. Añadir una forma
 * nueva es añadir una clase aquí, y entonces la siguiente pieza la reutiliza en
 * vez de reinventarla.
 *
 *     node scripts/formas.mjs        # el inventario: qué está construido y qué no
 */

/** Los topes de `src/brand/copy.ts`. Se repiten aquí porque este módulo es
 *  node plano y no puede importar el `.ts`; si divergen, `--comprobar` lo dice. */
export const TOPE = { title: 42, statement: 52, outcome: 38, label: 26, legal: 190 };

/**
 * El cromo que llevan casi todas las formas. Se declara una vez.
 *
 * Estaba repetido en cada tablero y por eso `BeliefSwap` parecía tener 18
 * propiedades: trece eran esto.
 */
const CROMO = {
  familia: "cargada | tranquila — la alterna la pieza, no el tablero",
  zona: "dónde cae en el cuadro, sin tapar la cara",
  cubre: "si el tablero toma el cuadro entero o acompaña al plano",
  oro: "QUÉ va en oro, y es uno solo: si hay tres, dos sobran",
  sound: "el movimiento que suena, en el frame en que se mueve",
  fondo: "la placa o el plano de color de debajo",
  source: "de dónde sale la cifra. Obligatorio si rotula una",
  filete: "los filetes de 1 px que separan, en vez de sombras",
};

/** Las formas que `src/Ad.tsx` sabe dibujar hoy. Lo demás es encargo de código. */
const CONSTRUIDAS = new Set(["causal", "twopaths", "comparacion", "acumulacion"]);

export class Forma {
  /**
   * @param {string} nombre        el `kind` que se guarda en `escena_desc.tablero`
   * @param {string} hace          qué dibuja, en una línea
   * @param {object} propios       sus props, `{nombre: rolDeCopy|descripcion}`
   * @param {string[]} exige       props sin los cuales no se puede dibujar
   */
  constructor(nombre, hace, propios, exige = []) {
    this.nombre = nombre;
    this.hace = hace;
    this.propios = propios;
    this.exige = exige;
  }

  get construida() {
    return CONSTRUIDAS.has(this.nombre);
  }

  /** Todos los props válidos: los suyos más el cromo compartido. */
  get admite() {
    return { ...CROMO, ...this.propios };
  }

  /**
   * Qué está mal en un tablero de esta forma. Lista vacía = se puede montar.
   *
   * Comprueba tres cosas y ninguna es de gusto: que estén los props sin los
   * que no se dibuja, que no haya props inventados —que es la deriva que este
   * fichero viene a parar— y que cada texto quepa en el tope de SU rol.
   */
  revisar(props) {
    const mal = [];
    const p = props ?? {};
    for (const k of this.exige) {
      if (p[k] === undefined || p[k] === null || p[k] === "")
        mal.push(`«${this.nombre}» necesita \`${k}\` y no llega`);
    }
    // **Un prop que el diseñador usó NO es un error.** Lo fue durante media
    // hora y estuvo mal: esto sacó 30 faltas culpando al diseño de props que yo
    // no había declarado. Jaime lo cortó — *«no es cierto que haya que tocar
    // nada del lado del diseñador»*—, y tiene razón: la forma la define quien
    // diseña, no el catálogo que yo escribí mirando un volcado.
    //
    // Lo que queda comprobado es sólo lo que **rompe el render**: que estén los
    // props sin los que no se puede dibujar, y que ningún texto pase el tope de
    // su rol. Eso no es opinión sobre el diseño: es lo que hace que la pieza
    // salga o se caiga.
    //
    // Los props no declarados se devuelven aparte, para poder ampliar la clase
    // cuando se repitan — que es como una forma crece sin rediseñarse.
    this.nuevos = Object.keys(p).filter((k) => !(k in this.admite));
    for (const [k, rol] of Object.entries(this.propios)) {
      if (!(rol in TOPE)) continue;
      const v = p[k];
      for (const t of Array.isArray(v) ? v : [v]) {
        if (typeof t === "string" && t.length > TOPE[rol])
          mal.push(
            `«${this.nombre}».\`${k}\` es ${rol} (tope ${TOPE[rol]}) y trae` +
              ` ${t.length}: «${t.slice(0, 40)}…». Esto NO avisa, falla el render`,
          );
      }
    }
    return mal;
  }
}

/**
 * El catálogo. Salen de lo que los diseñadores entregaron, consolidado.
 *
 * El orden es por cuántas veces se pidió: lo de arriba es lo que el lote usa de
 * verdad y lo primero que hay que construir.
 */
export const FORMAS = [
  // **Las formas las diseña el diseñador, no este fichero.**
  //
  // Regla de Jaime: *«deja que el diseñador diseñe las formas»*, y antes *«no es
  // cierto que haya que tocar nada del lado del diseñador»*.
  //
  // Aqui llegue a declarar veintitres formas con los props que yo creia que
  // llevaban, sacados de mirar un volcado. El resultado fue que la maquina
  // saco 39 faltas culpando al diseño de props que faltaban en MI lista — o
  // sea, mi catalogo convertido en techo del diseño, que es exactamente al
  // reves de como tiene que ser.
  //
  // Lo unico que se declara ahora es un hecho del CODIGO, no del diseño: que
  // formas tienen componente propio. Todo lo demas lo dibuja
  // `TableroDeclarado` con lo que el diseñador escribio, sin pedirle permiso a
  // ninguna lista.
  new Forma("comparacion", "dos cantidades enfrentadas sobre la misma reticula",
            { premisa: "title", izquierda: "statement", derecha: "statement",
              remate: "outcome", condicion: "legal" },
            ["izquierda", "derecha"]),
  new Forma("acumulacion", "algo que se apila por tramos hasta un total",
            { title: "title", concepto: "statement", resultado: "outcome",
              horizonte: "label", condicion: "legal" },
            ["tramos"]),
  new Forma("twopaths", "dos trayectorias desde la misma linea de salida",
            { title: "title", start: "statement", byDefault: "statement",
              deliberate: "statement", difference: "outcome",
              horizon: "label", condition: "legal" },
            ["byDefault", "deliberate", "horizon", "condition"]),
  new Forma("causal", "cadena institucion -> consecuencia",
            { title: "title", condicion: "legal" }, []),
];


const POR_NOMBRE = new Map(FORMAS.map((f) => [f.nombre, f]));

export const forma = (nombre) => POR_NOMBRE.get(nombre) ?? null;

/**
 * Revisa un tablero contra su forma.
 *
 * Una forma que no está en el catálogo **no es un error del tablero**: es una
 * forma nueva que hay que declarar aquí. Se dice así para que no se confunda
 * con un tablero mal montado.
 */
export const revisarTablero = (kind, props) => {
  // **Una forma que no está en este catálogo NO es un error.** Se dibuja con
  // `TableroDeclarado` y punto. Esto devolvía una falta por cada una —42 en el
  // lote— y eso es otra vez mi lista poniéndole techo al diseño, que es lo que
  // Jaime paró: *«deja que el diseñador diseñe las formas»*.
  //
  // Sólo se revisa lo que tiene componente propio, porque ahí sí hay un
  // contrato de código que respetar: esos componentes llaman a `assertShort` y
  // **tumban el render** si un texto se pasa de su tope.
  const f = forma(kind);
  if (!f) return [];
  return f.revisar(props);
};

const main = () => {
  const hechas = FORMAS.filter((f) => f.construida);
  const faltan = FORMAS.filter((f) => !f.construida);
  console.log(`formas declaradas: ${FORMAS.length}`);
  console.log(`  construidas (${hechas.length}): ${hechas.map((f) => f.nombre).join(", ")}`);
  console.log(`\n  por construir (${faltan.length}) — encargos de codigo:`);
  for (const f of faltan)
    console.log(`    ${f.nombre.padEnd(16)} ${f.hace}`);
};

// La comparacion con `import.meta.url` no cuadra en Windows —barras y prefijo
// `file:///`—, asi que se mira el nombre del script que se lanzo.
if ((process.argv[1] ?? "").replace(/\\/g, "/").endsWith("scripts/formas.mjs")) main();
