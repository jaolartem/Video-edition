"""Los tiquets de Jaime que una pieza tenía que haber atendido y no atendió.

Jaime, después de una noche entera con trece correcciones suyas sin aplicar:
*«termina y sube todos los malditos tikets, todos, para eso hicimos esa maldita
tabla, y por alguna razón siempre estoy repitiendo las mismas correcciones
porque nunca llegan las indicaciones»*.

## Por qué no llegaban

La tabla `revision` guarda sus correcciones desde hace semanas, con sus palabras
literales. Y la línea **no la mira**. `avanzar --volver recortado` devuelve la
pieza a esa fase, la fase corre su paso, y el paso no pregunta si hay un tiquet
suyo esperando: la pieza atraviesa `recortado`, `disenado` y `nivelado` y sale
por el otro lado exactamente igual que entró.

Medido el 5 de septiembre: trece tiquets suyos abiertos, las siete piezas
recorridas de punta a punta dos veces, **cero aplicados**. No es que se
perdieran — es que nadie los buscó.

Es la avería de siempre en su forma más cara: una decisión guardada que el paso
que la necesita no lee. Sólo que aquí la decisión es suya.

## Cómo se cierra

Cada corrección dice en `accion` de qué es, y de ahí sale **qué paso la
arregla**. Si la pieza ya pasó ese punto y la corrección sigue abierta, la línea
se para ahí y la nombra, con su número y sus palabras.

No la aplica sola: aplicarla es trabajo del paso, y adivinarlo sería peor. Lo
que garantiza es que **ninguna pieza llega a entregarse con un tiquet suyo
abierto**, que es lo único que hacía falta para que dejara de repetirse.
"""
from __future__ import annotations

import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

BASE = "ads/decisiones.db"

#: De qué es una corrección → qué paso la arregla. Es el mismo reparto que ya
#: usa `dominio/ticket.py` con `RUTA`, escrito para la tabla de Jaime.
#:
#: `otro` va a `disenado` porque es donde vive el criterio: casi todas sus notas
#: de ese tipo son de qué dice la pieza o de cómo se ve, y ninguna se arregla
#: sola en un paso mecánico.
FASE = {
    "cortar": "recortado",
    "grafico": "disenado",
    "sonido": "nivelado",
    "subtitulo": "montado",
    "otro": "disenado",
}


#: Lo que NO es una correccion suya: las notas que levanta la propia maquina.
#: Se marcan al escribirlas y es la unica excepcion.
MAQUINA = "MAQUINA"


def suyas(slug):
    """Sus correcciones abiertas de esta pieza: (id, accion, fase, palabras).

    **Esto filtraba por `que like '%Jaime%'` y se comia tiquets enteros.**

    El #752 de reel-02 —dos capas dibujando la misma comparacion, con las cifras
    contradiciendose en el mismo frame— nunca llego al pedido de diseno: lo
    habia escrito un agente contando el defecto medido, sin nombrarle. El pedido
    salio con `modo: null` y `tiquets: null`, o sea que el paso siguiente no vio
    la correccion. Es exactamente la averia que este proyecto existe para
    impedir: la decision esta anotada y el que trabaja no se entera.

    Buscar su nombre en el texto era adivinar quien escribio la nota. Ahora se
    da la vuelta: **abierta es suya salvo que este marcada como de maquina**, que
    es lo unico que se sabe de cierto porque se marca al escribirla. Equivocarse
    hacia enviar de mas cuesta que el paso lea una linea que no le toca;
    equivocarse hacia enviar de menos cuesta una entrega con el defecto dentro,
    que es lo que llevamos pagando.
    """
    try:
        cx = basedatos.abrir(BASE)
        cx.row_factory = sqlite3.Row
        filas = cx.execute(
            "select id, accion, que from revision where video_slug = ?"
            " and estado = 'pendiente' and ifnull(que,'') not like ? || '%'"
            " order by id",
            (slug, MAQUINA)).fetchall()
    except sqlite3.Error:
        return []
    # **Enteras.** El tope de 120 venia de cuando una correccion era una linea.
    # Hoy llevan la decision dentro, y cortarlas manda el titular sin el
    # encargo: el 7-9-2026 la #805 le llego al disenador cortada en «...no
    # sostiene: «usted no es» —justo antes de la frase que Jaime eligio— y
    # eligio otra distinta. La instruccion viaja entera o no viaja.
    suyas_ = [(r["id"], r["accion"], FASE.get(r["accion"], "disenado"),
               " ".join((r["que"] or "").split())) for r in filas]
    return suyas_ + _tiquets(slug)


