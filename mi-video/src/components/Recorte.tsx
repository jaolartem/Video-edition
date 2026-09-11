import React from "react";
import { OffthreadVideo, staticFile } from "remotion";
import { color } from "../brand/tokens";

/**
 * **La pegatina: él recortado, en blanco y negro y con canto de papel rasgado.**
 *
 * Aprobado por Jaime el 6-9-2026 sobre reel-02 e2, donde nació como capa 3 de
 * *«El panel con él dentro»*: la placa, las masas negras, **él recortado** y
 * encima la figura que argumenta. *«Todo el color lo llevan las formas.»*
 *
 * **Y ya no es del panel.** Jaime: *«en la biblioteca ya quedó el sticker
 * blanco y negro con textura de papel roto, ese ya debe estar como elemento
 * disponible para todos»*. Lo que lo ataba no era el tratamiento —eso es suyo—
 * sino la colocación: `lado` sólo admitía los tres sitios medidos contra
 * `PanelDentro`, así que fuera de ese panel no había forma de ponerlo donde uno
 * quisiera. Ahora hay dos entradas y **la de los tres sitios no cambió**:
 * `lado` para quien componga dentro del panel, `sitio` para el resto.
 *
 * ## Lo que hace, y lo que NO
 *
 * Recibe el recorte con alfa que produce `scripts/text-behind.py` —el canto de
 * papel ya viene rasgado desde ahí, con su semilla constante— y le aplica el
 * tratamiento **por fotograma, dentro del render**: gris más **doce escalones
 * discretos**.
 *
 * Los escalones van aquí y no en Python por el motivo de siempre: el sistema
 * visual vive en Remotion. En Python quedarían escritos en el píxel, así que
 * cambiar de blanco y negro a sepia obligaría a volver a pasar MediaPipe por la
 * etapa entera — y el tratamiento **cambia por etapa**, que es justo el grado de
 * libertad que Jaime pidió.
 *
 * ## Los doce escalones, y por qué doce
 *
 * *«Con tres dijo "quedó irreconocible"; con seis, "un poquito mucho más"»*. Doce
 * es lo que quedó: bastantes para que la cara siga siendo una cara, pocos para
 * que el plano deje de ser una foto y pase a ser material del tablero.
 *
 * Se hacen con `feComponentTransfer type="discrete"`, que es la única primitiva
 * que corta la rampa en escalones de verdad.
 *
 * **El estirado previo NO va aquí**, y eso costó un fotograma: la receta del
 * canon dice *«doce escalones por percentiles del 5 al 95 dentro de la
 * máscara»*, y un filtro SVG no mira el histograma ni sabe dónde está la
 * máscara. Sin estirar, en una habitación en penumbra los doce niveles se
 * reparten sobre un rango que la toma no usa: el sujeto entero cae en los tres
 * de abajo y sale como una mancha negra sobre la masa negra. El estirado lo
 * hace `scripts/dominio/papel.py`, que es donde la máscara existe.
 *
 * ## Lo que NO se elige a mano
 *
 * `tratamiento` sale de `escena_desc.color` (avivar / apagar / dejar) y lo
 * resuelve `scripts/imagen.mjs` antes de llegar aquí, igual que el virado del
 * plano: el nombre y el filtro se declaran en el mismo sitio o se separan. Jaime
 * lo puso como condición: *«en color o en sepia, depende de la composición, del
 * arco emocional y del arco narrativo»* — del arco, no del gusto.
 * @clase capa
 */

/** Dónde se coloca **dentro del panel**. *«Ahora yo puedo ir abajo o al otro lado.»* */
export type Lado = "izquierda" | "derecha" | "abajo";

/**
 * **Dónde cae, en píxeles del cuadro de 1080×1920.**
 *
 * Se ancla por el borde que se declare: `left` **o** `right`, `top` **o**
 * `bottom` — uno de cada eje, ni ninguno ni los dos. Con los dos horizontales
 * el ancho decide cuál gana y el otro se ignora en silencio; sin ninguno
 * vertical cae en el 0 sin que nadie lo haya pedido. Las dos formas colocan la
 * figura en un sitio que no se declaró, y eso sólo se ve sacando el fotograma —
 * que es el error que más caro sale en este proyecto. Lo para `anclado`.
 *
 * `ancho` es lo único obligatorio: el alto sale de él, porque el recorte
 * conserva la proporción del cuadro.
 */
export type Sitio = {
  ancho: number;
  left?: number;
  right?: number;
  top?: number;
  bottom?: number;
};

/**
 * Un sitio declarado a medias no se dibuja: se denuncia.
 *
 * @throws si falta el anclaje de un eje o si están los dos del mismo eje.
 */
