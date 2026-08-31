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
"""
from __future__ import annotations

import dataclasses
import hashlib
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


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
        return os.path.join(RAIZ, "mi-video", self.fichero)

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
            t = open(os.path.join(RAIZ, "mi-video", self.fichero),
                     encoding="utf-8").read()
        except OSError:
            return False
        return plano(self.frase).lower() in plano(t).lower()


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


# ═════════════════════════════════════════════════════════════════════════════
# Los dos bloques que van en TODOS los contratos
# ═════════════════════════════════════════════════════════════════════════════
#
# Y van con campos y con claves, no sólo con prosa. Ésa era la trampa de la
# versión anterior: los cinco prompts hablaban de cumplimiento y ninguno tenía
# dónde devolverlo, así que un dato sin respaldo se guardaba con la misma forma
# que un ajuste de color y el lote seguía.

SUBE = Clave(
    "sube",
    dispara=(Aguja("scripts/revision.py", "def anotar(slug, accion, desde, hasta, que, regla=None, estado=\"pendiente\"",
                   pendiente="llamar con estado='sube' cuando la respuesta trae `sube`;"
                             " el CHECK de la tabla ya lo admite y nadie lo usa"),
             Aguja("scripts/verificar.py", "def revisar(",
                   pendiente="la puerta cuenta las notas estado='sube' y para la pieza")),
    efecto="nota de revisión con estado='sube': la pieza no pasa la puerta hasta"
           " que Jaime la mire",
    lista=("cifra_sin_fuente", "cifra_contradicha", "precio_o_fecha_cambiada",
           "caso_no_documentado", "etapa_obligatoria_sin_material",
           "material_no_grabado"),
    nota="Es la clave que faltaba en los cinco pasos. Regla corta del proyecto:"
         " se consulta lo que cambia el mensaje, no lo que cambia la ejecución —"
         " y hasta ahora lo que cambia el mensaje no tenía dónde escribirse.",
)

REDUNDANCIA = Bloque(
    "redundancia",
    texto="""
**Nada se dice dos veces, y la repetición se recorta — no se penaliza.**

La repetición del bruto es un abanico para elegir, no basura: sobra UNA versión,
la que más comunique. Reconocerlo es predicción de lenguaje, no coincidencia de
n-gramas, y por eso lo decides tú y no Python.

Se mira en tres sitios, y son tres defectos distintos:

1. **Dentro de la ventana** — la misma idea dicha dos veces en el mismo trozo.
2. **Cruzando el corte** — la cola de un trozo y la cabeza del siguiente dicen
   lo mismo. Es del montaje, no del hablante.
3. **El mismo dato en dos etapas** — la cifra que ya se dio, repetida más tarde
   como si fuera nueva.

Y el freno, que pesa más que los tres: **si sin eso la etapa deja de hacer su
trabajo, no se corta aunque repita.** Una repetición que sostiene una etapa es
menos daño que una etapa que se queda sin sostener nada. Si al terminar tu lista
la pieza ha perdido una etapa entera del frame o el cierre, la lista está mal
aunque cada línea sea cierta — y eso se dice en `pieza.veredicto`, no callándose.
""",
    campos=(),
    claves=(),
)

CUMPLIMIENTO = Bloque(
    "cumplimiento",
    texto="""
**Cumplimiento manda sobre todo lo demás, también sobre la fuerza de la pieza.**

Nunca se inventa un caso, testimonio, resultado, cifra ni detalle personal —
tampoco para que la historia golpee más fuerte. Si lo que tienes delante presenta
como real algo que no consta que lo sea, eso no se arregla cortando: se sube.

Tres comprobaciones, en cada paso y sobre lo que ese paso tenga delante:

- **Cada cifra que se dice o se rotula tiene de dónde sale.** Si no la tienes
  respaldada aquí, no la des por buena: `sube: cifra_sin_fuente`.
- **El precio y la fecha son los de hoy.** Vienen en `precio_vigente`, con su
  ventana. Si la voz dice otro importe, u otra fecha de cierre, o el escalón está
  cerrado (`precio_vigente` llega `null`), la pieza no sale: `sube`.
- **Las cosas se llaman igual en toda la pieza.** El nombre del evento, el
  tratamiento de usted, el nombre del público. Dos nombres para lo mismo es un
  defecto de cumplimiento, no de estilo.