def _tiquets(slug):
    """Y los tiquets abiertos, que son lo mismo escrito en la otra tabla.

    **Dos tablas para una decision, y el que reparte solo miraba una.** Una
    correccion de Jaime vive en `revision` y una objecion suya sobre una pieza
    vive en `ticket` — la separacion tiene su motivo, la explica
    `dominio/ticket.py`—, pero para ESTA pregunta son la misma cosa: qué tiene
    que mirar el paso que viene, y por tanto qué NO tiene que volver a mirar.

    Sin esto el pedido salia con `modo: null` y `tiquets: null`, o sea sin
    acotar: el 7-9-2026 el compositor de reel-03 recibio las 7 escenas enteras
    —252 KB— para arreglar 8 segundos de gancho, y estuvo veinte minutos
    redescribiendo la parte que Jaime ya habia aprobado. Es el mismo defecto que
    el docstring de arriba cuenta con el #752, arreglado por el lado del filtro
    y no por el de la tabla.

    El paso lo declara el propio tiquet en `vuelve_a`, que es donde ya estaba.
    """
    try:
        from . import ticket as _t
        cx = basedatos.abrir(BASE)
        cx.row_factory = sqlite3.Row
        filas = cx.execute(
            "select id, dijo, beat, vuelve_a from ticket"
            " where pieza = ? and estado = 'abierto'"
            " and ifnull(vuelve_a,'') <> '' order by id", (slug,)).fetchall()
    except (sqlite3.Error, ImportError):
        return []
    fuera = []
    for r in filas:
        # El beat que el tiquet ya trae vale mas que buscarlo en la prosa:
        # `abrir` lo derivo del segundo que Jaime dijo. Se antepone al texto
        # porque `etapa_de` lee ahi, y asi acotar no depende de como se redacto.
        # **Entero, no recortado a 120.** Ese tope viene de `revision`, donde
        # una nota es una linea. Un tiquet es lo contrario —el esquema lo dice:
        # «sus palabras, sin resumir»— y ahi dentro va la medida con la que se
        # atiende. Cortado a 120 llega el titular y se pierde el encargo, y
        # quien contesta tiene que ir a buscarlo a la base.
        txt = " ".join((r["dijo"] or "").split())
        if r["beat"] is not None:
            txt = f"e{r['beat']} · {txt}"
        # **Marcado, porque los dos numeros se pisan.** `revision` y `ticket`
        # numeran cada una por su cuenta: la revision 279 existe y el tiquet
        # 279 tambien, y son cosas distintas. `cerrar` escribe en `revision`,
        # asi que un `tiquets: [279]` de una respuesta habria marcado como
        # aplicada una correccion que nadie miro — el mismo defecto silencioso
        # que `CierreAjeno` impide un piso mas arriba.
        fuera.append((f"t{r['id']}", "otro", r["vuelve_a"], txt))
    return fuera


def vencidas(slug, fase_actual, orden):
    """Las que ya deberían estar hechas: su paso quedó atrás y siguen abiertas.

    `orden` es el mapa nombre-de-fase → posición en el camino, para saber qué
    quedó detrás. Una corrección cuya fase todavía no ha llegado no es una
    falta: es trabajo pendiente y la línea va hacia ella.
    """
    aqui = orden.get(fase_actual)
    if aqui is None:
        return []
    # **Y una pieza aprobada entera no se para por lo que la puerta ya no
    # reabre** (C-489). `puertas.del_tiquet` deja abiertos sus tiquets y los
    # sube a Jaime; esto la paraba igual con «su paso ya quedó atrás». reel-12,
    # 13-9: sus ocho etapas aprobadas y dos tiquets de subtítulos para «montado»,
    # y se quedó en «visto» sin llegar a la revisión de Jaime, que es donde esos
    # tiquets tienen que verse.
    from .segmento import aprobada as _entera
    if _entera(slug):
        return []
    # **Estrictamente ANTES, no «hasta aqui».** Con `<=`, una pieza sentada en la
    # fase que atiende su correccion se declaraba bloqueada por lo que habia
    # venido a arreglar: el 7-9-2026 el despachador dio vueltas sin mover nada
    # con las siete piezas diciendo «tiene correcciones sin aplicar y su paso ya
    # quedo atras», y reel-01 estaba EN `descrito` con su correccion PARA
    # `descrito`. Igual no es atras — es ahora.
    return [t for t in suyas(slug)
            if orden.get(t[2]) is not None and orden[t[2]] < aqui]


