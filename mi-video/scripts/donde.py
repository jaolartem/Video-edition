"""Dónde está cada pieza. Lo primero que se corre en una sesión nueva.

Regla de Jaime, dicha como comprobación: *«si ya estamos, nunca se va a perder el
estado de un vídeo así limpie completamente el contexto»*.

Eso sólo es cierto si el estado **se puede reconstruir sin preguntarle a nadie**.
Y hasta ahora no del todo: había estado por fragmento (`fase`/`paso`) y ninguna
vista que dijera en qué punto está cada vídeo. Una sesión nueva tenía que
deducirlo mirando ficheros y fechas — que es exactamente como se pierde.

Esto lo lee todo de la base y del disco, y no de la memoria de nadie:

    version      qué corte es el vigente y si cambió desde el último registrado
    aprobación   si está aprobado, por quién y cuándo
    audio        si salió el virgen, si volvió el limpio, si está integrado
    publicación  si se subió y dónde
    pendiente    cortes suyos sin aplicar y pedidos de IA sin contestar
    puerta       si pasaría la verificación ahora mismo

Si esto se ejecuta y contesta, el contexto es prescindible. Ése es el criterio.

    python scripts/donde.py
"""
import argparse
import json
import os
import sqlite3
import basedatos
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import modelo  # noqa: E402
import servicio  # noqa: E402
import rutas  # noqa: E402
from dominio import segmento as _segmento  # noqa: E402
from dominio.pieza import Pieza as _Pieza  # noqa: E402
from dominio.oficio import DE as _DE  # noqa: E402

BASE = "ads/decisiones.db"


def _commit():
    """El código que corre: el del despliegue en la línea, el de git fuera."""
    from dominio import despliegue

    return despliegue.actual() or "?"


