"""Lo que viaja al paso de corte: `Campo.manda`, la mitad del pedido.

Un fichero para el payload y otro para la respuesta porque son las dos mitades
que el contrato distingue —el dato que se manda y la clave que se ejecuta— y
porque este contrato es el unico de los cuatro que no cabe entero: colapsa tres
fases, asi que lleva el triple de campos que los demas.

`en=(...)` es lo que hace que eso funcione sin partir el contrato: un campo
declara en que momentos viaja, y `campos_del_momento` arma el pedido de la fase
que toque. Lo demas del contrato —los tres momentos, como se repite— esta en
`__init__.py`, y lo que se contesta en `respuesta.py`.
"""
from ..aguja import Aguja, Prompt
from ..piezas import Campo

CAMPOS = (
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
          condicional="sólo si el trozo llega a `beats.VENTANA_MIN`, que es"
                      " lo que la medida de F0 necesita para existir",
          si_falta=Prompt("scripts/redundancia.prompt.md",
                          "si un trozo llega sin `voz` ni `tono`, es que no se"
                          " pudo medir — no que salga cero"),
          nota="Cerrado. El código ponía su propio umbral (0,6 s) por debajo"
               " del de la medida (1,0 s), y en esa franja `expresividad`"
               " aplanaba el «no medido» en 0.0: el trozo viajaba con «voz"
               " 0.0» y eso se lee como entrega muerta. Ahora el campo no"
               " viaja, y el prompt dice qué hacer con el hueco."),
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
    Campo("libreto",
          manda=Aguja("scripts/revalidar.py",
                      '"libreto": _lib[beat - 1] if 1 <= beat <= len(_lib) else None,'),
          exige=(Prompt("scripts/repaso.prompt.md", "el libreto quería decir"),
                 Prompt("scripts/revalidar.prompt.md", "del libreto y del texto")),
          nota="La intencion de SU beat al lado de lo que la etapa dice, en el"
               " dossier de `revalidar` — que es el paso cuyo prompt promete"
               " comparar «del libreto y del texto». Estuvo EXIGIDO Y NO ENVIADO,"
               " y esa es la averia que Jaime nombro: «si el objetivo es comparar"
               " A con B, no puedes entregarme B roto o solo el final de A»."
               " Viaja la intencion por beat (1,2-1,7 KB), no el corpus: los 118"
               " KB salieron de `repaso` a proposito y no vuelven."),
    Campo("estructura",
          manda=Aguja("scripts/servicios/repaso.py", '**_contexto_del_corte(pieza.slug)}'),
          exige=(Prompt("scripts/redundancia.prompt.md", "PAS sin problema o sin activación"),),
          nota="EXIGIDO Y NO ENVIADO desde que `repasado` dejo este contrato."
               " Que lo mandara el paso equivocado es justo lo que escondia la"
               " deuda: `redundancia` razona sobre PAS sin recibir el arco, y"
               " parecia cubierto porque OTRO momento del mismo contrato lo"
               " traia. Valores reales: 'Polarizing Thesis', 'Belief Demolition',"
               " 'Two Paths / Default Loss'. El prompt de repaso afirma en"
               " duro «estas piezas son SELL» con una tabla de cuatro arcos"
               " donde ninguno de ésos aparece, y el de redundancia razona"
               " sobre PAS sin recibir el arco."),
    Campo("pilar / cta / enunciados",
          manda=None,
          deuda="ver `nota`",
          exige=(Prompt("scripts/revalidar.prompt.md", "El nombre de las cosas"),),
          nota="EXIGIDO Y NO ENVIADO. El EDL los tiene y `revalidar.dossier`"
               " los lee y los tira."),
    Campo("candidatas",
          manda=Aguja("scripts/revalidar.py", '"candidatas": candidatas(slug, beat)'),
          exige=(Prompt("scripts/revalidar.prompt.md", "revisa los candidatos con sus puntuaciones"),),
          en=("revalidado",),
          nota="Máximo 3, y su `texto` va TRUNCADO a 400 caracteres — con el"
               " tuteo del cierre como descalificador duro, en una candidata"
               " larga el final se corta antes de llegar. `puntuacion` puede"
               " ser `null` a propósito y el prompt la asume presente."),
    Campo("abanico",
          manda=Aguja("scripts/servicios/repaso.py",
                      '"instrumentos": INSTRUMENTOS, "ya_medido": YA_MEDIDO,'),
          exige=(Prompt("scripts/revalidar.prompt.md", "no se salta un peldaño"),),
          en=("revalidado", "repasado"),
          nota="EL ACCESO AL CORPUS, y viaja como INSTRUMENTO, no como dato."
               " El peldano 2 ordena buscar en las siete cintas y el corpus"
               " nunca viajaba: se le pedia elegir sin darle entre que. Mandarlo"
               " entero son megabytes por pieza, asi que se declara como se pide"
               " —`consulta.py abanico` con una frase— y quien compone lo invoca"
               " para el sitio que necesita. Jaime: «siempre que sean necesarias,"
               " para ahorrar tokens»."),
    Campo("lo_que_hizo_la_maquina",
          manda=Aguja("scripts/servicios/repaso.py",
                      '"lo_que_hizo_la_maquina": lo_que_hizo_la_maquina(pieza.slug),'),
          exige=(Prompt("scripts/repaso.prompt.md", "se supervisa"),),
          en=("repasado",),
          nota="Lo que los pasos automaticos movieron en el corte. Jaime: «los"
               " procesos declarados no desaparecen, son supervisados y"
               " entendidos por el LLM, que se da cuenta cuando un borde quedo"
               " mas cerrado». Los pasos ya lo anotaban en `incidencia` y nadie"
               " se lo ensenaba a quien compone."),
    Campo("tramos_actuales",
          manda=Aguja("scripts/servicios/repaso.py", '**_contexto_del_corte(pieza.slug)}'),
          exige=(Prompt("scripts/revalidar.prompt.md", "qué edición la salva"),),
          en=("revalidado",),
          nota="EXIGIDO Y NO ENVIADO. Se pide mover la costura y del montaje"
               " sólo llega el span (`desde`/`hasta` = min y max) más el"
               " contador `trozos`. Dónde están hoy las costuras, no."),
    Campo("vuelta",
          manda=None,
          deuda="ver `nota`",
          exige=(Prompt("scripts/repaso.prompt.md", "ya dio tres vueltas"),),
          nota="EXIGIDO Y NO ENVIADO. Quien cuenta las vueltas es `avanzar.py`"
               " y no se lo dice a quien contesta. El código escribe siempre"
               " `pasada=2`."),
)