#: **La capa de instrucción del contrato**, cuando lo que hay son tiquets.
#:
#: Jaime: *«hay dos modos para cada agente; el contrato tiene dos capas, una con
#: las capacidades y otra con la instrucción. Si es general es una cosa, pero si
#: son tikets son eso»*. El prompt del paso son **las capacidades** —lo que ese
#: agente sabe hacer, y no cambia—; esto es **la instrucción** —lo que se le pide
#: hoy—. Mezclarlas es lo que convertía cada corrección en un rebuild: *«no puedo
#: estar haciendo un rebuild cada vez que corrijo cosas puntuales»*.
MODO = """

---

# HOY NO COMPONES LA PIEZA: ARREGLAS ESTOS TIQUETS

Jaime: *«no puedo estar haciendo un rebuild cada vez que corrijo cosas
puntuales»*, y *«no quiero otro rediseño ni más retrabajos, quiero las
correcciones»*.

Las capacidades de arriba siguen siendo las tuyas. Lo que cambia es el encargo:

- **Toca sólo las etapas que nombran los tiquets** de `datos.tiquets`. El resto
  de la pieza está aprobado y no se rehace, ni «de paso» ni «ya que estamos».
- Devuelve **sólo esas etapas**. Una etapa que no devuelves se queda como está,
  que es justo lo que se quiere.
- Si un tiquet no se puede resolver sin tocar otra etapa, **dilo en `por_que`**
  en vez de tocarla.
- Si un tiquet ya está resuelto en el montaje de hoy, dilo también: cerrarlo
  vale tanto como aplicarlo, y callarlo no vale nada.
- **Y di cuáles atiendes**, en `tiquets: [números]`: al primer nivel si tu
  respuesta es un objeto, o en cada etapa que lo atiende si tu contrato contesta
  con una lista de etapas; la línea lee las dos (C-664). Sólo se cierran ésos. Los que no nombras se quedan abiertos, que es
  lo que hay que hacer con un tiquet que no has mirado — antes se cerraban todos
  los de la fase y una respuesta sobre los paneles se llevó por delante el
  tiquet del gancho.
"""


def etapa_de(texto):
    """La etapa que nombra una corrección suya, o `None` si habla de la pieza.

    Los tres nombres que este proyecto usa para lo mismo —`e7`, `etapa 7` y
    `beat 7`—, porque él escribe uno y la máquina escribe otro. `None` no es un
    fallo de lectura: hay correcciones que son de la pieza entera («el abuso del
    glitch en este reel»), y ésas abren todas las etapas.
    """
    import re

    t = (texto or "").lower()
    m = re.search(r"\b(?:e|b|etapa\s*|beat\s*)(\d{1,2})\b", t)
    # **Y las dos formas que escribe la propia maquina** (C-560): «b7» en la
    # regla de plano y «etapas [4]» en la puerta. Sin ellas el tiquet contaba
    # como de la pieza entera y abria todas las etapas, aprobadas incluidas.
    m = m or re.search(r"etapas?\s*\[(\d{1,2})", t)
    return int(m.group(1)) if m else None


def _medida(id_):
    """Con qué se cierra ese tiquet: lo que declara su fila, o su tipo.

    Las dos mitades ya están escritas —`ticket.cierra_con` y `ticket.RUTA`—, así
    que aquí no se decide nada: se lee la primera y, si viene vacía, la segunda.
    """
    from . import ticket as _t

    try:
        cx = basedatos.abrir(BASE)
        cx.row_factory = sqlite3.Row
        f = cx.execute("select tipo, cierra_con from ticket where id = ?",
                       (int(id_),)).fetchone()
    except sqlite3.Error:
        return "objecion"
    if not f:
        return "objecion"
    return (f["cierra_con"] or _t.RUTA.get(f["tipo"], ("", ""))[1]
            or f["tipo"] or "objecion")


