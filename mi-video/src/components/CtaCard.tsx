import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe, masLarga } from "../brand/medida";
import { Cinta, Fondo } from "./Fondo";
import { Cuenta } from "./ctaCard/Cuenta";
import { horarioDe } from "./ctaCard/horario";
import {
  accentChoice,
  color,
  layout,
  mode as modes,
  size,
  tone as tones,
  tracking,
} from "../brand/tokens";
import type { CtaCardProps } from "./ctaCard/tipos";

export type { CtaCardProps } from "./ctaCard/tipos";

/**
 * La tarjeta de cierre, **en el vocabulario de los tableros**.
 *
 * Jaime: *«el último tablero no se lee bien y no sigue el formato de diseño»*, y
 * tenía razón por dos motivos distintos que conviene no mezclar:
 *
 * 1. **No seguía el canon.** Era una lista de filas con etiquetas en mono a un
 *    lado y valores al otro — el registro de una ficha técnica, no el de los
 *    carruseles. El canon resuelve una comparación con **dos bloques planos,
 *    navy contra oro**, cintas giradas y una banda de pie; y eso es exactamente
 *    lo que `Comparacion` ya hace en el minuto 19 de esta misma pieza. Dos
 *    registros distintos en una pieza se leen como dos piezas.
 * 2. **No se leía.** El contenido acababa al 59% de altura y los 800 px de
 *    abajo eran placa vacía, así que el ojo tenía que buscar el dato en el
 *    tercio superior mientras el resto del cuadro pedía atención sin decir
 *    nada.
 *
 * Ahora la tarjeta **es un tablero**: cinta de antetítulo, promesa en
 * condensada, las dos cuentas enfrentadas ocupando el centro y la banda de pie
 * con la fecha y la acción. Mismo lenguaje que el tablero del minuto 19, que es
 * lo que hace que la pieza cierre donde abrió.
 *
 * ## Aquí sólo se dibuja y se ata
 *
 * El contrato de la oferta está en [`ctaCard/tipos`](./ctaCard/tipos.ts), el
 * reparto sobre la duración en [`ctaCard/horario`](./ctaCard/horario.ts) y la
 * columna en [`ctaCard/Cuenta`](./ctaCard/Cuenta.tsx) — que además vivía
 * declarada dentro del cuerpo de este componente.
 */
export const CtaCard: React.FC<CtaCardProps> = ({
  promesa,
  fecha,
  precio,
  corrige,
  cuenta,
  accion,
  kicker,
  mode = "evidence",
  tone = "base",
  accent,
  duracion,
  placa,
}) => {
  const entra = useEntrada();
  const base = modes[mode];
  const t = {
    ...base,
    ground: tones[mode][tone],
    accent: accent ? accentChoice[accent] : base.accent,
  };

  const h = horarioDe(duracion);
  const abre = entra(0);
  const promesaP = entra(h.promesaAt);

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      {placa ? (
        <Fondo placa={placa} recorte="cuna" fuerza={1} deriva={h.total} />
      ) : null}

      {/**
       * El bloque de contenido cubre de la zona segura superior a la inferior.
       * Antes acababa al 59% y dejaba 800 px de placa vacia debajo: el dato
       * quedaba arriba del todo y el resto del cuadro pedia atencion sin decir
       * nada.
       */}
      <AbsoluteFill
        style={{
          top: layout.safe.top - 60,
          bottom: layout.safe.bottom - 300,
          backgroundColor: t.ground,
          opacity: abre * 0.93,
        }}
      />

      <AbsoluteFill
        style={{
          paddingTop: layout.safe.top - 20,
          paddingBottom: layout.safe.bottom - 260,
          paddingLeft: layout.safe.left,
          paddingRight: layout.safe.right,
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
        }}
      >
        {/* Cinta de antetitulo: banda girada, texto negro sobre el color. */}
        {kicker ? (
          <div
            style={{
              display: "flex",
              fontFamily: fontFamily.bloque,
              opacity: entra(h.kickerAt),
            }}
          >
            <Cinta tinte={color.lightNeutral} giro={-1.5} cuerpo={40}>
              {assertShort(kicker, "label", "CtaCard.kicker")}
            </Cinta>
          </div>
        ) : null}

        {/**
         * La promesa, en **condensada pesada y versales**.
         *
         * El cuerpo se ajusta a la palabra mas larga y no envuelve por ancho:
         * donde respira la frase lo decide quien la escribe.
         */}
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: cuerpoQueCabe({
              ancho: layout.width - layout.safe.left * 2,
              largo: masLarga(promesa.split(" ")),
              registro: "anton",
              holgura: 1.1,
              tope: 92,
            }),
            lineHeight: 0.98,
            letterSpacing: "0.004em",
            textTransform: "uppercase",
            color: t.text,
            opacity: promesaP,
            transform: `translateY(${(1 - promesaP) * 14}px)`,
          }}
        >
          {assertShort(promesa, "title", "CtaCard.promesa")}
        </div>

        {/**
         * Las dos cuentas, enfrentadas. Navy lo que ya esta pasando, oro la
         * salida — que es donde el canon manda mirar.
         *
         * Sin `cuenta` declarada cae a una sola columna con el precio, que es lo
         * que llevaban las piezas antes de que Jaime separase las dos cifras.
         */}
        <div style={{ display: "flex", gap: 24 }}>
          {cuenta ? (
            <>
              <Cuenta
                etiqueta="No saberlo"
                cifra={corrige?.es ?? cuenta.cuesta}
                pie={corrige ? cuenta.cuesta.replace(/^\$\d+\s*/, "") : undefined}
                tachado={corrige?.dice}
                progreso={entra(h.cuestaAt)}
              />
              <Cuenta
                etiqueta="El bootcamp"
                cifra={cuenta.vale.split(" ")[0] ?? ""}
                pie={[cuenta.vale.split(" ").slice(1).join(" "), cuenta.nota]
                  .filter(Boolean)
                  .join(" · ")}
                oro
                progreso={entra(h.valeAt)}
              />
            </>
          ) : precio ? (
            <Cuenta
              etiqueta="Precio"
              cifra={precio}
              oro
              progreso={entra(h.cuestaAt)}
            />
          ) : null}
        </div>

        {/**
         * Banda de pie: fecha y accion en el registro de dato del sistema.
         * Claro sobre oscuro, que es como el canon cierra un tablero.
         */}
        <div
          style={{
            backgroundColor: color.lightNeutral,
            padding: "20px 26px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 24,
            opacity: entra(h.pieAt),
          }}
        >
          <div
            style={{
              fontFamily: fontFamily.data,
              fontSize: size.source,
              letterSpacing: tracking.labelMono,
              textTransform: "uppercase",
              color: color.navy,
            }}
          >
            {fecha}
          </div>
          <div
            style={{
              fontFamily: fontFamily.bloque,
              fontSize: 46,
              textTransform: "uppercase",
              color: color.richBlack,
            }}
          >
            {accion}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
