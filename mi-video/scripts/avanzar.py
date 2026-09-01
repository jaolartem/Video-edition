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
import basedatos
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import planificador  # noqa: E402
import registro  # noqa: E402
import servicios  # noqa: E402
from servicios import Pieza  # noqa: E402
import rutas  # noqa: E402

BASE = "ads/decisiones.db"


# **Lo que una fase ES vive en el dominio**; aquí sólo se recorre. Se
# importan con su nombre de siempre porque `donde.py` y `aprobar.py` ya
# los llaman así, y mover algo no tiene por qué romper a quien lo usa.
from dominio.fase import (  # noqa: E402,F401
    _con, _fallo_antes, _render_caduco, anotar, camino, fase_de)


def avanzar(n, ver=False, tope=None, permiso=None):
    """**La frontera del enrutador.** Nada de aquí dentro puede escapar sin log.

    Regla de Jaime: *«todos los pasos con código van con try / if not para el log
    de errores»*, precisada después: *«en el enrutador»*. Y ahí está la razón de
    que vaya aquí y no dentro de cada función — un `try` por función esconde el
    fallo y lo devuelve convertido en dato tres pasos más allá; un `try` en la
    frontera **lo anota y para esa pieza**, que es lo que hace falta.

    Lo que cubre y antes no: `Pieza(n)`, `camino()`, `fase_de()`,
    `_render_caduco()` y los cinco `anotar()`. Todo eso es enrutado, no trabajo
    del paso, y si revienta el motor moría sin dejar dicho por qué.
    """
    import registro as _reg

    try:
        return _recorrer(n, ver=ver, tope=tope, permiso=permiso)
    except Exception as e:                         # noqa: BLE001
        slug = f"reel-{int(n):02d}"
        motivo = f"el enrutado revento: {type(e).__name__}: {e}"
        _reg.aviso("avanzar", "el enrutado revento",
                   detalle=f"{slug}: {motivo}"[:600], eco=True)
        return {"slug": slug, "fase": "?", "saltos": 0, "motivo": motivo[:300]}


