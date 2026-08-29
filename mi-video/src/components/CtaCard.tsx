import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { Cinta, Fondo } from "./Fondo";
import {
  accentChoice,
  color,
  duration,
  ease,
  layout,
  mode as modes,
  size,
  tone as tones,
  tracking,
  type Accent,
  type Mode,
  type Tone,
} from "../brand/tokens";

export type CtaCardProps = {
  /** La promesa, en corto. No el guion entero. */
  promesa: string;
  /** Los datos duros de la oferta. Un CTA incompleto no sirve. */
  fecha: string;
  /**
   * Precio suelto. Se conserva para las piezas que no declaran `cuenta`.
   *
   * **Sólo entra con su fecha de cierre.** Sin ella caduca en silencio: «$20»
   * deja de ser cierto el día que sube y la pieza sigue publicada.
   */
  precio?: string;
  /**
   * El desliz que se señala. Se oye `dice`, se lee `es`.
   *
   * En el reel 1 Jaime dice «550» y el cálculo de su propio libreto da `$576`.
   * La diferencia es de redondeo y no cambia el mensaje — por eso se señala en
   * vez de corregirse, y por eso lo tachado es pequeño y lo cierto es lo grande.
   */
  corrige?: { dice: string; es: string };
  /**
   * **Las dos cuentas**, que es de lo que va la pieza.
   *
   * Corrección de Jaime: *«el precio del bootcamp es 20, 30 o 40 dólares; el
   * precio de NO conocerlos es de 576»*. Antes los 576 ocupaban la fila de
   * precio, así que la tarjeta decía que el bootcamp costaba 576 — el número
   * correcto en la fila equivocada.
   *
   * Van **en dos columnas, navy contra oro**, que es como el canon resuelve una
   * comparación: el navy es el camino por defecto y el oro es donde hay que
   * mirar. Y **la pregunta no se escribe**: la hace la voz —*«revise qué cuenta
   * le sale mejor»*— y aquí sólo están las dos cuentas para que tenga a qué
   * referirse.
   */
  cuenta?: { cuesta: string; vale: string; nota?: string };
  accion: string;
  kicker?: string;
  /**
   * Cuánto dura la tarjeta, en frames. **El horario se reparte sobre ella.**
   *
   * Jaime: *«todo el panel final pasa muy rápido»*. La duración la calcula
   * `reels-spec.mjs` a partir de lo que la tarjeta lleva dentro, no de un
   * número redondo: así cada bloque tiene su tiempo de lectura.
   */
  duracion?: number;
  /** Placa de fondo recortada. El CTA es el último frame: no puede ser un plano negro. */
  placa?: string;
  mode?: Mode;
  tone?: Tone;
  accent?: Accent;
};

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
  const frame = useCurrentFrame();
  const base = modes[mode];
  const t = {
    ...base,
    ground: tones[mode][tone],
    accent: accent ? accentChoice[accent] : base.accent,
  };

  const T = duracion ?? 120;
  const enter = (at: number) =>
    interpolate(frame, [at, at + duration.entry], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: ease.out,
    });

  /** Ancho de cada columna. Dos cuentas, un filete de 24 px entre ellas. */
  const ancho = (layout.width - layout.safe.left - layout.safe.right - 24) / 2;

  /**
   * Una cuenta: etiqueta arriba, cifra grande, condición debajo.
   *
   * `oro` marca cuál es la que el espectador debe mirar. En el canon la
   * distinción entre lo que se atiende y lo que no se hace **con oro contra
   * navy**, nunca con semáforo — no hay rojo en el sistema.
   */
  const Cuenta: React.FC<{
    etiqueta: string;
    cifra: string;
    pie?: string;
    tachado?: string;
    oro?: boolean;
    at: number;
  }> = ({ etiqueta, cifra, pie, tachado, oro, at }) => {
    const p = enter(at);
    return (
      <div
        style={{
          width: ancho,
          minHeight: 420,
          backgroundColor: oro ? color.gold : color.navy,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: 22,
          padding: "34px 26px",
          opacity: p,
          transform: `translateY(${((1 - p) * 26).toFixed(1)}px)`,
        }}
      >
        <div
          style={{
            fontFamily: fontFamily.bloque,
            fontSize: 42,
            lineHeight: 1.02,
            textAlign: "center",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.secondaryBlue,
          }}
        >
          {etiqueta}
        </div>
        {tachado ? (
          <div
            style={{
              fontFamily: fontFamily.bloque,
              fontSize: 44,
              textDecoration: "line-through",
              textTransform: "uppercase",
              color: oro ? color.richBlack : color.secondaryBlue,
              opacity: 0.75,
            }}
          >
            {tachado}
          </div>
        ) : null}
        <div
          style={{
            fontFamily: fontFamily.bloque,
            // Anton gasta ~0,47 em por caracter en versales, medido sobre
            // render. El margen se paga en cuerpo, que es barato.
            fontSize: Math.min(156, (ancho - 52) / (cifra.length * 0.47)),
            lineHeight: 0.94,
            whiteSpace: "nowrap",
            textTransform: "uppercase",
            color: oro ? color.richBlack : color.lightNeutral,
          }}
        >
          {cifra}
        </div>
        {pie ? (
          <div
            style={{
              fontFamily: fontFamily.video,
              fontSize: 28,
              fontWeight: 800,
              lineHeight: 1.2,
              textAlign: "center",
              textTransform: "uppercase",
              letterSpacing: "0.02em",
              color: oro ? color.richBlack : color.secondaryBlue,
            }}
          >
            {pie}
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <AbsoluteFill style={{ backgroundColor: t.ground }}>
      {placa ? (
        <Fondo placa={placa} recorte="cuna" fuerza={1} deriva={T} />
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
          opacity: interpolate(frame, [0, duration.entry], [0, 0.93], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: ease.out,
          }),
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
              opacity: enter(Math.round(T * 0.05)),
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
            fontSize: Math.min(
              92,
              (layout.width - layout.safe.left * 2) /
                (Math.max(...promesa.split(" ").map((w) => w.length), 1) * 0.47) /
                1.1,
            ),
            lineHeight: 0.98,
            letterSpacing: "0.004em",
            textTransform: "uppercase",
            color: t.text,
            opacity: enter(Math.round(T * 0.18)),
            transform: `translateY(${(1 - enter(Math.round(T * 0.18))) * 14}px)`,
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
                at={Math.round(T * 0.34)}
              />
              <Cuenta
                etiqueta="El bootcamp"
                cifra={cuenta.vale.split(" ")[0]}
                pie={[cuenta.vale.split(" ").slice(1).join(" "), cuenta.nota]
                  .filter(Boolean)
                  .join(" · ")}
                oro
                at={Math.round(T * 0.5)}
              />
            </>
          ) : precio ? (
            <Cuenta etiqueta="Precio" cifra={precio} oro at={Math.round(T * 0.34)} />
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
            opacity: enter(Math.round(T * 0.68)),
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
