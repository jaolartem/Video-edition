import React from "react";
import { useCurrentFrame } from "remotion";
import { ThreeCanvas } from "@remotion/three";
import { color, layout } from "../brand/tokens";
import registro from "../brand/volumenes.json";
import { Compuerta3D, Desvio3D, Fuga3D } from "./volumen/escenas";
import { Brecha3D, Contencion3D, Foco3D, Franja3D, Umbral3D }
  from "./volumen/masas";
import { Relevo3D, Tajo3D } from "./volumen/partido";

/**
 * **La animación del panel, con volumen y con luz.** Sustituye a los palitos.
 *
 * Instrucción de lote de Jaime (5-9-2026): *«para los paneles, las animaciones
 * de bolitas y palitos y ultra sencillas se acaban, quitan más de lo que dan;
 * ahora sólo animaciones complejas que muestren luz o movimiento, ojalá con
 * animación 3D, y que estén en consonancia con la idea del tablero o del
 * panel»*. Y el porqué, que no es de gusto: *«quitan más de lo que dan»* — una
 * animación que no aporta más de lo que cobra en pantalla y en atención, sobra.
 *
 * ## Qué es un volumen y qué NO es
 *
 * No es un efecto de catálogo que se le pone a un panel para que se mueva. Cada
 * uno **afirma una cosa** —está escrito así en
 * [`volumenes.json`](../brand/volumenes.json), «qué afirma», no «qué dibuja»— y
 * se elige por lo que la etapa tiene que dejar entendido. Un volumen que ilustra
 * otra cosa es peor que ninguno.
 *
 * ## Por qué el canon no se rompe por venir de 3D
 *
 * Las masas son losas planas, el material es mate —`roughness: 1`,
 * `metalness: 0`, sin brillo especular— y no hay esquina redondeada, degradado
 * ni sombra difusa. Lo que el 3D añade es lo que el plano no tiene: profundidad
 * y **luz con dirección**, que es lo que deja ver que algo atraviesa algo. Es
 * constructivismo con eje Z, no render de agencia.
 *
 * Y es determinista: todo sale de `useCurrentFrame()`, así que dos renders del
 * mismo frame salen idénticos.
 * @clase capa
 */
export type Volumen = keyof typeof registro.volumenes;

/**
 * **Qué dibuja cada nombre**, y es un mapa y no una cadena de ternarios.
 *
 * Con tres escenas los ternarios daban igual; con ocho, un nombre registrado en
 * `volumenes.json` y sin escena **salía como panel mudo** —el fallo invisible
 * que la puerta de paneles existe para evitar— porque ninguna rama lo cogía y
 * nadie se quejaba. Escrito como `Record<Volumen, …>`, `tsc` no compila hasta
 * que la escena existe: registrar y construir dejan de poder separarse.
 */
const ESCENA: Record<Volumen, React.FC<{ frame: number }>> = {
  compuerta: Compuerta3D,
  desvio: Desvio3D,
  fuga: Fuga3D,
  brecha: Brecha3D,
  franja: Franja3D,
  contencion: Contencion3D,
  umbral: Umbral3D,
  foco: Foco3D,
  tajo: Tajo3D,
  relevo: Relevo3D,
};

/**
 * **El sitio: una columna en el lado libre, no una caja delante de la cara.**
 *
 * La primera versión ocupaba el 52% del ancho centrado en el lado libre y
 * **caía encima de la cara** — el pórtico cruzaba las gafas en la etapa 2 y el
 * desvío la boca en la etapa 5. Es la misma regla que ya costó una vuelta con
 * los bloques del panel: *«misma facturación tapa la mitad de la cara»*. La cara
 * es el argumento, y una capa que la tapa no compone: sustituye.
 *
 * **Y el hueco se MIDE, no se supone.** Esto decía «medido sobre el encuadre del
 * lote — sujeto descentrado», y ese descentrado salía de una sola cuenta hecha
 * sobre la primera escena de la pieza: el centro del recorte. La cámara está
 * fija y el encuadre sólo se acerca, así que ese número daba prácticamente el
 * mismo lado para las siete y para todas sus escenas — una constante disfrazada
 * de medida, que es el fallo que ya costó `sujeto.py` en el otro eje.
 *
 * Lo que hay de verdad, medido con `scripts/dominio/hueco.py` en esta misma
 * banda de altura y escena por escena: el hueco de ese lado va de **0,00 a 0,53**
 * del ancho, y esta caja pide 0,30. O sea que **doce de los trece volúmenes se
 * dibujaban encima de él** —el de reel-05 e7 le cruzaba las gafas— porque nadie
 * medía. Ahora el lado y el ancho visible llegan medidos desde el spec.
 *
 * Lo que no cabe **sangra por el borde**, que es lo que el canon ya hace con su
 * recorte: *«entero dentro del cuadro sería pegatina»*. Así el volumen conserva
 * su escala y su diagonal, y lo único que cambia es cuánto se ve. Por debajo de
 * `caja.minimo` no sangra: es que no cabe, y eso lo dice
 * `scripts/reels/paneles.mjs` en vez de dibujarse sobre su cara.
 *
 * Abajo se para en el techo de la franja: ningún elemento baja de ahí.
 */
