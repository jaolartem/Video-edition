"""La puerta del camino. Nada se renderiza sin pasar por aquí.

Regla de Jaime, y viene de un fallo que costó los seis vídeos: *«el camino es
obligatorio siempre, ninguno de esos vídeos es siquiera útil»*.

## Qué pasó, para que no vuelva a pasar

Él corrigió **cómo se mide la emoción**. De `voz_st` cuelgan cuatro reglas más
—el umbral de lectura plana, el envío a tablero, el tratamiento y el reparto de
etapas— y yo **sólo verifiqué la escala que había cambiado**. Cuando vi los
tableros dispararse recalibré el umbral y ahí paré: no volví a leer una sola
pieza contra el libreto.

Resultado medido: `escena_desc` —integridad, tratamiento, prioridad— llevaba seis
horas sin tocarse mientras los EDL se regeneraban una docena de veces. El
diagnóstico de integridad que estaba dando **describía un montaje que ya no
existía**. Y por eso el reel 3 llegó con el gancho en un tablero, la tesis
borrada y el precio fuera: nada de eso es emocionalidad, es cobertura e
integridad, que es justo lo que dejé de mirar.

Su diagnóstico fue exacto: *«cada cambio en una parte del proceso lo tomas como
un cambio de proceso, y al evaluar la emocionalidad dejaste de lado el resto»*.

## Por qué una puerta y no una lista

Las comprobaciones ya existían —integridad, cobertura, caminos, presencia— pero
**sueltas**, como scripts que hay que invocar. Las guardas sí paraban el lote
porque están dentro del camino; las demás dependían de que yo me acordara. Una
comprobación que depende de la memoria de alguien no es una comprobación.

Aquí corren **como conjunto** y el paso sale con código 1: `montar.sh` no
renderiza y `pipeline.sh` no sigue.

    python scripts/verificar.py          # los seis
    python scripts/verificar.py 3        # sólo el reel 3
    python scripts/verificar.py --avisa  # informa y no bloquea
"""
import argparse
import json
import os
import re
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
from servicios import Pieza  # noqa: E402
import rutas  # noqa: E402

BASE = "ads/decisiones.db"


