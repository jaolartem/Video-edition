import React from "react";
import { fontFamily } from "../../brand/fonts";
import { color } from "../../brand/tokens";
import { azar, hacia, type Punto } from "./rig";

/**
 * **El taller del mecánico**: tablas como motores, pinza, cable y chispa.
 *
 * Lo usa `Mecanico`; no se pide aparte.
 *
 * Jaime: *«puede conectar dos tablas entre sí, simulando que la conexión es un
 * cable, y que él es mecánico de autos, conecta cables entre motores»*. La
 * tabla se dibuja como tabla —cabecera con su nombre, filas, la columna de la
 * llave— y lo que la vuelve motor es el borne de arriba, donde muerde la
 * pinza. Bloques planos de la paleta y filetes; el oro sólo pasa por el cable
 * cuando ya está conectado, que es lo que hay que mirar.
 */

/** Dónde muerde la pinza: el borne, del lado que mira al otro motor. */
export const borne = (cx: number, ancho: number, alto: number, haciaDentro: number): Punto => ({
  x: cx + haciaDentro * ancho * 0.26,
  y: -alto - 16,
});

export const Motor: React.FC<{
  cx: number;
  ancho: number;
  alto: number;
  nombre: string;
  haciaDentro: number;
  /** El borne se enciende en oro cuando le llega corriente: 0 a 1. */
  enciende: number;
}> = ({ cx, ancho, alto, nombre, haciaDentro, enciende }) => {
  const b = borne(cx, ancho, alto, haciaDentro);
  const cab = alto * 0.27;
  const izq = cx - ancho / 2;
  const cuerpo = Math.min(cab * 0.74, (ancho * 0.84) / (Math.max(nombre.length, 1) * 0.47));
  const filas = [1, 2, 3].map((i) => -alto + cab + (i * (alto - cab)) / 4);
  return (
    <g>
      <rect x={b.x - 16} y={b.y} width={32} height={18} fill={color.lightNeutral} />
      <rect x={b.x - 16} y={b.y} width={32} height={18} fill={color.gold} opacity={enciende} />
      <rect x={izq} y={-alto} width={ancho} height={alto} fill={color.richBlack} />
      <rect x={izq} y={-alto} width={ancho} height={cab} fill={color.secondaryBlue} />
      <text
        x={cx}
        y={-alto + cab / 2 + cuerpo * 0.36}
        textAnchor="middle"
        fontFamily={fontFamily.bloque}
        fontSize={cuerpo}
        fill={color.richBlack}
      >
        {nombre.toUpperCase()}
      </text>
      <g stroke={color.navyHi} strokeWidth={3}>
        {filas.map((y) => (
          <line key={y} x1={izq + 10} y1={y} x2={izq + ancho - 10} y2={y} />
        ))}
        <line x1={izq + ancho * 0.28} y1={-alto + cab} x2={izq + ancho * 0.28} y2={0} />
      </g>
      <rect x={izq} y={-alto} width={ancho} height={alto} fill="none" stroke={color.secondaryBlue} strokeWidth={4} />
    </g>
  );
};

/** Lo que mide la pinza de la punta al mango. */
export const PINZA = 54;

/** El mango de la pinza, que es de donde sale el cable y por donde se coge. */
export const mango = (punta: Punto, angulo: number): Punto => hacia(punta, angulo + 180, PINZA);

/**
 * La pinza de batería: dos palancas que se cruzan en el eje. Cerrada, las
 * mandíbulas se juntan en la punta y los mangos se abren; al apretarla, al
 * revés.
 */
export const Pinza: React.FC<{ punta: Punto; angulo: number; abre: number }> = ({ punta, angulo, abre }) => {
  const boca = 4 + abre * 13;
  const mangos = 14 - abre * 8;
  return (
    <g
      transform={`translate(${punta.x.toFixed(2)} ${punta.y.toFixed(2)}) rotate(${(-angulo).toFixed(2)})`}
      stroke={color.lightNeutral}
      strokeWidth={7}
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    >
      <path d={`M ${-boca} 0 L 0 -24 L ${mangos} ${-PINZA}`} />
      <path d={`M ${boca} 0 L 0 -24 L ${-mangos} ${-PINZA}`} />
    </g>
  );
};

