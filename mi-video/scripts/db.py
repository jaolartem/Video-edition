"""La base de decisiones: creación, migración y consultas.

Jaime: *«hazla relacional con varias entidades —vídeo, frame, parte del frame,
mensaje esperado— pero mantén un nivel de normalización de tercer nivel, sin
excusas y desde origen»*.

El esquema está en `scripts/esquema.sql` y explica ahí por qué cada tabla está
donde está. Esto es la capa que la llena y la pregunta.

## Qué resuelve

Las decisiones vivían en cuatro JSON y el mismo dato aparecía en dos sitios. Eso
costó cuatro fallos registrados —C-04, C-05, y los aprendizajes 33 y 43— y
siempre el mismo patrón: dos fuentes que se separan en cuanto una cambia. En 3FN
eso deja de ser posible: cada hecho vive en un sitio.

## Uso

    python scripts/db.py crear         # crea el esquema
    python scripts/db.py migrar        # vuelca los JSON actuales
    python scripts/db.py plan 1        # el plan de una pieza
    python scripts/db.py falta         # qué le falta a cada pieza
"""
import argparse
import json
import os
import re
import sqlite3
import basedatos
import sys

RUTA = os.path.join("ads", "decisiones.db")
ESQUEMA = os.path.join(os.path.dirname(__file__), "esquema.sql")


def abrir():
    os.makedirs("ads", exist_ok=True)
    cx = basedatos.abrir(RUTA)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA foreign_keys = ON")
    return cx


def crear():
    cx = abrir()
    cx.executescript(open(ESQUEMA, encoding="utf-8").read())
    cx.commit()
    return cx


def _id(cx, tabla, nombre, **extra):
    """Busca o inserta por nombre y devuelve el id. Idempotente."""
    r = cx.execute(f"SELECT id FROM {tabla} WHERE nombre = ?", (nombre,)).fetchone()
    if r:
        if extra:
            sets = ", ".join(f"{k} = ?" for k in extra)
            cx.execute(f"UPDATE {tabla} SET {sets} WHERE id = ?",
                       (*extra.values(), r["id"]))
        return r["id"]
    cols = ["nombre", *extra]
    cx.execute(f"INSERT INTO {tabla} ({', '.join(cols)}) "
               f"VALUES ({', '.join('?' * len(cols))})", (nombre, *extra.values()))
    return cx.execute("SELECT last_insert_rowid() AS i").fetchone()["i"]


