import React from "react";
import {
  AbsoluteFill,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { color } from "../brand/tokens";

/**
 * El fotomontaje de fondo: una **placa** de `public/fondos/`.
 *
 * Las placas las genera Jaime, y cada una dice lo que dice su beat — el
 * corredor de archivadores con un solo cajón enfrente, las columnas que se
 * acumulan hacia el fondo, la brecha que se abre entre dos masas. `ads/fondos.json`
 * dice qué placa sirve a qué beat, y no se elige a ojo: *«todas tienen en común
 * que acompañan la intención comunicativa»*.
 *
 * ## Hubo un collage generado aquí dentro y se borró
 *
 * Intenté componer el fondo con SVG: rectángulos alineados a la retícula,
 * tramas de medio tono, flechas, papel rasgado. Jaime: *«el collage procedural
 * se borra, estaba muy feo»*, y tenía razón por cuatro motivos que conviene
 * dejar escritos para no volver a intentarlo:
 *
 * 1. **No tenía profundidad.** Formas planas sobre un plano. Las placas llevan
 *    perspectiva de un punto y eso mete un *espacio* en el cuadro, no una
 *    textura.
 * 2. **No decía nada.** Un corredor con un cajón solo enfrente de una pared
 *    llena **argumenta**; veintiséis rectángulos en la paleta correcta son
 *    decoración con los colores de la marca.
 * 3. **La textura era falsa.** Patrones vectoriales con un filtro de ruido
 *    encima se leen como digital. Las placas tienen fibra de papel y trama
 *    impresa de verdad.
 * 4. **No dejaba sitio.** Ruido en todo el cuadro obligaba al panel a taparlo
 *    entero. Las placas reservan una zona tranquila —la banda clara, la masa
 *    negra— donde el texto entra sin pelear.
 *
 * Lo que sí sobrevive de aquel intento es la regla que lo mató: **retícula
 * estricta, y lo torcido torcido con intención**. Vale para el panel y las
 * cintas de aquí abajo.
 */
export type FondoProps = {
  /** Placa en `public/fondos/`, sin extensión. Ver `ads/fondos.json`. */
  placa: string;
  /** Fondo de base bajo la placa, por si no cubre. */
  suelo?: string;
  /** Opacidad de la placa. 1 por defecto; se baja si el texto no respira. */
  fuerza?: number;
  /**
   * Deriva lenta: sobre cuántos frames la placa se acerca un 6%.
   *
   * Jaime pidió *«más color y movimiento»*. Un fondo quieto detrás de un tablero
   * que se construye deja la mitad del cuadro muerta; una deriva de 6% repartida
   * por toda la duración **no se nota mientras pasa** —que es la regla del
   * acercamiento, aprendizaje 27— pero el plano deja de estar clavado.
   *
   * Sin valor, no hay movimiento: el fondo de una portada quieta se queda quieto.
   */
  deriva?: number;
  /**
   * Recorte geométrico de la placa. Jaime: *«la placa puede ser el fondo, pero
   * recortada en una figura geométrica que respete la estética»*.
   *
   * Es la diferencia entre **collage y papel pintado**. En el canon la
   * fotografía nunca cubre el cuadro entero: aparece como un fragmento con
   * bordes rectos y diagonales, y el resto es plano de color. A sangre completa
   * la placa deja de ser un elemento compuesto y pasa a ser un fondo.
   *
   * Los ángulos salen del juego corto de siempre —0° y ±45°—, así que el
   * recorte respeta la retícula aunque la rompa.
   */
  recorte?: Recorte;
};

/**
 * Las formas del recorte, en porcentaje del cuadro. Todas de lados rectos: la
 * curva no pertenece a este vocabulario salvo en los discos, que van dentro de
 * la propia placa.
 */
export type Recorte =
  | "lleno"      // a sangre; sólo para cortinillas, donde la placa ES el plano
  | "banda"      // franja horizontal ancha, ligeramente inclinada
  | "cuna"       // cuña diagonal desde una esquina
  | "columna"    // columna vertical a un lado
  | "esquina";   // triángulo grande desde arriba a la derecha

const RECORTE: Record<Recorte, string | undefined> = {
  lleno: undefined,
  banda: "polygon(0% 18%, 100% 10%, 100% 74%, 0% 82%)",
  cuna: "polygon(0% 0%, 100% 0%, 100% 46%, 0% 88%)",
  columna: "polygon(52% 0%, 100% 0%, 100% 100%, 44% 100%)",
  esquina: "polygon(38% 0%, 100% 0%, 100% 100%, 78% 100%)",
};

export const Fondo: React.FC<FondoProps> = ({
  placa,
  suelo = color.richBlack,
  fuerza = 1,
  deriva,
  recorte = "lleno",
}) => {
  const frame = useCurrentFrame();
  const escala = deriva
    ? interpolate(frame, [0, deriva], [1, 1.06], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 1;
  return (
    <AbsoluteFill
      style={{
        backgroundColor: suelo,
        overflow: "hidden",
        clipPath: RECORTE[recorte],
      }}
    >
      <Img
        src={staticFile(`fondos/${placa}.png`)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          opacity: fuerza,
          transform: `scale(${escala})`,
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * El panel de contenido: bloque opaco y **girado** sobre la placa.
 *
 * Es la pieza que ordena el canon, y **lo único que rompe la retícula**. Todo
 * el texto vive dentro; la placa sólo asoma por los bordes. El giro es la
 * ruptura deliberada — por eso es de un par de grados y por eso es la única: si
 * el fondo también estuviera girado, el panel no destacaría de nada.
 *
 * En los tableros de datos va a `giro={0}`: sostiene cifras, y ahí lo torcido
 * son sólo las cintas.
 */
export const Panel: React.FC<{
  children: React.ReactNode;
  /** Grados. Uno o dos bastan: es tensión, no descuido. */
  giro?: number;
  fondo?: string;
  style?: React.CSSProperties;
}> = ({ children, giro = -1.4, fondo = color.richBlack, style }) => (
  <div
    style={{
      position: "absolute",
      backgroundColor: fondo,
      transform: `rotate(${giro}deg)`,
      ...style,
    }}
  >
    {children}
  </div>
);

/**
 * La cinta: banda girada con texto en negro encima.
 *
 * Es el recurso más reconocible del canon — la pegatina que cruza el panel. El
 * texto va SIEMPRE en negro sobre el color, nunca al revés: el color es la
 * superficie y por eso el bloque se lee antes que la palabra.
 */
export const Cinta: React.FC<{
  children: React.ReactNode;
  tinte?: string;
  giro?: number;
  cuerpo?: number;
  style?: React.CSSProperties;
}> = ({ children, tinte = color.gold, giro = -2.2, cuerpo = 58, style }) => (
  <div
    style={{
      backgroundColor: tinte,
      color: color.richBlack,
      padding: "0.2em 0.6em",
      transform: `rotate(${giro}deg)`,
      whiteSpace: "nowrap",
      textTransform: "uppercase",
      fontSize: cuerpo,
      lineHeight: 1.12,
      ...style,
    }}
  >
    {children}
  </div>
);
