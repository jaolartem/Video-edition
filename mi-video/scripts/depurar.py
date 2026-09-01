"""Borra los segundos que no aportan. Después de elegir la escena, no antes.

Regla de Jaime, y señala un paso que faltaba: *«el filtro de la redundancia se
aplica después de escoger la escena; lo que no aporte, o los segundos que no
aporten, se deben borrar»*. Y el diagnóstico: *«noto con el primero que el filtro
contra redundancia no se aplicó — ese paso no está en código dentro del
pipeline»*.

`seleccionar.py` poda **la selección**: decide qué trozo se usa. Eso no dice cómo
se corta por dentro, así que lo que llegaba al montaje seguía trayendo el aire y
los intentos fallidos. El reel 1 abría con **ocho segundos para decir cuatro
palabras**.

**Este fichero es el paso, no las tijeras.** Lo que se quita —el aire, el ensayo
y el tartamudeo— lo sabe `dominio.depuracion`, que es donde vive la regla y donde
la usan también `seleccionar` para predecir cuánto sobrevive una toma. Aquí queda
el recorrido: abrir el corte de cada pieza, aplicarlo, anotar lo que queda roto y
escribir. Los nombres que ya llamaban desde fuera siguen aquí y delegan.

## Lo que ya NO hace, y es deliberado

**La redundancia de sentido no vive aqui.** Jaime, despues de ver tres intentos
algoritmicos fallar: *«la redundancia no es algo que se pueda inferir con codigo
facilmente; necesitariamos un modelo probabilistico de prediccion de lenguaje,
que es exactamente lo que tenemos contigo — no esta en la capacidad de Python ni
de ninguna de sus dependencias»*.

Esta comprobado. Un trigrama **no ve** que «de cada 100 dolares que el» y «100
dolares que el recibe el» son la misma frase empezada dos veces: no comparten
ninguno. Ni que «pero que el sistema se quedo» y «pero que el sistema capturo»
dicen lo mismo con otro verbo. El ultimo intento dejo la pieza mas larga que
antes, y por eso **partir por repeticion se probo y se retiro**: partia donde no
tocaba. Eso vive en `redundancia.py`, que es un paso de IA.

## Lo que NO hace

No decide qué se dice: eso ya está decidido y no se toca. No quita pausas
retóricas ni junta frases que Jaime separó a propósito. Y **no recorta por
duración**: *«respeta el guion; si hay necesidad de recortar lo definimos al
final»*.

    python scripts/depurar.py 1        # depura el EDL del reel 1
    python scripts/depurar.py --ver 1  # dice qué quitaría y no toca nada
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import basedatos  # noqa: E402
import registro  # noqa: E402
import rutas  # noqa: E402

from dominio import depuracion as _dep  # noqa: E402
from dominio.cinta import Cinta  # noqa: E402
from dominio.continuidad import Continuidad  # noqa: E402
from dominio.cruce import repite_en_el_corte  # noqa: E402
from dominio.montaje import Montaje  # noqa: E402
from dominio.palabra import Palabra  # noqa: E402
from dominio.tramo import Tramo  # noqa: E402

AIRE_MAX = _dep.AIRE_MAX
MARGEN = _dep.MARGEN


# ── los nombres que ya se llamaban desde fuera ──────────────────────────────
#
# La regla vive en `dominio`; aquí queda la firma que usan `seleccionar.limpieza`
# y `revalidar`. Es el mismo acuerdo que `transcribir.suena` con `Palabra`: mover
# el mecanismo no puede obligar a reescribir a quien lo llama.
def _palabras(ws):
    """Las palabras como `Palabra`, vengan como vengan.

    Quien llama desde fuera todavía tiene listas de `{"start", "end", "text"}`
    —es lo que devuelve `transcribir.exigir`— y dentro se trabaja con objetos.
    La traducción es de este borde, no de las dos partes.
    """
    return [w if isinstance(w, Palabra) else Palabra.de_dict(w) for w in ws]


def trozos_con_voz(palabras, a, b):
    """Parte [a,b] en los tramos donde de verdad se dice algo."""
    tramo = _dep.corte(a, b)
    if tramo is None:
        return []
    return [[t.desde, t.hasta]
            for t in _dep.con_voz(_palabras(palabras), tramo)]


def podar_dentro(palabras, a, b):
    """Corta la repetición que ocurre DENTRO de un mismo trozo."""
    tramo = _dep.corte(a, b)
    if tramo is None:
        return a, b
    t = _dep.podar_dentro(_palabras(palabras), tramo)
    return t.desde, t.hasta


def sin_tartamudeo(palabras, a, b):
    """Quita la palabra repetida de seguido: «el el», «y es y es»."""
    tramo = _dep.corte(a, b)
    if tramo is None:
        return [[a, b]]
    return [[t.desde, t.hasta]
            for t in _dep.sin_tartamudeo(_palabras(palabras), tramo)]


def sin_repetir(palabras, trozos, toma=None):
    """Cuando la misma idea vuelve, se queda la que más comunica."""
    tramos = [Tramo.de_lista(t, toma or "") for t in trozos]
    quedan, fuera = _dep.sin_repetir(_palabras(palabras), tramos)
    return [[t.desde, t.hasta] for t in quedan], fuera


def cruza_el_corte(palabras, cola, cabeza):
    """La repetición que ocurre ENTRE dos etapas. Devuelve el nuevo arranque."""
    ws = _palabras(palabras)
    return repite_en_el_corte(Tramo.de_lista(cola), ws,
                              Tramo.de_lista(cabeza), ws)


def continuidad(palabras, trozos):
    """Cuánto de lo que se cortó respeta la frontera que ya había."""
    return Continuidad(_palabras(palabras), trozos).cuenta()


# ── el paso ─────────────────────────────────────────────────────────────────
class _Depurada:
    """El corte de una pieza ya podado: lo que queda y lo que se fue.

    Primero dentro de cada trozo y luego entre trozos: son dos repeticiones
    distintas y la de dentro no la ve la de fuera.
    """

    def __init__(self, m):
        self.segs, self.det, self.cruces = [], [], []
        self.aire = self.quitado = 0.0
        self.rotas, self.brutos, self.partes = [], {}, []
        self._depurar(m)

    def _depurar(self, m):
        segs, det = self.segs, self.det
        for tramo, d in m.tramos():
            pal = m.palabras(tramo.cinta)
            self.brutos[d["beat"]] = (tramo.desde, tramo.hasta)
            trozos = _dep.con_voz(pal, tramo)
            util = sum(t.dura for t in trozos)
            self.aire += tramo.dura - util
            trozos = [_dep.podar_dentro(pal, t) for t in trozos]
            trozos = [x for t in trozos for x in _dep.sin_tartamudeo(pal, t)]
            trozos, tirados = _dep.sin_repetir(pal, trozos)
            self.quitado += util - sum(t.dura for t in trozos)
            if not trozos:
                trozos = [tramo]      # antes dejarlo entero que dejarlo vacío
            # **Y la costura contra la etapa anterior.** Se mira aquí porque es
            # donde están los dos lados a la vez. **Y ya no corta: apunta**
            # (C-88): cortaba hasta la palabra repetida incluida, y en reel-01 e7
            # esa palabra era la unidad de dos cifras distintas — se llevó el
            # precio de la oferta, que es lo único que la pieza vende.
            if segs:
                nuevo = cruza_el_corte(pal, segs[-1], trozos[0])
                if nuevo is not None:
                    self.cruces.append({
                        "etapa": d.get("beat"), "corta_hasta": nuevo,
                        "cola": segs[-1].texto_de(pal)[-70:],
                        "cabeza": Tramo(trozos[0].desde, nuevo,
                                        tramo.cinta).texto_de(pal)})
            segs += trozos
            det += [{**d, "start": t.desde, "end": t.hasta} for t in trozos]
            c = Continuidad(pal, [(t.desde, t.hasta) for t in trozos])
            if c.rota:
                self.rotas.append((d["beat"], c))
            self.partes.append((tramo, d, trozos, tirados, c))


def _anotar_rotas(slug, fragmentadas, brutos):
    """**El descarte se registra, si no el aviso es papel.**

    Sin esto, `depurar` decía «ésta queda picada» y la siguiente corrida volvía a
    elegirla porque nada recordaba el descarte. Se anota hasta DOS veces por
    etapa: si la tercera también queda rota es que la cinta es así ahí, el
    handicap ya está puesto y la que más comunique se queda igual.
    """
    con = basedatos.abrir()
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    for beat, c in fragmentadas:
        print(f"  etapa {beat}: {c} — el mensaje queda roto; compite con"
              f" handicap, no queda fuera")
        ya = con.execute(
            "select count(*) from descartado where video_slug=? and etapa_orden=?",
            (slug, beat)).fetchone()[0]
        if ya >= 2:
            print(f"    (ya se descartaron {ya} para esta etapa: se queda esta,"
                  f" la cinta no da mas)")
            continue
        desde, hasta = brutos.get(beat, (0, 0))
        con.execute(
            "insert or replace into descartado (video_slug, etapa_orden,"
            " desde, hasta, motivo, fecha) values (?,?,?,?,?,?)",
            (slug, beat, desde, hasta, c.motivo, ahora))
        registro.aviso("depurar", "el mensaje queda roto",
                       detalle=f"{slug} etapa {beat}: {c}", eco=False)
    con.commit()
    con.close()


def _una(slug, ver):
    m = Montaje(slug)
    if not m.existe:
        return
    # **Depurar dos veces no depura mejor: depura de mas.** Este paso quita el
    # aire midiendo contra las palabras, y sobre su propia salida vuelve a
    # encontrar «aire» en los margenes que dejo — en reel-01, una segunda pasada
    # se llevo 48,3 s mas de una pieza ya limpia. Se compara el NUMERO de
    # segmentos, no la marca: `seleccionar` escribe un EDL nuevo pero arrastra el
    # bloque `revision`, asi que la marca sola decia «ya depurado» sobre una
    # seleccion recien hecha.
    if (m.edl.get("revision") or {}).get("depurado_n") == len(m.edl["segmentos"]):
        print(f"{slug}: ya depurado — se salta (corre seleccionar antes"
              f" para rehacerlo)")
        return
    # **Una cinta que no se puede sostener para el paso, no lo degrada.** Si se
    # deja pasar, sus tramos salen sin palabras y todo el corte «sobrevive»: el
    # paso informa de que no quitó nada y parece que la pieza estaba limpia.
    for cinta in sorted({t.cinta for t, _ in m.tramos()}):
        Cinta(cinta).exigir()

    r = _Depurada(m)
    if ver:
        for tramo, d, trozos, tirados, c in r.partes:
            roto = f"   <-- FRACTURADA: {c}" if c.rota else ""
            fuera = (f", {len(tirados)} repetido(s) fuera" if tirados else "")
            print(f"  etapa {d['beat']:>2}: {tramo.dura:5.1f}s ->"
                  f" {sum(t.dura for t in trozos):5.1f}s"
                  f"  ({len(trozos)} trozo(s){fuera}){roto}")
    print(f"{slug}: {len(m.edl['segmentos'])} cortes -> {len(r.segs)} · "
          f"{r.aire:.1f}s de aire y {r.quitado:.1f}s de repeticion fuera")
    for c in r.cruces:
        print(f"  costura e{c['etapa']}: se repite cerca del corte —"
              f" «…{c['cola'].strip()}» / «{c['cabeza'].strip()}» —"
              f" NO se corta: lo resuelve quien compone")
    _anotar_rotas(slug, r.rotas, r.brutos)
    if not ver:
        _guardar(m, r)


def _guardar(m, r):
    """Escribe el corte depurado. **`fuentes` se deriva de `detalle`.**

    Al partir un corte en varios trozos el índice deja de significar lo mismo, y
    `fuentes[min(i, n-1)]` acababa diciendo una cinta y `detalle[i].toma` otra
    para el mismo segmento — en reel-01, cinco segmentos apuntaban a una cinta
    que ni siquiera llega a ese segundo. No rompió ningún render porque **nadie
    lee `fuentes`**, y eso es lo peligroso: un campo que existe, miente y parece
    autoridad.
    """
    edl = m.edl
    edl["segmentos"] = [[t.desde, t.hasta] for t in r.segs]
    edl["detalle"] = r.det
    edl["fuentes"] = [d.get("toma") or "" for d in r.det]
    edl["duracion_montada_s"] = round(sum(t.dura for t in r.segs), 2)
    rev = dict(edl.get("revision") or {})
    rev["depurado_n"] = len(r.segs)
    rev["depurado"] = (f"Se quitaron {r.aire:.1f}s sin una sola palabra y "
                       f"{r.quitado:.1f}s de repeticion, midiendo contra las "
                       f"PALABRAS y no contra los tramos de habla. Ver "
                       f"scripts/depurar.py.")
    edl["revision"] = rev
    with open(m.pieza.ruta_edl, "w", encoding="utf-8") as f:
        json.dump(edl, f, ensure_ascii=False, indent=1)
    registro.nota("depurar", "aire y repeticion fuera",
                  detalle=f"{m.slug}: {r.aire:.1f}s + {r.quitado:.1f}s")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true", help="dice que quitaria")
    a = ap.parse_args()
    for n in (a.reels or rutas.piezas()):
        _una(f"reel-{n:02d}", a.ver)


if __name__ == "__main__":
    main()
