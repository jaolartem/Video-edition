import React from "react";
import { AbsoluteFill } from "remotion";
import { fontFamily } from "../brand/fonts";
import { assertShort } from "../brand/copy";
import { useEntrada } from "../brand/horario";
import { cuerpoQueCabe } from "../brand/medida";
import { MotionSound } from "./MotionSound";
import { ZonaTablero } from "./ZonaTablero";
import { Cinta, Fondo } from "./Fondo";
import { Barra } from "./acumulacion/Barra";
import { Total } from "./acumulacion/Cierre";
import { CINTA, TITULO, cruzaEn } from "./acumulacion/caja";
import { BARRE, horarioDe } from "./acumulacion/horario";
import { color } from "../brand/tokens";
import type { AcumulacionProps } from "./acumulacion/tipos";
import { useLienzo } from "../brand/LienzoContexto";

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
 * - R2 · *«esta diferencia, 21 dólares de cada 100, en cinco años son 189 mil»*
 *   — la misma barra sin umbral: cinco tramos que suman, el último en oro y la
 *   cifra encima.
 *
 * Jaime: *«cada animación funciona como un tablero que muestra gráficamente lo
 * que se dice en el audio»*. Por eso la geometría no ilustra el tema, dice la
 * frase: hay una cantidad que sube, hay una raya, y el momento en que la
 * cantidad pasa la raya es el momento en que la voz lo dice.
 *
 * ## La lámina, rehecha sobre la que Jaime aprobó
 *
 * El 6-9-2026, mirando `work/fotogramas/reel-02/e07-3.jpg`: *«la caja negra se
 * come el cuadro»* —la placa asomando sólo por los bordes—, *«cuatro bloques
 * navy iguales: el ojo no sabe dónde mirar»*, *«dice cinco años y dibuja
 * cuatro»* y la cifra que el tablero demuestra sin aparecer en pantalla.
 *
 * Lo que lo sustituye no se inventó: es el vocabulario del panel de la e2 de
 * esta misma pieza, aprobado ese día tras seis vueltas y guardado en
 * `docs/ejemplos/composicion/01-panel-con-el-dentro.png`.
 *
 * - **La placa a sangre** y el negro **sólo bajo lo que hay que leer**: el
 *   bloque del título, la ficha de cada etiqueta, la banda del pie. El panel
 *   opaco de 988×680 se retiró (ver `acumulacion/caja`).
 * - **Un solo acento.** Sin umbral el oro es del último tramo, que es el que
 *   cierra la cuenta. Con umbral sigue siendo lo que asoma por encima de la
 *   raya. Nunca los dos.
 * - **El remate barre el panel.** *«Puede borrar el panel o parte de él, pero
 *   debe salir súper enfático»*: cuando la pila está entera, lo que la
 *   construyó se retira y la cifra se queda sola.
 * - **El pie fuera de la zona segura**, en una línea y en afirmativo.
 *
 * ## Aquí sólo se dibuja y se ata
 *
 * Las otras cosas viven fuera, cada una en su fichero: el contrato de
 * cumplimiento en [`acumulacion/tipos`](./acumulacion/tipos.ts), el calendario
 * en [`acumulacion/horario`](./acumulacion/horario.ts), la geometría en
 * [`acumulacion/caja`](./acumulacion/caja.ts), el gráfico en
 * [`acumulacion/Barra`](./acumulacion/Barra.tsx) y lo que remata en
 * [`acumulacion/Cierre`](./acumulacion/Cierre.tsx).
 *
 * Eran cuatrocientas líneas con todo mezclado, y el precio estaba a la vista:
 * el horario estaba escrito **dos veces dentro del mismo fichero** —el del
 * componente y el de `duracionDe`— así que el spec podía reservar un hueco de
 * un largo y el tablero construirse en otro.
  * @clase tablero
