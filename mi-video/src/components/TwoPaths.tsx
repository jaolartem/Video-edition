import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { MotionSound } from "./MotionSound";
import { franja } from "../brand/franja";
import {
  beat,
  color,
  duration,
  ease,
  layout,
  lineHeight,
  mode as modes,
  readingFrames,
  size,
  tracking,
  weight,
  type Mode,
  type ModeTokens,
} from "../brand/tokens";

type ComparedPathBase = {
  /** Nombre de la trayectoria, p.ej. "Por defecto". */
  label: string;
  /** Los pasos que la componen. Dos a cuatro caben legibles en media columna. */
  steps: string[];
  /** Dónde termina. */
  outcome: string;
};

/** Una cifra de resultado nunca aparece sin fuente. Lo garantiza el tipo. */
export type ComparedPath =
  | (ComparedPathBase & { figure?: never; source?: never })
  | (ComparedPathBase & { figure: string; source: string });

export type TwoPathsProps = {
  /**
   * Las condiciones iniciales, comunes a las dos trayectorias. El playbook
   * exige que el punto de partida sea el mismo: si difiere, la comparación no
   * es honesta.
   */
  start: string;
  /**
   * El horizonte temporal compartido. **Obligatorio.** El playbook exige "the
   * same time horizon" para que la comparación sea válida, así que el
   * componente no se puede instanciar sin declararlo.
   */
  horizon: string;
  byDefault: ComparedPath;
  deliberate: ComparedPath;
  /**
   * Qué condición cambiaría la comparación. **Obligatorio.** El playbook
   * prohíbe presentar el camino deliberado como universalmente superior sin
   * condiciones del caso concreto; hacerlo prop requerido impide que se caiga.
   */
  condition: string;
  /** La diferencia acumulada entre ambas. Cifra y fuente, o ninguna de las dos. */
  difference?: { figure: string; source: string };
  mode?: Mode;
  title?: string;
  /**
   * Emite el efecto de sonido de cada movimiento. **Requiere los ficheros de
   * `public/sfx/`**, que aún no existen — por eso está apagado por defecto.
   */
  sound?: boolean;
};

const FORK_HEIGHT = 72;

/**
 * Separación entre el paso de una trayectoria y el equivalente de la otra.
 * Medio segundo: suficiente para que el ojo registre que son la misma decisión
 * resuelta de dos maneras, no dos frases sueltas.
 */