const anclado = (s: Sitio, de: string): Sitio => {
  const eje = (a?: number, b?: number) =>
    (a === undefined ? 0 : 1) + (b === undefined ? 0 : 1);
  const h = eje(s.left, s.right);
  const v = eje(s.top, s.bottom);
  if (h !== 1 || v !== 1) {
    throw new Error(
      `Recorte: el sitio ${de} declara ${h} anclaje(s) horizontal(es) y ${v}` +
        " vertical(es), y va uno de cada: `left` o `right`, `top` o `bottom`." +
        " Con los dos de un eje gana uno y el otro no hace nada; sin ninguno" +
        " cae en el 0. Las dos cosas colocan la figura donde nadie dijo.",
    );
  }
  return s;
};

/** Cuántos escalones. Ver arriba: no es un número redondo, es lo calibrado. */
const ESCALONES = 12;

/** El id del filtro. Uno solo: los escalones son los mismos para los tres tratos. */
const FILTRO = "recorte-escalones";

const tabla = Array.from({ length: ESCALONES }, (_, i) =>
  (i / (ESCALONES - 1)).toFixed(4),
).join(" ");

/**
 * **Los tres sitios del panel**, medidos contra `PanelDentro`.
 *
 * Son un atajo con nombre, no la única forma de colocarlo: quien componga fuera
 * del panel pasa `sitio` y lo pone donde quiera. Estos tres siguen aquí, con
 * los mismos números, porque los números **son del panel** —de su columna de
 * contenido y del techo de la franja— y perderlos sería tener que volver a
 * medirlos mirando fotogramas.
 *
 * El recorte llega **a tamaño de cuadro completo** —`text-behind.py` escribe el
 * mismo 1080×1920 con el fondo borrado—, así que colocarlo es escalarlo y
 * moverlo. Los tres sitios sangran por su borde: una figura recortada que flota
 * entera dentro del cuadro se lee como una pegatina, no como parte del collage.
 *
 * ## El ancho lo fija la columna; el `top`, la franja
 *
 * **620 no es un número redondo**: con el plano a 620 de ancho la figura ocupa
 * hasta el 501, y la columna de contenido de `PanelDentro` empieza en el 520.
 * Él llena su lado exacto y no invade el de las cifras.
 *
 * El `top` se calibró contra la lámina, que dibujaba sobre los 1920 enteros, y
 * en la pieza el panel acaba en el techo de la franja (1048): con 268 la
 * coronilla caía en el 515 y del 790 para abajo se lo comía el pie, así que de
 * él quedaba una cabeza en una esquina. Subido, entra **entero hasta el
 * regazo** dentro de la mitad que el panel sí tiene. La coronilla queda en el
 * 287, justo debajo de la banda de la premisa — la misma relación que en la
 * lámina, medida sobre el alto que hay y no sobre el que había.
 */
const SITIO: Record<Lado, Sitio> = {
  // **Torso y manos, no el cuerpo entero.** Jaime: *«mi imagen puede ocupar
  // más espacio y podemos cortar las piernas, sólo el torso y las manos»*, y
  // *«un poquito más centrado»*. Con 620 entraba de la coronilla al regazo y se
  // leía como una pegatina pequeña en el canto; a 800 el plano recorta por
  // debajo de las manos —el corte de `ZonaTablero` hace de encuadre— y él pasa
  // a ser una de las dos cosas grandes de la lámina, que es lo que era en la
  // maqueta. El `left` sube de -70 a -30: entra más y sigue sangrando por el
  // borde, porque entero dentro del cuadro volvería a ser pegatina.
  izquierda: { ancho: 980, left: -200, top: -180 },
  derecha: { ancho: 980, right: -200, top: -180 },
  abajo: { ancho: 900, left: 110, top: 70 },
};

/**
 * **Las dos formas de ponerlo, y no sólo la pegatina.**
 *
 * Jaime, 11-9-2026: *«debe haber más formatos de tablero, por ejemplo cuadrado y
 * a color cuando sea un tablero más formal, también en sepia o a color como
 * stiquer; no lo cierres a blanco y negro rasgado»*.
 *
 * - `pegatina` — la aprobada el 6-9: canto de papel rasgado y doce escalones.
 *   El color lo pone el tratamiento (blanco y negro, sepia o color).
 * - `cuadro` — el retrato formal: un cuadrado de canto limpio sobre el navy de
 *   la paleta, con su filete de 1 px y **sin escalones**, que es lo que lo hace
 *   foto y no collage. Pide su recorte con canto `limpio` (ver `sujeto.py`).
 */
export type Forma = "pegatina" | "cuadro";

/** Dónde va el cuadro. Entero dentro del cuadro: es un retrato, no sangra. */
const CUADRO: Record<Lado, Sitio> = {
  izquierda: { ancho: 400, left: 54, top: 250 },
  derecha: { ancho: 400, right: 54, top: 250 },
  abajo: { ancho: 400, left: 340, top: 560 },
};

