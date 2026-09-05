import { Easing } from "remotion";

/**
 * Sistema visual el canon, adaptado a video vertical.
 *
 * La página es la autoridad. Aquí no se inventa nada: se traduce de superficie
 * web a superficie de video. Los valores absolutos cambian (una pantalla de
 * 1080×1920 vista en la mano no es un viewport de 1400 px), pero la paleta, los
 * roles tipográficos, los modos y las prohibiciones se respetan literalmente.
 *
 * No se usa el logo por decisión de Jaime.
 */

export const FPS = 30;

export const layout = {
  width: 1080,
  height: 1920,
  /**
   * Las plataformas verticales superponen su interfaz. El margen inferior es
   * mucho mayor porque ahí viven el copy, el usuario y los botones de
   * Reels/TikTok: cualquier texto que caiga dentro queda tapado.
   */
  /**
   * Zonas seguras de Instagram Reels — **fuente oficial de Meta**.
   *
   * Meta indica dejar libres de texto, logos y elementos clave: **14% arriba,
   * 35% abajo y 6% a cada lado**. Sobre 1080x1920 son 269 / 672 / 65.
   *
   * Se llego aqui despues de un rodeo que conviene no repetir: los blogs de
   * terceros daban cifras contradictorias —de 108 a 270 arriba, de 280 a 672
   * abajo— y varios afirmaban margenes ASIMETRICOS por los botones de accion.
   * La guia oficial dice **simetricos**. Cuando hay fuente canonica, no se
   * promedian opiniones.
   *
   * Meta publica ademas una plantilla verificadora de zona segura (ppt/psd/key)
   * si hace falta comprobar una pieza concreta.
   */
  safe: { top: 269, bottom: 672, left: 65, right: 65 },
  /**
   * Franja de subtitulos, **dentro** de la zona segura.
   *
   * Los subtitulos son elemento clave —el playbook exige que el argumento
   * funcione sin audio— asi que van por encima del 35% inferior que Meta
   * reserva, no dentro. Ocupan los ultimos 200 px de la zona segura.
   */
  captionBand: 200,
  /**
   * Distancia de la banda de subtitulos al borde inferior.
   *
   * **760, no 420: los subtitulos van pegados a la barbilla, nunca abajo.**
   * Peticion de Jaime. Con 420 la banda caia en el 68-78% de altura —lejos de
   * la cara, en la zona donde la vista ya no esta— y el ojo tenia que viajar
   * entre el rostro y el texto en cada frase.
   *
   * Con 760 la banda ocupa el 50-60%: justo debajo de la barbilla en los planos
   * medios, donde la mirada ya esta puesta. Sigue muy por encima de la interfaz
   * de la plataforma, que ocupa los 400 px inferiores.
   *
   * Esto **desplazo el rotulo**, que vivia en esa franja: ahora va debajo (ver
   * `BigTitle`). El subtitulo es la capa permanente y se queda con el mejor
   * sitio; el rotulo es un golpe de dos segundos y cede.
   */
  captionBottom: 760,
  /** Margen inferior extremo que citan algunas fuentes (35%). Solo para
   *  comprobar si un elemento critico sobrevive al peor caso. */
  safeBottomExtremo: 672,
} as const;

/**
 * El alto útil de un tablero **ya no se calcula aquí**: vive en
 * `src/brand/franja.ts`, derivado de `franja.json`, que es el único sitio donde
 * está declarada la franja del subtítulo. Esto era la quinta copia del mismo
 * número —`layout.safe.bottom + layout.captionBand`— y encima no lo leía nadie.
 */

/** Paleta canónica de `tokens.css`. Los hex no se ajustan "a ojo" para video. */
export const color = {
  richBlack: "#0B0B0F",
  navy: "#252A44",
  navyHi: "#333A5C",
  gold: "#fad02c",
  deepGold: "#B8860B",
  secondaryBlue: "#8facc5",
  lightNeutral: "#e9eaec",
  white: "#ffffff",
  /**
   * Rojo profundo. **No está prohibido** — lo estuvo por un error de lectura
   * mío: el rojo no aparece en las 26 láminas del canon y yo convertí esa
   * ausencia observada en una regla de marca. Jaime lo corrigió: *«acá no me
   * importa que haya rojo; eso se debe a un error común en otra parte, no
   * extrapoles»*.
   *
   * El criterio no es «sin rojo»: es **coherente con los colores**. La paleta
   * es oscura y desaturada —navy, negro, azul pizarra— con el oro como único
   * tono vivo. Un rojo que pertenece a esa familia es oscuro y apagado, como
   * este `#6E2233`; uno de semáforo compite con el oro por la atención y rompe
   * la jerarquía, que es lo que de verdad hay que proteger.
   *
   * Dicho de otro modo: el oro dice **mira aquí**. Si otro color grita igual de
   * fuerte, ya no lo dice nadie.
   */
  diagnosticDeficit: "#6E2233",
} as const;