*/
export const Acumulacion: React.FC<AcumulacionProps> = ({
  title,
  concepto,
  horizonte,
  tramos,
  umbral,
  resultado,
  condicion,
  placa, recorte = "lleno",
  sound = false,
}) => {
  const layout = useLienzo();
  const entra = useEntrada();

  assertShort(title, "title", "Acumulacion.title");
  assertShort(concepto, "label", "Acumulacion.concepto");
  assertShort(horizonte, "label", "Acumulacion.horizonte");
  assertShort(condicion, "legal", "Acumulacion.condicion");
  if (resultado) {
    assertShort(resultado.figure, "outcome", "Acumulacion.resultado.figure");
  }

  /**
   * **Una acumulación acumula, y eso son tramos rotulados: por lo menos dos.**
   *
   * Con `tramos: [{etiqueta: "", alto: 1}]` este componente dibuja exactamente
   * lo que le piden —un rectángulo partido por la raya— y en pantalla eso no es
   * una acumulación: son dos bloques vacíos. Salió así en reel-05 e6, un tablero
   * titulado «LA RAYA YA ESTABA PUESTA» con un horizonte que decía «TRIMESTRE A
   * TRIMESTRE» y ni un trimestre dibujado, o sea **la lámina afirmando algo que
   * no enseña**. Es el contraejemplo de `docs/ejemplos/composicion/03-tablero-como-NO.jpg`
   * por su otra cara: allí decía cinco y dibujaba cuatro; aquí dice muchos y
   * dibuja uno.
   *
   * Y el tramo sin etiqueta tampoco es una decisión de composición: `Barra` sólo
   * pinta la ficha cuando hay texto, así que un tramo mudo es un bloque de color
   * del que nadie sabe qué cuenta. Si un tramo no se puede nombrar, no es un
   * tramo — es la barra entera, y entonces esto no es el componente.
   *
   * **Y con raya, además, cuánto es cada uno.** Rotularlos fue lo que salió mal
   * la segunda vez: cuatro trimestres de 0,26 · 0,24 · 0,22 · 0,28 y una raya en
   * 0,78 dibujan una escala en dólares —cuánto puso cada trimestre y en cuál se
   * cruzó— que ninguna fila de `dato` sostiene. Ver `Tramo.valor`.
   */
  if (tramos.length < 2) {
    throw new Error(
      `Acumulacion: ${tramos.length} tramo(s) y una acumulación se ve porque` +
        " algo se apila. Con uno solo lo que se dibuja es un rectángulo partido" +
        " por la raya, no una cantidad que sube: declara los tramos que la voz" +
        " nombra —los trimestres, los años— o usa otra forma.",
    );
  }
  for (const tr of tramos) {
    if (!tr.etiqueta.trim()) {
      throw new Error(
        "Acumulacion: un tramo sin `etiqueta` sale como un bloque de color que" +
          " no dice qué cuenta —`Barra` no pinta ficha sin texto—. Cada tramo" +
          " lleva el suyo, en versales y corto.",
      );
    }
    if (umbral && !tr.valor?.trim()) {
      throw new Error(
        `Acumulacion: la raya rotula «${umbral.etiqueta}», así que la columna` +
          ` deja de repartir un total y pasa a ser una escala en esa unidad:` +
          ` «${tr.etiqueta}» dibuja cuánto puso sin decir cuánto es, y el cruce` +
          " sale de esas alturas. Declara `valor` en cada tramo —una cantidad" +
          " dibujada afirma igual que una cifra rotulada y necesita su fila en" +
          " `dato`— o, si los importes no tienen respaldo, usa otra forma.",
      );
    }
  }

  const t = horarioDe({ tramos, condicion, resultado });
  const cruce = cruzaEn(tramos, umbral);
  // El barrido, ya resuelto: 0 mientras el diagrama manda, 1 cuando la cifra se
  // ha quedado sola. Todo lo que se retira lo hace multiplicando por `1 - barre`,
  // que es como lo hace la lámina aprobada.
  const barre = t.barrido === null ? 0 : entra(t.barrido, BARRE);
  const queda = 1 - barre;

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {/**
       * **La placa, a sangre.** Es la primera de las cuatro capas de la lámina
       * aprobada, y la única que se queda fuera de `ZonaTablero`: el fondo está
       * detrás de todo y no compite con nadie.
       */}
      {placa ? (
        <Fondo placa={placa} recorte={recorte} deriva={t.duracion + 60} />
      ) : null}

      {sound ? (
        <>
          <MotionSound motion="draw" at={t.raya} />
          {t.entradas.map((f, i) => (
            <MotionSound key={tramos[i]?.etiqueta ?? i} motion="mark" at={f} />
          ))}
          {t.barrido !== null ? (
            <MotionSound motion="land" at={t.barrido} />
          ) : null}
          {umbral && cruce >= 0 && t.barrido === null ? (
            <MotionSound motion="land" at={t.entradas[cruce] ?? 0} />
          ) : null}
        </>
      ) : null}

      {/**
       * **Sin cabecera.** Llevaba `EL CÓDIGO DEL EMPRESARIO / INFORMATION GAP`
       * y el contador `03—08`, y Jaime lo señaló: *«tiene un título en la parte
       * superior que no debe ir ahí»*. El nombre de la estructura es vocabulario
       * del playbook y el contador es una prestación de carrusel: en vídeo no
       * hay nada que contar y sólo ocupa la franja donde empieza el contenido.
       */}

      {/**
       * **Todo el contenido dentro de la zona del tablero.** Este componente y
       * `Comparacion` son los dos que fabricaron la instrucción T-02: dibujaban
       * a 1390, 1452 y 1570, o sea bajo la interfaz de la plataforma. Con
       * `ZonaTablero` salirse vuelve a ser un fallo visible en vez de un
       * argumento perdido. La placa se queda fuera: sigue a cuadro entero.
       */}
      <ZonaTablero>
        {/* Cinta de encabezado: las condiciones de la comparación. Va arriba y
            en claro, como en el canon — es el marco del dato, no el dato. **Y
            no se la lleva el barrido**: cuando la cifra se queda sola, esta
            línea es lo que dice de qué es. */}
        <div
          style={{
            position: "absolute",
            top: CINTA.y,
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

        {/* El título, en un bloque negro que **sangra por la izquierda**. Es la
            masa de la lámina aprobada: sostiene lo que hay que leer y se acaba
            donde se acaba el texto. Cuerpo ajustado a la línea y `nowrap` —
            dónde respira una frase lo decide quien la escribe, no el ancho que
            sobra, y el render es determinista, así que se estima con el avance
            de `brand/medida`. */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: TITULO.y,
            width: TITULO.ancho,
            padding: `24px ${TITULO.relleno}px 28px`,
          }}
        >
          {/* El negro se abre desde el borde y **el texto no se estira con
              él**: puesto como fondo del mismo div, el `scaleX` de la entrada
              deformaba la Anton hasta que el bloque acababa de abrirse. */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: color.richBlack,
              transformOrigin: "left",
              transform: `scaleX(${entra(0) * queda})`,
            }}
          />
          <div
            style={{
              position: "relative",
              fontFamily: fontFamily.bloque,
              fontSize: cuerpoQueCabe({
                ancho: TITULO.ancho - TITULO.relleno * 2,
                largo: title.length,
                registro: "anton",
                tope: TITULO.tope,
              }),
              lineHeight: 0.94,
              letterSpacing: "0.004em",
              whiteSpace: "nowrap",
              textTransform: "uppercase",
              color: color.lightNeutral,
              // **La letra se va antes que su negro.** Con la misma curva que
              // el bloque, a mitad del barrido el título asomaba fuera de su
              // masa ya encogida y quedaba flotando sobre el collage como un
              // fantasma. El negro se lleva la letra, no al revés.
              opacity: entra(0) * Math.max(0, queda * 2 - 1),
            }}
          >
            {title}
          </div>
        </div>

        <div style={{ opacity: queda }}>
          <Barra
            tramos={tramos}
            umbral={umbral}
            entradas={t.entradas}
            raya={t.raya}
            entra={entra}
          />
        </div>

        {resultado ? <Total figura={resultado.figure} barre={barre} /> : null}
      </ZonaTablero>

      {/* **El pie ya no lo dibuja este componente.** Fue el primero en sacarlo
          de la lámina —copiado de `PanelDentro`, con el 1262 escrito a mano en
          los dos— y ahora lo monta `dibujaTablero` para las 24. Ver
          `PieTablero.tsx`. */}
    </AbsoluteFill>
  );
};