def estado(slug):
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row
    v = con.execute("select id from video where slug = ?", (slug,)).fetchone()
    if not v:
        con.close()
        return None
    ult = con.execute(
        "select * from version where video_id = ? order by n desc limit 1",
        (v["id"],)).fetchone()
    ap = con.execute(
        "select * from aprobacion where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    au = con.execute(
        "select * from audio_version where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    pu = con.execute(
        "select * from publicacion where version_id = ?",
        (ult["id"],)).fetchone() if ult else None
    pend = con.execute(
        "select count(*) from revision where video_slug = ? and accion='cortar'"
        " and estado='pendiente'", (slug,)).fetchone()[0]
    con.close()
    # **La huella dice si el corte se movió desde la versión registrada.** Es la
    # diferencia entre «hay una versión» y «la versión es ésta»: sin esto, una
    # sesión nueva creería que lo registrado corresponde al EDL de ahora.
    h = modelo.huella_edl(slug)
    return {
        "version": ult["n"] if ult else None,
        "huella_reg": ult["huella"] if ult else None,
        "huella_hoy": h,
        "al_dia": bool(ult and ult["huella"] == h),
        "duracion": ult["duracion_s"] if ult else None,
        # **Una sola respuesta a «¿esta aprobada?»: la de las guardas.** Esto
        # leia `aprobacion` por version y decia «—» de reel-04 y reel-07 mientras
        # `segmento.aprobada` —lo que protege la pieza— decia que si.
        "aprobada": ("aprobada" if _segmento.aprobada(slug)
                     else ap["veredicto"] if ap and ap["veredicto"] != "aprobada"
                     else None),
        "audio_virgen": bool(au and au["virgen"]),
        "audio_limpio": bool(au and au["limpio"]),
        # **Y se compara, no se pregunta por la verdad del valor.** La columna
        # tiene afinidad TEXT, asi que un `0` vuelve como `"0"` y `bool("0")` es
        # cierto: esta fila decia «integrado» aunque el paso que la escribe
        # hubiera medido que no. O sea que arreglar quien mide no bastaba —
        # quien lee no podia ver la diferencia.
        "audio_integrado": bool(au) and str(au["integrado"] or "0") == "1",
        "publicada": pu["destino"] if pu else None,
        "cortes_pendientes": pend,
        "pedidos_ia": [p for p, sl, _ in servicio.pendientes() if sl == slug],
        # **En que fase esta, que es la pregunta del titulo.** La tabla decia
        # version, corte, duracion y audio — todo menos donde esta la pieza, que
        # es lo unico que no se puede deducir mirando ficheros. Sale de `Pieza`,
        # que ya es su duena; preguntarlo aqui con otro SQL seria la segunda
        # copia de la regla.
        "fase": (_Pieza(int(slug[-2:])).fase or {}).get("nombre"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    print(f"commit {_commit()}\n")
    print(f"{'pieza':<9} {'fase':<15} {'ver':>3} {'corte':>7} {'dur':>7}  "
          f"{'aprobada':<9} {'audio':<22} {'espera / pendiente'}")
    for n in rutas.piezas():
        slug = f"reel-{n:02d}"
        e = estado(slug)
        if not e:
            continue
        corte = "al dia" if e["al_dia"] else "CAMBIO"
        # **«Sin integrar» se dice con las palabras que tiene.** Hay una
        # devolucion de Adobe y no entro en la mezcla: eso no es un paso
        # pendiente, es que lo entregado suena crudo. Con la etiqueta blanda la
        # fila se leia como «ya llegara» — y asi salieron cinco de siete.
        audio = ("integrado" if e["audio_integrado"]
                 else "CRUDA: stem no cuadra" if e["audio_limpio"]
                 else "virgen entregado" if e["audio_virgen"]
                 else "—")
        pend = []
        if e["cortes_pendientes"]:
            pend.append(f"{e['cortes_pendientes']} corte(s)")
        # **Y se dice a quien espera, no que «hay un pedido».** «IA: visto» no
        # dice que hacer; «espera a disenador (visto)» si. Es la diferencia
        # entre un informe y una instruccion, y era lo que obligaba a ir a
        # buscarlo a mano cada vez.
        for paso in e["pedidos_ia"]:
            quien = _DE.get(paso)
            pend.append(f"espera a {quien} ({paso})" if quien
                        else f"espera {paso} — sin oficio declarado")
        dur = f"{e['duracion']:.0f}s" if e["duracion"] else "—"
        print(f"{slug:<9} {(e['fase'] or '—'):<15}"
              f" {str(e['version'] or '-'):>3} {corte:>7} {dur:>7}"
              f"  {(e['aprobada'] or '-'):<9} {audio:<22}"
              f" {'; '.join(pend) or '-'}")
    # **Y el material que todavia no es pieza.** Esto es lo que hacia que la
    # septima grabacion fuera invisible: la tabla recorre piezas, asi que una
    # cinta sin pieza no salia ni como pendiente ni como nada. No es que
    # estuviera mal contada — es que **no se podia echar de menos**, que es la
    # unica averia que este comando existe para no tener.
    #
    # Se dice en que punto esta, porque lo que le falta a cada una es distinto:
    # una sin copiar se pide, una sin transcribir se transcribe, y una
    # transcrita y sin libreto **espera a Jaime**, no a la maquina.
    huerfanas = []
    for t in rutas.material():
        if t in set(rutas.TOMAS.values()):
            continue
        hay_mp4 = bool(rutas.angulos(t))
        hay_tr = os.path.exists(f"{rutas.TRABAJO}/transcripts/{t}.json")
        falta = ("sin copiar de origen" if not hay_mp4
                 else "sin transcribir — corre transcribir.py" if not hay_tr
                 else "transcrita y sin libreto: la construye Jaime")
        huerfanas.append((t, falta))
    if huerfanas:
        print()
        print(f"Y {len(huerfanas)} grabacion(es) que todavia no son pieza:")
        for t, falta in huerfanas:
            print(f"    · {t}: {falta}")

    print("\nY lo que dice la puerta ahora mismo:")
    # **Y lo que este fichero imprime va DELANTE de lo que imprime un hijo.**
    #
    # Los `print` de aqui se guardan en el buffer y el subproceso escribe
    # directo al descriptor, asi que el informe salia al reves: las 47
    # lineas de deuda del esquema primero y la tabla de las piezas en la
    # linea 48 de 61. El comando que contesta «¿donde esta cada pieza?»
    # enterraba su respuesta debajo de la salud del codigo, que es otra
    # pregunta.
    sys.stdout.flush()
    subprocess.run([sys.executable, "scripts/verificar.py", "--avisa"])
    # **Y si el sistema esta conectado, que es lo primero que hay que saber.**
    #
    # Jaime, despues de una noche de correcciones suyas que no llegaban: *«tu
    # objetivo no es editar videos, es vigilar que el sistema funcione y este
    # todo conectado; aca no esta conectado»*.
    #
    # Va aqui y no en `montar.sh` a proposito: un cable suelto no tiene por que
    # parar una entrega —Jaime quiere ver la pieza—, pero **no puede pasar
    # inadvertido al empezar**. Un productor sin consumidor no da error nunca;
    # sale cuando el mira la entrega y echa en falta lo que pidio.
    print()
    # **Y la salud del sistema se dice en una linea, con donde mirarla.**
    # Las 47 de `conectado.py` son trabajo pendiente del codigo, no de la
    # pieza; leerlas cada vez que se pregunta por las piezas es lo que
    # hace que se dejen de leer las dos cosas.
    sys.stdout.flush()
    _r = subprocess.run([sys.executable, "scripts/conectado.py"],
                        capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    _dicho = [x for x in (_r.stdout or "").strip().splitlines() if x.strip()]
    print(_dicho[-1] if _dicho else "conectado: sin respuesta")
    print("  python scripts/conectado.py   para verlos uno a uno")


if __name__ == "__main__":
    main()