/** Rampa secuencial oro→navy para datos, con un único tono de contraste. */
export const viz = {
  ramp: ["#fad02c", "#D4AC22", "#B8860B", "#7C6A38", "#4A4E62", "#252A44"],
  contrast: color.secondaryBlue,
} as const;

/**
 * Los dos modos del sistema. **Nunca se mezclan dentro de una misma pieza**: la
 * superficie declara quién está hablando.
 *
 * Es también el eje que da identidad propia a cada ad sin romper la familia, y
 * encaja con los pilares del playbook: CONNECT es Jaime hablando (Guide), y
 * EDUCATE / SOCIAL PROOF / SELL son los datos hablando (Evidence).
 */
export const mode = {
  /** "The data speaks." Negro o navy, serif con peso, oro a máximo contraste. */
  evidence: {
    ground: color.richBlack,
    surface: color.navy,
    text: color.white,
    textSecondary: color.secondaryBlue,
    /** Solo para lo que el espectador debe atender. Oro decorativo prohibido. */
    accent: color.gold,
    hairline: "rgba(255,255,255,.15)",
    rule: "rgba(250,208,44,.3)",
  },
  /** "Jaime speaks." Neutro claro, prosa aireada, azul secundario estructurando. */
  guide: {
    ground: color.lightNeutral,
    surface: color.white,
    text: color.richBlack,
    textSecondary: color.navy,
    /** En Guide el acento es navy: el oro no vive en esta superficie. */
    accent: color.navy,
    hairline: "rgba(37,42,68,.18)",
    rule: "rgba(37,42,68,.25)",
  },
} as const;

export type Mode = keyof typeof mode;

/**
 * Deliberadamente `string` y no las literales que infiere `as const`: el tono y
 * el acento sobrescriben estos campos, así que el tipo tiene que admitir
 * cualquier color de la paleta.
 */
export type ModeTokens = {
  ground: string;
  surface: string;
  text: string;
  textSecondary: string;
  accent: string;
  hairline: string;
  rule: string;
};

/**
 * Fondos alternativos dentro de cada modo.
 *
 * No todo tablero se ve igual. El modo decide QUIÉN habla; el tono decide sobre
 * qué superficie, y da variedad entre piezas sin salirse de la paleta. Todos
 * los valores son tokens del canon: no hay grises inventados.
 */
export const tone = {
  evidence: {
    /** Negro máximo. La gravedad por defecto. */
    base: color.richBlack,
    /** Navy: gris azulado, menos severo, bueno para tableros densos. */
    raised: color.navy,
    /** Navy claro: el más aireado de los oscuros. */
    high: color.navyHi,
  },
  guide: {
    base: color.lightNeutral,
    raised: color.white,
    high: color.lightNeutral,
  },
} as const;

export type Tone = keyof (typeof tone)["evidence"];

/**
 * Acentos elegibles. El oro sigue reservado a lo que el espectador debe
 * atender; para tableros que solo explican, el azul secundario baja el volumen
 * sin romper el sistema.
 */
export const accentChoice = {
  gold: color.gold,
  blue: color.secondaryBlue,
  deepGold: color.deepGold,
  navy: color.navy,
} as const;

export type Accent = keyof typeof accentChoice;

/**
 * Escala tipográfica. Conserva las proporciones e interlineados del sistema web
 * y sube los cuerpos para lectura en móvil a distancia de brazo.
 */
export const size = {
  displayXl: 108,
  displayL: 76,
  /** Registro de hallazgo, en itálica y dorado. */
  displayM: 52,
  /** Cifras grandes aisladas: reverencia editorial, en Playfair y no en mono. */
  figure: 132,
  /** Enunciado de un nodo dentro de un tablero. */
  nodeText: 56,
  /** Un hecho relevante en mitad de la cadena, agrandado. */
  emphasis: 62,
  /** El remate de una cadena: la consecuencia pesa más que el andamiaje. */
  payoff: 68,
  /** Paso dentro de una trayectoria comparada. */
  step: 34,
  body: 38,
  labelMono: 26,
  dataTabular: 34,
  source: 22,
} as const;