/**
 * El cable entre dos puntos, con su largo: cuelga lo que le sobra y nunca
 * atraviesa el suelo. Devuelve el trazo y cómo recorrerlo.
 */
export const cable = (p0: Punto, p1: Punto, largo: number) => {
  const sobra = Math.max(0, largo - Math.hypot(p1.x - p0.x, p1.y - p0.y));
  const medio = { x: (p0.x + p1.x) / 2, y: (p0.y + p1.y) / 2 };
  const cy = Math.min(medio.y + Math.min(sobra * 0.6, 280), (-16 - p0.y - p1.y) / 2);
  const c = { x: medio.x, y: cy };
  const en = (t: number): Punto => ({
    x: (1 - t) ** 2 * p0.x + 2 * (1 - t) * t * c.x + t ** 2 * p1.x,
    y: (1 - t) ** 2 * p0.y + 2 * (1 - t) * t * c.y + t ** 2 * p1.y,
  });
  let mide = 0;
  for (let i = 1; i <= 24; i++) {
    const a = en((i - 1) / 24);
    const b = en(i / 24);
    mide += Math.hypot(b.x - a.x, b.y - a.y);
  }
  const d = `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} Q ${c.x.toFixed(2)} ${c.y.toFixed(2)} ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
  return { d, en, mide };
};

/**
 * La chispa: rayos de oro que salen del contacto y se apagan, y en la grande
 * unas brasas que caen. `t` son los fotogramas desde que saltó.
 */
export const Chispa: React.FC<{ en: Punto; t: number; grande?: boolean; semilla?: number }> = ({
  en, t, grande = false, semilla = 0,
}) => {
  const dura = grande ? 10 : 6;
  if (t < 0 || t > (grande ? 18 : dura)) return null;
  const s = Math.min(1, t / 3);
  const apaga = 1 - Math.max(0, (t - dura * 0.5) / (dura * 0.5));
  const rayos = grande ? 9 : 5;
  return (
    <g stroke={color.gold} strokeLinecap="round" fill="none">
      {apaga > 0
        ? Array.from({ length: rayos }, (_, i) => {
            const a = (i * 360) / rayos + azar(semilla + i) * 24;
            const r0 = 8 + (grande ? 22 : 10) * s;
            const r1 = r0 + (grande ? 38 : 18) * (0.5 + 0.5 * azar(semilla + i + 9)) * apaga;
            const p0 = hacia(en, a, r0);
            const p1 = hacia(en, a, r1);
            return (
              <line key={i} x1={p0.x} y1={p0.y} x2={p1.x} y2={p1.y} strokeWidth={grande ? 6 : 4} opacity={apaga} />
            );
          })
        : null}
      {grande
        ? Array.from({ length: 7 }, (_, i) => {
            const a = 100 + 160 * azar(semilla + i * 3);
            const v = 7 + 6 * azar(semilla + i * 5);
            const x = en.x + Math.sin((a * Math.PI) / 180) * v * t;
            const y = en.y + Math.cos((a * Math.PI) / 180) * v * t + 0.55 * t * t;
            const vy = Math.cos((a * Math.PI) / 180) * v + 1.1 * t;
            const vx = Math.sin((a * Math.PI) / 180) * v;
            const n = Math.hypot(vx, vy) || 1;
            return (
              <line
                key={`b${i}`}
                x1={x}
                y1={y}
                x2={x - (vx / n) * 10}
                y2={y - (vy / n) * 10}
                strokeWidth={4}
                opacity={1 - t / 18}
              />
            );
          })
        : null}
    </g>
  );
};
