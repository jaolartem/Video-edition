import React from "react";
import { color } from "../../brand/tokens";
import { Losa } from "./losa";

/**
 * Las escenas de [`Volumen`](../Volumen.tsx) en las que **algo se parte en dos y
 * sólo una de las dos partes se queda con el argumento**. En
 * [`escenas`](./escenas.tsx) algo circula y en [`masas`](./masas.tsx) algo se
 * acumula; aquí hay un corte, y después del corte no queda lo mismo que había.
 *
 * Las dos nacieron de un encargo que no cabía en las ocho que ya existían, y se
 * escribieron en vez de sustituirse por la más parecida. Regla de Jaime:
 * *«si no existe se crea; el compositor la propone y el diseñador la acepta o
 * genera una más compleja, nunca hacia abajo, siempre hacia arriba»*. Poner
 * `fuga` donde el beat pide un tajo es exactamente ir hacia abajo: se mueve
 * algo, y afirma otra cosa.
 *
 * **Cada una afirma una cosa**, y lo que dice está en
 * `src/brand/volumenes.json`. Aquí se traza.
 * @clase capa
 */

/** El frame en que el filete llega y corta. Antes de eso sólo hay avance. */
const CORTE = 22;

/** Lo que tarda cada parte en irse a su sitio, en frames. */
const REPARTO = 26;

/** Avance suave y sin rebote: `t` de 0 a 1, salida desacelerada. */
const suave = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : 1 - (1 - t) * (1 - t));

/**
 * **Tajo.** Una losa de cien avanza y un filete la parte: lo que se va sale de
 * cuadro apagado, lo que queda se queda entero y en oro.
 *
 * La proporción no se dibuja a ojo — la marca el propio ancho de las dos
 * piezas, que suman el de la losa entera. Así la lámina dice la cuenta aunque el
 * espectador no lea una sola cifra, que es para lo que está.
 *
 * El filete **cae de canto y de golpe**: es el corte, no una transición. Se
 * queda encendido después, porque lo que partió sigue partido.
 */
export const Tajo3D: React.FC<{ frame: number; parte?: number }> = ({
  frame,
  parte = 0.54,
}) => {
  const ancho = 3.0;
  const izq = ancho * parte;
  const der = ancho - izq;
  // Antes del corte la losa entera avanza hacia la cámara; después, cada mitad
  // va a lo suyo. El avance no se reinicia: el corte le pasa a algo que venía.
  const z = Math.min(frame, CORTE) * 0.055 - 1.2;
  const t = suave((frame - CORTE) / REPARTO);
  // La caída del filete: entra por arriba y se clava en el mismo frame en que
  // la losa se parte. Sin esto el corte pasaba sin que nada lo causara.
  const cae = suave((frame - (CORTE - 8)) / 8);
  return (
    <>
      {/* Lo que se va: se separa, se apaga y sale. Se lleva la porción mayor, y
          por eso el cuadro se queda más vacío de lo que estaba. */}
      <Losa
        posicion={[-(ancho - izq) / 2 - t * 2.6, -0.1 - t * 0.9, z]}
        medida={[izq, 0.62, 0.8]}
        tinte={color.secondaryBlue}
        giro={[0, 0, -t * 0.34]}
      />
      {/* Lo que queda: no se mueve del sitio y es lo único en oro. */}
      <Losa
        posicion={[izq / 2 + t * 0.34, -0.1, z]}
        medida={[der, 0.62 + t * 0.16, 0.8]}
        tinte={color.gold}
      />
      {/* El filete que corta. Un píxel de canon en 3D: fino, recto y claro. */}
      {cae > 0 ? (
        <Losa
          posicion={[izq - ancho / 2, 1.9 - cae * 2.0, z]}
          medida={[0.09, 2.4, 0.9]}
          tinte={color.lightNeutral}
        />
      ) : null}
    </>
  );
};

/** Cuándo entra la tacha, y cuándo sube la que la sustituye. */
const TACHA = 18;
const SUBE = 40;

/**
 * **Relevo.** La idea que había se tacha, se vuelca y sale; en su hueco sube
 * otra, en oro, y se queda.
 *
 * Afirma la sustitución, no la suma: si las dos se quedaran en pantalla la
 * lámina diría «además», y el beat dice «en vez de». Por eso la primera **se va
 * del cuadro** en lugar de apagarse — apagada seguiría estando, y el ojo la
 * seguiría contando.
 *
 * Y el sitio es el mismo: la segunda sube exactamente a donde estaba la primera.
 * Ocupar otro hueco sería ponerlas a convivir.
 */
export const Relevo3D: React.FC<{ frame: number }> = ({ frame }) => {
  const sitio: [number, number, number] = [0, 0.15, 0];
  const tacha = suave((frame - TACHA) / 10);
  const vuelca = suave((frame - (TACHA + 10)) / 18);
  const sube = suave((frame - SUBE) / 22);
  return (
    <>
      {/* La creencia. Sigue entera mientras se la tacha: primero se lee, luego
          se cae. Tacharla y tirarla en el mismo frame no deja leer ninguna de
          las dos cosas. */}
      {vuelca < 1 ? (
        <Losa
          posicion={[sitio[0] - vuelca * 1.1, sitio[1] - vuelca * 3.4, sitio[2]]}
          medida={[2.7, 0.62, 0.8]}
          tinte={color.navyHi}
          giro={[0, 0, -vuelca * 0.9]}
        />
      ) : null}
      {/* La tacha: cruza de lado a lado y no vuelve. Se va con la losa que
          tachó, porque tachar lo que ya no está no significa nada. */}
      {tacha > 0 && vuelca < 1 ? (
        <Losa
          posicion={[sitio[0] - vuelca * 1.1, sitio[1] - vuelca * 3.4, sitio[2] + 0.5]}
          medida={[2.9 * tacha, 0.11, 0.2]}
          tinte={color.lightNeutral}
          giro={[0, 0, -vuelca * 0.9]}
        />
      ) : null}
      {/* La verdad: sube al hueco y se queda. Un poco más gruesa, y es el único
          oro de la escena. */}
      {sube > 0 ? (
        <Losa
          posicion={[sitio[0], sitio[1] - (1 - sube) * 3.2, sitio[2]]}
          medida={[2.7, 0.62 + sube * 0.18, 0.8]}
          tinte={color.gold}
        />
      ) : null}
    </>
  );
};