export const lineHeight = {
  displayXl: 0.93,
  displayL: 1.08,
  displayM: 1.2,
  body: 1.7,
  data: 1.6,
} as const;

/**
 * Tracking. El display lleva tracking NEGATIVO y caja mixta — versales con
 * tracking amplio es el registro de la etiqueta mono, nunca el del titular.
 */
/**
 * Texto sobre video. Valores de la investigacion de legibilidad en movil,
 * escalados de la referencia habitual (1080 de ancho).
 *
 * El minimo practico esta sobre 55 px para subtitulo; por debajo se pierde a
 * distancia de brazo. Los rotulos suben bastante mas porque compiten con la
 * imagen, no con papel en blanco.
 */
export const videoText = {
  /** Subtitulo. Nunca por debajo de esto. */
  caption: 62,
  /** Rotulo normal. */
  title: 96,
  /** Rotulo de remate. */
  titleBig: 128,
  /** Rotulo de gran formato para componer detras del sujeto. */
  behind: 210,
  /** Peso: manda sobre el cuerpo para la legibilidad. */
  weight: 800,
  /** Tracking ligeramente abierto: en versales y peso alto, junta demasiado. */
  tracking: "0.01em",
} as const;

export const tracking = {
  display: "-0.022em",
  labelMono: "0.2em",
  body: "0em",
} as const;

export const weight = {
  regular: 400,
  medium: 500,
  semibold: 600,
} as const;

/** Escala de espaciado sobre base 4, duplicada para la superficie de video. */
export const space = [8, 16, 24, 40, 64, 104, 168] as const;

/**
 * Duraciones de ANIMACIÓN en frames.
 *
 * **No hay techo.** La duracion la decide el tiempo de lectura: si una entrada
 * necesita 15 frames para leerse, lleva 15. Lo que si es regla, y es de
 * registro y no de duracion, es que no haya rebote ni micro-animacion
 * juguetona. Estos valores son el ritmo por defecto, no un limite.
 */
export const duration = {
  /**
   * 0,15 s — la transición estándar del sistema.
   *
   * No se llama `transition`: el linter de Remotion toma esa propiedad por una
   * transición CSS y avisa de animación no pura, que aquí sería un falso
   * positivo — esto es una constante en frames, no un estilo.
   */
  standard: 5,
  /** 0,27 s — entrada de un elemento en video. */
  entry: 8,
  /** 0,2 s — entrada rapida, para lo que no lleva texto que leer. */
  max: 6,
} as const;

/**
 * Frames que un texto necesita para poder LEERSE en pantalla.
 *
 * Es la diferencia de medio mas importante: la web es
 * autopaso — el lector decide cuánto mira — y el video no. Un dato que no da
 * tiempo a leer no está en el video aunque esté en el frame.
 *
 * ~2,8 palabras/segundo es cómodo cuando el espectador además está escuchando.
 * En montaje final estos tiempos los sustituye el anclaje al transcript; esto es
 * el suelo por defecto, no el objetivo.
 */
export const readingFrames = (text: string): number => {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(36, Math.ceil((words / 2.8) * FPS));
};

/**
 * Ritmo de CORTE en frames. Es montaje, no animación: no le aplica el techo de
 * 0,2 s, que regula cuánto dura el movimiento de un elemento.
 */
/** Separación vertical entre nodos de un tablero. */
export const gap = {
  tight: 40,
  normal: 64,
  loose: 88,
} as const;

export const beat = {
  /** Cambio de toma por defecto: 3 s. */
  default: 90,
  /** CONNECT sostiene el plano — cortar cada 3 s destruye la intimidad. */
  connect: 180,
  /** Separación entre entradas encadenadas dentro de un mismo plano. */
  stagger: 10,
  /**
   * Silencio antes del remate. Estructuralmente el último elemento de una
   * cadena no es uno más: es la consecuencia. Entra después de una pausa
   * porque una cadena que informa a ritmo constante no aprieta.
   */
  hold: 22,
} as const;

/**
 * Easing.
 *
 * El sistema admite **linear o ease-out, y nada más**. Quedan prohibidos el
 * rebote, el wiggle y cualquier micro-animación juguetona; también el
 * ease-in-out, que no está en la lista. Todo movimiento llega y se queda.
 */
export const ease = {
  linear: Easing.linear,
  /** easeOutCubic. La curva de salida del sistema. */
  out: Easing.bezier(0.33, 1, 0.68, 1),
} as const;

/** Segundos → frames. Usar solo en el borde del sistema (props, EDL). */
export const seconds = (s: number): number => Math.round(s * FPS);
