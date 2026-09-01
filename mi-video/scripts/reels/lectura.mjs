/**
 * **Cuanto dura lo que hay que leer.**
 *
 * La regla del proyecto, y gobierna tableros, tarjetas y paneles por igual: **un
 * dato que no da tiempo a leer no esta en el video aunque este en el frame**. La
 * web es autopaso —el lector decide cuanto mira— y el video no.
 *
 * Asi que aqui no hay numeros redondos puestos a ojo: cada elemento dura lo que
 * cuesta leer lo que lleva dentro.
 */
import { FPS } from "./reloj.mjs";

/**
 * Cuanto tiene que durar el hueco de un tablero, en frames.
 *
 * **Un componente con horario propio necesita su tiempo.** Los tableros se
 * construyen por tiempo de lectura —cada nodo espera a que el anterior se haya
 * podido leer—, asi que un numero redondo puesto desde fuera los deja a medio
 * construir: con 5,5 s el `TwoPaths` mostraba solo la cabecera y el pie, y en el
 * render parecia un tablero vacio cuando lo que estaba era corto de tiempo.
 *
 * Esto replica la cadena de `duracionDe` de cada componente. Es duplicacion y se
 * sabe: el spec es Node y los componentes son TSX, y no hay import directo.
 * **Si cambias el horario de un componente, cambia tambien aqui** — la señal de
 * que se te olvido es un tablero que aparece incompleto.
 */
export const lectura = (t) =>
  Math.max(36, Math.ceil((String(t).trim().split(/\s+/).length / 2.8) * FPS));

/**
 * Cuanto se estira un tablero por encima de la costura que sigue.
 *
 * 0,8 s: el beat siguiente arranca por debajo mientras el tablero todavia esta,
 * asi que al volver al plano no hay corte que ver. Es la forma clasica de
 * esconder una costura —cortar a otra cosa y volver tarde— y aqui esa otra cosa
 * ademas explica.
 */
export const SOLAPE = 24;

/**
 * **Sin tope de 3 s.** Jaime: *«si los tableros duran más de 3 segundos no hay
 * problema, siempre que sean dinámicos y expliquen conceptos»*. La regla de los
 * 3 s es el pulso del CORTE, no del tablero — y un tablero que se construye por
 * tiempo de lectura no está quieto: cada nodo entra cuando el anterior ya se
 * pudo leer. Lo que no se permite es un tablero estático largo.
 *
 * Se le suma un margen para que el último elemento respire antes de irse: con la
 * duración justa, el remate aparecía y desaparecía en el mismo suspiro.
 */
const RESPIRO = 20;

/** Frames de entrada de un bloque de tablero. */
const ENTRADA = 8;

export const duracionTablero = (kind, p) => {
  if (kind === "acumulacion") {
    const tramos = p.tramos.reduce(
      (n, tr) => n + Math.max(ENTRADA + 4, lectura(tr.etiqueta)), 0);
    return ENTRADA * 3 + tramos + lectura(p.condicion) + RESPIRO + 24;
  }
  if (kind === "comparacion") {
    return ENTRADA * 2 + Math.max(20, lectura(p.izquierda.cifra)) +
      Math.max(20, lectura(p.derecha.cifra)) + lectura(p.condicion) +
      RESPIRO + 24;
  }
  // `TwoPaths` y `CausalChain` no publican su horario; 8,5 s es lo medido.
  return Math.round(8.5 * FPS);
};

/** `Tarjeta` encadena: un bloque cada 8 frames, luego el remate, luego el pie. */
export const duracionTarjeta = (p) =>
  p.bloques.length * ENTRADA + 6 + p.remate.length * 4 + 4 +
  lectura(p.remate.join(" ")) + (p.pie ? lectura(p.pie) : 0) + 20;

/**
 * Cuanto entra el panel antes que su tablero.
 *
 * **Se calcula por bloque, no es fijo.** Con 1,6 s los tres letreros entraban
 * encima unos de otros y no daba tiempo a leer ninguno — Jaime: *«los números
 * que salen en el segundo 17 se pierden porque el tablero aparece muy rápido;
 * cada letrero se debe ver»*.
 *
 * 0,75 s por bloque mas medio segundo de respiro antes de que el tablero tome el
 * cuadro.
 */
export const ADELANTO = (bloques) =>
  Math.round((bloques.length * 0.75 + 0.5) * FPS);

/**
 * **La condicion que cabe en pantalla, no la ficha entera.**
 *
 * Jaime, viendo el reel-01 bloqueado: *«lo que hace falta es simplificar el
 * tablero y animarlo mas, reducir la carga cognitiva; para eso son los
 * tableros»*. Y antes: *«ponemos pies de foto con la info complementaria que no
 * cabe en el video»*.
 *
 * El tablero dura lo que cuesta leerlo, y eso esta bien — es lo que impide que
 * un dato pase sin poder leerse. Pero la condicion de la etapa 3 del reel-01
 * llevaba **100 palabras**: una nota de metodo —CCPC, capital gravable, personal
 * services business— escrita para dejar constancia, no para leerse en pantalla.
 * A 2,8 palabras por segundo son 39 s, y el tablero salia de 40,9 s sobre una
 * pieza de 101,5 s. Con eso Jaime se quedaba en 59,7% de cara —el suelo es 60— y
 * sin un segundo limpio en el tercio central, asi que la pieza no se renderizaba
 * **y el motivo que se imprimia era el equivocado**: decia que Jaime no aparecia
 * en mitad, cuando la causa era la letra pequena.
 *
 * Se corta por frases enteras, nunca a mitad de una: una condicion partida dice
 * otra cosa que la condicion. Lo que no entra viaja como `condicion_completa`
 * para el copy, que es donde Jaime dijo que va.
 */
export const CONDICION_PALABRAS = 25;

export const enPantalla = (t) => {
  const limpio = String(t).trim().replace(/\s+/g, " ");
  const palabras = limpio.split(" ");
  if (palabras.length <= CONDICION_PALABRAS) return limpio;
  const frases = limpio.match(/[^.!?]+[.!?]*/g) ?? [limpio];
  let salida = "";
  for (const f of frases) {
    const cand = (salida + f).trim();
    /**
     * **La primera frase tambien cuenta.** Esto llevaba un `salida &&` delante,
     * asi que la primera vuelta nunca podia cortar: una condicion de una sola
     * oracion de cien palabras salia entera y el tope no existia para ella. El
     * recorte por palabra de la linea de abajo estaba escrito y era
     * **inalcanzable**.
     *
     * Hoy no cambia ni un frame, y por un pelo: `pieDe` se queda con una fila de
     * `dato` por etapa y la primera frase mas larga de las que elige tiene
     * **exactamente 25 palabras**, o sea justo el tope. Basta una coma menos en
     * una ficha para que la condicion entera se cuele en pantalla, y con ella la
     * duracion del tablero que la lleva.
     */
    if (cand.split(" ").length > CONDICION_PALABRAS) break;
    salida = cand;
  }
  // Si la primera frase ya se pasa, se corta por palabra y se dice que sigue.
  return salida || `${palabras.slice(0, CONDICION_PALABRAS).join(" ")}…`;
};
