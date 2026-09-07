import "./index.css";
import React from "react";
import {
  AbsoluteFill, Composition, Img, registerRoot, staticFile,
} from "remotion";
import { assertShort } from "./brand/copy";
import { fontFamily } from "./brand/fonts";
import { useEntrada } from "./brand/horario";
import { color } from "./brand/tokens";
import { PanelDentro, type PanelDentroProps } from "./components/PanelDentro";
import { Reparto } from "./components/Reparto";


/**
 * El panel de reel-02 e1, con todo lo que Jaime fijó el 6-9-2026 puesto:
 * su plano DESATURADO y el color sólo en la geometría; una banda plana como
 * estructura ocupando la franja libre de arriba; y la figura haciendo la idea
 * en vez de tres bloques de texto diciéndola.
 */
const PanelE1: React.FC = () => {
  const entra = useEntrada();
  const banda = entra(0, 16);
  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      <Img
        src={staticFile("prueba-plano.jpg")}
        style={{ width: "100%", height: "100%", objectFit: "cover",
                 filter: "grayscale(1) contrast(1.08) brightness(0.82)" }}
      />
      {/* El disco plano detrás de su cabeza: separa sin tapar. */}
      <div style={{
        position: "absolute", left: 250, top: 250, width: 620, height: 620,
        borderRadius: "50%", backgroundColor: color.navy, opacity: 0.92 * banda,
      }} />
      <Img
        src={staticFile("prueba-plano.jpg")}
        style={{ width: "100%", height: "100%", objectFit: "cover",
                 position: "absolute", inset: 0,
                 filter: "grayscale(1) contrast(1.08) brightness(0.82)",
                 // La banda pasa por DETRÁS y él queda delante: el segundo
                 // pase se recorta a su silueta. Aquí, para la prueba, con un
                 // degradado de máscara; en la pieza, con la máscara real de
                 // `text-behind.py`.
                 WebkitMaskImage:
                   "radial-gradient(ellipse 40% 34% at 50% 30%, #000 62%, transparent 66%)",
      }} />
      {/* La banda de estructura, a sangre por los dos lados. */}
      <div style={{
        position: "absolute", left: -60, top: 52, width: 1200, height: 348,
        backgroundColor: color.richBlack, opacity: 0.94,
        transform: `translateY(${(1 - banda) * -40}px)`,
      }} />
      <div style={{
        position: "absolute", left: -60, top: 392, width: 1200 * banda, height: 5,
        backgroundColor: color.gold,
      }} />
      <div style={{ position: "absolute", left: 90, top: 150 }}>
        <Reparto
          total={100}
          porciones={[
            { valor: 54, rotulo: "SE VA" },
            { valor: 46, rotulo: "LE QUEDA", foco: true },
          ]}
          ancho={900}
          signo="$"
          desde={8}
          source="CRA · IMPUESTO DE SOCIEDADES 2026 · ONTARIO"
        />
      </div>
      <div style={{
        position: "absolute", left: 90, top: 78,
        fontFamily: fontFamily.bloque, fontSize: 46, letterSpacing: "0.02em",
        textTransform: "uppercase", color: color.lightNeutral, opacity: banda,
      }}>
        {assertShort("DE CADA $100 QUE FACTURA", "label", "panel.premisa")}
      </div>
    </AbsoluteFill>
  );
};

/**
 * El tablero de reel-02 e2, a pantalla («plano: fuera»). Dos siluetas sobre la
 * misma línea de salida — es el encargo literal de `escena_desc`— y el oro
 * marcando de qué lado está lo que hay que mirar.
 */
/** El bloque negro que sostiene un texto. El negro ya no es el fondo. */
const Bloque: React.FC<{
  left: number; top: number; ancho: number; alto: number; abre: number;
  children: React.ReactNode;
}> = ({ left, top, ancho, alto, abre, children }) => (
  <div style={{ position: "absolute", left, top, width: ancho, height: alto }}>
    <div style={{
      position: "absolute", inset: 0, backgroundColor: color.richBlack,
      transformOrigin: "left", transform: `scaleX(${abre})`,
    }} />
    <div style={{ position: "absolute", left: 34, top: 26, opacity: abre }}>
      {children}
    </div>
  </div>
);

