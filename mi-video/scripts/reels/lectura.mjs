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
import { createRequire } from "node:module";
const LEE = createRequire(import.meta.url)("../../src/brand/lectura.json");

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
  Math.max(LEE.sueloFrames,
    Math.ceil((String(t).trim().split(/\s+/).filter(Boolean).length
               / LEE.palabrasPorSegundo) * FPS));

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

/**
 * El silencio antes del remate y lo que tarda el barrido en cruzar.
 *
 * Espejo de `beat.hold` y de `BARRE` en `src/components/acumulacion/horario.ts`:
 * la pila se sostiene entera un momento y entonces el barrido se la lleva y deja
 * la cifra sola. Si esto no estuviera aqui, el spec reservaria el hueco de un
 * tablero que acaba con el ultimo tramo y el barrido saldria cortado.
 */
const HOLD = 22;
const BARRE = 16;

/**
 * **Lo que se entrega va a 1,15x, y hasta ahora nadie lo restaba.**
 *
 * Jaime, viendo reel-05: *«todo tablero tiene que tener tiempo suficiente de
 * lectura»*. Todo este fichero calcula el tiempo del MONTAJE, y el montaje se
 * acelera despues en `voz-limpia.py` (`VELOCIDAD = 1.15`). Un tablero medido
 * para 8,0 s de lectura se entrega en 7,0: un 13% menos, en TODOS, siempre, sin
 * que apareciera en ninguna cuenta.
 *
 * Medido sobre las siete: cuatro tableros por debajo de su tiempo, y el peor
 * —reel-05 beat 6— con 6,00 s reales para 8,75 s de texto.
 *
 * Se compensa aqui y no en el paso de audio porque aqui es donde se decide
 * cuanto dura: alargarlo despues movería el corte entero.
 */
const ENTREGA = 1.15;

/** El texto de un tablero, venga en el prop que venga. */
const textos = (p) => {
  const fuera = [];
  const mete = (v) => {
    if (typeof v === "string" && v.trim()) fuera.push(v);
    else if (Array.isArray(v)) v.forEach(mete);
    else if (v && typeof v === "object") Object.values(v).forEach(mete);
  };
  for (const [k, v] of Object.entries(p ?? {})) {
    // Lo que no se lee: la placa es una imagen, el sonido un nombre de fichero,
    // y `cubre`/`familia`/`oro` son instrucciones de composicion.
    // Lo que no se lee: la placa es una imagen, el sonido un nombre de
    // fichero, y `cubre`/`familia`/`oro`/`recorte` son instrucciones de
    // composicion. `condicion_completa` y `source` se escriben para el copy
    // del post y **no se dibujan nunca**.
    //
    // `recorte` entro en la lista el mismo dia que `armarTableros` empezo a
    // ponerlo en todo tablero a pleno: valia «lleno», se contaba como un
    // bloque de texto, y con eso aparecieron dos faltas de lectura que nadie
    // habia disenado y dos recortes buenos siguieron dando falta.
    //
    // `sujeto`, `sujeto_src` y `sujeto_css` entran por esa misma puerta: son de
    // que lado va el, que fichero lo trae y con que filtro. Tres instrucciones
    // de composicion que, contadas como texto, sumarian tres bloques de lectura
    // a un tablero donde no se lee ni una palabra de ellas.
    // Y **el pie tampoco es un bloque de la lamina**: desde que va fuera de la
    // zona segura (`src/components/PieTablero.tsx`) no le disputa sitio a
    // nada, asi que contarlo aqui pedia medio segundo de lectura por una linea
    // que ya no esta dentro del tablero. `condicion` y `fuente` estaban
    // contadas y `source` no, que es la misma linea con dos nombres.
    // `zona` entra por la misma puerta que `figura` y `recorte`: dice DONDE cae
    // la lamina —«pie»— y quien la lee es `TableroDeclarado`, no el espectador.
    // Contada como bloque, un `zona: "pie"` sumaba 0,75 s de lectura a un
    // tablero de una sola linea, y la prosa de composicion que otras piezas
    // escriben ahi —300 caracteres en reel-07 e1— habria pedido diez segundos
    // por un texto que no se dibuja. `declarado/lineas.ts` ya no la rotula; esto
    // es la otra mitad de la misma lista.
    if (["placa", "sound", "sfx", "cubre", "familia", "oro", "figura", "zona",
         "source", "anclas", "recorte", "ventana", "signo", "total",
         "sujeto", "sujeto_src", "sujeto_css",
         "pie", "fuente", "condicion", "condition", "limitation",
         "condicion_completa"].includes(k)) continue;
    mete(v);
  }
  return fuera;
};

