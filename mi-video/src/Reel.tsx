import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { Ad } from "./Ad";
import { BigTitle } from "./components/BigTitle";
import { BarWipe } from "./components/BarWipe";
import { Filete } from "./components/Filete";
import { SidePanel } from "./components/SidePanel";
import { Tarjeta } from "./components/Tarjeta";
import { Cortinilla } from "./components/Cortinilla";
import { Contraste } from "./components/Contraste";
import { CtaCard } from "./components/CtaCard";
import { MotionSound } from "./components/MotionSound";
import { Capas, PunchIn } from "./components/Capas";
import { subtitulosVisibles } from "./reel/subtitulos";
import { FPS } from "./brand/tokens";
import spec from "./reels.json";
import type { ReelSpec } from "./reel/tipos";

export type { ReelSpec } from "./reel/tipos";

export const REELS: ReelSpec[] = spec as unknown as ReelSpec[];

/** Desvanece lo de debajo en vez de cortarlo: la capa sustituye, no salta. */
const Aparece: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [0, 9], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ opacity: p }}>{children}</AbsoluteFill>;
};

/**
 * Un reel completo: **el orden en que se apilan las capas**, y nada más.
 *
 * Lo que cada pieza declara vive en [`reel/tipos`](./reel/tipos.ts) y la regla
 * de cuándo calla el subtítulo, en
 * [`reel/subtitulos`](./reel/subtitulos.ts) — que es montaje, no dibujo. Aquí
 * queda lo único que es de dibujo: qué va encima de qué, que es exactamente lo
 * que hay que poder leer de un vistazo cuando una capa aparece donde no debe.
 */
export const Reel: React.FC<{ spec: ReelSpec }> = ({ spec: r }) => {
  const captions = subtitulosVisibles(r);
  return (
  <>
    {/**
     * **La música NO va aquí.** Vive en `scripts/musica.sh`, en el paso de
     * audio.
     *
     * Estuvo aquí como un `<Audio>` a volumen fijo, y ahí es imposible hacer lo
     * que pidió Jaime: *«se baja el volumen de las frecuencias que interfieran
     * con la voz»*. Para tallar la banda de la voz hacen falta las dos señales
     * por separado y encadenadas, y Remotion sólo ve una mezcla.
     *
     * Con fader plano el problema no se resuelve: la música sigue ocupando la
     * banda de la voz, sólo que más flojito; y bajada lo suficiente para no
     * estorbar, deja de aportar el pulso que venía a aportar.
     */}
    {/**
     * El plano dentro de `PunchIn`: el camino decide si esa escena se mueve
     * dentro de si misma, y aqui solo se aplica. Escala el contenedor y no el
     * video, asi las capas de encima no viajan con el.
     */}
    <PunchIn capas={r.caminos.filter((c) => c.tipo === "punch")}>
      <Ad
        video={r.video}
        volumen={r.volumen ?? 1}
        coronilla={r.cara?.coronilla}
        lado={r.lado}
        mode="evidence"
        captions={captions}
        boards={r.boards}
        desatura={r.desatura}
        glitch={r.glitch}
        virados={r.virados}
      />
    </PunchIn>
    <BigTitle lineas={r.lineas} entraEn={r.entra} sostiene={r.sostiene} />
    {/**
     * Las ilustraciones y los movimientos que el camino de cada segmento pide.
     *
     * Van **despues del rotulo y antes de las tarjetas**: el gancho apila sobre
     * la cara, pero una tarjeta o una cortinilla ocupan el cuadro entero y ahi
     * no hay nada que acompanar.
     */}
    <Capas capas={r.caminos} sonido={r.sonido} />
    {/**
     * La tarjeta entra con la barra POR DELANTE y la toma anterior
     * desvaneciéndose por debajo.
     *
     * La barra ya no cruza en cada cambio de encuadre — ahí quedaba peor que el
     * salto que venía a tapar. Su único trabajo ahora es **traer un gráfico**:
     * pasa, y detrás queda la tarjeta. El movimiento tiene un motivo.
     */}
    {/**
     * Van DESPUÉS del vídeo y ANTES de todo lo demás: tapan la costura sin
     * tapar el subtítulo, que sigue siendo capa portante.
     */}
    {/**
     * La transición animada, en la costura donde se pidió.
     *
     * Va **encima del plano y de sus capas** —tiene que cruzar por delante de
     * lo que haya— y **debajo de la tarjeta y del CTA**, que ocupan el cuadro
     * entero: un filete cruzando por encima de una tarjeta no tapa ninguna
     * costura, la raya.
     */}
    {(r.filetes ?? []).map((f) => (
      <Filete
        key={`f${f.at}`}
        en={f.at}
        dura={f.duration}
        grosor={f.grosor}
        segundo={f.segundo}
      />
    ))}
    {r.cortinillas.map((c) => (
      <Sequence key={`c${c.at}`} from={c.at} durationInFrames={c.duration}>
        <Cortinilla {...c.props} />
      </Sequence>
    ))}
    {/* El chasquido, en el mismo frame que la distorsión. */}
    {r.glitch.map((g) => (
      <MotionSound key={`g${g.at}`} motion="glitch" at={g.at} />
    ))}
    {r.tarjetas.map((t) => (
      <Sequence key={t.at} from={t.at} durationInFrames={t.duration}>
        <Aparece>
          <Tarjeta {...t.props} />
        </Aparece>
        <BarWipe en={5} dura={11} tono="gold" />
      </Sequence>
    ))}
    {r.contraste ? (
      <Sequence
        from={r.contraste.at}
        durationInFrames={r.contraste.duration}
      >
        <Contraste {...r.contraste.props} />
      </Sequence>
    ) : null}
    {r.paneles.map((p) => (
      <Sequence key={p.at} from={p.at} durationInFrames={p.duration}>
        <SidePanel bloques={p.bloques} lado={r.lado} />
      </Sequence>
    ))}
    {r.cta ? (
      <Sequence
        from={Math.round(r.cta.at * FPS)}
        durationInFrames={Math.round(r.cta.dur * FPS)}
      >
        <CtaCard
          kicker="Bootcamp en vivo"
          promesa={r.cta.promesa}
          fecha={r.cta.fecha}
          precio={r.cta.precio}
          corrige={r.cta.corrige}
          cuenta={r.cta.cuenta}
          duracion={r.cta.duracion}
          placa={r.cta.placa}
          accion="Link abajo"
        />
      </Sequence>
    ) : null}
  </>
  );
};
