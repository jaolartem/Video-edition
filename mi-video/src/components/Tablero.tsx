import { CausalChain, type CausalChainProps } from "./CausalChain";
import { Comparacion, type ComparacionProps } from "./Comparacion";
import { BeliefSwap, type BeliefSwapProps } from "./BeliefSwap";
import { Compuerta, type CompuertaProps } from "./Compuerta";
import { Acumulacion, type AcumulacionProps } from "./Acumulacion";
import { TwoPaths, type TwoPathsProps } from "./TwoPaths";
import { Anidado, type AnidadoProps } from "./Anidado";
import { Recuento, type RecuentoProps } from "./Recuento";
import { Fusion, type FusionProps } from "./Fusion";
import { Desvio, type DesvioProps } from "./Desvio";
import { Fichas } from "./Fichas";
import { LaminaCasillas } from "./LaminaCasillas";
import { Techo, type TechoProps } from "./Techo";
import { PanelDentro, type PanelDentroProps } from "./PanelDentro";
import { PieTablero } from "./PieTablero";
import { TableroDeclarado } from "./TableroDeclarado";
import { Recorte, type Forma, type Lado } from "./Recorte";
import { LadoDelSujeto, ZonaTablero } from "./ZonaTablero";
import { COLUMNA } from "./panel/sitio";
import type { Mode } from "../brand/tokens";

/**
 * **Qué componente dibuja cada forma declarada.** Un solo sitio, y por eso es
 * un fichero.
 *
 * Vivía derramado en un ternario de doce ramas dentro del `map` de `Ad.tsx`, y
 * esa forma tenía un coste concreto: **una forma que no estaba en la lista no
 * daba error, dibujaba lo que podía y salía un hueco**. Siete cayeron ahí
 * durante cinco ciclos —`Anidado`, `fusion`, `BandaFecha`, `ListaNumerada`,
 * `EvidenceCard`, `desvio` y la propia `TableroDeclarado` usada como forma— y
 * las entregas del 5 de septiembre salieron con los nombres internos escritos
 * en pantalla.
 *
 * **Cuatro de las siete eran la misma idea con otro nombre**: bloques planos
 * apilados y separados por filetes. Por eso hay cuatro componentes nuevos y no
 * siete — escribir siete es tener siete filetes que acaban midiendo distinto,
 * que es la avería de las cuatro copias de la franja otra vez.
 *
 * `scripts/conectado.py` lee estas comparaciones literales para decir qué se
 * declara y no se despacha, así que la lista y el informe no pueden separarse:
 * quitar una rama de aquí hace que la forma vuelva a salir en el informe, que
 * es exactamente lo que tiene que pasar.
 * @clase sistema
 */
export type CueDeTablero = {
  kind: string;
  props: Record<string, unknown> | unknown;
};

/**
 * **El tablero y su pie, que ya no son cosa de cada forma.**
 *
 * El pie de fuente estaba escrito cinco veces —una por forma que lo necesitó— y
 * las cinco divergieron: banda clara en tres, banda oscura en dos, el `1262`
 * escrito a mano en dos, y en cinco tableros del lote acabó siendo un párrafo
 * de tres y cuatro renglones dentro de la lámina. Aquí se monta **una vez para
 * las 24**, así que una forma nueva nace con su pie puesto y ninguna puede
 * volver a dibujarlo a su manera. Ver [`PieTablero`](./PieTablero.tsx).
 *
 * La línea la compone `scripts/reels/cifras.mjs :: pieDe` y viaja en el único
 * prop `pie`: **un destino, no uno por forma**. El mapa `PIE_POR_KIND` que había
 * allí —`fuente` en unos, `resultado.source` en otros, `limitation` en los de
 * más allá— existía justo porque cada componente lo leía por su cuenta.
 */
export const dibujaTablero = (cue: CueDeTablero, mode: Mode) => {
  const props = cue.props as Record<string, unknown>;
  /**
   * **Él dentro del tablero, puesto aquí para todas las formas** (T-06).
   *
   * Jaime, 10-9-2026: *«ahora todos los tableros deben mostrar mi cara en la
   * composición; la base son los del R-02»*. Lo sabía dibujar sólo
   * `PanelDentro`, así que `sujeto` declarado en cualquier otra forma no salía.
   * Aquí se monta una vez, igual que el pie: el lado viaja por contexto hasta
   * `ZonaTablero`, que deja libre su columna, y el recorte va encima, cortado
   * en el techo de la franja. `PanelDentro` sigue pintando el suyo —su horario
   * y su orden de capas son los que Jaime aprobó— y por eso no entra aquí.
   */
  const lado = props?.sujeto as Lado | undefined;
  const src = props?.sujeto_src as string | undefined;
  const conSujeto = Boolean(lado && src) && cue.kind !== "PanelDentro";
  return (
    <>
      <LadoDelSujeto.Provider value={conSujeto ? lado ?? null : null}>
        {laForma(cue, mode)}
      </LadoDelSujeto.Provider>
      {conSujeto ? (
        <ZonaTablero>
          {/* **Y el recorte no sale de su columna.** La pegatina mide 980 px y
              se comía la columna del copy: reel-08 e3, reel-09 e7 y reel-11 e3
              salieron con la tarjeta de oro o las fichas tapadas (C-443). */}
          <div
            style={{
              position: "absolute",
              top: 0,
              bottom: 0,
              [lado === "derecha" ? "right" : "left"]: 0,
              width: COLUMNA.x,
              overflow: "hidden",
            }}
          >
            <Recorte
              src={src as string}
              lado={lado}
              forma={props?.sujeto_forma as Forma | undefined}
              css={props?.sujeto_css as string | undefined}
            />
          </div>
        </ZonaTablero>
      ) : null}
      <PieTablero linea={props?.pie as string | undefined} />
    </>
  );
};

