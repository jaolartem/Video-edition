"""De dónde sale cada cifra que la pieza pone en pantalla.

Regla de Jaime, y es la que abre este paso: *«lo importante es que la fuente
aparezca en todos esos datos; pon en los CC el valor real, y un cuadro con la
fuente de la info»*.

## Por qué es un paso y no un campo

La atribución ya era obligatoria **en el código**: `Comparacion` no compila sin
`fuente`, `TwoPaths` exige `horizon` y `condition`. Eso es lo correcto —*«el
cumplimiento va en la API, no en la revisión»*— y aun así no bastaba, porque el
**valor** se escribía a mano en `reels-spec.mjs`, una cadena por pieza:

    fuente: "Cálculo de Jaime Olarte · $21 por cada $100 facturado"

Un literal por pieza es la misma trampa que un `if (slug === …)`: no escala a
16–50 anuncios, no se puede auditar, y el tablero que dibuja el **camino** —el
que se usa de verdad— ni siquiera recibía fuente. Así que la fuente tenía que
dejar de ser un adorno del spec y pasar a ser **un dato que viaja con la cifra**.

## Y por qué es un paso de IA

Porque comprobar una cifra es leer una fuente primaria y decidir si dice eso.
No es una consulta: es un juicio con evidencia. Así que va por el mismo contrato
que redundancia y revalidar —pedido fuera, respuesta dentro— y lo conteste el
CLI o la sesión, se valida igual.

Lo que este paso **no** hace: corregir la pieza. Dice qué respalda cada cifra y
en qué condiciones; qué se hace con una cifra que no se sostiene es decisión de
Jaime, porque cambia el mensaje.

    python scripts/fuentes.py          # las seis
    python scripts/fuentes.py 2        # solo el reel 2
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import sys
import rutas  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = "ads/decisiones.db"
PROMPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fuentes.prompt.md")

# Lo que cuenta como cifra en pantalla: dinero, porcentajes, años, plazos. No se
# busca «tres» ni «dos trabajos» — una cantidad sin unidad no se rotula ni se
# puede comprobar, y meterla haría ruido en un paso que tiene que ser exacto.
CIFRA = re.compile(r"(\$\s?[\d.,]+|\d[\d.,]*\s?(?:%|mil|millones|dólares|"
                   r"dolares|años|anos|semanas|meses|puntos)|\b\d{2,}[.,]\d+\b)",
                   re.IGNORECASE)


def _con():
    c = sqlite3.connect(BASE)
    c.row_factory = sqlite3.Row
    return c


def dossier(slug):
    """Las etapas que ponen una cifra delante del espectador, con su contexto.

    Se mira el libreto —lo que se quería decir—, el tratamiento y el gráfico
    —lo que se va a dibujar— porque **una cifra dibujada pesa más que una
    dicha**: la dicha pasa, la del tablero se queda en pantalla y se puede
    congelar y compartir.
    """
    con = _con()
    filas = con.execute(
        "select e.orden, l.texto as libreto, d.trato, d.grafico, d.que_pasa,"
        "       n.dice as corrige_dice, n.es as corrige_es"
        "  from etapa e"
        "  join video v on v.id = e.video_id"
        "  left join libreto l on l.video_id = v.id and l.orden = e.orden"
        "  left join escena_desc d on d.video_id = v.id and d.etapa_orden = e.orden"
        "  left join enmienda n on n.video_id = v.id and n.etapa_orden = e.orden"
        " where v.slug = ? order by e.orden", (slug,)).fetchall()
    con.close()
    out = []
    for f in filas:
        texto = " ".join(x for x in (f["libreto"], f["grafico"]) if x)
        cifras = sorted(set(m.group(0).strip() for m in CIFRA.finditer(texto)))
        if not cifras:
            continue
        out.append({"etapa": f["orden"], "cifras": cifras,
                    "libreto": f["libreto"], "trato": f["trato"],
                    "grafico": f["grafico"], "que_pasa": f["que_pasa"],
                    "corrige": ({"dice": f["corrige_dice"], "es": f["corrige_es"]}
                                if f["corrige_dice"] else None)})
    return out


def cargar(slug, respuesta):
    """Guarda lo que contestó el servicio. Devuelve cuántos datos quedaron.

    `sin_fuente` **se guarda igual que los demás**. Es la diferencia entre «no
    lo hemos mirado» y «lo miramos y no hay nada que lo sostenga», y sólo la
    segunda permite que la puerta se plante.
    """
    con = _con()
    vid = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not vid:
        con.close()
        raise SystemExit(f"{slug}: no está en la base")
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    n = 0
    for d in respuesta:
        fid = None
        if d.get("fuente"):
            con.execute(
                "insert into fuente (rotulo, organismo, url, vigencia, cita,"
                " fecha) values (?,?,?,?,?,?)"
                " on conflict(rotulo) do update set"
                " organismo=coalesce(excluded.organismo, fuente.organismo),"
                " url=coalesce(excluded.url, fuente.url),"
                " vigencia=coalesce(excluded.vigencia, fuente.vigencia),"
                " cita=coalesce(excluded.cita, fuente.cita)",
                (d["fuente"], d.get("organismo"), d.get("url"),
                 d.get("vigencia"), d.get("cita"), ahora))
            fid = con.execute("select id from fuente where rotulo = ?",
                              (d["fuente"],)).fetchone()["id"]
        con.execute(
            "insert into dato (video_id, etapa_orden, cifra, afirmacion,"
            " fuente_id, condiciones, respalda, nota, fecha)"
            " values (?,?,?,?,?,?,?,?,?)"
            " on conflict(video_id, etapa_orden, cifra) do update set"
            " afirmacion=excluded.afirmacion, fuente_id=excluded.fuente_id,"
            " condiciones=excluded.condiciones, respalda=excluded.respalda,"
            " nota=excluded.nota, fecha=excluded.fecha",
            (vid["id"], int(d.get("etapa") or 0), d["cifra"],
             d.get("afirmacion") or "", fid, d.get("condiciones"),
             d.get("respalda") or "sin_fuente", d.get("nota"), ahora))
        n += 1
    con.commit()
    con.close()
    return n


def sin_respaldo(slug):
    """Las cifras que la pieza pone en pantalla y no se sostienen.

    Es lo que mira la puerta. `no` es peor que `sin_fuente`: `sin_fuente` es que
    no se encontró respaldo; `no` es que la fuente **dice otra cosa**, y eso ya
    no es un hueco, es una afirmación contradicha.
    """
    con = _con()
    filas = con.execute(
        "select d.etapa_orden, d.cifra, d.respalda, d.nota from dato d"
        "  join video v on v.id = d.video_id"
        " where v.slug = ? and d.respalda in ('no','sin_fuente')"
        " order by d.etapa_orden", (slug,)).fetchall()
    con.close()
    return [dict(f) for f in filas]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    a = ap.parse_args()
    import servicio as contrato
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        filas = dossier(slug)
        if not filas:
            print(f"{slug}: ninguna cifra en pantalla")
            continue
        prompt = open(PROMPT, encoding="utf-8").read()
        r = contrato.pedir("fuentes", slug, prompt, filas)
        if r is None:
            print(f"{slug}: espera respuesta del servicio -> "
                  f"{contrato.ruta_pedido('fuentes', slug)}")
            continue
        print(f"{slug}: {cargar(slug, r)} dato(s) con su respaldo")
        for x in sin_respaldo(slug):
            print(f"    · [{x['respalda']}] e{x['etapa_orden']} {x['cifra']}")


if __name__ == "__main__":
    main()
