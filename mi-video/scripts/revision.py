"""La revisión final: lo que Jaime quita mirando la pieza montada.

Regla que la creó: *«vamos a instaurar una última etapa, la revisión final; en
esta etapa quitamos partes de cada vídeo, haciendo ajustes finales»*. Y la parte
que la convierte en sistema y no en una lista de recados: *«importante, las
correcciones se van integrando para que se puedan automatizar, que sirvan de
entrenamiento»*.

## Por qué una tabla y no un mensaje

Un recado se atiende una vez. Una nota guardada con su tramo, su acción y **la
regla general que hay detrás** se atiende una vez y luego se automatiza — y a
partir de ahí ya no hay nota que atender, porque el defecto no vuelve a
producirse. Ése es el bucle que él pidió.

Cada nota lleva dos textos y no son el mismo:

- `que` — **sus palabras, literales**. No se reescriben ni se resumen: si dentro
  de tres semanas la regla que deduje resulta equivocada, lo que hay que releer
  es lo que dijo, no mi interpretación de lo que dijo.
- `regla` — la versión general. *«Desde el segundo 20 hasta el tablero sobra,
  sólo es una persona leyendo»* es una nota; *«un tramo largo de lectura sin
  tratamiento no aporta y se corta»* es una regla, y esa vale para las 16-50
  piezas.

Y `estado` cuenta en qué punto del bucle está cada una:

    pendiente     dicha, todavía no hecha
    aplicada      hecha en esta pieza, a mano
    automatizada  la regla vive en código: no vuelve a hacer falta
    sube          necesita una decisión suya antes de tocar nada

## Las dos pasadas

*«Este no pasa directo con las correcciones, pero en segunda revisión pasa.»*
Una pieza corregida no se aprueba sola — se vuelve a mirar. Por eso `pasada`, y
por eso `publicar.py` mira que no queden notas pendientes.

## Y la nota que NO es un tramo también se cierra por aquí

`--aplicar` sólo sabe cerrar las de `cortar`, porque son las únicas que ejecuta.
Las de `grafico`, `sonido` y `subtitulo` se arreglan en el paso que les toca —el
spec, la mezcla, el subtítulo— y hasta ahora **no había forma de decirlo por la
línea**: la tabla nombraba cuatro estados y el código sabía escribir dos. Lo que
se hacía en su lugar era un `update` a mano contra la base, que es exactamente
la manera de perder el estado que este proyecto persigue — y se nota en la
tabla: siete notas de `grafico` cerradas y ni una línea de código que las
cerrara.

`--cerrar` lo pone en la línea, y pide **con qué** se cierra: `aplicada` es
«hecha en esta pieza», `automatizada` es «la regla vive en código». La segunda
exige decir la regla, porque una nota automatizada sin regla escrita es una
corrección contada y no hecha.

## Este fichero es el paso, no el criterio

Llegó a 306 líneas de código con el techo en 300 (`scripts/tamano.py`), y lo que
sobraba no era prosa: eran tres trabajos distintos compartiendo sitio. Se parte
como manda el propio techo —*«lo que mide, lo que decide y lo que escribe son
tres cosas»*—, no por líneas:

    dominio/ancla.py    dónde cae un texto en el montaje de hoy; sólo mide
    dominio/recorte.py  lo único que escribe: el EDL recortado y su rastro
    dominio/nota.py     si una nota todavía se puede aplicar, y qué hacer si no

Aquí se queda lo del medio, que es el paso: qué notas entran, cuáles se pisan,
cuáles suben a ticket, cuáles se cierran y cómo se informa.

    python scripts/revision.py --ver                 # el estado de todas
    python scripts/revision.py --ver 1               # sólo el reel 1
    python scripts/revision.py --aplicar 1           # los cortes al EDL
    python scripts/revision.py --anotar 1 cortar 20 47 "sólo es lectura"
    python scripts/revision.py --cerrar 667 --como automatizada --regla "..."
"""
import basedatos
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402
from dominio import recorte  # noqa: E402
from dominio.nota import Nota, sanear  # noqa: E402

