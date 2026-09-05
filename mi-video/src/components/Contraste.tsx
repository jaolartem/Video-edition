import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { fontFamily } from "../brand/fonts";
import { color, layout } from "../brand/tokens";

/**
 * **La comparación como texto fuerza, no como tablero.**
 *
 * Petición de Jaime: *«para la comparación no quiero un tablero, quiero el
 * texto fuerza comparando como animación»*. Y venía de una queja concreta sobre
 * el reel 2: *«no queda en pantalla lo que se queda el electricista y lo que se
 * queda el empresario»*.
 *
 * Un tablero resuelve eso pero **le quita el plano**: Jaime desaparece del
 * cuadro durante veinte segundos justo cuando está contando quién es cada uno.
 * Aquí las dos cifras aterrizan **encima del plano**, cada una cuando la voz la
 * dice, y **se quedan las dos** — que es lo que hace que sea una comparación y
 * no dos datos seguidos.
 *
 * ## Por qué las dos se quedan
 *
 * Si la primera se va cuando entra la segunda, el espectador tiene que
 * recordar el 44 para restarlo del 67, y a velocidad de scroll no lo hace. La
 * comparación existe **cuando los dos números están en pantalla a la vez**; lo
 * demás es una secuencia de cifras.
 *
 * ## Registro
 *
 * Navy el camino por defecto, oro el otro: la distinción del canon entre lo que
 * pasa y lo que hay que mirar, sin semáforo —no hay rojo en el sistema—. Bloques
 * planos, condensada pesada en versales, y la etiqueta encima en Montserrat
 * para que se sepa de quién es cada cifra sin leer el subtítulo.
 *
 * Va en la banda alta, por encima de la cara (24–40%) y muy lejos de la de
 * subtítulos (50–60%): las tres capas caben sin pisarse.
  * @clase tablero
*/
export type ContrasteProps = {
  izq: { etiqueta: string; cifra: string; at: number; de100?: number; placa?: string };
  der: { etiqueta: string; cifra: string; at: number; de100?: number; placa?: string };
  /** Una línea debajo, con la condición que hace comparables las dos. */
  pie?: string;
};

const Lado: React.FC<{
  etiqueta: string;
  cifra: string;
  at: number;
  /** Cuanto le queda de cada $100. Se dibuja como barra, no como texto. */
  de100?: number;
  /** Placa del collage detras, con un crecimiento lento. */
  placa?: string;
  oro?: boolean;
  desde: "izq" | "der";
}> = ({ etiqueta, cifra, at, de100, placa, oro, desde }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  if (p <= 0) return null;
  const dx = (desde === "izq" ? -1 : 1) * (1 - p) * layout.width * 0.3;
  /**
   * **La barra ES la idea.** Jaime: *«no busco un CC animado, busco representar
   * las ideas mas fuertes: lo que le queda a cada uno luego de vender 100
   * dolares»*. Cien es el ancho entero; lo que le queda es lo que se llena. Se
   * ve la diferencia sin leer una cifra, que es lo que una comparacion tiene que
   * conseguir a velocidad de scroll.
   */
  const lleno = interpolate(frame, [at + 6, at + 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  /**
   * **La placa crece despacio.** Jaime: *«imagenes que crezcan o disminuyan, no
   * buscamos una animacion compleja; buscamos color y movimiento para no perder
   * audiencias»*. Sale del collage que ya esta aprobado en `public/fondos/`, asi
   * que no hay material nuevo que licenciar ni que revisar.
   */
  const zoom = interpolate(frame, [at, at + 150], [1, 1.12], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        flex: 1,
        backgroundColor: oro ? color.gold : color.navy,
        padding: "18px 20px 24px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        opacity: p,
        overflow: "hidden",
        position: "relative",
        transform: `translateX(${dx.toFixed(1)}px)`,
      }}
    >
      {placa ? (
        <Img
          src={staticFile(`fondos/${placa}.png`)}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
            opacity: 0.28,
            transform: `scale(${zoom.toFixed(3)})`,
          }}
        />
      ) : null}
      <div
        style={{
          fontFamily: fontFamily.video,
          fontSize: 30,
          fontWeight: 900,
          letterSpacing: "0.02em",
          textTransform: "uppercase",
          textAlign: "center",
          lineHeight: 1.1,
          color: oro ? color.richBlack : color.secondaryBlue,
        }}
      >
        {etiqueta}
      </div>
      <div
        style={{
          fontFamily: fontFamily.bloque,
          // Anton gasta ~0,47 em por caracter en versales, medido sobre render.
          fontSize: Math.min(
            140,
            (layout.width / 2 - layout.safe.left - 52) / (cifra.length * 0.47),
          ),
          lineHeight: 0.94,
          whiteSpace: "nowrap",
          textTransform: "uppercase",
          color: oro ? color.richBlack : color.lightNeutral,
        }}
      >
        {cifra}
      </div>
      {de100 ? (
        <div
          style={{
            position: "relative",
            width: "100%",
            height: 22,
            backgroundColor: oro ? "rgba(11,11,15,.22)" : "rgba(233,234,236,.18)",
          }}
        >
          <div
            style={{
              position: "absolute",
              inset: 0,
              width: `${(de100 * lleno).toFixed(1)}%`,
              backgroundColor: oro ? color.richBlack : color.lightNeutral,
            }}
          />
        </div>
      ) : null}
      {de100 ? (
        <div
          style={{
            fontFamily: fontFamily.data,
            fontSize: 22,
            letterSpacing: "0.18em",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.secondaryBlue,
          }}
        >
          de cada $100
        </div>
      ) : null}
    </div>
  );
};

export const Contraste: React.FC<ContrasteProps> = ({ izq, der, pie }) => {
  const frame = useCurrentFrame();
  const hayPie = interpolate(frame, [der.at + 6, der.at + 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <AbsoluteFill
      style={{
        // Banda alta: por encima de la cara y muy lejos de los subtitulos.
        paddingTop: layout.height * 0.1,
        paddingLeft: layout.safe.left,
        paddingRight: layout.safe.right,
        display: "flex",
        flexDirection: "column",
        justifyContent: "flex-start",
        alignItems: "stretch",
      }}
    >
      <div style={{ display: "flex", gap: 12 }}>
        <Lado {...izq} desde="izq" />
        <Lado {...der} desde="der" oro />
      </div>
      {pie ? (
        <div
          style={{
            marginTop: 10,
            alignSelf: "flex-start",
            backgroundColor: color.richBlack,
            color: color.lightNeutral,
            fontFamily: fontFamily.video,
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: "0.02em",
            textTransform: "uppercase",
            padding: "8px 14px",
            opacity: hayPie,
          }}
        >
          {pie}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