const laForma = (cue: CueDeTablero, mode: Mode) => {
  const props = cue.props as Record<string, unknown>;
  if (cue.kind === "causal")
    return <CausalChain {...(cue.props as CausalChainProps)} mode={mode} />;
  if (cue.kind === "comparacion")
    return <Comparacion {...(cue.props as ComparacionProps)} />;
  if (cue.kind === "acumulacion")
    return <Acumulacion {...(cue.props as AcumulacionProps)} />;
  if (cue.kind === "twopaths")
    return <TwoPaths {...(cue.props as TwoPathsProps)} mode={mode} />;
  if (cue.kind === "BeliefSwap")
    return <BeliefSwap {...(cue.props as BeliefSwapProps)} />;
  if (cue.kind === "Compuerta")
    return <Compuerta {...(cue.props as CompuertaProps)} />;
  if (cue.kind === "Anidado")
    return <Anidado {...(cue.props as AnidadoProps)} />;
  /**
   * **Cuántos hay de un lado y cuántos del otro, contados en marcas.** No es
   * una comparación de cifras: la asimetría se ve sin leer nada, que es lo que
   * pidió Jaime para reel-02 e7 — *«hay muchos y hay un curso en español»*.
   */
  if (cue.kind === "Recuento")
    return <Recuento {...(cue.props as RecuentoProps)} />;
  if (cue.kind === "fusion")
    return <Fusion {...(cue.props as FusionProps)} />;
  /**
   * **Una cifra sola, con la condición que la produce y el tramo donde vale.**
   * Es la mitad de «gráficos y palabras» que no dibuja nada: cuando el dato es
   * una tasa y un umbral —y no un reparto—, la proporción no existe y dibujarla
   * afirma lo que ninguna fuente sostiene. Ver `Techo.tsx` y el tiquet #215.
   */
  if (cue.kind === "Techo")
    return <Techo {...(cue.props as TechoProps)} />;
  if (cue.kind === "desvio")
    return <Desvio {...(cue.props as DesvioProps)} />;
  /**
   * **El panel con él dentro.** No es una lámina de reel-02: es el tipo que
   * Jaime aprobó el 6-9-2026, con su placa, sus masas negras, su recorte y la
   * figura que argumenta. Los grados de libertad —de qué lado va él y con qué
   * tratamiento— viajan en los props y salen del arco, no del gusto.
   */
  if (cue.kind === "PanelDentro")
    return <PanelDentro {...(cue.props as PanelDentroProps)} />;
  /**
   * **Las cuatro que son la misma forma.** `ListaNumerada` es la única que
   * lleva el número delante, y eso lo dice la forma —no un prop suelto que
   * habría que acordarse de poner en cada tablero.
   */
  if (cue.kind === "Fichas" || cue.kind === "EvidenceCard" ||
      cue.kind === "BandaFecha" || cue.kind === "ListaNumerada")
    return <Fichas props={props} numerada={cue.kind === "ListaNumerada"} />;
  /** **Casillas que se tachan cuando se dicen**, a cuadro completo. */
  // Y por su propio nombre, que es el que da el catálogo: declarado así, reel-11
  // e5 caía en la lista genérica sin tachar ni sellar nada (C-435).
  if (cue.kind === "tachadura" || cue.kind === "Casillas" || cue.kind === "LaminaCasillas")
    return <LaminaCasillas props={props} />;
  /**
   * **Y lo demás también se dibuja.** Aquí caían diecinueve formas declaradas
   * por el diseñador y no salía nada — ni en pantalla ni en el log. `TwoPaths`
   * era el `else`, así que una forma que no fuera ninguna de las tres primeras
   * se intentaba dibujar como dos trayectorias y reventaba o salía vacía.
   *
   * `cue.kind === "TableroDeclarado"` está escrito aparte a propósito: es una
   * forma que el diseño **elige** cuando no quiere ninguna otra, y sin la rama
   * explícita el informe la contaba como forma sin despachar.
   */
  if (cue.kind === "TableroDeclarado")
    return <TableroDeclarado kind={cue.kind} props={props} />;
  return <TableroDeclarado kind={cue.kind} props={props} />;
};