def revisar(slug):
    """Todo lo que tiene que cumplirse. Devuelve la lista de motivos para parar."""
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return [f"{slug}: no hay EDL"]
    edl = json.load(open(ruta, encoding="utf-8"))
    mal = []
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row

    # 1 · **La descripción caduca cuando cambia EL TEXTO, no la fecha.**
    #
    # La primera versión comparaba marcas de tiempo: si el EDL se reescribía,
    # las seis piezas quedaban invalidadas aunque las etapas dijeran lo mismo, y
    # eso obligaba a rehacer las 52 descripciones por cualquier ajuste. Jaime lo
    # corto: *«tenemos una estructura modular para poder apegarnos a la
    # estructura sin tener que cambiar todo, pero si a cada ajuste de tuerca
    # cambias el motor nunca vamos a llegar a ningún lado»*.
    #
    # Comparando el texto, **caduca sólo la etapa que se movió**. Las demás
    # siguen valiendo, que es exactamente para lo que existe la modularidad.
    dice = Pieza(int(slug[-2:])).texto
    filas = con.execute(
        "select etapa_orden, sobre_texto, integridad, remedio from escena_desc"
        " where video_slug = ?", (slug,)).fetchall()
    if not filas:
        mal.append(f"{slug}: sin descripción de escena — corre el paso 4")
    else:
        viejas = []
        for f in filas:
            b = f["etapa_orden"]
            ahora = " ".join((dice.get(b) or "").split())
            antes = " ".join((f["sobre_texto"] or "").split())
            if b in dice and antes and antes != ahora:
                viejas.append(b)
        if viejas:
            mal.append(
                f"{slug}: la descripción de las etapas {viejas} habla de otro"
                f" texto — vuelve a describir ESAS, no la pieza entera.")

    # 1b · **Una etapa no puede sonar dos veces.**
    #
    # Este es el que faltaba, y su ausencia es la razon de que un fallo caro
    # pasara desapercibido: `_mover_bordes` declaraba sin retirar lo anterior,
    # reel-05 quedo diciendo su cierre entero dos veces, la pieza paso de 105 a
    # 157 segundos — y **la puerta la dejo pasar**, porque miraba que cada
    # fijado estuviera en el EDL y ninguno sobrara.
    #
    # Se mira en los dos sitios a proposito, porque son dos averias distintas:
    # en la declaracion es una contradiccion —«esta etapa es esto, y otra vez
    # esto»—, y en el montaje es lo que el espectador oye. Puede haber lo
    # segundo sin lo primero: la declaracion se arreglo y el EDL se quedo con la
    # version vieja, que es justo cuando hay que correr `fijar --rehacer`.
    try:
        import fijar as _fj

        for beat, x, y in _fj.solapes(slug):
            mal.append(f"{slug} e{beat}: los tramos declarados se pisan"
                       f" ({x['desde']}-{x['hasta']} y {y['desde']}-{y['hasta']})"
                       f" — una etapa no se declara dos veces")
    except Exception:                              # noqa: BLE001
        pass
    _por_beat = {}
    for _r, _d in zip(edl.get("segmentos") or [], edl.get("detalle") or []):
        _por_beat.setdefault(_d.get("beat"), []).append((_d.get("toma"), _r))
    for _b, _v in sorted(_por_beat.items(), key=lambda x: (x[0] is None, x[0])):
        _v = sorted(_v, key=lambda x: (str(x[0]), x[1][0]))
        for (_t1, _a), (_t2, _c) in zip(_v, _v[1:]):
            if _t1 == _t2 and _c[0] < _a[1] - 1e-3:
                mal.append(
                    f"{slug} e{_b}: el montaje repite {_a[0]:.1f}-{_a[1]:.1f}s"
                    f" y {_c[0]:.1f}-{_c[1]:.1f}s de la misma cinta — se va a"
                    f" oir dos veces. Corre: python scripts/fijar.py"
                    f" {int(slug[-2:])} --rehacer {_b}")
                break

    # 2 · **Ninguna etapa se queda muda.** Ni sin material ni con dos palabras:
    # una etapa que no dice nada es una etapa que no está.
    beats_edl = {d.get("beat") for d in edl["detalle"]}
    tablero = {d.get("beat") for d in (edl.get("sin_toma") or [])}
    for b, t in sorted(dice.items()):
        if len(t.split()) < 4:
            mal.append(f"{slug} e{b}: dice «{t}» — no llega a una idea")

    # 3 · **El gancho es su cara.** Nunca un tablero: contradice el camino
    # `portada` entero, y ya paso en reel-03.
    if 1 in tablero:
        mal.append(f"{slug}: la etapa 1 va a tablero, y el gancho tiene que ser"
                   f" su cara. Elige otra apertura.")

    # 4 · **Las etapas obligatorias existen**, con toma o con tablero.
    #
    # **Salvo la que se decidio sacar.** Una etapa cortada a proposito no tiene
    # material ni tablero, y no deberia: la puerta la contaba como falta y la
    # pieza no podia avanzar por no tener algo que alguien mando quitar. Paso
    # con el mecanismo del reel-01, que Jaime mando fuera entero.
    #
    # La diferencia entre «falta» y «se quito» no es del montaje: esta en el
    # log. Una nota de corte aplicada, con su ancla y su porque, es la prueba de
    # que hubo una decision — y una decision no es un agujero.
    quitadas = set()
    try:
        _c = basedatos.abrir(BASE)
        for (q,) in _c.execute(
                "select que from revision where video_slug = ? and accion='cortar'"
                " and estado='aplicada' and regla='seccion que sobra'", (slug,)):
            for _b in re.findall(r"e(\d+)", q or ""):
                quitadas.add(int(_b))
        _c.close()
    except Exception as e:                         # noqa: BLE001
        # **Y si no se puede saber, no se da por hecho que no hay ninguna.**
        # Este `pass` dejaba `quitadas` vacio ante cualquier tropiezo —la base
        # tomada por otra corrida, por ejemplo— y entonces la puerta acusaba de
        # falta una etapa que alguien mando quitar. Un fallo de lectura no es
        # una respuesta: se dice y se para por lo que es.
        mal.append(f"{slug}: no se pudo leer que etapas se quitaron ({e})."
                   f" Vuelve a correr cuando la base este libre.")
    for f in filas:
        b = f["etapa_orden"]
        if (b not in beats_edl and b not in tablero
                and int(b) not in quitadas):
            mal.append(f"{slug} e{b}: sin material y sin tablero")

    # 5 · **Ningún pedido de IA sin contestar.**
    #
    # Un paso de IA con el pedido abierto significa que la pieza se monto sin esa
    # decision — sin la lectura de redundancia, o sin la descripcion de escena. No
    # es un aviso: es que falta un paso del camino.
    import servicio as _sv
    abiertos = [p for p, sl, _ in _sv.pendientes() if sl == slug]
    if abiertos:
        mal.append(f"{slug}: pedido(s) de IA sin contestar: {abiertos}."
                   f" La pieza se montaria sin esa decision.")

    # **Nada se dice dos veces por culpa del corte.**
    #
    # Jaime: *«la redundancia o es explicita en el libreto, o es continua en la
    # grabacion; pero dejar enfasis cada corte no es enfasis sino ruido»*. Lo
    # que sobrevive aqui es lo tercero: el montaje pego dos tomas de la misma
    # frase y la pieza la dice dos veces.
    #
    # Existia el detector —`repeticiones.py`— y **no lo llamaba nadie**. Por eso
    # esta aqui: en la puerta, que es lo que no se puede saltar.
    import consulta as _cs

    # **La puerta para lo que hizo EL CORTE, y solo eso.**
    #
    # Paraba por cualquier repeticion pegada, y con eso se comio una
    # enumeracion correcta: «ni a su abogado ni a su contador» dice «ni a su»
    # dos veces porque el castellano lo pide. La distancia no las separa —el
    # ejemplo de ruido de este mismo comentario, «su negocio esta funcionando,
    # su negocio esta vendiendo», tiene la misma forma exacta—, asi que un
    # umbral no puede decidirlo: hay que entender la frase.
    #
    # Regla de Jaime, que es la que reparte: *«la redundancia o es explicita en
    # el libreto, o es continua en la grabacion; pero dejar enfasis cada corte
    # no es enfasis sino ruido»*. **La puerta es duena del corte.** Si las dos
    # veces caen en el mismo trozo, el hablante lo dijo asi de seguido y la
    # puerta no tiene nada que arbitrar; si caen en trozos distintos, la pego
    # el montaje y eso si es aritmetica.
    #
    # Y lo que no para tiene que ir a alguien: `repaso` lo recibe en su pedido
    # (`repeticiones`) y decide con la frase delante. Parar por algo que el que
    # compone no ve es dejar la pieza sin nadie que pueda arreglarla — el mismo
    # atasco de C-116, que costo dos vueltas contando el mismo fallo.
    for r in _cs.repetido(slug):
        if r["separadas_por"] <= 8 and not r["una_toma"]:
            mal.append(
                f"{slug} e{r['etapa']}: dice «{r['dice']}» dos veces seguidas"
                f" — es rearranque del hablante o repeticion del corte, no"
                f" enfasis")

    # 6a · **Una cifra en la descripción tiene que estar declarada.**
    #
    # Jaime cerró que la cifra de reel-05 e6 es $14.000 —*«los 300 los quité
    # porque complica las cuentas»*—, se aplicó, y **volvió**: al re-describir
    # la etapa, el paso copió el número viejo del texto anterior. La decisión
    # existía y no estaba registrada donde el paso siguiente la lee.
    #
    # El registro de cifras es la tabla `dato`. Una descripción que rotula un
    # importe que ninguna fila declara es una cifra inventada o una decisión
    # perdida, y las dos son cumplimiento. No se compara el texto entero: se
    # comparan los importes, que son explícitos y no admiten lectura.
    import re as _re

    _IMPORTE = _re.compile(r"\$ ?\d{1,3}(?:[.,]\d{3})+")

    def _importes(t):
        return {x.replace(" ", "").replace(".", ",") for x in _IMPORTE.findall(t or "")}

    # **El registro es de la PIEZA, no del beat.** Exigirlo por etapa obligaba a
    # duplicar la fila cada vez que una cifra se recuerda: reel-02 declara los
    # $189.000 en la etapa 3 y los vuelve a enseñar en el cierre, y eso no es una
    # cifra sin declarar — es la misma cifra. Lo que hay que impedir es que
    # aparezca en pantalla un importe que la pieza no declaró en ningún sitio.
    declarados = set()
    for f in con.execute(
            "select d.cifra, d.afirmacion from dato d"
            "  join video v on v.id = d.video_id where v.slug = ?", (slug,)):
        declarados |= _importes(f["cifra"]) | _importes(f["afirmacion"])
    for f in con.execute(
            "select etapa_orden, que_pasa, grafico, corrige_es from escena_desc"
            " where video_slug = ?", (slug,)):
        dice = set()
        for c in ("que_pasa", "grafico", "corrige_es"):
            dice |= _importes(f[c])
        sueltas = dice - declarados
        if sueltas:
            mal.append(
                f"{slug} e{f['etapa_orden']}: la descripción rotula"
                f" {', '.join(sorted(sueltas))} y ninguna fila de `dato` lo"
                f" declara. O se declara con su fuente, o no sale en pantalla.")

    # 6b · **El sonido también pasa por la puerta.**
    #
    # Jaime: *«el sonido también forma parte de la verificación final»*, dicho
    # después de oír el reel-01 montado y encontrar dos cosas que ninguna puerta
    # miraba: cortes que se oyen sucios y un tablero mudo.
    #
    # **Los cortes.** No se comprueba con una regla propia: se le pregunta al
    # paso que los arregla si todavía movería alguno. Una puerta con su propio
    # criterio se separa del arreglo en la primera corrección, y entonces avisa
    # de lo que ya está bien o calla lo que está mal. Aquí no puede pasar,
    # porque es el mismo código en seco.
    import costuras as _co

    quedan = _co.a_lo_callado(slug, ver=True, minimo=_co.PUERTA)
    if quedan:
        mal.append(f"{slug}: {quedan} corte(s) caen en pleno sonido y hay un"
                   f" punto callado a menos de 120 ms. Corre el paso `cosido`.")

    # **El tablero mudo.** Un tablero se construye por tiempo de lectura: cada
    # nodo entra cuando el anterior ya se pudo leer, o sea que **es una
    # animación**, y la ley del proyecto es que el sonido sigue al movimiento.
    # Jaime lo dijo así: *«el sonido del tablero deben ser las acciones animadas
    # del tablero»*. Un tablero sin `sound` es una animación que nadie oye.
    spec = "src/reels.json"
    if os.path.exists(spec):
        try:
            n_reel = int(slug[-2:])
            for r in json.load(open(spec, encoding="utf-8")):
                if r.get("id") != f"Reel-R{n_reel}":
                    continue
                mudos = [b for b in r.get("boards", [])
                         if not (b.get("props") or {}).get("sound")]
                if mudos:
                    mal.append(
                        f"{slug}: {len(mudos)} tablero(s) sin sonido. El tablero"
                        f" se construye por tiempo de lectura: es animación, y"
                        f" el sonido sigue al movimiento.")
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    # 7 · **Un tramo fijado que no llegó al corte es una decisión perdida.**
    #
    # Fijar una etapa es declarar cuál es su tramo, y esa decisión tiene que
    # poder sobrevivir a rehacer la selección. Si el EDL no la lleva, alguien
    # decidió y el montaje no se enteró — que es la forma exacta en la que este
    # proyecto perdía el estado antes de que fijar existiera.
    import fijar as _fj

    # **Se comprueba que el tramo esta REPRESENTADO, no que sea identico.** Un
    # recorte de redundancia posterior acorta legitimamente lo fijado: exigir el
    # rango exacto convertia cada recorte en un fallo de la puerta. Lo que no
    # puede pasar es que del tramo declarado no quede nada.
    for f in _fj.fijados(slug):
        dentro = any(d.get("beat") == f["beat"]
                     and min(b_, f["hasta"]) - max(a_, f["desde"]) > 0.1
                     for (a_, b_), d in zip(edl["segmentos"], edl["detalle"]))
        if not dentro:
            mal.append(
                f"{slug} e{f['beat']}: el tramo fijado"
                f" [{f['desde']}-{f['hasta']}] no dejo rastro en el corte."
                f" Corre: python scripts/fijar.py --aplicar {int(slug[-2:])}")

    # 7 · **Lo que Jaime pidió cortar está cortado.** Una nota pendiente con
    # ancla que ya no resuelve es una corrección perdida en silencio (C-79).
    #
    # **Y sólo las de ESTE montaje.** Una nota se estampa con la huella del
    # corte en que se apuntó y `revision.aplicar` se salta —con razón— las de
    # otro: hablan de un sitio que ya no existe. Pero la puerta las contaba
    # igual, así que la pieza quedaba bloqueada por tres notas que ningún paso
    # puede aplicar nunca. reel-06 se paró así con notas de un montaje anterior.
    #
    # Es la cuenta falsa contra la que ya avisa `revision.aplicar`: mientras el
    # número incluye lo inaplicable, tapa a la nota que sí falta. Las viejas se
    # quedan en la tabla —son el recorrido del vídeo— y dejan de ser tarea.
    try:
        import modelo as _mo

        _h = _mo.huella_edl(slug)
    except Exception:                              # noqa: BLE001
        _h = None
    pend = con.execute(
        "select count(*) from revision where video_slug = ? and accion='cortar'"
        " and estado='pendiente' and huella is ?", (slug, _h)).fetchone()[0]
    if pend:
        mal.append(f"{slug}: {pend} corte(s) de revisión sin aplicar")
    con.close()
    return mal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--avisa", action="store_true",
                    help="informa y no bloquea")
    a = ap.parse_args()
    todo = []
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        mal = revisar(slug)
        todo += mal
        print(f"{slug}: {'OK' if not mal else str(len(mal)) + ' motivo(s)'}")
        for m in mal:
            print(f"    · {m}")
    if todo and not a.avisa:
        print(f"\nEL CAMINO SE PARA — {len(todo)} motivo(s). Nada se renderiza"
              f" hasta que esten resueltos.")
        sys.exit(1)
    print("\nverificacion: todo en pie" if not todo else
          "\n(--avisa: no bloquea)")


if __name__ == "__main__":
    main()
