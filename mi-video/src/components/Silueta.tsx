import React from "react";
import { color } from "../brand/tokens";

/**
 * **Objetos reconocibles, dibujados con geometría plana.**
 *
 * Los encargos de `escena_desc.grafico` piden cosas concretas y nombradas: en
 * reel-02 e2, *«dos siluetas geométricas planas sobre la misma línea de salida:
 * a la izquierda la furgoneta del electricista, a la derecha una casa baja y un
 * casco de yate»*. Ninguna de las tres estaba en la biblioteca —`Pictograma`
 * sabe trazar diez figuras y son señales, no objetos— así que el encargo caía a
 * texto, que es de lo que Jaime se quejó cuatro veces.
 *
 * Su regla, del 6-9-2026: *«hazlas genéricas para todo el lote, pero recuerda
 * que es responsabilidad del diseñador ampliar y construir la biblioteca para
 * cada video»*. Esto es esa biblioteca, y **está hecha para crecer**: cada
 * entrada de `SILUETAS` es una lista de rectángulos y triángulos en una caja de
 * 100×100, así que añadir un objeto nuevo es añadir una fila, no escribir un
 * componente.
 *
 * ## Por qué el ejemplo tiene que ser concreto
 *
 * Jaime: *«la idea clara es que el diseñador pueda entender el sentido e
 * ilustrarlo con ejemplos entendibles»*. Una furgoneta frente a un yate dice
 * «dos que facturan lo mismo y viven distinto» sin una sola palabra; dos cajas
 * abstractas no dicen nada. La prueba, aplicable sobre un fotograma: **si se
 * tapa el texto, la figura tiene que seguir diciendo de qué va el tramo.**
 *
 * ## Cómo está dibujada, y por qué así
 *
 * Rectángulos y triángulos a escuadra, relleno plano, sin trazo interior, sin
 * sombra y sin volumen. Es el canon —*«un pictograma geométrico sí entra:
 * círculo, rectángulo, triángulo y línea en plano de color»*— y es también lo
 * que Jaime pidió al pasar la referencia de Veritasium: vector plano, y
 * traducido a nuestros tokens, no importado con sus colores.
 *
 * ## Un nombre que no existe NO dibuja otra cosa
 *
 * Lanza. `Pictograma` tenía un `switch` con `default` y una flecha, así que un
 * nombre mal escrito **dibujaba una flecha** y la pieza afirmaba en pantalla
 * algo que nadie compuso (C-168). Antes que una figura inventada, un fallo.
 */
/**
 * Un objeto del catálogo: su contorno en un `viewBox` de 100×100, ya cerrado.
 *
 * **Esto eran rectángulos apilados y no valía.** Jaime, viéndolos: *«las
 * imágenes muy feas… el carro, la casa y el bote no… les falta mucha
 * suavidad»*. Y tenía razón de raíz: con cajas apiladas no hay contorno posible
 * —el perfil sale escalonado— así que ninguna cantidad de ajuste iba a
 * arreglarlo. Un objeto se dibuja con su trazado o no se dibuja.
 *
 * Suavidad NO es redondez amable, que el canon prohíbe: es que el perfil esté
 * resuelto —un guardabarros que acompaña a la rueda, la caída de un casco, el
 * alero de un tejado— y que la silueta se reconozca de un vistazo.
 */
type Objeto = {
  /** Trazados del contorno, en coordenadas de 0 a 100. */
  d: string[];
  /** Trazados que van en el tono de acento, encima. */
  foco?: string[];
};

/**
 * El catálogo. **Aquí se añade**, y una entrada nueva sirve a las 16-50 piezas.
 *
 * Todos apoyan en y≈88 para que varios compartan línea de suelo sin cuadrarlos
 * a mano, y todos caben en 100×100.
 */
