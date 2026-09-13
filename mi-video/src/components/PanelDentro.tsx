import React from "react";
import { AbsoluteFill } from "remotion";
import { assertShort } from "../brand/copy";
import { fontFamily } from "../brand/fonts";
import { useEntrada } from "../brand/horario";
import { color } from "../brand/tokens";
import { Fondo } from "./Fondo";
import { Bloque } from "./panel/Cierre";
import { COLUMNA, T, cabeElSujeto, columnaDe } from "./panel/sitio";
import { Recorte, type Lado } from "./Recorte";
import { Reparto, type Porcion } from "./Reparto";
import { ZonaTablero } from "./ZonaTablero";

/**
 * **El panel con él dentro.**
 *
 * Aprobado por Jaime el 6-9-2026 sobre reel-02 e2, después de siete referencias
 * y seis vueltas de mirar. La ficha entera está en `docs/canon.md`; aquí va lo
 * que hace falta para leer el código.
 *
 * **Aquí sólo se apilan capas.** Lo que decide dónde y cuándo va cada cosa
 * —horario, columna, la masa que lo separa del collage y la colocación que hay
 * que refutar— vive en [`panel/sitio`](./panel/sitio.ts), y cómo se apila lo
 * que remata, en [`panel/Cierre`](./panel/Cierre.tsx). Son tres trabajos: lo
 * que mide, lo que decide y lo que escribe.
 *
 * **Es un tipo, no una lámina.** Cuatro capas, de abajo arriba:
 *
 * 1. **La placa** de `public/fondos/`, a sangre. El collage que las referencias
 *    pedían ya existía —papel rasgado, tramas, tres tintas— y lo declara el
 *    propio tablero.
 * 2. **Masas negras**, con un solo trabajo: **sostener lo que hay que leer**.
 *    Una columna bajo su figura —el disco detrás de la cabeza de la referencia,
 *    hecho columna porque el formato es vertical— y un bloque bajo las cifras.
 *    El negro dejó de ser el fondo.
 * 3. **Él, recortado** ([`Recorte`](./Recorte.tsx)), en blanco y negro salvo que
 *    el arco pida otra cosa. *«Todo el color lo llevan las formas.»*
 * 4. **La figura que argumenta** ([`Reparto`](./Reparto.tsx)) y el texto.
 *
 * ## Dónde va cada cosa, y por qué esa raya
 *
 * Las tres primeras capas son **superficie** y van a sangre, como la placa: él
 * cruza la franja del subtítulo igual que el fotomontaje. La cuarta es
 * **contenido** y vive dentro de `ZonaTablero`, que es la instrucción T-02 —
 * *«ningún tablero baja hasta esa franja, que queda reservada al subtítulo»*—.
 * Lo que hay que leer no baja; lo que se mira, sí.
 *
 * ## El copy, con sus dos reglas
 *
 * Las etiquetas **no dicen «usted»**: van `SIN ESTRUCTURA` y `CON ESTRUCTURA`,
 * porque el reproche personal en la etiqueta convierte el dato en acusación. Y
 * la pregunta que se la devuelve al espectador va **abajo y en su propio
 * bloque**: es otro movimiento —del dato a él— y por eso no comparte bloque.
 * @clase tablero
 */
export type RepartoDeclarado = {
  /** Lo que se lee bajo la barra: `SIN ESTRUCTURA`. Nunca «usted». */
  etiqueta: string;
  porciones: Porcion[];
};

export type PanelDentroProps = {
  /** Frames desde el arranque en que se dice cada campo anclado. Lo pone el motor (C-458). */
  tiempos?: Record<string, number | (number | undefined)[] | undefined>;
  /** Placa de `public/fondos/`, a sangre. */
  placa?: string;
  /** Dónde va él: donde esté el hueco. Lo elige quien compone. */
  sujeto?: Lado;
  /** El recorte con alfa. Lo inyecta el spec; no se escribe a mano. */
  sujeto_src?: string;
  /** El filtro del tratamiento, resuelto por `scripts/imagen.mjs`. */
  sujeto_css?: string;
  /** La condición común: sin ella la comparación no es honesta. */
  premisa?: string;
  /** La cifra de esa condición, en oro. */
  cifra?: string;
  /** Uno o dos. Con dos, el segundo es el que se lleva el argumento. */
  repartos: RepartoDeclarado[];
  /** El todo del que se reparte. 100 salvo que la escena diga otra cosa. */
  total?: number;
  signo?: string;
  /** La conclusión, en oro y en una línea. */
  remate?: string;
  /** La pregunta que se la devuelve al espectador. Abajo y en su bloque. */
  pregunta?: string;
  /** De dónde salen las cifras. Cumplimiento: no se dibuja sin él. */
  fuente: string;
  /** Bajo qué supuestos son ciertas. */
  condicion?: string;
  duracion?: number;
};

