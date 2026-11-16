import { color } from "../../brand/tokens";
import type { Accion, Escena, Escenario } from "./accion";
import { CURVA, HUESO, NEUTRA, Pista, alcanza, articula, corto, hacia, type Clave, type Pose, type Punto } from "./rig";
import { Chispa, Motor, PINZA, Pinza, borne, cable, mango } from "./Taller";
import { conVida } from "./vida";

/**
 * **Mecánico**: conecta dos tablas con pinzas de batería y salta la chispa.
 *
 * Recoge la pinza del suelo, cruza tirando del cable y la clava en el borne de
 * la otra tabla; el calambre le sacude. Para lo que relaciona dos cosas —
 * *SQL une dos tablas*.
 *
 * Jaime: *«en la parte de sql, puede conectar dos tablas entre sí, simulando
 * que la conexión es un cable, y que él es mecánico de autos»*. La primera
 * pinza ya muerde la tabla de la izquierda. Él coge la otra en el 18, cruza a
 * zancadas —cuántas, lo dice la distancia—, levanta la pinza, la descarga y en
 * ese fotograma salta la chispa: el calambre lo levanta del suelo. Se seca la
 * frente, se pone en jarras llevando el compás con el pie, y por el cable corre
 * la corriente en oro de una tabla a la otra mientras dure el tablero.
 */

/** Lo que abre la pierna al andar, en grados, y lo que avanza cada paso. */
const PASO = 18;
const ZANCADA = 2 * (HUESO.muslo + HUESO.pierna) * Math.sin((PASO * Math.PI) / 180);
const POR_PASO = 10;
const AGARRA = 18;
const ANDA = 32;
/** Cada cuánto corre un pulso por el cable, y cuánto tarda en cruzarlo. */
const PULSO = 26;
const CRUZA = 18;

const rampa = (f: number, a: number, b: number) => Math.min(1, Math.max(0, (f - a) / (b - a)));

/** El andar: las piernas siguen a la cadera por el suelo, sin patinar. */
const andar = (p: Pose, peso: number, desde: number): Pose => {
  if (peso <= 0) return p;
  const fase = (Math.PI * (p.x - desde)) / ZANCADA;
  const s = Math.sin(fase);
  const muslo = { D: PASO * s, I: -PASO * s };
  const rodilla = { D: -38 * Math.max(0, Math.cos(fase)), I: -38 * Math.max(0, -Math.cos(fase)) };
  const mezcla = (a: number, b: number) => a + (b - a) * peso;
  return {
    ...p,
    caderaD: mezcla(p.caderaD, muslo.D),
    rodillaD: mezcla(p.rodillaD, rodilla.D - 4),
    caderaI: mezcla(p.caderaI, muslo.I),
    rodillaI: mezcla(p.rodillaI, rodilla.I - 4),
    pieD: mezcla(p.pieD, 90 - muslo.D - rodilla.D),
    pieI: mezcla(p.pieI, 90 - muslo.I - rodilla.I),
    hombroI: mezcla(p.hombroI, 4 + 24 * s),
    tronco: mezcla(p.tronco, 7),
  };
};

