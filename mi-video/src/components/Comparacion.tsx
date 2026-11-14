import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo } from "./Fondo";
import { Remate } from "./Remate";
import { ZonaTablero } from "./ZonaTablero";
import { Columna } from "./comparacion/Columna";
import { horarioDe } from "./comparacion/horario";
import { color } from "../brand/tokens";
import type { ComparacionProps } from "./comparacion/tipos";
import { useLienzo } from "../brand/LienzoContexto";

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
  placa, recorte = "esquina",
  duracion,
  sound = false,
}) => {
  const layout = useLienzo();
  const entra = useEntrada();

  assertShort(premisa, "title", "Comparacion.premisa");
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

      {/**
       * **El remate y el pie, apilados desde abajo. No cada uno por su lado.**
       *
       * Jaime, sobre R-07 e3: *«el pie de fuente se dibuja encima de la cinta»*.
       * Y era inevitable por construcción: el remate iba en `top: 790` —un
       * número escrito a mano— y el pie en `bottom: 0`, así que quién tapaba a
       * quién dependía de **cuánto texto trajera la condición**. Con dos líneas
       * de condición la banda mide 140 px y no se tocan; con cuatro mide 200 y
       * se comen la cinta, que es lo que salió en pantalla desde 36,6 s.
       *
       * Apilados en una sola columna anclada abajo, el solape deja de ser
       * posible: el pie ocupa lo que necesita y el remate se apoya encima. Es la
       * misma corrección que T-02 hizo con la franja — sustituir un número
       * escrito a mano por una relación que no se puede incumplir.
       */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          bottom: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "stretch",
        }}
      >
        {remate ? (
          <div
            style={{
              display: "flex",
              justifyContent: "center",
              paddingLeft: layout.safe.left,
              paddingRight: layout.safe.right,
              marginBottom: 34,
              opacity: entra(t.remateAt),
              fontFamily: fontFamily.bloque,
            }}
          >
            {/* **Un acento por tablero, y aquí es la columna de oro.** Lo que
                demuestra una comparación es el contraste entre los dos bloques,
                así que el remate va en claro: con los dos en oro el ojo no sabe
                por dónde entrar. Ver `Remate.tsx`. */}
            <Remate giro={1.8} cuerpo={50}>{remate}</Remate>
          </div>
        ) : null}

        {/**
         * **El pie ya no vive aquí.**
         *
         * Esta banda de `lightNeutral` con la condición en Montserrat a 26 px
         * era la masa más clara del cuadro puesta en lo que menos hay que
         * mirar, y dentro de la lámina: en `Reel-R1 e3` ocupaba más sitio que
         * el dato al que venía a respaldar. Instrucción de Jaime (6-9-2026): el
         * pie va **fuera de la zona segura, en una línea**. Lo dibuja
         * [`PieTablero`](./PieTablero.tsx), montado por `dibujaTablero` para las
         * 24 láminas del lote — aquí ya no hay pie que apilar, sólo el remate.
         */}
      </div>
      </ZonaTablero>
    </AbsoluteFill>
  );
};
