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
    (16, "publicado", "scripts/publicar.py --finales {n}"),
]


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
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


def fase_de(pieza):
    return pieza.fase


def _fallo_antes(video_id, fase_id, motivo):
    """¿Esta fase ya habia fallado por lo mismo? Entonces no es una espera."""
    con = _con()
    n = con.execute(
        "select count(*) from video_fase where video_id = ? and fase_id = ?"
        " and por_que is not null and por_que <> ''", (video_id, fase_id)).fetchone()[0]
    con.close()
    return n > 1


def anotar(video_id, fase_id, por_que=None):
    con = _con()
    con.execute("insert into video_fase (video_id, fase_id, entro, por_que)"
                " values (?,?,?,?)",
                (video_id, fase_id, datetime.datetime.now().isoformat(
                    timespec="seconds"), por_que))
    con.commit()
    con.close()


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
    n = int(pieza.slug[-2:])
    video = rutas.salida("reels", f"reel-R{n}.mp4")
    if not os.path.exists(video):
        return f"no hay render de {pieza.slug}: la fase dice montado y el fichero no esta"
    if os.path.getmtime(video) < os.path.getmtime(edl):
        return (f"el render de {pieza.slug} es anterior a su corte"
                f" — se rehace, la etiqueta no basta")
    # **Y la descripcion tambien cambia el video.** El corte decide que se oye;
    # la descripcion decide los tableros y lo que se lee. Comparar solo con el
    # EDL dejaba pasar una pieza re-descrita: reel-03 y reel-06 quedaron
    # montadas con la descripcion vieja porque su corte no se habia movido.
    con = _con()
    f = con.execute("select max(fecha) from escena_desc where video_slug = ?",
                    (pieza.slug,)).fetchone()[0]
    con.close()
    if f:
        try:
            descrito = datetime.datetime.fromisoformat(f).timestamp()
        except ValueError:
            descrito = 0
        if os.path.getmtime(video) < descrito:
            return (f"el render de {pieza.slug} es anterior a su descripcion"
                    f" — los tableros y los subtitulos salen de ahi")
    return None
