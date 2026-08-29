import React from "react";
import {
  AbsoluteFill,
  Sequence,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { Ad, type BoardCue, type CaptionCue } from "./Ad";
import { BigTitle } from "./components/BigTitle";
import { BarWipe } from "./components/BarWipe";
import { SidePanel } from "./components/SidePanel";
import { Tarjeta, type TarjetaProps } from "./components/Tarjeta";
import { Cortinilla, type CortinillaProps } from "./components/Cortinilla";
import { Contraste, type ContrasteProps } from "./components/Contraste";
import { CtaCard } from "./components/CtaCard";
import { MotionSound } from "./components/MotionSound";
import { Capas, PunchIn, type Capa } from "./components/Capas";
import { FPS } from "./brand/tokens";
import spec from "./reels.json";

/**
 * Un reel completo: vídeo montado + subtítulos + rótulo de gancho + CTA.
 *
 * El vídeo ya viene cortado y con los encuadres aplicados (`plan-reel.mjs` →
 * `punch-ins.py` → `render-hook.mjs`). Aquí sólo va lo que se superpone, y las
 * tres capas son portantes:
 *
 * - **Subtítulos**: el playbook exige que el argumento funcione sin audio. Se
 *   callan mientras el rótulo cruza: comparten franja —el rótulo vive entre el
 *   44 y el 63% de altura y el subtítulo empieza en el 55%— y en render salían
 *   uno encima de otro, ilegibles los dos. Además dirían lo mismo, porque el
 *   rótulo entra justo en la frase que subraya.
 * - **Rótulo**: entra por un lado **en la palabra que subraya** y sale por el
 *   otro. Antes se quedaba quieto desde el frame 0 diciendo lo que la voz diría
 *   cinco segundos después: para cuando llegaba la frase, el remate ya estaba
 *   gastado.
 * - **Tableros**: durante una explicación el tablero ES el plano; Jaime
 *   desaparece del cuadro y la voz sigue por debajo (un L-cut, así la costura no
 *   se oye).
 * - **CTA**: uno y sólo uno, y sólo en SELL. Los demás pilares llevan cero, así
 *   que el CTA vive en el spec y no en el componente: una pieza sin CTA
 *   simplemente no lo trae.
 */
export type ReelSpec = {
  id: string;
  video: string;
  /**
   * Las capas que decidio el camino de cada segmento. Ver `scripts/caminos.mjs`
   * y `components/Capas.tsx`: aqui solo se dibujan.
   */
  caminos: Capa[];
  duracion: number;
  lineas: string[];
  /** Frame en que ENTRA el rótulo: el de la palabra que subraya. */
  entra: number;
  /** Frames que se sostiene dentro del cuadro antes de salir. */
  sostiene: number;
  cta: {
    at: number;
    dur: number;
    promesa: string;
    fecha: string;
    duracion?: number;
    corrige?: { dice: string; es: string };
    /** Las dos cuentas enfrentadas. Ver `cuenta` en `CtaCard`. */
    cuenta?: { cuesta: string; vale: string; nota?: string };
    placa?: string;
    /** Opcional: no se declara porque sube pronto. Ver `CtaCard`. */
    precio?: string;
  } | null;
  captions: CaptionCue[];
  /**
   * Tableros: el plano de las explicaciones.
   *
   * Petición explícita de Jaime — «animaciones en las partes que se expliquen
   * cosas, así yo no me vea». Y resuelve lo otro que señaló, que los cambios de
   * escena se ven raros: un punch-in cada tres segundos desde una cámara fija es
   * un jump cut, y los jump cuts son visibles por diseño. Se tapan cortando a
   * otra cosa. Aquí esa otra cosa además explica.
   */
  boards: BoardCue[];
  /** Tramos en blanco y negro. Ver `Desatura` en `Ad`. */
  desatura: { at: number; duration: number }[];
  /**
   * Costuras tapadas con distorsión. Ver `Glitch` en `Ad`.
   *
   * Jaime: *«lo ideal del corte y del cambio de escena es que no se note»*. El
   * glitch no oculta el corte — lo **sustituye**: el ojo registra la
   * distorsión, no el salto de encuadre.
   */
  glitch: { at: number; duration: number }[];
  /**
   * Cortinillas: lo que media cada costura entre beats.
   *
   * Jaime, del segundo 33: *«el corte es demasiado duro, muy brusco; eso debe
   * estar mediado o por un gráfico o por algo que lo suavice»*. Ahí el montaje
   * salta 83 s de material y cambia de encuadre a la vez, sin nada que lo cubra.
   */
  cortinillas: { at: number; duration: number; props: CortinillaProps }[];
  /**
   * Frames donde cambia el encuadre.
   *
   * Ya **no** llevan barra: se probó en todos y quedó peor que el salto. La
   * barra queda reservada a la entrada de una tarjeta, que es cuando el
   * movimiento trae algo. Se conservan porque el rótulo los usa para decidir
   * dónde cede.
   */
  cortes: number[];
  /** Lado libre del cuadro, derivado de dónde está el sujeto. */
  lado: "izq" | "der";
  /**
   * Paneles que se construyen en el hueco del plano, **sin cortar**.
   *
   * Idea de Jaime: en vez de cortar, irse al plano más lejano y animar en el
   * espacio disponible. El cambio deja de verse porque no hay corte — cambia lo
   * que ocupa el cuadro.
   */
  paneles: { at: number; duration: number; bloques: { texto: string; fuerte?: boolean }[] }[];
  /**
   * Tarjetas: los beats del libreto que no tienen plano utilizable.
   *
   * *«A cada estructura le escogemos el mejor, y si no entra bien hacemos un
   * gráfico, así sea sólo palabras.»* Un beat no se cae por falta de toma: se
   * dibuja, con el audio bueno por debajo si lo hay.
   */
  tarjetas: { at: number; duration: number; props: TarjetaProps }[];
  /**
   * Las dos cifras de la comparacion, encima del plano. Ver `Contraste`.
   *
   * No roba el plano como un tablero: Jaime sigue en cuadro contando quien es
   * cada uno mientras los dos numeros se quedan arriba.
   */
  contraste?: { at: number; duration: number; props: ContrasteProps } | null;
};

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


export const Reel: React.FC<{ spec: ReelSpec }> = ({ spec: r }) => {
  /**
   * El subtítulo NO se calla nunca. **La mayoría ve los reels sin audio**, así
   * que un hueco sin texto es un hueco sin argumento.
   *
   * Convivían mal con el rótulo porque compartían franja; se resolvió bajando
   * la banda a la zona segura de Reels (420 px) en vez de silenciar una capa.
   *
   * La única excepción es el tablero: ahí el tablero **es** el plano y lleva su
   * propio texto, así que el subtítulo se solapaba con su pie legal. Durante un
   * tablero no hay subtítulo porque no hay nada que subtitular que el tablero no
   * esté diciendo ya.
   *
   * Y **lo mismo vale para las tarjetas**, que llevan su texto igual. Faltaba
   * aquí: el subtítulo seguía corriendo por debajo de una tarjeta que ocupa el
   * cuadro entero, con dos textos distintos a la vez.
   */
  /**
   * **Qué calla el subtítulo, y qué no.**
   *
   * - **Tarjeta y cortinilla: callan.** Ocupan el cuadro entero con su propio
   *   texto, así que debajo no queda sitio ni hay nada que añadir.
   * - **Tablero: NO calla.** Jaime: *«en los tableros también hay cc»*. Ahí la
   *   voz sigue por debajo diciendo cosas que el tablero no enseña —es un
   *   L-cut— y el argumento tiene que funcionar sin sonido. El tablero deja
   *   libre la banda de subtítulos por diseño.
   * - **Panel: TAMPOCO calla.** Estuvo callando y costó 20 de los 36
   *   subtítulos del reel 1 — 43,6 s de una pieza de 75,2 s sin una palabra en
   *   pantalla. El panel vive en la mitad superior por un lado; la banda de
   *   subtítulos, en el 50–60%. **No compiten por el sitio.** Lo que Jaime
   *   pidió en su día —*«cada letrero se debe ver»*— se resolvió dándole a
   *   cada bloque su tiempo de lectura, no borrando la capa portante. Lo que
   *   sí cede el subtítulo mientras el panel escribe es el **volumen**: ahí no
   *   se compone (ver `componer()` en `reels-spec.mjs`).
   *
   * Y calla **por mayoría, no por roce**: una cue que solapa 0,2 s con el final
   * de un panel se perdía entera. Se calla si la tapan más de la mitad.
   */
  const tapan = [...r.tarjetas, ...r.cortinillas];
  const captions = r.captions.filter(
    (c) =>
      tapan.reduce(
        (n, b) =>
          n +
          Math.max(
            0,
            Math.min(c.at + c.duration, b.at + b.duration) -
              Math.max(c.at, b.at),
          ),
        0,
      ) <=
      c.duration / 2,
  );
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
        mode="evidence"
        captions={captions}
        boards={r.boards}
        desatura={r.desatura}
        glitch={r.glitch}
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
    <Capas capas={r.caminos} kicker={r.lineas[0] ?? ""} />
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