const TableroE2: React.FC = () => {
  const entra = useEntrada();
  const eje = entra(4, 14);
  return (
    <AbsoluteFill style={{ backgroundColor: color.navy }}>
      {/* **La placa que ya existe.** `c3-routes-vertical` es la que declara este
          tablero en `src/reels.json`, y es el collage que Jaime venía pidiendo
          con las referencias: papel rasgado, tramas de puntos, siluetas
          recortadas y tres tintas. No había que inventarlo. */}
      <Img
        src={staticFile("fondos/c3-routes-vertical.png")}
        style={{ position: "absolute", inset: 0, width: "100%", height: "100%",
                 objectFit: "cover", opacity: entra(0, 20) }}
      />
      {/* La masa plana bajo su figura: lo separa del collage sin taparlo. Es el
          disco detrás de la cabeza de la referencia, hecho columna porque el
          formato es vertical. */}
      <div style={{
        position: "absolute", left: -40, top: 400, width: 620, height: 1180,
        backgroundColor: color.richBlack, opacity: 0.9 * entra(2, 16),
        transform: `rotate(-4deg)`,
      }} />
      <Bloque left={0} top={214} ancho={800} alto={176} abre={entra(0, 14)}>
        <div style={{
          fontFamily: fontFamily.bloque, fontSize: 58, lineHeight: 1.06,
          letterSpacing: "0.01em", textTransform: "uppercase",
          color: color.lightNeutral,
        }}>
          MISMA FACTURACIÓN
          <div style={{ color: color.gold }}>$180,000 AL AÑO</div>
        </div>
      </Bloque>
      {/* Y lo que hay que LEER se apoya en negro, igual que los textos: sobre
          las flechas de la placa las cifras y sus rótulos no se leían. */}
      <div style={{
        position: "absolute", left: 470, top: 430, width: 660, height: 740,
        backgroundColor: color.richBlack, opacity: 0.93 * entra(4, 16),
        transform: "rotate(-3deg)",
      }} />
      {/* **El mecanismo, no los objetos.** Los dos reparten el MISMO $100: lo
          que cambia es dónde cae el tajo. Eso es lo que dice el tramo — «vende
          exactamente lo mismo y se queda con más»— y no se puede ver en una
          casa ni en un yate. */}
      <div style={{ position: "absolute", left: 528, top: 470, opacity: eje }}>
        <Reparto total={100} ancho={500} signo="$" desde={18}
          porciones={[{ valor: 54, rotulo: "SE VA" },
                      { valor: 46, rotulo: "LE QUEDA", foco: true }]}
          source="SIN ESTRUCTURA" />
      </div>
      <div style={{ position: "absolute", left: 528, top: 790, opacity: entra(30, 16) }}>
        <Reparto total={100} ancho={500} signo="$" desde={34}
          porciones={[{ valor: 33, rotulo: "SE VA" },
                      { valor: 67, rotulo: "LE QUEDA", foco: true }]}
          source="CON ESTRUCTURA" />
      </div>
      {/* **Él dentro del sistema, no encima de él.** Jaime: «ponerme a mí
          dentro del sistema… si el contorno desaparece y yo empiezo a funcionar
          como parte del collage, en ningún caso el fondo de las imágenes
          aparece». Va recortado y posterizado en tres tonos de la familia, así
          que deja de ser una foto pegada y pasa a ser material del tablero — y
          es uno de los dos términos de la comparación, no un adorno. */}
      <Img
        src={staticFile("recorte-plano.png")}
        style={{
          position: "absolute", left: -70, top: 268, width: 620,
          opacity: entra(12, 18),
        }}
      />
      
      <div style={{
        position: "absolute", left: 528, top: 1075, width: 500, textAlign: "center",
        fontFamily: fontFamily.bloque, fontSize: 30, letterSpacing: "0.06em",
        textTransform: "uppercase", color: color.gold, opacity: entra(36, 12),
      }}>
        {assertShort("21 MÁS POR CADA $100", "label", "tablero.der")}
      </div>
      <Bloque left={0} top={1300} ancho={900} alto={192} abre={entra(44, 14)}>
        <div style={{
          fontFamily: fontFamily.bloque, fontSize: 64, lineHeight: 1.04,
          textTransform: "uppercase", color: color.lightNeutral,
        }}>
          LA DIFERENCIA NO ESTÁ
          <div style={{ color: color.gold }}>EN LO QUE VENDE</div>
        </div>
      </Bloque>
      {/* La pregunta que se la devuelve al espectador. Va aparte y debajo: es
          otro movimiento —del dato a él— y por eso no comparte bloque. */}
      <Bloque left={0} top={1530} ancho={780} alto={116} abre={entra(58, 14)}>
        <div style={{
          fontFamily: fontFamily.bloque, fontSize: 52, letterSpacing: "0.01em",
          textTransform: "uppercase", color: color.gold,
        }}>
          ¿USTED TIENE ESTRUCTURA?
        </div>
      </Bloque>
      <Bloque left={0} top={1770} ancho={700} alto={72} abre={entra(52, 12)}>
        <div style={{
          fontFamily: fontFamily.data, fontSize: 20, letterSpacing: "0.08em",
          textTransform: "uppercase", color: color.secondaryBlue,
        }}>
          CRA · IMPUESTO DE SOCIEDADES 2026 · ONTARIO
        </div>
      </Bloque>
    </AbsoluteFill>
  );
};

