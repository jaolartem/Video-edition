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

import fs from "node:fs";
import { cerrada } from "./biblioteca.mjs";
import { camposDe, piezas } from "./catalogo.mjs";
import { CLIPS, faltasDeApoyo } from "./reels/apoyo.mjs";
import { faltasDePalote } from "./reels/palote.mjs";
import { faltasDeTarjeta } from "./reels/tarjeta.mjs";

const DIR_C = "src/components";

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
  volumen: "la animación 3D del panel. **RETIRADA desde el 6-9-2026**: la"
    + " biblioteca está cerrada —«hasta que no tengamos una biblioteca de"
    + " figuras decentes no las vamos a utilizar»— y declararla es lo que ahora"
    + " para la pieza. El panel lleva el dato o la letra",
  oro: "QUÉ va en oro, y es uno solo: si hay tres, dos sobran",
  sound: "el movimiento que suena, en el frame en que se mueve",
  fondo: "la placa o el plano de color de debajo",
  source: "de dónde sale la cifra. Obligatorio si rotula una",
  filete: "los filetes de 1 px que separan, en vez de sombras",
  sujeto: "izquierda | derecha: de qué lado va su recorte. La lámina se encoge a"
    + " la otra columna. Obligatorio a pleno si la pieza es `cara: siempre`",
  sujeto_forma: "pegatina (papel rasgado, collage) | cuadro (retrato formal,"
    + " canto limpio sobre navy). Por defecto, pegatina",
  sujeto_color: "bn | sepia | color. Si no se dice, lo decide el arco"
    + " (`escena_desc.color`)",
};

/** Las formas que `src/Ad.tsx` sabe dibujar hoy. Lo demás es encargo de código. */
/**
 * Las que tienen componente propio, **leidas de quien las despacha**.
 *
 * Esto era una lista escrita a mano, y habia otra igual en `reels/base.mjs`
 * (`DIBUJA`) y una tercera implicita en el ternario de `Ad.tsx`. Tres copias de
 * la misma verdad: al construir `BeliefSwap` y `Compuerta` se actualizaron dos
 * y la tercera siguio diciendo «sale con TableroDeclarado» de dos formas que ya
 * se dibujaban. Jaime: *«si trabajamos con POO lo obvio es no escribir o dejar
 * nada a mano»*.
 *
 * Ahora se saca del propio `Ad.tsx`: si esta en el despacho, esta construida.
 * Anadir un componente lo pone en la lista sin tocar la lista.
 */
/**
 * El rol de copy de cada prop, **leido de los `assertShort` que lo aseguran**.
 *
 * Un rol escrito aqui y otro en el componente son dos tallas para el mismo
 * texto, y la que decide es siempre la del componente porque es la que aborta
 * el render. Leyendolo, la lista no puede desviarse de lo que se dibuja.
 */