export type RecorteProps = {
  /** El recorte con alfa, relativo a `public/`. Lo produce `text-behind.py`. */
  src: string;
  /** `pegatina` (por defecto) o `cuadro`. Lo elige quien diseña. */
  forma?: Forma;
  /**
   * Uno de los tres sitios del panel. Lo elige quien compone según dónde esté
   * el hueco. Para cualquier otra lámina, `sitio`.
   */
  lado?: Lado;
  /**
   * **Dónde va, en píxeles del cuadro.** Gana sobre `lado`, y es la entrada de
   * quien lo usa fuera del panel: `{ ancho: 520, right: -60, bottom: 40 }`.
   *
   * Se declara la posición y no el `lado` porque un nombre de lado sólo
   * significa algo dentro de la lámina que lo midió — es el mismo motivo por el
   * que en este proyecto no hay un `if (slug === …)`: si hace falta un caso, lo
   * que falta es el prop.
   */
  sitio?: Sitio;
  /**
   * El filtro de color ya resuelto, de `scripts/imagen.mjs`. Sin él sale el
   * blanco y negro del canon, que es el valor por defecto del tipo.
   */
  css?: string;
  /** 0 a 1. Lo pone quien lo hospeda con su propio horario. */
  entra?: number;
};

export const Recorte: React.FC<RecorteProps> = ({
  src,
  forma = "pegatina",
  lado = "izquierda",
  sitio,
  css = "grayscale(1) contrast(1.06)",
  entra = 1,
}) => {
  const cuadro = forma === "cuadro";
  // El sitio explícito gana; si no, el del lado. `?? SITIO.izquierda` sigue
  // cubriendo un `lado` que llegue del spec sin ser ninguno de los tres.
  const { ancho, ...donde } = anclado(
    sitio ?? (cuadro ? CUADRO[lado] : SITIO[lado]) ?? SITIO.izquierda,
    sitio ? "que le pasaron" : `«${lado}»`,
  );
  if (cuadro) {
    return (
      <div
        style={{
          position: "absolute",
          ...donde,
          width: ancho,
          height: ancho,
          opacity: entra,
          overflow: "hidden",
          pointerEvents: "none",
          backgroundColor: color.navy,
          border: `1px solid ${color.lightNeutral}`,
        }}
      >
        {/* El plano es vertical y el cuadro no: se encuadra por la cara, que
            en el recorte vive en el tercio de arriba. */}
        <OffthreadVideo
          src={staticFile(src)}
          transparent
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            objectPosition: "50% 22%",
            filter: css,
          }}
        />
      </div>
    );
  }
  return (
    <>
      {/**
       * El filtro vive en un SVG de tamaño cero: sólo tiene que estar en el
       * documento para que `url(#…)` lo encuentre. No dibuja nada.
       */}
      <svg
        aria-hidden
        style={{ position: "absolute", width: 0, height: 0 }}
      >
        <defs>
          <filter
            id={FILTRO}
            colorInterpolationFilters="sRGB"
            x="-2%"
            y="-2%"
            width="104%"
            height="104%"
          >
            {/**
             * Los escalones. **Sin `feFuncA`**: el canal alfa trae el canto de
             * papel, y escalonarlo lo devolvería a un borde de tijera de doce
             * niveles — justo lo que la orla de fibra viene a evitar.
             */}
            <feComponentTransfer>
              <feFuncR type="discrete" tableValues={tabla} />
              <feFuncG type="discrete" tableValues={tabla} />
              <feFuncB type="discrete" tableValues={tabla} />
            </feComponentTransfer>
          </filter>
        </defs>
      </svg>
      <div
        style={{
          position: "absolute",
          ...donde,
          width: ancho,
          // El recorte conserva la proporción del cuadro: es el mismo plano.
          height: Math.round((ancho * 1920) / 1080),
          opacity: entra,
          pointerEvents: "none",
          // **El corte de abajo también rasgado.** Lo cortaba la caja de
          // `ZonaTablero` en una horizontal perfecta, y una figura de papel con
          // un lado recto deja de ser papel. La máscara lleva la misma receta
          // que el contorno —grano grueso más fibra fina— para que sea el mismo
          // desgarro.
          WebkitMaskImage: `url(${staticFile("canto-abajo.png")})`,
          maskImage: `url(${staticFile("canto-abajo.png")})`,
          WebkitMaskSize: "100% 100%",
          maskSize: "100% 100%",
        }}
      >
        {/**
         * `transparent` no se puede quitar: sin él Chromium descarta el canal
         * alfa del VP9 y el recorte sale como un rectángulo opaco encima del
         * tablero. `muted` porque la voz ya la lleva el plano de debajo — la
         * misma voz dos veces suena con flanger.
         */}
        <OffthreadVideo
          src={staticFile(src)}
          transparent
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: `${css} url(#${FILTRO})`,
          }}
        />
      </div>
    </>
  );
};
