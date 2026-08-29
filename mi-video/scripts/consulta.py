"""Las consultas que necesita `describir.mjs`, en un solo sitio.

El paso de IA vive en JavaScript porque ahí está el `fetch`, pero la base es de
Python en todo el resto del proyecto. En vez de abrir la base desde los dos
lados —dos formas de escribir la misma tabla es de donde salen los fallos de
este proyecto— el lado JS pide por nombre y aquí está la única implementación.

    python scripts/consulta.py escenas_por_describir '[[], false]'
    python scripts/consulta.py guardar_escena '["reel-03", 2, {...}]'
"""
import datetime
import json
import sqlite3
import sys

BASE = "ads/decisiones.db"


def escenas_por_describir(reels=None, rehacer=False):
    """Cada etapa con su función, su libreto y lo que se dijo de verdad."""
    con = sqlite3.connect(BASE)
    con.row_factory = sqlite3.Row
    donde = ""
    args = []
    if reels:
        donde = " and v.slug in (%s)" % ",".join("?" * len(reels))
        args = [f"reel-{int(r):02d}" for r in reels]
    if not rehacer:
        donde += (" and not exists (select 1 from escena_desc d"
                  " where d.video_slug = v.slug and d.etapa_orden = e.orden)")
    filas = con.execute(f"""
        select v.slug, e.orden, ec.nombre as etapa, es.nombre as estructura,
               e.mensaje_esperado as mensaje, l.texto as libreto,
               (select group_concat(u.texto, ' ') from eleccion el
                  join fragmento f on f.id = el.fragmento_id
                  join fragmento_unidad fu on fu.fragmento_id = f.id
                  join unidad u on u.id = fu.unidad_id
                 where el.etapa_id = e.id) as dicho
          from etapa e
          join video v on v.id = e.video_id
          join estructura es on es.id = e.estructura_id
          left join etapa_canonica ec
                 on ec.estructura_id = e.estructura_id and ec.orden = e.etapa_orden
          left join libreto l on l.video_id = v.id and l.orden = e.orden
         where l.texto is not null {donde}
         order by v.slug, e.orden
    """, args).fetchall()
    con.close()
    return [dict(f) for f in filas]


def guardar_escena(slug, orden, d):
    """Guarda la descripción. `ninguno` se guarda como NULL, no como texto."""
    con = sqlite3.connect(BASE)
    con.execute(
        "insert into escena_desc (video_slug, etapa_orden, que_pasa, emocion,"
        " componente, grafico, color, sonido, plano, trato, trato_porque,"
        " prioridad, integridad, remedio, corrige_dice, corrige_es,"
        " quien, fecha)"
        " values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        " on conflict(video_slug, etapa_orden) do update set"
        " que_pasa=excluded.que_pasa, emocion=excluded.emocion,"
        " componente=excluded.componente, grafico=excluded.grafico,"
        " color=excluded.color, sonido=excluded.sonido, plano=excluded.plano,"
        " trato=excluded.trato, trato_porque=excluded.trato_porque,"
        " prioridad=excluded.prioridad,"
        " integridad=excluded.integridad, remedio=excluded.remedio,"
        " corrige_dice=excluded.corrige_dice, corrige_es=excluded.corrige_es,"
        " quien=excluded.quien, fecha=excluded.fecha",
        (slug, int(orden), d["que_pasa"], d.get("emocion"),
         None if d.get("componente") in (None, "ninguno") else d["componente"],
         d.get("grafico"), d.get("color"), d.get("sonido"), d.get("plano"),
         d.get("trato"), d.get("trato_porque"), d.get("prioridad"),
         d.get("integridad"), d.get("remedio"),
         (d.get("corrige") or {}).get("dice"), (d.get("corrige") or {}).get("es"),
         # `quien` decia «gemini» y esa via se descarto —*«no quiero a
         # Google»*—, asi que el campo mentia sobre quien decidio.
         d.get("quien", "cli"),
         datetime.datetime.now().isoformat(timespec="seconds")))
    con.commit()
    con.close()
    return {"ok": True}


if __name__ == "__main__":
    fn = {"escenas_por_describir": escenas_por_describir,
          "guardar_escena": guardar_escena}[sys.argv[1]]
    args = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    print(json.dumps(fn(*args), ensure_ascii=False))
