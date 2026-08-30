"""Re-calificar lo elegido después del paso caro, y pasar a la siguiente si cae.

Es el bucle que Jaime describió entero:

    *«Seguimos calificando con entrega emocional, ése es nuestro criterio de
    selección. Si después de las cuatro pasadas baja su puntaje, o es demasiado
    fragmentado, si no hay ritmo y si no hay cambio de tono, entonces escogemos
    el siguiente»* — *«hasta encontrar el mejor costo/beneficio»*.

Y quién decide:

    *«Por eso es importante que el LLM sea el que lo revisa también, y por eso
    define si pasa o no basándose en los tres elementos pero sobre todo en la
    intención comunicativa: si el mensaje llega muy roto, pues no llegó.»*

## Los números no deciden, informan

Aquí se miden cuatro cosas sobre el tramo ya afinado, y **ninguna vota sola**:

    voz         recorrido de F0 en semitonos — la entrega emocional
    tono        cuánto se MUEVE la voz, st/s — leer plano da bajo aunque el
                recorrido sea ancho, que es la trampa que `voz` no ve
    ritmo       variación de la velocidad del habla — una lectura mantiene el
                mismo paso de principio a fin
    continuidad qué fracción de las costuras respeta una frontera de idea

El veredicto lo da el LLM leyendo **el texto** con esos números al lado, porque
la pregunta final no es numérica: *¿llega la intención?*. Un tramo con buenos
números y el mensaje partido no pasa, y uno con números mediocres que dice lo
que tiene que decir, sí.

## El coste manda cuándo parar

Cada intento cuesta un afinado con el modelo bueno. Así que no se busca «la que
pase», se busca **el mejor coste/beneficio**: se prueban como mucho `INTENTOS`
candidatas, se guarda siempre la mejor vista, y si una tanda no mejora a la
mejor, se para y se queda ésa. Seguir tirando candidatas dejó la etapa 2 del
reel 1 peor de lo que estaba — ya pasó una vez (C-65).

    python scripts/revalidar.py 1          # el dossier del reel 1
    python scripts/revalidar.py --json 1   # para el paso de IA
"""
import argparse
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
import beats  # noqa: E402
import depurar  # noqa: E402
import transcribir  # noqa: E402
import rutas  # noqa: E402

# Cuántas candidatas se prueban por etapa antes de quedarse con la mejor vista.
# Tres es el punto donde el afinado deja de pagarse: la cuarta rara vez mejora y
# cuesta lo mismo que las tres primeras juntas.
INTENTOS = 3

# Suelos de referencia. **No son puertas** — son lo que el dossier marca para que
# el LLM sepa dónde mirar. Medidos sobre lo elegido de estas seis cintas.
SUELO = {"voz": 4.3, "tono": 18.0, "ritmo": 0.30, "continuidad": 0.5}


def medir(toma, palabras, tramos):
    """Las cuatro medidas sobre los tramos ya afinados de una etapa."""
    a = min(x for x, _ in tramos)
    b = max(y for _, y in tramos)
    rotas, costuras, esquirlas = depurar.continuidad(palabras, sorted(tramos))
    return {
        "desde": round(a, 2),
        "hasta": round(b, 2),
        "voz": round(float(beats.expresividad(toma, a, b)), 2),
        "tono": round(beats.cambio_de_tono(toma, a, b), 1),
        "ritmo": round(beats.ritmo(palabras, a, b), 2),
        "continuidad": (round(1 - rotas / costuras, 2) if costuras else 1.0),
        "trozos": len(tramos),
        "esquirlas": esquirlas,
    }


def flojo(m):
    """Qué medidas quedan por debajo de su suelo. Informa, no descalifica."""
    return [k for k, v in SUELO.items() if m.get(k, 0) < v]


