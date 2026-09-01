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

    python scripts/revision.py --ver                 # el estado de todas
    python scripts/revision.py --ver 1               # sólo el reel 1
    python scripts/revision.py --aplicar 1           # los cortes al EDL
    python scripts/revision.py --anotar 1 cortar 20 47 "sólo es lectura"
"""
import basedatos
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402

BASE = "ads/decisiones.db"
# **1, no 1,15: no hay que acelerar nada.** Jaime, al ver las duraciones reales:
# *«ninguno hay que acelerar la verdad, todos estan por debajo de los 120 y en
# el rango de los 90s»*. A velocidad natural el lote va de 47,6 a 118,5 s, con
# cuatro de seis entre 72 y 89 — que es formato corto sin forzar nada.
#
# Y quita de la cadena la resintesis mas grande. `rubberband` no es un filtro:
# reconstruye la senal. Con la voz limpiada fuera eran **dos resintesis
# encadenadas**, y ahi es donde empezo a sonar a papilla.
VELOCIDAD = 1.0


def _con():
    import sqlite3
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def anotar(slug, accion, desde, hasta, que, regla=None, estado="pendiente",
           pasada=1, ancla=None, cual=1):
    """Guarda una nota de revisión. `que` va literal, siempre.

    `ancla` es **el texto** que hay que cortar. Los segundos sirven para
    encontrarlo la primera vez; el texto es lo que sobrevive a que la pieza se
    vuelva a montar, y en un camino que regenera el EDL en cada corrida eso es
    la diferencia entre una corrección que persiste y una que se pierde (C-79).
    """
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
    con.execute(
        "insert into revision (video_slug, huella, pasada, desde_s, hasta_s, ancla,"
        " cual, accion, que, regla, estado, fecha)"
        " values (?,?,?,?,?,?,?,?,?,?,?,?)",
        (slug, _huella, pasada, desde, hasta, ancla, int(cual or 1), accion, que,
         regla, estado, datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()


def _montado_a_cinta(edl, t_montado):
    """De segundo de la pieza montada a segundo de la cinta.

    Jaime mira **la pieza**, así que sus tiempos son de la pieza. El EDL vive en
    tiempo de cinta y además el montaje corre a 1,15×. Sin esta traducción, un
    «desde el segundo 20» recortaría el sitio equivocado — que es exactamente el
    tipo de fallo que no se ve hasta que ya está renderizado.

    Devuelve `(i, t_cinta)`: en qué segmento cae y en qué segundo de la cinta.
    """
    t = 0.0
    for i, (a, b) in enumerate(edl["segmentos"]):
        dur = (b - a) / VELOCIDAD
        if t_montado <= t + dur + 1e-6:
            return i, a + (t_montado - t) * VELOCIDAD
        t += dur
    return len(edl["segmentos"]) - 1, edl["segmentos"][-1][1]


def _por_ancla(edl, ancla, slug="", cual=1):
    """Dónde está ese texto en la pieza, en segundos de montaje.

    Es lo que hace que una corrección sobreviva a que la pieza se vuelva a
    montar. Se busca sobre las palabras de la cinta recorridas en orden de
    montaje, que es exactamente lo que el espectador oye.

    `cual` dice **qué aparición**, y sin eso el paso de redundancia no podia
    hacer su trabajo. La cinta es un abanico: la misma frase esta grabada varias
    veces para poder escoger. Cuando dos tomas dicen exactamente lo mismo, el
    ancla —que es texto— casa con las dos, y devolvia siempre la primera. O sea
    que el paso podia medir cual se entrega mejor y **no tenia como pedir que se
    fuera la otra**.

    Medido en reel-01 e2: «terminan ganando mucho mas» dicho dos veces, la
    primera con intensidad 2,26 y la segunda con 0,22 —plana, por debajo del
    suelo de 0,25—. Sin `cual`, cortar la plana era imposible: el ancla se
    llevaba la buena.
    """
    import unicodedata
    sys.path.insert(0, os.path.dirname(__file__))
    import transcribir as _tr, rutas as _ru

    from dominio import texto as _tx

    limpio = _tx.comparable          # la vara con la que se busca un ancla

    # Un ancla puede ser una frase, o «desde ... hasta» separadas por «|»: para
    # un corte largo, la primera dice donde empieza y la segunda donde acaba.
    partes = [limpio(x).split() for x in ancla.split("|")]
    obj = partes[0]
    fin_obj = partes[1] if len(partes) > 1 else None
    if not obj:
        return None
    cache, linea, t, ilegible = {}, [], 0.0, set()
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        toma = det.get("toma") or _ru.TOMAS.get(slug or slug_de(edl))
        if toma not in cache:
            try:
                cache[toma] = _tr.exigir(toma)["segmentos"]
            except (SystemExit, _tr.Incompleta):
                # **Una cinta que no se puede leer no es una cinta sin texto.**
                # Con `[]` a secas el ancla no resolvia, y mas abajo eso se lee
                # como «el texto ya no esta en la pieza»: la nota se marcaba
                # `aplicada` y **el corte se perdia para siempre**, sin que
                # nadie lo contara. Se distingue una cosa de la otra.
                cache[toma] = []
                ilegible.add(toma)
        for w in cache[toma]:
            # La vara de que palabra suena dentro del corte vive en
            # `transcribir.suena` (C-84). Este era el CUARTO sitio con su propia
            # copia, y aqui el precio es alto: si la linea del montaje no es la
            # que se oye, los segundos que se calculan no son los de la pieza y
            # **el corte cae donde no es**. Reel-01 perdio media etapa 2 y el
            # cierre entero por esto.
            if _tr.suena(w, rango[0], rango[1]):
                dentro = (w["start"] - rango[0]) / VELOCIDAD
                linea.append((limpio(w["text"]).strip(), t + dentro,
                              t + (w["end"] - rango[0]) / VELOCIDAD))
        t += (rango[1] - rango[0]) / VELOCIDAD
    pal = [x[0] for x in linea]
    visto = 0
    for i in range(len(pal) - len(obj) + 1):
        if pal[i:i + len(obj)] != obj:
            continue
        visto += 1
        if visto < max(1, int(cual or 1)):
            continue
        desde = round(linea[i][1], 2)
        if not fin_obj:
            return desde, round(linea[i + len(obj) - 1][2], 2)
        for j in range(i + len(obj), len(pal) - len(fin_obj) + 1):
            if pal[j:j + len(fin_obj)] == fin_obj:
                return desde, round(linea[j + len(fin_obj) - 1][2], 2)
        return False if ilegible else None
    # **`False` es «no pude mirar»; `None` es «mire y no esta».** Son cosas
    # opuestas y las dos llegaban como `None`: quien llama lo leia como «el
    # texto ya no esta en la pieza», marcaba la nota `aplicada` y el corte
    # desaparecia sin que nadie lo contara.
    return False if ilegible else None


def _retirar_fijados(slug, edl, antes):
    """Una etapa que se corta entera **deja de estar declarada**.

    Sin esto los dos mecanismos se pelean y gana el que corre despues. La nota
    dice «esta seccion sobra» y `corte_fijo` sigue diciendo «esta etapa es este
    tramo», asi que `fijar.aplicar` la vuelve a meter en la corrida siguiente —
    y lo hace en silencio, porque desde su punto de vista esta cumpliendo.

    Paso con el reel-01: Jaime pidio sacar el mecanismo entero, la nota lo
    corto, y la pieza volvio a salir con el dentro y ocho segundos mas larga.

    Retirar la declaracion no es perder el registro: la nota de corte queda, con
    su porque y su ancla, y es la que explica por que esa etapa ya no esta.
    """


    vivos = {d.get("beat") for d in edl.get("detalle", [])}
    fuera = [b for b in antes if b is not None and b not in vivos]
    if not fuera:
        return 0
    con = basedatos.abrir(BASE)
    con.executemany(
        "delete from corte_fijo where papel='etapa' and orden = ?"
        " and video_id = (select id from video where slug = ?)",
        [(b, slug) for b in fuera])
    con.commit()
    con.close()
    print(f"  {slug}: etapa(s) {sorted(fuera)} fuera de la pieza —"
          f" se retira su declaracion para que no vuelvan")
    return len(fuera)


def slug_de(edl):
    return edl.get("slug") or edl.get("video_slug") or ""


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
    notas = [n for n in con.execute(
        "select * from revision where video_slug = ? and accion = 'cortar'"
        " and estado in ('pendiente','aplicada') order by desde_s",
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
    try:
        import modelo as _mo

        huella_hoy = _mo.huella_edl(slug)
    except Exception:                              # noqa: BLE001
        huella_hoy = None
    puestos = []
    for n in notas:
        # **Solo las notas de este montaje.** Las de un corte anterior se
        # quedan en la tabla —son el recorrido del video— pero no se aplican:
        # hablan de un sitio que ya no existe. La huella lo dice sin ambiguedad.
        #
        # **Y la que no trae huella tampoco vale.** Esto decia `if n["huella"]
        # and ...`, o sea que una nota sin estampa pasaba siempre — y las que no
        # la traen son justo las viejas, de antes de que la columna existiera.
        # El resultado, medido en reel-01: treinta notas de montajes que ya no
        # existen se aplicaron a este, y la pieza paso de 136,4 a 92,6 segundos.
        # Se llevaron la revelacion entera de e2 y el cierre completo.
        #
        # El fallo estaba en la direccion de la duda. Sin huella no sabemos de
        # que corte habla la nota, y ante esa duda cortar es la opcion cara: si
        # se salta de mas, la redundancia se vuelve a anotar en la corrida
        # siguiente —el paso corre en cada vuelta— pero lo que se corta de mas
        # no vuelve solo, y encima la pieza parece entera.
        if huella_hoy and n["huella"] != huella_hoy:
            continue
        # `cual` puede no estar en notas viejas: entonces es la primera.
        try:
            _cual = n["cual"]
        except (IndexError, KeyError):
            _cual = 1
        rango = _por_ancla(edl, n["ancla"], slug, _cual) if n["ancla"] else None
        # No se aplica **y no se da por hecha**: la cinta no se pudo leer, asi
        # que de esta nota no sabemos nada. Callar aqui es perder el corte.
        if rango is False:
            print(f"  {slug}: nota {n['id']} sin mirar — la cinta no se pudo"
                  f" leer entera. Ni se aplica ni se da por hecha.")
            continue
        if rango is None and n["desde_s"] is None:
            # **Un ancla que ya no esta en la pieza es un corte ya hecho.**
            # Antes se saltaba y la nota se quedaba pendiente para siempre: la
            # puerta contaba «5 cortes sin aplicar» que en realidad estaban
            # todos aplicados, y esa cuenta falsa tapa a la nota que si falta.
            # Si el texto que habia que quitar no suena, la nota cumplio.
            if n["ancla"] and not ver:
                con.execute(
                    "update revision set estado='aplicada',"
                    " que = que || ' [el texto ya no esta en la pieza]'"
                    " where id = ?", (n["id"],))
                con.commit()
            continue
        # **Si la nota trae ancla y el ancla no resuelve, no se corta.** Los
        # segundos son de la corrida en que se apunto y la pieza se ha vuelto a
        # montar desde entonces: usarlos corta en otro sitio. Paso justo eso —
        # una nota de e7 se llevo por delante de e2 a e8 y la pieza cayo de
        # 119 s a 75 s. Los segundos solo valen para una nota **sin** ancla,
        # que es la que se apunto mirando el video.
        if n["ancla"] and rango is None:
            continue
        d, h = rango if rango else (n["desde_s"], n["hasta_s"])
        puestos.append((d, h, n["id"], n["que"]))
    cortes = sorted(puestos, key=lambda x: -x[0])
    hechos = []
    for d, h, nid, que in cortes:
        i0, c0 = _montado_a_cinta(edl, d)
        i1, c1 = _montado_a_cinta(edl, h if h is not None else d)
        segs, det = [], []
        for i, (rango, dd) in enumerate(zip(edl["segmentos"], edl["detalle"])):
            a, b = rango
            if i < i0 or i > i1:
                segs.append([a, b])
                det.append(dd)
                continue
            # Lo que queda del segmento a cada lado del recorte.
            iz_a, iz_b = a, (c0 if i == i0 else a)
            de_a, de_b = (c1 if i == i1 else b), b
            if i == i0 and iz_b - iz_a > 0.25:
                segs.append([iz_a, iz_b])
                det.append({**dd, "start": iz_a, "end": iz_b})
            if i == i1 and de_b - de_a > 0.25:
                segs.append([de_a, de_b])
                det.append({**dd, "start": de_a, "end": de_b})
        edl["segmentos"], edl["detalle"] = segs, det
        hechos.append((nid, d, h, que))

    if ver:
        con.close()
        for _, d, h, que in hechos:
            print(f"  {slug}: cortaria {d:.1f}-{h:.1f}s — {que[:60]}")
        return len(hechos)

    # Derivada de `detalle`, nunca re-indexada: ver el mismo comentario en
    # `depurar.py`. Un corte parte segmentos, y el indice deja de valer.
    edl["fuentes"] = [d.get("toma") or "" for d in edl["detalle"]]
    edl["duracion_montada_s"] = round(
        sum((b - a) / VELOCIDAD for a, b in edl["segmentos"]), 2)
    rev = dict(edl.get("revision") or {})
    rev["revision_final"] = " · ".join(
        f"{d:.0f}-{h:.0f}s: {q[:70]}" for _, d, h, q in hechos)
    rev["notas_aplicadas"] = sorted(ya | {nid for nid, _, _, _ in hechos})
    edl["revision"] = rev
    json.dump(edl, open(ruta, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # Si algun corte se llevo una etapa entera, su declaracion se retira: si no,
    # `fijar` la vuelve a meter en la corrida siguiente y el corte se deshace.
    _retirar_fijados(slug, edl, _beats_antes)
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
        tramo = ("pieza entera" if f["desde_s"] is None
                 else f"{f['desde_s']:.0f}-{f['hasta_s']:.0f}s"
                 if f["hasta_s"] is not None else f"{f['desde_s']:.0f}s")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--seco", action="store_true", help="dice que cortaria")
    ap.add_argument("--anotar", nargs="+", metavar="ARG",
                    help="slug accion desde hasta «texto»")
    ap.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()

    if a.anotar:
        n, accion, desde, hasta, *resto = a.anotar
        anotar(f"reel-{int(n):02d}", accion,
               None if desde == "-" else float(desde),
               None if hasta == "-" else float(hasta), " ".join(resto))
        print("anotada")
        return
    if a.aplicar or a.seco:
        for n in (a.reels or rutas.piezas()):
            aplicar(f"reel-{n:02d}", ver=a.seco)
        return
    ver(a.reels)


if __name__ == "__main__":
    main()
