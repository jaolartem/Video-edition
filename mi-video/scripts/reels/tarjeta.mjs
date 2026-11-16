/**
 * **Lo que una `Tarjeta` necesita para dibujarse, dicho antes de guardarla**
 * (C-708). El esquema exigía `beat` por nombre y no por forma: reel-23, 15-11,
 * el compositor mandó `beat: [6]` creyendo que era «la etapa», y la cabecera
 * habría pintado «06—NaN». `beat` es `[posición, total]` —`[6, 19]` imprime
 * «06—19»— y lo dibuja `src/components/Tarjeta.tsx`.
 */
export function faltasDeTarjeta(props) {
  const b = props?.beat;
  const dos = Array.isArray(b) && b.length === 2 && b.every((n) => Number.isInteger(n) && n > 0);
  if (!dos || b[0] > b[1])
    return ["«Tarjeta» `beat` es [posición, total], dos enteros con posición ≤ total —"
            + " `[6, 19]` imprime «06—19»—; no es la lista de etapas ni la etapa sola"];
  return [];
}
