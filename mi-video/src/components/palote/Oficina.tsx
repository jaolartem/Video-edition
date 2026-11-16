import React from "react";
import { color } from "../../brand/tokens";
import { hacia, type Punto } from "./rig";

/**
 * **La oficina del palote**: libros, lupa, hoja, lápiz, máquina y avión de
 * papel. Lo usan `Investigar`, `Curriculum`, `Guion` y `Aplicacion`; no se
 * pide aparte.
 *
 * Jaime: *«parte de research, resume, script, todo eso tiene que estar el
 * muñequito haciendo cada una de esas acciones; es parte también del
 * proceso»*. Son los objetos de ese proceso y nada más: bloques planos de la
 * paleta, el filete claro del personaje y ni una sombra. El oro va sólo en lo
 * que sale —el avión de la solicitud—, que es lo que hay que mirar.
 */

const TRAZO = 5;
const f2 = (n: number) => n.toFixed(2);

/** Un libro de canto, con su lomo: `y` es su base. */
export const Libro: React.FC<{ x: number; y: number; ancho: number; giro?: number; tono?: number }> = ({
  x, y, ancho, giro = 0, tono = 0,
}) => (
  <g transform={`translate(${f2(x)} ${f2(y)}) rotate(${f2(giro)})`} stroke={color.lightNeutral}
    strokeWidth={TRAZO} strokeLinejoin="round">
    <rect x={-ancho / 2} y={-24} width={ancho} height={24} fill={tono ? color.navyHi : color.navy} />
    <rect x={-ancho / 2 + 14} y={-24} width={10} height={24} fill={color.secondaryBlue} stroke="none" />
  </g>
);

/** La lupa: el mango sale de la mano y el cristal agranda renglones. */
export const MANGO = 52;
export const CRISTAL = 30;
export const Lupa: React.FC<{ mano: Punto; angulo: number; escala?: number; fase?: number }> = ({
  mano, angulo, escala = 1, fase = 0,
}) => {
  const c = hacia(mano, angulo, (MANGO + CRISTAL) * escala);
  const cuello = hacia(mano, angulo, MANGO * escala);
  const r = CRISTAL * escala;
  return (
    <g strokeLinecap="round">
      <line x1={mano.x} y1={mano.y} x2={cuello.x} y2={cuello.y} stroke={color.lightNeutral}
        strokeWidth={10 * escala} />
      <circle cx={c.x} cy={c.y} r={r} fill={color.richBlack} fillOpacity={0.72} />
      {[-0.42, 0, 0.42].map((d, i) => (
        <line key={d} x1={c.x - r * 0.62} x2={c.x + r * (0.3 + 0.3 * Math.sin(fase + i * 1.7))}
          y1={c.y + d * r} y2={c.y + d * r} stroke={color.secondaryBlue} strokeWidth={5 * escala} />
      ))}
      <circle cx={c.x} cy={c.y} r={r} fill="none" stroke={color.lightNeutral} strokeWidth={7 * escala} />
    </g>
  );
};

/** Lo que mide una hoja, en unidades. */
export const HOJA = { ancho: 74, alto: 96 } as const;

/**
 * Una hoja de frente, centrada en `en`: los renglones se escriben de arriba
 * abajo según `escrito` (0 a 1). Con `cara`, el hueco de la foto de un
 * currículum arriba a la izquierda.
 */
export const Hoja: React.FC<{ en: Punto; giro?: number; escrito: number; cara?: boolean; escala?: number }> = ({
  en, giro = 0, escrito, cara = false, escala = 1,
}) => {
  const { ancho: w, alto: h } = HOJA;
  const renglones = cara ? [0.42, 0.56, 0.7, 0.84] : [0.16, 0.3, 0.44, 0.58, 0.72, 0.86];
  return (
    <g transform={`translate(${f2(en.x)} ${f2(en.y)}) rotate(${f2(giro)}) scale(${f2(escala)})`}>
      <rect x={-w / 2} y={-h / 2} width={w} height={h} fill={color.lightNeutral}
        stroke={color.richBlack} strokeWidth={3} />
      {cara ? (
        <g fill={color.navy}>
          <rect x={-w / 2 + 9} y={-h / 2 + 9} width={22} height={24} />
          <rect x={-w / 2 + 37} y={-h / 2 + 12} width={26 * Math.min(1, escrito * 4)} height={6} />
          <rect x={-w / 2 + 37} y={-h / 2 + 24} width={18 * Math.min(1, escrito * 4)} height={4}
            fill={color.secondaryBlue} />
        </g>
      ) : null}
      {renglones.map((y, i) => {
        const n = renglones.length;
        const lleno = Math.min(1, Math.max(0, escrito * n - i));
        const largo = (w - 18) * (i % 3 === 2 ? 0.66 : 1) * lleno;
        return lleno > 0 ? (
          <line key={y} x1={-w / 2 + 9} x2={-w / 2 + 9 + largo} y1={-h / 2 + y * h} y2={-h / 2 + y * h}
            stroke={color.navy} strokeWidth={4} strokeLinecap="round" />
        ) : null;
      })}
    </g>
  );
};

