"""El motor: un camino de fases, y nada más.

Regla de Jaime: *«el principal es un camino de fases, no un monolito de
servicios desconectados»*. Y la de antes, que la sostiene: *«las fases y los
estados son etiquetas que llaman servicios; si una etiqueta está en un paso,
entonces avanza automáticamente en ese paso, y si no avanza pues para eso es el
log»*.

Así que aquí sólo hay tres cosas: **dónde está la pieza**, **qué servicio la
mueve** y **qué se apunta cuando no se mueve**. El cómo de cada paso vive en su
servicio (`scripts/servicios/`), y el orden vive en la tabla `fase`. Este fichero
no sabe que por debajo hay scripts, ni cuáles.

Lo que eso permite: añadir un paso es insertar una fila y registrar un objeto.
Cambiar cómo se hace un paso es tocar una clase. Ninguna de las dos cosas se
toca aquí.

    python scripts/avanzar.py            # mueve todo lo que se pueda
    python scripts/avanzar.py 3          # solo el reel 3
    python scripts/avanzar.py --ver      # el camino, sin recorrerlo
    python scripts/avanzar.py --paso 1   # un salto por pieza
"""
import argparse
import datetime
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registro  # noqa: E402
import servicios  # noqa: E402
from servicios import Pieza  # noqa: E402
import rutas  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    c = sqlite3.connect(BASE)
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