/**
 * **Los tres lados de `PanelDentro`, para poder mirarlos.**
 *
 * Jaime se quedó con tres sitios —*«ahora yo puedo ir abajo o al otro lado»*—
 * y sólo `izquierda` había pasado por un fotograma: `derecha` y `abajo`
 * estaban escritos y **nadie los había visto**, que es lo mismo que no
 * existir. Con el mismo tablero de reel-02 e2 y su recorte de verdad, cambiar
 * `sujeto` es cambiar la composición entera —la columna de contenido se va al
 * lado libre— así que mirarlos cuesta un `remotion still` por lado.
 *
 * No es una lámina nueva: es el componente de la pieza con los props de la
 * pieza. Si aquí se ve mal, se ve mal en el render.
 */
const LADOS = ["izquierda", "derecha", "abajo"] as const;

const REPARTOS = [
  { etiqueta: "SIN ESTRUCTURA",
    porciones: [{ valor: 54, rotulo: "SE VA" },
                { valor: 46, rotulo: "LE QUEDA", foco: true }] },
  { etiqueta: "CON ESTRUCTURA",
    porciones: [{ valor: 33, rotulo: "SE VA" },
                { valor: 67, rotulo: "LE QUEDA", foco: true }] },
];

const panelE2 = (sujeto: (typeof LADOS)[number]): PanelDentroProps => ({
  placa: "c3-routes-vertical",
  sujeto,
  sujeto_src: "recorte/reel-02-e2.webm",
  premisa: "MISMA FACTURACIÓN",
  cifra: "$180,000 AL AÑO",
  // **`abajo` va con el panel ligero, y no por comodidad de la muestra**: el
  // propio componente lo exige, porque bajo el techo de la franja el hueco que
  // le queda entre el último reparto y el cierre no da para él. Mirarlo con
  // dos repartos era mirar un mechón de 26 px.
  repartos: sujeto === "abajo" ? REPARTOS.slice(1) : REPARTOS,
  remate: "21 MÁS POR CADA $100",
  pregunta: sujeto === "abajo" ? undefined : "¿USTED TIENE ESTRUCTURA?",
  fuente: "EY — Ontario: tasas personales combinadas 2025",
  condicion: "Marginal del tramo $177.883–$220.000 sobre dividendo elegible.",
});

export const Root: React.FC = () => (
  <>
    <Composition id="PanelE1" component={PanelE1} durationInFrames={120}
                 fps={30} width={1080} height={1920} />
    <Composition id="TableroE2" component={TableroE2} durationInFrames={120}
                 fps={30} width={1080} height={1920} />
    {LADOS.map((lado) => (
      <Composition key={lado} id={`PanelDentro-${lado}`} component={PanelDentro}
                   durationInFrames={240} fps={30} width={1080} height={1920}
                   defaultProps={panelE2(lado)} />
    ))}
  </>
);

registerRoot(Root);
