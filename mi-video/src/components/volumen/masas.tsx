import React from "react";
import { color } from "../../brand/tokens";
import { Losa } from "./losa";

/**
 * Los volúmenes que trabajan con **una masa quieta**, y no con un caudal.
 *
 * Viven aparte de [`escenas`](./escenas.tsx) por lo que afirman, no por sitio:
 * allí algo circula —entra por un lado y sale por otro—, y el argumento está en
 * el trayecto. Aquí no circula nada. Hay una masa, y lo que argumenta es lo que
 * le pasa: crece hasta el borde, cruza una raya, se separa de otra dejando un
 * hueco, o queda señalada por una luz. Juntarlos en un fichero hacía además que
 * `scripts/tamano.py` lo parase, que fue el aviso.
 *
 * La primitiva sigue siendo la misma —la losa plana y mate de
 * [`losa`](./losa.tsx)—, porque el canon no cambia por añadir escenas: bloque de
 * color, canto recto, sin brillo, sin bisel. Lo que el 3D pone es profundidad y
 * luz con dirección; nada más.
 *
 * Todo sale de `frame`: mismo frame, mismo dibujo.
 * @clase capa
 */

/** Cada cuántos frames entra una losa cuando algo se traza o se apila. */
const PASO = 4;

/**
 * **Brecha.** Dos columnas suben desde la misma línea a distinta altura y un
 * filete de oro cruza el hueco entre las dos cabezas.
 *
 * Afirma que las dos partieron del mismo sitio y que **la distancia es el
 * dato**: no hay nada malo en la columna corta, lo que hay que mirar es el
 * espacio entre las dos. Por eso el oro no está en ninguna de las dos masas —
 * está en el hueco, que es lo que el beat nombra.
 */
export const Brecha3D: React.FC<{ frame: number }> = ({ frame }) => {
  const corta = 4;
  const larga = 9;
  const puestas = Math.floor(frame / PASO);
  // El filete llega cuando las dos columnas están, no antes: cruzar un hueco
  // que todavía se está construyendo no dice nada.
  const cruza = puestas > larga;
  const cabezaCorta = -1.5 + corta * 0.34;
  const cabezaLarga = -1.5 + larga * 0.34;
  return (
    <>
      {Array.from({ length: larga }, (_, i) => (
        <React.Fragment key={i}>
          {i < corta && i < puestas ? (
            <Losa
              posicion={[-1.05, -1.5 + i * 0.34, 0]}
              medida={[1.5, 0.28, 0.6]}
              tinte={color.navyHi}
            />
          ) : null}
          {i < puestas ? (
            <Losa
              posicion={[1.05, -1.5 + i * 0.34, 0]}
              medida={[1.5, 0.28, 0.6]}
              tinte={color.secondaryBlue}
            />
          ) : null}
        </React.Fragment>
      ))}
      {/* Cabeza a cabeza y ni un milímetro más: el filete MIDE el hueco, así
          que si sobresale por fuera de las columnas deja de medir nada — la
          primera versión iba a 3,4 de largo y salía disparado por encima de la
          columna alta. La longitud es la hipotenusa entre las dos cabezas. */}
      {cruza ? (
        <Losa
          posicion={[0, (cabezaCorta + cabezaLarga) / 2, 0.32]}
          medida={[Math.hypot(2.1, cabezaLarga - cabezaCorta) * 0.9, 0.1, 0.12]}
          tinte={color.gold}
          giro={[0, 0, Math.atan2(cabezaLarga - cabezaCorta, 2.1)]}
        />
      ) : null}
    </>
  );
};

/**
 * **Franja.** Dos muros avanzan en profundidad, uno desde cada lado, y se
 * detienen sin llegar a tocarse.
 *
 * Afirma que cada lado hizo lo suyo y que **el hueco que queda en medio no es
 * de nadie**. Los dos muros son iguales y ninguno falla: lo único que se ve
 * distinto es el corredor vacío, y por eso el oro está ahí y no en ellos.
 */
export const Franja3D: React.FC<{ frame: number }> = ({ frame }) => {
  const fondo = 7;
  const puestas = Math.floor(frame / PASO);
  // Los muros no se cierran nunca: se paran a esta distancia del eje y ahí se
  // quedan. **Medido sobre render**: con 0,55 el corredor se veía como una cuña
  // asomando por debajo, no como un hueco — y el hueco es lo que argumenta.
  const HUECO = 0.75;
  return (
    <>
      {Array.from({ length: fondo }, (_, i) =>
        i < puestas ? (
          <React.Fragment key={i}>
            <Losa
              posicion={[-HUECO - 0.85, 0.1, -3 + i * 0.85]}
              medida={[1.5, 1.6, 0.5]}
              tinte={color.navyHi}
            />
            <Losa
              posicion={[HUECO + 0.85, 0.1, -3 + i * 0.85]}
              medida={[1.5, 1.6, 0.5]}
              tinte={color.navyHi}
            />
          </React.Fragment>
        ) : null,
      )}
      {/* El suelo del corredor, en oro: es lo único encendido de la escena y es
          lo que no tiene dueño. Se ilumina cuando los dos muros ya están. */}
      {puestas > fondo ? (
        <Losa
          posicion={[0, -0.68, -0.5]}
          medida={[HUECO * 2, 0.08, 6]}
          tinte={color.gold}
        />
      ) : null}
    </>
  );
};

/** Cada cuántos frames la masa contenida da un salto. */
const SALTO = 20;

/**
 * **Contención.** Dentro de un cajón, una masa crece a saltos y no sale nada.
 *
 * Afirma que **lo que no se mueve se acumula dentro**. El cajón no se rompe y
 * la masa no desborda: el argumento no es un accidente, es que quedarse quieto
 * tiene consecuencia. Va sin oro a propósito — aquí todavía no ha pasado nada
 * que mirar, y ése es justo el punto del beat.
 */
