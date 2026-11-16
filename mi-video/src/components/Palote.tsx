import React, { useContext, useId, useMemo } from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { pintaDelCc } from "../brand/cc";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useLienzo } from "../brand/LienzoContexto";
import { color, ease } from "../brand/tokens";
import { Fondo, Panel, type Recorte } from "./Fondo";
import { MotionSound } from "./MotionSound";
import { DondeEstaEl, ZonaTablero, acompanaAlPlano } from "./ZonaTablero";
import type { Accion, Escenario } from "./palote/accion";
import { aplicacion } from "./palote/Aplicacion";
import { encadena, juntas } from "./palote/cadena";
import { acompana, compone, type Sitio } from "./palote/composicion";
import { Cuerpo } from "./palote/Cuerpo";
import { curriculum } from "./palote/Curriculum";
import { aprobar, caminar, celebrar, encoger, pensar, saludar, senalar } from "./palote/Gestos";
import { guion } from "./palote/Guion";
import { investigar } from "./palote/Investigar";
import { mecanico } from "./palote/Mecanico";
import { millonario } from "./palote/Millonario";
import { musculo } from "./palote/Musculo";

/**
 * **El palote**: el segundo al mando. Un personaje de palotes que actúa la
 * idea —alivio cómico y recurso recurrente— a pleno o acompañándolo a él.
 *
 * Sale igual en vertical y en horizontal: el sitio lo pone el lienzo.
 *
 * Jaime: *«utiliza animación de bolitas y palotes para ejemplificar cosas como
 * code is cheap, o judgment is muscle memory»*, *«que ese personaje quede como
 * recurso recurrente»* y, el 16-11: *«el muñequito tiene que estar ahí como
 * segundo al mando, ¿me entiendes? En todo»*. No explica: **actúa** la frase
 * que se está diciendo, y la frase va escrita a su lado.
 *
 * ## Cuándo pedirlo, y cómo
 *
 * - **A pleno** (por defecto): el beat es una idea que se entiende mejor vista
 *   hacer que leída. Una o dos por pieza: si toma el cuadro en cada beat deja
 *   de ser un respiro.
 * - **Acompañándolo** (`cubre: "panel"` + `lado`): mientras él habla a cámara.
 *   Fondo transparente, un quinto del cuadro, en `arriba`, `abajo`,
 *   `izquierda` o `derecha` —dentro de la zona segura, sobre el subtítulo y
 *   sin bajar de su coronilla—. Jaime: *«si yo aparezco en la cara y el
 *   muñequito también aparece, no pasa nada; ponlo en un sitio que no estorbe
 *   tanto»*. Va en el lado contrario a lo que él saca a cámara: sus ayudas
 *   visuales no se tapan nunca. Así puede salir en muchos beats.
 * - **Varias acciones en la etapa** (`acciones: [{ accion, en }]`, `en` en
 *   segundos desde que empieza): `accion` es lo que hace al entrar y cada
 *   entrada de `acciones`, lo siguiente, sin cortes. Si hay tantas líneas de
 *   `texto` como acciones, cada línea entra con la suya.
 *
 * No lleva cifras —una cantidad dibujada afirma igual que una rotulada—: para
 * eso están `Techo` o `comparacion`.
 *
 * ## Lo que sabe hacer (`accion`)
 *
 * Las ideas, para un beat a pleno:
 * - `millonario` — chistera, mano al bolsillo y a tirar billetes: lo que de
 *   pronto sobra, *code is cheap*. Primer puñado en 1,5 s.
 * - `musculo` — se planta y le sale el bíceps: lo que se gana repitiendo,
 *   *judgment is muscle memory*. Revienta en 0,7 s.
 * - `mecanico` — conecta dos tablas (`tablas`) con pinzas y salta la chispa:
 *   lo que relaciona dos cosas, *SQL*. Pide 5 s para verlo entero.
 *
 * El proceso, paso a paso —*«research, resume, script… es parte también del
 * proceso»*—, encadenables:
 * - `investigar` — le cae una pila de libros y la repasa con la lupa. 1 s.
 * - `curriculum` — escribe una hoja con su foto y la levanta. Arriba en 1,9 s.
 * - `guion` — aporrea una máquina de escribir; la hoja llena sale volando a
 *   los 2,1 s y entra otra.
 * - `aplicacion` — pliega la hoja en avión, pliegue de oro, y lo lanza hacia
 *   el borde en 1,3 s. Cada 4 s, otro.
 *
 * Los gestos del que acompaña —en 0,4 a 1 s, luego los repite—:
 * - `senalar` — le señala a él (o al texto, a pleno): «esto que dice».
 * - `pensar` — mano al mentón y puntos sobre la cabeza: una pregunta.
 * - `aprobar` — pulgar arriba y asiente: lo correcto, lo que funciona.
 * - `celebrar` — saltito con los brazos en uve: un logro, un resultado.
 * - `encoger` — se encoge de hombros: lo que nadie sabe, el «depende».
 * - `saludar` — saluda con la mano: la entrada, la despedida.
 * - `caminar` — entra andando desde el borde a su sitio: la primera vez que
 *   sale en la pieza.
 *
 * Después de la acción **sigue vivo** lo que dure la etapa: repite lo suyo y
 * entre medias mira alrededor, se rasca la cabeza, mira el reloj, golpea con
 * el pie o se coloca el sombrero (`palote/reposo.ts`). Nunca medio segundo
 * quieto, y en 12 s nunca un solo gesto en bucle.
 *
 * ## El personaje
 *
 * Un trazo grueso de punta redonda, cabeza hueca, codos y rodillas: el
 * registro de las figuras de Alan Becker que trajo Jaime, en `lightNeutral` y
 * no en su naranja. Se mueve de pose a pose con anticipación, se pasa y vuelve,
 * y lo que cuelga llega tarde — *«quiero que veas la fluidez del movimiento»*.
 * Acompañando lleva un filete `richBlack` alrededor, como el subtítulo: sobre
 * la pared clara de la toma, una línea clara no se ve.
 * @clase tablero
 */