const PAIR_STAGGER = 14;

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
  const frame = useCurrentFrame();
  const t = modes[mode];

  /**
   * Los pasos se construyen INTERCALADOS, no una columna entera y luego la
   * otra. El argumento no es "aquí está el camino A y aquí el B": es que en
   * cada decisión los dos hacen algo distinto. Se ve cuando el paso `i` de
   * ambas aparece casi a la vez y la bifurcación se ensancha delante del
   * espectador. Revelar cada columna de golpe convierte la divergencia en dos
   * listas paralelas, que es otra cosa y más floja.
   */
  const timing = React.useMemo(() => {
    const startAt = 0;
    const forkAt = startAt + readingFrames(start);
    const stepCount = Math.max(byDefault.steps.length, deliberate.steps.length);

    const pairs: { left: number; right: number }[] = [];
    let cursor = forkAt + duration.standard;

    for (let i = 0; i < stepCount; i++) {
      const left = cursor;
      const right = cursor + PAIR_STAGGER;
      pairs.push({ left, right });
      const dwell = Math.max(
        readingFrames(byDefault.steps[i] ?? ""),
        readingFrames(deliberate.steps[i] ?? ""),
      );
      cursor = right + dwell;
    }

    /** Pausa antes del resultado: la consecuencia no llega a ritmo de paso. */
    const outcomeAt = cursor + beat.hold;
    const differenceAt =
      outcomeAt +
      Math.max(
        readingFrames(byDefault.outcome),
        readingFrames(deliberate.outcome),
      );

    return { startAt, forkAt, pairs, outcomeAt, differenceAt };
  }, [start, byDefault, deliberate]);

  const enter = (frameAt: number): number =>
    interpolate(frame, [frameAt, frameAt + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  const forkProgress = interpolate(
    frame,
    [timing.forkAt, timing.forkAt + duration.standard],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease.linear },
  );

  /**
   * El raíl de cada columna crece conforme se recorren los pasos: es el camino
   * siendo andado, no un borde decorativo. Va en lineal a propósito — el
   * avance del tiempo no acelera ni frena.
   */
  const railProgress = (side: "left" | "right"): number => {
    const first = timing.pairs[0];
    const last = timing.pairs[timing.pairs.length - 1];
    if (!first || !last) {
      return 0;
    }
    return interpolate(
      frame,
      [first[side], last[side] + duration.entry],
      [0, 1],
      {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: ease.linear,
      },
    );
  };

  /**
   * El sistema NO tiene rojo semántico: está prohibido fuera de la cifra de
   * estado de la FNA. La distinción se hace con oro —aquello que el espectador
   * debe atender— frente al azul secundario. Es mejor restricción que el rojo:
   * obliga a que el acento señale la acción en lugar de pintar la pérdida.
   */
  const deliberateInk = t.accent;
  const defaultInk = mode === "evidence" ? color.secondaryBlue : color.navy;

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      <AbsoluteFill
        style={{
          paddingTop: layout.safe.top,
          /** Se descuenta la banda de subtítulos: también se ven. */
          paddingBottom: franja.reserva,
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          display: "flex",
          flexDirection: "column",
        }}
      >
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
            opacity: enter(timing.startAt),
            transform: `translateY(${(1 - enter(timing.startAt)) * 12}px)`,
          }}
        >
          <Label color={t.accent}>Mismo punto de partida</Label>
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
          <div
            style={{
              fontFamily: fontFamily.data,
              fontSize: size.source,
              letterSpacing: tracking.labelMono,
              textTransform: "uppercase",
              color: t.textSecondary,
              marginTop: 14,
            }}
          >
            {`Horizonte · ${horizon}`}
          </div>
        </div>

        <Fork
          progress={forkProgress}
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
          <PathColumn
            path={byDefault}
            tokens={t}
            ink={defaultInk}
            stepAt={timing.pairs.map((p) => p.left)}
            railProgress={railProgress("left")}
            outcomeProgress={enter(timing.outcomeAt)}
            enter={enter}
          />
          <PathColumn
            path={deliberate}
            tokens={t}
            ink={deliberateInk}
            stepAt={timing.pairs.map((p) => p.right)}
            railProgress={railProgress("right")}
            outcomeProgress={enter(timing.outcomeAt)}
            enter={enter}
            emphasized
          />
        </div>

        {difference ? (
          <div
            style={{
              marginTop: 26,
              opacity: enter(timing.differenceAt),
              display: "flex",
              alignItems: "baseline",
              gap: 20,
            }}
          >
            <Label color={t.textSecondary}>Diferencia acumulada</Label>
            <div
              style={{
                fontFamily: fontFamily.display,
                fontSize: size.displayL,
                fontWeight: weight.semibold,
                letterSpacing: tracking.display,
                color: t.accent,
                lineHeight: 1,
              }}
            >
              {difference.figure}
            </div>
            <div
              style={{
                fontFamily: fontFamily.data,
                fontSize: size.source,
                letterSpacing: tracking.labelMono,
                textTransform: "uppercase",
                color: t.textSecondary,
              }}
            >
              {difference.source}
            </div>
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
      </AbsoluteFill>

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

const Label: React.FC<{ color: string; children: React.ReactNode }> = ({
  color: ink,
  children,
}) => (
  <div
    style={{
      fontFamily: fontFamily.data,
      fontSize: size.labelMono,
      fontWeight: weight.medium,
      letterSpacing: tracking.labelMono,
      textTransform: "uppercase",
      color: ink,
    }}
  >
    {children}
  </div>
);

/**
 * La bifurcación en diagonal. La asimetría diagonal es recurso obligatorio del
 * sistema en composiciones editoriales, y aquí además es literal: el dibujo ES
 * el argumento — dos trayectorias que se separan desde el mismo origen.
 */
const Fork: React.FC<{
  progress: number;
  defaultInk: string;
  deliberateInk: string;
}> = ({ progress, defaultInk, deliberateInk }) => {
  const w = layout.width - (layout.safe.left + layout.safe.right);
  const mid = w / 2;

  return (
    <svg
      width={w}
      height={FORK_HEIGHT}
      viewBox={`0 0 ${w} ${FORK_HEIGHT}`}
      style={{ display: "block", flexShrink: 0, marginTop: 16 }}
    >
      <path
        d={`M ${mid} 0 L ${w * 0.25} ${FORK_HEIGHT}`}
        stroke={defaultInk}
        strokeWidth={2}
        fill="none"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - progress}
      />
      <path
        d={`M ${mid} 0 L ${w * 0.75} ${FORK_HEIGHT}`}
        stroke={deliberateInk}
        strokeWidth={2}
        fill="none"
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - progress}
      />
    </svg>
  );
};

