import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { color, videoText, tracking } from "../brand/tokens";
import { Casillas } from "./Casillas";
// El contrato del panel vive aparte, como el de las otras seis formas: ver
// `panel/tipos.ts`.
import type { SidePanelProps } from "./panel/tipos";
import { Reparto } from "./Reparto";
import { Volumen as Escena3D } from "./Volumen";
import { useLienzo } from "../brand/LienzoContexto";

/**
 * Bloques que se construyen **en el espacio libre del plano abierto**.
 *
 * Idea de Jaime: en vez de cortar, irse una vez al plano más lejano y animar en
 * el hueco que queda al lado del sujeto. El cambio de escena deja de verse
 * porque no hay corte — lo que cambia es lo que ocupa el cuadro.
 *
 * Es fotomontaje constructivista en su forma literal: geometría compuesta
 * **con** la fotografía, no encima de ella. Y es el registro Gen Z/Alpha del
 * sistema — bloques planos apilados, tipografía cinética, entrada por peso y no
 * por fundido.
 *
 * Cada bloque entra por su lado y se queda: la pila se construye, no aparece.
  * @clase capa
*/
export const SidePanel: React.FC<SidePanelProps> = ({
  bloques, lado, ladoVolumen, volumen, hueco, fuente,
  casillas, reparto, eje, sfx = null, escalon = LEE, paso = 8,
}) => {
  const layout = useLienzo();
  const franja = layout.franja;
  const frame = useCurrentFrame();
  // **El bloque que no cabe falla, no se recorta.** El `overflow: hidden` de
  // abajo es correcto —impide que una tercera línea se coma la cara— pero
  // callaba: reel-04 e5 rotulaba «NO PUEDE / PROBAR EL» y la palabra que hacía
  // significar la frase no llegaba a la pantalla. El tope está medido sobre
  // render y vive en `copy.ts` con los demás.
  for (const b of bloques) assertShort(b.texto, "panel", "SidePanel.bloque");
  // **El pie va en UNA línea, y eso es un tope, no un deseo.**
  //
  // Medido sobre el ancho útil —1080 menos las dos zonas seguras, 950 px— con
  // JetBrains Mono a 18 px y el tracking de `data`: el avance es de 11,9 px por
  // carácter, o sea 79 caben. Se cortan en 78 para no jugarse el último. Por
  // encima de eso el pie se parte en dos líneas y deja de ser un pie: es un
  // párrafo debajo del panel, que es justo lo que había que quitar.
  if (fuente && fuente.length > PIE_MAX)
    throw new Error(
      `SidePanel.fuente: ${fuente.length} caracteres y el pie va en una línea` +
      ` (máx. ${PIE_MAX}). Recórtalo dejando la cifra y el tramo: «${fuente}»`,
    );
  /**
   * El panel ocupa el 42% del ancho. Con el sujeto descentrado —el ancla cae
   * hacia un lado en las seis tomas— ese hueco existe de verdad; medirlo es lo
   * que impide que el bloque acabe sobre la cara.
   */
  const ancho = layout.width * 0.44;
  /**
   * Cuerpo ajustado al bloque mas largo, no fijo.
   *
   * Con tamano fijo se partia «$30,00 / 0» y «FACTURACI / ÓN», y el ultimo
   * bloque se salia del cuadro. El hueco del plano da lo que da; el texto se
   * adapta a el, no al reves.
   *
   * **El interletrado cuenta.** La primera version uso 0,62 em por caracter —el
   * avance de la Montserrat 900 en versales— y siguio saliendose: las etiquetas
   * llevan `tracking.labelMono`, que son **0,2 em mas por caracter**. Sumarlo es
   * la diferencia entre caber y no caber. Aun asi se salia: el valor final
   * (1,0 em para etiquetas) esta **medido sobre render**, no derivado. Estimar
   * el ancho de un texto sin medirlo tiene un error irreducible; el margen se
   * paga en cuerpo, que es barato, y no en texto cortado, que no lo es.
   */
  const AVANCE_FUERTE = 0.78;
  const AVANCE_ETIQUETA = 1.0;
  const cuerpo = (fuerte: boolean) => {
    const tope = fuerte ? videoText.title : Math.round(videoText.caption * 0.8);
    const AVANCE = fuerte ? AVANCE_FUERTE : AVANCE_ETIQUETA;
    const largo = Math.max(
      ...bloques.filter((b) => !!b.fuerte === fuerte).map((b) => b.texto.length),
      1,
    );
    // **Y un suelo, porque encoger no es una solucion infinita.**
    //
    // Esta cuenta supone UNA linea, asi que con un bloque de 22 caracteres da
    // 475/22 = 21 px. Medido en el render de reel-07: los dos paneles salian a
    // ~21 px arriba a la derecha, ilegibles — y no era de esa pieza, le pasa a
    // cualquier bloque de mas de ~10 caracteres, en todas.
    //
    // Un tablero que no se lee no esta en el video aunque este en el frame. Asi
    // que por debajo del minimo el texto **se reparte en lineas** en vez de
    // seguir encogiendo, y si aun asi no cabe, eso es texto de mas y se ve —
    // que es un fallo visible, mejor que uno invisible.
    return Math.max(MINIMO, Math.min(tope, ancho / (largo * AVANCE)));
  };

  //: Por debajo de esto no se lee a distancia de brazo. Es el mismo suelo
  //: medido que usa la franja del subtitulo (`src/brand/franja.json`), y por el
  //: mismo motivo: el limite no es geometrico, es de vista.
  const MINIMO = 34;

  //: Cuantas lineas puede ocupar un bloque antes de que sobre texto. Dos: una
  //: etiqueta de panel que necesita tres ya no es una etiqueta.
  const LINEAS_MAX = 2;

  /**
   * **El oro sale UNA vez por panel, y con volumen el oro es del volumen.**
   *
   * El bloque `fuerte` ya dejó de repartir oro a los demás; faltaba la otra
   * mitad, que sólo se ve con la lámina delante: **el volumen también lleva
   * oro** —lo lleva por diseño, es su único tono vivo—, así que un panel con
   * volumen y bloque fuerte ponía dos acentos a 200 px uno del otro. Se vio en
   * reel-05 e7: la losa dorada del umbral y la cinta dorada de «SE ACTIVÓ SOLO»
   * peleando en la misma esquina. Jaime: *«si hay tres cosas en oro, dos
   * sobran; el oro dice mira aquí y con tres no lo dice nadie»*.
   *
   * Quién se queda con él no es arbitrario: **el volumen es lo que argumenta** y
   * el bloque es su rótulo. Y el bloque no se queda sin jerarquía — invierte la
   * cinta, clara con texto negro, que es el contraste que el canon ya reserva
   * para eso y no gasta el acento.
   */
  // **Y con lámina, el oro es de la lámina**, por lo mismo: la casilla sellada
  // es lo que argumenta y el bloque de al lado es su rótulo. Dos acentos en la
  // misma esquina y el oro deja de decir «mira aquí».
  // Y con reparto el oro es de la porción con `foco`, por lo mismo: la cifra que
  // queda es lo que argumenta y el bloque de al lado es su premisa.
  const oroEnTexto = !volumen && !casillas?.some((c) => c.sella) && !reparto;

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        flexDirection: "column",
        // **Arriba, por encima de la cara.** Centrado caía en la franja del
        // rostro —que ocupa del 24 al 40% de altura— y tapaba los ojos. Jaime:
        // «misma facturación tapa la mitad de la cara, puede quedar un poco más
        // arriba». El sitio es la banda entre la zona segura y la frente.
        justifyContent: "flex-start",
        alignItems: lado === "der" ? "flex-end" : "flex-start",
        paddingLeft: lado === "der" ? 0 : layout.safe.left,
        paddingRight: lado === "der" ? layout.safe.right : 0,
        paddingTop: layout.height * 0.115,
        paddingBottom: layout.height * 0.42,
      }}
    >
      {/* Va primero, y por eso queda DEBAJO de los bloques: el volumen es lo
          que el ancla significa, no lo que se lee. Está fuera del flujo —lleva
          su propio `position: absolute`— así que no empuja la pila. */}
      {volumen ? (
        <Escena3D nombre={volumen} lado={ladoVolumen ?? lado} hueco={hueco} />
      ) : null}
      {/* **La lámina, ARRIBA de los bloques y en el flujo**: los bloques que la
          acompañan son su pie —«virtual · en vivo · en español» bajo la tira de
          días—, no un rótulo aparte. Ver `Casillas`. */}
      {casillas?.length ? (
        <Casillas
          casillas={casillas}
          eje={eje}
          ancho={ancho}
          sfx={sfx}
          alinea={lado}
        />
      ) : null}
      {bloques.map((b, i) => {
        const t = frame - i * escalon;
        const p = interpolate(t, [0, paso], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        if (p <= 0) return null;
        const dx = (lado === "der" ? 1 : -1) * (1 - p) * layout.width * 0.5;
        return (
          <div
            key={b.texto}
            style={{
              maxWidth: ancho,
              // **Parte linea en vez de encogerse hasta no leerse.**
              //
              // Estaba en `nowrap` para que no se saliera por la derecha, y la
              // otra mitad de esa decision era encoger el cuerpo sin suelo: con
              // 22 caracteres salia a 21 px. Con el suelo puesto, lo que hace
              // falta es dejarle repartirse — el `maxWidth` sigue impidiendo
              // que se salga, y `LINEAS_MAX` acota cuanto puede crecer hacia
              // abajo antes de que sea texto de mas.
              whiteSpace: "normal",
              maxHeight: `${LINEAS_MAX * 1.05}em`,
              textAlign: lado === "der" ? "right" : "left",
              marginBottom: 10,
              padding: "0.12em 0.3em",
              position: "relative",
              overflow: "hidden",
              backgroundColor: !b.fuerte
                ? color.richBlack
                : oroEnTexto
                  ? color.gold
                  : color.lightNeutral,
              // **El oro sale una vez por panel: en el bloque `fuerte`.**
              //
              // Esto pintaba en oro el texto de TODOS los bloques que no fueran
              // `fuerte`, asi que un panel de tres bloques ponia tres cosas en
              // oro. El canon dice lo contrario y dice por que: *«el oro dice
              // "mira aqui"; si en un tablero hay tres cosas en oro, dos sobran,
              // el ojo no sabe donde ir y el recurso deja de significar nada»*.
              //
              // Lo que no es el foco va en neutro claro, que es lo que el canon
              // reserva para texto sobre oscuro. La jerarquia la marca el
              // contraste —placa de oro contra negro—, no repetir el acento.
              color: b.fuerte ? color.richBlack : color.lightNeutral,
              fontFamily: fontFamily.video,
              fontSize: cuerpo(!!b.fuerte),
              fontWeight: 900,
              lineHeight: 1.02,
              letterSpacing: b.fuerte ? videoText.tracking : tracking.labelMono,
              textTransform: "uppercase",
              transform: `translateX(${dx}px)`,
              opacity: p,
            }}
          >
            {b.placa ? (
              <Img
                src={staticFile(`fondos/${b.placa}.png`)}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  // Un recorte, no una imagen: se ve el material del collage
                  // pero el bloque sigue leyéndose como bloque plano.
                  opacity: 0.5,
                }}
              />
            ) : null}
            <span style={{ position: "relative" }}>{b.texto}</span>
          </div>
        );
      })}
      {/**
       * **El reparto, DEBAJO de los bloques y empezando cuando ya se leyeron.**
       *
       * Los dos detalles son la misma regla —el orden de lectura lo manda lo que
       * la lámina afirma— y salieron de mirar el fotograma, no de deducirlos:
       * puesto arriba, la barra daba la respuesta antes de que nadie hubiera
       * dicho de qué era; puesto abajo pero entrando en el frame 0, la premisa y
       * el reparto se construían a la vez y no se leía ninguno.
       *
       * `pie={false}` porque el panel ya imprime la fuente abajo, fuera de la
       * zona segura: repetirla aquí son 92 px más de figura, y en el hueco del
       * plano esos 92 px caen sobre su cabeza.
       */}
      {reparto ? (
        <Reparto
          total={reparto.total}
          porciones={reparto.porciones}
          signo={reparto.signo}
          etiqueta={reparto.etiqueta}
          ancho={ancho}
          desde={bloques.length * escalon}
          source={fuente ?? ""}
          pie={false}
        />
      ) : null}
      {/**
       * **El pie, FUERA de la zona segura y en una línea.**
       *
       * Mismo sitio y mismo trato que el de `PanelDentro`, que es el que Jaime
       * aprobó: pegado por debajo de `franja.sueloPx` —no al fondo del cuadro,
       * que ahí lo tapa la interfaz de Meta— y con su banda propia, porque sobre
       * el plano no se lee ni parando la pieza. *«No me interesa que lo lean,
       * sólo que sepan que existe»*, y acto seguido *«ahora que si lo leen, pues
       * que esté bien leído»*.
       *
       * Entra con el último bloque y no antes: es el pie de lo que se acaba de
       * decir, no un rótulo que espera al texto.
       */}
      {fuente ? (
        <div
          style={{
            position: "absolute",
            left: layout.safe.left,
            top: franja.sueloPx + 14,
            width: layout.width - layout.safe.left - layout.safe.right,
            padding: "10px 14px",
            backgroundColor: color.richBlack,
            fontFamily: fontFamily.data,
            fontSize: PIE_CUERPO,
            lineHeight: 1.4,
            letterSpacing: "0.06em",
            // En una línea de verdad: si algún día el tope de arriba se relaja,
            // esto lo deja en evidencia en vez de dejarlo caer a dos líneas.
            whiteSpace: "nowrap",
            overflow: "hidden",
            textTransform: "uppercase",
            color: color.secondaryBlue,
            opacity: interpolate(
              frame - bloques.length * escalon,
              [0, 12],
              [0, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
            ),
          }}
        >
          {fuente}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

/**
 * **El cuerpo del pie y lo que cabe en su línea**, y el segundo sale del
 * primero medido, no estimado.
 *
 * Ancho útil: 1080 menos las dos zonas seguras de 65 px = 950. JetBrains Mono
 * a 18 px avanza 0,6 em por carácter y el tracking de `data` añade 0,06 em, o
 * sea 11,88 px: caben 79. Se corta en 78 para no jugarse el último.
 */
const PIE_CUERPO = 18;
const PIE_MAX = 78;

/**
 * **Lo que cuesta leer un bloque, y por eso es lo que se espera antes de meter
 * el siguiente.**
 *
 * 0,75 s, que es la misma cifra con la que `scripts/reels/lectura.mjs ::
 * ADELANTO` **ya reservaba** el hueco del panel —*«0,75 s por bloque más medio
 * segundo de respiro»*—. Estaba reservada y no la usaba el que dibuja: con 7
 * frames los tres bloques de reel-01 e2 entraban en 0,7 s y el panel se quedaba
 * quieto los cinco segundos siguientes. Eso es literalmente lo que Jaime llamó
 * «tres rótulos quietos» (C-254) — el tiempo estaba comprado y no se gastaba.
 *
 * Con la biblioteca de figuras cerrada pesa el doble: lo único que puede
 * construirse mientras él habla es la tipografía, y si entra de golpe no
 * construye nada.
 *
 * **Cabe siempre, por construcción**: el spec le reserva al panel
 * `(0,75 n + 0,5) s` como mínimo y el último bloque entra en
 * `0,75 (n−1) s + paso`.
 */
const LEE = 22;