const monta = (e: Escenario): Escena => {
  const ancho = Math.min(340, e.ancho * 0.33);
  const alto = ancho * 0.62;
  const D = Math.min(e.ancho / 2 - ancho / 2 - 10, 420);
  const bA = borne(-D, ancho, alto, 1);
  const bB = borne(D, ancho, alto, -1);
  /** Las pinzas muerden el borne de lado, con el mango hacia el otro motor. */
  const muerdeA: Punto = { x: bA.x + 12, y: bA.y + 9 };
  const muerdeB: Punto = { x: bB.x - 12, y: bB.y + 9 };
  const x0 = -D + ancho / 2 + 40;
  const x1 = bB.x - 136;
  const enSuelo: Punto = { x: x0 + 140, y: -7 };
  const largo = bB.x - bA.x + 150;
  const llega = ANDA + Math.max(2, Math.round((x1 - x0) / ZANCADA)) * POR_PASO;
  const conecta = llega + 24;
  const salta = conecta + 5;
  const cae = conecta + 13;
  const jarras = cae + 38;
  const pulsos: number[] = [];
  for (let s = conecta + 34; s < e.dur; s += PULSO) pulsos.push(s);

  const claves: Clave<Pose>[] = [
    { f: 0, ...NEUTRA, x: x0 },
    // Mira la pinza en el suelo, delante, y se gira hacia ella.
    { f: 3, pieI: -82, pieD: 82 },
    { f: 7, c: CURVA.suave, cuello: 14, tronco: 6 },
    { f: 8, c: CURVA.suave, caderaI: -9, rodillaI: 4, caderaD: 9, rodillaD: -4, pieI: 84,
      pieD: 86, espalda: 14 },
    // En cuclillas, el tronco tendido y de perfil.
    { f: 16, c: CURVA.suave, tronco: 64, cuello: 12, caderaI: 48, rodillaI: -100, caderaD: 60,
      rodillaD: -110, pieI: 142, pieD: 140, espalda: 5 },
    { f: AGARRA + 1, tronco: 64 },
    // Se levanta tirando: se echa atrás y el cable se tensa.
    { f: 27, c: CURVA.sale, tronco: -8, cuello: 0, caderaI: -8, rodillaI: 4, caderaD: 10,
      rodillaD: -4, pieI: 84, pieD: 86, hombroD: 34, codoD: 52 },
    { f: ANDA, c: CURVA.suave, tronco: 6, x: x0 },
    { f: llega, c: CURVA.suave, x: x1, tronco: 2 },
    { f: llega + 4, caderaI: -12, rodillaI: 5, caderaD: 14, rodillaD: -5, pieI: 84, pieD: 86 },
    // Levanta la pinza, echado atrás, y la descarga.
    { f: conecta - 6, c: CURVA.suave, tronco: -12, cuello: -8, caderaI: -16, rodillaI: 20,
      caderaD: 20, rodillaD: -26 },
    { f: conecta, c: CURVA.cae, tronco: 16, cuello: 6 },
    // El chispazo: lo levanta, brazos al cielo, y cae.
    { f: conecta + 1, alza: 0, hombroI: -10, codoI: 10, hombroD: 34, codoD: 52, pecho: 0, espalda: 5 },
    { f: salta, c: CURVA.sale, alza: 26, tronco: -18, cuello: -10, hombroD: 140, codoD: 26,
      hombroI: -140, codoI: -26, caderaI: -26, rodillaI: 12, caderaD: 26, rodillaD: -12, pecho: 8,
      espalda: 14 },
    { f: cae, c: CURVA.cae, alza: 0, tronco: -4 },
    { f: cae + 5, c: CURVA.sale, caderaI: -24, rodillaI: 30, caderaD: 24, rodillaD: -30 },
    // De frente, se seca la frente: ¡uf! La mano la lleva `mano`.
    { f: cae + 12, c: CURVA.suave, caderaI: -12, rodillaI: 5, caderaD: 12, rodillaD: -5, cuello: 0,
      hombroD: 20, codoD: 10, hombroI: -16, codoI: 8, tronco: 2, pecho: 0, espalda: 14,
      pieI: -82, pieD: 82 },
    { f: cae + 18, c: CURVA.suave, cuello: -8, tronco: -3 },
    { f: cae + 26, c: CURVA.suave, cuello: 6, tronco: 2 },
    // En jarras, de frente y sacando pecho.
    { f: jarras, c: CURVA.suave, hombroI: -52, codoI: 109, hombroD: 52, codoD: -109,
      pieI: -82, pieD: 82, pecho: 5, tronco: 0, caderaI: -14, caderaD: 14, espalda: 14 },
    ...pulsos.flatMap((s, n) => [
      { f: s + 10, cuello: 0 },
      { f: s + 30, c: CURVA.suave, cuello: n % 2 ? 9 : -9 },
    ]),
  ];
  const pista = new Pista<Pose>(NEUTRA, claves);
  /** La mano: a la pinza del suelo, luego arriba y luego al borne. */
  const suelo = mango(enSuelo, 90);
  const mano = new Pista({ x: 0, y: 0, peso: 0, abre: 0, frente: 0, barre: 0 }, [
    { f: 9, ...suelo, peso: 0 },
    { f: 16, c: CURVA.suave, peso: 1 },
    { f: AGARRA + 1, ...suelo, peso: 1 },
    { f: 26, c: CURVA.suave, ...suelo, peso: 0 },
    { f: llega, x: bB.x - 110, y: bB.y - 60, peso: 0, abre: 0 },
    { f: llega + 8, c: CURVA.suave, peso: 1 },
    { f: conecta - 6, c: CURVA.suave, ...hacia(mango(muerdeB, 90), 172, 170), abre: 1 },
    { f: conecta, c: CURVA.cae, ...mango(muerdeB, 90), abre: 0 },
    { f: conecta + 1, peso: 1 },
    { f: salta, c: CURVA.sale, peso: 0 },
    { f: cae + 4, frente: 0, barre: 0 },
    { f: cae + 11, c: CURVA.suave, frente: 1 },
    { f: cae + 13, barre: 0 },
    { f: cae + 22, c: CURVA.suave, barre: 1 },
    { f: cae + 24, frente: 1 },
    { f: cae + 31, c: CURVA.sale, frente: 0 },
  ]);

  const poseEn = (f: number) => {
    const p = andar(pista.en(f), rampa(f, ANDA, ANDA + 5) * (1 - rampa(f, llega - 5, llega)), x0);
    // El calambre: tiembla entero un instante, y se le pasa.
    const tiembla = f >= conecta && f < conecta + 14 ? 1 - (f - conecta) / 14 : 0;
    p.tronco += 5 * tiembla * Math.sin(f * 2.6);
    p.cuello += 9 * tiembla * Math.sin(f * 3.3 + 1);
    // En jarras, satisfecho, lleva el compás con el pie mientras corre la corriente.
    const golpe = f > jarras + 6 ? Math.max(0, Math.sin((2 * Math.PI * (f - jarras - 6)) / 16)) : 0;
    p.pieD += 24 * golpe;
    p.rodillaD -= 6 * golpe;
    return p;
  };
  return {
    fotograma: (f) => {
      const m = mano.en(f);
      const vida = conVida(poseEn, f, 1.6 * rampa(f, jarras, jarras + 20));
      const cabeza = articula(vida).cabeza;
      const frente = { x: cabeza.x - 34 + 70 * m.barre, y: cabeza.y - 14 - 8 * Math.sin(Math.PI * m.barre) };
      const seca = alcanza(vida, frente, m.frente, "D", -1);
      const cuerpo = articula(alcanza(seca, m, m.peso, "D", f < 30 ? -1 : 1));
      const antebrazo =
        (Math.atan2(cuerpo.manoD.x - cuerpo.codoD.x, cuerpo.manoD.y - cuerpo.codoD.y) * 180) / Math.PI;
      // La pinza: en el suelo, luego en la mano siguiendo el antebrazo, y al
      // descargarla gira hasta morder el borne de lado, como la otra.
      const enMano = f >= AGARRA && f < conecta;
      const toma = 90 + corto(antebrazo - 90) * rampa(f, AGARRA, AGARRA + 5);
      const angulo = enMano ? toma + corto(90 - toma) * rampa(f, conecta - 6, conecta) : 90;
      const punta = enMano ? hacia(cuerpo.manoD, angulo, PINZA) : f < AGARRA ? enSuelo : muerdeB;
      const linea = cable(mango(muerdeA, -90), mango(punta, angulo), largo);
      const ultimo = pulsos.filter((s) => s <= f).pop();
      const corre = ultimo === undefined ? -1 : (f - ultimo) / CRUZA;
      const llegaPulso = ultimo === undefined ? -99 : f - ultimo - CRUZA;
      return {
        cuerpo,
        detras: (
          <>
            <Motor cx={-D} ancho={ancho} alto={alto} nombre={e.tablas[0]} haciaDentro={1}
              enciende={corre >= 0 && corre < 0.3 ? 1 - corre / 0.3 : 0} />
            <Motor cx={D} ancho={ancho} alto={alto} nombre={e.tablas[1]} haciaDentro={-1}
              enciende={Math.max(1 - Math.abs(llegaPulso) / 5, f >= conecta && f < conecta + 8 ? 1 : 0)} />
            <Pinza punta={muerdeA} angulo={-90} abre={0} />
            <path d={linea.d} fill="none" stroke={color.secondaryBlue} strokeWidth={8} strokeLinecap="round" />
            {corre >= 0 && corre <= 1.2 ? (
              <path
                d={linea.d}
                fill="none"
                stroke={color.gold}
                strokeWidth={9}
                strokeLinecap="round"
                strokeDasharray={`70 ${linea.mide + 140}`}
                strokeDashoffset={70 - corre * (linea.mide + 70)}
              />
            ) : null}
          </>
        ),
        delante: (
          <>
            <Pinza punta={punta} angulo={angulo} abre={enMano ? m.abre : 0} />
            <Chispa en={muerdeB} t={f - conecta} grande semilla={3} />
            <Chispa en={muerdeB} t={llegaPulso} semilla={pulsos.length} />
          </>
        ),
      };
    },
    sonidos: [
      { motion: "mark", at: AGARRA },
      { motion: "draw", at: 26 },
      { motion: "whoosh", at: conecta - 8 },
      { motion: "fork", at: conecta },
      { motion: "land", at: cae },
    ],
  };
};

export const mecanico: Accion = { alto: 440, ancho: 720, texto: "arriba", monta };
