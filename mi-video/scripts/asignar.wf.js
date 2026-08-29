/**
 * PASO 2 DEL PROCESO — la frase que cumple la función y comunica.
 *
 * Este fichero **es el candado**. Jaime: *«lo que es por IA debe tener un
 * mecanismo para que siempre lo hagas exactamente igual»*. El prompt vive aquí,
 * versionado, y se invoca verbatim; no se improvisa por sesión.
 *
 *   Workflow({ scriptPath: "scripts/asignar.wf.js" })
 *
 * Lo que entra lo genera código (`scripts/candidatos.py`), así que la IA ve
 * siempre el mismo formato. Lo que sale es un esquema fijo que se valida al
 * recibirlo. Y lo que la IA NO decide —los topes de texto, que la unidad sea de
 * una sola toma, que no se repita una idea— lo comprueba el código.
 *
 * Si hay que cambiar el criterio, **se cambia aquí y se nota en el diff**. Un
 * prompt que sólo existe en una conversación no es un mecanismo.
 */
export const meta = {
  name: 'asignar-frames',
  description: 'Paso 2: elige por sentido la frase de cada etapa, la refuta, y redacta el copy de las que quedan sin toma',
  whenToUse: 'Despues de scripts/candidatos.py y antes de escribir el EDL. Es el unico paso no determinista del proceso.',
  phases: [
    { title: 'Asignar', detail: 'una unidad por etapa: funcion Y contenido' },
    { title: 'Refutar', detail: 'un esceptico intenta tumbar cada asignacion' },
    { title: 'Tarjetas', detail: 'copy canonico de las etapas sin toma' },
  ],
}

const BASE = 'F:/Edicion de video/mi-video'
const REELS = args?.reels ?? ['01', '02', '03', '04', '05', '06']

/**
 * El contexto que ve TODO agente de este paso. Es la parte que no puede variar
 * entre ejecuciones: si esto cambia, cambian los resultados.
 */
const CANON = `
CONTEXTO
Anuncios verticales en espanol para Jaime Olarte Finanzas, pilar SELL, sobre
estructura fiscal para duenos de negocio en Ontario. Cada reel ejecuta UNA
estructura del playbook y sus etapas van EN ORDEN. El frame manda: el guion se
reparte dentro de el, no al reves.

LA PRUEBA QUE HAY QUE PASAR — SON DOS COSAS A LA VEZ
Jaime: "se busca la frase exacta que cumpla la funcion del frame y comunique lo
que debe comunicar, las dos cosas, asi no sea exactamente lo mismo".

  (a) FUNCION  - ¿hace el trabajo que esa etapa hace en la estructura?
  (b) CONTENIDO - ¿dice lo que ahi hay que decir?

Las dos, o no entra. Y lo que NO es prueba: parecerse a las palabras del
libreto. Una frase que dice lo mismo con otras palabras vale IGUAL o MAS que una
que repite el vocabulario. Elegir por vocabulario es exactamente lo que fallaba.

LO QUE EL CODIGO YA GARANTIZA — no lo revises, dalo por hecho
- Cada unidad es UN INTENTO CONTINUO de una sola toma. Sus pausas internas se
  quitan al cortar. Nunca hay dos trozos cosidos.
- Los tiempos estan cruzados con el silencio medido, no con la puntuacion de
  whisper, que es poco fiable.

LO QUE TU DECIDES
- Que unidad cumple cada etapa, o ninguna.
- "abre" y "cierra" te dicen si la unidad empieza en mayuscula y acaba en punto.
  Son PISTAS, no reglas: whisper puntua mal justo donde importa. Lo que juzgas
  es si SE LEE COMO UN PENSAMIENTO COMPLETO al oirlo suelto.

REGLAS DURAS
1. Una unidad por etapa. Una unidad no se usa dos veces.
2. Una etapa cumplida cierra su idea: si dos unidades dicen lo mismo, solo una
   entra y la otra etapa se queda sin toma.
3. El precio NO entra: descarta cualquier unidad que diga "20 dolares",
   "40 dolares", "veinte", "cuarenta" o "el precio es". Cambio y volvera a
   cambiar. La fecha (21 de septiembre) SI se mantiene.
4. Si ninguna unidad cumple una etapa, devuelve null. Eso NO es un fallo: esa
   etapa ira con animacion, que es la regla de Jaime — "si no entra bien hacemos
   un grafico, asi sea solo palabras". Es preferible animarla que meter una
   frase que no dice lo que hace falta.
5. Ante la duda, null.
`

const ASIGNACION = {
  type: 'object',
  required: ['asignaciones'],
  properties: {
    asignaciones: {
      type: 'array',
      items: {
        type: 'object',
        required: ['etapa_n', 'unidad_id', 'cumple_funcion', 'comunica', 'razon'],
        properties: {
          etapa_n: { type: 'integer' },
          unidad_id: { type: ['integer', 'null'] },
          cumple_funcion: { type: 'boolean' },
          comunica: { type: 'boolean' },
          razon: { type: 'string' },
        },
      },
    },
  },
}