Lo que no es tuyo: **no corrijas la afirmación.** Qué se hace con un dato que no
se sostiene —cambiarlo, condicionarlo, quitar la etapa— cambia el mensaje, y eso
lo decide Jaime. Tu salida es la evidencia, y va en `sube`.
""",
    campos=(
        Campo("precio_vigente",
              manda=Aguja("scripts/servicios/repaso.py", "precio = _co.precio_vigente()"),
              exige=(Prompt("scripts/repaso.prompt.md", "El precio en voz coincide con el escalón"),),
              condicional="`None` si no hay escalón abierto **y también si la"
                          " llamada revienta**: los dos casos son el mismo dato",
              si_falta=Prompt("scripts/repaso.prompt.md", "sin escalón, la pieza no sale"),
              nota="{importe, hasta, vale, luego}. Es el único «contra qué» que"
                   " el paso tiene para comprobar el precio."),
        Campo("hoy",
              manda=None,
              exige=(Prompt("scripts/fuentes.prompt.md", "no respalda una cifra de hoy"),),
              nota="EXIGIDO Y NO ENVIADO. La fecha del render. Sin ella, «hoy»"
                   " es lo que el modelo suponga, y una vigencia se juzga contra"
                   " una fecha inventada."),
        Campo("evento",
              manda=None,
              exige=(Prompt("scripts/repaso.prompt.md", "El nombre del evento es uno solo"),
                     Prompt("scripts/repaso.prompt.md", "fecha del evento")),
              nota="EXIGIDO Y NO ENVIADO. {nombre, fecha}. Lo único que llega es"
                   " `precio_vigente.hasta`, que es el cierre del escalón —no la"
                   " fecha del evento— y no dice cómo se llama."),
        Campo("datos_respaldados",
              manda=None,
              une_con="etapa",
              exige=(Prompt("scripts/repaso.prompt.md", "las cifras y las promesas no se contradigan"),),
              nota="EXIGIDO Y NO ENVIADO. Lo que `fuentes` ya guardó en `dato`:"
                   " {etapa, cifra, respalda, condiciones}. Es literalmente la"
                   " instrucción de Jaime —fuentes en todos los contratos— y hoy"
                   " ningún paso ve lo que el paso de fuentes averiguó."),
    ),
    claves=(SUBE,),
)


# ═════════════════════════════════════════════════════════════════════════════
# 1 · CORTE — el paso que se repite hasta que pase
# ═════════════════════════════════════════════════════════════════════════════
#
# Aquí se colapsan `sin_redundancia` (5), `revalidado` (5.5) y `repasado` (6.5).
# No son tres pasos: son la misma pregunta —¿el corte dice lo que tiene que
# decir, entero y una sola vez?— hecha en tres puntos donde el corte ya cambió,
# con tres esquemas que no se parecen y que por eso se contradicen:
#
#   · redundancia ve `antes`/`despues` con sus segundos —los recibe desde
#     ccef7c5— y su esquema sólo sabe cortar. Ve el borde roto y la única salida
#     que tiene es cortar más.
#   · revalidar puede mover tramos y no puede decir de qué cinta son.
#   · repaso puede mover tramos y cortar, y no puede decir nada sin cortar.
#
# Y las tres cuentan «pasa» distinto. Un contrato, tres momentos.

CORTE = Contrato(
    paso="corte",
    prompt="scripts/corte.prompt.md",
    unidad="trozo de montaje (una fila por trozo del EDL, en orden de montaje)",
    llave="beat",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/servicio.py", "def recoger(",
                 pendiente="validar la respuesta contra contratos.por_paso(paso)"
                           " antes de devolverla; hoy el docstring promete «la"
                           " valida contra el esquema del paso» y hace json.load"),
    momentos=(
        Momento("sin_redundancia", 5.0,
                trae=("montaje", "texto", "antes", "despues", "voz", "tono"),
                no_trae=("se_ve", "onda", "candidatas", "historial"),
                nota="Sobre el corte recién depurado: es cuando la repetición es"
                     " más barata de quitar."),
        Momento("revalidado", 5.5,
                trae=("candidatas", "historial", "saltos", "flojo", "intensidad"),
                no_trae=("se_ve",),
                nota="`escena_desc` todavía no existe —`descrito` es la 7—, así"
                     " que aquí no se puede decidir nada que se escriba ahí. Es"
                     " el no-op de `compone`, que cuenta como aplicado y toca"
                     " cero filas."),
        Momento("repasado", 6.5,
                trae=("se_ve", "onda", "cierres_en_corpus", "precio_vigente"),
                no_trae=(),
                nota="Último punto donde el texto está cerrado y cortar todavía"
                     " es barato. Después de `descrito` invalida descripciones."),
    ),
    campos=(
        # ── lo que se oye ────────────────────────────────────────────────────
        Campo("montaje[].texto",
              manda=Aguja("scripts/redundancia.py", '"texto": " ".join(ws)'),
              exige=(Prompt("scripts/redundancia.prompt.md", "el texto de la pieza montada"),),
              nota="Sólo las palabras que suenan dentro del corte"
                   " (`transcribir.suena`). Es lo único que se puede juzgar de verdad."),
        Campo("montaje[].beat",
              manda=Aguja("scripts/redundancia.py", '"beat": det.get("beat")'),
              exige=(Prompt("scripts/redundancia.prompt.md", "la etapa sigue haciendo su trabajo"),),
              nota="La llave con la que vuelve todo."),
        Campo("montaje[].etapa",
              manda=Aguja("scripts/redundancia.py", '"etapa": det.get("etapa")'),
              exige=(Prompt("scripts/redundancia.prompt.md", "la etapa sigue haciendo su trabajo"),),
              nota="El título del frame. Es toda la descripción de su función que"
                   " hay, y con eso se pide juzgar si la etapa perdió la suya."),
        Campo("montaje[].toma",
              manda=Aguja("scripts/redundancia.py", '"toma": toma,'),
              exige=(Prompt("scripts/revalidar.prompt.md", "los segundos exactos"),),
              nota="De qué cinta son los segundos. Sin esto no se puede devolver"
                   " `tramos` honestos: es C-115."),
        Campo("montaje[].desde / .hasta",
              manda=Aguja("scripts/redundancia.py", '"desde": round(rango[0], 3), "hasta": round(rango[1], 3)'),
              exige=(Prompt("scripts/revalidar.prompt.md", "los segundos exactos"),)),
        Campo("montaje[].antes / .despues",
              manda=Aguja("scripts/redundancia.py", '"antes": _vecinas(cache[toma], rango[0], "antes")'),
              exige=(Prompt("scripts/repaso.prompt.md", "el borde no se estima"),),
              nota="16 palabras por lado con [empieza, acaba, palabra]. Es medio"
                   " contrato: el borde no se estima, se copia el `empieza`."),
        Campo("montaje[].voz / .tono",
              manda=Aguja("scripts/redundancia.py", 'fila["voz"] = round('),
              exige=(Prompt("scripts/redundancia.prompt.md", "más voz y más cambio de tono"),),
              condicional="sólo si el trozo dura más de 0,6 s Y `beats.expresividad`"
                          " no lanza (el except es silencioso)",
              si_falta=Prompt("scripts/corte.prompt.md", "si un trozo llega sin `voz` ni `tono`"),
              nota="El prompt promete «te doy los números medidos al lado de cada"
                   " trozo» sin condiciones, y el código pone dos."),
        Campo("montaje[].en",
              manda=Aguja("scripts/redundancia.py", '"en": round(t, 1)'),
              exige=(),
              nota="INERTE POR EL OTRO LADO: viaja y ningún prompt lo nombra. El de"
                   " redundancia además declara lo contrario —«el ancla es texto y"
                   " no segundos a propósito»—. O se usa para ordenar la lista, o"
                   " se quita."),
        # ── lo que se mide ───────────────────────────────────────────────────
        Campo("intensidad",
              manda=Aguja("scripts/revalidar.py", '"intensidad": inten.get("intensidad")'),
              exige=(Prompt("scripts/revalidar.prompt.md", "la medida que manda"),),
              en=("revalidado", "repasado"),
              nota="OJO: el dossier PISA con la del span la que `medir` calcula"
                   " ponderada por trozo conservado. El prompt la describe como"
                   " lo conservado y el número que llega es el otro; y `flojo` se"
                   " calcula sobre la ponderada, así que puede llegar"
                   " `flojo: ['intensidad']` junto a una intensidad por encima de 1,2."),
        Campo("altura / velocidad",
              manda=Aguja("scripts/revalidar.py", '"altura": inten.get("altura")'),
              exige=(Prompt("scripts/revalidar.prompt.md", "si hablo de muerte no quiero estar cagado de la risa"),),
              en=("revalidado", "repasado")),
        Campo("saltos",
              manda=Aguja("scripts/revalidar.py", '"saltos": saltos(toma, pal, d["tramos"], ultimo)'),
              exige=(Prompt("scripts/revalidar.prompt.md", "lo que se oye AL CRUZAR cada costura"),),
              en=("revalidado", "repasado"),
              nota="Cada salto con su `donde`, su `en`, su `tono` y su `ritmo`."),
        Campo("flojo / esquirlas",
              manda=Aguja("scripts/revalidar.py", '"flojo": flojo(m)'),
              exige=(),
              en=("revalidado",),
              nota="INERTE: cero apariciones en el prompt de revalidar. `flojo` es"
                   " el cálculo del suelo ya hecho y el prompt pide aplicarlo a mano."),
        Campo("onda",
              manda=Aguja("scripts/servicios/repaso.py", "curva = consulta.onda(pieza.slug)"),
              exige=(Prompt("scripts/repaso.prompt.md", "arriba, luego abajo, luego arriba"),),
              en=("repasado",),
              condicional="si la llamada revienta se manda `[]` en silencio",
              si_falta=Prompt("scripts/corte.prompt.md", "si `onda` llega vacía"),
              nota="Trae `tibio` ya calculado con el umbral 1,2 que el prompt pide"
                   " aplicar a mano, y no lo nombra."),
        # ── lo que se ve ─────────────────────────────────────────────────────
        Campo("se_ve",
              manda=Aguja("scripts/servicios/repaso.py",
                          "select etapa_orden, remedio, trato, componente, grafico,"),
              exige=(Prompt("scripts/repaso.prompt.md", "lo que se oye contra lo que se ve"),),
              en=("repasado",),
              une_con="beat",
              condicional="si la base falla se manda `[]` y el contrato sigue"
                          " pidiendo juzgar lo que se ve",
              si_falta=Prompt("scripts/corte.prompt.md", "si `se_ve` llega vacía"),
              nota="`etapa_orden` es la ÚNICA junta con `montaje[].beat` y ningún"
                   " prompt dice que se unen por ahí."),
        Campo("se_ve[].dura_en_pantalla",
              manda=None,
              exige=(Prompt("scripts/repaso.prompt.md", "da tiempo a leerse"),),
              en=("repasado",),
              nota="EXIGIDO Y NO ENVIADO. `se_ve` no trae duración ni cantidad de"
                   " texto, y `montaje` da segundos de cinta, no de permanencia"
                   " del gráfico. El caso fundacional del paso —reel-01, segundo"
                   " 30— es exactamente éste."),
        Campo("subtitulo",
              manda=None,
              exige=(Prompt("scripts/repaso.prompt.md", "voz, subtítulo y"),),
              en=("repasado",),
              nota="EXIGIDO Y NO ENVIADO. Se pide que las cifras no se contradigan"
                   " entre voz, subtítulo y tablero, y el subtítulo no viaja."),
        # ── lo que la pieza quería decir ─────────────────────────────────────
        Campo("libreto",
              manda=None,
              exige=(Prompt("scripts/repaso.prompt.md", "el libreto quería decir"),
                     Prompt("scripts/revalidar.prompt.md", "del libreto y del texto")),
              nota="EXIGIDO Y NO ENVIADO, y es la definición misma de congruencia."
                   " El EDL trae `de_jaime`, `dice`, `cobertura` y `literal`, y"
                   " ninguno se reenvía. No hay contra qué comparar."),
        Campo("estructura",
              manda=Aguja("scripts/servicios/repaso.py", '"estructura": (pieza.edl or {}).get("estructura")'),
              exige=(Prompt("scripts/redundancia.prompt.md", "PAS sin problema o sin activación"),),
              nota="Valores reales: 'Polarizing Thesis', 'Belief Demolition',"
                   " 'Two Paths / Default Loss'. El prompt de repaso afirma en"
                   " duro «estas piezas son SELL» con una tabla de cuatro arcos"
                   " donde ninguno de ésos aparece, y el de redundancia razona"
                   " sobre PAS sin recibir el arco."),
        Campo("pilar / cta / enunciados",
              manda=None,
              exige=(Prompt("scripts/revalidar.prompt.md", "El nombre de las cosas"),),
              nota="EXIGIDO Y NO ENVIADO. El EDL los tiene y `revalidar.dossier`"
                   " los lee y los tira."),
        Campo("cierres_en_corpus",
              manda=Aguja("scripts/servicios/repaso.py", "cierres = redundancia.cierres_en_corpus()"),
              exige=(Prompt("scripts/repaso.prompt.md", "elige uno de ahí"),),
              en=("repasado",),
              condicional="si falla se manda `[]` y el prompt sigue diciendo"
                          " «elige uno de ahí»",
              si_falta=Prompt("scripts/corte.prompt.md", "si no llega ningún cierre")),
        Campo("candidatas",
              manda=Aguja("scripts/revalidar.py", '"candidatas": candidatas(slug, beat)'),
              exige=(Prompt("scripts/revalidar.prompt.md", "revisa los candidatos con sus puntuaciones"),),
              en=("revalidado",),
              nota="Máximo 3, y su `texto` va TRUNCADO a 400 caracteres — con el"
                   " tuteo del cierre como descalificador duro, en una candidata"
                   " larga el final se corta antes de llegar. `puntuacion` puede"
                   " ser `null` a propósito y el prompt la asume presente."),
        Campo("abanico",
              manda=None,
              exige=(Prompt("scripts/revalidar.prompt.md", "no se salta un peldaño"),),
              en=("revalidado", "repasado"),
              nota="EXIGIDO Y NO ENVIADO. El peldaño 2 ordena buscar en las siete"
                   " cintas con `consulta.py abanico`. Quien contesta por fichero"
                   " no puede ejecutar un comando: o viaja el resultado, o el"
                   " peldaño 2 no existe."),
        Campo("tramos_actuales",
              manda=None,
              exige=(Prompt("scripts/revalidar.prompt.md", "qué edición la salva"),),
              en=("revalidado",),
              nota="EXIGIDO Y NO ENVIADO. Se pide mover la costura y del montaje"
                   " sólo llega el span (`desde`/`hasta` = min y max) más el"
                   " contador `trozos`. Dónde están hoy las costuras, no."),
        Campo("vuelta",
              manda=None,
              exige=(Prompt("scripts/repaso.prompt.md", "ya dio tres vueltas"),),
              nota="EXIGIDO Y NO ENVIADO. Quien cuenta las vueltas es `avanzar.py`"
                   " y no se lo dice a quien contesta. El código escribe siempre"
                   " `pasada=2`."),
    ),
    claves=(
        Clave("beat",
              dispara=(Aguja("scripts/servicios/repaso.py", "beat = b.get(\"beat\")"),
                       Aguja("scripts/servicios/revalidar.py", "beat = v.get(\"beat\")")),
              efecto="enruta el elemento a su etapa",
              obligatoria=True,
              nota="Sin él la fila se descarta con `continue`, sin aviso."),
        Clave("ancla",
              dispara=(Aguja("scripts/redundancia.py", 'revision.anotar(slug, "cortar", None, None,'),
                       Aguja("scripts/revision.py", "def _por_ancla(")),
              efecto="nota `cortar` en `revision`, que `revision.aplicar` recorta"
                     " del EDL buscando ese texto sobre el montaje de hoy",
              exige_ademas=("por_que",),
              nota="Único campo obligatorio de un corte. `cargar` manda siempre"
                   " desde=None y hasta=None: lo que no se pueda anclar en texto"
                   " exacto no se puede cortar."),
        Clave("cual",
              dispara=(Aguja("scripts/revision.py", "def _por_ancla("),),
              efecto="salta apariciones hasta la enésima al aplicar",
              sin_valor="1",
              nota="Se cuenta sobre el montaje entero y el payload viene troceado"
                   " por segmento: contar apariciones globales es reconstrucción"
                   " del lector, no un dato. Lo arregla `montaje[].en`, que ya viaja."),
        Clave("tramos",
              dispara=(Aguja("scripts/servicios/repaso.py",
                             "vd = fijar.declarar(pieza.slug, int(beat), toma, tramos,"),
                       Aguja("scripts/servicios/revalidar.py",
                             "vd = fijar.declarar(pieza.slug, beat, toma, nuevos,")),
              efecto="declara el tramo por `fijar`, que lo mide y lo deja escrito"
                     " en `corte_fijo`; sobrevive a que la selección se rehaga",
              exige_ademas=("toma", "por_que"),
              nota="Es la única clave que cambia el montaje. Si `declarar` dice"
                   " «peor» se avisa y SE APLICA IGUAL."),
        Clave("toma",
              dispara=(Aguja("scripts/servicios/revalidar.py", 'toma = v.get("toma") or next('),),
              efecto="fija de qué cinta son los segundos de `tramos`",
              obligatoria=True,
              exige_ademas=("tramos",),
              nota="EL PROMPT NO LA OFRECE y el código la lee. Con `tramos` cae"
                   " siempre al fallback del EDL, así que material traído de otra"
                   " cinta —que es lo que ordena el peldaño 2— se declara con el"
                   " nombre de la cinta del montaje. C-115 reabierto por el esquema."),
        Clave("elegida",
              dispara=(Aguja("scripts/servicios/revalidar.py", 'int(v.get("elegida") or 1) != 1'),),
              efecto="sustituye el tramo por el de esa candidata",
              sin_valor="1",
              nota="`elegida: 1` es indistinguible de «no cambies», y el prompt"
                   " afirma «1 es la actual», que sólo es cierto si el montaje"
                   " coincide con el puesto 1 — deja de serlo en cuanto `fijar`"
                   " toca la etapa."),
        Clave("falso_positivo",
              dispara=(Aguja("scripts/servicios/revalidar.py", "insert or replace into descartado"),
                       Aguja("scripts/seleccionar.py",
                             "select etapa_orden, desde, hasta from descartado where video_slug = ?")),
              efecto="descarta ese tramo para que la selección tome la siguiente"
                     " candidata",
              exige_ademas=("desde", "hasta"),
              nota="Hoy es inerte de facto: el prompt no pide `desde`/`hasta`, la"
                   " fila entra como (0,0) y `seleccionar` casa por"
                   " `abs(a-desde) < 0.3` — nunca casa. La etapa marcada mala se"
                   " vuelve a elegir en la corrida siguiente."),
        Clave("desde / hasta",
              dispara=(Aguja("scripts/servicios/revalidar.py",
                             'v.get("desde") or 0, v.get("hasta") or 0'),),
              efecto="los segundos concretos del descarte",
              exige_ademas=("falso_positivo",)),
        Clave("costura_mala",
              dispara=(Aguja("scripts/costuras.py", "and componente is not null",
                             pendiente="leer la costura señalada (beat + `en`) y"
                                       " moverla o disimularla; hoy `costuras.py`"
                                       " sólo mira `escena_desc.componente`"),),
              efecto="mueve o disimula esa costura",
              nota="Sustituye a `entrecortado`, que era un booleano por etapa: los"
                   " `saltos` llegan uno a uno con su `en` y su `donde`, y la"
                   " respuesta no podía señalar ninguno. Su docstring decía «se"
                   " marca la costura para que costuras.py la mueva» y"
                   " `costuras.py` no lee nada de este paso."),
        Clave("por_que",
              dispara=(Aguja("scripts/redundancia.py", "c.get('por_que') or 'redundancia'"),
                       Aguja("scripts/servicios/repaso.py",
                             'b.get("por_que") or "borde movido en el repaso"')),
              efecto="se guarda con la nota o con la declaración",
              adjunta_a="ancla|tramos|falso_positivo",
              obligatoria=True,
              nota="Es prosa y por eso va COLGADA: un `por_que` que no acompaña a"
                   " una clave ejecutable es un diagnóstico que muere. El prompt"
                   " le pide lo más caro —de qué paso anterior vino el fallo— y"
                   " ningún paso lo lee después."),
        Clave("de_donde",
              dispara=(Aguja("scripts/servicios/revalidar.py", "def aplicar(pieza: Pieza, veredictos) -> str:",
                             pendiente="cuando el elemento trae `de_donde`"
                                       " {toma, desde, hasta}, declararlo por"
                                       " `fijar` con ESA cinta"),),
              efecto="trae material de otra cinta a esta etapa",
              nota="Es el peldaño 2 hecho clave. Sin esto, «la versión buena está"
                   " en otra toma» sólo se puede decir en prosa."),
        Clave("peldano",
              dispara=(Aguja("scripts/registro.py", "def aviso(",
                             pendiente="registrar el peldaño usado por etapa: es"
                                       " lo que distingue «se arregla montando»"
                                       " de «hay que volver a grabar»"),),
              efecto="queda registrado con qué se resolvió la etapa",
              lista=("candidatas", "corpus", "tablero"),
              nota="El prompt lo exige literalmente —«se dice en la respuesta cuál"
                   " de los tres peldaños se usó»— en dos ficheros, y no hay clave"
                   " en ninguno de los dos."),
        # ── el objeto de pieza: decir algo sin cortar ────────────────────────
        Clave("pieza.veredicto",
              dispara=(Aguja("scripts/servicios/base.py", "volver_a: str = \"\"",
                             pendiente="del veredicto sale `volver_a` y el motivo,"
                                       " en vez de deducirlo de cuántos cortes se"
                                       " aplicaron"),),
              efecto="decide si la pieza pasa, vuelve a coser o para",
              obligatoria=True,
              lista=("limpia", "corregida", "rota"),
              nota="Es la clave que arregla el fallo de fondo: `[]` y"
                   " `[]`-con-diagnóstico eran el mismo fichero, y el consumidor"
                   " imprimía «pieza limpia, sin repeticiones» para los dos."),
        Clave("pieza.falta",
              dispara=(Aguja("scripts/verificar.py", "def revisar(",
                             pendiente="la puerta lee lo que el paso declaró que"
                                       " falta y lo cuenta como motivo"),),
              efecto="para la pieza en la puerta",
              lista=("etapa", "cta", "precio", "fuente"),
              nota="«Si al terminar tu lista la pieza ha perdido una etapa entera,"
                   " la lista está mal» — el prompt lo exige y no había dónde"
                   " retirar ni condicionar la lista entera."),
        Clave("pieza.nota",
              dispara=(Aguja("scripts/servicios/base.py", "salida: str = \"\"",),),
              efecto="sale en el parte del motor",
              adjunta_a="pieza.veredicto"),
    ),
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=Repeticion(
        vuelve_a="cosido",
        cuenta=Aguja("scripts/avanzar.py", 'atras.setdefault(siguiente["nombre"], []).append('),
        tope=3,
        puerta=Aguja("scripts/verificar.py", "def revisar("),
        pasa_si=("propuestos == 0",
                 "sube == 0",
                 "pieza.veredicto == 'limpia'",
                 "la puerta no devuelve motivos"),
        no_pasa_por=("aplicados == 0",),
        contadores=("propuestos", "aplicados", "no_aplicados", "sube"),
        nota="`no_aplicados` —anclas que no resuelven, tramos que `declarar`"
             " rechaza, bordes sin toma— NO es silencio: es el peor caso, y hoy"
             " se cuenta igual que la pieza limpia. Sube.",
    ),
)


# ═════════════════════════════════════════════════════════════════════════════
# 2 · COMPONE — describir, con lo que `revalidar` decidía por duplicado
# ═════════════════════════════════════════════════════════════════════════════
#
# `revalidar.camino` y `describir.trato` son la MISMA lista de cinco valores
# decidida en dos pasos distintos: uno de los dos se tira (`camino` tiene cero
# lecturas en todo el repo) y el otro se pide dos fases después. Aquí hay un
# solo sitio donde se decide cómo se ve una etapa.

COMPONE = Contrato(
    paso="describir",
    prompt="scripts/describir.prompt.md",
    unidad="etapa, con la pieza entera delante",
    llave="etapa_orden",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/describir.mjs", "const CAMPOS = {"),
    momentos=(Momento("descrito", 7.0),),
    campos=(
        Campo("etapas",
              manda=Aguja("scripts/describir.mjs", "`Reel: ${slug} — ${filas.length} etapas, en orden.`"),
              exige=(Prompt("scripts/describir.prompt.md", "el contexto es el video en general"),),
              nota="La unidad de la llamada es la pieza porque la segunda variable"
                   " —lo que la pieza necesita— no existe a nivel de etapa."),
        Campo("portada",
              manda=Aguja("scripts/describir.mjs", 'portada = edl.detalle?.find((d) => d.trato === "portada")?.beat'),
              exige=(Prompt("scripts/describir.prompt.md", "el gancho"),),
              condicional="si el EDL no existe, el catch deja la línea vacía",
              si_falta=Prompt("scripts/describir.prompt.md", "sin portada marcada"),
              nota="Sin ella el modelo elige `trato:'portada'` a ciegas y `valida`"
                   " lo acepta en cualquier etapa o en ninguna."),
        Campo("libreto",
              manda=Aguja("scripts/describir.mjs", '"Libreto:",'),
              exige=(Prompt("scripts/describir.prompt.md", "la intención comunicativa"),),
              nota="Trae el `[pausa]`. Una etapa sin libreto no entra al paso:"
                   " `escenas_por_describir` filtra `where l.texto is not null`."),
        Campo("mensaje",
              manda=Aguja("scripts/describir.mjs", '`Funcion: ${f.mensaje ?? "(no declarada)"}`'),
              exige=(Prompt("scripts/describir.prompt.md", "qué función cumple cada una"),)),
        Campo("dicho",
              manda=Aguja("scripts/describir.mjs", '"Lo que de verdad se dijo:"'),
              exige=(Prompt("scripts/describir.prompt.md", "la intención comunicativa"),),
              nota="`montaje || dicho`: lo que el montaje dice hoy, no lo que se"
                   " eligió. Son cosas distintas en cuanto un recorte toca la etapa."),
        Campo("etapa",
              manda=Aguja("scripts/consulta.py", "def escenas_por_describir("),
              exige=(Prompt("scripts/describir.prompt.md", "qué función cumple cada una"),),
              nota="Puede llegar literalmente `null`: el LEFT JOIN a"
                   " `etapa_canonica` empareja por `ec.orden = e.etapa_orden`"
                   " mientras todo lo demás del paso usa `e.orden`."),
        Campo("bordes",
              manda=None,
              exige=(Prompt("scripts/describir.prompt.md", "Cada etapa puede traer una lista"),),
              nota="EXIGIDO Y NO ENVIADO, y el dato EXISTE: `escenas_por_describir`"
                   " lo calcula y lo adjunta a cada fila, y `describePieza` no lo"
                   " copia a `entrada`. La cadena `bordes` no aparece ni una vez"
                   " en describir.mjs. Coste pagado y tirado."),
        Campo("segundos",
              manda=None,
              exige=(Prompt("scripts/describir.prompt.md", "con los segundos exactos"),),
              nota="EXIGIDO Y NO ENVIADO. El payload no lleva un solo segundo: ni"
                   " inicio, ni fin, ni duración — y el prompt razona sobre tiempo"
                   " de lectura y pide devolver `tramos`."),
        Campo("candidatas",
              manda=None,
              exige=(Prompt("scripts/describir.prompt.md", "no se salta un peldaño"),),
              nota="EXIGIDO Y NO ENVIADO. `remedio: 'recuperar'` presupone saber"
                   " qué más se grabó y el payload manda un único texto por etapa."),
        Campo("cruces",
              manda=None,
              exige=(Prompt("scripts/describir.prompt.md", "Lo que se repite en la costura"),),
              nota="EXIGIDO Y NO ENVIADO. `consulta.cruces` existe y no viaja."),
        Campo("repetido",
              manda=Aguja("scripts/consulta.py", "def repetido(slug, n=3):"),
              exige=(),
              nota="INERTE: se calcula por etapa en cada corrida, `describePieza`"
                   " no lo copia y el prompt no lo nombra."),
    ),
    claves=(
        Clave("etapa_orden",
              dispara=(Aguja("scripts/describir.mjs", "new Map(ds.map((d) => [Number(d.etapa_orden), d]))"),),
              efecto="enruta el objeto a su fila",
              obligatoria=True,
              nota="No se guarda: la fila se escribe con `f.orden`, el número del"
                   " código."),
        Clave("que_pasa",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):"),),
              efecto="`escena_desc.que_pasa`, y de ahí al payload del corte",
              obligatoria=True),
        Clave("trato",
              dispara=(Aguja("scripts/trato.py", "select trato, trato_porque from escena_desc"),),
              efecto="impone el tratamiento del segmento por encima de la heurística",
              obligatoria=True,
              lista=("portada", "tablero", "cercano", "metafora", "diapositiva"),
              nota="Absorbe `revalidar.camino`, que es la misma lista y tiene cero"
                   " lecturas en el repo."),
        Clave("trato_porque",
              dispara=(Aguja("scripts/trato.py", "select trato, trato_porque from escena_desc"),),
              efecto="queda escrito para poder discutirlo después",
              adjunta_a="trato"),
        Clave("prioridad",
              dispara=(Aguja("scripts/seleccionar.py",
                             'manda_limpieza = (prioridades or {}).get(s0 + 1) == "limpieza"'),),
              efecto="cambia qué toma gana en la selección",
              lista=("entrega", "limpieza"),
              nota="La clave con el efecto más fuerte sobre el corte final."),
        Clave("componente",
              dispara=(Aguja("scripts/caminos.mjs", "componente: desc?.componente ?? null,"),
                       Aguja("scripts/costuras.py", "and componente is not null")),
              efecto="pone el tablero en los props y marca qué etapas componen",
              lista=("CausalChain", "TwoPaths", "BeliefSwap", "ThenNow",
                     "EvidenceCard", "ComparisonTable"),
              sin_valor="ninguno",
              nota="`ninguno` se guarda como NULL, así que «no hace falta tablero»"
                   " y «no lo dijo» quedan indistinguibles en la base. `sin_valor`"
                   " tiene que guardarse como valor, no como ausencia."),
        Clave("grafico",
              dispara=(Aguja("scripts/caminos.mjs", "export const figuraDe = (grafico) => {"),),
              efecto="la figura dibujable o la composición tipográfica; sin ella"
                     " el gancho falla",
              obligatoria=True),
        Clave("color",
              dispara=(Aguja("scripts/caminos.mjs", "const desaturaDe = (color) =>"),),
              efecto="desatura la escena del tablero",
              lista=("avivar", "apagar"),
              sin_valor="dejar",
              nota="`dejar` por defecto era indistinguible de `dejar` decidido."),
        Clave("sonido",
              dispara=(Aguja("scripts/caminos.mjs", "export const sonidoDe = (sonido) => {"),),
              efecto="el movimiento sonoro de la capa",
              nota="Texto libre: lo que `sonidoDe` no reconozca cae en silencio."
                   " O es lista cerrada, o `sonidoDe` avisa."),
        Clave("corrige",
              dispara=(Aguja("scripts/reels-spec.mjs", "select corrige_dice, corrige_es from escena_desc"),
                       Aguja("scripts/fuentes.py", "d.corrige_dice, d.corrige_es")),
              efecto="coloca la corrección sobre la línea de CC y falla el build"
                     " si no encuentra las palabras",
              nota="NO ESTÁ EN `CAMPOS`: no se valida, no se exige, y una"
                   " respuesta sin `corrige` pasa la puerta sin aviso. Y es un"
                   " único par {dice, es}: dos contradicciones en la misma etapa"
                   " y la segunda se pierde."),
        Clave("integridad",
              dispara=(Aguja("scripts/verificar.py", "def revisar(",
                             pendiente="si `integridad` dice que el mensaje no"
                                       " llega, la etapa no se da por descrita:"
                                       " hoy se guarda y cuenta en `ok` igual"),),
              efecto="para la etapa cuando el mensaje no llega",
              nota="Hoy `verificar.py` la selecciona y no la usa."),
        Clave("remedio",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):"),),
              efecto="qué hacer con la etapa incompleta",
              lista=("recuperar", "tablero", "cortar"),
              sin_valor="ninguno",
              exige_ademas=("de_donde",),
              nota="`recuperar` sin `de_donde` es «esto se dijo en otra parte» sin"
                   " poder decir dónde. `revalidar` lo sobrescribe con"
                   " `coalesce(remedio,'tablero')` desde una fase anterior."),
        Clave("de_donde",
              dispara=(Aguja("scripts/consulta.py", "def guardar_escena(slug, orden, d):",
                             pendiente="columnas `recupera_toma`, `recupera_desde`,"
                                       " `recupera_hasta` y declaración por `fijar`"),),
              efecto="de qué cinta y qué segundos se recupera",
              exige_ademas=("remedio",)),
        Clave("plano",
              dispara=(NADIE,),
              efecto="—",
              lista=("en cuadro", "cerrado", "fuera"),
              nota="INERTE: lista cerrada validada en `describir.mjs`, guardada en"
                   " la base y ninguna línea del proyecto la lee después."),
        Clave("emocion",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE: el prompt exige que sea concreta —«alarma contenida»,"
                   " no «negativa»— y nada comprueba ni consume esa concreción."),
        Clave("pieza.veredicto",
              dispara=(Aguja("scripts/describir.mjs", "process.exit(1)",
                             pendiente="un objeto de pieza: tres tableros seguidos"
                                       " o un orden que no sostiene el argumento"
                                       " no caben en un array por etapa"),),
              efecto="para la pieza entera",
              lista=("compone", "rota")),
    ),
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=None,
    nota="Lo único que para de verdad hoy es `sinAfinar` al 95%: el contenido no"
         " se juzga en ningún sitio, y una etapa con `integridad` diciendo que el"
         " mensaje no llega se cuenta en `ok` igual que una entera.",
)


# ═════════════════════════════════════════════════════════════════════════════
# 3 · RESPALDO — fuentes, que además deja de ser un script que nadie llama
# ═════════════════════════════════════════════════════════════════════════════
#
# `fuentes.py` no está en `CICLO` ni en la tabla `fase`, y no lo llama
# `pipeline.sh` ni ningún otro script. Un paso de cumplimiento que no corre es
# peor que no tenerlo: `reels-spec.mjs` deja el literal escrito a mano cuando no
# hay `respalda='si'`, así que la ausencia se ve exactamente igual que el éxito.

RESPALDO = Contrato(
    paso="fuentes",
    prompt="scripts/fuentes.prompt.md",
    unidad="cifra en pantalla",
    llave="etapa",
    envoltura=("pieza", "elementos"),
    valida=Aguja("scripts/servicio.py", "def recoger(",
                 pendiente="misma validación que los demás pasos"),
    momentos=(Momento("respaldado", 7.5,
                      trae=("grafico", "trato"),
                      nota="Después de `descrito` porque necesita `grafico`, y"
                           " antes de `cortado` porque `respalda='si'` es lo que"
                           " enciende el pie del tablero."),),
    campos=(
        Campo("etapa",
              manda=Aguja("scripts/fuentes.py", '"etapa": f["orden"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "el número de etapa donde sale"),)),
        Campo("libreto",
              manda=Aguja("scripts/fuentes.py", '"libreto": f["libreto"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "lo que decía el libreto"),)),
        Campo("trato / grafico",
              manda=Aguja("scripts/fuentes.py", '"grafico": f["grafico"]'),
              exige=(Prompt("scripts/fuentes.prompt.md", "qué se va a dibujar"),),
              nota="Una cifra dibujada pesa más que una dicha: la del tablero se"
                   " queda en pantalla y se puede congelar y compartir."),
        Campo("cifras",
              manda=Aguja("scripts/fuentes.py", "cifras = sorted(set(m.group(0).strip() for m in CIFRA.finditer(texto)))"),
              exige=(Prompt("scripts/fuentes.prompt.md", "tal como sale en la pieza"),),
              nota="Derivada de un regex sobre libreto+grafico. El prompt pide la"
                   " cifra «tal como sale en la pieza» como si el modelo la"
                   " buscara, y `cargar` no comprueba que la devuelta estuviera"
                   " en la lista: en `dato` hay filas —«la mitad (50%)», «sin"
                   " cifra en pantalla (rotulo COMISION)»— que el regex no mandó."),
        Campo("dicho",
              manda=None,
              exige=(Prompt("scripts/fuentes.prompt.md", "tal como sale en la pieza"),),
              nota="EXIGIDO Y NO ENVIADO. Una cifra dicha y no rotulada no llega:"
                   " el propio `dato` id 6 lo registra —«en la toma se dice hasta"
                   " 550 dólares»— y esa cifra no estaba en el payload."),
        Campo("slug",
              manda=None,
              exige=(),
              nota="NO ENVIADO Y NECESARIO: está en el `.pedido.json` y `_por_cli`"
                   " concatena sólo `prompt` + `datos`. El modelo no ve de qué"
                   " reel es lo que juzga."),
        Campo("provincia",
              manda=None,
              exige=(Prompt("scripts/fuentes.prompt.md", "provincia, tipo"),),
              nota="EXIGIDO Y NO ENVIADO. Va fijada como Ontario en el texto del"
                   " prompt, no como dato de la pieza — o sea, un `if (slug ===`"
                   " escrito en prosa."),
        Campo("caso_real",
              manda=None,
              exige=(Prompt("scripts/fuentes.prompt.md", "si no consta que sea real"),),
              nota="EXIGIDO Y NO ENVIADO. Ningún campo dice si el electricista de"
                   " Brampton está documentado; el modelo lo deduce del libreto."),
        Campo("ya_guardado",
              manda=None,
              exige=(),
              nota="NO ENVIADO Y NECESARIO: el upsert sobrescribe, y en la base hay"
                   " filas de la misma pieza con fechas distintas y veredictos"
                   " distintos. Sin ver lo anterior no se puede saber si esto es"
                   " una corrección o una regresión."),
    ),
    claves=(
        Clave("etapa",
              dispara=(Aguja("scripts/reels-spec.mjs", "d.etapa_orden = ?"),),
              efecto="engancha el pie al beat",
              obligatoria=True,
              nota="Si falta o no es número entra como 0: la fila se guarda, no"
                   " engancha con ningún beat y no salta nada."),
        Clave("cifra",
              dispara=(Aguja("scripts/fuentes.py", "insert into dato (video_id, etapa_orden, cifra, afirmacion,"),),
              efecto="parte de la clave única del dato y desempate del pie",
              obligatoria=True,
              nota="Se lee por índice, no con `.get`: si falta, KeyError a mitad"
                   " del bucle y se pierde la carga entera porque el commit es al"
                   " final."),
        Clave("principal",
              dispara=(Aguja("scripts/reels-spec.mjs", "order by length(d.cifra) desc limit 1",
                             pendiente="ordenar por `principal` y no por longitud"
                                       " de la cadena"),),
              efecto="cuál de las cifras de la etapa lleva el pie del tablero"),
        Clave("fuente",
              dispara=(Aguja("scripts/reels-spec.mjs", "const pieDe = (beat) => {"),),
              efecto="el pie del tablero en pantalla, sólo si `respalda='si'`",
              nota="El upsert es por `rotulo` UNIQUE: dos fuentes distintas con el"
                   " mismo rótulo se funden en una fila."),
        Clave("condiciones",
              dispara=(Aguja("scripts/reels-spec.mjs", "const pieDe = (beat) => {"),),
              efecto="`props.condicion` del tablero",
              nota="Prosa larga de comprobación entrando directa a un pie: en la"
                   " base hay `condiciones` de 400+ caracteres. O se corta aquí"
                   " con su límite declarado, o llega a pantalla."),
        Clave("respalda",
              dispara=(Aguja("scripts/reels-spec.mjs", "d.respalda = 'si'"),
                       Aguja("scripts/fuentes.py", "def sin_respaldo(slug):")),
              efecto="enciende el pie y alimenta el listado de sin respaldo",
              obligatoria=True,
              lista=("si", "parcial", "no", "sin_fuente"),
              exige_ademas=("sube",),
              nota="`no` y `sin_fuente` caen en el mismo cubo y ninguno para nada,"
                   " y el propio prompt dice que `no` sube a Jaime. `parcial` es"
                   " invisible por los dos lados: no sale en el listado y no"
                   " imprime pie, así que el tablero se queda con el literal"
                   " escrito a mano sin que nadie lo vea. Por eso `respalda`"
                   " exige `sube`."),
        Clave("marcar_como",
              dispara=(Aguja("scripts/reels-spec.mjs", "const pieDe = (beat) => {",
                             pendiente="rotular HIPOTÉTICO / EJEMPLO en el tablero"
                                       " cuando el caso no está documentado"),),
              efecto="marca el caso en pantalla",
              lista=("real", "hipotetico", "ejemplo"),
              nota="Es cumplimiento —prioridad 1— y hoy sólo cabe como prosa"
                   " dentro de `condiciones` o `nota`."),
        Clave("rotulo_falso",
              dispara=(Aguja("scripts/verificar.py", "def revisar(",
                             pendiente="parar la pieza cuando el rótulo en pantalla"
                                       " no es lo que la fuente dice"),),
              efecto="para la pieza",
              nota="Registrado en `dato` id 4: «COMISION» donde la fuente dice"
                   " tarifa de gestión anual. La cifra se sostiene y el rótulo"
                   " miente, y no había clave para decirlo."),
        Clave("deriva_de",
              dispara=(Aguja("scripts/reels-spec.mjs", "const pieDe = (beat) => {",
                             pendiente="una cifra derivada hereda el pie de la"
                                       " cifra de la que sale"),),
              efecto="la cifra derivada comparte el pie de su origen",
              nota="`dato` id 6: 576 = 30.000/52, «el pie tiene que ser el mismo"
                   " que el de los 30.000». `fuente` es cadena o null y no puede"
                   " apuntar a otro `dato`."),
        Clave("afirmacion",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE: columna NOT NULL de la tabla, el sitio donde se explica"
                   " qué afirma la pieza, y ningún paso la lee. Es candidata a ir"
                   " al payload del corte con `datos_respaldados`."),
        Clave("organismo / url / vigencia / cita",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTES las cuatro. `url` es la prueba de «una URL que no"
                   " abriste no se declara comprobada» y no la comprueba ningún"
                   " paso ni la muestra ninguna pantalla; `vigencia` existe porque"
                   " «una tasa sin año caduca en silencio» y no hay guarda que la"
                   " compare con la fecha del render."),
        Clave("nota",
              dispara=(NADIE,),
              efecto="—",
              nota="INERTE, y es donde acaba todo lo que el esquema no tiene clave"
                   " para decir: rótulos falsos, riesgo reputacional, caducidades."
                   " El campo que más recibe y menos se lee. Se vacía repartiendo"
                   " su contenido en `rotulo_falso`, `marcar_como` y `sube`."),
    ),
    bloques=(REDUNDANCIA, CUMPLIMIENTO),
    repite=None,
)


# ─────────────────────────────────────────────────────────────────────────────
CONTRATOS: dict[str, Contrato] = {c.paso: c for c in (CORTE, COMPONE, RESPALDO)}
BLOQUES: dict[str, Bloque] = {b.nombre: b for b in (REDUNDANCIA, CUMPLIMIENTO)}

#: De fase del `CICLO` al contrato que la gobierna. Las tres primeras son el
#: mismo contrato en tres momentos: eso es el colapso, y es un dato.
POR_FASE: dict[str, Contrato] = {
    "sin_redundancia": CORTE,
    "revalidado": CORTE,
    "repasado": CORTE,
    "descrito": COMPONE,
    "respaldado": RESPALDO,
}


def por_paso(paso: str) -> Contrato | None:
    return CONTRATOS.get(paso)


def momento(fase: str) -> tuple[Contrato, Momento] | None:
    c = POR_FASE.get(fase)
    if not c:
        return None
    m = next((x for x in c.momentos if x.fase == fase), None)
    return (c, m) if m else None


def campos_del_momento(fase: str) -> tuple[Campo, ...]:
    """Los campos que el payload TIENE que llevar en esa fase.

    Es de aquí de donde se arma el pedido, no de un `dict` escrito a mano en
    cada servicio: un campo que se añade al contrato aparece en el payload y en
    la comprobación a la vez, que es lo que hace que no puedan divergir.
    """
    par = momento(fase)
    if not par:
        return ()
    c, m = par
    return tuple(x for x in c.campos_todos()
                 if (not x.en or fase in x.en) and x.nombre not in m.no_trae)


def main():
    import sys

    prompts = "--prompts" in sys.argv
    if prompts:
        print("Los bloques compartidos, con su marca:\n")
        for b in BLOQUES.values():
            print(f"{b.marca()}\n{b.texto.strip()}\n{b.fin()}\n")
        return
    for c in CONTRATOS.values():
        faltan = [x for x in c.campos_todos() if x.manda is None and x.exige]
        sobran = [x for x in c.campos_todos() if x.manda is not None and not x.exige]
        inertes = [k for k in c.claves_todas() if NADIE in k.dispara]
        deuda = [(k.nombre, a) for k in c.claves_todas() for a in k.dispara
                 if a.pendiente]
        print(f"\n== {c.paso} == {len(c.momentos)} momento(s):"
              f" {', '.join(m.fase for m in c.momentos)}")
        print(f"   exigidos y no enviados : {len(faltan)}"
              + ("  -> " + ", ".join(x.nombre for x in faltan) if faltan else ""))
        print(f"   enviados y no pedidos  : {len(sobran)}"
              + ("  -> " + ", ".join(x.nombre for x in sobran) if sobran else ""))
        print(f"   claves inertes         : {len(inertes)}"
              + ("  -> " + ", ".join(k.nombre for k in inertes) if inertes else ""))
        print(f"   deuda declarada        : {len(deuda)}")


if __name__ == "__main__":
    main()
