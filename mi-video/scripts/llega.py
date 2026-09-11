"""Lo que se declara, ¿llega al render? La comprobación que faltaba.

Jaime, después de un día entero: *«las correcciones no estaban llegando a la
renderización»*, *«eso es un problema que me obliga a retrabajar, a hacer dobles
y triples procesos»*.

## La familia entera, encontrada en un día

Diez decisiones distintas, todas con la misma forma — declarada, guardada, y
descartada aguas abajo por algo que ni siquiera sabía que existía:

    la placa que elige el diseñador   `placaDe()` la pisaba despues de sus props
    `componente`                      declarado en el contrato, `aplicar()` no lo escribia
    `ventana`                         los cinco componentes no la reenviaban a `Fondo`
    `recorte`                         escrito a fuego dentro de cada componente
    el rotulo del gancho              se leia de un literal de `reels-spec.mjs`
    `corrige_es`                      `frames.json` le ganaba en silencio
    donde esta la cara                se predecia con una constante, no se medía
    el tiempo de lectura              contaba props que no se dibujan
    el render                         el acelerado lo sobreescribia en su sitio
    la voz limpia                     la guarda miraba duracion, no contenido

Ninguna dio error. Cada una salió cuando Jaime miró la entrega y echó en falta lo
que había pedido — y entonces el ciclo entero se repetía.

## Qué hace esto

Coge cada decisión que alguien puede declarar, mira **dónde se guarda** y **si
aparece en `src/reels.json`**, que es lo único que el render dibuja. Si está
declarada y no llega, lo dice con su nombre y su etapa **antes** de renderizar.

No sustituye a las guardas: las guardas comprueban que el código siga ahí. Esto
comprueba lo otro, que es lo que fallaba — que el dato **viaje**.

    python scripts/llega.py           # las siete
    python scripts/llega.py 2 6       # sólo esas
"""
import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import basedatos  # noqa: E402

BASE = "ads/decisiones.db"
SPEC = "src/reels.json"


def _spec():
    with open(SPEC, encoding="utf-8") as f:
        return {p["id"]: p for p in json.load(f)}


def _tablero(fila):
    if not fila or not fila["tablero"]:
        return None
    try:
        return json.loads(fila["tablero"])
    except (TypeError, ValueError):
        return None


def _camara(fila):
    """Lo que el diseñador pidió de cámara en esa etapa, ya como objeto."""
    if not fila or not fila["camara"]:
        return {}
    try:
        d = json.loads(fila["camara"])
        return d if isinstance(d, dict) else {}
    except (TypeError, ValueError):
        return {}


def _enSegundos(anclas):
    """El ancla si va en segundos; `None` si va en texto o no hay.

    Las dos formas existen y son distintas: un número se queda clavado donde el
    corte de ayer lo dejó —eso es lo que la guarda 3b audita— y un texto se
    resuelve contra el subtítulo de hoy, así que no puede caducar. Distinguirlas
    aquí evita además el `float("septiembre")` que tumbaba la auditoría entera.
    """
    s = anclas[0] if isinstance(anclas, list) and anclas else anclas
    if isinstance(s, dict):
        s = s.get("segundo", s.get("en"))
    if isinstance(s, bool) or s is None:
        return None
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return None


def _pisa(capa, ventana):
    """¿Cae esa capa dentro de la ventana del beat? Sin ventana, vale igual."""
    if not ventana:
        return True
    return (capa["at"] < ventana[1]
            and capa["at"] + capa["duration"] > ventana[0])


