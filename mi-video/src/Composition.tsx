import { Composition } from "remotion";
import { CausalChain, type CausalChainProps } from "./components/CausalChain";
import { TwoPaths, type TwoPathsProps } from "./components/TwoPaths";
import { Cover, type CoverProps } from "./components/Cover";
import { CtaCard } from "./components/CtaCard";
import { BigTitle } from "./components/BigTitle";
import { GANCHOS, Gancho } from "./Ganchos";
import { REELS, Reel } from "./Reel";
import { Tarjeta } from "./components/Tarjeta";
import { Acumulacion } from "./components/Acumulacion";
import { Comparacion } from "./components/Comparacion";
import { FPS, layout } from "./brand/tokens";

/**
 * Contenido ilustrativo del territorio "resistencia a incorporar".
 *
 * Frases cortas y memorables: **el tablero no transcribe lo que se dice**. La
 * voz de Jaime lleva la explicación y los subtítulos cubren lo hablado para
 * quien mira sin sonido. Lo que va en pantalla es el ancla, no el guion.
 *
 * Sin cifras: el playbook prohíbe inventar datos, y un placeholder con pinta de
 * dato real es el error que se cuela en producción. Cuando haya cifras
 * verificadas se añaden con su `source` — el tipo no deja ponerlas sin fuente.
 */

const causalChain: CausalChainProps = {
  title: "Por qué tu capital no tiene salida",
  nodes: [
    { stage: "Contexto institucional", text: "Nadie te explicó las reglas." },
    { stage: "Creencia adaptativa", text: "Confiar en los tuyos te protegió." },
    {
      stage: "Manifestación financiera",
      text: "Tu negocio y tú son la misma cuenta.",
    },
    { stage: "Consecuencia", text: "Tu capital no tiene salida." },
  ],
  caption:
    "…y entonces el capital que tanto te costó levantar se queda sin ninguna salida.",
  limitation:
    "Incorporar no baja impuestos por sí solo. Depende del beneficio, la provincia, el riesgo y la caja. Consúltalo con el profesional que corresponda.",
};

const twoPaths: TwoPathsProps = {
  title: "Dos negocios idénticos",
  start: "Mismo beneficio. Misma provincia. Mismo riesgo.",
  horizon: "10 años",
  byDefault: {
    label: "Por defecto",
    steps: [
      "Todo sale a tu cuenta personal.",
      "El negocio y tú son lo mismo.",
      "Nadie revisa la estructura.",
    ],
    outcome: "Capital sin destino.",
  },
  deliberate: {
    label: "Deliberado",
    steps: [
      "La mesa correcta revisa la estructura.",
      "El capital tiene destino.",
      "El riesgo queda separado.",
    ],
    outcome: "Capital con arquitectura.",
  },
  condition:
    "Cambia si el beneficio no sostiene el coste de la sociedad, si la provincia altera el trato o si necesitas la caja hoy. Consúltalo con el profesional que corresponda.",
};

/**
 * Cada modo se registra por separado. El sistema prohíbe mezclarlos dentro de
 * una pieza, así que tampoco existe una composición que los combine: cada ad
 * declara su modo y se queda en él.
 */
/**
 * Portadas de los seis reels. El gancho es la primera línea hablada, no un
 * título aparte: portada y voz deben decir lo mismo o se nota el cambiazo.
 */
const COVERS: { id: string; props: CoverProps }[] = [
  { id: "1", props: { hook: "Vende más y le queda menos.", kicker: "El código del empresario" } },
  { id: "2", props: { hook: "Mismo sueldo, distinta tajada.", kicker: "El código del empresario", tone: "raised" } },
  { id: "3", props: { hook: "Su contador no es su estratega.", kicker: "El código del empresario" } },
  { id: "4", props: { hook: "El banco no le presta.", kicker: "El código del empresario", tone: "raised" } },
  { id: "5", props: { hook: "Su mejor trimestre le costó más.", kicker: "El código del empresario" } },
  { id: "6", props: { hook: "Una pérdida sin fecha.", kicker: "El código del empresario", accent: "blue" } },
];

/**
 * Los rótulos van anclados a la palabra que subrayan, no a tiempos redondos:
 * «no le queda lo que debería» entra cuando lo dice, y el remate «Eso no es
 * mala suerte» cuando lo remata.
 */
/**
 * Rotulo de gran formato POR DELANTE, en la franja del torso.
 *
 * Se probo detras de la figura con segmentacion y funcionaba tecnicamente, pero
 * el sujeto tapaba la mayor parte del texto — el efecto se lucia y el mensaje
 * se perdia. Por delante y por debajo de la cara se lee entero sin estorbar.
 */