const ROLES = (() => {
  const fuera = {};
  const dirs = [DIR_C, ...fs.readdirSync(DIR_C, { withFileTypes: true })
    .filter((d) => d.isDirectory()).map((d) => `${DIR_C}/${d.name}`)];
  for (const d of dirs) {
    for (const f of fs.readdirSync(d).filter((x) => x.endsWith(".tsx"))) {
      const src = fs.readFileSync(`${d}/${f}`, "utf8");
      for (const m of src.matchAll(
        /assertShort\([^,]+,\s*"([a-z]+)",\s*"([A-Za-z]+)\.([a-zA-Z_]+)"/g,
      )) {
        const [, rol, forma, prop] = m;
        const clave = forma.charAt(0).toLowerCase() + forma.slice(1);
        for (const k of [forma, clave]) (fuera[k] ??= {})[prop] = rol;
      }
    }
  }
  return fuera;
})();

/**
 * **Y se lee del despachador, no de `Ad.tsx`.**
 *
 * Leía `src/Ad.tsx`, que es donde estaba el ternario. El día que `Ad.tsx` pasó
 * del techo de 300 líneas el despacho se mudó a `components/Tablero.tsx`, y con
 * la ruta escrita a fuego esto habría devuelto un conjunto **vacío**: el parte
 * habría mandado a construir las once formas que ya se dibujan, justo el día en
 * que se acabaron de construir. Es la misma verdad copiada, esta vez por la
 * puerta de la ruta.
 */
export const CONSTRUIDAS = new Set(
  [...fs.readFileSync(`${DIR_C}/Tablero.tsx`, "utf8")
      .matchAll(/cue\.kind === "([^"]+)"/g)].map((m) => m[1]),
);

/**
 * **El nombre de la forma, como lo despacha `Tablero.tsx`.** «Comparacion» con
 * mayúscula no es `comparacion` para el despacho y caía en `TableroDeclarado`,
 * que rotula sus datos; y `Gancho` es el rótulo del gancho, o sea `tipo`
 * (reel-08 v1, 12-9, C-422). Vive aquí, junto a `CONSTRUIDAS`, porque la usan
 * el montaje y la puerta de `describir` (C-547).
 */
export const canonico = (k) => {
  const s = String(k ?? "");
  if (s.toLowerCase() === "gancho") return "tipo";
  return [...CONSTRUIDAS].find((d) => d.toLowerCase() === s.toLowerCase()) ?? s;
};

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

  /**
   * Todos los props validos: los suyos, el cromo compartido, y **el rol de copy
   * que asegura el propio componente**, que manda sobre lo escrito aqui.
   *
   * `Acumulacion.concepto` estaba declarado `statement` (52) y el componente lo
   * asegura como `label` (26): el disenador validaba contra esta lista, pasaba,
   * y el render moria en el frame 581 con 37 caracteres. Dos declaraciones del
   * mismo rol y la que no dibuja ganando la validacion.
   *
   * Jaime: *«la idea es que no haya redundancias ni en el modelo ni en el
   * codigo»*. La que dibuja es la fuente; esta lista dice QUE props hay, no de
   * que talla son.
   */
  get admite() {
    return { ...CROMO, ...this.propios, ...(ROLES[this.nombre] ?? {}) };
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
    // **`admite`, no `propios`.** El tope se comprobaba contra la lista escrita
    // a mano y no contra el rol que asegura el componente, asi que un texto
    // podia pasar la revision y tumbar el render: `acumulacion.concepto` estaba
    // aqui como `statement` (52), el componente lo asegura como `label` (26), y
    // 37 caracteres mataron el lote en el frame 581 con seis piezas sin salir.
    for (const [k, rol] of Object.entries(this.admite)) {
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
  // **El B-roll propio: la voz sigue y la imagen es un clip.** No es un
  // gráfico, pero ocupa el plano igual que uno y se elige con el mismo mando.
  new Forma("Apoyo", "un clip propio de la biblioteca de apoyo bajo la voz:"
            + " Alfred en pantalla, el guion escrito… en marcha, nunca congelado",
            { clip: "el id del clip. Los que hay: " + (Object.entries(CLIPS)
                .map(([k, c]) => `\`${k}\` (${c.muestra})`).join("; ") || "ninguno todavía"),
              forma: "completo | panel | amplia. Sin decirlo, panel si el clip es vertical y el"
                + " cuadro no. `amplia` (C-696): el clip arranca DENTRO del monitor que se ve en el"
                + " plano y crece al cuadro entero —«mira al computador y la pantalla se amplía»—;"
                + " sólo donde la cinta declara su monitor (rutas.json → monitores) y el sitio lo"
                + " pone el spec. Con amplia, opcionales `espera` (fotogramas quieto en el"
                + " monitor, 12) y `crece` (fotogramas hasta llenar el cuadro, 20)",
              fondo_clip: "sólo con amplia (C-704): el PLANO es otro clip de la biblioteca —uno"
                + " con `monitor` y `recorte` declarados, p. ej. él girándose a cámara y"
                + " mirando al monitor— y la pantalla nace del monitor de ese clip. La voz"
                + " sigue siendo la del corte; `espera` es el fotograma en que mira al monitor",
              etiqueta: "label" },
            ["clip"]),
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
  // **Las dos que se construyeron con lo que ya habia.** Jaime: *«que utilicen
  // los fondos que ya existen, para generar texto encima de ellos, como lo
  // muestran los ejemplos de carruseles; no es reinventar la rueda, es seguir
  // la identidad grafica»*. Ninguna dibuja geometria propia: componen `Cinta`,
  // `Marco` y `Fondo` sobre una placa de `public/fondos/`.
  new Forma("BeliefSwap", "la creencia se tacha y la verdad entra en oro",
            { creencia: "statement", verdad: "statement", condicion: "legal" },
            ["creencia", "verdad"]),
  new Forma("Compuerta", "lo que entra, lo que atraviesa y lo que sale distinto",
            { entra: "outcome", compuerta: "label", sale: "outcome",
              condicion: "legal" },
            ["entra", "compuerta", "sale"]),
  // **Cuantas hay de un lado y cuantas del otro, contadas en marcas.** No es
  // `comparacion`: alli hay dos cifras que leer y restar, y aqui la asimetria se
  // ve sin contar nada. Tampoco `acumulacion`, que apila hacia un total.
  //
  // **Y `cuantos` se exige.** Hasta el 6-9-2026 el componente dibujaba las que
  // cupieran —63— y eso AFIRMABA una abundancia que nadie habia declarado. Jaime:
  // *«en ingles no hay tantos, hay como cinco o seis»*. Una cantidad dibujada es
  // una cifra rotulada con otra forma, asi que la escribe quien compone.
  new Forma("Recuento", "cuantas marcas hay de un lado y cuantas del otro",
            { titulo: "title", muchos: "label", uno: "label",
              cuantos: "cuantas marcas van bajo `muchos`. Una cantidad dibujada AFIRMA igual que una cifra: se declara, y sin ella falla el render",
              condicion: "para quien esta hecho lo que hay: va bajo las marcas, un renglon por linea",
              cierre: "el contraste con el que se cierra el tramo: va abajo, un renglon por linea",
              entrada: "el movimiento, para quien compone; no se dibuja" },
            ["muchos", "uno", "cuantos"]),
  // **Una cifra sola, cuando el dato NO tiene forma.** Es la otra mitad de
  // «graficos y palabras»: una tasa marginal es un numero, la condicion que lo
  // produce y el tramo donde vale — tres textos, ninguna proporcion. Dibujarla
  // como barras obliga a inventar el reparto, que es afirmar una cantidad que
  // ninguna fuente sostiene (tiquet #215).
  //
  // `alcance` se EXIGE, y es cumplimiento y no estilo: «53,53 %» sin «marginal,
  // solo sobre el ultimo tramo» se lee como lo que se paga sobre todo lo que se
  // gana, que es otra afirmacion.
  new Forma("Techo", "una cifra sola, con su condicion arriba y su alcance debajo",
            { titulo: "label", cifra: "outcome", alcance: "statement" },
            ["titulo", "cifra", "alcance"]),
  new Forma("comparacion", "dos cantidades enfrentadas sobre la misma reticula",
            { premisa: "title", izquierda: "statement", derecha: "statement",
              remate: "outcome", condicion: "legal" },
            ["izquierda", "derecha"]),
  // **Con `umbral`, cada tramo trae su `valor`.** Una raya rotulada con una
  // cifra convierte la columna en una escala en esa unidad: cada `alto` afirma
  // cuanto puso ese tramo y el cruce afirma en cual se paso. Son mediciones, y
  // una cantidad dibujada afirma igual que una cifra rotulada — la misma regla
  // que `Recuento.cuantos`. Sin `valor` el render muere: cuatro fracciones
  // inventadas que suman 1 dibujaron en reel-05 e6 un cruce que ninguna fila de
  // `dato` sostiene (tiquet #217). Sin `umbral` la barra solo reparte un total,
  // y el total es el `resultado` rotulado con su fuente.
  new Forma("acumulacion", "algo que se apila por tramos hasta un total",
            { title: "title", concepto: "statement", resultado: "outcome",
              horizonte: "label", condicion: "legal",
              tramos: "los escalones, `{etiqueta, alto}`. Con `umbral` cada uno"
                + " lleva ademas `valor` —cuanto es, en la unidad de la raya—:"
                + " sin el, las alturas afirman una medida que nadie declaro y"
                + " falla el render" },
            ["tramos"]),
  new Forma("twopaths", "dos trayectorias desde la misma linea de salida",
            { title: "title", start: "statement", byDefault: "statement",
              deliberate: "statement", difference: "outcome",
              horizon: "label", condition: "legal" },
            ["byDefault", "deliberate", "horizon", "condition"]),
  new Forma("causal", "cadena institucion -> consecuencia",
            { title: "title", condicion: "legal" }, []),
  // **El panel con el dentro.** Es la unica forma que mete a Jaime DENTRO del
  // tablero, asi que declara dos props que ninguna otra tiene: `sujeto` —de que
  // lado va— y `repartos`, la figura que argumenta. Lo demas —el fichero del
  // recorte y el filtro del tratamiento— lo pone el spec: ver `armarTableros`.
  new Forma("PanelDentro",
            "la placa, las masas negras, el recortado y la figura que reparte"
            + " un total",
            { premisa: "title", cifra: "outcome", remate: "label",
              pregunta: "label", condicion: "legal",
              sujeto: "izquierda | derecha | abajo: donde va el",
              repartos: "las barras que argumentan, con su etiqueta y sus"
                + " porciones",
              total: "el todo del que se reparte. 100 salvo que la escena diga"
                + " otra cosa",
              signo: "que se antepone a cada cifra: «$», «%», o nada",
              sujeto_src: "el recorte con alfa. **Lo pone el spec**, no se"
                + " escribe a mano",
              sujeto_css: "el filtro del tratamiento. Lo pone el spec desde"
                + " `escena_desc.color`" },
            ["repartos", "fuente"]),
  // **El palote: el segundo al mando.** Jaime: «utiliza animación de bolitas y
  // palotes… el personaje sirve de alivio cómico», «que quede como recurso
  // recurrente» y «tiene que estar ahí como segundo al mando… en todo». Sin
  // `accion` no hay qué actuar; cuándo pedir cada una, acompañándolo
  // (`cubre: "panel"` + `lado`) o encadenadas, lo dice la cabecera de
  // `Palote.tsx`, que es lo que lee el catálogo. `texto` y `tablas` tienen su
  // tope en el componente (`assertShort`).
  new Forma("Palote", "segundo al mando: un personaje de palotes actúa la idea, a pleno o acompañándolo a él (`cubre: panel`), alivio cómico y recurso recurrente",
            { accion: "ideas: millonario | musculo | mecanico · proceso: investigar | curriculum | guion | aplicacion · gestos: senalar | pensar | aprobar | celebrar | encoger | saludar | caminar", acciones: "[{accion, en}]: lo que hace después en la etapa, `en` en segundos desde que empieza", lado: "con `cubre: panel`: arriba | abajo | izquierda | derecha (por defecto); a un lado es lo segundo del cuadro, más de medio alto", textoAl: "a un lado: frente (al otro lado de él) | encima (del muñeco)", texto: "statement", tablas: "label" }, ["accion"]),
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
/**
 * **La biblioteca de figuras, cerrada.** Jaime, 6-9-2026.
 *
 * Se comprueba aqui —y no solo en `escena.mjs`— porque son dos puertas
 * distintas: alli se rechaza la figura al ir a trazarla, y **la escena sale
 * igual, sin figura**; aqui se dice al recibir el tablero, que es cuando
 * todavia se puede componer otra cosa. Una lamina a la que se le cae la figura
 * en silencio es media lamina, y eso es lo que produjo `desvio` en reel-07 e2:
 * un encargo que decia «sin figura» dibujado como diagrama.
 */
const FIGURA_CERRADA = cerrada("figuras.json");

/** Los props con los que un tablero pide una figura dibujada. */
const PIDEN_FIGURA = ["figura", "silueta", "volumen"];

/**
 * Lo que un tablero declara y la biblioteca cerrada no deja dibujar.
 *
 * Va aparte de `Forma.revisar` a proposito: aquello comprueba una forma contra
 * SU contrato —props que faltan, textos que se pasan del tope— y esto es una
 * regla de lote que vale para las 24, tengan forma en el catalogo o no. Metida
 * dentro de `revisar` solo alcanzaria a las ocho declaradas.
 */
export const figurasCerradas = (kind, props) => {
  if (!FIGURA_CERRADA) return [];
  const p = props ?? {};
  return PIDEN_FIGURA
    .filter((k) => typeof p[k] === "string" && p[k].trim())
    .map((k) =>
      `«${kind}» declara \`${k}: "${p[k]}"\` y la biblioteca de figuras esta` +
      ` CERRADA desde el ${FIGURA_CERRADA.desde}: «${FIGURA_CERRADA.jaime}».` +
      ` Sale ${FIGURA_CERRADA.que_sale}; entra ${FIGURA_CERRADA.que_entra}.` +
      ` Este tablero se compone con el dato o con la letra`);
};

/**
 * **Las formas cuyo componente deja sitio a su cara**, leídas de quien dibuja.
 *
 * Una forma deja sitio si dibuja dentro de `ZonaTablero`: ahí `dibujaTablero`
 * le estrecha la caja a la columna contraria a la suya. Las que componen a mano
 * sobre el cuadro entero no se enteran, y el recorte les pisaría el texto. Se
 * lee del despacho y de cada componente —como `CONSTRUIDAS`— para que construir
 * la columna en uno lo saque de la falta sin tocar ninguna lista.
 */
export const DEJAN_SITIO = (() => {
  const t = fs.readFileSync(`${DIR_C}/Tablero.tsx`, "utf8");
  const deja = new Set();
  for (const m of t.matchAll(/if \(([^{;]*?)\)\s*return <(\w+)/g)) {
    let src = "";
    try { src = fs.readFileSync(`${DIR_C}/${m[2]}.tsx`, "utf8"); } catch { /* sin fichero, no deja */ }
    if (!src.includes("<ZonaTablero")) continue;
    for (const k of m[1].matchAll(/cue\.kind === "([^"]+)"/g)) deja.add(k[1]);
  }
  return deja;
})();

/**
 * **En las piezas que lo declaran, todo tablero a pleno lleva su cara** (T-06).
 *
 * Jaime, 10-9-2026: *«ahora todos los tableros deben mostrar mi cara en la
 * composición»*. Regla de lote como `figurasCerradas`, pero **de pieza**: la
 * aplica quien sabe de qué pieza es el tablero —`reels/base.mjs`, con el prop
 * `cara: "siempre"` del marco— y por eso las siete de venta salen igual. Un
 * panel o una banda ya le dejan la cara; `cc` no tapa nada.
 */
/**
 * Las formas que se dibujan **sobre su plano**: el rótulo va detrás o encima de
 * él, así que su cara ya es la composición y un recorte aparte la duplicaría.
 * `Gancho` faltaba y paró el primer render de reel-08 (12-9, C-417).
 */
const SOBRE_SU_PLANO = new Set(["tipo", "Gancho"]);

export const sinSujeto = (kind, props) => {
  const p = props ?? {};
  if (SOBRE_SU_PLANO.has(kind) || (p.cubre ?? "pleno") !== "pleno") return [];
  if (!p.sujeto)
    return [`«${kind}» va a pleno sin \`sujeto\`, y en esta pieza todo tablero` +
      " muestra su cara (Jaime, 10-9: «todos los tableros deben mostrar mi" +
      " cara»). Declara su lado —izquierda o derecha— y el copy va en la otra" +
      " columna; o que acompañe (`panel`, `banda`)"];
  if (CONSTRUIDAS.has(kind) && !DEJAN_SITIO.has(kind))
    return [`«${kind}» lleva \`sujeto\` y su componente no dibuja dentro de` +
      " `ZonaTablero`: no deja la columna libre y el recorte le pisaría el" +
      " texto. Otra forma, o construirle la columna"];
  return [];
};

export const revisarTablero = (kind, props) => {
  // **Una forma que no está en este catálogo NO es un error.** Se dibuja con
  // `TableroDeclarado` y punto. Esto devolvía una falta por cada una —42 en el
  // lote— y eso es otra vez mi lista poniéndole techo al diseño, que es lo que
  // Jaime paró: *«deja que el diseñador diseñe las formas»*.
  //
  // Sólo se revisa lo que tiene componente propio, porque ahí sí hay un
  // contrato de código que respetar: esos componentes llaman a `assertShort` y
  // **tumban el render** si un texto se pasa de su tope.
  const cerradas = figurasCerradas(kind, props);
  const f = forma(kind);
  // Un clip que no está en la biblioteca, cuyo fichero falta o con una forma
  // que no existe tumba el render a mitad: se dice aquí, que es antes (C-673).
  // Las formas con regla propia, cada una en su fichero (Palote: C-724).
  for (const f of [{ Apoyo: faltasDeApoyo, Palote: faltasDePalote }[kind]].filter(Boolean)) if (f(props).length) return f(props);
  if (kind === "Tarjeta" && faltasDeTarjeta(props).length) return faltasDeTarjeta(props);
  return [...cerradas, ...(f ? f.revisar(props) : []), ...sinSusCampos(kind, props),
          ...pilaQueDesborda(props), ...oroSinLinea(kind, props)];
};

/**
 * **El oro de un tablero declarado apunta al texto de una línea** (C-693).
 * `declarado/lineas.ts` lanza si `oro` no casa con ninguna, y lo lanzaba en el
 * render: reel-23, 15-11-2026, `oro: 2` en una `ListaNumerada` mató `render.mjs`
 * en el fotograma 647 en cada vuelta, hora y media. La misma regla aquí, donde
 * se rechaza antes de guardar. Se busca en TODO texto de las props —un
 * superconjunto de las líneas que el componente saca—, así que nunca rechaza
 * un oro que el componente aceptaría.
 */
const DECLARADOS = new Set(["fichas", "evidencecard", "bandafecha", "listanumerada", "tablerodeclarado"]);
const limpio = (s) => String(s).toLowerCase().normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9 ]/g, "").replace(/\s+/g, " ").trim();
const textos = (v) => typeof v === "string" ? [v]
  : Array.isArray(v) ? v.flatMap(textos)
  : v && typeof v === "object" ? Object.values(v).flatMap(textos) : [];
const oroSinLinea = (kind, props) => {
  // Las que llegan enteras a `leerDeclarado`: la familia de `Fichas`, y
  // cualquier nombre que el catálogo no conoce, que cae en `TableroDeclarado`.
  if (!DECLARADOS.has(String(kind).toLowerCase()) && forma(kind)) return [];
  const oro = props?.oro;
  if (oro === undefined || oro === null || oro === false || oro === ""
      || String(oro).toLowerCase() === "ninguno") return [];
  const busca = limpio(oro).slice(0, 14);
  const resto = Object.fromEntries(Object.entries(props).filter(([k]) => k !== "oro"));
  if (busca && textos(resto).some((t) => limpio(t).includes(busca))) return [];
  return [`\`oro: ${JSON.stringify(oro)}\` no casa con ninguna línea del tablero: el oro` +
          " es el TEXTO exacto de la línea que el tablero demuestra, o `false`"];
};

/**
 * **Los tramos de una pila se reparten la altura: suman 1 como mucho.** El
 * diseñador de reel-13 e6 los escribió acumulados (0,1 … 1,0, suma 5,5) y los
 * años se montaron unos encima de otros desde el cuarto (C-448).
 */
const pilaQueDesborda = (props) => {
  const t = props?.tramos;
  if (!Array.isArray(t) || !t.every((x) => typeof x?.alto === "number")) return [];
  const suma = t.reduce((s, x) => s + x.alto, 0);
  return suma > 1.05
    ? [`los \`tramos\` suman ${suma.toFixed(2)} de alto y la pila es 1: cada \`alto\`` +
       " es la parte que ocupa ESE tramo, no la altura acumulada"]
    : [];
};

/**
 * **Los campos obligatorios del componente, por su nombre.** `Fusion` de
 * reel-11 llegó con `a`, `b` y `resultado` y el render murió en
 * `fusion.length` tras cinco minutos de recorte (C-428). El pie lo pone el
 * motor, así que `fuente` y `condicion` no se exigen aquí.
 */
// `props` y `kind` son de los que reciben la declaración entera (`Fichas`,
// `TableroDeclarado`): ahí no hay nombres que exigir. `bloques` y `lado` los
// pone el montaje del panel —`bloquesDePanel` deriva los bloques de los textos
// y el lado es el de la pieza—; lo que llega tal cual es cada bloque (C-638).
const DEL_MOTOR = new Set(["fuente", "condicion", "source", "props", "kind", "bloques", "lado"]);
const sinSusCampos = (kind, props) => {
  const nombre = piezas().find((n) => n.toLowerCase() === String(kind).toLowerCase());
  const campos = nombre ? camposDe(nombre) : null;
  if (!campos) return [];
  const p = props ?? {};
  // **Salvo que el propio componente lo mida.** `Acumulacion` hace
  // `assertShort(condicion, …)` y sin ella el render de reel-13 murió en
  // `length` (C-434): ahí no la pone nadie más que quien diseña.
  const fuente = fs.readFileSync(`src/components/${nombre}.tsx`, "utf8");
  // Se mira el último tramo del nombre: el `source` de `resultado: { figure;
  // source }` también lo pone el motor, que dibuja el pie de las 24 (C-638).
  const exige = (c) => {
    const hoja = c.split(".").pop();
    return !DEL_MOTOR.has(hoja) || fuente.includes(`assertShort(${hoja},`);
  };
  const faltan = Object.keys(campos).filter((c) => !c.endsWith("?") &&
    exige(c) && (c.includes("[].")
      // Lo de dentro de una lista se exige a cada elemento (C-432).
      ? (() => {
          const [lista, dentro] = c.split("[].");
          return Array.isArray(p[lista]) &&
            p[lista].some((x) => x && typeof x === "object" && x[dentro] == null);
        })()
      // Y lo de dentro de un objeto declarado, si está (C-457).
      : c.includes(".")
        ? (() => {
            const [obj, dentro] = c.split(".");
            return p[obj] && typeof p[obj] === "object" && p[obj][dentro] == null;
          })()
        : p[c] == null));
  // **Y un elemento que no es un objeto no trae ninguno.** Arriba sólo se miran
  // los objetos, así que `bloques: ["¿LE ASESORARON", …]` pasaba entero y
  // `SidePanel` murió en `b.texto` en el fotograma 150 (reel-22 e1, C-638).
  const listas = [...new Set(Object.keys(campos).filter((c) => c.includes("[]."))
    .map((c) => c.split("[].")[0]))];
  const sueltos = listas.flatMap((l) => {
    const i = Array.isArray(p[l]) ? p[l].findIndex((x) => !x || typeof x !== "object") : -1;
    if (i < 0) return [];
    const suyos = Object.keys(campos).filter((c) => c.startsWith(`${l}[].`))
      .map((c) => c.slice(l.length + 3));
    return [`«${nombre}».\`${l}\` trae ${JSON.stringify(p[l][i])} y cada elemento es` +
      ` un objeto {${suyos.join(", ")}}: escrito así el render muere`];
  });
  return [...sueltos, ...(faltan.length
    ? [`«${nombre}» se declara con ${Object.keys(campos).join(", ")} y le faltan ` +
       `${faltan.join(", ")}: con otro nombre no llega a la pantalla`]
    : [])];
};

/**
 * **La prueba de C-638, sobre lo que reel-22 e1 declaró de verdad.** Con los
 * bloques como cadenas pasó las tres puertas y el render murió en el fotograma
 * 150; la misma lámina con cada bloque como objeto se monta. La corre
 * `guardas.mjs`: si alguna vez vuelve a pasar, la línea para.
 */
const REEL22_E1 = { familia: "cargada", bloques: ["¿LE ASESORARON", "O LE VENDIERON?"],
                    lado: "izq", cubre: "panel" };
export const comprobar = () => {
  const bien = { ...REEL22_E1, bloques: REEL22_E1.bloques.map((texto) => ({ texto })) };
  const dice = (props, aguja) => revisarTablero("SidePanel", props).some((m) => m.includes(aguja));
  return [
    ...(dice(REEL22_E1, "`bloques` trae") ? [] : ["C-638: los bloques de reel-22 e1" +
      " escritos como cadenas pasan la revisión, y `SidePanel` muere en `b.texto`"]),
    ...(dice({ ...bien, bloques: [{ fuerte: true }] }, "bloques[].texto") ? []
      : ["C-638: un bloque de `SidePanel` sin `texto` pasa la revisión"]),
    ...revisarTablero("SidePanel", bien).map((m) => `C-638: reel-22 e1 bien escrita` +
      ` no debería tener faltas y tiene «${m}»`),
  ];
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
