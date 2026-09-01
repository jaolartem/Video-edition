"""Lo único del contrato que mira el disco: la aguja de código y la frase.

Todo lo demás de este paquete es declaración —se lee y no comprueba nada—.
Aquí viven las dos cosas que abren un fichero y contestan sí o no, y por eso
están juntas y solas: cuando la comprobación falla, se falla en un sitio.

Es la mitad del contrato que puede decir «esto ya no existe». La otra mitad no
sabe distinguir una promesa de un hecho.
"""
from __future__ import annotations

import dataclasses
import os
import re

#: La carpeta `mi-video`, que es donde cuelgan las rutas de las agujas
#: (`scripts/...`, `src/...`). El mismo calculo y el mismo significado que en
#: `verdad.py` — y tienen que coincidir, porque son el mismo mecanismo.
#:
#: **Tres `dirname`, y se cuentan.** Este fichero cuelga un piso mas hondo que
#: el `contratos.py` de donde salio (`scripts/contrato/aguja.py`), asi que
#: copiar los dos de antes dejaba `RAIZ` en `scripts/` y las 300 agujas daban
#: «no esta» — exactamente la averia que `Aguja.ruta()` documenta abajo, otra
#: vez y por mover el fichero.
RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def plano(t: str) -> str:
    """Un texto con los espacios colapsados. La búsqueda de agujas va sobre esto.

    Los prompts van a 80 columnas y una frase se parte a mitad: buscar literal
    sobre el fichero crudo hace que «una tabla de 2017 no respalda una cifra de
    hoy» no exista porque hay un salto de línea dentro. Colapsando, la frase es
    la frase.
    """
    return re.sub(r"\s+", " ", t or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# La aguja: lo mismo que en `docs/correcciones.md`, y por la misma razón
# ─────────────────────────────────────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class Aguja:
    """Un trozo de código LITERAL que tiene que seguir existiendo.

    No es una referencia a un fichero: es una referencia a **la línea que hace
    el trabajo**. Un fichero se reescribe entero y sigue existiendo; la aguja
    no. Es C-02: el aprendizaje llevaba semanas documentado y se perdió al
    sustituir el script donde vivía, con el texto ahí, correcto y muerto.

    `pendiente` es deuda declarada: la línea todavía no está escrita y aquí se
    dice qué hay que escribir. Falla el build en `--estricto` y avisa siempre.
    Es lo que permite pegar este fichero hoy sin rehacer la máquina: el contrato
    entra completo, y cada hueco sale nombrado con su fichero y su arreglo.
    """

    fichero: str
    aguja: str
    pendiente: str = ""

    def ruta(self) -> str:
        # **Sin `"mi-video"` en medio.** `RAIZ` ya ES `mi-video`, asi que
        # ponerlo otra vez daba `mi-video/mi-video/scripts/...`: una ruta que no
        # existe. Y `esta()` devuelve `False` tanto cuando la aguja se perdio
        # como cuando el fichero no se pudo abrir, asi que **las 300 agujas de
        # este contrato daban «no esta»** y nadie se enteraba — los cuatro
        # numeros que imprime el parte se calculan sin tocar el disco, de modo
        # que la parte que mira la realidad estaba muerta y la que no, viva.
        return os.path.join(RAIZ, self.fichero)

    def esta(self) -> bool:
        if self is NADIE or not self.fichero:
            return False
        try:
            return self.aguja in open(self.ruta(), encoding="utf-8").read()
        except OSError:
            return False

    def __str__(self):
        return f"`{self.fichero}` :: `{self.aguja}`"


#: Nadie lo lee. Se declara a propósito para que el build lo diga con nombre,
#: en vez de que la clave se pierda en silencio dentro de un `.get()`.
NADIE = Aguja("—", "—")


@dataclasses.dataclass(frozen=True)
class Prompt:
    """Una frase del prompt que **no se puede contestar sin** cierto campo.

    Es la mitad que faltaba. Un prompt puede pedir comprobar que la fecha del
    evento es la misma en todas las etapas y no recibir ninguna fecha, y eso no
    rompe nada: el modelo se inventa la comprobación y contesta que sí. Atando
    la frase al campo, el build lo dice.
    """

    fichero: str
    frase: str

    def esta(self) -> bool:
        try:
            t = open(os.path.join(RAIZ, self.fichero), encoding="utf-8").read()
        except OSError:
            return False
        return plano(self.frase).lower() in plano(t).lower()
