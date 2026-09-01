"""El transcript como fichero: cómo se escribe y qué se sanea al leerlo.

**Por qué es una responsabilidad propia.** Transcribir es una cosa —arrancar el
modelo, oír una ventana, votar entre pasadas— y **guardar** es otra: dónde va el
fichero, qué se estampa en él para que se sepa cómo se hizo, qué llega a la base
y qué filtros se le pasan al leerlo aunque no existieran cuando se escribió.

Estaban juntas en `transcribir.py`, y por eso ese fichero seguía por encima del
techo cuando ya sólo le quedaba una cosa que hacer.

**La regla que gobierna `_saneado`, y es del proyecto entero:** un arreglo que
sólo vale para las cintas futuras no arregla nada — las siete de este proyecto
costaron horas de CPU y no se van a rehacer porque un filtro crezca. Así que se
aplica **al pasar**, que es cuando el paso ya tiene el fichero delante.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402


def guardar(toma, palabras, mapa, dudosos, modelo=None, paso=None):
    """Escribe EL transcript, no uno paralelo.

    Dos ficheros describiendo la misma cinta es el aprendizaje 33, y ya costo
    cuatro fallos: se corrige uno y el otro sigue diciendo lo de antes. Asi que
    esto sustituye a `work/transcripts/<toma>.json` en vez de convivir con el.
    """
    from transcribir import MODELO, PASO, SELLO, VENTANA, gpu, sin_fantasmas

    os.makedirs("work/transcripts", exist_ok=True)
    ruta = f"work/transcripts/{toma}.json"
    con_texto = [m for m in mapa if m.get("texto")]
    # **El sello dice lo que se hizo, no lo que dice la constante.** Guardaba
    # `PASO` del modulo mientras la corrida usaba otro: con `--pasadas 4` el
    # paso real es 7,5 y el fichero declaraba 10. Un sello que miente sobre su
    # procedencia hace imposible comparar dos corridas, que es exactamente para
    # lo que existe.
    json.dump({"toma": toma, "ventana": VENTANA, "paso": paso or PASO,
               "modelo": os.path.basename(modelo or MODELO).replace("ggml-", "").replace(".bin", ""),
               # **Quien lo transcribio va en el sello.** El fichero ya declara
               # con que modelo y con cuantas pasadas se hizo, por el mismo
               # motivo: `comparar.py` contrasta dos corridas y sin saber de
               # donde sale cada una la comparacion no significa nada. Ahora hay
               # dos caminos —la tarjeta y la CPU— y aunque el texto sale igual
               # (medido, 1,000 de parecido), eso es un hecho a comprobar en
               # cada corrida, no una suposicion a heredar.
               "dispositivo": gpu.sello(),
               SELLO: len(con_texto) and round(
                   sum(m["pasadas"] for m in con_texto) / len(con_texto), 2),
               "dudosos": dudosos,
               "segmentos": sin_fantasmas(palabras),
               "tramos": con_texto},
              open(ruta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # El fichero ya esta escrito arriba. Lo que sigue es la base, y **un fallo
    # ahi no puede tirar quince minutos de transcripcion**: se avisa y se sigue.
    # Paso de verdad: `subtitulo.acuerdo` era NOT NULL de una version anterior y
    # `CREATE TABLE IF NOT EXISTS` no altera lo que ya existe, asi que al
    # empezar a guardar «acuerdo desconocido» reventaba el guardado entero.
    try:
        _guardar_en_base(toma, mapa)
    except Exception as e:                        # noqa: BLE001
        registro.error("transcribir", "no se pudo guardar en la base",
                       toma=toma, detalle=str(e)[:160])
    return ruta

def _guardar_en_base(toma, mapa):
    from transcribir import BASE

    con = basedatos.abrir(BASE)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript("""
      CREATE TABLE IF NOT EXISTS subtitulo (
        toma_id INTEGER NOT NULL REFERENCES toma(id) ON DELETE CASCADE,
        desde   REAL NOT NULL,
        hasta   REAL NOT NULL,
        texto   TEXT NOT NULL,
        acuerdo REAL,
        pasadas INTEGER NOT NULL,
        PRIMARY KEY (toma_id, desde)
      );
    """)
    fila = con.execute("select id from toma where nombre = ?", (toma,)).fetchone()
    toma_id = fila[0] if fila else con.execute(
        "insert into toma (nombre) values (?)", (toma,)).lastrowid
    con.execute("delete from subtitulo where toma_id = ?", (toma_id,))
    con.executemany(
        "insert into subtitulo (toma_id, desde, hasta, texto, acuerdo, pasadas)"
        " values (?,?,?,?,?,?)",
        [(toma_id, round(m["cinta"], 3), round(m["cinta"] + m["dur"], 3),
          m["texto"], m["acuerdo"], m["pasadas"])
         for m in mapa if m.get("texto")])
    con.commit()
    con.close()

def _saneado(toma, d):
    """Pasa por el transcript ya escrito los filtros que no existian al hacerlo.

    **Un arreglo que solo vale para las cintas futuras no arregla nada**: las
    siete de este proyecto costaron horas de CPU y no se van a rehacer porque
    el filtro de etiquetas creciera. Asi que se aplica al pasar, que es cuando
    el paso ya tiene el fichero delante, y se reescribe solo si cambio algo.

    Es la misma idea que la cobertura de C-89: el paso comprueba el resultado
    que tiene, no el trabajo que recuerda haber hecho.
    """
    from transcribir import sin_etiquetas, sin_fantasmas

    ws = d.get("segmentos") or []
    # `sin_etiquetas` habla en el idioma de la transcripcion —`t`— y el fichero
    # guarda `text`; se traduce en los dos sentidos en vez de duplicar la regla.
    puente = [{"t": w["text"], "_w": w} for w in ws]
    limpias = [x["_w"] for x in sin_etiquetas(puente)]
    limpias = sin_fantasmas(limpias)
    if len(limpias) == len(ws):
        return d, 0
    quitadas = len(ws) - len(limpias)
    d["segmentos"] = limpias
    json.dump(d, open(f"work/transcripts/{toma}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return d, quitadas
