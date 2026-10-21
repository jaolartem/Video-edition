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
import subprocess
import basedatos
import sys
import rutas  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dominio.escena import correcciones as _correcciones  # noqa: E402

BASE = "ads/decisiones.db"
PROMPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fuentes.prompt.md")

# Lo que cuenta como cifra en pantalla: dinero, porcentajes, años, plazos. No se
# busca «tres» ni «dos trabajos» — una cantidad sin unidad no se rotula ni se
# puede comprobar, y meterla haría ruido en un paso que tiene que ser exacto.
CIFRA = re.compile(r"(\$\s?[\d.,]+|\d[\d.,]*\s?(?:%|mil|millones|dólares|"
                   r"dolares|años|anos|semanas|meses|puntos)|\b\d{2,}[.,]\d+\b)",
                   re.IGNORECASE)


def _normal(c):
    """La misma cifra escrita de dos maneras es una cifra, no dos.

    Sin esto la puerta contaba `$20` y `$20.` como dos rotulos distintos, y
    `$180,000` y `$180.000` como dos cifras — cada una pidiendo su fuente. Una
    puerta que reclama el doble de lo que hay se aprende a ignorar, y entonces
    deja de ser una puerta.

    Se quita la puntuacion que arrastra el final de una frase y se unifica el
    separador de miles. Lo que NO se toca es el valor: `25.000` y `25` son
    cifras distintas y tienen que seguir siendolo.
    """
    c = (c or "").strip().rstrip(".,;:)")
    if not c:
        return ""
    # El separador de miles se escribe con punto o con coma segun quien teclee;
    # se unifica a coma para que `180.000` y `180,000` sean el mismo rotulo.
    c = re.sub("(?<=[0-9])[.](?=[0-9]{3})", ",", c)
    # Y el decimal: `53.53%` y `53,53%` son el mismo numero escrito por dos
    # teclados distintos, no dos rotulos que respaldar por separado.
    c = re.sub("(?<=[0-9])[.](?=[0-9]{1,2}(?![0-9]))", ",", c)
    return re.sub(r"\s+", " ", c)


def _con():
    c = basedatos.abrir(BASE)
    c.row_factory = sqlite3.Row
    return c


def propias():
    """Las cifras cuya fuente es el proyecto, no un organismo.

    El precio del bootcamp no lo respalda la CRA: lo pone Jaime, y vive en la
    tabla `precio` con su escalon y su fecha de cierre. Pedirle una fuente
    externa es pedirle que demuestre su propio precio, y una puerta que reclama
    lo que no tiene sentido reclamar es una puerta que se aprende a saltar.

    Cinco de las treinta y ocho cifras del lote eran esto. Se declaran aqui como
    respaldadas por su origen —la escalera— y siguen siendo comprobables: si el
    escalon cambia, la cifra deja de casar y vuelve a salir.

    Lo que esto **no** cubre: cualquier numero que no sea exactamente un importe
    de la escalera. Un `$21` derivado de un calculo no es el precio.
    """
    con = _con()
    filas = con.execute("select importe, desde, hasta, nota from precio"
                        " order by hasta").fetchall()
    con.close()
    fuera = {}
    # **La fecha del evento tambien es de la casa.** Es su bootcamp: la fija el
    # y vive en el ultimo escalon, el que «cierra con el evento». Pedirle un
    # organismo que respalde cuando da su propia charla es la misma clase de
    # ruido que pedirle que demuestre su precio.
    ult = filas[-1] if filas else None
    if ult and (ult["hasta"] or ""):
        d = (ult["hasta"] or "")[:10].split("-")
        MES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
               "agosto", "septiembre", "octubre", "noviembre", "diciembre")
        if len(d) == 3:
            dia = f"{int(d[2])} de {MES[int(d[1]) - 1]}"
            respaldo = ("Jaime Olarte Finanzas · fecha del evento",
                        f"el evento es el {dia} de {d[0]}")
            for forma in (dia, f"El {dia}", f"el {dia}", d[0]):
                fuera[forma] = respaldo
    for f in filas:
        vale = f"${f['importe']}"
        cierra = (f["hasta"] or "")[:10]
        fuera[vale] = ("Jaime Olarte Finanzas · escalera de precios del evento",
                       f"escalon de {vale} hasta el {cierra}"
                       + (f" · {f['nota']}" if f["nota"] else ""))
    return fuera


def pintadas(slug):
    """Lo que los tableros pintan sin fila en `dato`, contado por quien para.

    Este dossier buscaba cifras en el libreto y en `grafico`, y la puerta en
    los props que se pintan: R20 rotulaba «$2,50» y «$0,10» en un tablero, aquí
    no salió ninguna y el paso pasó con «ninguna cifra en pantalla» (C-616). Se
    le pregunta a `cifras.mjs`, que es el dueño. Y si no contesta, se para: no
    medir no es aprobar.
    """
    cifras = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "reels", "cifras.mjs")
    r = subprocess.run(["node", cifras, "--sin-respaldo", slug],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"{slug}: cifras.mjs no dijo qué se pinta —"
                           f" {(r.stderr or '').strip()[:300]}")
    por = {}
    for x in json.loads(r.stdout):
        por.setdefault(int(x["beat"]), []).append(x["cifra"])
    return por