def _recorrer(n, ver=False, tope=None, permiso=None):
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

        # El turno para este paso sobre esta pieza. Sin planificador no
        # hay turno que pedir y esto es transparente: ver `planificador.py`.
        #
        # **Y va dentro de un `try`, que es lo que faltaba para que esto sea un
        # enrutador.** Jaime: *«sin enrutador no hay ni ha habido pipeline»*, y
        # *«pueden ser etiquetas con try if, y con if not para la recoleccion de
        # errores en el log»*.
        #
        # Sin el `try`, una excepcion dentro de un paso no para esa pieza: mata
        # la corrida entera y se lleva por delante a las otras seis. Paso dos
        # veces la misma noche con `database is locked`, con las siete
        # respuestas de la ronda ya escritas y ninguna aplicada.
        #
        # Un enrutador no puede caerse porque un destino falle. Lo que hace es
        # **anotar cual fallo y seguir con los demas**, que es la diferencia
        # entre una linea y un script largo.
        try:
            if permiso is None:
                r = serv.correr(pieza)
            else:
                with permiso(serv, pieza):
                    r = serv.correr(pieza)
        except Exception as e:                     # noqa: BLE001
            motivo = f"{siguiente['nombre']} revento: {type(e).__name__}: {e}"
            anotar(pieza.video_id, actual["id"], motivo[:400])
            registro.aviso("avanzar", "el paso revento",
                           detalle=f"{pieza.slug}: {motivo}"[:600], eco=True)
            break
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
    ap.add_argument("--hilos", type=int, default=4, metavar="N",
                    help="cuantas piezas a la vez (1 = como antes)")
    ap.add_argument("--paso", type=int, metavar="N",
                    help="como mucho N saltos por pieza")
    ap.add_argument("--volver", metavar="FASE",
                    help="devuelve la pieza a esa fase y la vuelve a recorrer")
    ap.add_argument("--por-que", default="", metavar="RAZON",
                    help="por que vuelve; queda en el log de la pieza")
    a = ap.parse_args()

    # **Devolver una pieza a una fase es del motor, no de un apano.**
    #
    # Solo se podia volver desde dentro de un servicio (`Resultado.volver_a`) o
    # por el render caduco. Fuera de eso no habia manera, y eso deja un hueco
    # real: un pedido de IA contestado **satisface la puerta** —comprueba que el
    # fichero de respuesta exista— pero su decision no se aplica hasta que el
    # servicio corre otra vez. Sin poder devolver la pieza, la respuesta se
    # queda escrita y sin efecto, que es la forma de siempre de perder el
    # estado: la etiqueta dice hecho y el trabajo no esta.
    #
    # Con esto la pieza vuelve a recorrer el camino y **el servicio consume su
    # respuesta**, que es lo unico que convierte una decision en un montaje.
    if a.volver:
        con = _con()
        destino = con.execute("select id, nombre from fase where nombre = ?",
                              (a.volver,)).fetchone()
        con.close()
        if destino is None:
            raise SystemExit(f"avanzar: no existe la fase «{a.volver}»."
                             f" Mira la tabla `fase`.")
        for n in (a.reels or rutas.piezas()):
            pieza = Pieza(n)
            if pieza.video_id is None:
                continue
            razon = a.por_que or f"devuelta a «{a.volver}» a mano"
            if a.ver:
                print(f"  {pieza.slug}: volveria a {a.volver} ({razon})")
                continue
            anotar(pieza.video_id, destino["id"], razon)
            registro.aviso("avanzar", "pieza devuelta",
                           detalle=f"{pieza.slug} -> {a.volver}: {razon}",
                           eco=False)
            print(f"  {pieza.slug}: vuelve a {a.volver} ({razon})")
    # **Se recorre hasta que nadie se mueve, no una vez por pieza.**
    #
    # Las piezas comparten cintas. Recorriendo de una en una, la quinta afina
    # `20260825_151758` DESPUES de que la segunda ya haya dejado escrita su
    # pregunta sobre esa misma cinta — y entonces la pregunta de la segunda
    # cambia sola. Su respuesta, que era correcta, entra como «anterior al
    # pedido», se archiva, y se vuelve a preguntar lo mismo.
    #
    # Medido hoy: tres respuestas de redundancia —reel-02, reel-03 y reel-04—
    # archivadas en una sola corrida, con el trabajo ya hecho. El texto de
    # reel-02 paso de «100 dolares que el» a «100 dolares que recibe, el»
    # porque otra pieza mejoro la cinta compartida entre medias. Ninguna
    # respuesta estaba mal: cambio la pregunta debajo.
    #
    # Asi que primero se agota el trabajo determinista de TODAS, y solo la
    # ultima vuelta —en la que ya no se mueve nada— deja las preguntas escritas.
    # Un pedido abierto sobre un material que todavia puede cambiar es una
    # pregunta que no se puede contestar, y contestarla es trabajo tirado.
    piezas = list(a.reels or rutas.piezas())
    # **Las piezas que no comparten cinta trabajan a la vez.** El bucle de una
    # en una hacía que el paso más lento parase a las siete, incluidas las que
    # no dependían de él. Ver `planificador.py`.
    plan = planificador.Planificador(hilos=1 if (a.ver or a.paso) else a.hilos)
    ultimo, total = {}, {}
    # Con `--paso N` se pidio un numero de saltos, no que se agote: una vuelta.
    vueltas = 1 if (a.ver or a.paso) else 4
    for vuelta in range(1, vueltas + 1):
        movidos = 0
        hechos = plan.correr(piezas, lambda n: avanzar(
            n, ver=a.ver, tope=a.paso, permiso=plan.permiso))
        for n in piezas:
            r = hechos.get(n)
            if not r:
                continue
            ultimo[n] = r
            total[n] = total.get(n, 0) + r["saltos"]
            movidos += r["saltos"]
        if not movidos or vuelta == vueltas:
            break
        print(f"  -- se movio algo (vuelta {vuelta}): se recorre otra vez para"
              f" que ninguna pregunta quede escrita sobre material que aun"
              f" puede cambiar")
    for n in piezas:
        r = ultimo.get(n)
        if not r:
            continue
        saltos = total.get(n, r["saltos"])
        print(f"{r['slug']}: {r['fase']}"
              + (f"  (+{saltos})" if saltos else "")
              + (f"  — {r['motivo']}" if r["motivo"] else ""))


if __name__ == "__main__":
    main()