/** El lápiz, con la punta en `punta` y el cuerpo hacia `angulo`. */
export const Lapiz: React.FC<{ punta: Punto; angulo: number }> = ({ punta, angulo }) => {
  const fin = hacia(punta, angulo, 46);
  const filo = hacia(punta, angulo, 10);
  return (
    <g strokeLinecap="round">
      <line x1={filo.x} y1={filo.y} x2={fin.x} y2={fin.y} stroke={color.secondaryBlue} strokeWidth={9} />
      <line x1={punta.x} y1={punta.y} x2={filo.x} y2={filo.y} stroke={color.lightNeutral} strokeWidth={5} />
    </g>
  );
};

/**
 * La máquina de escribir, de frente sobre su mesa: tapa al personaje de cintura
 * para abajo. `carro` corre el carro a lo ancho y `golpe` hunde una tecla; el
 * papel lo pone quien la usa, detrás, y el tablero de la mesa le tapa el pie.
 */
export const MESA = { alto: 122, ancho: 250 } as const;
/** Donde muerde el rodillo: de ahí sale el papel. */
export const RODILLO = -MESA.alto - 60;
export const Maquina: React.FC<{ carro: number; golpe: number }> = ({ carro, golpe }) => (
  <g stroke={color.lightNeutral} strokeWidth={TRAZO} strokeLinejoin="round">
    <rect x={-MESA.ancho / 2} y={-MESA.alto} width={MESA.ancho} height={26} fill={color.navy} />
    <line x1={-MESA.ancho / 2 + 18} y1={-MESA.alto + 26} x2={-MESA.ancho / 2 + 18} y2={0} />
    <line x1={MESA.ancho / 2 - 18} y1={-MESA.alto + 26} x2={MESA.ancho / 2 - 18} y2={0} />
    <path d={`M -70 ${-MESA.alto} L -56 ${-MESA.alto - 46} L 56 ${-MESA.alto - 46} L 70 ${-MESA.alto} Z`}
      fill={color.richBlack} />
    <rect x={-62 + carro} y={-MESA.alto - 60} width={124} height={14} rx={7} fill={color.navyHi} />
    {[-36, -12, 12, 36].map((x, i) => (
      <circle key={x} cx={x} cy={-MESA.alto - 18 + (golpe === i ? 3 : 0)} r={6} fill={color.secondaryBlue}
        stroke="none" />
    ))}
  </g>
);

/**
 * La hoja que se pliega en avión: `pliega` va de la hoja (0) al avión (1), de
 * perfil y mirando a `d`. El pliegue es de oro: es lo que sale.
 */
export const Avion: React.FC<{ en: Punto; pliega: number; giro: number; d: number; escala?: number }> = ({
  en, pliega, giro, d, escala = 1,
}) => {
  const k = Math.min(1, Math.max(0, pliega));
  const mezcla = (a: [number, number], b: [number, number]) =>
    `${f2(a[0] + (b[0] - a[0]) * k)} ${f2(a[1] + (b[1] - a[1]) * k)}`;
  const hoja: [number, number][] = [[-37, -48], [37, -48], [37, 48], [-37, 48]];
  const avion: [number, number][] = [[-46, -14], [54, 0], [-30, 22], [-40, 2]];
  const forma = hoja.map((p, i) => mezcla(p, avion[i]));
  return (
    <g transform={`translate(${f2(en.x)} ${f2(en.y)}) scale(${f2(d * escala)} ${f2(escala)}) rotate(${f2(giro * d)})`}>
      <path d={`M ${forma.join(" L ")} Z`} fill={color.lightNeutral} stroke={color.richBlack}
        strokeWidth={3} strokeLinejoin="round" />
      <line x1={f2(-37 * (1 - k) - 40 * k)} y1={f2(-48 * (1 - k) + 2 * k)} x2={f2(37 * (1 - k) + 54 * k)}
        y2={f2(48 * (1 - k))} stroke={color.gold} strokeWidth={5} strokeLinecap="round" opacity={0.25 + 0.75 * k} />
    </g>
  );
};
