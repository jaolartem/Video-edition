import React from "react";
import { Composition } from "remotion";
import { CausalChain, type CausalChainProps } from "./components/CausalChain";
import { TwoPaths, type TwoPathsProps } from "./components/TwoPaths";
import { Cover } from "./components/Cover";
import { CtaCard } from "./components/CtaCard";
import { BigTitle } from "./components/BigTitle";
import { GANCHOS, Gancho } from "./Ganchos";
import { REELS, Reel } from "./Reel";
import { Tarjeta } from "./components/Tarjeta";
import { Acumulacion } from "./components/Acumulacion";
import { Comparacion } from "./components/Comparacion";
import { FPS, layout } from "./brand/tokens";
import { lienzoDe, type Lienzo } from "./brand/lienzo";
import { enSuLienzo } from "./brand/LienzoContexto";
import {
  COVERS,
  acumulacion,
  bigTitle,
  causalChain,
  comparacion,
  cta,
  tarjeta,
  twoPaths,
} from "./muestras";

/**
 * **El índice de lo que se puede renderizar**, y nada más.
 *
 * El contenido de cada vista vive en [`muestras`](./muestras.ts): son dos
 * trabajos distintos y estaban en el mismo fichero, así que retocar una frase
 * de ejemplo obligaba a abrir el registro entero.
 *
 * Cada modo se registra por separado. El sistema prohíbe mezclarlos dentro de
 * una pieza, así que tampoco existe una composición que los combine: cada ad
 * declara su modo y se queda en él.
 */

/**
 * Una composición del lote.
 *
 * Todas van a los mismos fps y salen de la misma plantilla, así que eso se
 * declara una vez y no catorce. Lo que cambia de una a otra es el nombre, qué
 * dibuja, cuánto dura, con qué props y **en qué lienzo**: el de la pieza, que
 * mide el cuadro y se pone en el contexto para quien dibuja dentro (C-670). Sin
 * lienzo, el vertical, que es lo que han sido siempre.
 */
const Pieza = <P extends Record<string, unknown>>({
  id,
  componente,
  dura,
  props,
  lienzo = layout,
}: {
  id: string;
  componente: React.FC<P>;
  /** Duración en frames. */
  dura: number;
  props: P;
  lienzo?: Lienzo;
}) => (
  <Composition
    id={id}
    component={enSuLienzo(componente, lienzo)}
    durationInFrames={dura}
    fps={FPS}
    width={lienzo.width}
    height={lienzo.height}
    defaultProps={props}
  />
);

/** Las cuatro vistas de la cadena causal: los dos modos y dos variantes. */
const CADENAS: { id: string; props: CausalChainProps }[] = [
  { id: "CausalChain-Evidence", props: { ...causalChain, mode: "evidence" } },
  { id: "CausalChain-Guide", props: { ...causalChain, mode: "guide" } },
  /**
   * Variantes de superficie y acento. El tablero NO siempre es el mismo: el
   * modo decide quién habla, el tono y el acento dan variedad entre piezas sin
   * salirse de la paleta. Están para comparar y elegir.
   */
  {
    id: "Variante-Navy",
    props: {
      ...causalChain,
      mode: "evidence",
      tone: "raised",
      gap: "loose",
      nodes: causalChain.nodes.map((n, i) =>
        i === 2 ? { ...n, emphasis: true } : n,
      ),
    },
  },
  {
    id: "Variante-Gris-AzulSecundario",
    props: {
      ...causalChain,
      mode: "evidence",
      tone: "high",
      accent: "blue",
      gap: "loose",
    },
  },
];

const BIFURCACIONES: { id: string; props: TwoPathsProps }[] = [
  { id: "TwoPaths-Evidence", props: { ...twoPaths, mode: "evidence" } },
  { id: "TwoPaths-Guide", props: { ...twoPaths, mode: "guide" } },
];

export const MyComposition = () => {
  return (
    <>
      {COVERS.map((c) => (
        <Pieza
          key={c.id}
          id={`Portada-Reel-${c.id}`}
          componente={Cover}
          dura={90}
          props={c.props}
        />
      ))}
      {/**
       * **La portada de cada pieza que la declara**, sobre su propio plano.
       *
       * Las de arriba son las muestras del sistema; éstas son las de verdad, y
       * salen del spec —o sea de `frames.json`— igual que todo lo demás. Un
       * fotograma con la fecha correcta y el texto centrado no es lo mismo que
       * una captura del vídeo: la captura trae el CC del segundo en que se
       * hizo. C-498.
       */}
      {REELS.filter((r) => r.portada).map((r) => (
        <Pieza
          key={`portada-${r.id}`}
          id={`Portada-${r.id}`}
          componente={Cover}
          dura={90}
          lienzo={lienzoDe(r.formato)}
          props={{
            hook: r.portada!.titulo,
            subtitulo: r.portada!.subtitulo,
            fotograma: r.portada!.fotograma,
            forma: (r.portada as {forma?: "velo" | "bloque"}).forma,
          }}
        />
      ))}
      {/**
       * Los seis reels completos: montaje + subtítulos + rótulo + CTA.
       * La duración sale del spec generado, no de un número escrito a mano.
       */}
      {REELS.map((r) => (
        <Pieza
          key={r.id}
          id={r.id}
          componente={Reel}
          dura={Math.round(r.duracion * FPS)}
          lienzo={lienzoDe(r.formato)}
          props={{ spec: r }}
        />
      ))}
      {/**
       * Los seis ganchos, cada uno con su rótulo. Se generan del mismo spec
       * para que ninguno se quede sin — la regla es que todo gancho lo lleva.
       */}
      {GANCHOS.map((g) => (
        <Pieza
          key={g.id}
          id={g.id}
          componente={Gancho}
          dura={Math.round(g.duracion * FPS)}
          props={{ spec: g }}
        />
      ))}
      <Pieza id="Tarjeta" componente={Tarjeta} dura={150} props={tarjeta} />
      <Pieza
        id="Acumulacion"
        componente={Acumulacion}
        dura={240}
        props={acumulacion}
      />
      <Pieza
        id="Comparacion"
        componente={Comparacion}
        dura={240}
        props={comparacion}
      />
      <Pieza id="BigTitle" componente={BigTitle} dura={1} props={bigTitle} />
      <Pieza id="CtaCard" componente={CtaCard} dura={120} props={cta} />
      {CADENAS.map((c) => (
        <Pieza
          key={c.id}
          id={c.id}
          componente={CausalChain}
          dura={660}
          props={c.props}
        />
      ))}
      {BIFURCACIONES.map((b) => (
        <Pieza
          key={b.id}
          id={b.id}
          componente={TwoPaths}
          dura={660}
          props={b.props}
        />
      ))}
    </>
  );
};
