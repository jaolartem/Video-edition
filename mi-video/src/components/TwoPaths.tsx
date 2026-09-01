import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { MotionSound } from "./MotionSound";
import { Cifra, Etiqueta, Fuente, Marco } from "./Canon";
import { Bifurcacion } from "./twoPaths/Bifurcacion";
import { Trayectoria } from "./twoPaths/Trayectoria";
import { horarioDe } from "./twoPaths/horario";
import {
  color,
  duration,
  ease,
  lineHeight,
  mode as modes,
  size,
  tracking,
  weight,
} from "../brand/tokens";
import type { TwoPathsProps } from "./twoPaths/tipos";

export type { ComparedPath, TwoPathsProps } from "./twoPaths/tipos";

/**
 * Dos trayectorias que salen del mismo punto y acaban en sitios distintos.
 *
 * El componente sólo **dibuja y ata**: el contrato de cumplimiento está en
 * `twoPaths/tipos`, el calendario en `twoPaths/horario`, y las dos piezas del
 * dibujo —la bifurcación y cada columna— en sus ficheros. Eran quinientas
 * líneas con las tres cosas mezcladas, y ahí es donde un cambio de ritmo se
 * lleva por delante una regla del playbook sin que se note.
 */
export const TwoPaths: React.FC<TwoPathsProps> = ({
  start,
  horizon,
  byDefault,
  deliberate,
  condition,
  difference,
  mode = "evidence",
  title,
  sound = false,
}) => {
  const t = modes[mode];
  const entra = useEntrada();

  const timing = React.useMemo(
    () => horarioDe({ start, byDefault, deliberate }),
    [start, byDefault, deliberate],
  );

  /**
   * El raíl de cada columna crece conforme se recorren los pasos. Va en lineal
   * a propósito — el avance del tiempo no acelera ni frena.
   */
  const rail = (side: "left" | "right"): number => {
    const first = timing.pairs[0];
    const last = timing.pairs[timing.pairs.length - 1];
    if (!first || !last) {
      return 0;
    }
    const desde = first[side];
    return entra(desde, last[side] + duration.entry - desde, ease.linear);
  };

  /**
   * El sistema NO tiene rojo semántico: está prohibido fuera de la cifra de
   * estado de la FNA. La distinción se hace con oro —aquello que el espectador
   * debe atender— frente al azul secundario. Es mejor restricción que el rojo:
   * obliga a que el acento señale la acción en lugar de pintar la pérdida.
   */
  const deliberateInk = t.accent;
  const defaultInk = mode === "evidence" ? color.secondaryBlue : color.navy;
  const arranca = entra(timing.startAt);

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <Marco>
        {title ? (
          <div
            style={{
              fontFamily: fontFamily.display,
              fontSize: size.displayL,
              fontWeight: weight.semibold,
              letterSpacing: tracking.display,
              lineHeight: lineHeight.displayL,
              color: t.text,
              marginBottom: 40,
            }}
          >
            {assertShort(title, "title", "TwoPaths.title")}
          </div>
        ) : null}

        <div
          style={{
            opacity: arranca,
            transform: `translateY(${(1 - arranca) * 12}px)`,
          }}
        >
          <Etiqueta tinta={t.accent}>Mismo punto de partida</Etiqueta>
          <div
            style={{
              fontFamily: fontFamily.display,
              fontSize: size.nodeText,
              letterSpacing: tracking.display,
              lineHeight: lineHeight.displayM,
              color: t.text,
              marginTop: 12,
            }}
          >
            {assertShort(start, "statement", "TwoPaths.start")}
          </div>
          {/* El horizonte compartido. Es cumplimiento, no adorno: sin el mismo
              plazo la comparación no significa nada. */}
          <Fuente tinta={t.textSecondary} style={{ marginTop: 14 }}>
            {`Horizonte · ${horizon}`}
          </Fuente>
        </div>

        <Bifurcacion
          progress={entra(timing.forkAt, duration.standard, ease.linear)}
          defaultInk={defaultInk}
          deliberateInk={deliberateInk}
        />

        <div
          style={{
            display: "flex",
            gap: 1,
            backgroundColor: t.hairline,
            /**
             * `0 0 auto`: las columnas se ajustan a su contenido en vez de
             * estirarse hasta el fondo. Estirándose, el `flex: 1` interior de
             * los pasos abría un hueco negro entre el último paso y el filete
             * de resultado. Al ajustarse, no hay sobrante que repartir: los
             * resultados siguen alineados porque ambas columnas se estiran a
             * la altura de la más alta, y el aire queda abajo de una pieza.
             */
            flex: "0 0 auto",
          }}
        >
          <Trayectoria
            path={byDefault}
            tokens={t}
            ink={defaultInk}
            stepAt={timing.pairs.map((p) => p.left)}
            railProgress={rail("left")}
            outcomeProgress={entra(timing.outcomeAt)}
            entra={entra}
          />
          <Trayectoria
            path={deliberate}
            tokens={t}
            ink={deliberateInk}
            stepAt={timing.pairs.map((p) => p.right)}
            railProgress={rail("right")}
            outcomeProgress={entra(timing.outcomeAt)}
            entra={entra}
            emphasized
          />
        </div>

        {difference ? (
          <div
            style={{
              marginTop: 26,
              opacity: entra(timing.differenceAt),
              display: "flex",
              alignItems: "baseline",
              gap: 20,
            }}
          >
            <Etiqueta tinta={t.textSecondary}>Diferencia acumulada</Etiqueta>
            <Cifra tinta={t.accent}>{difference.figure}</Cifra>
            <Fuente tinta={t.textSecondary}>{difference.source}</Fuente>
          </div>
        ) : null}

        <div
          style={{
            marginTop: 24,
            paddingTop: 20,
            borderTop: `1px solid ${t.rule}`,
            fontFamily: fontFamily.body,
            fontSize: size.source,
            lineHeight: lineHeight.body,
            color: t.textSecondary,
          }}
        >
          {assertShort(condition, "legal", "TwoPaths.condition")}
        </div>
      </Marco>

      {/**
       * El sonido se emite en el mismo frame que el movimiento que lo produce:
       * la bifurcación al abrirse, un clic por paso, un golpe al resultado.
       * Nada de colchón genérico — el sistema prohíbe el registro juguetón, y
       * un efecto que no corresponde a un movimiento es decoración.
       */}
      {sound ? (
        <>
          <MotionSound motion="fork" at={timing.forkAt} />
          {timing.pairs.map((pair, index) => (
            <React.Fragment key={index}>
              <MotionSound motion="mark" at={pair.left} />
              <MotionSound motion="mark" at={pair.right} />
            </React.Fragment>
          ))}
          <MotionSound motion="land" at={timing.outcomeAt} />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
