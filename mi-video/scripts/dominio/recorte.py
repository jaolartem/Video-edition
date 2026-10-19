"""Lo único que **escribe** cuando la revisión final corta: el EDL y su rastro.

La otra mitad de `dominio/ancla.py`. Allí se mide dónde cae un texto; aquí se
quita, se deja el fichero cuadrado y se apunta en los dos sitios donde el que
monta lo lee. `revision.py` se queda con lo del medio —qué notas entran, cuáles
se pisan y cuáles suben a ticket—, que es lo que decide.

    recorte.recortar(edl, cortes)          # la cirugía: quita los tramos
    recorte.guardar(ruta, edl, hechos, ya) # fuentes, duraciones y `revision`
    recorte.retirar_fijados(slug, edl, …)  # la etapa que se fue deja de estar
    recorte.dar_por_hecha(slug, nota_id)   # una nota retirada, donde se lee

**Ninguna de las cuatro decide nada.** Cuando una de ellas se puso a decidir
—re-aplicar un corte «porque el ancla todavía resuelve»— salieron 125 frases
repetidas en reel-06 y 23 s de más en reel-07; el porqué está escrito entero en
`revision.aplicar`, que es quien tiene que saberlo.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basedatos  # noqa: E402

from .ancla import montado_a_cinta  # noqa: E402


def dar_por_hecha(slug, nota_id):
    """Apunta esa nota de `cortar` en el registro que lee el que ejecuta.

    **El estado no basta, y esto costó estar a un comando de partir el reel-02.**
    `aplicar` no mira `estado` para decidir si un corte está hecho —mira
    `edl["revision"]["notas_aplicadas"]`, porque `seleccionar.py` regenera el EDL
    y una nota `aplicada` tiene que volver a ejecutarse sobre el corte nuevo—.
    Así que cerrar a mano una nota de `cortar` la dejaba cerrada **y viva**: la
    siguiente corrida la aplicaba igual.

    Con dos notas que dicen lo mismo eso es un corte doble. Medido: #676 y #678
    llevan el mismo texto —«no voy a reemplazar»— y las dos resolvían en
    79,1-80,3 s; #672 y su sustituta arrancan las dos en 44,0 s. Cerrar la vieja
    no la retiraba, y el segundo recorte cae sobre el material que acaba de
    ocupar el hueco del primero: es C-92 —cortar por unos segundos que ya no son
    los de nadie— entrando por la puerta de al lado.

    Retirar una nota es, entonces, decirlo **donde el que monta lo lee**.
    """
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return
    edl = json.load(open(ruta, encoding="utf-8"))
    rev = dict(edl.get("revision") or {})
    ya = set(rev.get("notas_aplicadas") or [])
    if nota_id in ya:
        return
    rev["notas_aplicadas"] = sorted(ya | {nota_id})
    edl["revision"] = rev
    # Y sólo si cambia (C-566): con 0 cortes reescribia el EDL igual y movia
    # su fecha, que es lo que hace caducar el re-corte y el render.
    texto = json.dumps(edl, ensure_ascii=False, indent=1)
    try:
        if open(ruta, encoding="utf-8").read() == texto:
            return
    except OSError:
        pass
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


def retirar_fijados(slug, edl, antes):
    """Una etapa que se corta entera **deja de estar declarada**.

    Sin esto los dos mecanismos se pelean y gana el que corre despues. La nota
    dice «esta seccion sobra» y `corte_fijo` sigue diciendo «esta etapa es este
    tramo», asi que `fijar.aplicar` la vuelve a meter en la corrida siguiente —
    y lo hace en silencio, porque desde su punto de vista esta cumpliendo.

    Paso con el reel-01: Jaime pidio sacar el mecanismo entero, la nota lo
    corto, y la pieza volvio a salir con el dentro y ocho segundos mas larga.

    Retirar la declaracion no es perder el registro: la nota de corte queda, con
    su porque y su ancla, y es la que explica por que esa etapa ya no esta.
    """
    vivos = {d.get("beat") for d in edl.get("detalle", [])}
    fuera = [b for b in antes if b is not None and b not in vivos]
    if not fuera:
        return 0
    con = basedatos.abrir(basedatos.BASE)
    con.executemany(
        "delete from corte_fijo where papel='etapa' and orden = ?"
        " and video_id = (select id from video where slug = ?)",
        [(b, slug) for b in fuera])
    con.commit()
    con.close()
    print(f"  {slug}: etapa(s) {sorted(fuera)} fuera de la pieza —"
          f" se retira su declaracion para que no vuelvan")
    return len(fuera)


def al_silencio(edl, cortes):
    """Los bordes de cada corte, llevados al silencio medido antes de cortar (C-603).

    El ancla da los tiempos de palabra del transcript, y whisper los adelanta y
    los estira. reel-20, 19-10: `revisar` quitó «y y» y «de su propio» por esos
    tiempos y los dos cortes quedaron sobre la voz (36,14 y 153,79). Como los
    trozos estaban fijados, el cosido no podía tocarlos y la pieza se quedó
    parada en `cortado`. Es la misma vara del cosido y de la puerta (`Senal`).
    """
    from .senal import SUENA, Senal

    segs, det, fuera = edl.get("segmentos") or [], edl.get("detalle") or [], []
    for d, h, nid, que in cortes:
        try:
            i = next(k for k, s in enumerate(segs) if s[0] - 1e-6 <= d <= s[1] + 1e-6)
            sen = Senal(det[i].get("toma"))
            d = sen.salida_callada(segs[i][0], d)
            if h is not None and sen.suena(h) > SUENA:
                h = sen.donde_calla(h) or h
        except Exception:                          # noqa: BLE001 — se corta como venía
            pass
        fuera.append((d, h, nid, que))
    return fuera


def recortar(edl, cortes):
    """Quita esos tramos del EDL, **de atrás hacia delante**, y dice cuáles.

    El orden no es una preferencia: cada corte mueve los tiempos de todo lo que
    viene después, y hacerlo en orden natural invalida el segundo corte con el
    primero. Quien llama ya trae la lista sin solapes; aquí sólo se ejecuta.

    Devuelve `hechos`: `(id, desde, hasta, que)` por corte aplicado.
    """
    cortes = sorted(cortes, key=lambda x: -x[0])
    hechos = []
    for d, h, nid, que in cortes:
        i0, c0 = montado_a_cinta(edl, d)
        i1, c1 = montado_a_cinta(edl, h if h is not None else d)
        segs, det = [], []
        for i, (rango, dd) in enumerate(zip(edl["segmentos"], edl["detalle"])):
            a, b = rango
            if i < i0 or i > i1:
                segs.append([a, b])
                det.append(dd)
                continue
            # Lo que queda del segmento a cada lado del recorte.
            iz_a, iz_b = a, (c0 if i == i0 else a)
            de_a, de_b = (c1 if i == i1 else b), b
            if i == i0 and iz_b - iz_a > 0.25:
                segs.append([iz_a, iz_b])
                det.append({**dd, "start": iz_a, "end": iz_b})
            if i == i1 and de_b - de_a > 0.25:
                segs.append([de_a, de_b])
                det.append({**dd, "start": de_a, "end": de_b})
        edl["segmentos"], edl["detalle"] = segs, det
        hechos.append((nid, d, h, que))
    return hechos


def guardar(ruta, edl, hechos, ya):
    """Escribe el EDL recortado: derivadas, duraciones y el rastro de la nota.

    `ya` son los ids que el fichero ya cargaba, y salen sumados a los de esta
    corrida — la lista es lo que impide que un corte se ejecute dos veces.
    """
    # Derivada de `detalle`, nunca re-indexada: ver el mismo comentario en
    # `depurar.py`. Un corte parte segmentos, y el indice deja de valer.
    edl["fuentes"] = [d.get("toma") or "" for d in edl["detalle"]]
    # **Las dos duraciones, no una.** El EDL lleva la misma cifra en `duracion_s`
    # y `duracion_montada_s`, y este paso sólo tocaba la segunda: tras cortar, el
    # fichero decía 62,79 y 88,81 a la vez. Es C-192 en el otro fichero que
    # recorta — quien lea la equivocada cree que la pieza dura 26 s más de lo que
    # dura.
    edl["duracion_s"] = round(sum(s[1] - s[0] for s in edl["segmentos"]), 2)
    edl["duracion_montada_s"] = round(
        sum(s[1] - s[0] for s in edl["segmentos"]), 2)
    rev = dict(edl.get("revision") or {})
    rev["revision_final"] = " · ".join(
        f"{d:.0f}-{h:.0f}s: {q[:70]}" for _, d, h, q in hechos)
    rev["notas_aplicadas"] = sorted(ya | {nid for nid, _, _, _ in hechos})
    edl["revision"] = rev
    # Y sólo si cambia (C-566): con 0 cortes reescribia el EDL igual y movia
    # su fecha, que es lo que hace caducar el re-corte y el render.
    texto = json.dumps(edl, ensure_ascii=False, indent=1)
    try:
        if open(ruta, encoding="utf-8").read() == texto:
            return
    except OSError:
        pass
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)