BASE = "ads/decisiones.db"


def _con():
    import sqlite3
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def anotar(slug, accion, desde, hasta, que, regla=None, estado="pendiente",
           pasada=1, ancla=None, cual=1, reabre=False):
    """Guarda una nota de revisión. `que` va literal, siempre.

    `ancla` es **el texto** que hay que cortar. Los segundos sirven para
    encontrarlo la primera vez; el texto es lo que sobrevive a que la pieza se
    vuelva a montar, y en un camino que regenera el EDL en cada corrida eso es
    la diferencia entre una corrección que persiste y una que se pierde (C-79).
    """
    # **`desde` y `hasta` son segundos.** Llamando en posicional es facil colar
    # el ancla en el tercer hueco —me paso con dos notas de reel-02— y la fila
    # queda con `desde_s='no voy a reemplazar'` y el ancla vacia: existe, se lee,
    # y no apunta a ningun sitio. Se avisa y se recoloca; la regla vive en
    # `Nota.sanear` (`dominio/nota.py`), que es por donde tambien pasa el que lee.
    if isinstance(desde, str) or isinstance(hasta, str):
        print(f"revision.anotar: «{desde or hasta}» llego donde van segundos;"
              f" se toma como ancla.")
    desde, hasta, ancla = sanear(desde, hasta, ancla)
    con = _con()
    # **La nota pertenece al montaje en que se apunto**, y se estampa con su
    # huella. Regla de Jaime: *«las anclas tienen la funcion de establecer los
    # lugares; si el video se edita o se corta, el ancla cambia, pero es
    # idempotente: no borra registro, crea otro»*.
    #
    # Antes intente lo contrario —caducar la nota vieja— y es peor por dos
    # razones: se pierde el recorrido del video, y una nota sin montaje sigue
    # pudiendo encajar a medias y cortar donde no es. Con la huella, cada nota
    # sabe de que corte habla y las viejas se quedan como lo que son: historia.
    try:
        import modelo as _mo

        _huella = _mo.huella_edl(slug)
    except Exception:                              # noqa: BLE001
        _huella = None
    # **Lo que sube a Jaime se cuenta, no se apila.**
    #
    # Cada vuelta que veía lo mismo escribía una fila nueva, así que la misma
    # observación acababa repetida con la cifra remedida: el cierre del reel-01
    # que no levanta estaba ocho veces, con 0,86 / 0,98 / 1,02 / 1,08 de
    # intensidad. Medido el 1 de septiembre: **134 notas para 7 piezas**, y
    # Jaime, mirándolas: *«no veo qué tengo que decidir»*. Tenía razón — no se
    # veía porque estaban ocho veces.
    #
    # Es exactamente lo que `instruccion.guardar` ya resuelve subiendo `veces`.
    # Aquí la clave no puede ser el texto entero: la cifra cambia cada vez que se
    # remide. Son las **palabras de contenido** las que dicen si es la misma
    # observación, y `veces` pasa a ser lo que era en la otra tabla: la medida de
    # cuántas vueltas lleva esperando una decisión.
    #
    # **Y lo mismo vale para los cortes, que son los que ejecutan.** Esto vivía
    # dentro de un `if estado == "sube"`, así que `cortar` se apilaba sin freno:
    # 482 notas para 7 piezas —110 en reel-02, 93 en reel-05— y `--ver 2`
    # imprimía 110 líneas para 4 pendientes. La que falta de verdad queda
    # enterrada, que es la misma queja de entonces: *«no veo qué tengo que
    # decidir»*.
    #
    # La clave de un corte no es el porqué —lo reescribe el modelo en cada
    # vuelta— sino **el ancla y qué aparición**: eso es lo que identifica el
    # corte. Y si la nota que ya estaba se había dado por huérfana, el hecho de
    # que el paso la vuelva a medir contra el montaje de hoy dice que el sitio
    # volvió a existir: se resucita y se cierra su ticket.
    ya = None
    try:
        from dominio.texto import contenido

        if accion == "cortar" and (ancla or "").strip():
            fila = con.execute(
                "select id, estado from revision where video_slug = ?"
                " and accion = 'cortar' and ancla = ? and cual = ?",
                (slug, ancla, int(cual or 1))).fetchone()
            ya = fila["id"] if fila else None
            if fila and fila["estado"] == "huerfana":
                Nota(con.execute("select * from revision where id = ?",
                                 (ya,)).fetchone()).resucitar(con)
            # **Y si Jaime se vuelve a quejar del mismo sitio, se REABRE.**
            #
            # El deduplicado sobre el ancla es lo que impide que 482 notas
            # entierren las cuatro que importan. Pero tenia un agujero por el que
            # se cuela justo lo mas caro: una nota ya cerrada como «aplicada»
            # absorbia la queja nueva sin cambiar de estado. Paso con el
            # «semanales huerfano» de reel-01, ancla `semanales`, la tercera vez
            # que lo pedia: la nota #749 estaba en «aplicada» —honestamente, por
            # su propia medida lo estaba— y la cuarta queja se sumo a ella y
            # desaparecio de los pendientes.
            #
            # Que el vuelva a verlo ES la prueba de que no estaba hecho. Se
            # reabre y se deja escrito cuantas vueltas lleva; `reabre` es
            # explicito para que una pasada automatica no resucite lo cerrado.
            if fila and reabre and fila["estado"] in ("aplicada", "automatizada"):
                con.execute("update revision set estado = 'pendiente' where id = ?",
                            (ya,))
        elif estado == "sube":
            clave = " ".join(contenido(que or "")[:14])
            for i, otro in con.execute(
                    "select id, que from revision where video_slug = ?"
                    " and estado = 'sube'", (slug,)).fetchall():
                if " ".join(contenido(otro or "")[:14]) == clave:
                    ya = i
                    break
    except Exception:                              # noqa: BLE001
        ya = None
    if ya is not None:
        con.execute("update revision set veces = coalesce(veces, 1) + 1,"
                    " que = ?, fecha = ? where id = ?",
                    (que, datetime.datetime.now().isoformat(timespec="seconds"),
                     ya))
        con.commit()
        con.close()
        return
    con.execute(
        "insert into revision (video_slug, huella, pasada, desde_s, hasta_s, ancla,"
        " cual, accion, que, regla, estado, fecha)"
        " values (?,?,?,?,?,?,?,?,?,?,?,?)",
        (slug, _huella, pasada, desde, hasta, ancla, int(cual or 1), accion, que,
         regla, estado, datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()


#: Lo que `--cerrar` sabe escribir. `pendiente` y `huerfana` no entran: las pone
#: el que ejecuta —`aplicar` y `Nota`— midiendo contra el montaje, y dejar que
#: se pongan a mano convierte una medida en una opinión.
CIERRES = ("aplicada", "automatizada", "sube")


def cerrar(ids, estado="aplicada", regla=None):
    """Cierra notas que **no son un tramo**, diciendo con qué se cerraron.

    `aplicar` cierra las de `cortar` porque las ejecuta: la nota se convierte en
    un recorte y el estado es el recibo. Las demás —`grafico`, `sonido`,
    `subtitulo`, `otro`— las arregla otro paso, y ese paso necesita poder
    decirlo sin abrir la base a mano.

    **`automatizada` exige `regla`.** Es la diferencia entre las dos maneras de
    cerrar: `aplicada` dice «lo hice en esta pieza» y vuelve a hacer falta en la
    siguiente; `automatizada` dice «ya no puede volver a pasar», y eso sólo es
    verdad si está escrito dónde vive ahora. Sin esa frase la tabla cuenta un
    porcentaje de automatización que no significa nada.

    Devuelve los ids que cambiaron.
    """
    if estado not in CIERRES:
        raise SystemExit(f"--como {estado}: sólo {', '.join(CIERRES)}")
    if estado == "automatizada" and not (regla or "").strip():
        raise SystemExit("automatizada sin --regla: una nota que dice que la"
                         " regla vive en código tiene que decir dónde")
    con = _con()
    hechos = []
    for i in ids:
        fila = con.execute("select id, estado, accion, video_slug, quien"
                           " from revision where id = ?", (int(i),)).fetchone()
        if not fila:
            print(f"  nota {i}: no está en la tabla")
            continue
        # **Un tiquet que nunca estuvo «en curso» se cierra sin haberlo mirado.**
        #
        # Jaime, 6-9-2026: *«cada tiquet debe tener 3 estados —activo, en proceso
        # y resuelto— y un agente resuelve un tiquet a la vez»*. El estado de en
        # medio existía en las consultas y **no lo había usado nadie**: cero
        # tiquets habían pasado por él, así que saltaban de activo a resuelto sin
        # que constara quién los trabajó.
        #
        # Y eso ya se cobró una: el paso de diseño cerraba todos los de su fase,
        # así que una respuesta sobre dos paneles de reel-07 cerró el tiquet del
        # gancho sin haberlo abierto.
        if fila["estado"] != "en curso":
            print(f"  ojo: la nota {i} se cierra sin haber pasado por «en curso»"
                  f" — nadie la tomó. Se anota, no se bloquea.")
        con.execute("update revision set estado = ?,"
                    " regla = coalesce(?, regla), fecha = ? where id = ?",
                    (estado, regla, datetime.datetime.now().isoformat(
                        timespec="seconds"), int(i)))
        print(f"  nota {i} ({fila['video_slug']} · {fila['accion']}):"
              f" {fila['estado']} → {estado}")
        hechos.append(int(i))
        if fila["accion"] == "cortar":
            recorte.dar_por_hecha(fila["video_slug"], int(i))
    con.commit()
    con.close()
    if hechos:
        registro.nota("revision", f"nota(s) cerradas como {estado}",
                      detalle=", ".join(str(i) for i in hechos))
    return hechos


def reabrir(ids, por_que):
    """Devuelve a `pendiente` una nota que se cerró **sin haberla atendido**.

    Hacía falta y no existía. Un paso puede cerrar de más —`abierto.cerrar`
    cerraba todos los tiquets de su fase, y una respuesta que arreglaba dos
    paneles de reel-07 se llevó por delante el tiquet del gancho— y la única
    forma de deshacerlo era un `update` a mano contra la base, que es
    exactamente la manera de perder el estado que este proyecto persigue.

    Es el reverso de `cerrar` y pide lo mismo: **por qué**. Una nota que vuelve
    a pendiente sin decirlo es indistinguible de una que nunca se cerró, y
    entonces no se puede saber si el paso que la cerró de más está arreglado.

    No resucita lo `automatizada`: eso dice que la regla vive en código, y si
    volvió a pasar lo que falla es la guarda, no la nota.
    """
    con = _con()
    hechos = []
    for i in ids:
        fila = con.execute("select id, estado, accion, video_slug from revision"
                           " where id = ?", (int(i),)).fetchone()
        if not fila:
            print(f"  nota {i}: no está en la tabla")
            continue
        if fila["estado"] == "automatizada":
            print(f"  nota {i}: está automatizada — si volvió a pasar, lo que"
                  f" falla es su guarda, no la nota")
            continue
        if fila["estado"] == "pendiente":
            print(f"  nota {i}: ya estaba pendiente")
            continue
        con.execute("update revision set estado = 'pendiente', regla = ?,"
                    " fecha = ? where id = ?",
                    (f"reabierta: {por_que}"[:400],
                     datetime.datetime.now().isoformat(timespec="seconds"),
                     int(i)))
        print(f"  nota {i} ({fila['video_slug']} · {fila['accion']}):"
              f" {fila['estado']} → pendiente")
        hechos.append(int(i))
    con.commit()
    con.close()
    if hechos:
        registro.nota("revision", "nota(s) reabiertas",
                      detalle=f"{', '.join(str(i) for i in hechos)} — {por_que}")
    return hechos


def aplicar(slug, ver=False):
    """Convierte las notas `cortar` en recortes del EDL.

    **Sólo `cortar` se aplica sola.** Las de sonido, gráfico o subtítulo no son
    un tramo que quitar: son un mecanismo que cambiar, y ésas se automatizan en
    el paso que corresponda y se marcan aquí. Aplicar automáticamente algo que
    no es un tramo sería fingir que se hizo.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return 0
    edl = json.load(open(ruta, encoding="utf-8"))
    # Que etapas habia ANTES de cortar, para saber cual desaparecio.
    _beats_antes = {d.get("beat") for d in edl.get("detalle", [])}
    # **Los cortes se re-aplican, no se dan por hechos.** `seleccionar.py`
    # regenera el EDL desde cero en cada corrida, asi que un corte «ya aplicado»
    # desaparece en la siguiente y la correccion se pierde sin que nadie se
    # entere. Por eso se aplican todos los que no esten ya dentro de ESTE
    # fichero — el EDL lleva la lista de ids que carga.
    #
    # Es la misma leccion de C-32: editar un artefacto no sirve si el paso que
    # lo produce no sabe de la edicion. La nota es la fuente; el EDL, la copia.
    ya = set(edl.get("revision", {}).get("notas_aplicadas") or [])
    con = _con()
    # **`huerfana` entra también, y por eso se recupera sola.** Una nota que se
    # quedó sin sitio se vuelve a mirar en cada corrida: si el montaje cambia y
    # el texto vuelve a sobrar, `Nota.clase` la devuelve como aplicable y se
    # corta. Dejarla fuera del `select` la convertiría en lo que ya era: una
    # corrección viva a la que ningún paso vuelve nunca.
    # **Y NO se re-aplica lo ya aplicado. Lo intente y rompi los siete EDL.**
    #
    # El registro por id parecia el fallo: una nota `aplicada` queda saltada
    # para siempre, asi que si el montaje se rehace y el texto vuelve, el corte
    # no se repite. Le puse una comprobacion —si el ancla todavia resuelve, el
    # texto esta ahi, se re-aplica— y **multiplique la redundancia en vez de
    # quitarla**: reel-06 paso a 125 frases repetidas, reel-04 acabo diciendo
    # «la verdad es la verdad» tres veces, reel-07 crecio 23 s.
    #
    # La causa es la que este fichero ya explica dos parrafos arriba: los cortes
    # se aplican de atras hacia delante porque **cada uno mueve los tiempos de
    # todo lo que viene despues**. Un ancla que resuelve NO prueba que la nota
    # este sin aplicar: puede estar casando con otra aparicion, o con el texto
    # que quedo al lado del corte ya hecho. Re-aplicarla quita el tramo
    # equivocado y deja material duplicado.
    #
    # Asi que el registro se respeta. Si un corte hay que revisarlo, se revisa
    # por su ancla y se anota de nuevo —eso es lo que hace `huerfana`—, no
    # re-ejecutando a ciegas lo que ya se ejecuto.
    notas = [n for n in con.execute(
        "select * from revision where video_slug = ? and accion = 'cortar'"
        " and estado in ('pendiente','aplicada','huerfana') order by desde_s",
        (slug,)).fetchall() if n["id"] not in ya]
    if not notas:
        con.close()
        return 0

    # Se recortan de atrás hacia delante: cada corte mueve los tiempos de todo
    # lo que viene después, y hacerlo en orden natural invalida el segundo corte
    # con el primero.
    # **El ancla manda sobre los segundos.** Si la nota trae texto, se busca
    # dónde está AHORA; los segundos sólo valen para la corrida en que se
    # apuntó, porque la pieza se vuelve a montar en cada pasada (C-79).
    # **La huella no es un filtro de entrada: es el disparador del re-anclaje.**
    #
    # Esto era `if huella_hoy and n["huella"] != huella_hoy: continue`, y esa
    # guarda se autodestruye: aplicar un corte cambia el EDL, o sea que cambia
    # la huella, o sea que **toda nota escrita contra el corte anterior queda
    # huerfana para siempre**. Medido el 1 de septiembre: de 482 notas `cortar`,
    # 0 llevaban la huella de hoy en las 7 piezas, y `--seco` recortaba 0 s en
    # las siete — hoy y cualquier otro dia. La promesa de C-79 —«el ancla es
    # texto, sobrevive a que la pieza se vuelva a montar»— estaba anulada por el
    # que ejecuta: el mecanismo que decide funcionaba y no le dejaba hablar.
    #
    # Lo que aquella guarda protegia se conserva entero, y es lo unico que hay
    # que conservar: **no cortar por segundos viejos** (C-92). Ahora eso lo
    # decide `Nota.clase`, que vuelve a buscar el TEXTO en el montaje de hoy en
    # vez de creerse un numero — y cuando no queda sitio donde anclar, la nota
    # no se calla: sale por ticket.
    puestos = []
    for fila in notas:
        n = Nota(fila)
        cual = n.clase(edl)
        # No se aplica **y no se da por hecha**: la cinta no se pudo leer, asi
        # que de esta nota no sabemos nada. Callar aqui es perder el corte.
        if cual == Nota.ILEGIBLE:
            print(f"  {slug}: nota {n.id} sin mirar — la cinta no se pudo"
                  f" leer entera. Ni se aplica ni se da por hecha.")
            continue
        if cual == Nota.APLICABLE:
            r = n.rango(edl)
            d, h = r if r else (n.desde_s, n.hasta_s)
            if d is not None:
                puestos.append((d, h, n.id, n.que))
            continue
        # Lo que sigue escribe, asi que no pasa en seco. Y solo se le hace a una
        # nota `pendiente`: una ya aplicada que hoy no re-ancla es historia del
        # video, no una tarea que reabrir.
        if ver or n.estado != "pendiente":
            continue
        if cual == Nota.CUMPLIDA:
            # **Un ancla que ya no esta Y cuyo contenido tampoco suena es un
            # corte hecho.** La segunda mitad de esa frase es la que faltaba:
            # sin ella, un ancla que deja de resolver porque el montaje cambio
            # de toma se sellaba como «aplicada» y la redundancia seguia en la
            # pieza (nota 105 del reel-02, con la comparacion viva y el verbo
            # cambiado). Las dos perdidas son la misma.
            con.execute(
                "update revision set estado='aplicada',"
                " que = que || ' [el texto ya no esta en la pieza]'"
                " where id = ?", (n.id,))
        else:
            n.desahuciar(con)
        con.commit()
    # **Y el mismo tramo no se corta dos veces en la misma corrida.**
    #
    # Dos notas pueden apuntar al mismo sitio sin ser un error de nadie: una
    # sustituye a la otra con mejor ancla, o el mismo defecto se apuntó dos
    # veces. Lo que no puede pasar es que las dos ejecuten, porque los cortes se
    # aplican de atrás hacia delante sobre un EDL que va cambiando: cuando el
    # segundo llega, sus segundos ya no señalan lo que la nota nombraba, sino lo
    # que acaba de ocupar el hueco del primero. Recorta contenido bueno y no
    # falla — alarga o acorta, que es como se corrompieron los siete EDL.
    #
    # Se queda el corte más ancho: contiene lo que el otro pedía. Medido hoy en
    # reel-02, donde había dos parejas así: 79,1-80,3 s por duplicado y
    # 44,0-44,4 dentro de 44,0-63,8.
    puestos.sort(key=lambda x: (x[0], -(((x[1] if x[1] is not None else x[0])) - x[0])))
    cortes, tapados = [], []
    for d, h, nid, que in puestos:
        fin = h if h is not None else d
        cubierto = next((c for c in cortes
                         if c[0] <= d + 1e-6
                         and (c[1] if c[1] is not None else c[0]) >= fin - 1e-6),
                        None)
        if cubierto is not None:
            tapados.append((nid, d, fin, cubierto[2]))
            continue
        cortes.append((d, h, nid, que))
    for nid, d, fin, otro in tapados:
        print(f"  {slug}: nota {nid} ({d:.1f}-{fin:.1f}s) cae dentro del corte"
              f" de la nota {otro}: no se ejecuta dos veces. Se da por hecha.")
        if not ver:
            con.execute("update revision set estado='aplicada' where id=?",
                        (nid,))
            # Al registro que lee el que ejecuta, no sólo al estado: lo escribe
            # la misma línea que guarda los cortes de esta corrida, más abajo.
            ya.add(nid)
    if tapados and not ver:
        con.commit()
    hechos = recorte.recortar(edl, cortes)

    if ver:
        con.close()
        for _, d, h, que in hechos:
            print(f"  {slug}: cortaria {d:.1f}-{h:.1f}s — {que[:60]}")
        return len(hechos)

    recorte.guardar(ruta, edl, hechos, ya)
    # Si algun corte se llevo una etapa entera, su declaracion se retira: si no,
    # `fijar` la vuelve a meter en la corrida siguiente y el corte se deshace.
    recorte.retirar_fijados(slug, edl, _beats_antes)
    for nid, d, h, que in hechos:
        con.execute("update revision set estado='aplicada' where id=?", (nid,))
    con.commit()
    con.close()
    registro.nota("revision", "cortes de revision final aplicados",
                  detalle=f"{slug}: {len(hechos)} corte(s)")
    return len(hechos)


def ver(reels=None):
    con = _con()
    filas = con.execute("select * from revision order by video_slug, pasada,"
                        " desde_s").fetchall()
    con.close()
    if reels:
        slugs = {f"reel-{int(n):02d}" for n in reels}
        filas = [f for f in filas if f["video_slug"] in slugs]
    if not filas:
        print("revision: sin notas")
        return
    por_estado = {}
    slug = None
    for f in filas:
        por_estado[f["estado"]] = por_estado.get(f["estado"], 0) + 1
        if f["video_slug"] != slug:
            slug = f["video_slug"]
            print(f"\n{slug}")
        # Por `sanear` y no por la fila cruda: un ancla en la columna de los
        # segundos hacía saltar el informe entero con un ValueError de formato,
        # o sea que la pieza con una nota mal escrita **no se podía ni mirar**.
        d_s, h_s, _ = sanear(f["desde_s"], f["hasta_s"], f["ancla"])
        tramo = ("pieza entera" if d_s is None
                 else f"{d_s:.0f}-{h_s:.0f}s"
                 if h_s is not None else f"{d_s:.0f}s")
        print(f"  p{f['pasada']} [{f['estado']:<12}] {f['accion']:<9}"
              f" {tramo:<14} {f['que'][:64]}")
        if f["regla"]:
            print(f"       regla: {f['regla'][:88]}")
    print("\n" + " · ".join(f"{k}: {v}" for k, v in sorted(por_estado.items())))
    # Lo que de verdad importa del bucle: cuanto se ha automatizado.
    auto = por_estado.get("automatizada", 0)
    print(f"automatizadas {auto} de {len(filas)}"
          f" ({100 * auto / max(len(filas), 1):.0f}%) — el resto todavia"
          f" necesita mano")


def _segundo(v):
    """Un extremo tal como llega por la línea: `-`, un número, o **el ancla**.

    Esto hacía `float(v)` a secas, y con eso **el ancla no se podía escribir por
    la línea**: el paso reventaba con un `ValueError` antes de llegar a `anotar`,
    que sí sabe qué hacer con un texto en la columna de los segundos —lo dice su
    docstring, lo recoloca `Nota.sanear` y lo avisa al escribir—. O sea que la
    única forma de anotar un corte con ancla era llamar a `anotar` desde Python,
    que es hacer a mano el trabajo de la máquina.

    Y el ancla no es un adorno: es lo único de una nota que sobrevive a que la
    pieza se vuelva a montar (C-79). Sin él la nota queda atada a unos segundos
    que en la corrida siguiente señalan otra frase, que es C-92.
    """
    if v == "-":
        return None
    try:
        return float(v)
    except ValueError:
        return v                       # texto: `sanear` lo pone en el ancla


def tomar(ids, quien):
    """Pasa esas notas a «en curso» y deja escrito quién las tiene.

    Es el estado que faltaba. Jaime: *«un agente resuelve un tiquet a la vez»*,
    y para que eso se pueda comprobar el tiquet tiene que decir quién lo tomó y
    cuándo. Tomar una que ya tiene dueño avisa: dos a la vez sobre el mismo
    sitio es como se pisan.
    """
    con = _con()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    for i in ids:
        f = con.execute("select estado, quien, video_slug, accion from revision"
                        " where id = ?", (int(i),)).fetchone()
        if not f:
            print(f"  nota {i}: no está en la tabla")
            continue
        if f["estado"] == "en curso" and (f["quien"] or "") != quien:
            print(f"  ojo: la nota {i} ya la tiene «{f['quien']}»")
        con.execute("update revision set estado = 'en curso', quien = ?,"
                    " tomado = ? where id = ?", (quien, ahora, int(i)))
        print(f"  nota {i} ({f['video_slug']} · {f['accion']}):"
              f" {f['estado']} → en curso · {quien}")
    con.commit()
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--seco", action="store_true", help="dice que cortaria")
    ap.add_argument("--anotar", nargs="+", metavar="ARG",
                    help="slug accion desde hasta «texto»; en desde/hasta vale"
                         " `-`, un segundo o el ANCLA, que es lo que sobrevive"
                         " a re-montar")
    ap.add_argument("--tomar", nargs="+", type=int, metavar="ID",
                    help="pasa esas notas a «en curso»; exige --quien")
    ap.add_argument("--quien", help="quién toma la nota")
    ap.add_argument("--cerrar", nargs="+", type=int, metavar="ID",
                    help="cierra esas notas (las que no son un tramo)")
    ap.add_argument("--como", default="aplicada", choices=CIERRES,
                    help="con qué se cierran; automatizada exige --regla")
    ap.add_argument("--regla", default=None,
                    help="la versión general: dónde vive ahora, en código")
    ap.add_argument("--reabrir", nargs="+", type=int, metavar="ID",
                    help="devuelve a pendiente una nota que un paso cerró sin"
                         " atenderla; exige --por-que")
    ap.add_argument("--por-que", dest="por_que", default=None,
                    help="por qué vuelve a estar pendiente")
    ap.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()

    if a.reabrir:
        if not (a.por_que or "").strip():
            raise SystemExit("--reabrir sin --por-que: una nota que vuelve a"
                             " pendiente sin decir por qué es indistinguible de"
                             " una que nunca se cerró")
        reabrir(a.reabrir, a.por_que)
        return
    if a.tomar:
        if not (a.quien or "").strip():
            raise SystemExit("--tomar exige --quien: un tiquet en curso sin"
                             " dueño no es un estado, es una etiqueta")
        tomar(a.tomar, a.quien.strip())
        return 0
    if a.cerrar:
        cerrar(a.cerrar, a.como, a.regla)
        return
    if a.anotar:
        n, accion, desde, hasta, *resto = a.anotar
        anotar(f"reel-{int(n):02d}", accion, _segundo(desde), _segundo(hasta),
               " ".join(resto))
        print("anotada")
        return
    if a.aplicar or a.seco:
        for n in (a.reels or rutas.piezas()):
            aplicar(f"reel-{n:02d}", ver=a.seco)
        return
    ver(a.reels)


if __name__ == "__main__":
    main()
