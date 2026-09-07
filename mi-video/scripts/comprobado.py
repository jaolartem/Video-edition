"""Con qué se comprueba cada decisión — y que sea con OTRA señal.

Jaime, 7-9-2026: *«para tomar decisiones, por ejemplo sobre cómo o dónde cortar,
utilizan sólo un mecanismo, los CC por ejemplo, y no el sonido, que es el
indicador más claro de que el CC está mal puesto»*. Y lo que lo cierra:
*«entonces hacen cosas sin comprobación, o la comprobación tiene varios
elementos de juicio»*; *«y como no se vieron en conjunto, hay reprocesos»*.

## Qué mira

Esto es a la comprobación lo que `verdad.py` es a la fuente: una tabla de
decisiones, y para cada una **con qué se toma** y **con qué se comprueba**. Tres
reglas, y las tres se miran aquí:

1. **Cada decisión declara su comprobación.** Si no está escrita, no existe.
2. **La comprobación viene de otra señal.** Lo decidido con el texto se
   comprueba con la onda; lo decidido con la onda, con el texto o con el
   libreto. Una comprobación que mira lo mismo que la decisión sólo confirma que
   el paso corrió.
3. **Mira un criterio.** Una que mezcla varios elementos de juicio no puede
   fallar limpio: no dice qué falló, así que no se arregla ni se automatiza, y
   acaba siendo un informe que nadie lee.

**Falla** si una comprobación declarada ya no está en el código —igual que una
aguja de `guardas.mjs`— y **avisa** de las decisiones que todavía no tienen
comprobación o la tienen con la misma señal. Avisar y no parar es a propósito:
la lista de huecos es el trabajo pendiente, no un defecto de esta corrida.

    python scripts/comprobado.py          # la tabla, con sus huecos
    python scripts/comprobado.py --solo-huecos
"""
from __future__ import annotations

import dataclasses
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclasses.dataclass(frozen=True)
class Comprobado:
    """Una decisión, la señal con que se toma y la señal que la comprueba.

    `vive_en` es «fichero :: trozo de código literal», igual que las agujas del
    log de correcciones: se busca tal cual, no como patrón.
    """

    decision: str
    decide_con: str
    comprueba_con: str
    vive_en: str | None = None
    #: Por qué todavía no la hay, cuando `vive_en` es `None`.
    falta: str = ""

    @property
    def misma_senal(self) -> bool:
        return self.decide_con.split(":")[0] == self.comprueba_con.split(":")[0]


#: **Las señales**, para que «otra señal» signifique algo y no sea una opinión:
#:
#:   texto    lo que dicen las palabras — transcript, libreto, EDL
#:   onda     lo que suena — nivel, tono, ritmo, silencio
#:   imagen   lo que se ve — dónde está él, qué hay detrás, qué luz
#:   reloj    duración y posición
COMPROBACIONES = [
    Comprobado(
        decision="donde empieza y acaba un tramo",
        decide_con="texto: las marcas de tiempo de whisper",
        comprueba_con="onda: el salto de tono y de ritmo al cruzar la union",
        vive_en="scripts/suena.py :: def costuras(slug):",
    ),
    Comprobado(
        decision="que la pieza entregada no tenga huecos muertos",
        decide_con="texto: el corte elegido",
        comprueba_con="onda: el silencio mas largo del fichero",
        vive_en="scripts/suena.py :: def aire(t):",
    ),
    Comprobado(
        decision="a que nivel sale la entrega",
        decide_con="onda: loudnorm sobre la mezcla",
        comprueba_con="onda: los LUFS del fichero ya escrito",
        vive_en="scripts/suena.py :: def onda(t):",
    ),
    Comprobado(
        decision="donde se coloca la banda de subtitulos",
        decide_con="imagen: donde esta su cara, medido sobre el corte",
        comprueba_con="imagen: que hay detras de la banda en ese corte",
        vive_en="scripts/dominio/trasfondo.py :: def de_la_pieza(",
    ),
    Comprobado(
        decision="que el render corresponde al montaje que se compuso",
        decide_con="texto: la huella del spec",
        comprueba_con="reloj: el fichero es posterior a su corte",
        vive_en="scripts/cadena.py :: def hay_que(nombre, n):",
    ),
    Comprobado(
        decision="cuando entra cada subtitulo",
        decide_con="texto: las marcas de tiempo de whisper",
        comprueba_con="—",
        falta=("nadie compara el arranque del subtitulo con el ataque del habla."
               " Es el ejemplo con el que Jaime nombro esto: el sonido es el que"
               " dice que el cc esta mal puesto, y no entra en la decision ni en"
               " la comprobacion"),
    ),
    Comprobado(
        decision="que toma se queda de dos que dicen lo mismo",
        decide_con="texto: cuanto de la etapa cubre y como de literal es",
        comprueba_con="—",
        falta=("la entrega —como lo dice— se juzga leyendo, no oyendo. La onda"
               " tiene el dato: energia, tono y ritmo de cada candidata"),
    ),
]


def _existe(vive_en: str) -> tuple[bool, str]:
    """¿Sigue ahí la comprobación declarada? Se busca literal, como una aguja."""
    if "::" not in vive_en:
        return False, f"«{vive_en}» no tiene la forma «fichero :: aguja»"
    rel, aguja = (x.strip() for x in vive_en.split("::", 1))
    ruta = os.path.join(RAIZ, rel)
    if not os.path.exists(ruta):
        return False, f"{rel} no existe"
    with open(ruta, encoding="utf-8", errors="replace") as f:
        if aguja not in f.read():
            return False, f"{rel} ya no contiene «{aguja}»"
    return True, ""


def main():
    solo_huecos = "--solo-huecos" in sys.argv
    rotas, huecos, mismas = [], [], []
    ancho = max(len(c.decision) for c in COMPROBACIONES)
    for c in COMPROBACIONES:
        if c.vive_en is None:
            huecos.append(c)
        else:
            ok, por = _existe(c.vive_en)
            if not ok:
                rotas.append((c, por))
            if c.misma_senal:
                mismas.append(c)
        if not solo_huecos:
            marca = "  " if c.vive_en else "??"
            print(f"{marca} {c.decision.ljust(ancho)}  {c.decide_con}")
            print(f"   {' '.ljust(ancho)}  -> {c.comprueba_con}")

    if mismas:
        print(f"\nse comprueban con la MISMA señal ({len(mismas)}), "
              f"que solo dice que el paso corrio:")
        for c in mismas:
            print(f"  · {c.decision} — {c.decide_con.split(':')[0]}")
    if huecos:
        print(f"\nsin comprobacion ({len(huecos)}), y no bloquean:")
        for c in huecos:
            print(f"  · {c.decision}: {c.falta}")
    if rotas:
        print(f"\nCOMPROBACIONES DECLARADAS QUE YA NO ESTAN — {len(rotas)}:")
        for c, por in rotas:
            print(f"  · {c.decision}: {por}")
        return 1
    print(f"\ncomprobado: {len(COMPROBACIONES)} decisiones, "
          f"{len(COMPROBACIONES) - len(huecos)} con su comprobacion en pie.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
