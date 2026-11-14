"""Cataloga la grabación ENTERA en la base, y de ahí se selecciona.

Regla de Jaime, y es la que faltaba: *«tienes que catalogar toda la grabación y
de ahí seleccionar las mejores tomas, para eso hicimos un SQL»*. Y antes de eso:
*«buscas pero no catalogas todo lo que hay en el video... si no encuentras nada
es porque honestamente ni has mirado»*.

## Qué cambia respecto de lo que había

`beats.py` construía sus candidatos en memoria, los filtraba por calidad **antes
de mirarlos** y se quedaba con el primero que encajaba. Tres consecuencias, las
tres vistas en el lote:

- Una unidad que no pasaba el filtro **no existía**, aunque dijera la única cifra
  que la etapa necesitaba.
- La búsqueda paraba en la primera aparición, y por cómo graba Jaime —repite
  hasta que sale— **la buena suele ser la última**.
- Nadie podía ver qué había en la cinta sin volver a correr el montaje.

Aquí se invierte: **se cataloga todo y no se descarta nada**. Lo que antes era un
filtro pasa a ser una columna —el aire, si abre en mayúscula, si cierra en punto,
la expresividad— y la selección decide mirando la tabla entera.

    python scripts/catalogar.py            # las seis tomas
    python scripts/catalogar.py --toma 3   # sólo la del reel 3

Después, en la base:

    select desde, hasta, texto from unidad where texto like '%dentista%'
"""
import argparse
import json
import os
import re
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
from dominio.idioma import Idioma  # noqa: E402
import rutas  # noqa: E402
import transcribir  # noqa: E402

BASE = os.path.join("ads", "decisiones.db")


