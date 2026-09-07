/**
 * **Dónde cae el rótulo del gancho y con qué cuerpo.** Lo que mide.
 *
 * Vive aparte de la puerta porque son dos trabajos: aquí se calcula la
 * geometría —el cuerpo que cabe, el alto del bloque, el sitio que le toca
 * mirando su coronilla— y en `portada.mjs` se arma la capa y se comprueba que
 * cumple. El camino (`scripts/gancho.mjs`) entra por aquí; la puerta también,
 * y así los dos miran el mismo número.
 *
 * **Y el número no está aquí**: está en `src/brand/gancho.json`, que es de
 * donde lo lee también el render (`src/brand/gancho.ts`). Es la lección de
 * `franja.json`: la franja del subtítulo estuvo escrita cuatro veces y por eso
 * dos tableros de cuatro pudieron ignorarla.
 */
import fs from "node:fs";
import { FPS } from "./reloj.mjs";

const J = JSON.parse(fs.readFileSync("src/brand/gancho.json", "utf8"));

/**
 * El canon del gancho, tal como lo declara `src/brand/gancho.json`.
 *
 * Lo importa `scripts/gancho.mjs` para emitir la capa con esos mismos tiempos:
 * el camino y la puerta miran el mismo número o la puerta no comprueba nada.
 */
export const CANON = {
  arriba: J.arriba,
  arribaMin: J.arribaMin,
  roce: J.roce,
  hombro: J.hombro,
  empate: J.empate,
  izquierda: J.izquierda,
  ancho: J.ancho,
  primera: J.primera,
  segunda: J.segunda,
  interlinea: J.interlinea,
  suelo: J.suelo,
  entradaEn: J.entradaEn,
  escalon: J.escalon,
  entrada: J.entrada,
  palabra: J.palabra,
  regla: J.regla,
  reglaGrosor: J.reglaGrosor,
  quieto: J.quieto,
  salida: J.salida,
  /** Lo que dura el gancho, en segundos. Lo lee también `dominio/sujeto.py`. */
  dura: J.dura,
  /** Cuándo queda armado el bloque del rótulo, ya en frames. Ver `_armado`. */
  armado: Math.round(J.armado * FPS),
  /** El tercio de abajo, en píxeles: ahí no vive el rótulo. */
  tercioPx: Math.round(J.tercio * 1920),
};

/**
 * Avance medio de un carácter de Anton en versales, **leído de donde vive**.
 *
 * No es una lista paralela: es `avance.anton` de `src/brand/medida.ts`, el
 * mismo número que usa el componente para decidir el cuerpo. Escribirlo aquí
 * otra vez sería inventar un ancho distinto del que se va a dibujar, que es
 * exactamente la clase de falta que esta puerta viene a cazar.
 */
const AVANCE = (() => {
  const t = fs.readFileSync("src/brand/medida.ts", "utf8");
  return Number(t.match(/anton:\s*([\d.]+)/)?.[1] ?? 0.47);
})();

/**
 * **Cuántos caracteres caben en una línea al cuerpo más pequeño que se admite.**
 *
 * Pasado eso no se arregla encogiendo más: sobra copy, y eso lo dice la puerta.
 */
export const CABEN = Math.floor(CANON.ancho / (CANON.suelo * AVANCE));

/**
 * **El cuerpo de cada línea.** Baja si la frase no cabe: el margen se paga en
 * cuerpo, que es barato, no en texto cortado, que no lo es. La jerarquía no se
 * pierde porque la llevan el peso y el color, no el tamaño.
 *
 * Se calcula aquí y no en el componente por lo de siempre: el componente dibuja
 * lo que le llega. Y además hace falta aquí para poder colocar el bloque —el
 * alto sale de los cuerpos— y para que la puerta compruebe geometría de verdad
 * y no la del caso mejor.
 */
export const cuerposDe = (lineas, oro = lineas.length - 1) =>
  lineas.map((l, i) =>
    Math.round(
      Math.max(
        CANON.suelo,
        Math.min(
          i === oro ? CANON.segunda : CANON.primera,
          CANON.ancho / Math.max(1, l.length * AVANCE),
        ),
      ),
    ),
  );

/** Lo ancho que sale una línea a ese cuerpo, en píxeles. */
const anchoDe = (linea, cuerpo) => Math.round(linea.length * cuerpo * AVANCE);

/**
 * **Por dónde se parte una línea en palabras.** Una sola expresión, y la misma
 * que usa el componente: si los dos partieran distinto, a una palabra le
 * tocaría el frame de otra y nadie se enteraría.
 */
export const enPalabras = (linea) => String(linea).trim().split(/\s+/);

/**
 * **El frame de cada palabra, y el del filete que cierra el bloque.**
 *
 * Jaime, sobre el gancho, 6-9-2026: *«con mucho movimiento, porque la idea es
 * capturar la atención esos tres segundos»*. Lo que había entraba en dos frames
 * —el 2 y el 15— y a partir del 28 no se movía nada más: **la mitad de los tres
 * segundos que deciden era una foto con texto.**
 *
 * Dos cosas lo llenan y ninguna es adorno:
 *
 * 1. **La frase se escribe por palabras**, `palabra` frames entre una y la
 *    siguiente, dentro del mismo escalón de línea que ya estaba aprobado.
 * 2. **El filete se traza y dura el hueco**: arranca `regla` frames después de
 *    la última palabra y **termina cuando entra el subtítulo**. Así no queda
 *    ventana quieta por construcción, y como el hueco depende de cuántas
 *    palabras tenga el rótulo, cada pieza lo traza a su propio ritmo — la
 *    variedad sale del copy, igual que el lado sale de dónde está él.
 */