export const SILUETAS: Record<string, Objeto> = {
  /** Furgoneta de oficio, de perfil: caja, morro rebajado y dos ruedas. */
  furgoneta: {
    d: [
      "M4 34 Q4 28 10 28 L54 28 Q60 28 63 33 L76 52 Q78 55 82 56 L90 58"
      + " Q95 60 95 66 L95 74 Q95 78 90 78 L84 78 A10 10 0 0 0 64 78"
      + " L40 78 A10 10 0 0 0 20 78 L9 78 Q4 78 4 73 Z",
      "M66 40 L74 52 L58 52 L58 40 Z",
    ],
    foco: [
      "M74 78 A10 10 0 1 1 74 77.9 Z",
      "M30 78 A10 10 0 1 1 30 77.9 Z",
    ],
  },
  /** Casa baja: cuerpo, tejado a dos aguas con alero y chimenea. */
  casa: {
    d: [
      "M50 14 L94 50 L86 50 L86 86 Q86 88 84 88 L16 88 Q14 88 14 86 L14 50"
      + " L6 50 Z",
      "M68 22 L76 22 L76 36 L68 30 Z",
    ],
  },
  /** Yate de motor, de perfil: casco con caída, caseta rebajada y antena. */
  yate: {
    d: [
      "M5 60 Q5 58 8 58 L92 58 Q97 58 95 63 L88 80 Q85 88 76 88 L20 88"
      + " Q12 88 9 80 Z",
      "M26 40 Q26 38 29 38 L58 38 Q62 38 64 42 L70 58 L26 58 Z",
      "M72 22 L75 22 L75 58 L72 58 Z",
    ],
  },
  /** Edificio: torre con basamento y remate. */
  edificio: {
    d: [
      "M26 16 Q26 12 30 12 L70 12 Q74 12 74 16 L74 82 L26 82 Z",
      "M14 82 L86 82 Q88 82 88 84 L88 88 L12 88 L12 84 Q12 82 14 82 Z",
    ],
  },
  /** Pila de billetes: tres capas con el canto acusado. */
  fajo: {
    d: [
      "M12 70 Q12 68 14 68 L86 68 Q88 68 88 70 L88 80 Q88 82 86 82 L14 82"
      + " Q12 82 12 80 Z",
      "M14 52 Q14 50 16 50 L84 50 Q86 50 86 52 L86 62 Q86 64 84 64 L16 64"
      + " Q14 64 14 62 Z",
      "M16 34 Q16 32 18 32 L82 32 Q84 32 84 34 L84 44 Q84 46 82 46 L18 46"
      + " Q16 46 16 44 Z",
    ],
  },
  /** Puerta abierta: marco y hoja abatida en fuga. */
  puerta: {
    d: [
      "M20 10 L34 10 L34 88 L20 88 Z",
      "M66 10 L80 10 L80 88 L66 88 Z",
    ],
    foco: ["M36 16 L64 10 L64 88 L36 82 Z"],
  },
};

export const Silueta: React.FC<{
  /** Nombre del catálogo. Uno que no esté lanza, no dibuja otra cosa. */
  nombre: keyof typeof SILUETAS | string;
  /** Lado de la caja en px. La figura es cuadrada y apoya en su base. */
  lado: number;
  /** La que importa: va en oro. Sólo una por tablero. */
  foco?: boolean;
  /** 0 a 1. Lo pone quien la hospeda con su propio horario. */
  entra?: number;
}> = ({ nombre, lado, foco = false, entra = 1 }) => {
  const obj = SILUETAS[nombre];
  if (!obj) {
    throw new Error(
      `Silueta: «${nombre}» no está en el catálogo. Añádela a SILUETAS —su` +
        " contorno en un viewBox de 100×100— en vez de usar la más parecida:" +
        " una figura que nadie compuso afirma en pantalla lo que no se dijo.",
    );
  }
  const tinta = foco ? color.gold : color.secondaryBlue;
  return (
    <svg
      viewBox="0 0 100 100"
      width={lado}
      height={lado}
      style={{
        display: "block",
        // Se descubre de abajo arriba, sin rebote: la regla de lote vale para
        // todo lo que entra en pantalla, no sólo para las letras.
        clipPath: `inset(${(1 - Math.min(1, Math.max(0, entra))) * 100}% 0 0 0)`,
      }}
    >
      {obj.d.map((d) => (
        <path key={d.slice(0, 24)} d={d} fill={tinta} />
      ))}
      {(obj.foco ?? []).map((d) => (
        <path
          key={d.slice(0, 24)}
          d={d}
          // Los detalles —la rueda, la hoja de la puerta— van SIEMPRE en el
          // negro del fondo y no en navy: sobre la banda navy desaparecían y
          // la furgoneta se quedaba con dos arcos en vez de dos ruedas.
          fill={color.richBlack}
        />
      ))}
    </svg>
  );
};