def avanzar(n, ver=False, tope=None):
    """Recorre el camino con una pieza hasta donde pueda.

    Se para por tres motivos y **son distintos**: llegó al final, espera a
    alguien, o un servicio no pudo. Sólo el tercero es un fallo; confundirlos
    hace que una pieza esperando aprobación parezca rota.
    """
    pieza = Pieza(n)
    if pieza.video_id is None:
        return None
    ruta = camino()
    actual = fase_de(pieza)
    if actual is None:
        actual = ruta[0]
        if not ver:
            anotar(pieza.video_id, actual["id"])
    # **Y si la etiqueta miente, se corrige antes de recorrer nada.**
    orden = {f["nombre"]: k for k, f in enumerate(ruta)}
    if orden.get(actual["nombre"], -1) >= orden.get("montado", 10 ** 9):
        caduco = _render_caduco(pieza)
        if caduco:
            destino = next((f for f in ruta if f["nombre"] == VUELVE_SI_CADUCO), None)
            if destino is not None:
                print(f"  {pieza.slug}: {caduco}")
                if not ver:
                    anotar(pieza.video_id, destino["id"], caduco)
                actual = destino

    saltos, motivo, atras = 0, None, {}
    while True:
        i = next((k for k, f in enumerate(ruta) if f["id"] == actual["id"]), None)
        if i is None or i + 1 >= len(ruta):
            motivo = "final del camino"
            break

        siguiente = ruta[i + 1]
        serv = servicios.para(siguiente["nombre"], siguiente["servicio"])
        if serv is None:
            motivo = f"«{siguiente['nombre']}» no tiene servicio"
            break

        puede, por_que = serv.puede(pieza)
        if not puede:
            motivo = f"{siguiente['nombre']}: {por_que}"
            break

        if ver:
            print(f"  {pieza.slug}: {actual['nombre']} -> {siguiente['nombre']}"
                  f"   [{type(serv).__name__}]")
            actual = siguiente
            saltos += 1
            if tope and saltos >= tope:
                break
            continue

        r = serv.correr(pieza)
        if not r.ok:
            motivo = f"{siguiente['nombre']}: {r.motivo}"
            anotar(pieza.video_id, actual["id"], motivo)
            registro.aviso("avanzar", "la pieza no avanza",
                           detalle=f"{pieza.slug}: {motivo}", eco=False)
            # **A la segunda, error.** Regla de Jaime: *«si algo no funciona a
            # la primera, paras y que genere error; corregimos y volvemos a
            # correr — para eso esta el log»*.
            #
            # Un paso que ya fallo antes y vuelve a fallar no es una espera: es
            # el mismo problema sin resolver, y seguir dandole vueltas lo
            # esconde. El motor se planta y sale con codigo 1; lo que hay que
            # arreglar queda en `registro` con su motivo.
            #
            # Una espera —un servicio de IA sin contestar— **no cuenta como
            # fallo**: ahi el paso no se rompio, esta pidiendo su turno.
            espera = "espera" in (r.motivo or "").lower()
            if not espera and _fallo_antes(pieza.video_id, actual["id"], motivo):
                raise SystemExit(
                    f"avanzar: {pieza.slug} lleva dos intentos fallando en"
                    f" «{siguiente['nombre']}» por lo mismo — {r.motivo}."
                    " Se para aqui a proposito: corrige y vuelve a correr,"
                    " que el detalle esta en el log.")
            break

        if r.volver_a:
            # **El ciclo, y acotado.** Un paso puede mandar la pieza atras
            # porque cambio algo que ya se habia dado por bueno. Se permite,
            # pero se cuenta: si no converge en tres vueltas es que hay algo
            # que no se arregla repitiendo, y entonces vale la regla de siempre
            # —*«el loop no es intentar hacer lo mismo con resultados
            # distintos»*— y se para con el motivo escrito.
            atras.setdefault(siguiente["nombre"], []).append(r.salida or "?")
            vueltas = atras[siguiente["nombre"]]
            if len(vueltas) > 3:
                # **Y el error trae el diagnostico, no la invitacion a
                # buscarlo.** Jaime: *«si pasa mas de 3 veces es un bug, y lo
                # bueno es que ya tendrias info para resolverlo»*. Esa info es
                # QUE se corto en cada vuelta: si son cortes distintos, la pieza
                # se esta desmontando poco a poco; si es el mismo tres veces,
                # algo lo esta devolviendo entre vuelta y vuelta — que es
                # exactamente la familia de fallos de esta sesion (C-105, C-107).
                # Ponerlo en el mensaje ahorra el rato de reconstruirlo del log.
                raise SystemExit(
                    f"avanzar: {pieza.slug} lleva {len(vueltas)} vueltas en"
                    f" «{siguiente['nombre']}» sin quedar limpia. Esto es un"
                    f" bug, no una espera. Lo que corto cada vuelta:"
                    + "".join(f"{chr(10)}    {k + 1}. {v}"
                              for k, v in enumerate(vueltas))
                    + f"{chr(10)}  Si es lo mismo cada vez, algo lo devuelve"
                      f" entre vueltas; si cambia, la pieza se esta"
                      f" desmontando.")
            destino = next((f for f in ruta if f["nombre"] == r.volver_a), None)
            if destino is None:
                motivo = f"{siguiente['nombre']}: no existe la fase «{r.volver_a}»"
                break
            anotar(pieza.video_id, destino["id"],
                   f"vuelve desde {siguiente['nombre']}: {r.salida}")
            print(f"  {pieza.slug}: {siguiente['nombre']} -> vuelve a"
                  f" {r.volver_a} ({r.salida})")
            actual = destino
            saltos += 1
            if tope and saltos >= tope:
                motivo = "tope de saltos"
                break
            continue

        anotar(pieza.video_id, siguiente["id"])
        actual = siguiente
        saltos += 1
        if tope and saltos >= tope:
            motivo = "tope de saltos"
            break

    return {"slug": pieza.slug, "fase": actual["nombre"], "saltos": saltos,
            "motivo": motivo}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true", help="el camino, sin recorrerlo")
    ap.add_argument("--paso", type=int, metavar="N",
                    help="como mucho N saltos por pieza")
    a = ap.parse_args()
    for n in (a.reels or rutas.piezas()):
        r = avanzar(n, ver=a.ver, tope=a.paso)
        if not r:
            continue
        print(f"{r['slug']}: {r['fase']}"
              + (f"  (+{r['saltos']})" if r["saltos"] else "")
              + (f"  — {r['motivo']}" if r["motivo"] else ""))


if __name__ == "__main__":
    main()
