"""Las fases: qué camino hay, dónde está una pieza y cómo se anota que se movió.

**Por qué vive aquí y no en el motor.** `avanzar.py` es una cosa —recorrer— y
esto es otra: **lo que una fase es**. Estaban juntas porque el motor fue lo
primero que necesitó preguntarlo, y con eso `avanzar.py` pasó del techo de 300
líneas. La regla dice que una regla nueva no añade un fichero al lado: quita
uno. Aquí quita cien líneas de donde no eran.

La fase es un dato, no una posición en una lista: por eso hay tabla `fase` y
tabla `video_fase`, y por eso una pieza puede volver atrás sin que el motor
sepa nada del camino.

**Y el camino se declara aquí.** `CICLO` vivía en `modelo.py`, que es el script
que migra, y este fichero tenía que decir «ver `modelo.CICLO`» — una fase
preguntándole a la herramienta de migración cuáles son las fases. Ahora el
catálogo es de quien es: `camino()` lee de la base lo que `migraciones._ciclo`
escribió leyendo `CICLO`, y los tres miran el mismo sitio.
"""
from __future__ import annotations

import datetime
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402
import rutas  # noqa: E402

BASE = basedatos.BASE


# El ciclo completo, en orden. Cada fase dice **que servicio la mueve a la
# siguiente**: la etiqueta llama al servicio, no al reves.
CICLO = [
    (1, "catalogado", "scripts/transcribir.py --barato"),
    (2, "elegido", "scripts/seleccionar.py {n} --edl"),
    # **Los tramos declarados se vuelven a poner justo despues de elegir.**
    # `seleccionar` rehace el EDL desde cero, asi que sin este paso cada pasada
    # del motor borraba las decisiones fijadas —el arranque bueno de reel-01
    # volvia a ser la toma dudada— y nadie se enteraba. Una decision que no
    # sobrevive a rehacer el paso anterior no es una decision: es un apaño.
    (2.5, "fijado", "scripts/fijar.py --aplicar {n}"),
    (3, "afinado", "scripts/transcribir.py --elegidos {n}"),
    (4, "depurado", "scripts/depurar.py {n}"),
    (5, "sin_redundancia", "scripts/redundancia.py {n}"),
    # **Y los cortes anotados se aplican.** `redundancia` no corta: anota en
    # `revision` con su ancla y su porque, que es lo correcto —el ancla
    # sobrevive a que la pieza se vuelva a montar y los segundos no—. Pero
    # ninguna fase los llevaba al EDL: se anotaban, `verificar` los contaba como
    # pendientes, y la pieza se montaba con la redundancia dentro.
    #
    # Es exactamente la queja de Jaime sobre el primer video —*«no parece que
    # hubieras revisado redundancia despues de las cuatro pasadas»*— y la
    # respuesta es que si se reviso: los cuatro cortes estaban escritos en la
    # base, en estado «pendiente», desde antes de montar.
    #
    # Va **antes** de `revalidado` a proposito. La segunda valoracion juzga
    # entrega y ritmo, y tiene que juzgarlos sobre la pieza sin lo que sobra;
    # ademas las notas se estampan con la huella del montaje en que se
    # apuntaron, asi que si el corte cambia primero, las notas quedan huerfanas.
    (5.2, "recortado", "scripts/revision.py --aplicar {n}"),
    (5.5, "revalidado", None),       # servicio de IA con decision acotada
    (6, "cosido", "scripts/costuras.py {n}"),
    # **Y un ultimo repaso de redundancia, con la pieza ya cosida.** Jaime:
    # *«revisemos si otra pasada extra de redundancia al final antes de
    # renderizar vale la pena — siempre»*. La de la fase 5 juzga el corte de
    # entonces, y entre medias `fijar`, `revalidado` y `cosido` lo rehacen:
    # medido en una tarde, la misma repeticion volvio tres veces. Va aqui
    # porque es el ultimo punto donde el texto ya esta cerrado y cortar
    # todavia no obliga a rehacer descripciones ni recortes.

    (6.5, "repasado", None),
    (7, "descrito", "scripts/describir.mjs {n}"),
    # **La composicion son dos pasos, no uno con dos sombreros.** Regla de
    # Jaime: *«un agente se dedica a planear y verificar y otro agente a
    # disenar»*, *«son dos tareas diferentes»*, *«uno define lo que va a haber y
    # el otro lo monta»*, *«una cadena de produccion agentica»*.
    #
    # `descrito` define QUE va a haber —que etapas componen y que tiene que
    # quedar dicho en cada una, que se ve mirando el argumento entero— y ademas
    # **escribe el contrato del siguiente**: *«el contrato del segundo lo crea el
    # primero»*. Este monta: forma, copy y familia.
    #
    # Va antes de `cortado` porque montar sobre un corte que todavia puede
    # moverse es pagarlo dos veces, y despues de `descrito` porque sin encargo no
    # hay nada que disenar.
    (7.5, "disenado", None),         # servicio de IA: el diseno grafico
    (8, "cortado", "scripts/cortar.py {n}"),
    (10, "verificado", "scripts/verificar.py {n}"),
    (11, "montado", "scripts/montar.sh {n}"),
    # **Nivelar y medir el sonido son pasos de la linea, no algo que yo haga
    # despues.** Regla de Jaime, y viene de verme hacerlo a mano: *«integra todo
    # al contrato, no debe ser por fuera del pipeline para la proxima»*.
    #
    # Los dos existian como scripts sueltos —`sonoridad.sh` desde hace dias,
    # `suena.py` desde hoy— y **no los llamaba nadie**, que en este proyecto
    # significa que no existen: los seis salian a −10 LUFS con pico +0,1 dBTP y
    # la tabla `medicion` llevaba seis tipos declarados y cero filas.
    #
    # Van ANTES de `revisado` a proposito: el criterio humano es el escalon mas
    # caro, y gastarlo en una pieza a un nivel que la plataforma va a cambiar es
    # pedirle que juzgue algo que no es lo que se publica.
    #
    # Nivelar **no es «audio adicional»** —eso son la musica y los efectos, que
    # siguen fuera hasta que apruebe—: es dejar la pieza donde las plataformas
    # normalizan, para que el nivel sea una decision del montaje y no de donde
    # se publique.
    (11.2, "nivelado", "scripts/sonoridad.sh {n}"),
    # Y medir como suena, que es lo unico que tengo en lugar de oido. Jaime:
    # *«no se escucha con subtitulos, el sonido no es escrito»*.
    (11.4, "medido", "scripts/suena.py {n} --guardar"),
    # **El criterio humano es el escalon mas caro, y por eso va aqui.** Jaime:
    # *«lo mas caro es criterio humano, por eso es el paso anterior a la
    # aprobacion»*. Mirar una pieza montada cuesta su tiempo y su atencion, asi
    # que se hace **una vez** y sobre algo que ya paso todos los filtros baratos.
    # **El diseñador revisa lo que salió, y es su segundo momento.** Jaime:
    # *«que lo revise el diseñador como paso final»*, *«asegurate de que las
    # piezas del renderizado sean revisadas por el ultimo agente y que todo
    # este en el pipline»*.
    #
    # Va DESPUES de nivelar y medir, y ANTES de que la mire el: el criterio
    # humano es el escalon mas caro del embudo, y gastarlo en una pieza con un
    # silencio de seis segundos es tirarlo. Todos los pasos anteriores juzgan lo
    # que se va a montar; este es el unico que mira lo que salio.
    (11.6, "visto", None),
    (12, "revisado", None),          # el mira y anota; lo mueve el
    (13, "aprobado", None),          # lo mueve Jaime, no un servicio
    # **La voz virgen sale DESPUES de aprobar, no antes.** Regla de Jaime:
    # *«o mejor despues de aprovacion dame un audio con mi voz y solo mi voz
    # virgen»*.
    #
    # Estaba en la fase 9, antes de montar, y eso es trabajo tirado en cuanto la
    # revision mueve un corte: el audio exportado deja de corresponder a la
    # pieza, y encima habria pasado por Adobe Podcast —que es manual y en
    # minutos suyos— para nada. Es la misma cuenta que le hizo quitar la musica
    # de las piezas sin aprobar: *«sera mas facil con el audio final y
    # definitivo, menos retrabajo»*.
    #
    # Aqui el corte ya lo cerro el, asi que lo que se exporta es lo que va a
    # sonar en la entrega.
    (13.5, "voz_entregada", "scripts/voz-limpia.py --exportar {n}"),
    (14, "voz_limpia", "scripts/voz-limpia.py {n}"),
    (15, "masterizado", "scripts/musica.sh {n}"),
    # **Estaba en la tabla y no aqui.** La tabla `fase` la tenia en 15,5 y el
    # motor la recorria —con `ServicioRespaldo` registrado—, pero el camino
    # declarado no la nombraba: dos respuestas a «¿que camino hay?».
    (15.5, "respaldado", None),      # servicio de IA: las fuentes de cada cifra
    (16, "publicado", "scripts/publicar.py --finales {n}"),
]