def _props(tablero):
    """Lo que el tablero pinta, con su fuente declarada al pie si la lleva."""
    try:
        return (json.loads(tablero) or {}).get("props") if tablero else None
    except (ValueError, AttributeError):
        return None


def dossier(slug):
    """Las etapas que ponen una cifra delante del espectador, con su contexto.

    Se mira el libreto —lo que se quería decir—, el tratamiento y el gráfico
    —lo que se va a dibujar— porque **una cifra dibujada pesa más que una
    dicha**: la dicha pasa, la del tablero se queda en pantalla y se puede
    congelar y compartir.
    """
    con = _con()
    # **Por `video_slug`, que es lo que la descripción siempre lleva.** Se unía
    # por `video_id`, y 98 de 152 filas lo tienen vacío —de reel-07 en
    # adelante—: a este paso no le llegaba ni el gráfico ni el tratamiento de
    # dieciséis piezas (C-616). `arco.py` ya la une así.
    filas = con.execute(
        "select e.orden, l.texto as libreto, d.trato, d.grafico, d.que_pasa,"
        "       d.corrige_dice, d.corrige_es, d.tablero"
        "  from etapa e"
        "  join video v on v.id = e.video_id"
        "  left join libreto l on l.video_id = v.id and l.orden = e.orden"
        "  left join escena_desc d on d.video_slug = v.slug and d.etapa_orden = e.orden"
        " where v.slug = ? order by e.orden", (slug,)).fetchall()
    con.close()
    pinta = pintadas(slug)
    out = []
    for f in filas:
        # **Del libreto y de lo pintado, no de la instrucción del gráfico**
        # (C-639). `grafico` es cómo se maqueta —«por encima del 52 % de
        # altura», «sale a los 5,0 s»— y sus números no se afirman: reel-21,
        # aprobada, se paró pidiendo respaldo para un «52 %» que no sale en
        # pantalla. Lo que el gráfico dibuja lo cuenta `pintadas`, su dueño.
        texto = f["libreto"] or ""
        cifras = sorted({_normal(m.group(0)) for m in CIFRA.finditer(texto)}
                        | set(pinta.get(f["orden"], [])))
        cifras = [c for c in cifras if c]
        # **El precio no necesita fuente externa: es de la casa.** Se marca aqui
        # para que el paso de respaldo no lo pregunte y quien contesta no gaste
        # una decision en ello. Ver `propias()`.
        de_casa = propias()
        propia = {c: de_casa[c] for c in cifras if c in de_casa}
        if not cifras:
            continue
        out.append({"etapa": f["orden"], "cifras": cifras,
                    "ya_respaldadas": propia,
                    "libreto": f["libreto"], "trato": f["trato"],
                    "grafico": f["grafico"], "que_pasa": f["que_pasa"],
                    "tablero": _props(f["tablero"]),
                    # Una o varias (C-465).
                    "corrige": ([{"dice": d, "es": e} for d, e in
                                 _correcciones(f["corrige_dice"], f["corrige_es"])]
                                or None)})
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


# La marca con la que una cifra se declara parte de un caso construido. Va en
# `nota` porque `respalda` tiene su CHECK cerrado en la base y ampliarlo seria
# migrar la tabla para decir algo que cabe en el texto. Lo importante es que sea
# **una sola cadena**, escrita en el contrato: un agente la invento por su
# cuenta y funciono, y lo que funciona por casualidad se rompe a la tercera.
HIPOTETICO = "CASO_HIPOTETICO"


def sin_respaldo(slug):
    """Las cifras que la pieza pone en pantalla y no se sostienen.

    Es lo que mira la puerta. `no` es peor que `sin_fuente`: `sin_fuente` es que
    no se encontró respaldo; `no` es que la fuente **dice otra cosa**, y eso ya
    no es un hueco, es una afirmación contradicha.
    """
    #
    # **Y un caso hipotetico declarado no es un hueco.** Regla del proyecto,
    # escrita al resolver la etapa 5 de reel-04: *«un caso hipotetico declarado
    # no necesita fuente externa: necesita que el mecanismo que describe sea
    # cierto. Si la relacion causal se sostiene, la afirmacion se sostiene
    # aunque no exista un documento que la diga»*.
    #
    # Un electricista que factura 180 mil no es una afirmacion sobre el mundo:
    # es un ejemplo construido para explicar una mecanica. Pedirle una fuente es
    # pedirle un documento a algo que nadie dijo que hubiera pasado — y con eso
    # reel-02 paraba por 21 cifras de las que 8 eran esto.
    #
    # Lo que si tiene que estar es **declarado**: la nota dice que es un ejemplo,
    # y el tablero lo rotula. Un hipotetico sin declarar sigue siendo un hueco.
    con = _con()
    filas = con.execute(
        "select d.etapa_orden, d.cifra, d.respalda, d.nota from dato d"
        "  join video v on v.id = d.video_id"
        " where v.slug = ? and d.respalda in ('no','sin_fuente')"
        "   and coalesce(d.nota,'') not like ?"
        " order by d.etapa_orden", (slug, f"%{HIPOTETICO}%")).fetchall()
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
