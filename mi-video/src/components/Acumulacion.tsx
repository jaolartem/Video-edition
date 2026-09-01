import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { MotionSound } from "./MotionSound";
import { Cinta, Fondo, Panel } from "./Fondo";
import { Barra } from "./acumulacion/Barra";
import { EJE, PANEL, SUELO, cruzaEn } from "./acumulacion/caja";
import { horarioDe } from "./acumulacion/horario";
import { color, layout, size, tracking } from "../brand/tokens";
import type { AcumulacionProps } from "./acumulacion/tipos";

export type { AcumulacionProps, Tramo } from "./acumulacion/tipos";
export { duracionDe } from "./acumulacion/horario";

/**
 * Una magnitud que se acumula, y la línea que no había que cruzar.
 *
 * Es el tablero de tres beats del lote, y los tres dicen literalmente esto:
 *
 * - R5 · *«dejó la plata dentro de la corporación mientras esperaba los meses
 *   lentos»* — la barra crece por debajo de la línea. Aún no pasa nada.
 * - R5 · *«cuando esa plata quieta cruzó cierto umbral, el gobierno empezó a
 *   cobrarle más sobre cada dólar nuevo»* — la barra cruza, y lo que asoma por
 *   encima se pone en oro. **$14,000.**
 * - R6 · *«en diez años eso es entre $250.000 y $300.000»* — la misma barra sin
 *   umbral: sólo acumulación sobre un horizonte declarado.
 *
 * Jaime: *«cada animación funciona como un tablero que muestra gráficamente lo
 * que se dice en el audio»*. Por eso la geometría no ilustra el tema, dice la
 * frase: hay una cantidad que sube, hay una raya, y el momento en que la
 * cantidad pasa la raya es el momento en que la voz lo dice.
 *
 * ## El canon
 *
 * La referencia son **los carruseles de Jaime**, y mandan sobre el canon — palabras
 * suyas: *«esto es más canon que el el canon; el el canon de hecho sirvió como inspiración,
 * pero esto es mucho más cercano a lo que quiero»*. De ahí sale la anatomía, y
 * lo que cambia respecto de la web es sustantivo:
 *
 * - **Condensada pesada en versales para TODO lo grande**, cifras incluidas. En
 *   los doce ejemplos no aparece la serif ni una vez. Playfair se queda en la
 *   web, que se lee con calma y sin compresión encima.
 * - **Fotomontaje debajo**, no fondo plano. Ver `Fondo`.
 * - **Panel opaco y girado** sosteniendo el contenido, y **cintas** cruzándolo.
 * - **El oro es superficie**, no sólo tinta: paneles y bandas enteras en oro.
 *
 * ## Aquí sólo se dibuja y se ata
 *
 * Las otras tres cosas viven fuera, cada una en su fichero: el contrato de
 * cumplimiento en [`acumulacion/tipos`](./acumulacion/tipos.ts), el calendario
 * en [`acumulacion/horario`](./acumulacion/horario.ts), la geometría en
 * [`acumulacion/caja`](./acumulacion/caja.ts) y el gráfico en
 * [`acumulacion/Barra`](./acumulacion/Barra.tsx).
 *
 * Eran cuatrocientas líneas con todo mezclado, y el precio estaba a la vista:
 * el horario estaba escrito **dos veces dentro del mismo fichero** —el del
 * componente y el de `duracionDe`— así que el spec podía reservar un hueco de
 * un largo y el tablero construirse en otro.
 */