_CON_VECES = []


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    if not _CON_VECES:
        # La columna de las vueltas iguales (C-660), una vez por proceso.
        try:
            c.execute("alter table video_fase add column veces integer")
        except sqlite3.OperationalError:
            pass
        _CON_VECES.append(True)
    return c


def camino():
    """El camino de fases, en orden. Es un dato, no código.

    Se excluye `preparado`, que es una fase de fragmento heredada y no del ciclo
    de la pieza: mezclarlas haría que el motor moviera piezas por una etiqueta
    que habla de otra cosa.
    """
    con = _con()
    fs = [dict(r) for r in con.execute(
        "select id, nombre, orden, servicio from fase where orden > 0"
        " and nombre <> 'preparado' order by orden")]
    con.close()
    return fs


def antes_de(fase):
    """Desde donde se vuelve a correr ese paso. **No es su propia etiqueta.**

    Una etiqueta nombra el paso YA HECHO: dejar la pieza en `descrito` es
    dejarla con la descripcion por buena, asi que lo siguiente que corre es
    `disenar` y el compositor no vuelve a mirar nada.

    La regla estaba escrita en `avanzar._antes_de` y **la otra puerta no la
    preguntaba**: `puertas.del_tiquet` mandaba la pieza a la fase que el tiquet
    nombra, tal cual. Medido el 9-9-2026: el tiquet #289 de reel-03 pedia
    «descrito», la puerta dejo la pieza en `descrito`, y de ahi lo unico que
    podia correr era el disenador — el compositor, que es quien lo atiende, no
    entraba nunca. Es la misma averia del 8-9 con reel-03 y reel-05, que
    entraron en `descrito` y salieron a `disenado` el mismo segundo.

    Vive aqui porque el orden es de `CICLO`, y las dos puertas lo preguntan.
    """
    if not fase:
        return None
    ruta = camino()
    i = next((k for k, f in enumerate(ruta) if f["nombre"] == fase), None)
    return ruta[i - 1]["nombre"] if i else fase


