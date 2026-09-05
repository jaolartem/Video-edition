import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo } from "./Fondo";
import { ZonaTablero } from "./ZonaTablero";
import { Columna } from "./comparacion/Columna";
import { horarioDe } from "./comparacion/horario";
import { color, layout, size, tracking } from "../brand/tokens";
import type { ComparacionProps } from "./comparacion/tipos";

export type { Columna, ComparacionProps } from "./comparacion/tipos";
export { duracionDe } from "./comparacion/horario";

/**
 * Dos columnas, mismas condiciones de partida, resultados distintos.
 *
 * Es el tablero de la **familia tranquila**: fondo plano, geometría a escuadra,
 * y lo único torcido son las cintas. Va donde hay cifras que leer — una tabla
 * sobre un fotomontaje es una tabla que no se lee.
 *
 * Sirve a tres beats del lote, y los tres son la misma forma:
 *
 * - R2 · *«en inglés va a encontrar seminarios del CRA; en español, solo hay
 *   uno»* — la asimetría ES el argumento.
 * - R1 · *«$180.000 de utilidad: sin estructura paga $30.000 más»*.
 * - R3 · *«hasta 53,53% marginal; con la mezcla correcta, 32%»* — y aquí no es
 *   opcional: en Polarizing Thesis **la demostración carga el argumento**, la
 *   actitud sola no.
 *
 * ## Por qué no es `TwoPaths`
 *
 * `TwoPaths` es el componente de **una** estructura del playbook — Two Paths /
 * Default Loss, que en este lote sólo ejecuta el reel 2 — y recorre dos
 * trayectorias paso a paso con horizonte y condición obligatorios. Esto es otra
 * cosa: una comparación de dos estados como **evidencia** dentro de otra
 * estructura. Usar `TwoPaths` en los cuatro reels hacía que cuatro frameworks
 * distintos se vieran idénticos, y entonces el componente deja de significar
 * nada.
 *
 * ## Aquí sólo se dibuja y se ata
 *
 * El contrato de cumplimiento está en
 * [`comparacion/tipos`](./comparacion/tipos.ts), el reparto del horario sobre
 * la escena en [`comparacion/horario`](./comparacion/horario.ts) y la columna
 * en [`comparacion/Columna`](./comparacion/Columna.tsx).
  * @clase tablero
*/
export const Comparacion: React.FC<ComparacionProps> = ({
  premisa,
  izquierda,
  derecha,
  remate,
  fuente,
  condicion,
  placa, recorte = "esquina",
  duracion,
  sound = false,
}) => {
  const entra = useEntrada();

  assertShort(premisa, "title", "Comparacion.premisa");
  assertShort(condicion, "legal", "Comparacion.condicion");
  for (const [k, c] of [["izquierda", izquierda], ["derecha", derecha]] as const) {
    assertShort(c.titulo, "label", `Comparacion.${k}.titulo`);
    assertShort(c.cifra, "outcome", `Comparacion.${k}.cifra`);
    if (c.pie) assertShort(c.pie, "statement", `Comparacion.${k}.pie`);
  }
  if (remate) assertShort(remate, "title", "Comparacion.remate");

  const t = horarioDe({ izquierda, derecha, duracion });

  // **Aire.** Jaime: *«dales aire y espacio a los tableros, que se sientan
  // útiles y no un comodity para cambiar escenas»*. Las columnas ocupaban
  // 500-1200 y el resto era negro apretado arriba y vacío abajo; ahora respiran
  // de verdad y el pie legal tiene su banda.
  const util = layout.width - layout.safe.left * 2;
  const ancho = (util - 34) / 2;

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? <Fondo placa={placa} recorte={recorte} fuerza={1} deriva={t.finColumnas + 60} /> : null}
      {sound ? (
        <>
          <MotionSound motion="mark" at={t.entraIzq} />
          <MotionSound motion="mark" at={t.entraDer} />
          {remate ? <MotionSound motion="land" at={t.remateAt} /> : null}
        </>
      ) : null}

      {/**
       * **Sin cabecera.** Llevaba `EL CÓDIGO DEL EMPRESARIO / INFORMATION GAP`
       * y el contador `03—08`, y Jaime lo señaló: *«tiene un título en la parte
       * superior que no debe ir ahí»*.
       *
       * Dos motivos, y los dos son de traducción de medio:
       *
       * - **El nombre de la estructura es vocabulario del playbook.** «Information
       *   Gap» no significa nada para un dueño de negocio, igual que «revelación»
       *   no significaba nada en la cortinilla.
       * - **El contador es una prestación de carrusel.** Orienta cuando deslizas
       *   seis láminas; en vídeo no hay nada que contar y sólo ocupa la franja
       *   donde debería empezar el contenido.
       *
       * Que el frame esté presente no es imprimir su nombre: es que la pieza
       * respete su secuencia. Eso lo garantiza el montaje, no un rótulo.
       */}

      {/**
       * **Todo el contenido dentro de la zona del tablero.**
       *
       * Este componente es uno de los dos que fabricaron la instrucción T-02:
       * el remate salía a 1390 y el pie a 1570, o sea bajo la interfaz de la
       * plataforma, donde no se ve mal — **no se ve**. `ZonaTablero` lo recorta
       * al techo de la franja por construcción, así que salirse vuelve a ser un
       * fallo visible en vez de un argumento perdido. El fondo se queda fuera:
       * la placa sigue ocupando el cuadro entero.
       */}
      <ZonaTablero>
      {/* Cinta de premisa: la condición común. Sin ella la comparación no es
          honesta — el playbook exige que el punto de partida sea el mismo. */}
      <div
        style={{
          position: "absolute",
          top: 120,
          left: layout.safe.left,
          right: layout.safe.right,
          display: "flex",
          justifyContent: "center",
          opacity: entra(0),
          fontFamily: fontFamily.bloque,
        }}
      >
        <Cinta tinte={color.lightNeutral} giro={-1.5} cuerpo={44}>
          {premisa}
        </Cinta>
      </div>

      <Columna
        datos={izquierda}
        x={layout.safe.left}
        ancho={ancho}
        oro={false}
        progreso={entra(t.entraIzq)}
      />
      <Columna
        datos={derecha}
        x={layout.safe.left + ancho + 34}
        ancho={ancho}
        oro
        progreso={entra(t.entraDer)}
      />

      {remate ? (
        <div
          style={{
            position: "absolute",
            top: 790,
            left: layout.safe.left,
            right: layout.safe.right,
            display: "flex",
            justifyContent: "center",
            opacity: entra(t.remateAt),
            fontFamily: fontFamily.bloque,
          }}
        >
          <Cinta tinte={color.gold} giro={1.8} cuerpo={50}>
            {remate}
          </Cinta>
        </div>
      ) : null}

      {/**
       * **Fuente y condición en la misma banda clara.**
       *
       * La fuente iba suelta sobre el fondo y caía justo encima de la trama de
       * la placa: ilegible. En el canon el pie va sobre plano —«FUENTE: CRA
       * 2026»— y por eso aquí comparte la banda con la condición: las dos son
       * letra pequeña que tiene que poder leerse, y ninguna compite con el dato.
       */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          // Apoyado en el techo de la franja, no en un 1570 escrito a mano.
          bottom: 0,
          backgroundColor: color.lightNeutral,
          transform: "rotate(0.8deg)",
          padding: "18px 74px 22px",
          opacity: entra(t.pieAt),
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.data,
            fontSize: size.source,
            letterSpacing: tracking.labelMono,
            textTransform: "uppercase",
            color: color.navy,
            marginBottom: 12,
          }}
        >
          {fuente}
        </div>
        <div
          style={{
            fontFamily: fontFamily.video,
            fontSize: 26,
            fontWeight: 700,
            lineHeight: 1.34,
            color: color.richBlack,
          }}
        >
          {condicion}
        </div>
      </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