export const PanelDentro: React.FC<PanelDentroProps> = ({
  placa,
  sujeto = "izquierda",
  sujeto_src,
  sujeto_css,
  premisa,
  cifra,
  repartos,
  total = 100,
  signo = "$",
  remate,
  pregunta,
  fuente,
  condicion,
  duracion,
  tiempos,
}) => {
  const entra = useEntrada();
  // **Y cada bloque entra con su palabra, si el diseño lo ancló** (C-458):
  // con el reloj fijo el reparto de reel-15 e3 salía 2 s y el remate lo barría
  // antes de que él dijera la cifra. Lo que no está anclado sigue en `T`.
  const tq = tiempos ?? {};
  const nu = (v: unknown) => (typeof v === "number" ? v : undefined);
  const rq = Array.isArray(tq.repartos) ? tq.repartos : [nu(tq.repartos)];
  const H = { ...T,
    premisa: nu(tq.premisa) ?? T.premisa,
    unoA: nu(rq[0]) ?? nu(tq.cifra) ?? T.unoA,
    unoB: nu(rq[1]) ?? (nu(rq[0]) != null ? (nu(rq[0]) as number) + (T.unoB - T.unoA) : T.unoB),
    remate: nu(tq.remate) ?? T.remate,
    pregunta: nu(tq.pregunta) ?? (nu(tq.remate) != null ? (nu(tq.remate) as number) + (T.pregunta - T.remate) : T.pregunta),
  };

  if (premisa) assertShort(premisa, "title", "PanelDentro.premisa");
  if (cifra) assertShort(cifra, "outcome", "PanelDentro.cifra");
  // **El remate es un `outcome`, no una etiqueta.** `copy.ts` lo dice con
  // ese nombre —«es el remate: cuanto mas corto, mas golpea», 38— y aqui se
  // validaba contra los 26 de `label`, asi que la frase que cierra el
  // argumento no cabia y hubo que discutir que sacar del tablero. El tope
  // correcto existia; lo que estaba mal era el rol.
  if (remate) assertShort(remate, "outcome", "PanelDentro.remate");
  if (pregunta) assertShort(pregunta, "label", "PanelDentro.pregunta");
  if (condicion) assertShort(condicion, "legal", "PanelDentro.condicion");

  cabeElSujeto(sujeto, repartos.length, Boolean(pregunta));
  const barre = entra(H.remate, 16);

  const x = columnaDe(sujeto);

  return (
    <AbsoluteFill style={{ backgroundColor: color.richBlack }}>
      {/* 1. La placa, a sangre. */}
      {placa ? (
        <Fondo placa={placa} recorte="lleno" deriva={duracion ?? 300} />
      ) : null}

      {/**
       * **Y de aquí abajo, todo lo que dibuja el panel para de la franja.**
       *
       * Las masas y él iban FUERA de `ZonaTablero` —«son superficie, como la
       * placa»— y en el fotograma de reel-02 e2 eso se vio en las dos formas
       * que tiene de romperse: el subtítulo «cada 100 dólares que él recibe,»
       * cayó **encima de su silueta**, y la cola de la columna quedó de 1.370 a
       * 1.580 como una masa negra suelta que no sostenía nada, en la mitad de
       * abajo que la lámina aprobada deja al collage.
       *
       * A sangre se queda **sólo la placa**, que es fondo y no compite con
       * nada. Todo lo demás —las masas, él y el contenido— es del panel, y el
       * panel acaba en el techo de la franja. Así no hay que acordarse: lo que
       * se pase se ve cortado, que es la misma relación de T-02.
       */}
      <ZonaTablero>
        {/**
         * 2. La masa negra, y **hay UNA, no dos**: la que sostiene las cifras.
         * Sobre las flechas de la placa ni los números ni sus rótulos se leían.
         *
         * **Debajo de él no va ninguna.** La llevaba —el disco de la referencia,
         * hecho columna porque el formato es vertical— y Jaime la quitó al
         * verla: *«yo no debería tener cuadrado negro de contraste, el efecto de
         * papel recortado cumple esa función»*. Y es exacto: la orla clara de
         * fibra ya lo separa del collage por todo el contorno, así que la masa
         * hacía dos veces el mismo trabajo y encima tapaba la placa. Es la regla
         * de siempre —nada se dice dos veces— aplicada a la composición.
         */}
        <div
          style={{
            position: "absolute",
            left: x - 50,
            top: COLUMNA.arriba - 50,
            width: COLUMNA.ancho + 160,
            // **Y baja hasta el remate.** Con 540 la masa acababa en los
            // rótulos y el remate caía sobre las diagonales de la placa: se
            // leía, pero peleando. El único trabajo de esta masa es sostener lo
            // que hay que leer, y el remate es lo último de la columna.
            height: COLUMNA.salto + 400,
            backgroundColor: color.richBlack,
            opacity: 0.93 * entra(H.unoA - 4, 16) * (1 - barre),
            transform: "rotate(-3deg)",
          }}
        />

        {/* **El barrido del remate.** Jaime: *«que puede borrar el panel o
            parte de él, pero debe salir super enfático»*. Cuando aterriza la
            frase que cierra, lo que la demostró se retira — las barras, la
            premisa, la masa que las sostenía—. No es un efecto: mientras el
            diagrama sigue en pantalla el ojo está en las cifras y la conclusión
            es un renglón más. Vaciando el cuadro, la conclusión es lo único que
            queda. Es la carga cognitiva llevada al tiempo: no poner menos, sino
            que en cada instante haya una sola cosa. */}

        {/* 4. Lo que hay que leer. */}
        {premisa ? (
          <Bloque
            ancho={820}
            abre={entra(H.premisa, 14)}
            style={{ position: "absolute", left: 0, top: 24, opacity: 1 - barre }}
          >
            <div
              style={{
                fontFamily: fontFamily.bloque,
                fontSize: 54,
                lineHeight: 1.06,
                textTransform: "uppercase",
                color: color.lightNeutral,
              }}
            >
              {premisa}
              {cifra ? <div style={{ color: color.gold }}>{cifra}</div> : null}
            </div>
          </Bloque>
        ) : null}

        {repartos.slice(0, 2).map((r, i) => (
          <div
            key={r.etiqueta}
            style={{
              position: "absolute",
              left: x,
              top: COLUMNA.arriba + i * COLUMNA.salto,
              opacity: entra(i ? H.unoB : H.unoA, 14) * (1 - barre),
            }}
          >
            <Reparto
              total={total}
              porciones={r.porciones}
              ancho={COLUMNA.ancho}
              signo={signo}
              desde={i ? H.unoB : H.unoA}
              etiqueta={assertShort(r.etiqueta, "label", "PanelDentro.etiqueta")}
              source={fuente}
            />
          </div>
        ))}

        {remate ? (
          <div
            style={{
              position: "absolute",
              left: 0,
              top: 620,
              width: 1080,
              padding: "44px 54px",
              backgroundColor: color.richBlack,
              opacity: barre,
              transform: `translateY(${(1 - barre) * 28}px)`,
            }}
          >
            <div
              style={{
                fontFamily: fontFamily.bloque,
                fontSize: 104,
                lineHeight: 0.98,
                letterSpacing: "-0.01em",
                textTransform: "uppercase",
                color: color.gold,
              }}
            >
              {remate}
            </div>
            {/* La pregunta va DENTRO del mismo bloque y debajo: puesta aparte
                caía encima de la segunda línea del remate. Y entra después —es
                otro movimiento, del dato a él— con el mismo escalonado. */}
            {pregunta ? (
              <div
                style={{
                  marginTop: 26,
                  fontFamily: fontFamily.bloque,
                  fontSize: 46,
                  letterSpacing: "0.01em",
                  textTransform: "uppercase",
                  color: color.lightNeutral,
                  opacity: entra(H.pregunta, 14),
                }}
              >
                {pregunta}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* **Él, DELANTE de los datos.** Jaime: *«que los datos también jueguen
            con mi cara»*. Dibujado antes, la masa de las cifras se lo comía por
            el hombro y parecía metido en una caja. Dibujado aquí —después de
            los repartos— las barras le pasan por detrás igual que el texto en
            el gancho, y la lámina deja de ser dos columnas que se ignoran.
            Sangra por su borde: entero dentro del cuadro sería pegatina. */}
        {sujeto_src ? (
          <Recorte
            src={sujeto_src}
            lado={sujeto}
            css={sujeto_css}
            // **Él no se barre.** El remate lo fundía al 10 % y quedaba su
            // sombra: reel-15 e3 pasó 6 s con un fantasma de su cara (C-461).
            // Desde el 10-9 todo tablero lleva su cara, también en el remate.
            entra={entra(H.el, 18)}
          />
        ) : null}
      </ZonaTablero>

      {/* **La fuente sigue fuera de la zona segura, y ya no la dibuja este
          componente.** Era la primera lámina que lo hizo bien —Jaime: *«por
          fuera de la zona segura; no me interesa que lo lean, sólo que sepan
          que existe»*— y por eso se copió a `acumulacion/Cierre`, con el 1262
          escrito a mano en los dos. Dos copias de una regla del canon divergen:
          ahora la monta `dibujaTablero` para las 24. Ver `PieTablero.tsx`. */}
    </AbsoluteFill>
  );
};
