"""Lo que va en TODOS los contratos, escrito una vez.

Jaime: *«redundancia y fuentes debe estar en todos los contratos»*. Y no sólo
la prosa: **con campos y con claves**. Ésa era la trampa de la versión anterior
—los cinco prompts hablaban de cumplimiento y ninguno tenía dónde devolverlo,
así que un dato sin respaldo se guardaba con la misma forma que un ajuste de
color y el lote seguía—.

Los cuatro contratos lo montan con `bloques=(...)`, así que corregir aquí
corrige los cuatro. Duplicarlo es la avería que este fichero existe para
impedir.
"""
from .aguja import Aguja, Prompt
from .piezas import Bloque, Campo, Clave

SUBE = Clave(
    "sube",
    dispara=(Aguja("scripts/servicio.py", "for k in PARAN:"),
             Aguja("scripts/verificar.py", "for n in Nota.subidas(slug):")),
    efecto="nota de revisión con estado='sube': la pieza no pasa la puerta hasta"
           " que Jaime la mire",
    lista=("cifra_sin_fuente", "cifra_contradicha", "precio_o_fecha_cambiada",
           "caso_no_documentado", "etapa_obligatoria_sin_material",
           "material_no_grabado"),
    nota="Es la clave que faltaba en los cinco pasos. Regla corta del proyecto:"
         " se consulta lo que cambia el mensaje, no lo que cambia la ejecución —"
         " y hasta ahora lo que cambia el mensaje no tenía dónde escribirse."
         " Escribe `servicio._escala` desde `recoger()`, que es la puerta por la"
         " que entra toda respuesta, y la cuenta `verificar.revisar` leyendo"
         " `Nota.subidas`. Ver C-532.",
)

CLASE = Clave(
    "clase",
    dispara=(Aguja("scripts/servicio.py",
                   'marca = f"[{clase}] " if clase in ("comprobable", "criterio") else ""'),),
    efecto="la nota que sube dice de qué clase es el hallazgo",
    adjunta_a="sube",
    lista=("comprobable", "criterio"),
    nota="Los dos criterios no son simétricos. Lo de composición casi siempre"
         " se puede contrastar —una duración, una repetición, una cifra contra"
         " `dato`—; lo estético no, y produce hallazgos que ninguna herramienta"
         " puede contradecir. Sin marcarlos, la puerta los trata igual y Jaime"
         " no sabe cuál puede comprobar antes de mirar. Es la misma regla que"
         " el proyecto le exige a los informes, aplicada dentro del sistema.",
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
              manda=Aguja("scripts/servicio.py", '"precio_vigente": _precio(),'),
              exige=(Prompt("scripts/repaso.prompt.md", "El precio en voz coincide con el escalón"),),
              condicional="`None` si no hay escalón abierto **y también si la"
                          " llamada revienta**: los dos casos son el mismo dato",
              si_falta=Prompt("scripts/repaso.prompt.md", "sin escalón, la pieza no sale"),
              nota="{importe, hasta, vale, luego}. Es el único «contra qué» que"
                   " el paso tiene para comprobar el precio, y por eso viaja en"
                   " TODOS los pedidos y no sólo en `repaso`: llegando a uno"
                   " solo, tres agentes dedujeron la ventana de las fechas de"
                   " `datos_respaldados`, se quedaron con la fila del Early"
                   " Bird y dieron por caducado un precio abierto (C-160)."),
        Campo("hoy",
              manda=Aguja("scripts/servicio.py",
                          'd = {"hoy": _hoy(), "datos_respaldados": _respaldos(slug),'),
              exige=(Prompt("scripts/fuentes.prompt.md", "no respalda una cifra de hoy"),),
              nota="La fecha del render. Sin ella, «hoy» es lo que el modelo"
                   " suponga, y una vigencia se juzga contra una fecha"
                   " inventada. Viaja por `pedir()`, que es el unico sitio por"
                   " el que pasan los cuatro contratos — y cuenta como volatil,"
                   " para que una respuesta de anoche no caduque al amanecer."),
        Campo("evento",
              manda=None,
              deuda="ver `nota`",
              exige=(Prompt("scripts/repaso.prompt.md", "El nombre del evento es uno solo"),
                     Prompt("scripts/repaso.prompt.md", "fecha del evento")),
              nota="EXIGIDO Y NO ENVIADO. {nombre, fecha}. Lo único que llega es"
                   " `precio_vigente.hasta`, que es el cierre del escalón —no la"
                   " fecha del evento— y no dice cómo se llama."),
        Campo("datos_respaldados",
              manda=Aguja("scripts/servicio.py", "def _respaldos(slug):"),
              une_con="etapa",
              exige=(Prompt("scripts/repaso.prompt.md", "las cifras y las promesas no se contradigan"),),
              nota="Lo que `fuentes` guardó en `dato` —86 filas— con su fuente,"
                   " su vigencia y sus condiciones: {etapa, cifra, respalda,"
                   " condiciones, rotulo, organismo, url, vigencia, cita}. Es"
                   " la instrucción de Jaime —fuentes en todos los contratos—."
                   " Mientras no llegaba, quien contestaba no tenia contra que"
                   " comprobar una cifra y su unica salida honesta era subirla:"
                   " cinco de siete agentes subieron «sin fuente» el mismo dia."),
    ),
    claves=(SUBE, CLASE),
)
