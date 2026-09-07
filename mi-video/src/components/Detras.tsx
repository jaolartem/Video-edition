import React from "react";
import {
  AbsoluteFill,
  Easing,
  OffthreadVideo,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { color } from "../brand/tokens";
import { Titular, type Rotulo } from "./Gancho";

/**
 * **Lo que pasa POR DETRÁS de él.**
 *
 * Jaime, pidiéndolo: *«y ojalá jueguen con mi cara, es decir que se pasen por
 * arriba, por abajo, que se escondan detrás»*.
 *
 * Dos capas y el orden es todo el componente:
 *
 *     el elemento  ->  el recorte del sujeto (WebM con alfa)
 *
 * El recorte es el mismo plano que ya se está viendo, con el fondo borrado por
 * la máscara de MediaPipe (`scripts/text-behind.py`). Apilado encima del
 * elemento y **en el mismo sitio del que salió**, devuelve la figura al frente:
 * lo que quedaba tapado por su hombro vuelve a estar tapado, y lo que asomaba
 * por encima de su cabeza sigue asomando. De ahí sale la profundidad.
 *
 * ## La raya de Jaime, y dónde está de verdad
 *
 * Se probó el texto detrás de la figura y el sujeto tapaba la mayor parte:
 * *«el efecto se lucía a costa del mensaje»*. Durante un tiempo eso se escribió
 * aquí como «copy, nunca», y era leerlo de más: **el límite es de sitio, no de
 * capa**. Se midió a la altura del pecho, donde él ocupa el cuadro entero; por
 * encima de su coronilla lo único que le tapa es el pelo.
 *
 * Por eso el `titular` del gancho SÍ es un elemento de ésta familia —el rótulo
 * pasándole por detrás de la cabeza, aprobado el 6-9-2026— y todo lo demás
 * sigue igual: el subtítulo se dibuja más arriba en la pila y no se entera de
 * que esto existe. Quien comprueba que el rótulo no baje de ahí es
 * `scripts/reels/portada.mjs`.
 *
 * ## Y el elemento dice lo que dice la etapa
 *
 * Regla del canon desde que se retiraron las animaciones simples: *«ahora sólo
 * animaciones complejas que muestren luz o movimiento, y que estén en
 * consonancia con la idea del tablero o del panel»*. Un elemento bonito que
 * ilustra otra cosa es peor que ninguno.
 * @clase capa
 */
export type DetrasProps = {
  /** Qué se esconde detrás. El catálogo vive en `DETRAS`, en `camara.mjs`. */
  elemento: string;
  /** Sólo para `titular`: el rótulo del gancho. Ver `Gancho.tsx`. */
  rotulo?: Rotulo;
  /** El recorte con alfa, relativo a `public/`. */
  src: string;
  /**
   * El mismo filtro que lleva el plano en este frame.
   *
   * Sin esto, un tramo en blanco y negro o un virado dejaría al plano teñido y
   * a su silueta en color: dos versiones de la misma cara en el mismo frame,
   * recortadas la una sobre la otra. La marca de humanidad es un comentario
   * sobre lo que se dice, y no puede partirse por la mitad.
   */
  filtro?: string;
};

/**
 * Cuánto mide la columna y dónde para. Múltiplos del módulo, a escuadra.
 *
 * **El suelo son 780 y no el borde de la franja**, y el número tiene motivo: el
 * gancho ya reserva de 790 para abajo —ahí entra el pictograma del camino
 * `portada`, en `Capas.tsx`, y a 1015 cruza su filete—. Una columna que bajara
 * más se pintaría debajo de esas dos capas, que van por encima de todo esto.
 *
 * Y el techo sale de la cuenta contraria: cuatro escalones desde 780 dejan el
 * último en 244, o sea **por encima de su coronilla**, que es lo único que esta
 * figura tiene que conseguir. Con cinco se salía de la zona segura (220).
 */
const BLOQUE = { alto: 128, hueco: 8, ancho: 760, suelo: 780, cuantos: 4 };

/**
 * **La columna que sube y le pasa por detrás.**
 *
 * Bloques planos que aterrizan de uno en uno desde la izquierda, apilándose
 * desde la altura del pecho hasta por encima de su cabeza. El último se enciende
 * en oro —lo único que hay que mirar— y un barrido de luz de borde duro recorre
 * la columna entera cuando ya está puesta.
 *
 * Dice lo que dice la etapa que la pide: **algo creció por encima de quien lo
 * mira**. Por eso apila en vez de crecer o girar, por eso el último queda más
 * alto que él, y por eso entra por el lado libre y termina metida detrás de su
 * hombro: la columna ocupa el sitio que él no ocupa y el resto lo tapa él.
 *
 * Nada de rebote ni de fundido: `Easing.out(cubic)` es masa frenando, que es
 * como se mueven las cosas que pesan.
 */
const Columna: React.FC = () => {
  const frame = useCurrentFrame();
  // El barrido entra cuando el último bloque ya aterrizó: 8 + 3·11 + 13 = 54.
  const luz = interpolate(frame, [56, 78], [-260, 1180], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.quad),
  });
  const alto = BLOQUE.cuantos * (BLOQUE.alto + BLOQUE.hueco);
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {Array.from({ length: BLOQUE.cuantos }, (_, k) => {
        const arriba = k === BLOQUE.cuantos - 1;
        const p = interpolate(frame, [8 + k * 11, 21 + k * 11], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        return (
          <div
            key={k}
            style={{
              position: "absolute",
              left: 0,
              top: BLOQUE.suelo - (k + 1) * (BLOQUE.alto + BLOQUE.hueco),
              width: BLOQUE.ancho,
              height: BLOQUE.alto,
              background: arriba ? color.gold : color.navy,
              // Filete, no sombra: el canon separa bloques con una línea.
              borderTop: `3px solid ${arriba ? color.richBlack : color.lightNeutral}`,
              transform: `translateX(${((1 - p) * -880).toFixed(1)}px)`,
            }}
          />
        );
      })}
      {/**
       * El barrido: una banda de borde duro que cruza la columna.
       *
       * Es luz y no un degradado —los degradados suaves están prohibidos por
       * nombre—, así que es un plano de color en `screen` con los cantos
       * rectos. Sale de la misma familia que el corredor de `Desvio` (C-241).
       */}
      <div
        style={{
          position: "absolute",
          left: luz,
          top: BLOQUE.suelo - alto,
          width: 120,
          height: alto,
          background: color.lightNeutral,
          opacity: 0.42,
          mixBlendMode: "screen",
          transform: "skewX(-18deg)",
        }}
      />
    </AbsoluteFill>
  );
};