const VEREDICTO = {
  type: 'object',
  required: ['veredictos'],
  properties: {
    veredictos: {
      type: 'array',
      items: {
        type: 'object',
        required: ['etapa_n', 'sostiene', 'por_que'],
        properties: {
          etapa_n: { type: 'integer' },
          sostiene: { type: 'boolean' },
          por_que: { type: 'string' },
        },
      },
    },
  },
}

const TARJETAS = {
  type: 'object',
  required: ['tarjetas'],
  properties: {
    tarjetas: {
      type: 'array',
      items: {
        type: 'object',
        required: ['etapa_n', 'bloques', 'remate', 'pie'],
        properties: {
          etapa_n: { type: 'integer' },
          bloques: { type: 'array', items: { type: 'string' } },
          remate: { type: 'array', items: { type: 'string' } },
          pie: { type: 'string' },
        },
      },
    },
  },
}

/**
 * **Lo que cada fase produce se guarda, porque el paso siguiente lo lee.**
 *
 * `pipeline()` devuelve solo el resultado de la ultima fase, asi que las
 * asignaciones y los veredictos se perdian: el paso corria entero, costaba lo
 * que cuesta, y `beats.py` -que lee `work/asignacion/reel-NN.json`- no
 * encontraba nada y caia a su propia puntuacion. Ese es el motivo de fondo de
 * que el reel 2 saliera mutilado (C-38): **el paso de sentido no llegaba al
 * montaje**.
 */
const ASIG = new Map();

const out = await pipeline(
  REELS,

  (r) => agent(
    `Lee ${BASE}/work/candidatos/reel-${r}.json.

${CANON}

Trae "etapas" (en orden; cada una con su funcion y una "idea" que es como lo
decia el libreto — es descripcion, no el texto a buscar) y "oraciones" (unidades
de audio de la toma, con id, tiempos y texto).

Para CADA etapa elige la unidad que pasa las dos pruebas, o null.
Entre varias que pasan: la que lo dice mas entero y con menos "aire".

Devuelve una entrada por etapa con cumple_funcion, comunica y una razon de una
linea.`,
    { label: `asignar:R${r}`, phase: 'Asignar', schema: ASIGNACION },
  ).then((a) => (ASIG.set(r, a), a)),

  (asig, r) => agent(
    `Eres un revisor esceptico. Lee ${BASE}/work/candidatos/reel-${r}.json.

${CANON}

Otro revisor propuso:
${JSON.stringify(asig?.asignaciones ?? [], null, 1)}

Para cada asignacion con unidad_id NO nulo, intenta TUMBARLA. sostiene=false si:
- No hace el trabajo de esa etapa, aunque comparta palabras.
- Dice lo mismo que otra etapa ya asignada: el argumento se repetiria.
- Menciona el precio.
- Al oirla suelta NO se lee como un pensamiento completo: arranca sin sujeto,
  cuelga a mitad, o es un arranque fallido antes de la frase buena.

Por defecto DUDA. Es mejor animar la etapa que meter una frase a medias — que es
justo lo que rompio el lote anterior.`,
    { label: `refutar:R${r}`, phase: 'Refutar', schema: VEREDICTO, effort: 'high' },
  ),

  (ver, r) => agent(
    `Lee ${BASE}/work/candidatos/reel-${r}.json y, de ${BASE}/../CLAUDE.md, las
secciones "Identidad grafica: el canon" y "Texto en pantalla".

${CANON}

Estas etapas se quedaron sin unidad utilizable y van con animacion:
${JSON.stringify((ver?.veredictos ?? []).filter((v) => !v.sostiene), null, 1)}

Escribe el copy de cada tarjeta. TOPES DUROS — el render FALLA si se pasan:
- "bloques": 2 o 3 etiquetas, maximo 26 caracteres cada una.
- "remate": 2 o 3 lineas, maximo 38 caracteres cada una.
- "pie": una linea, maximo 52 caracteres.

Como se escribe:
- El tablero NO transcribe lo que se dice: lleva el ancla corta y memorable.
- **Reduce complejidad.** Jaime lo pidio asi: util, legible, con tiempo para
  leerlo y con la sencillez suficiente para captar la idea central. UNA idea por
  tablero; si hacen falta dos, son dos tableros.
- Espanol nativo, tratando de usted. Nada traducido.
- Sin precio. La fecha si.
- Nada inventado: ni cifras, ni casos, ni resultados fuera de la "idea" de esa
  etapa. Toda cifra que aparezca tiene que estar en esa idea.

Si no queda ninguna etapa sin toma, devuelve lista vacia.`,
    { label: `tarjetas:R${r}`, phase: 'Tarjetas', schema: TARJETAS },
  ).then((t) => ({
    reel: r,
    asignaciones: ASIG.get(r)?.asignaciones ?? [],
    veredictos: ver?.veredictos ?? [],
    tarjetas: t?.tarjetas ?? [],
  })),
)

return { reels: REELS, resultado: out }