const CAJA = registro.caja;
const ANCHO = Math.round(layout.width * CAJA.ancho);
const ALTO = Math.round(layout.height * CAJA.alto);

/** Se aparta del borde: la interfaz de la plataforma muerde los laterales. */
const MARGEN = Math.round(layout.width * CAJA.margen);

/**
 * Unidades de mundo por píxel del lienzo. A 10,5 de distancia el semiancho
 * visible es 1,92 para los 162 px de medio lienzo: 3,84 / `ANCHO`.
 */
const MUNDO_POR_PX = 3.84 / ANCHO;

export const Volumen: React.FC<{
  nombre: Volumen;
  /** Lado libre del cuadro. Sale del hueco medido, no del recorte de la toma. */
  lado: "izq" | "der";
  /**
   * Cuánto ancho deja libre su cuerpo de ese lado, en fracción del cuadro. Lo
   * mide `hueco.py` sobre la escena en la que cae el panel. Sin él se supone
   * que cabe entero, que es lo que se hacía y salía sobre su cara.
   */
  hueco?: number;
}> = ({ nombre, lado, hueco = CAJA.ancho + CAJA.margen }) => {
  const frame = useCurrentFrame();
  const Escena = ESCENA[nombre];
  // Lo que se ve del volumen: el hueco menos el margen del borde, y nunca más
  // que la caja entera. Lo que sobra sale del cuadro por fuera.
  const visible = Math.min(
    ANCHO,
    Math.max(0, Math.round(hueco * layout.width) - MARGEN),
  );
  const fuera = ANCHO - visible;
  return (
    <div
      style={{
        position: "absolute",
        top: Math.round(layout.height * CAJA.arriba),
        left: lado === "der" ? undefined : MARGEN - fuera,
        right: lado === "der" ? MARGEN - fuera : undefined,
        width: ANCHO,
        height: ALTO,
      }}
    >
      <ThreeCanvas
        width={ANCHO}
        height={ALTO}
        style={{ background: "transparent" }}
        gl={{ alpha: true, antialias: true }}
        // La distancia sale de medirla contra el lienzo: es una columna
        // estrecha —324 px— y a menos de esto el pórtico, que mide 3,1 unidades,
        // se sale por los lados. A 10,5 el semiancho visible es 1,92.
        camera={{ position: [0, 1.1, 10.5], fov: 36 }}
      >
        {/* Luz con dirección: una clave dura que talla el canto de las losas y
            un relleno bajo para que la cara oscura no se cierre del todo. Nada
            de luz ambiental alta, que es lo que aplana el volumen y deja el
            render con pinta de ilustración. */}
        <ambientLight intensity={0.32} />
        <directionalLight position={[3.4, 5.2, 4]} intensity={2.1} />
        <directionalLight position={[-4, 1.2, -2]} intensity={0.5} />
        {/* Y el oro también ilumina: es la única fuente de color de la escena,
            igual que en el canon es el único tono vivo de la paleta. */}
        <pointLight position={[0, 0.6, 0.4]} intensity={16} distance={7}
          color={color.gold} />
        {/**
         * **Y la escena se corre a lo que se ve, que es la otra mitad de
         * sangrar.**
         *
         * Sin esto la caja sale del cuadro llevándose dentro lo que había que
         * mirar: en reel-02 e1 la mitad de oro del tajo caía en los 204 px que
         * quedan fuera y el volumen se veía **vacío**, que es peor que no
         * ponerlo. Sangrar no es recortar por un lado: es enseñar la parte que
         * cuenta y dejar fuera el aire.
         *
         * La cuenta es directa: el semiancho visible del lienzo es 1,92 en
         * mundo para 162 px, o sea 0,01185 por píxel, y la escena se corre
         * medio `fuera` hacia el lado que sí se ve.
         *
         * La rotación es la diagonal del canon: nada de frente, y el mismo
         * ángulo siempre — girar al azar es ruido, no composición.
         */}
        <group
          position={[(lado === "der" ? -1 : 1) * (fuera / 2) * MUNDO_POR_PX, 0, 0]}
          rotation={[0.24, lado === "der" ? -0.42 : 0.42, 0]}
        >
          <Escena frame={frame} />
        </group>
      </ThreeCanvas>
    </div>
  );
};

/** Los nombres que existen de verdad. Lo lee la puerta, no una lista aparte. */
export const VOLUMENES = Object.keys(registro.volumenes) as Volumen[];