export type NombreDeAccion =
  | "millonario" | "musculo" | "mecanico"
  | "investigar" | "curriculum" | "guion" | "aplicacion"
  | "senalar" | "pensar" | "aprobar" | "celebrar" | "encoger" | "saludar" | "caminar";

export type PaloteProps = {
  /** Lo que actúa, o lo primero que hace si lleva `acciones`. */
  accion: NombreDeAccion;
  /** Lo que hace después en la misma etapa: cada una entra en su segundo `en`. */
  acciones?: { accion: NombreDeAccion; en: number }[];
  /** `pleno` toma el cuadro; `panel` (o `banda`) lo acompaña a él sin fondo. */
  cubre?: "pleno" | "panel" | "banda";
  /** Acompañando, dónde va. Sin decirlo, a la derecha. */
  lado?: Sitio;
  /** Las líneas que van a su lado, en Anton versales. Cada entrada es una línea. */
  texto?: string[];
  /** Qué línea va en oro: su texto exacto. Una sola. */
  oro?: string;
  /** Las dos tablas que conecta el mecánico, de izquierda a derecha. */
  tablas?: [string, string];
  /** Suena lo que él hace, en el fotograma en que lo hace. */
  sound?: boolean;
  /** La placa de la pieza, en marcha, detrás. A pleno; acompañando no hay fondo. */
  placa?: string;
  recorte?: Recorte;
};

const ACCIONES: Record<NombreDeAccion, Accion> = {
  millonario, musculo, mecanico, investigar, curriculum, guion, aplicacion,
  senalar, pensar, aprobar, celebrar, encoger, saludar, caminar,
};
const SITIOS: Sitio[] = ["arriba", "abajo", "izquierda", "derecha"];

/** Lo que se separa del techo de la franja lo último que se dibuja. */
const AIRE = 28;
/** El filete oscuro que lo separa de la toma cuando la acompaña, en píxeles. */
const FILETE = 4;

/** Una acción que no existe no se adivina: falla el render y dice cuáles hay. */
const sinAccion = (accion: string): never => {
  throw new Error(`Palote: «${accion}» no es una acción. Hay: ${Object.keys(ACCIONES).join(", ")}`);
};

/** Las acciones de la etapa con su fotograma de entrada, comprobadas. */
const pasosDe = (accion: string, acciones: PaloteProps["acciones"], fps: number, dur: number) =>
  [{ accion, en: 0 }, ...(acciones ?? [])].map((p, i, todas) => {
    const en = Math.round(Number(p.en) * fps);
    if (i > 0 && !(en > Math.round(Number(todas[i - 1].en) * fps) && en < dur))
      throw new Error(`Palote: «${p.accion}» entra en ${p.en} s; cada acción entra después de la` +
        ` anterior y antes de que acabe la etapa (${(dur / fps).toFixed(1)} s). La primera es \`accion\``);
    return { papel: ACCIONES[p.accion as NombreDeAccion] ?? sinAccion(p.accion), en };
  });