function ritmo(lineas) {
  const palabras = lineas.map((l, i) =>
    enPalabras(l).map(
      (_, k) => CANON.entradaEn + i * CANON.escalon + k * CANON.palabra,
    ),
  );
  const ultima = Math.max(...palabras.flat()) + CANON.entrada;
  const regla = ultima + CANON.regla;
  return {
    palabras,
    regla,
    // Nunca menos que lo que tarda una línea en entrar: un trazo más corto que
    // eso se lee como un parpadeo, no como una línea que se dibuja.
    reglaDura: Math.max(CANON.entrada, CANON.armado - regla),
  };
}

/**
 * **De qué lado del cuadro cae el bloque, mirando dónde está su cabeza.**
 *
 * Jaime, sobre la variedad del gancho: *«el lado y la altura los decide DÓNDE
 * ESTÁ ÉL, no el gusto: el texto ocupa el hueco que deja su cuerpo. Si está a la
 * derecha del cuadro, el bloque va a la izquierda»*.
 *
 * El hueco se mide a los lados de la franja que ocupa su cabeza, que trae la
 * ficha del recorte (`cabeza`, en `dominio/papel.py`). Si ninguno de los dos
 * gana por `empate`, el bloque se queda donde estaba aprobado —a la izquierda—:
 * moverlo por una diferencia de 20 px sería elegir por gusto, que es lo que
 * esto viene a quitar.
 */
const ladoDe = (cabeza) => {
  if (!cabeza) return "izq";
  const [izq, der] = [cabeza[0], 1 - cabeza[1]];
  return der - izq > CANON.empate ? "der" : "izq";
};

/**
 * **Dónde empieza el bloque, y sale de su cabeza — no de un número fijo.**
 *
 * Un `arriba` clavado se comía la palabra en una pieza y flotaba en otra: en el
 * caso aprobado su coronilla cae en el 430 y el bloque acaba en el 500, o sea
 * 70 px por detrás del pelo; en reel-01, en el segundo 1,6, su coronilla está
 * 100 px más arriba y con el mismo `arriba` la segunda línea entera quedaba
 * detrás de su cabeza —«MALA S···RTE»—. El efecto luciéndose a costa del
 * mensaje, que es la raya que Jaime ya había puesto.
 *
 * La coronilla la midió la pasada del recorte sobre la ventana entera y la dejó
 * en su ficha (`public/recorte/<pieza>-e1.json`). Sin ficha se usa el sitio
 * aprobado, que es lo que había.
 *
 * **Y el gesto son dos, que es de donde sale la variedad.** Jaime, viendo los
 * siete ya rehechos: *«me gusta, pero me gustaría más variedad»* — y el defecto
 * medido no era que se parecieran, era *«el mismo bloque en la misma esquina»*.
 * Con `arriba` de suelo, cinco de las siete acababan pegadas al techo y las
 * otras dos aquí: la geometría no tenía por dónde variar. Ahora el bloque
 * **roza** su coronilla si su cabeza deja sitio, y le **cruza por detrás del
 * hombro** si no lo deja; el suelo es el tercio que tapa la interfaz de Meta,
 * que es la regla que protege algo.
 *
 * **El techo sigue siendo `arribaMin`**: pegado al borde el rótulo deja de
 * leerse como composición y empieza a leerse como texto que no cupo.
 */
export function colocar(lineas, src, oro = lineas.length - 1) {
  const cuerpos = cuerposDe(lineas, oro);
  const alto = Math.round(
    cuerpos.reduce((n, c) => n + c, 0) * CANON.interlinea,
  );
  const ficha = `public/${src}`.replace(/\.webm$/, ".json");
  let coronilla = null;
  let cabeza = null;
  if (fs.existsSync(ficha)) {
    const f = JSON.parse(fs.readFileSync(ficha, "utf8"));
    if (typeof f.coronilla === "number") coronilla = Math.round(f.coronilla * 1920);
    if (Array.isArray(f.cabeza) && f.cabeza.length === 2) cabeza = f.cabeza;
  }
  const golpe = cuerpos[oro] ?? cuerpos[cuerpos.length - 1] ?? CANON.primera;
  // El gesto no se elige: si su coronilla deja sitio para el bloque entero por
  // encima del techo, roza; si no, no hay forma de rozar sin pegarlo al borde,
  // así que cruza por detrás de él.
  const roce = Math.round(CANON.roce * golpe);
  const gesto =
    coronilla !== null && coronilla + roce - alto >= CANON.arribaMin
      ? "roce"
      : "hombro";
  const mordida = gesto === "roce" ? roce : Math.round(CANON.hombro * golpe);
  const arriba =
    coronilla === null
      ? CANON.arriba
      : Math.max(
          CANON.arribaMin,
          Math.min(CANON.tercioPx - alto, coronilla + mordida - alto),
        );
  const lado = ladoDe(cabeza);
  return {
    cuerpos,
    alto,
    arriba,
    coronilla,
    cabeza,
    lado,
    gesto,
    oro,
    anchos: lineas.map((l, i) => anchoDe(l, cuerpos[i])),
    ...ritmo(lineas),
  };
}