def fase_de(pieza):
    return pieza.fase


def _fallo_antes(video_id, fase_id, motivo):
    """¿Esta fase ya habia fallado por lo mismo? Entonces no es una espera."""
    con = _con()
    n = con.execute(
        "select coalesce(sum(coalesce(veces, 1)), 0) from video_fase where video_id = ?"
        " and fase_id = ? and por_que is not null and por_que <> ''",
        (video_id, fase_id)).fetchone()[0]
    con.close()
    return n > 1


#: A cuántas vueltas iguales se dice en voz alta que la pieza sigue igual (C-660).
AVISA = (6, 12, 24, 48, 96)


def vueltas_atras(video_id, fase) -> list:
    """Lo que devolvió la pieza desde `fase` desde la última vez que la pasó (C-660)."""
    con = _con()
    pasa = con.execute("select coalesce(max(id), 0) from video_fase where video_id = ?"
                       " and fase_id = ? and (por_que is null or por_que = '')",
                       (video_id, fase["id"])).fetchone()[0]
    filas = con.execute("select por_que, coalesce(veces, 1) from video_fase"
                        " where video_id = ? and id > ?"
                        " and por_que like ?", (video_id, pasa,
                                                f"vuelve desde {fase['nombre']}:%")).fetchall()
    con.close()
    return [r[0].split(": ", 1)[-1] for r in filas for _ in range(r[1])]


def anotar(video_id, fase_id, por_que=None):
    con = _con()
    # **El mismo estado se cuenta, no se repite** (C-660). El disparador da una
    # vuelta cada 30 s y anotaba la espera en cada una: el 83 % de las 11.428
    # filas de W40 era el mismo «espera al visto» o «no llega a una idea»
    # escrito otra vez, y el registro dejaba de decir cuándo cambió algo. La
    # fila se queda con la hora en que empezó y cuenta las vueltas en `veces`.
    ult = con.execute("select id, fase_id, por_que, coalesce(veces, 1) as veces"
                      " from video_fase where video_id = ? order by id desc limit 1",
                      (video_id,)).fetchone()
    if por_que and ult and ult["fase_id"] == fase_id and ult["por_que"] == por_que:
        con.execute("update video_fase set veces = ? where id = ?",
                    (ult["veces"] + 1, ult["id"]))
        con.commit()
        r = con.execute("select slug from video where id = ?", (video_id,)).fetchone()
        con.close()
        if ult["veces"] + 1 in AVISA and r:
            import registro
            registro.aviso("avanzar", "la pieza sigue igual", toma=r["slug"],
                           detalle=f"{r['slug']}: {ult['veces'] + 1} vueltas igual — {por_que}"[:600])
        return
    con.execute("insert into video_fase (video_id, fase_id, entro, por_que)"
                " values (?,?,?,?)",
                (video_id, fase_id, datetime.datetime.now().isoformat(
                    timespec="seconds"), por_que))
    con.commit()
    r = con.execute("select slug from video where id = ?", (video_id,)).fetchone()
    con.close()
    # **Y se publica.** Mover la pieza y decirlo son lo mismo: un estado que solo
    # vive en la base no lo puede leer quien tiene `Read` y `Write` y nada mas,
    # que son los dos oficios de la linea. Ver `dominio/estado.py`.
    try:
        from . import estado as _e
        if r:
            _e.escribe(r["slug"])
    except Exception:                              # noqa: BLE001
        pass


