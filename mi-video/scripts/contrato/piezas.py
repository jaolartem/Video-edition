"""Las piezas con las que se escribe un contrato. El vocabulario, no lo dicho.

Aquí no hay ni un dato de ninguna pieza: hay qué es un campo, qué es una clave,
qué es un bloque compartido, qué es un momento y qué es repetir hasta que pase.
Esto no cambia cuando cambia un contrato — y ésa es toda la razón de que viva
aparte de los cuatro ficheros que declaran.

Lo que se declara está en `corte.py`, `componer.py`, `respaldo.py` y
`diseno.py`; lo compartido por todos, en `comun.py`.
"""
from __future__ import annotations

import dataclasses
import hashlib

from .aguja import Aguja, Prompt, plano


# ─────────────────────────────────────────────────────────────────────────────
# Las tres piezas de un contrato
# ─────────────────────────────────────────────────────────────────────────────
@dataclasses.dataclass(frozen=True)
class Campo:
    """Un dato del payload.

    - `manda` — la línea que lo mete en el pedido. `None` = no viaja.
    - `exige` — las frases del prompt que dependen de él. Vacío = el prompt no
      lo usa, y entonces el dato es coste pagado y tirado.
    - `condicional` — cuándo NO viaja aunque `manda` exista. Un campo
      condicional obliga a que el prompt diga qué hacer cuando falta
      (`si_falta`), porque «te doy los números al lado de cada trozo» sin
      condiciones es una promesa que el código no cumple.
    - `une_con` — con qué clave de otra lista del payload se junta. Si no se
      declara, quien contesta tiene que adivinar la junta: `se_ve[].etapa_orden`
      con `montaje[].beat` no se dice en ningún sitio.
    """

    nombre: str
    manda: Aguja | None
    exige: tuple[Prompt, ...] = ()
    condicional: str = ""
    si_falta: Prompt | None = None
    une_con: str = ""
    en: tuple[str, ...] = ()          # momentos donde tiene que viajar; () = todos
    nota: str = ""
    # **Por que se exige y no se manda.** Un campo con `exige` y `manda=None`
    # es un prompt que pide juzgar algo que no recibe, y hasta hoy eso solo
    # salia como un numero en el parte —«exigidos y no enviados: 10»— con
    # codigo de salida 0. Llevaba meses ahi. `datos_respaldados` era uno de
    # ellos, y su precio fue que cinco de siete agentes subieran «cifra sin
    # fuente» el mismo dia teniendo 86 filas con su fuente en la base.
    #
    # Ahora hay que escribirlo: o se manda, o se dice por que no y que cuesta.
    # Lo que no se puede es quedar declarado y callado. **Un guarda que avisa y
    # sigue no es un guarda** — es la misma leccion de C-146 un piso mas arriba.
    deuda: str = ""


@dataclasses.dataclass(frozen=True)
class Clave:
    """Una clave de la respuesta.

    - `dispara` — la línea que la ejecuta. `NADIE` falla el build.
    - `adjunta_a` — prosa. Sólo vale colgada de una clave que sí ejecuta, y se
      guarda con ella. Un `por_que` suelto es un diagnóstico que muere.
    - `sin_valor` — cómo se dice «no me pronuncio». Sin esto, una lista cerrada
      obliga a inventar un valor por defecto, que es indistinguible de una
      decisión: `color: dejar` decidido y `color: dejar` por no saber.
    """

    nombre: str
    dispara: tuple[Aguja, ...]
    efecto: str
    obligatoria: bool = False
    adjunta_a: str = ""
    lista: tuple[str, ...] = ()
    sin_valor: str = ""
    exige_ademas: tuple[str, ...] = ()   # claves sin las cuales ésta no se aplica
    nota: str = ""


@dataclasses.dataclass(frozen=True)
class Bloque:
    """Prosa compartida por TODOS los contratos, escrita una vez.

    Jaime: *«redundancia y fuentes debe estar en todos los contratos»*. La
    manera cara de cumplirlo es pegar los mismos tres párrafos en cinco
    ficheros; a la tercera corrección, tres de los cinco dicen otra cosa y nadie
    sabe cuál manda.

    Aquí el texto vive una vez. Cada prompt lleva la marca
    `<!-- bloque:cumplimiento sha=... -->` y `--prompts` escribe el texto
    debajo. El verificador compara la huella: si alguien edita la copia, el
    build lo dice; si alguien edita el original, `--prompts` lo propaga a los
    cinco.
    """

    nombre: str
    texto: str
    campos: tuple[Campo, ...] = ()
    claves: tuple[Clave, ...] = ()

    def huella(self) -> str:
        return hashlib.sha1(plano(self.texto).encode("utf-8")).hexdigest()[:12]

    def marca(self) -> str:
        return f"<!-- bloque:{self.nombre} sha={self.huella()} -->"

    def fin(self) -> str:
        return f"<!-- /bloque:{self.nombre} -->"


@dataclasses.dataclass(frozen=True)
class Momento:
    """Cuándo se hace la misma pregunta. Tres veces, no tres preguntas.

    `no_trae` es la mitad importante: a las 5.5 todavía no existe una fila en
    `escena_desc` —`descrito` es la fase 7—, así que `compone: true` escribe un
    UPDATE que toca cero filas y se cuenta como aplicado. Un momento que no
    trae un campo obligatorio para una clave es esa clave inaplicable ahí.
    """

    fase: str
    orden: float
    trae: tuple[str, ...] = ()
    no_trae: tuple[str, ...] = ()
    nota: str = ""


@dataclasses.dataclass(frozen=True)
class Repeticion:
    """«Hasta que pase», leído de lo que la máquina ya hace.

    Ya existe todo: `Resultado.volver_a` manda la pieza atrás, `avanzar.py`
    cuenta las vueltas en `atras[fase]` y se planta a la cuarta, y `verificar.py`
    es la puerta que dice si la pieza está entera. Lo que faltaba es **qué
    cuenta como pasar**.

    Hoy se mide sobre lo aplicado: `repaso.py` imprime «pieza limpia, sin
    repeticiones» cuando `revision.aplicar` puso 0 cortes, lo mismo da que la
    respuesta fuera `[]` que quince cortes cuyas anclas no resuelven contra el
    montaje de hoy. O sea que el peor caso —el paso ve quince defectos y no
    consigue tocar ninguno— y el mejor caso son el mismo mensaje.

    `pasa_si` se mide sobre lo PROPUESTO. Y lo propuesto que no se pudo aplicar
    no es silencio: es `no_aplicado`, que sube.
    """

    vuelve_a: str
    cuenta: Aguja
    tope: int
    puerta: Aguja
    pasa_si: tuple[str, ...]
    no_pasa_por: tuple[str, ...]
    contadores: tuple[str, ...]
    nota: str = ""


@dataclasses.dataclass(frozen=True)
class Contrato:
    paso: str                       # carpeta de `work/servicio/<paso>/`
    prompt: str
    unidad: str
    llave: str
    momentos: tuple[Momento, ...]
    campos: tuple[Campo, ...]
    claves: tuple[Clave, ...]
    bloques: tuple[Bloque, ...]
    valida: Aguja
    envoltura: tuple[str, str] = ()
    repite: Repeticion | None = None
    nota: str = ""

    def campos_todos(self) -> tuple[Campo, ...]:
        return self.campos + tuple(c for b in self.bloques for c in b.campos)

    def claves_todas(self) -> tuple[Clave, ...]:
        return self.claves + tuple(k for b in self.bloques for k in b.claves)