def cerrar(slug, fase, por_que, atendidos=None):
    """Cierra como `aplicada` los tiquets **que la respuesta dice haber atendido**.

    Lo llama **el paso que los arregló**, y por eso vive aquí: cerrar una
    corrección es parte de atenderla, no un trámite aparte. Sin esto el servicio
    componía, la nota seguía abierta y la línea se paraba otra vez por algo ya
    hecho — y la única salida era un `update` a mano contra la base.

    **Y cierra los declarados, no todos los de la fase.** Cerraba todos, y con
    dos pasos trabajando la misma pieza eso se cobró en el acto: una respuesta
    que arreglaba los dos paneles de reel-07 cerró de paso el tiquet del gancho,
    que nadie había mirado. La corrección de Jaime salía de los pendientes sin
    haberse atendido — que es exactamente lo que este fichero existe para
    impedir.

    `atendidos` son los números que la respuesta declara. **Sin ellos no se
    cierra nada**, y ése es el lado seguro: dejar una nota abierta cuesta otra
    vuelta; cerrarla sin haberla hecho cuesta que él la vuelva a pedir. El modo
    de tiquets ya se lo pide a quien compone — *«si un tiquet ya está resuelto en
    el montaje de hoy, dilo también: cerrarlo vale tanto como aplicarlo»*.
    """
    # Una respuesta nombra numeros sueltos; aqui se decide de que tabla es cada
    # uno mirando lo que `suyas` declaro, no adivinando por el numero.
    pedidos = {str(i).strip().lstrip("t") for i in (atendidos or [])}
    mios = [t[0] for t in suyas(slug)
            if t[2] == fase and str(t[0]).lstrip("t") in pedidos]
    tiquets = [int(str(i)[1:]) for i in mios if str(i).startswith("t")]
    suyos = [int(i) for i in mios if not str(i).startswith("t")]
    # **Con la medida que el tiquet declara, no con una fija.** Esto cerraba
    # todos con la de `objecion`, asi que un tiquet de `suena` —que se cierra
    # oyendo el borde— quedaba cerrado con la medida de otra cosa: el recibo
    # existe y no dice nada de lo que habia que comprobar. La medida la eligio
    # quien lo abrio y esta en su fila (`ticket.abrir` la escribe desde `RUTA`).
    #
    # Y el fallo no se traga: cerrar es lo que convierte una correccion en
    # atendida, asi que un cierre que revienta y devuelve el numero igual es la
    # forma mas cara de mentir. Solo se devuelven los que se cerraron.
    cerrados = []
    for i in tiquets:
        from . import ticket as _t

        # **La prueba movida no se cierra con palabras** (C-687): la cierra
        # `cierre.atiende_las_movidas` cuando lo declarado vuelve a casar.
        import fijar

        if _medida(i) == fijar.MOVIDA:
            print(f"  el tiquet #{i} se cierra midiendo, no declarandolo", flush=True)
            continue
        try:
            _t.contestar(i, por_que[:400], "arreglado", "la linea", _medida(i))
            cerrados.append(i)
        except Exception as e:                     # noqa: BLE001
            print(f"  el tiquet #{i} no se pudo cerrar:"
                  f" {type(e).__name__}: {e}", flush=True)
    if not suyos:
        return [f"t{i}" for i in cerrados]
    try:
        cx = basedatos.abrir(BASE)
        cx.executemany(
            "update revision set estado = 'aplicada', regla = ? where id = ?",
            [(por_que[:400], i) for i in suyos])
        cx.commit()
        cx.close()
    except sqlite3.Error:
        return []
    return suyos


def beats_de_tiquets(slug, fase):
    """Las etapas que abre un tiquet de `ticket`, por su `beat`.

    **Son dos tablas para lo mismo y sólo una abría trabajo.** `revision` guarda
    sus correcciones y es la que lee todo este fichero; `ticket` es la que
    escribe el CLI que `CLAUDE.md` pone como forma de anotar una observación
    —*«los abiertos viajan en el pedido de su pieza, así que el paso que decide
    los ve colocados en su etapa»*—. Viajaban, sí: `servicio.pedir` los mete en
    `lo_que_dijo_jaime_de_la_pieza`. Pero **no abrían la etapa**, así que la
    lámina de la que hablaban seguía sin entrar al encargo y quien componía leía
    la objeción sin poder tocar lo que objeta.

    Un tiquet abre por `beat`, que ya lo trae medido y recolocado contra el
    corte de hoy (`ticket.recolocar`). El que no tiene beat no abre nada: abrir
    la pieza entera por una nota sin etapa es rehacer lo aprobado, que es lo que
    el modo de tiquets viene a impedir.
    """
    try:
        from . import ticket as _t
    except ImportError:                                # pragma: no cover
        return set()
    try:
        return {int(t["beat"]) for t in _t.abiertos(slug)
                if (t.get("vuelve_a") or "") == fase and t.get("beat") is not None}
    except Exception:                                  # noqa: BLE001
        return set()

def abre(slug, fase, fila):
    """¿Un tiquet suyo vuelve a poner esta etapa en el encargo?

    La respuesta la sabe el alcance; esto es la puerta que ya usaban los pasos.
    """
    from .alcance import Alcance

    return Alcance.de(slug, fase).abre(fila["etapa_orden"])


def modo(prompt, payload, slug, fase):
    """Pone el alcance encima del contrato. Ver `dominio/alcance.py :: sobre`."""
    from .alcance import Alcance

    return Alcance.de(slug, fase).sobre(prompt, payload)


# **`encargo`, `alcance`, `modo` y `abre` se fueron a `dominio/alcance.py`.**
#
# Eran cinco funciones y una tupla desnuda —`(hay, etapas, todas)`— para una
# sola pregunta: hasta donde llega el encargo de hoy. Jaime, 8-9-2026: *«las
# herramientas quedan iguales, lo que cambia es el alcance; esto es POO»*.
# Ahora es un objeto y aqui queda lo que si es de este fichero: que hay abierto,
# que quedo vencido y como se cierra.