const PathColumn: React.FC<{
  path: ComparedPath;
  tokens: ModeTokens;
  ink: string;
  /** Frame de entrada de cada paso. Uno por paso, en orden. */
  stepAt: number[];
  railProgress: number;
  outcomeProgress: number;
  enter: (frameAt: number) => number;
  emphasized?: boolean;
}> = ({
  path,
  tokens,
  ink,
  stepAt,
  railProgress,
  outcomeProgress,
  enter,
  emphasized = false,
}) => (
  <div
    style={{
      flex: 1,
      minWidth: 0,
      position: "relative",
      backgroundColor: tokens.ground,
      padding: "26px 26px 26px 29px",
      display: "flex",
      flexDirection: "column",
    }}
  >
    {/* El raíl: el camino recorrido hasta ahora. */}
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        bottom: 0,
        width: emphasized ? 3 : 2,
        backgroundColor: ink,
        transform: `scaleY(${railProgress})`,
        transformOrigin: "top",
      }}
    />

    <div style={{ opacity: enter(stepAt[0] ?? 0) }}>
      <Label color={ink}>{assertShort(path.label, "label", "TwoPaths.label")}</Label>
    </div>

    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 12,
        marginTop: 20,
        flex: 1,
      }}
    >
      {path.steps.map((step, index) => {
        const progress = enter(stepAt[index] ?? 0);
        return (
          <div
            key={step}
            style={{
              fontFamily: fontFamily.body,
              fontSize: size.step,
              lineHeight: 1.45,
              color: tokens.textSecondary,
              opacity: progress,
              transform: `translateY(${(1 - progress) * 10}px)`,
            }}
          >
            {assertShort(step, "statement", "TwoPaths.step")}
          </div>
        );
      })}
    </div>

    <div
      style={{
        marginTop: 22,
        paddingTop: 18,
        borderTop: `1px solid ${tokens.hairline}`,
        opacity: outcomeProgress,
      }}
    >
      <div
        style={{
          fontFamily: fontFamily.display,
          fontSize: size.body,
          fontWeight: emphasized ? weight.semibold : weight.regular,
          letterSpacing: tracking.display,
          lineHeight: lineHeight.displayM,
          color: tokens.text,
          /**
           * Reserva de dos líneas para que los filetes de resultado queden a la
           * misma altura en ambas columnas. Sin esto los bloques se anclan
           * abajo, el resultado de dos líneas sube su filete y el de una lo
           * baja: el ojo deja de comparar como con como, que es lo único que
           * este tablero tiene que hacer.
           */
          minHeight: size.body * lineHeight.displayM * 2,
        }}
      >
        {assertShort(path.outcome, "outcome", "TwoPaths.outcome")}
      </div>

      {path.figure === undefined ? null : (
        <>
          <div
            style={{
              fontFamily: fontFamily.display,
              fontSize: size.displayL,
              fontWeight: weight.semibold,
              letterSpacing: tracking.display,
              color: ink,
              lineHeight: 1,
              marginTop: 14,
            }}
          >
            {path.figure}
          </div>
          <div
            style={{
              fontFamily: fontFamily.data,
              fontSize: size.source,
              letterSpacing: tracking.labelMono,
              textTransform: "uppercase",
              color: tokens.textSecondary,
              marginTop: 10,
            }}
          >
            {path.source}
          </div>
        </>
      )}
    </div>
  </div>
);
