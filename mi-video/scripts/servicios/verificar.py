"""El servicio de verificación: la puerta, como objeto.

No hace trabajo: comprueba. Y por eso su fallo se lee distinto — una pieza que no
pasa la puerta no está rota, está incompleta, y el motivo dice exactamente qué le
falta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioVerificar(Servicio):
    nombre = "verificado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import verificar

        mal = verificar.revisar(pieza.slug)
        if not mal:
            return Resultado(True, salida="pasa la puerta")
        # **Lo que no para, se anota. Todo, sin excepcion.**
        #
        # Jaime: *«si ven algo raro, levanten tickets»*. La puerta ve cosas que
        # no sabe resolver sola y hasta ahora unas se convertian en ticket y
        # otras solo se imprimian — o sea que se perdian en cuanto la corrida
        # acababa. Un aviso que solo existe en la pantalla es un aviso que no
        # ocurrio.
        #
        # Que pare o no lo decide `verificar.separa`, que es una sola regla y la
        # leen las dos puertas. Lo que no para viene aqui y sale como ticket con
        # su pieza, para que viaje con ella hasta que alguien lo mire.
        # **Y se le pasa la pieza, que es lo que hace que sea la misma regla.**
        #
        # `separa` solo le pregunta a lo que Jaime ya decidio `if not blando and
        # slug`, asi que sin el slug la consulta no ocurre. Esta puerta lo
        # omitia: `verificar.py 3` decia «OK, todo en pie» y la linea paraba la
        # misma pieza por «e6: sin material y sin tablero», que la nota #661
        # contesta desde el 5-9. reel-03 dio dos vueltas asi y el motor la
        # planto — con el detalle correcto en un log que decia lo contrario del
        # que se corre a mano. C-351.
        paran, avisan = verificar.separa(mal, slug=pieza.slug)
        # **Lo que Jaime ya contesto no vuelve como tiquet.** Con C-351 la
        # puerta empezo a ablandar esos motivos —bien— y este bucle los
        # convertia en tiquets igual: el #291 decia literalmente «e6 · sin
        # material y sin tablero — YA DECIDIDO (nota #661)», iba a `disenado` y
        # dejaba la pieza trabada por algo resuelto hace cinco dias. Un aviso
        # que cita la decision que lo contesta no es trabajo pendiente: es la
        # prueba de que no lo hay.
        for m in avisan:
            if verificar.CONTESTADO in m:
                continue
            _anota(pieza, m)
        if not paran:
            return Resultado(True, salida=f"pasa; {len(avisan)} ticket(s)"
                                          f" levantados" if avisan
                             else "pasa la puerta")
        # **Un corte sobre la voz vuelve a quien puso ese borde** (C-555). El
        # motivo decia «corre el paso cosido» y nadie llevaba la pieza alli:
        # reel-18, 20 y 22 se quedaron el 18-10 fallando aqui en cada vuelta.
        # Y el borde de un tramo declarado no lo mueve el cosido: lo decide
        # quien lo declaro, en `revalidado`. A la segunda, error (C-551).
        voz = next((m for m in paran if "cae encima de la voz" in m), None)
        if voz:
            vuelta = _devuelve_el_borde(pieza, voz)
            if vuelta:
                return vuelta
        # **Y la toma que no le enseña los ojos vuelve a quien la eligió** (C-683):
        # otra que mire a cámara, y si no la hay, panel. Ver `dominio/mirada.py`.
        from dominio import mirada as _mirada

        mira = next((m for m in paran if _mirada.REGLA in m), None)
        if mira:
            return _devuelve_la_mirada(pieza, mira, _mirada.REGLA)
        # Se devuelve el primero y se cuentan los demas: el motivo tiene que
        # caber en una linea del log y ser accionable. La lista entera esta en
        # `verificar.py --avisa`.
        resto = f" (+{len(paran) - 1} mas)" if len(paran) > 1 else ""
        return Resultado(False, motivo=paran[0].split(": ", 1)[-1][:140] + resto)


def _anota(pieza, motivo: str) -> None:
    """Levanta el ticket, sin repetirlo si ya esta dicho."""
    from dominio import ticket as tk

    try:
        texto = motivo.split(": ", 1)[-1][:2000]
        # **Ni se reabre lo que cerró una persona** (C-628): reel-21, 20-10,
        # Jaime cerró las nueve «regla de plano» (#673–681) al firmar la pieza y
        # el siguiente montaje las abrió otra vez (#822–830). Lo decidido no
        # vuelve; lo que cerró la línea sí, porque puede haber vuelto a pasar.
        from dominio.autor import Autor

        def _persona(quien):
            return getattr(Autor.de(quien or ""), "tipo", None) == "persona"

        # **Y un aviso ya descartado no se vuelve a levantar** (C-659). En W40,
        # 165 de los 176 tiquets caducados eran avisos de la puerta («regla de
        # plano», «la descripción habla de otro texto») que se abrían en cada
        # montaje y morían en el sellado siguiente. Un `dato` no para nada: se
        # dice una vez. Lo que se ARREGLÓ y vuelve a pasar sí se levanta, porque
        # eso es una regresión.
        if any((t.get("dijo") or "").startswith(texto[:60])
               and (t.get("estado") in ("abierto", "descartado")
                    or _persona(t.get("quien")))
               for t in tk.historia(pieza.slug)):
            return
        # **Un aviso es un `dato`: se ve y no para** (C-559). La puerta ya
        # decidio que no bloquea; como `objecion` iba al disenador, y abierto
        # con su paso detras la pieza se quedaba trabada por lo que la propia
        # puerta dejo pasar —reel-20, 18-10, con «"barata y" dos veces»—. Lo
        # que si bloquea va por `_devuelve_el_borde`, con su paso y su tope.
        try:
            tk.abrir(pieza.slug, texto, None, "dato", vuelve_a="")
        except tk.SinEscena:
            # **Sin escena nombrada, es de la pieza** (C-555): «1 corte(s)…» o
            # «b1: regla de plano» no dicen `eN`, y el aviso se perdia entero.
            tk.abrir(pieza.slug, texto, None, "dato", vuelve_a="", etapa="pieza")
    except Exception:                              # noqa: BLE001
        import registro

        registro.aviso("verificar", "no se pudo levantar el ticket",
                       detalle=f"{pieza.slug}: {motivo[:120]}", eco=False)


#: La marca de los tiquets de este camino; cuenta las devoluciones (C-555).
SOBRE_LA_VOZ = "corte sobre la voz:"


def _devuelve_el_borde(pieza, motivo: str):
    """Tiquet al paso que puso ese borde y la pieza alli, o `None` si ya van dos."""
    import json
    import re

    from dominio import ticket as tk

    from .base import devuelve

    suyos = [t for t in tk.historia(pieza.slug)
             if (t.get("dijo") or "").startswith(SOBRE_LA_VOZ)]
    # Dos devoluciones como mucho, y ninguna con la anterior sin atender: si
    # sigue abierto y el corte sigue mal, volver otra vez es el bucle de C-551.
    if len(suyos) >= 2 or any(t.get("estado") == "abierto" for t in suyos):
        return None
    m = re.search(r"corte de ([\d.]+)s", motivo)
    seg = float(m.group(1)) if m else None
    atiende, beat = "cosido", None
    try:
        edl = json.load(open(os.path.join("ads", pieza.slug, "edl-sell.json"),
                             encoding="utf-8"))
        for (_a, b), d in zip(edl.get("segmentos", []), edl.get("detalle", [])):
            if seg is not None and abs(b - seg) < 0.02:
                beat = d.get("beat")
            if seg is not None and abs(b - seg) < 0.02 and d.get("fijado"):
                # **Salvo que el sonido lo resuelva** (C-558): si hay hueco
                # junto al borde, lo arregla el cosido sin pagar otra lectura.
                from dominio.senal import Senal
                cinta = d.get("toma")
                o = Senal(cinta) if cinta else None
                if o and (o.antes_calla(seg) or o.donde_calla(seg, maximo=0.35)):
                    break
                atiende = f"revalidado — e{d.get('beat')} es un tramo declarado"
                break
    except (OSError, ValueError):
        pass
    paso, _, por_que = atiende.partition(" — ")
    texto = motivo.split(": ", 1)[-1] + (f" ({por_que})" if por_que else "")
    # Y se cierra midiendo el borde: `cierre.cierra_cortes_limpios` (C-560).
    return devuelve(pieza, SOBRE_LA_VOZ, texto, atiende=paso, etapa=beat,
                    cierra_con="bordes")


def _devuelve_la_mirada(pieza, motivo: str, regla: str):
    """Primero a `revalidado`, otra toma; si ya se buscó, a `descrito`, panel.

    reel-23, 15-11-2026, e5: el compositor de `revalidar` contestó «ninguna
    candidata mira a cámara, va panel», pero el panel es plano y componente, que
    los decide `descrito`, así que nada cambió y la puerta la devolvió otra vez
    al mismo sitio (#1074, #1075). Y a la tercera, para: si tampoco el panel
    quita el reparo, es otra cosa y se cuenta (C-688).
    """
    from dominio import ticket as tk
    from dominio.abierto import etapa_de

    from .base import devuelve

    etapa = etapa_de(motivo)
    antes = [t for t in tk.historia(pieza.slug)
             if (t.get("dijo") or "").startswith(regla)
             and etapa_de(t.get("dijo")) == etapa and t.get("estado") != "abierto"]
    texto = motivo.split(": ", 1)[-1]
    fue = {t.get("vuelve_a") or "" for t in antes}
    if "descrito" in fue:
        return Resultado(False, motivo=f"{texto[:120]} — ya se buscó otra toma y"
                                       " se pidió panel, y sigue")
    if "revalidado" in fue:
        return devuelve(pieza, regla, texto + " — ya se buscó otra toma en"
                        " revalidado y no la hay: va panel, plano `fuera` o"
                        " tablero encima", atiende="descrito", etapa=etapa)
    return devuelve(pieza, regla, texto, atiende="revalidado", etapa=etapa,
                    cierra_con="tramos")
