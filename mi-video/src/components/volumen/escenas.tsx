import React from "react";
import { color } from "../../brand/tokens";
import { Losa } from "./losa";

/**
 * Las escenas de [`Volumen`](../Volumen.tsx) en las que **algo circula**: entra
 * por un lado, atraviesa una estructura y sale —o deja de salir— por el otro. El
 * argumento está en el trayecto. Las que trabajan con una masa quieta viven en
 * [`masas`](./masas.tsx), que salió de aquí cuando este fichero tocó el techo de
 * `scripts/tamano.py`.
 *
 * **Cada una afirma una cosa.** Lo que dice está en `src/brand/volumenes.json`,
 * que es la biblioteca; aquí se traza.
 *
 * Viven en su propio fichero por el mismo motivo que `comparacion/` o
 * `declarado/`: el componente de arriba coloca, enciende y despacha —eso no
 * cambia al añadir una escena— y esto dibuja. Una escena nueva se añade aquí y
 * se registra allí, y `tsc` no deja que una exista sin la otra.
 *
 * La primitiva es la losa plana y mate de [`losa`](./losa.tsx).
 * @clase capa
 */

/** Cuántas losas lleva el caudal que atraviesa la compuerta. */
const CAUDAL = 16;

/**
 * **Compuerta.** Un caudal atraviesa un pórtico y sale más grueso y en oro.
 *
 * Afirma lo que el beat afirma: lo que cambia no es cuánto entra, es qué lo
 * atraviesa. Por eso la losa **no cambia de tamaño al azar ni al entrar**:
 * cambia exactamente al cruzar z = 0, que es donde está la compuerta.
 */
export const Compuerta3D: React.FC<{ frame: number }> = ({ frame }) => {
  const largo = 13;
  return (
    <>
      {/* El pórtico: dos jambas y un dintel. Es lo único quieto de la escena, y
          por eso se lee como la estructura y no como parte del caudal. */}
      <Losa posicion={[-1.45, 0.5, 0]} medida={[0.2, 2.6, 0.5]} tinte={color.navyHi} />
      <Losa posicion={[1.45, 0.5, 0]} medida={[0.2, 2.6, 0.5]} tinte={color.navyHi} />
      <Losa posicion={[0, 1.7, 0]} medida={[3.1, 0.24, 0.5]} tinte={color.lightNeutral} />
      {Array.from({ length: CAUDAL }, (_, i) => {
        // Avance continuo y en bucle: cada losa recorre el mismo tramo con su
        // desfase, así que el caudal no tiene principio ni final visibles.
        const z = ((frame * 0.12 + i * (largo / CAUDAL)) % largo) - largo * 0.62;
        const paso = z > 0;
        return (
          <Losa
            key={i}
            posicion={[0, paso ? -0.15 : -0.5, z]}
            medida={[2.5, paso ? 0.7 : 0.22, 0.34]}
            tinte={paso ? color.gold : color.secondaryBlue}
          />
        );
      })}
    </>
  );
};

/**
 * **Desvío.** Una vía sube y se parte en dos: la apagada se queda a mitad de
 * camino, la de oro llega entera.
 *
 * Afirma que hay dos rutas para la misma plata y que sólo una llega. La rama
 * corta **no se desvanece**: deja de haber losas, que es la forma de decir que
 * el camino se acaba y no que se vea menos.
 */
export const Desvio3D: React.FC<{ frame: number }> = ({ frame }) => {
  const tronco = 7;
  const rama = 9;
  // Se traza: cada losa entra en su frame. El movimiento es el trazo, igual que
  // en el pictograma que esto sustituye — sólo que con canto y con luz.
  const puestas = Math.floor(frame / 3);
  const corta = Math.round(rama * 0.55);
  return (
    <>
      {Array.from({ length: tronco }, (_, i) =>
        i < puestas ? (
          <Losa
            key={`t${i}`}
            posicion={[0, -1 + i * 0.16, -3.4 + i * 0.62]}
            medida={[1.5, 0.2, 0.5]}
            tinte={color.secondaryBlue}
          />
        ) : null,
      )}
      {Array.from({ length: rama }, (_, i) => {
        const j = tronco + i;
        const y = -1 + tronco * 0.16;
        const z = -3.4 + tronco * 0.62 + i * 0.46;
        return (
          <React.Fragment key={`r${i}`}>
            {i < corta && j < puestas ? (
              <Losa
                posicion={[-0.45 - i * 0.16, y - i * 0.06, z]}
                medida={[0.95, 0.18, 0.5]}
                tinte={color.navyHi}
                giro={[0, -0.32, 0]}
              />
            ) : null}
            {j < puestas ? (
              <Losa
                posicion={[0.45 + i * 0.16, y + i * 0.26, z]}
                medida={[0.95, 0.26, 0.5]}
                tinte={color.gold}
                giro={[0, 0.32, 0]}
              />
            ) : null}
          </React.Fragment>
        );
      })}
    </>
  );
};

/** Cada cuántos frames se desprende un tramo de la columna. */
const TRAMO = 16;

/**
 * **Fuga.** Una columna se apila y, cada tramo, una losa se desprende y cae.
 *
 * Afirma que lo que se pierde se pierde por tramos y sin ruido: la columna sigue
 * ahí, y lo que falta sólo se ve porque algo cayó.
 */
export const Fuga3D: React.FC<{ frame: number }> = ({ frame }) => {
  const alto = 9;
  return (
    <>
      {Array.from({ length: alto }, (_, i) => {
        const cae = frame - (i + 1) * TRAMO;
        if (cae <= 0) {
          return (
            <Losa
              key={i}
              posicion={[0, -1.3 + i * 0.34, 0]}
              medida={[2.2, 0.3, 0.7]}
              tinte={i === alto - 1 ? color.gold : color.navyHi}
            />
          );
        }
        // Caída con aceleración constante: es una masa que se suelta, no un
        // objeto que se anima. Se sale del cuadro y no vuelve.
        const t = cae / 30;
        return (
          <Losa
            key={i}
            posicion={[0.4 * t, -1.3 + i * 0.34 - 4.6 * t * t, 0.3 * t]}
            medida={[2.2, 0.3, 0.7]}
            tinte={color.gold}
            giro={[0, 0, -0.5 * t]}
          />
        );
      })}
    </>
  );
};
