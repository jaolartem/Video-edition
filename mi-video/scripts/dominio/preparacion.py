"""Cómo se deja una cinta usable, de principio a fin.

**Por qué tiene nombre propio.** Esto vivía dentro del `main()` de
`transcribir.py`: la receta —¿está ya hecha?, ¿está entera?, ¿hay que taparle
huecos?, ¿hay que rehacerla?— escrita entre el código que lee argumentos de la
línea de comandos. Ahí dentro no se puede llamar desde ningún otro sitio y no se
puede leer sin leer el CLI.

Es la contraparte de `Cinta.exigir()`: aquella dice **si la cinta sirve**, y ésta
dice **qué hacer cuando no**.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import registro  # noqa: E402
import rutas  # noqa: E402

#: Con cuántas pasadas se rehace una cinta que no llegó al sello (C-541): el
#: paso baja a 5 s y lo del arranque cae en varias ventanas.
PASADAS_CORTA = 6


def preparar(toma, rehacer=False, pasadas=None, barato=False):
    """Deja la cinta lista, o dice por qué no puede. Una cinta, una llamada."""
    import json

    from transcribir import (Incompleta, _huecos, _saneado, _sin_cubrir,
                             afinar, exigir, guardar)
    from transcribir import transcribir as _hacer
    from transcribir import MODELOS, VENTANA

    # **Lo ya transcrito no se repite.** Cada toma cuesta media hora larga de
    # CPU, asi que rehacer una que ya esta sellada y al dia es tirar el rato.
    # `exigir()` es quien sabe si vale: sello puesto y no mas vieja que los
    # tramos. Con --rehacer se fuerza.
    if not rehacer:
        try:
            transcribir_ya = exigir(toma, cobertura=False)
            # **Sellada no es lo mismo que entera.** El sello dice cuantas
            # pasadas se hicieron, no si la cinta tiene agujeros; y una
            # cinta con agujeros deja sin texto a las etapas que caen ahi
            # —ocho de los once trozos del reel 1— mientras el paso repite
            # «ya esta». Se mira tambien la cobertura contra los tramos de
            # habla medidos, que es lo que dice cuanto deberia haber.
            transcribir_ya, quitadas = _saneado(toma, transcribir_ya)
            if quitadas:
                print(f"── {toma} ── saneado: {quitadas} palabra(s)"
                      f" fantasma o de etiqueta fuera")
            falta = _sin_cubrir(toma, transcribir_ya)
            if falta > 20.0:
                # **Se tapa el agujero donde esta.** Los tramos huerfanos
                # se vuelven a oir con el modelo bueno y una ventana mas
                # ancha; rehacer la cinta entera es caro y repite el mismo
                # barrido que ya los dejo vacios.
                hue = _huecos(toma, transcribir_ya)
                print(f"── {toma} ── sellada pero con {falta:.0f}s de habla"
                      f" sin texto en {len(hue)} tramos: se afinan")
                j = []
                for d0, h0 in sorted(hue):
                    if j and d0 - j[-1][1] < 2.0:
                        j[-1] = (j[-1][0], h0)
                    else:
                        j.append((d0, h0))
                transcribir_ya, n = afinar(toma, j)
                falta = _sin_cubrir(toma, transcribir_ya)
                print(f"   {n}/{len(j)} afinados → quedan {falta:.0f}s"
                      f" sin texto")
                # **Y si sigue faltando, para y avisa.** Regla de Jaime:
                # *«si algo no funciona a la primera, paras y que genere
                # error»*. Un tramo que no suelta texto tras afinarlo o no
                # es habla o no se entiende, y las dos cosas las decide
                # quien monta — no un umbral.
                if falta > 20.0:
                    for d0, h0 in _huecos(toma, transcribir_ya)[:10]:
                        print(f"   sin texto: {d0:.1f}-{h0:.1f}s")
                    raise Incompleta(
                        f"{toma}: {falta:.0f}s de habla sin texto tras"
                        f" afinar. Oye esos tramos y decide: o se rehace"
                        f" la cinta (--rehacer) o no son habla.")
            print(f"── {toma} ── ya esta ({transcribir_ya['pasadas']} pasadas"
                  f" por tramo, {len(transcribir_ya['segmentos'])} palabras)")
            return "ya estaba"
        except SystemExit:
            pass
    # **Una cinta sin preparar no se lleva por delante a las demas.**
    #
    # Esto abria los tramos sin comprobar que existieran, y una cinta nueva
    # —recien copiada, sin `cut-silence` corrido— reventaba el bucle entero
    # con un `FileNotFoundError` sin capturar. El corpus se recorre por orden
    # alfabetico, asi que la del 14 de agosto iba PRIMERA: se murio en
    # segundos y las otras siete ni se miraron.
    #
    # Y lo peor no es que fallara: es que fallo **en silencio para quien
    # miraba desde fuera**. La corrida salio, no dejo nada en `incidencia`, y
    # durante una hora el estado creido fue «transcribiendo».
    #
    # Ahora se dice que falta y se sigue con las demas: una cinta sin
    # preparar es un trabajo pendiente, no una corrida rota.
    # **Lo que hace el trabajo se importa aqui.** Faltaba, y esta funcion moria
    # con `NameError: name 'transcribir' is not defined` — o sea que rehacer una
    # cinta era imposible por la via canonica. Lo cazo Jaime pidiendo justo eso:
    # *«re transcribe ese tramo y aplica el corte»*. Va dentro y no arriba porque
    # `transcribir` importa de aqui: al reves seria un ciclo.
    from transcribir import MODELOS, VENTANA  # noqa: F811
    from transcribir import transcribir as _hacer

    cuts = f"work/cuts/{toma}.json"
    if not os.path.exists(cuts):
        registro.aviso("transcribir", "cinta sin tramos de voz: se salta",
                       toma=toma,
                       detalle=f"falta {cuts} — corre antes cut-silence.py"
                               f" sobre su audio")
        return "sin tramos de voz"
    runs = json.load(open(cuts, encoding="utf-8"))["segmentos"]
    print(f"── {toma} ──")
    modelo = MODELOS["barato" if barato else "bueno"]
    # **Un solo camino.** Jaime, tras ver que los dos fallos de la sesion
    # salian del afinado y no del barrido: *«prefiero que los hagas desde el
    # principio con el proceso nuevo y compares al final»*, y *«no podemos
    # estar todo el tiempo revisando a que algo quede»*. Mas pasadas de una
    # vez cuesta 1,6x y **quita el merge entero**, que es donde vivia la
    # fragilidad.
    paso = (VENTANA if barato
            else (VENTANA / pasadas if pasadas else None))
    palabras, mapa, dudosos = _hacer(toma, runs, modelo=modelo, paso=paso)
    ruta = guardar(toma, palabras, mapa, dudosos, modelo, paso)
    con_texto = [m for m in mapa if m.get("texto")]
    largas = sum(w["larga"] for w in palabras)
    # Solo promedian los que TIENEN acuerdo: un tramo que cayo en una sola
    # ventana no tiene con que compararse, y meterlo como 0 o como 1 son las
    # dos formas de mentir. Es el tercer sitio donde hacer representable el
    # «desconocido» rompio algo que asumia un numero — los otros dos fueron
    # el formateo y el NOT NULL de la tabla.
    medidos = [m["acuerdo"] for m in con_texto if m.get("acuerdo") is not None]
    acuerdo = (sum(medidos) / len(medidos)) if medidos else 0.0
    registro.nota("transcribir", "toma transcrita", toma=toma,
                  detalle=f"{len(palabras)} palabras, {len(con_texto)}/{len(runs)}"
                          f" tramos, acuerdo {acuerdo:.2f}, {largas} estiradas")
    print(f"  {len(palabras)} palabras · {len(con_texto)}/{len(runs)} tramos"
          f" · acuerdo medio {acuerdo:.2f} ({len(medidos)} medidos)"
          f" · {dudosos} tramos por oír · {largas} palabras estiradas"
          f" → {ruta}")
    # **Una cinta corta no llega al sello con el paso de siempre** (C-541). Lo
    # de los primeros `PASO` segundos cae en una sola ventana, y en una cinta de
    # 50 s eso pesa: `20261015_140249` salió con 1,67 pasadas de media,
    # `Cinta.exigir` la declaró «de UNA pasada» y la selección la dejó fuera.
    # Más pasadas es la receta que ya existía (`--pasadas`); aquí se aplica sola.
    if not barato and not pasadas:
        from dominio.cinta import PASADAS_MIN, Cinta
        sello = Cinta(toma).pasadas()
        if sello < PASADAS_MIN:
            print(f"   sello {sello:.2f} < {PASADAS_MIN}: cinta corta, se rehace"
                  f" con {PASADAS_CORTA} pasadas")
            return preparar(toma, rehacer=True, pasadas=PASADAS_CORTA)