const _tablero = (kind, p) => {
  if (kind === "acumulacion") {
    const tramos = p.tramos.reduce(
      (n, tr) => n + Math.max(ENTRADA + 4, lectura(tr.etiqueta)), 0);
    const fin = ENTRADA * 3 + tramos;
    // **Con resultado el tablero no acaba con el ultimo tramo: acaba con el
    // barrido.** La pila se sostiene, el barrido cruza y la cifra se queda sola
    // el tiempo de leerla. Sin resultado no hay barrido y manda la condicion.
    return p.resultado
      ? fin + HOLD + BARRE + lectura(p.resultado.figure) + RESPIRO + 24
      : fin + lectura(p.condicion) + RESPIRO + 24;
  }
  if (kind === "comparacion") {
    return ENTRADA * 2 + Math.max(20, lectura(p.izquierda.cifra)) +
      Math.max(20, lectura(p.derecha.cifra)) + lectura(p.condicion) +
      RESPIRO + 24;
  }
  // `TwoPaths` y `CausalChain` no publican su horario; 8,5 s es lo medido.
  //
  // Se probo medirlo por su texto y **infla**: como respaldo solo entra cuando
  // el beat no dice cuanto dura, y ahi `Math.min(pedido, hueco)` deja que el
  // tablero se coma el hueco entero — reel-07 beat 2 se fue de 9,3 a 53,9 s.
  // Lo que el texto pide sirve para AVISAR (ver `lecturaCorta`), no para fijar
  // la duracion: la duracion la manda el beat.
  return Math.round(8.5 * FPS);
};

/**
 * Los tableros cuyo copy NO da tiempo a leerse. Avisa; no toca nada.
 *
 * Jaime: *«todo tablero tiene que tener tiempo suficiente de lectura»*. La regla
 * estaba escrita en el contrato del disenador —0,75 s por bloque mas medio
 * segundo de respiro— y **no la comprobaba nadie**, asi que cuatro de diecisiete
 * salieron cortos sin que apareciera en ningun sitio.
 *
 * Y no se arregla estirando: un tablero no puede pasar de su beat sin comerse la
 * etapa siguiente. Lo que sobra es el COPY. Por eso esto es una falta con su
 * numero —cuanto pide y cuanto hay— y la decision es de quien compone.
 */
/**
 * Lo que la REGLA de Jaime pide para un tablero, en frames de montaje.
 *
 * *«0,75 s por bloque mas medio segundo de respiro»*, contado sobre la ENTREGA
 * —que va a 1,15x— y devuelto en frames del montaje, que es donde se decide.
 *
 * Existe para que no haya dos cuentas. `duracionTablero` calcula lo que tarda en
 * CONSTRUIRSE cada forma —cuando entra cada bloque, cuanto se sostiene— y esa es
 * otra pregunta. Cuando `armarTableros` quiso adelantar un tablero corto uso esa
 * y no cambio nada, porque la que se queja es esta.
 */
/**
 * Lo mas que un tablero puede entrar ANTES cuando el CTA le come el final.
 *
 * 24 frames, 0,8 s: lo mismo que `SOLAPE` estira por el otro lado y por la misma
 * razon —es un L-cut—. Mas que eso y el grafico llega antes que la idea que
 * ilustra.
 */
export const ANTES = 24;

export const pideLeer = (props) => {
  const n = textos(props).length;
  return n ? Math.ceil((0.75 * n + 0.5) * ENTREGA * FPS) : 0;
};

export const lecturaCorta = (tableros) => {
  const faltas = [];
  for (const b of tableros) {
    const n = textos(b.props).length;
    if (!n) continue;
    const pide = 0.75 * n + 0.5;
    const hay = b.duration / FPS / ENTREGA;
    if (hay < pide - 0.05) {
      faltas.push(
        `el tablero del beat ${b.beat} («${b.kind}») tiene ${n} bloques que piden`
        + ` ${pide.toFixed(1)}s de lectura y solo se ven ${hay.toFixed(1)}s`
        + ` (${(b.duration / FPS).toFixed(1)}s a 1,15x): sobra copy, no falta tiempo`);
    }
  }
  return faltas;
};

/** Lo que hay que dejar en el MONTAJE para que se lea en la ENTREGA. */
export const duracionTablero = (kind, p) =>
  Math.ceil(_tablero(kind, p) * ENTREGA);

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

/**
 * **El punto del separador de miles no acaba una frase.**
 *
 * Es el arreglo que `cifras.mjs` dejo declarado y puso en su propia copia: aqui
 * sirve para TODOS los lectores, que era la condicion de que fuera el
 * definitivo. Sin el, el corte por frases partia el importe y el pie del
 * tablero de reel-02 e3 salia diciendo «Caso hipotetico. Ontario, ano fiscal
 * 2026. Los $180.» — el importe mutilado y la frase diciendo otra cosa que la
 * condicion, justo en la linea que responde por la cifra.
 */
const MILES = " ";

export const enPantalla = (t) => {
  const limpio = String(t).trim().replace(/\s+/g, " ");
  const palabras = limpio.split(" ");
  if (palabras.length <= CONDICION_PALABRAS) return limpio;
  const protegido = limpio.replace(/(?<=\d)\.(?=\d)/g, MILES);
  const frases = protegido.match(/[^.!?]+[.!?]*/g) ?? [protegido];
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
  return (salida || `${palabras.slice(0, CONDICION_PALABRAS).join(" ")}…`)
    .split(MILES).join(".");
};
