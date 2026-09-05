import { CausalChain, type CausalChainProps } from "./CausalChain";
import { Comparacion, type ComparacionProps } from "./Comparacion";
import { BeliefSwap, type BeliefSwapProps } from "./BeliefSwap";
import { Compuerta, type CompuertaProps } from "./Compuerta";
import { Acumulacion, type AcumulacionProps } from "./Acumulacion";
import { TwoPaths, type TwoPathsProps } from "./TwoPaths";
import { Anidado, type AnidadoProps } from "./Anidado";
import { Fusion, type FusionProps } from "./Fusion";
import { Desvio, type DesvioProps } from "./Desvio";
import { Fichas } from "./Fichas";
import { TableroDeclarado } from "./TableroDeclarado";
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

export const dibujaTablero = (cue: CueDeTablero, mode: Mode) => {
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
  if (cue.kind === "fusion")
    return <Fusion {...(cue.props as FusionProps)} />;
  if (cue.kind === "desvio")
    return <Desvio {...(cue.props as DesvioProps)} />;
  /**
   * **Las cuatro que son la misma forma.** `ListaNumerada` es la única que
   * lleva el número delante, y eso lo dice la forma —no un prop suelto que
   * habría que acordarse de poner en cada tablero.
   */
  if (cue.kind === "Fichas" || cue.kind === "EvidenceCard" ||
      cue.kind === "BandaFecha" || cue.kind === "ListaNumerada")
    return <Fichas props={props} numerada={cue.kind === "ListaNumerada"} />;
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