def revisar(piezas=None):
    """Lo declarado que no llega, pieza por pieza. Lista vacía = todo viaja."""
    spec = _spec()
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row
    faltas = []
    import rutas
    for n in piezas or rutas.piezas():
        slug = f"reel-{n:02d}"
        p = spec.get(f"Reel-R{n}")
        if not p:
            faltas.append(f"{slug}: no esta en el spec")
            continue
        puestos = {b.get("beat"): b for b in (p.get("boards") or [])}
        filas = con.execute(
            "select etapa_orden, tablero, componente, corrige_dice, corrige_es,"
            " camara from escena_desc where video_slug = ? order by etapa_orden",
            (slug,)).fetchall()
        for f in filas:
            b = f["etapa_orden"]
            d = _tablero(f)
            # 0 · **El tratamiento de la imagen tambien viaja, o se dice.**
            #
            # El virado y la costura animada se declaran en la MISMA columna que
            # el encuadre —`escena_desc.camara`— y recorren el camino mas largo
            # del proyecto: la base, `plan-reel.mjs`, el plan, `punch-ins.py`
            # —que lo reescribe entero— y el spec. Cinco manos, y cualquiera de
            # ellas puede tirar una clave que no conoce sin decir nada.
            #
            # Es exactamente la familia de las diez averias de arriba, asi que
            # se comprueba igual: declarado y no llega, con su nombre y su etapa.
            cam = _camara(f)
            vent = (p.get("ventanas") or [])
            win = vent[b - 1] if 0 <= b - 1 < len(vent) else None
            vir = cam.get("virado")
            if vir and not any(v.get("virado") == vir and _pisa(v, win)
                               for v in p.get("virados") or []):
                faltas.append(f"{slug} e{b}: declara el virado «{vir}» y el"
                              f" plano llega sin virar")
            if cam.get("transicion") == "filete" and not any(
                    _pisa(x, win) for x in p.get("filetes") or []):
                faltas.append(f"{slug} e{b}: pide la transicion animada"
                              f" «filete» y la costura llega sin ella")
            # 1 · Un tablero declarado tiene que llegar — **a donde le toque
            #     segun `cubre`**, que es quien decide si ocupa el cuadro, si
            #     acompana en el lado libre o si lo lleva el subtitulo.
            #
            #     Mirar solo `boards` daba 33 faltas de las que la mayoria eran
            #     falsas: un `cubre: panel` va a `paneles` y esta bien. Una
            #     comprobacion que grita donde no hay problema se deja de mirar,
            #     y entonces no comprueba nada.
            cubre = (d.get("props") or {}).get("cubre", "pleno") if d else None
            if d and d.get("kind"):
                if cubre == "pleno" and b not in puestos:
                    faltas.append(f"{slug} e{b}: declara el tablero"
                                  f" «{d['kind']}» a cuadro completo y NO esta"
                                  f" en el spec")
                    continue
                if cubre in ("panel", "banda") and not (p.get("paneles") or []):
                    faltas.append(f"{slug} e{b}: declara «{d['kind']}» como"
                                  f" {cubre} y la pieza no tiene ninguno")
                    continue
                if cubre not in ("pleno", "panel", "banda", "cc"):
                    faltas.append(f"{slug} e{b}: declara cubre={cubre!r}, que no"
                                  f" es ninguno de los cuatro")
                    continue
            # 2 · Y con los props que se declararon, no con otros.
            if d and b in puestos:
                suyos = d.get("props") or {}
                llegan = puestos[b].get("props") or {}
                for k in ("placa", "recorte", "ventana", "cubre", "familia"):
                    if k in suyos and suyos[k] != llegan.get(k):
                        faltas.append(
                            f"{slug} e{b}: declara {k}={suyos[k]!r} y llega"
                            f" {llegan.get(k)!r}")
            # 3 · Una correccion declarada tiene que colocarse en un subtitulo.
            if f["corrige_dice"] and f["corrige_es"]:
                # **Se compara flojo a proposito.** La correccion puede salir
                # con otra redaccion que la declarada —`frames.json` gana sobre
                # `escena_desc` y escribe «FINANZAS» donde la base dice «Ministro
                # de Finanzas»— y eso no es que no llegue: es que llega con el
                # texto del otro. Comparar exacto daba un falso positivo, y una
                # comprobacion que grita en falso se deja de mirar.
                def _casa(c):
                    x = (c.get("corrige") or {})
                    if not x:
                        return False
                    a_ = str(x.get("es", "")).lower()
                    b_ = str(f["corrige_es"]).lower()
                    return (a_ in b_ or b_ in a_
                            or str(x.get("dice", "")).lower()
                            == str(f["corrige_dice"]).lower())
                puesta = any(_casa(c) for c in p.get("captions") or [])
                if not puesta:
                    faltas.append(
                        f"{slug} e{b}: declara la correccion"
                        f" «{f['corrige_dice']}» -> «{f['corrige_es']}»"
                        f" y NO sale en ningun subtitulo")
            # 3b · **Un tablero anclado por segundo no se re-deriva.**
            #
            # Jaime, sobre el repaso tras los cortes: *«si se revisa todo, pero
            # no para construir, para ajustar que todo siga cuadrando»*, *«lo
            # mismo con el diseñador, revisa que nada este roto»*.
            #
            # Casi todo se re-deriva del EDL: el plan, los encuadres, el corte,
            # los subtitulos, el spec. `anclas` no: es un segundo escrito por el
            # disenador contra el montaje que habia. Si el corte se acorta, el
            # tablero se queda clavado donde estaba y se separa de la palabra que
            # ilustra — o se sale de su propia etapa.
            #
            # **Y sólo se audita la que va en SEGUNDOS.** Un ancla en TEXTO
            # —`anclas: "septiembre"`— la resuelve `reels/tableros.mjs` contra el
            # subtítulo de hoy, así que no puede quedarse clavada: es la cura de
            # este defecto, no un caso suyo. Comprobarla aquí era además
            # `float("septiembre")`, o sea **reventar la auditoría entera** el día
            # que alguien la usara — y con ella las cinco guardas de abajo.
            anc = _enSegundos((d.get("props") or {}).get("anclas") if d else None)
            if anc is not None:
                puesto = puestos.get(b) or next(
                    (x for x in (p.get("paneles") or [])
                     if abs(x["at"] / 30 - anc) < 3), None)
                if puesto is not None:
                    real = puesto["at"] / 30
                    if abs(real - anc) > 2.0:
                        faltas.append(
                            f"{slug} e{b}: anclado a {anc}s y sale en"
                            f" {real:.1f}s — el corte se movio y el ancla no")
        # 4 · La cara: si se midio, tiene que viajar.
        medida = os.path.join("work", "scenes", slug, "cara.json")
        if os.path.exists(medida) and not (p.get("cara") or {}).get("coronilla"):
            faltas.append(f"{slug}: la cara esta medida y no llega al spec")
        # 5 · El render, ¿es el render? Un acelerado en su sitio lo delata.
        mp4 = os.path.join("out", "reels", f"reel-R{n}.mp4")
        if os.path.exists(mp4):
            import subprocess
            try:
                d_ = float(subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", mp4], capture_output=True,
                    text=True).stdout.strip())
                if abs(d_ - p["duracion"]) > 1.5:
                    faltas.append(
                        f"{slug}: el render dura {d_:.2f}s y el spec dice"
                        f" {p['duracion']:.2f}s — no es lo que se compuso")
            except (ValueError, OSError):
                pass
    con.close()
    return faltas


def main():
    piezas = [int(x) for x in sys.argv[1:] if x.isdigit()] or None
    faltas = revisar(piezas)
    for f in faltas:
        print(f"  · {f}")
    print(f"\nllega: {len(faltas)} declaracion(es) que no llegan al render"
          if faltas else "\nllega: todo lo declarado viaja al render.")
    return 1 if faltas else 0


if __name__ == "__main__":
    raise SystemExit(main())