def unidades(toma):
    """Cada tramo de voz medido, tal cual, sin filtrar por calidad.

    **La unidad es el tramo, no la frase.** Antes se partia por la puntuacion
    del modelo y salian unidades de 98 segundos con tres etapas dentro, porque
    `whisper -ml 1 -sow` apenas puntua: 48 signos en 767 palabras. La pausa, en
    cambio, esta **medida** por el detector de habla y no depende de que el
    modelo acierte.

    Un tramo no es un enunciado —Jaime avisa de lo contrario: *«hay silencios
    entre la misma frase, sólo me quedé callado pensando»*— y por eso el
    enunciado se compone despues, en `seleccionar.py`, juntando tramos hasta que
    dicen lo que la etapa necesita. Aqui se cataloga el atomo; alli se decide.

    Y no se descarta nada: lo que en su dia era motivo de exclusion —el aire, si
    abre en mayuscula, si cierra en punto— se guarda como columna.
    """
    # El peldano barato del embudo SI lee una cinta de una pasada: para eso
    # existe —catalogar con `small` y afinar despues solo lo preseleccionado
    # (C-59)—. Lo declara en vez de que la puerta se lo calle para todos.
    d = transcribir.exigir(toma, varias=False)
    ws = d["segmentos"]
    runs = json.load(open(f"work/cuts/{toma}.json", encoding="utf-8"))["segmentos"]

    por_tramo = [[] for _ in runs]
    k = 0
    for w in sorted(ws, key=lambda w: w["start"]):
        c = (w["start"] + w["end"]) / 2
        while k + 1 < len(runs) and c >= runs[k][1]:
            k += 1
        if runs[k][0] - 0.25 <= c < runs[k][1] + 0.25:
            por_tramo[k].append(w)

    # El acuerdo entre pasadas, por tramo: por debajo de 0,6 hay que oirlo.
    acuerdos = {round(m["cinta"], 2): m.get("acuerdo", 1.0)
                for m in d.get("tramos", [])}

    out = []
    for k, (a, b) in enumerate(runs):
        txt = " ".join(w["text"] for w in por_tramo[k]).strip()
        if not txt or b - a < 0.4:
            continue
        out.append({
            "desde": round(a, 3), "hasta": round(b, 3), "texto": txt,
            "aire": 0.0,          # dentro de un tramo, por definicion, no hay
            "abre": int(bool(txt[:1].isupper() or txt[:1] in "¿¡")),
            "cierra": int(bool(re.search(r"[.!?]$", txt))),
            "acuerdo": acuerdos.get(round(a, 2), 1.0),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--toma", type=int, help="sólo el reel N")
    ap.add_argument("--voz", action="store_true",
                    help="medir la expresividad de cada unidad (lento)")
    a = ap.parse_args()

    con = basedatos.abrir(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    reels = [a.toma] if a.toma else rutas.piezas()
    for n in reels:
        slug = f"reel-{n:02d}"
        toma = rutas.TOMAS[slug]
        fila = con.execute("select id from toma where nombre = ?", (toma,)).fetchone()
        if not fila:
            cur = con.execute("insert into toma (nombre) values (?)", (toma,))
            toma_id = cur.lastrowid
        else:
            toma_id = fila[0]

        us = unidades(toma)
        # **No se borra lo que ya hay**: `asignacion` cuelga de `unidad`, y
        # borrar una unidad se llevaria por delante una decision tomada.
        nuevas = 0
        for u in us:
            voz = None
            if a.voz:
                _v = beats.expresividad(toma, u["desde"], u["hasta"])
                voz = None if _v is None else round(_v, 2)
            try:
                con.execute(
                    "insert into unidad (toma_id, desde, hasta, texto, aire, abre,"
                    " cierra, voz_st) values (?,?,?,?,?,?,?,?)",
                    (toma_id, u["desde"], u["hasta"], u["texto"], u["aire"],
                     u["abre"], u["cierra"], voz))
                nuevas += 1
            except sqlite3.IntegrityError:
                con.execute(
                    "update unidad set texto=?, aire=?, abre=?, cierra=?"
                    " where toma_id=? and desde=? and hasta=?",
                    (u["texto"], u["aire"], u["abre"], u["cierra"],
                     toma_id, u["desde"], u["hasta"]))
        # **Lo que ya no es un tramo medido, sobra.** Quedaron las unidades de la
        # epoca en que se partia por la puntuacion del modelo —hasta 98 s, con
        # tres etapas dentro— y conviven con las nuevas falseando cualquier
        # consulta. Se van, salvo las que sostienen una decision ya tomada: esas
        # se dicen por su nombre en vez de desaparecer.
        buenas = {(round(u["desde"], 3), round(u["hasta"], 3)) for u in us}
        viejas = [(i, a, b) for i, a, b in con.execute(
            "select id, desde, hasta from unidad where toma_id = ?", (toma_id,))
            if (round(a, 3), round(b, 3)) not in buenas]
        atadas = {r[0] for r in con.execute(
            "select distinct unidad_id from asignacion where unidad_id is not null")}
        fuera = [i for i, _, _ in viejas if i not in atadas]
        if fuera:
            con.executemany("delete from unidad where id = ?",
                            [(i,) for i in fuera])
        quedan = [i for i, _, _ in viejas if i in atadas]
        con.commit()
        if fuera or quedan:
            aviso = f"    limpieza: {len(fuera)} unidades viejas fuera"
            if quedan:
                aviso += (f"; {len(quedan)} se quedan porque sostienen una"
                          f" asignacion (ids {quedan})")
            print(aviso)
        total = con.execute(
            "select count(*), round(sum(hasta-desde),1) from unidad where toma_id=?",
            (toma_id,)).fetchone()
        print(f"{slug} · {toma}: {len(us)} frases en la cinta, {nuevas} nuevas "
              f"→ la base tiene {total[0]} unidades ({total[1]} s)")

        # ── la candidatura ──────────────────────────────────────────────────
        #
        # **Cada seccion de cinta contra cada funcion del frame.** Regla de
        # Jaime: *«cada seccion de la cinta se relaciona con lo que debe decir
        # en el libreto y a su vez con la funcion en el frame»*.
        #
        # `dice` sale de `debe_decir`, que es lo declarado; `cubre`, de la misma
        # puntuacion de cobertura que usa el montaje contra el parrafo del
        # libreto. Con las dos columnas la seleccion deja de ser una busqueda
        # que para en el primero: es un `order by` sobre la tabla entera.
        libreto = beats.beats_del_libreto(n)
        frame = beats.frame_del_reel(n, libreto)
        etapas = con.execute(
            "select e.id, e.orden, e.mensaje_esperado from etapa e"
            " join video v on v.id = e.video_id where v.slug = ?"
            " order by e.orden", (slug,)).fetchall()
        filas = con.execute(
            "select id, desde, hasta, texto from unidad where toma_id = ?",
            (toma_id,)).fetchall()
        puestas = 0
        for eid, orden, mensaje in etapas:
            exige = (frame["beats"][orden - 1].get("debe_decir") or []
                     if orden - 1 < len(frame["beats"]) else [])
            parr = libreto[orden - 1] if orden - 1 < len(libreto) else mensaje
            for uid, d, h, txt in filas:
                idioma = Idioma.de_pieza(slug)
                u = {"a": d, "b": h, "texto": txt,
                     "clave": set(beats.norm(txt, idioma))}
                cubre = round(float(beats.puntua(parr, u, idioma)), 3)
                dice_ = int(bool(exige) and
                            all(beats.dice(txt, t) for t in exige))
                con.execute(
                    "insert into candidatura (etapa_id, unidad_id, dice, cubre)"
                    " values (?,?,?,?) on conflict(etapa_id, unidad_id) do update"
                    " set dice = excluded.dice, cubre = excluded.cubre",
                    (eid, uid, dice_, cubre))
                puestas += 1
        con.commit()
        print(f"    candidaturas: {puestas} ({len(etapas)} etapas x {len(filas)} unidades)")
    con.close()


if __name__ == "__main__":
    main()