def migrar():
    """Vuelca los JSON actuales a la base. Se puede correr las veces que haga falta."""
    cx = crear()
    # **Las piezas que derivan de otra se expanden antes de leer nada** (C-388):
    # su línea de `frames.json` se vuelve a generar desde su origen.
    sys.path.insert(0, os.path.dirname(__file__))
    from dominio.libreto import escribir_derivadas
    escribir_derivadas()
    frames = json.load(open("ads/frames.json", encoding="utf-8"))
    rutas = json.load(open("rutas.json", encoding="utf-8"))

    # ── catálogo de estructuras y su secuencia canónica ──────────────────
    for nombre, etapas in frames["estructuras"].items():
        eid = _id(cx, "estructura", nombre)
        for i, et in enumerate(etapas, 1):
            cx.execute("INSERT OR REPLACE INTO etapa_canonica "
                       "(estructura_id, orden, nombre) VALUES (?, ?, ?)",
                       (eid, i, et))

    # ── piezas ───────────────────────────────────────────────────────────
    for slug, f in frames["reels"].items():
        est = cx.execute("SELECT id FROM estructura WHERE nombre = ?",
                         (f["estructura"],)).fetchone()["id"]
        # Una derivada usa la cinta de su origen (C-388).
        toma = _id(cx, "toma", rutas["tomas"].get(slug)
                   or rutas["tomas"][f["deriva_de"]])
        m1 = _id(cx, "mecanismo", f["mecanismo"]["primario"])
        m2 = _id(cx, "mecanismo", f["mecanismo"]["secundario"])
        porque = " ".join(f.get("porque", []))
        cx.execute(
            "INSERT INTO video (slug, estructura_id, toma_id, "
            "mecanismo_primario_id, mecanismo_secundario_id, porque) "
            "VALUES (?,?,?,?,?,?) ON CONFLICT(slug) DO UPDATE SET "
            "estructura_id=excluded.estructura_id, toma_id=excluded.toma_id, "
            "mecanismo_primario_id=excluded.mecanismo_primario_id, "
            "mecanismo_secundario_id=excluded.mecanismo_secundario_id, "
            "porque=excluded.porque",
            (slug, est, toma, m1, m2, porque))
        vid = cx.execute("SELECT id FROM video WHERE slug = ?", (slug,)).fetchone()["id"]

        # Las etapas de la pieza, con su mensaje esperado sacado del libreto.
        sys.path.insert(0, os.path.dirname(__file__))
        import beats  # noqa: E402  (import tardío: necesita cwd en mi-video)
        # **Y su libreto es el de su origen**, en las etapas que hereda (C-388).
        # Nueve sitios leen la tabla `libreto` por el slug: una copia que se
        # regenera en cada migración es lo que les deja ver la pieza, y no puede
        # separarse del origen porque no sobrevive a la migración siguiente.
        if f.get("deriva_de"):
            ov = cx.execute("SELECT id FROM video WHERE slug = ?",
                            (f["deriva_de"],)).fetchone()
            textos = [r["texto"] for r in cx.execute(
                "SELECT texto FROM libreto WHERE video_id = ? ORDER BY orden",
                (ov["id"],))] if ov else []
            cx.execute("DELETE FROM libreto WHERE video_id = ?", (vid,))
            cx.executemany(
                "INSERT INTO libreto (video_id, orden, texto) VALUES (?,?,?)",
                [(vid, j + 1, textos[o - 1])
                 for j, o in enumerate(f.get("de_origen") or [])
                 if o - 1 < len(textos)])
            cx.commit()
        libreto = beats.beats_del_libreto(int(slug[-2:]))
        # `etapa_orden` apunta a la canónica; si la pieza declara una etapa que
        # no está en la secuencia canónica, se añade al final de ésta. Pasa con
        # las variantes («prueba del hueco», «urgencia y registro»).
        for i, b in enumerate(frames["reels"][slug]["beats"], 1):
            r = cx.execute("SELECT orden FROM etapa_canonica WHERE "
                           "estructura_id = ? AND nombre = ?",
                           (est, b["etapa"])).fetchone()
            if r is None:
                nxt = cx.execute("SELECT COALESCE(MAX(orden),0)+1 AS n FROM "
                                 "etapa_canonica WHERE estructura_id = ?",
                                 (est,)).fetchone()["n"]
                cx.execute("INSERT INTO etapa_canonica VALUES (?,?,?)",
                           (est, nxt, b["etapa"]))
                orden_can = nxt
            else:
                orden_can = r["orden"]
            cx.execute(
                "INSERT INTO etapa (video_id, orden, estructura_id, "
                "etapa_orden, mensaje_esperado, obligatorio) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(video_id, orden) DO UPDATE SET "
                "etapa_orden=excluded.etapa_orden, "
                "mensaje_esperado=excluded.mensaje_esperado, "
                "obligatorio=excluded.obligatorio",
                (vid, i, est, orden_can, libreto[i - 1] if i <= len(libreto) else "",
                 1 if b.get("obligatorio") else 0))

        # Apertura y cierre: decisiones de oído sobre la pieza entera.
        #
        # **Sólo se borra lo que esta migración vuelve a escribir.** Borraba
        # `corte_fijo` ENTERA y reinsertaba únicamente apertura y cierre desde
        # `frames.json`, así que se llevaba por delante las declaraciones de
        # etapa —`papel='etapa'`, las que escribe `fijar.declarar`— y lo hacía
        # en **cada invocación del motor**: `avanzar.main()` llama a `migrar()`
        # al arrancar, antes de recorrer nada.
        #
        # Medido: 117 declaraciones vivas en el commit 01c82ea (ids 405-630) y
        # **cero** en el siguiente, con los ids de apertura y cierre saltando de
        # 1-13 a 893-907 — la firma del DELETE+INSERT repetido. Hoy quedan 119
        # marcas `fijado` huérfanas en los siete EDL y ni una fila que las
        # sostenga.
        #
        # Ése es el «se corrige un corte, se vuelve a lanzar la línea y el vídeo
        # sale igual» de dos noches seguidas: la decisión existía y la migración
        # la borraba antes de que nadie la leyera.
        cx.execute("DELETE FROM corte_fijo WHERE video_id = ? AND papel IN"
                   " ('apertura','cierre')", (vid,))
        if f.get("apertura"):
            cx.execute("INSERT INTO corte_fijo (video_id, papel, orden, desde, "
                       "hasta, por_que) VALUES (?,'apertura',0,?,?,?)",
                       (vid, *f["apertura"], f.get("nota_de_orden", "")))
        for j, (a, b) in enumerate(f.get("cierre", [])):
            cx.execute("INSERT INTO corte_fijo (video_id, papel, orden, desde, "
                       "hasta, por_que) VALUES (?,'cierre',?,?,?,?)",
                       (vid, j, a, b, "cierre declarado"))

        # La marca de humanidad, si la pieza la tiene.
        m = f.get("senala")
        if m:
            e = cx.execute("SELECT id FROM etapa WHERE video_id = ? AND orden = ?",
                           (vid, m["beat"])).fetchone()
            if e:
                cx.execute("INSERT OR REPLACE INTO marca_humanidad VALUES "
                           "(?,?,?,?,?,?)",
                           (e["id"], m["dice"], m["es"],
                            1 if m.get("blanco_y_negro") else 0,
                            m.get("maximo_s", 1.6), m.get("por_que", "")))

    # ── placas ───────────────────────────────────────────────────────────
    # **La asignación es de PIEZA.** Jaime, 6-9-2026: *«es un FONDO de tablero
    # por reel»*. Esto leía `sirve` —una lista de `reel-NN:beat` dentro de cada
    # placa— y llenaba `placa_etapa` con una placa distinta por etapa, que es
    # exactamente el reparto que él paró. Ahora la placa de la pieza se aplica a
    # todas sus etapas: la tabla sigue estando por etapa porque el modelo lo
    # está, pero lo que declara es una sola placa repetida, no un mosaico.
    fondos = json.load(open("ads/fondos.json", encoding="utf-8"))
    ids = {}
    for nombre, p in fondos["placas"].items():
        ids[nombre] = _id(cx, "placa", nombre, dice=p["dice"],
                          siente=p.get("siente", ""))
    for slug, asignada in fondos.get("pieza", {}).items():
        pid = ids.get(asignada.get("placa")) if isinstance(asignada, dict) else None
        if pid is None:
            continue
        for e in cx.execute(
                "SELECT e.id FROM etapa e JOIN video v ON v.id = e.video_id "
                "WHERE v.slug = ?", (slug,)).fetchall():
            cx.execute("INSERT OR IGNORE INTO placa_etapa (placa_id, "
                       "etapa_id, elegida) VALUES (?,?,1)", (pid, e["id"]))

    # ── el log de correcciones ───────────────────────────────────────────
    log = "../docs/correcciones.md"
    if os.path.exists(log):
        txt = open(log, encoding="utf-8").read()
        for m in re.finditer(
                r"### (C-\d+) · (.+?)\n(.*?)(?=\n### |\Z)", txt, re.S):
            cod, titulo, cuerpo = m.group(1), m.group(2), m.group(3)
            def campo(k):
                r = re.search(rf"\*\*{k}\.?\*\*\s*(.+?)(?=\n\*\*|\Z)", cuerpo, re.S)
                return " ".join(r.group(1).split())[:600] if r else None
            cx.execute(
                "INSERT INTO correccion (codigo, fecha, sintoma, causa, "
                "mecanismo, deteccion) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(codigo) DO UPDATE SET sintoma=excluded.sintoma, "
                "causa=excluded.causa, mecanismo=excluded.mecanismo, "
                "deteccion=excluded.deteccion",
                (cod, "2026-08-27", campo("Síntoma") or titulo,
                 campo("Causa") or "", campo("Mecanismo"), campo("Detección")))

    cx.commit()
    return cx