export const Acumulacion: React.FC<AcumulacionProps> = ({
  title,
  concepto,
  horizonte,
  tramos,
  umbral,
  resultado,
  condicion,
  placa,
  sound = false,
}) => {
  const entra = useEntrada();

  assertShort(title, "title", "Acumulacion.title");
  assertShort(concepto, "label", "Acumulacion.concepto");
  assertShort(horizonte, "label", "Acumulacion.horizonte");
  assertShort(condicion, "legal", "Acumulacion.condicion");
  if (resultado) {
    assertShort(resultado.figure, "outcome", "Acumulacion.resultado.figure");
  }

  const t = horarioDe({ tramos, condicion });
  const cruce = cruzaEn(tramos, umbral);

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {placa ? <Fondo placa={placa} recorte="columna" fuerza={1} deriva={t.finTramos + 60} /> : null}
      {/**
       * **Tablero de datos: fondo PLANO.** No lleva fotomontaje.
       *
       * El canon tiene dos familias y se alternan. La cargada —punto de fuga,
       * geometría rota, elemento conceptual— acompaña el golpe. La tranquila
       * —negro o navy liso, geometría plana, grilla respetada— es donde hay
       * cifras que leer, y ésta es de ésas: una tabla sobre un fotomontaje es
       * una tabla que no se lee.
       *
       * Y la regla que las une: **lo que está torcido está torcido con
       * intención**. Aquí lo único torcido son las cintas. El panel va a
       * escuadra porque sostiene números.
       */}

      {sound ? (
        <>
          <MotionSound motion="draw" at={t.raya} />
          {t.entradas.map((f, i) => (
            <MotionSound key={tramos[i]?.etiqueta} motion="mark" at={f} />
          ))}
          {resultado ? <MotionSound motion="land" at={t.resultadoAt} /> : null}
          {umbral && cruce >= 0 && !resultado ? (
            <MotionSound motion="land" at={t.entradas[cruce] ?? 0} />
          ) : null}
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

      {/* Cinta de encabezado: las condiciones de la comparación. Va arriba y en
          claro, como en el canon — es el marco del dato, no el dato. */}
      <div
        style={{
          position: "absolute",
          top: 152,
          left: layout.safe.left,
          right: layout.safe.right,
          display: "flex",
          justifyContent: "center",
          opacity: entra(0),
          fontFamily: fontFamily.bloque,
        }}
      >
        <Cinta tinte={color.lightNeutral} giro={-1.6} cuerpo={44}>
          {concepto} · {horizonte}
        </Cinta>
      </div>

      <Panel
        giro={0}
        style={{
          left: PANEL.x,
          top: PANEL.y,
          width: PANEL.w,
          height: PANEL.h,
        }}
      >
        {/* Cuerpo ajustado a la linea, y `nowrap`.
            El titulo se partia en «LA PLATA QUE SE QUEDO / QUIETA», con la
            segunda linea huerfana. **Donde respira una frase lo decide quien la
            escribe**, no el ancho que sobra — y el render es determinista, asi
            que no hay layout al que preguntar: se estima. El avance de la Anton
            lo declara `brand/medida`, medido sobre render y en un solo sitio. */}
        <div
          style={{
            position: "absolute",
            top: 44,
            left: 56,
            right: 56,
            fontFamily: fontFamily.bloque,
            fontSize: cuerpoQueCabe({
              ancho: PANEL.w - 112,
              largo: title.length,
              registro: "anton",
              tope: 96,
            }),
            lineHeight: 0.94,
            letterSpacing: "0.004em",
            whiteSpace: "nowrap",
            textTransform: "uppercase",
            color: color.lightNeutral,
            opacity: entra(0),
          }}
        >
          {title}
        </div>

        <Barra
          tramos={tramos}
          umbral={umbral}
          entradas={t.entradas}
          raya={t.raya}
          entra={entra}
        />

        {resultado ? (
          <div
            style={{
              position: "absolute",
              left: EJE.x - 34,
              right: 56,
              top: SUELO + 62,
              opacity: entra(t.resultadoAt),
            }}
          >
            <div
              style={{
                fontFamily: fontFamily.bloque,
                fontSize: 132,
                lineHeight: 0.9,
                letterSpacing: "0.002em",
                textTransform: "uppercase",
                color: color.gold,
                whiteSpace: "nowrap",
                transform: `translateY(${(1 - entra(t.resultadoAt)) * 22}px)`,
              }}
            >
              {resultado.figure}
            </div>
            <div
              style={{
                marginTop: 14,
                fontFamily: fontFamily.data,
                fontSize: size.source,
                letterSpacing: tracking.labelMono,
                color: color.secondaryBlue,
                textTransform: "uppercase",
              }}
            >
              {resultado.source}
            </div>
          </div>
        ) : null}
      </Panel>

      {/* Banda inferior: la condición. Lleva banda propia y no vive de adorno
          al pie — un límite que comparte pantalla con el argumento no se lee. */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          top: 1452,
          backgroundColor: color.lightNeutral,
          transform: "rotate(0.9deg)",
          padding: "22px 74px",
          fontFamily: fontFamily.video,
          fontSize: 26,
          fontWeight: 700,
          lineHeight: 1.34,
          color: color.richBlack,
          opacity: entra(t.condicionAt),
        }}
      >
        {condicion}
      </div>
    </AbsoluteFill>
  );
};