def candidatas(slug, beat, cuantas=3):
    """Las otras opciones de esa etapa, con su texto y su puntuacion.

    Jaime, definiendo el contrato: *«por contrato recibes la informacion de cada
    escena y el contexto de las otras candidatas, para saber cual escoges»*.
    Elegir sin ver las alternativas no es elegir — y hasta ahora el dossier
    mandaba la elegida sola, asi que lo unico que se podia contestar era «esta
    vale o no vale», nunca «esta otra vale mas».

    Tres, que es el tope del embudo: *«si ninguna de las tres candidatas es, pues
    la que mejor puntaje tenga»*.
    """
    con = sqlite3.connect("ads/decisiones.db")
    con.row_factory = sqlite3.Row
    filas = con.execute(
        "select c.puesto, c.puntuacion, c.voz_st, f.desde, f.hasta, t.nombre toma"
        " from candidato c join etapa e on e.id = c.etapa_id"
        " join video v on v.id = e.video_id"
        " join fragmento f on f.id = c.fragmento_id"
        " join toma t on t.id = f.toma_id"
        " where v.slug = ? and e.orden = ? order by c.puesto limit ?",
        (slug, beat, cuantas)).fetchall()
    con.close()
    out = []
    for r in filas:
        try:
            pal = transcribir.exigir(r["toma"])["segmentos"]
        except SystemExit:
            pal = []
        txt = " ".join(w["text"] for w in pal
                       if r["desde"] - 0.02 <= w["start"]
                       and w["end"] <= r["hasta"] + 0.02)
        out.append({"puesto": r["puesto"],
                    # **La puntuación puede no estar, y eso no es cero.** Es la
                    # cuarta vez que este patrón rompe algo: hacer representable
                    # el «no medido» obliga a mirar todos los sitios que asumían
                    # un número (C-63 y las dos de hoy).
                    "puntuacion": (round(r["puntuacion"], 3)
                                   if r["puntuacion"] is not None else None),
                    "desde": round(r["desde"], 2), "hasta": round(r["hasta"], 2),
                    "dura": round(r["hasta"] - r["desde"], 1),
                    "texto": txt[:400]})
    return out


def dossier(slug):
    """Lo que el LLM necesita para decidir: el texto, sus números y las otras."""
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding="utf-8"))
    cache = {}
    por_beat = {}
    for rango, det in zip(edl["segmentos"], edl["detalle"]):
        por_beat.setdefault(det["beat"], {"tramos": [], "det": det})
        por_beat[det["beat"]]["tramos"].append(tuple(rango))
    out = []
    for beat, d in sorted(por_beat.items()):
        toma = d["det"].get("toma") or rutas.TOMAS[slug]
        if toma not in cache:
            try:
                cache[toma] = transcribir.exigir(toma)["segmentos"]
            except SystemExit:
                cache[toma] = []
        pal = cache[toma]
        m = medir(toma, pal, d["tramos"])
        texto = " ".join(
            w["text"] for x, y in sorted(d["tramos"])
            for w in pal if x - 0.02 <= w["start"] and w["end"] <= y + 0.02)
        try:
            inten = beats.intensidad(toma, m["desde"], m["hasta"], pal)
        except Exception:                          # noqa: BLE001
            inten = {}
        out.append({
            "beat": beat,
            "etapa": d["det"].get("etapa"),
            "trato": d["det"].get("trato"),
            **m,
            "intensidad": inten.get("intensidad"),
            "flojo": flojo(m),
            "texto": texto,
            # **Y las otras candidatas.** Sin esto solo se puede contestar «vale
            # o no vale»; con esto se puede elegir.
            "candidatas": candidatas(slug, beat),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--json", action="store_true",
                    help="para el paso de IA, que es quien decide")
    a = ap.parse_args()
    todo = {}
    for n in (a.reels or [1, 2, 3, 4, 5, 6]):
        slug = f"reel-{n:02d}"
        filas = dossier(slug)
        if not filas:
            continue
        todo[slug] = filas
        if a.json:
            continue
        print(f"\n{slug}")
        for f in filas:
            marca = (" ← " + ",".join(f["flojo"])) if f["flojo"] else ""
            print(f"  e{f['beat']:<2} voz {f['voz']:>4.1f}  tono {f['tono']:>5.1f}"
                  f"  ritmo {f['ritmo']:>4.2f}  cont {f['continuidad']:>4.2f}"
                  f"  {f['trozos']:>2} trozo(s){marca}")
            print(f"      {f['texto'][:100]}")
    if a.json:
        print(json.dumps(todo, ensure_ascii=False, indent=1))
    else:
        print("\nLos numeros informan; **quien decide si pasa es el LLM**, y decide"
              "\nsobre la intencion comunicativa: si el mensaje llega muy roto, no llego.")


if __name__ == "__main__":
    main()
