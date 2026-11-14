import React from "react";
import { layout, type Lienzo } from "./lienzo";

/**
 * **El lienzo de la pieza que se está dibujando.** Lo pone `Composition.tsx`
 * con el `formato` de la pieza y lo lee quien dibuja, sin saber de qué pieza
 * es — igual que `LadoDelSujeto` en `ZonaTablero` (C-670).
 *
 * Por defecto, el vertical: una composición que no lo pone es una pieza de
 * siempre, y sale idéntica a como salía.
 */
export const LienzoContexto = React.createContext<Lienzo>(layout);

/** El lienzo de la pieza. Su franja es `useLienzo().franja`. */
export const useLienzo = (): Lienzo => React.useContext(LienzoContexto);

/**
 * Una composición dentro de su lienzo. El vertical no se envuelve —es el valor
 * por defecto del contexto—, así que las piezas de siempre registran el mismo
 * componente que antes.
 */
const envueltos = new Map<string, Map<React.FC<never>, React.FC<never>>>();

export const enSuLienzo = <P extends object>(
  componente: React.FC<P>,
  lienzo: Lienzo,
): React.FC<P> => {
  if (lienzo === layout) return componente;
  const deEste = envueltos.get(lienzo.formato) ?? new Map();
  envueltos.set(lienzo.formato, deEste);
  const ya = deEste.get(componente as React.FC<never>);
  if (ya) return ya as React.FC<P>;
  const Envuelto: React.FC<P> = (props) => (
    <LienzoContexto.Provider value={lienzo}>
      {React.createElement(componente, props)}
    </LienzoContexto.Provider>
  );
  Envuelto.displayName = `${componente.displayName ?? componente.name}En${lienzo.formato}`;
  deEste.set(componente as React.FC<never>, Envuelto as React.FC<never>);
  return Envuelto;
};