def recuperar(slug):
    """Repone las declaraciones de etapa que la migración borró, **con su id**.

    Vive aquí y no en `fijar.py` porque el destrozo fue de la migración: lo que
    escribe apertura y cierre en `corte_fijo` es este fichero, y reponer lo que
    borró de más es suyo. `fijar.huerfanas` dice cuáles faltan; esto las mete.

    **Y se hace por la máquina, no a mano.** La marca `fijado` que `fijar.aplicar`
    dejó en el EDL lleva el id de la declaración, el beat, la cinta y el porqué:
    con eso se reconstruye la fila entera. El id se conserva a propósito —si se
    reinsertara con uno nuevo, las 119 marcas del lote seguirían huérfanas y la
    puerta seguiría parando.

    Lo que NO se recupera es la posición original: 17 de las 24 declaraciones
    comparables contra el commit 01c82ea habían derivado hasta **4,17 s** porque
    los pasos del cosido las movían sin preguntar. Vuelven donde están hoy; que
    no se vuelvan a mover es trabajo de `Tijera`, no de esto.

    **No es automática.** Correrla dentro de `migrar()` resucitaría también las
    declaraciones que `fijar.declarar` sustituyó legítimamente —el EDL conserva
    el recibo viejo hasta que `aplicar` lo reescribe—, así que la pide la puerta
    por su nombre y la lanza quien la lee.
    """
    import datetime

    import fijar

    filas = fijar.huerfanas(slug)
    cx = abrir()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    vid = cx.execute("SELECT id FROM video WHERE slug = ?", (slug,)).fetchone()["id"]
    cx.executemany(
        "INSERT OR IGNORE INTO corte_fijo (id, video_id, papel, orden, desde,"
        " hasta, toma, por_que, quien, fecha) VALUES (?,?,'etapa',?,?,?,?,?,?,?)",
        [(i, vid, b, x, y, tk, pq or "recuperado del recibo del EDL",
          "recuperar", ahora) for i, b, x, y, tk, pq in filas])
    cx.commit()
    return len(filas)