export const Palote: React.FC<PaloteProps> = ({
  accion,
  acciones,
  cubre = "pleno",
  lado,
  texto = [],
  oro,
  tablas = ["TABLE A", "TABLE B"],
  sound = true,
  placa,
  recorte = "lleno",
}) => {
  const layout = useLienzo();
  const frame = useCurrentFrame();
  const filete = useId();
  const plano = useContext(DondeEstaEl);
  const { durationInFrames, fps } = useVideoConfig();
  texto.forEach((l) => assertShort(l, "statement", "Palote.texto"));
  tablas.forEach((t) => assertShort(t, "label", "Palote.tablas"));
  const firma = JSON.stringify([accion, acciones ?? []]);
  const pasos = useMemo(() => pasosDe(accion, acciones, fps, durationInFrames),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [firma, fps, durationInFrames]);
  const papel = pasos.length > 1 ? juntas(pasos.map((p) => p.papel)) : pasos[0].papel;

  // **A pleno o acompañándolo**, y dónde: ver `palote/composicion.ts`.
  const conEl = acompanaAlPlano({ cubre });
  if (lado !== undefined && (!conEl || !SITIOS.includes(lado)))
    throw new Error(`Palote: \`lado: ${lado}\` sólo vale acompañándolo (\`cubre: "panel"\`) y es` +
      ` uno de ${SITIOS.join(", ")}`);
  const sitio = lado ?? "derecha";
  const zona = layout.height - layout.franja.reserva;
  const { caja, escena, k, centra, enMedio, cuerpoTexto } = conEl
    ? acompana(layout, papel, texto, sitio, plano, AIRE)
    : compone(layout, papel, texto, AIRE);
  const suelo = escena.y + escena.h;
  const cx = escena.x + escena.w / 2;
  /** Hacia dónde queda lo que acompaña: el texto a pleno; él, acompañándolo. */
  const senal = conEl && (sitio === "derecha" || (sitio !== "izquierda" && plano.libre === "der")) ? -1 : 1;

  const [tablaA, tablaB] = tablas;
  const montada = useMemo(() => {
    const e: Escenario = { ancho: escena.w / k, techo: suelo / k, dur: durationInFrames, tablas: [tablaA, tablaB], senal };
    return pasos.length > 1 ? encadena(pasos, e) : pasos[0].papel.monta(e);
  }, [pasos, escena.w, k, suelo, durationInFrames, tablaA, tablaB, senal]);
  const { cuerpo, detras, delante } = montada.fotograma(frame);
  const enOro = (l: string) => Boolean(oro) && l.trim().toUpperCase() === oro?.trim().toUpperCase();
  /** Una línea por acción: cada una entra con la suya. Si no, en cascada. */
  const porAccion = pasos.length > 1 && texto.length === pasos.length;
  const entra = (i: number) => (porAccion ? pasos[i].en + 3 : 3 + i * 5);

  return (
    <AbsoluteFill style={{ backgroundColor: conEl ? "transparent" : color.richBlack }}>
      {placa && !conEl ? (
        <Fondo placa={placa} recorte={recorte} fuerza={0.9} deriva={durationInFrames} />
      ) : null}
      {sound
        ? montada.sonidos.map((s) => <MotionSound key={`${s.motion}${s.at}`} motion={s.motion} at={s.at} />)
        : null}
      <ZonaTablero>
        {/* **Sobre la placa, un panel que lo sostiene.** La placa vertical es
            collage claro y él es una línea clara: sin el bloque negro detrás
            no se ve. Es el panel del canon —opaco, girado dos grados, la placa
            asomando por los bordes—; en el horizontal el suelo ya es la
            retícula oscura y no hace falta. */}
        {placa && !conEl && layout.tablero.suelo === "placa" ? (
          <Panel
            giro={-1.4}
            style={{
              left: layout.safe.left - 30,
              top: layout.safe.top - 40,
              width: layout.width - layout.safe.left - layout.safe.right + 60,
              height: zona - AIRE / 2 - layout.safe.top + 40,
            }}
          >
            {null}
          </Panel>
        ) : null}
        <svg
          width={layout.width}
          height={zona}
          style={{ position: "absolute", left: 0, top: 0, overflow: "visible" }}
        >
          {conEl ? (
            <defs>
              <filter id={filete} filterUnits="userSpaceOnUse" x={0} y={0} width={layout.width} height={zona}>
                <feMorphology in="SourceAlpha" operator="dilate" radius={FILETE} result="ancho" />
                <feFlood floodColor={color.richBlack} />
                <feComposite in2="ancho" operator="in" result="borde" />
                <feMerge>
                  <feMergeNode in="borde" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>
          ) : null}
          <g filter={conEl ? `url(#${filete})` : undefined}>
            <g transform={`translate(${cx.toFixed(2)} ${suelo.toFixed(2)}) scale(${k.toFixed(4)})`}>
              {detras}
              <Cuerpo a={cuerpo} tinte={color.lightNeutral} />
              {delante}
            </g>
          </g>
        </svg>
        <div
          style={{
            position: "absolute",
            left: caja.x,
            top: caja.y,
            width: caja.w,
            height: caja.h,
            display: "flex",
            flexDirection: "column",
            justifyContent: enMedio ? "center" : "flex-start",
            alignItems: centra ? "center" : "flex-start",
            textAlign: centra ? "center" : "left",
          }}
        >
          {texto.map((l, i) => {
            const p = interpolate(frame, [entra(i), entra(i) + 10], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: ease.out,
            });
            return (
              <div
                key={`${i}${l}`}
                style={{
                  ...(conEl ? pintaDelCc("limpio") : {}),
                  fontFamily: fontFamily.bloque,
                  fontSize: cuerpoTexto,
                  lineHeight: 0.96,
                  letterSpacing: "0.005em",
                  textTransform: "uppercase",
                  whiteSpace: "nowrap",
                  color: enOro(l) ? color.gold : color.lightNeutral,
                  opacity: p,
                  transform: `translateY(${((1 - p) * 26).toFixed(1)}px)`,
                }}
              >
                {l}
              </div>
            );
          })}
        </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