/**
 * Una etapa que pidió algo por detrás. Lo emite `reels/imagen.mjs` desde el
 * plan, y sólo cuando el recorte existe de verdad en `public/`.
 */
export type Recorte = {
  at: number;
  duration: number;
  elemento: string;
  src: string;
  /** Sólo el `titular`: qué dice el rótulo del gancho y dónde va. */
  rotulo?: Rotulo;
};

export const Detras: React.FC<DetrasProps> = ({
  elemento,
  src,
  filtro,
  rotulo,
}) => (
  <AbsoluteFill>
    {elemento === "columna" ? <Columna /> : null}
    {elemento === "titular" && rotulo ? <Titular rotulo={rotulo} /> : null}
    {/**
     * **El recorte va ENCIMA del elemento, y el `AbsoluteFill` no es adorno.**
     *
     * `OffthreadVideo` se pinta como un elemento **en flujo normal**, y en CSS
     * lo posicionado pinta por encima de lo que no lo está: sin envolverlo, el
     * vídeo quedaba DEBAJO del `AbsoluteFill` del elemento y la capa no aparecía
     * en ningún frame — sin error, sin log y con el fichero bien servido.
     *
     * `transparent` es lo otro que no se puede quitar: sin él Chromium descarta
     * el canal alfa del VP9 y la capa sale opaca, o sea el plano dibujado dos
     * veces y el elemento enterrado. `muted` porque el audio ya lo lleva el
     * plano de abajo — la misma voz dos veces sonaría con flanger.
     */}
    <AbsoluteFill>
      <OffthreadVideo
        src={staticFile(src)}
        transparent
        muted
        style={filtro ? { filter: filtro } : undefined}
      />
    </AbsoluteFill>
  </AbsoluteFill>
);

/**
 * Las de la pieza, ya colocadas.
 *
 * Vive aquí y no en `Ad.tsx` para que el orden de apilado de esta familia esté
 * escrito en un solo fichero: allí sólo se dice **dónde** entra en la pila —
 * encima del plano y debajo de todo lo demás.
 */
export const Recortes: React.FC<{ lista: Recorte[]; filtro?: string }> = ({
  lista,
  filtro,
}) => (
  <>
    {lista.map((r, i) => (
      <Sequence key={`d${r.at}-${i}`} from={r.at} durationInFrames={r.duration}>
        <Detras
          elemento={r.elemento}
          src={r.src}
          filtro={filtro}
          rotulo={r.rotulo}
        />
      </Sequence>
    ))}
  </>
);
