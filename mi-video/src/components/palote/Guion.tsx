import type { Accion, Escena, Escenario } from "./accion";
import { HOJA, Hoja, MESA, Maquina, RODILLO } from "./Oficina";
import { reposo } from "./reposo";
import { CURVA, NEUTRA, Pista, alcanza, articula, rampa, type Clave, type Pose } from "./rig";
import { conVida } from "./vida";

/**
 * **Guion**: aporrea una máquina de escribir y las hojas salen volando.
 *
 * Para el *script* —lo que se escribe para que otro lo diga—. Está detrás de
 * su mesa, que le tapa de cintura abajo; teclea a dos manos desde el 8 y el
 * papel sube renglón a renglón. En el 62 la hoja está llena: la arranca de un
 * tirón, sale revoloteando hacia el borde del cuadro y entra otra. Entre hoja
 * y hoja se rasca la cabeza o mira alrededor, como quien busca la frase.
 */

const EMPIEZA = 8;
const RENGLONES = 6;
const POR_RENGLON = 9;
/** Lo que tarda una hoja entera, el tirón y la hoja nueva. */
const HOJA_LLENA = RENGLONES * POR_RENGLON;
const PAGINA = HOJA_LLENA + 12;
/** Cada cuánto golpea una tecla, alternando las manos. */
const TECLA = 3;

const claves: Clave<Pose>[] = [
  { f: 0, ...NEUTRA },
  { f: EMPIEZA, c: CURVA.suave, cuello: 8, tronco: 2, pecho: -2 },
];

/** El renglón y la hoja en que va, y si está tecleando. */
const reloj = (f: number) => {
  const t = Math.max(0, f - EMPIEZA);
  const n = Math.floor(t / PAGINA);
  const dentro = t - n * PAGINA;
  return { n, dentro, escrito: Math.min(1, dentro / HOJA_LLENA), teclea: f >= EMPIEZA && dentro < HOJA_LLENA };
};

/** La hoja `n` que sale volando: hacia `d`, girando, y se va. */
const vuela = (t: number, d: number) => ({
  x: d * (14 * t + 30 * Math.sin(t * 0.16)),
  y: RODILLO - HOJA.alto / 2 - 9 * t + 0.16 * t * t,
  giro: d * (t * 7 + 18 * Math.sin(t * 0.3)),
  opacidad: 1 - rampa(t, 26, 40),
});

const monta = (e: Escenario): Escena => {
  const pista = new Pista<Pose>(NEUTRA, claves);
  const d = -e.senal;
  const varia = reposo({ desde: EMPIEZA + PAGINA, libres: ["D", "I"], sin: ["pie"], semilla: 3 });
  const poseEn = (f: number) => {
    const p = conVida((g) => pista.en(g), f, 0.6);
    const r = reloj(f);
    const carro = 18 - 36 * ((r.escrito * RENGLONES) % 1);
    const golpe = (lado: number) =>
      r.teclea ? Math.max(0, Math.sin((Math.PI * ((f + lado * TECLA) % (2 * TECLA))) / TECLA)) : 0;
    const tecla = (x: number, lado: number) => ({ x: x + carro * 0.15, y: -MESA.alto - 22 + 10 * golpe(lado) - 10 });
    // El tirón: la derecha sube con la hoja llena y vuelve.
    const tira = r.n > 0 || f > EMPIEZA + HOJA_LLENA ? Math.sin(Math.PI * rampa(r.dentro, HOJA_LLENA, PAGINA)) : 0;
    const arriba = { x: carro + 20, y: RODILLO - HOJA.alto - 20 };
    const derecha = tecla(30, 0);
    const der = { x: derecha.x + (arriba.x - derecha.x) * tira, y: derecha.y + (arriba.y - derecha.y) * tira };
    const entra = CURVA.suave(rampa(f, 2, EMPIEZA));
    const conIzq = alcanza(p, tecla(-30, 1), entra, "I", 1);
    return varia(alcanza({ ...conIzq, cuello: conIzq.cuello - 10 * tira }, der, entra, "D", -1), f);
  };
  return {
    fotograma: (f) => {
      const pose = poseEn(f);
      const cuerpo = articula(pose);
      const r = reloj(f);
      const carro = 18 - 36 * ((r.escrito * RENGLONES) % 1);
      // El papel sube un renglón por renglón tecleado, desde el rodillo.
      const sube = (HOJA.alto * 0.14) * Math.min(RENGLONES - 1, Math.floor(r.escrito * RENGLONES));
      const centro = r.dentro < HOJA_LLENA + 2
        ? { x: carro, y: RODILLO + HOJA.alto / 2 - HOJA.alto * 0.16 - sube }
        : null;
      const volando = Array.from({ length: r.n + 1 }, (_, k) => f - (EMPIEZA + k * PAGINA + HOJA_LLENA + 2))
        .filter((t) => t >= 0 && t < 40);
      return {
        cuerpo,
        pose,
        delante: (
          <>
            {centro ? <Hoja en={centro} escrito={r.escrito} /> : null}
            <Maquina carro={carro} golpe={r.teclea ? Math.floor(f / TECLA) % 4 : -1} />
            {volando.map((t) => {
              const v = vuela(t, d);
              return (
                <g key={t} opacity={v.opacidad}>
                  <Hoja en={{ x: v.x, y: v.y }} giro={v.giro} escrito={1} escala={0.9} />
                </g>
              );
            })}
          </>
        ),
      };
    },
    sonidos: [
      { motion: "type", at: EMPIEZA },
      { motion: "whoosh", at: EMPIEZA + HOJA_LLENA + 2 },
    ],
  };
};

export const guion: Accion = { alto: 400, ancho: 360, texto: "lado", monta };