def _resumen(cx):
    for t in ("estructura", "etapa_canonica", "mecanismo", "toma", "video",
              "etapa", "unidad", "asignacion", "placa", "placa_etapa",
              "corte_fijo", "marca_humanidad", "correccion"):
        n = cx.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
        print(f"  {t:18} {n:4}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("crear")
    sub.add_parser("migrar")
    sub.add_parser("falta")
    p = sub.add_parser("plan"); p.add_argument("reel", type=int)
    r = sub.add_parser("recuperar"); r.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()

    if a.cmd == "recuperar":
        import rutas
        for n in (a.reels or rutas.piezas()):
            s = f"reel-{n:02d}"
            print(f"{s}: {recuperar(s)} declaracion(es) repuestas desde el recibo")
        raise SystemExit(0)

    if a.cmd == "crear":
        crear(); print(f"esquema creado en {RUTA}")
    elif a.cmd == "migrar":
        cx = migrar(); print(f"migrado a {RUTA}\n"); _resumen(cx)
    elif a.cmd == "plan":
        cx = abrir()
        for r in cx.execute("SELECT * FROM v_plan WHERE video = ?",
                            (f"reel-{a.reel:02d}",)):
            m = "!" if r["obligatorio"] else " "
            t = (f"{r['desde']:7.2f}-{r['hasta']:7.2f}"
                 if r["desde"] is not None else "      sin toma  ")
            print(f" {m}{r['etapa_n']:2} {r['etapa']:34} {t}  "
                  f"{(r['estado'] or 'pendiente'):10} {(r['texto'] or '')[:44]}")
    elif a.cmd == "falta":
        cx = abrir()
        for r in cx.execute("SELECT * FROM v_pendiente"):
            print(f"  {'!' if r['obligatorio'] else ' '} {r['video']} "
                  f"etapa {r['etapa_n']:2}  {r['etapa']}")