export const Contencion3D: React.FC<{ frame: number }> = ({ frame }) => {
  const saltos = Math.min(5, 1 + Math.floor(frame / SALTO));
  const alto = 0.34 * saltos;
  return (
    <>
      {/* El cajón: suelo y dos paredes. Quieto, como el pórtico de la
          compuerta, para que se lea como el límite y no como parte de la masa. */}
      <Losa posicion={[0, -1.5, 0]} medida={[2.8, 0.16, 1.4]} tinte={color.navyHi} />
      <Losa posicion={[-1.42, -0.4, 0]} medida={[0.16, 2.4, 1.4]} tinte={color.navyHi} />
      <Losa posicion={[1.42, -0.4, 0]} medida={[0.16, 2.4, 1.4]} tinte={color.navyHi} />
      <Losa
        posicion={[0, -1.42 + alto / 2, 0]}
        medida={[2.5, alto, 1.1]}
        tinte={color.secondaryBlue}
      />
    </>
  );
};

/**
 * **Umbral.** La masa sube hasta pasar una raya que ya estaba puesta, y al
 * cruzarla la raya se enciende y lo que queda por encima cambia de tinte.
 *
 * Afirma que **lo dispara cruzar la raya, no una decisión**: nadie empuja la
 * masa, nadie mueve la raya. Es la otra mitad de `contencion` y por eso comparte
 * su cajón; lo que cambia es que aquí el límite se alcanza.
 */
export const Umbral3D: React.FC<{ frame: number }> = ({ frame }) => {
  const RAYA = -0.35;
  const alto = Math.min(2.3, 0.5 + frame * 0.022);
  const cima = -1.42 + alto;
  const cruzado = cima > RAYA;
  return (
    <>
      <Losa posicion={[0, -1.5, 0]} medida={[2.8, 0.16, 1.4]} tinte={color.navyHi} />
      <Losa posicion={[-1.42, -0.4, 0]} medida={[0.16, 2.4, 1.4]} tinte={color.navyHi} />
      <Losa posicion={[1.42, -0.4, 0]} medida={[0.16, 2.4, 1.4]} tinte={color.navyHi} />
      {/* Lo que está por debajo de la raya sigue siendo lo de siempre. */}
      <Losa
        posicion={[0, (-1.42 + Math.min(cima, RAYA)) / 2, 0]}
        medida={[2.5, Math.min(cima, RAYA) + 1.42, 1.1]}
        tinte={color.secondaryBlue}
      />
      {/* Y lo que pasa de la raya cambia de tinte: no es más masa, es la misma
          que ahora se cobra distinto. */}
      {cruzado ? (
        <Losa
          posicion={[0, (RAYA + cima) / 2, 0]}
          medida={[2.5, cima - RAYA, 1.1]}
          tinte={color.gold}
        />
      ) : null}
      {/* La raya estaba antes de que nada subiera: se ve apagada y se enciende
          sola. Si apareciera al cruzarse parecería que alguien la puso. */}
      <Losa
        posicion={[0, RAYA, 0.75]}
        medida={[3.2, 0.07, 0.12]}
        tinte={cruzado ? color.gold : color.navyHi}
      />
    </>
  );
};

/**
 * **Foco.** Tres losas apagadas se apilan; un haz de oro entra desde fuera de
 * cuadro, se para encima y un marco recto se cierra alrededor de la pila.
 *
 * Afirma que **lo que se dejó sin ordenar es lo que queda señalado**: la pila no
 * cae ni se rompe. No le pasa nada — lo único que cambia es que ahora se la
 * mira. Es el único volumen cuyo movimiento es la luz, y por eso el haz llega
 * despacio: barrer rápido lo convierte en un efecto.
 *
 * El marco existe porque una luz sola ilumina y no señala: el oro tiene que
 * decir dónde, y en este sistema eso lo hace la geometría.
 */
export const Foco3D: React.FC<{ frame: number }> = ({ frame }) => {
  const puestas = Math.min(3, Math.floor(frame / (PASO * 4)) + 1);
  // El haz barre de fuera hacia el centro y se para. Cuando llega ya están las
  // tres losas: se señala lo que hay, no lo que se está montando.
  const barrido = Math.max(0, 1 - Math.max(0, frame - 34) / 26);
  const marco = barrido === 0;
  const LADO = 1.7;
  const CANTO = 1.05;
  return (
    <>
      {/* Sin `target`: el foco apunta al origen, que es donde está la pila. */}
      <spotLight
        position={[5.2 * barrido + 0.3, 4.4, 2.6]}
        angle={0.4}
        penumbra={0.18}
        intensity={140}
        distance={14}
        color={color.gold}
      />
      {Array.from({ length: 3 }, (_, i) =>
        i < puestas ? (
          <Losa
            key={i}
            posicion={[0, -1.3 + i * 0.46, 0]}
            medida={[2.4, 0.38, 1]}
            tinte={color.navyHi}
          />
        ) : null,
      )}
      {marco ? (
        <>
          <Losa posicion={[0, CANTO, 0.6]} medida={[LADO * 2, 0.07, 0.07]} tinte={color.gold} />
          <Losa posicion={[0, -CANTO - 0.6, 0.6]} medida={[LADO * 2, 0.07, 0.07]} tinte={color.gold} />
          <Losa posicion={[-LADO, -0.3, 0.6]} medida={[0.07, CANTO * 2 + 0.6, 0.07]} tinte={color.gold} />
          <Losa posicion={[LADO, -0.3, 0.6]} medida={[0.07, CANTO * 2 + 0.6, 0.07]} tinte={color.gold} />
        </>
      ) : null}
    </>
  );
};
