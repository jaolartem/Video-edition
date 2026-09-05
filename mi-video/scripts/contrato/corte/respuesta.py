"""Lo que el paso de corte contesta: `Clave.dispara`, la linea que lo ejecuta.

La otra mitad de `pedido.py`. Una clave sin aguja —`dispara=NADIE`— falla el
build y dice cual, que es lo que impide que una clave quede declarada, pedida
en el prompt y muerta en el consumo.
"""
from ..aguja import Aguja
from ..piezas import Clave

CLAVES = (
    Clave("beat",
          dispara=(Aguja("scripts/servicios/revalidar.py", "beat = v.get(\"beat\")"),),
          efecto="enruta el elemento a su etapa",
          obligatoria=True,
          nota="Sin él la fila se descarta con `continue`, sin aviso."),
    Clave("ancla",
          dispara=(Aguja("scripts/redundancia.py", 'revision.anotar(slug, "cortar", None, None,'),
                   Aguja("scripts/dominio/ancla.py", "def por_ancla(")),
          efecto="nota `cortar` en `revision`, que `revision.aplicar` recorta"
                 " del EDL buscando ese texto sobre el montaje de hoy",
          exige_ademas=("por_que",),
          nota="Único campo obligatorio de un corte. `cargar` manda siempre"
               " desde=None y hasta=None: lo que no se pueda anclar en texto"
               " exacto no se puede cortar."),
    Clave("cual",
          dispara=(Aguja("scripts/dominio/ancla.py", "def por_ancla("),),
          efecto="salta apariciones hasta la enésima al aplicar",
          sin_valor="1",
          nota="Se cuenta sobre el montaje entero y el payload viene troceado"
               " por segmento: contar apariciones globales es reconstrucción"
               " del lector, no un dato. Lo arregla `montaje[].en`, que ya viaja."),
    Clave("tramos",
          dispara=(Aguja("scripts/servicios/revalidar.py",
                         "vd = fijar.declarar(pieza.slug, beat, toma, nuevos,"),),
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
                   Aguja("scripts/dominio/seleccion/corrida.py",
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
          dispara=(Aguja("scripts/redundancia.py", 'c.get("por_que")'),),
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
)
