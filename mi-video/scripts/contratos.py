"""Un contrato por paso de IA, y uno solo, del que se derivan las tres partes.

Regla de Jaime, que es la que ordena este fichero:

> *«Es un problema tener 3 contratos: estás validando lo mismo con diferentes
> criterios, no puede ser estable. No son tres pasos, es uno que se repite hasta
> que pase.»* Y la segunda: *«redundancia y fuentes debe estar en todos los
> contratos.»*

Y la de arquitectura, que dice por qué esto es un fichero de datos y no prosa:
lo que pueda hacerse por código se hace por código; lo que es por IA tiene que
tener un mecanismo para que **siempre se haga exactamente igual**. Un prompt es
prosa: se reescribe sin que nadie se entere. Esto no.

## Las tres partes, derivadas de aquí

    payload   `Campo.manda`   la línea de código que mete el dato en el pedido
    prompt    `Campo.exige`   la frase del prompt que no se puede contestar sin él
    consumo   `Clave.dispara` la línea de código que EJECUTA lo que se contesta

Ninguna de las tres se escribe a mano dos veces: el pedido se arma recorriendo
`campos_todos()`, los bloques de prosa compartida se renderizan en los prompts
con su huella, y el verificador comprueba que cada aguja sigue en su sitio —el
mismo mecanismo de `guardas.mjs`, que es el único que sobrevivió a una
reescritura.

## Lo que esto convierte en imposible

- **Una clave inerte.** `dispara=NADIE` falla el build y dice cuál. Hoy fallan
  `camino`, `entrecortado`, `plano`, `emocion`, `url`, `vigencia`, `cita`,
  `organismo`, `afirmacion` — nueve campos que el prompt pide razonar y nadie
  lee. Se enchufan o se borran del esquema; quedarse a medias ya no es opción.
- **Un prompt que exige juzgar algo que no recibe.** `Campo.manda=None` con
  `Campo.exige` no vacío falla el build. Es el `libreto` de `repaso`, el `pilar`
  de `revalidar`, los `bordes` de `describir` y la fecha del render de `fuentes`.
- **Un dato que viaja y nadie mira.** `Campo.exige=()` con `manda` puesto es
  coste pagado y tirado: `en`, `esquirlas`, `repetido`, `fragmento_id`.
- **Que «pasa» se mida sobre lo aplicado.** Ver `Repeticion`.

    python scripts/contratos.py            # el parte: qué falta y qué es inerte
    python scripts/contratos.py --prompts  # renderiza los bloques compartidos

## Dónde está cada cosa

Esto era un solo fichero de 1.157 líneas de código con dos cosas de naturaleza
distinta dentro: el **vocabulario** —qué es un campo, qué es una aguja, cómo se
comprueba— y la **declaración** —los cuatro contratos, que son datos y son lo
que crece—. Ahora el motor vive en `scripts/contrato/` y no se toca al añadir un
campo; aquí queda la puerta, que es lo que corre `montar.sh` y lo que importan
los pasos.

    contrato/aguja.py      lo único que abre un fichero: `Aguja` y `Prompt`
    contrato/piezas.py     `Campo`, `Clave`, `Bloque`, `Momento`, `Repeticion`
    contrato/registro.py   los cuatro indexados, y `revisar()` contra el disco
    contrato/parte.py      lo que se imprime y lo que para la línea
    contrato/comun.py      lo que va en TODOS: redundancia, cumplimiento, `sube`
    contrato/corte/        1 · CORTE, el que se repite hasta que pase — el
                           único que no cabe en un fichero: colapsa tres fases,
                           así que su pedido y su respuesta van aparte
    contrato/componer.py   2 · COMPONE, el que define lo que va a haber
    contrato/respaldo.py   3 · RESPALDO, las fuentes de cada cifra
    contrato/diseno.py     4 · DISEÑO, el que lo monta, con las reglas de marca
"""
from __future__ import annotations

from contrato import (NADIE, Aguja, Bloque, Campo, Clave, Contrato, Momento,
                      Prompt, Registro, Repeticion, bloques, parte, plano)
from contrato.comun import CUMPLIMIENTO, REDUNDANCIA, SUBE
from contrato.componer import COMPONE
from contrato.corte import CORTE
from contrato.diseno import DISENO, MARCA
from contrato.respaldo import RESPALDO

#: El registro vivo. Las tres primeras fases del `CICLO` son el mismo contrato
#: en tres momentos: eso es el colapso, y es un dato. Y la cadena de
#: composición son dos —`descrito` define lo que va a haber y escribe el
#: encargo, `disenado` lo monta—, porque son dos tareas. `visto` es el segundo
#: momento del que monta: revisa lo que salió y lo lanza.
REGISTRO = Registro((CORTE, COMPONE, DISENO, RESPALDO),
                    (MARCA, REDUNDANCIA, CUMPLIMIENTO))

CONTRATOS: dict[str, Contrato] = REGISTRO.contratos
BLOQUES: dict[str, Bloque] = REGISTRO.bloques
POR_FASE: dict[str, Contrato] = REGISTRO.por_fase


def por_paso(paso: str) -> Contrato | None:
    return REGISTRO.por_paso(paso)


def momento(fase: str) -> tuple[Contrato, Momento] | None:
    return REGISTRO.momento(fase)


def campos_del_momento(fase: str) -> tuple[Campo, ...]:
    """Los campos que el payload TIENE que llevar en esa fase."""
    return REGISTRO.campos_del_momento(fase)


def revisar():
    """Las agujas que ya no estan. Es lo que separa un contrato de una promesa."""
    return REGISTRO.revisar()


def main():
    import sys

    if "--prompts" in sys.argv:
        bloques(REGISTRO)
        return
    parte(REGISTRO)


if __name__ == "__main__":
    main()