#: **Qué eslabón de `cadena.py` produce cada fase**, para las que producen un
#: fichero. Si ese eslabón está al día, la fase no tiene trabajo que hacer.
#:
#: `montar.sh` ya le pregunta a la cadena antes de cortar, de renderizar y de
#: mezclar; el motor no preguntaba, así que al llegar a `masterizado` volvía a
#: mezclar lo que la fase `montado` acababa de mezclar. El mismo trabajo, dos
#: veces, por el mismo camino — y era lo que quedaba del punto 8 de
#: `docs/rendimiento.md`: `montar.sh` hacía el trabajo de otras cinco fases y
#: el motor lo repetía detrás.
#:
#: **Sólo las que producen un FICHERO declarado en la cadena.** `medido`
#: —`suena.py`— escribe filas en `medicion`, y un fichero al día no dice nada
#: de si la medida se tomó: saltarla sería dar por hecho lo que no se hizo. Es
#: la misma frontera que separa un artefacto de una decisión.
ESLABON_DE = {
    "montado": "render",
    "masterizado": "entrega",
}


#: Fase a la que vuelve una pieza cuyo render ya no corresponde a su corte.
VUELVE_SI_CADUCO = "verificado"


def _render_caduco(pieza):
    """El fichero entregado, ¿es mas viejo que el corte del que sale?

    **Una fase que dice «hecho» sin artefacto es la forma exacta en que este
    proyecto pierde el estado.** Paso dos veces el mismo dia: `montar.sh` se
    saltaba la pieza bloqueada y salia con exito, asi que reel-01 quedo en
    `montado` con el mp4 de siete horas antes; y despues, con el corte
    recalculado por `a_lo_callado`, reel-02 y reel-03 seguian en `montado` y
    `avanzar` no las tocaba —no hay salto que dar desde el final del camino—,
    de modo que se entregaba un video anterior al arreglo.

    Devolverlas a mano es el parche. Regla de Jaime: *«si sale error, paras,
    reparas el pipeline, no un parche; el problema resuelto y vuelves a
    correr»*. Asi que la comprobacion es del motor: **el render tiene que ser
    mas nuevo que el EDL del que sale.** Si no lo es, la pieza no esta montada,
    diga lo que diga la etiqueta.

    No se compara contra el codigo ni contra la fecha del ultimo commit: se
    compara contra el corte, que es el unico insumo que define lo que el render
    tiene que mostrar. Un cambio de codigo que no mueve el corte no obliga a
    rehacer nada.
    """
    edl = os.path.join("ads", pieza.slug, "edl-sell.json")
    if not os.path.exists(edl):
        return None
    # **Lo aprobado no se devuelve, y esta es la linea que le faltaba a C-348.**
    #
    # Aquella guarda le pregunto a la cadena entera —bien— y arrastro a
    # `verificado` cuatro piezas firmadas: se revirtio por eso. Ahora hay con
    # que distinguirlas, porque el segmento sabe decir quien lo aprobo. Una
    # pieza firmada por Jaime sale de la cinta y no vuelve por una fecha.
    try:
        from . import segmento as _sg

        if _sg.aprobada(pieza.slug):
            return None
    except Exception:                              # noqa: BLE001
        pass
    n = int(pieza.slug[-2:])
    video = rutas.salida("reels", f"reel-R{n}.mp4")
    if not os.path.exists(video):
        return f"no hay render de {pieza.slug}: la fase dice montado y el fichero no esta"
    # **Y montada quiere decir con SU audio, no con cualquiera.**
    #
    # Jaime, en una frase que corrige como estaba declarado esto: *«si el audio
    # no esta bien el video no esta bien»*. Yo habia contado la entrega de R1
    # como buena separando las dos cosas —«el video esta bien, el problema era
    # solo el audio»— y esa separacion no existe: una pieza con la voz de otro
    # montaje encima no esta a medias, esta mal.
    #
    # Lo que la dejo pasar fue mirar solo la duracion. La pista de reel-01 duraba
    # 102,92 s contra 96,34 del corte, se recorto a la duracion justa y entro con
    # contenido de una edicion anterior: desfasada de principio a fin.
    entrega = rutas.salida("entrega", f"reel-R{n}.mp4")
    if os.path.exists(entrega):
        try:
            import sys as _s
            _s.path.insert(0, os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))))
            import importlib
            _vl = importlib.import_module("voz-limpia".replace("-", "_"))
        except Exception:                          # noqa: BLE001
            _vl = None
        if _vl and hasattr(_vl, "_corresponde"):
            cerca = _vl._corresponde(entrega, video)
            if cerca is not None and cerca < 0.35:
                return (f"la entrega de {pieza.slug} lleva audio que no es el de"
                        f" su corte (parecido {cerca:.2f}): montada con la voz de"
                        f" otra edicion")
    # **La huella manda: dice lo que el fichero DIBUJO, no cuando se escribio.**
    #
    # Jaime, tras tres dias con el mismo video: *«con una que no cuadre es
    # suficiente para saber que eso no es lo que se mando a render»*. Todo lo de
    # abajo —comparar la fecha del mp4 con la del EDL, con la de `escena_desc`—
    # es deduccion, y se equivoco en las dos direcciones: no vio que el bundle
    # servia un spec cacheado de hacia dias, y rehizo renders que estaban bien.
    #
    # `reel-RN.mp4.huella` lleva el sha1 del spec que ese fichero dibujo. Si no
    # coincide con el spec de ahora, lo que hay en disco no es lo que se compuso.
    # Sin adivinar y sin mirar un frame.
    _h = _huella_del_spec(pieza.slug)
    if _h:
        _puesta = None
        try:
            with open(video + ".huella", encoding="utf-8") as f:
                _puesta = f.read().strip()
        except OSError:
            _puesta = None
        if _puesta != _h:
            return (f"el render de {pieza.slug} dibujo otra cosa"
                    f" ({_puesta or 'sin huella'} != {_h}): no es lo que se"
                    f" compuso")
        # **La huella contesta por SU eslabon, no por los once.** Si coincide,
        # el render dibujo el spec de ahora — y eso no dice nada de si el spec
        # sale de un plan viejo. Devolver `None` aqui era darle a la huella una
        # autoridad que no tiene, y por eso `_render_caduco` decia «al dia» de
        # reel-05 mientras la cadena la daba por caducada.
    # **Y si no hay huella, la pregunta es de la cadena. Una sola.**
    #
    # Esto comparaba a mano la fecha del mp4 con la del EDL y con la de
    # `escena_desc`. `cadena.py` compara los ONCE eslabones —y ademas contra la
    # version del codigo que los hizo—, asi que eran dos guardas contestando
    # «¿el artefacto corresponde?» con distinta vara. Medido el 10-9-2026 sobre
    # reel-05: la cadena decia «out/reels/reel-R5.mp4 es mas viejo que
    # src/reels.json» y esto decia «al dia», sobre la misma pieza y a la vez.
    #
    # Aqui se queda lo que la cadena NO sabe —la huella de lo que el fichero
    # dibujo y el audio de la entrega— y lo demas se le pregunta a ella.
    try:
        import cadena as _cad

        malo = _cad.desde(n)
        # **Cada una contesta por lo suyo y no se pisan.** De `render` en
        # adelante manda la huella —compara lo que el fichero DIBUJO, no cuando
        # se escribio, que es lo que rehacia renders buenos—; de `spec` hacia
        # atras manda la cadena, que es la unica que mira esos eslabones. El
        # corte esta en el indice de `render`, y sale de la propia lista.
        corte = next((i for i, e in enumerate(_cad.ESLABONES)
                      if e[0] == "render"), 99)
        if malo and malo[0] < corte:
            return (f"la cadena de {pieza.slug} esta caducada en"
                    f" «{malo[1]}»: {malo[3]}")
    except Exception:                              # noqa: BLE001
        pass
    return None


def _huella_del_spec(slug: str):
    """La huella que el spec de AHORA declara para esa pieza. `None` si no hay.

    Se lee de `src/reels.json`, que es lo que el render dibuja. Si no existe o no
    trae huella, se cae al metodo viejo de fechas: una pieza sin spec no puede
    quedarse sin comprobar.
    """
    import json

    try:
        n = int(slug[-2:])
        with open("src/reels.json", encoding="utf-8") as f:
            for p in json.load(f):
                if p.get("id") == f"Reel-R{n}":
                    return p.get("huella")
    except (OSError, ValueError, TypeError):
        return None
    return None