export const MyComposition = () => {
  return (
    <>
      {COVERS.map((c) => (
        <Composition
          key={c.id}
          id={`Portada-Reel-${c.id}`}
          component={Cover}
          durationInFrames={90}
          fps={FPS}
          width={layout.width}
          height={layout.height}
          defaultProps={c.props}
        />
      ))}
      {/**
       * Los seis ganchos, cada uno con su rótulo. Se generan del mismo spec
       * para que ninguno se quede sin — la regla es que todo gancho lo lleva.
       */}
      {/**
       * Los seis reels completos: montaje + subtítulos + rótulo + CTA.
       * La duración sale del spec generado, no de un número escrito a mano.
       */}
      {REELS.map((r) => (
        <Composition
          key={r.id}
          id={r.id}
          component={Reel}
          durationInFrames={Math.round(r.duracion * FPS)}
          fps={FPS}
          width={layout.width}
          height={layout.height}
          defaultProps={{ spec: r }}
        />
      ))}
      {GANCHOS.map((g) => (
        <Composition
          key={g.id}
          id={g.id}
          component={Gancho}
          durationInFrames={Math.round(g.duracion * FPS)}
          fps={FPS}
          width={layout.width}
          height={layout.height}
          defaultProps={{ spec: g }}
        />
      ))}
      {/** Prueba de la tarjeta: el plano cuando la toma no sirve. */}
      <Composition
        id="Tarjeta"
        component={Tarjeta}
        durationInFrames={150}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{
          framework: "Causal Reveal",
          beat: [5, 8] as [number, number],
          bloques: [
            { texto: "No más ventas" },
            { texto: "No otro empleado" },
            { texto: "No más horas" },
          ],
          remate: ["Necesita", "el mapa", "del dinero."],
          pie: "De la plata que ya está generando.",
        }}
      />
      {/**
       * El tablero que dibuja lo que se dice: la plata quieta que cruza el
       * umbral. Es el beat obligatorio del R5, que no tiene toma utilizable.
       */}
      <Composition
        id="Acumulacion"
        component={Acumulacion}
        durationInFrames={240}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{
          title: "La plata que se quedó quieta",
          concepto: "Ingreso pasivo",
          horizonte: "Un año fiscal",
          tramos: [
            { etiqueta: "Trimestre normal", alto: 0.3 },
            { etiqueta: "Se queda dentro", alto: 0.28 },
            { etiqueta: "Cruza el umbral", alto: 0.3 },
          ],
          umbral: { etiqueta: "Umbral", en: 0.6 },
          resultado: {
            figure: "$14,300 de más",
            source: "Caso relatado por Jaime Olarte",
          },
          condicion:
            "El umbral depende del ingreso pasivo acumulado y de la provincia. Confírmelo con su contador antes de decidir nada.",
        }}
      />
      {/** El tablero de dos columnas: la evidencia que carga el argumento. */}
      <Composition
        id="Comparacion"
        component={Comparacion}
        durationInFrames={240}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{
          placa: "r2-acceso",
          premisa: "Búsquelo en Google",
          izquierda: {
            titulo: "En inglés",
            cifra: "Seminarios",
            pie: "El CRA los publica y los explica.",
          },
          derecha: {
            titulo: "En español",
            cifra: "Uno",
            pie: "Y no está en ninguna plataforma.",
          },
          remate: "La brecha no es de esfuerzo",
          fuente: "Búsqueda pública · CRA, seminarios sobre el T2",
          condicion:
            "Lo que hay disponible cambia con el tiempo. Compruébelo usted mismo antes de darlo por cierto.",
        }}
      />
      <Composition
        id="BigTitle"
        component={BigTitle}
        durationInFrames={1}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{ lineas: ["No es", "mala", "suerte"] }}
      />
      <Composition
        id="CtaCard"
        component={CtaCard}
        durationInFrames={120}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{
          kicker: "Bootcamp en vivo",
          promesa: "Sepa qué preguntarle a su contador.",
          fecha: "21 de septiembre",
          precio: "$20",
          accion: "Link abajo",
        }}
      />
      <Composition
        id="CausalChain-Evidence"
        component={CausalChain}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={
          { ...causalChain, mode: "evidence" } satisfies CausalChainProps
        }
      />
      <Composition
        id="CausalChain-Guide"
        component={CausalChain}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={
          { ...causalChain, mode: "guide" } satisfies CausalChainProps
        }
      />
      {/**
       * Variantes de superficie y acento. El tablero NO siempre es el mismo:
       * el modo decide quién habla, el tono y el acento dan variedad entre
       * piezas sin salirse de la paleta. Están para comparar y elegir.
       */}
      <Composition
        id="Variante-Navy"
        component={CausalChain}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={
          {
            ...causalChain,
            mode: "evidence",
            tone: "raised",
            gap: "loose",
            nodes: causalChain.nodes.map((n, i) =>
              i === 2 ? { ...n, emphasis: true } : n,
            ),
          } satisfies CausalChainProps
        }
      />
      <Composition
        id="Variante-Gris-AzulSecundario"
        component={CausalChain}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={
          {
            ...causalChain,
            mode: "evidence",
            tone: "high",
            accent: "blue",
            gap: "loose",
          } satisfies CausalChainProps
        }
      />
      <Composition
        id="TwoPaths-Evidence"
        component={TwoPaths}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{ ...twoPaths, mode: "evidence" } satisfies TwoPathsProps}
      />
      <Composition
        id="TwoPaths-Guide"
        component={TwoPaths}
        durationInFrames={660}
        fps={FPS}
        width={layout.width}
        height={layout.height}
        defaultProps={{ ...twoPaths, mode: "guide" } satisfies TwoPathsProps}
      />
    </>
  );
};
