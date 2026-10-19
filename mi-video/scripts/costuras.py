"""El cosido: dejar el corte sano y, si la unión aún se oye, disimularla.

Regla de Jaime, con sus dos mitades: *«busca los mejores cortes posibles, y si
no, utiliza la transición del glitch — glitch y cambio de cámara»*. Mover el
corte es gratis porque no se añade nada: se elige. Y si no hay dónde, glitch **y**
cambio de encuadre a la vez — el ojo perdona un salto de voz cuando el plano
también cambió. **Pero el glitch no puede ir en todas**: una máscara que se pone
siempre deja de ser máscara, y entonces el corte limpio y el malo se ven igual de
raros — *«el glitch para cambios de escena o en cortes que quedan mal»*.

**Este fichero es el paso, no el criterio.** Lee el montaje, le pregunta al
dominio y escribe. Medir una costura y decidir qué hacer con ella estaban aquí
mezcladas —veintitrés funciones pasándose `(edl, i, cache)`—, así que no se podía
preguntar por una unión sin arriesgarse a moverla. Ahora cada cosa es de quien es:

    dominio/costura.py     si hay empalme, si se oye, dónde iría mejor la unión
    dominio/borde.py       a dónde debe ir cada extremo de un trozo
    dominio/aritmetica.py  las garantías que no necesitan entender una frase
    dominio/habla.py       las palabras de la cinta y dónde dejan cortar
    dominio/senal.py       la onda de la cinta y su punto más callado
    dominio/tijera.py      lo único que cambia el montaje, y lo deja cuadrado
    python scripts/costuras.py [n]  # el paso completo; --bordes y --palabras
                                    # corren sólo su parte, --ver no escribe
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402
from dominio import bordes as _bordes  # noqa: E402
from dominio.aritmetica import Aritmetica  # noqa: E402
from dominio.borde import BUSCA, COLA  # noqa: E402,F401
from dominio.costura import MARGEN, RITMO_OK, TONO_OK, Costura  # noqa: E402,F401
from dominio.habla import AIRE, ATAQUE, COLGANTES  # noqa: E402,F401
from dominio.senal import ALARGA, GANA, PUERTA, SUENA  # noqa: E402,F401
from dominio.tijera import Tijera  # noqa: E402
from dominio.tramo import Tramo  # noqa: E402


def sin_solapes(slug, ver=False):
    """Dos trozos de la misma cinta no pueden pisarse: es audio repetido."""
    return Aritmetica(slug, ver).sin_solapes()


def sin_eco(slug, ver=False):
    """La cola de un trozo no puede ser el arranque del siguiente."""
    return Aritmetica(slug, ver).sin_eco()


def palabras_enteras(slug, ver=False):
    """Ningún corte de la pieza cae dentro de una palabra."""
    return Aritmetica(slug, ver).palabras_enteras()


def ataques(slug, ver=False):
    """Ningún corte entra pisando la primera palabra."""
    return Aritmetica(slug, ver).ataques()


def mudos(slug, ver=False):
    """Fuera los trozos que no dicen ni una palabra entera."""
    return Aritmetica(slug, ver).mudos()


def colas(slug, ver=False):
    """Ningún trozo entra antes de hablar ni se queda después de callar.

    **La pausa declarada no se toca**, y eso lo sabe la base: se pregunta aquí.
    Con su lado, que es lo que distingue el silencio bueno del aire de al lado.
    """
    try:
        import consulta
        pausas = {int(k): (v or {}).get("donde")
                  for k, v in (consulta.pausas(slug) or {}).items()}
    except Exception:                              # noqa: BLE001
        pausas = {}
    return Aritmetica(slug, ver).colas(pausas)


def bordes(slug, ver=False):
    """Lleva cada entrada y cada salida a la frontera de frase más cercana.

    **No cambia lo que la etapa dice**: mueve el corte al silencio que ya existe,
    dentro de `BUSCA` segundos. El criterio vive en `Borde.a_frontera`.
    """
    sucios = []

    def propone(b, i, tij):
        antes = next((tij.tramo(j).hasta for j in range(i - 1, -1, -1)
                      if tij.tramo(j).cinta == b.t.cinta), None)
        nuevo, dice = b.a_frontera(antes)
        if dice == "sucio":
            sucios.append(i)
        return None if nuevo is None else (nuevo, dice)

    n = Aritmetica(slug, ver).recorre(propone, "borde(s) a frontera de frase")
    if sucios:
        print(f"  {slug}: {len(sucios)} sin frontera cerca")
    return n, len(sucios)


#: El margen que `ajuste.a_la_voz` deja alrededor de la voz, con holgura de
#: redondeo. Dentro de el, un borde ya esta bien puesto (C-566).
MARGEN_VOZ = 0.125


def sin_aire(slug, ver=False):
    """Quita de TODOS los segmentos el silencio que no es una pausa.

    `fijar.declarar` ya recorta lo que se le declara (C-129, C-134), pero por el
    EDL entran segmentos por tres puertas más: piezas con 14 y 18 segundos mudos
    que **cuatro vueltas de revisión no vieron**, porque por texto el trozo
    parece una frase. Un hueco largo parte el segmento; uno corto no.
    """
    import fijar

    tij = Tijera(slug)
    if not tij.existe:
        return 0
    nuevos, quitado, cambia = [], 0.0, False
    for i in range(len(tij)):
        t, d = tij.tramo(i), tij.detalle(i)
        # **Y lo declarado no pasa por aqui.**
        #
        # Este es el unico paso que reescribe la lista entera —`rehacer`— y por
        # ahi se cuela la unica cosa que `Tijera` existe para impedir: `mover` y
        # `quitar` preguntan quien puso el trozo ahi, y `rehacer` no puede
        # porque un trozo puede salir partido en tres. Resultado medido en
        # reel-03: **catorce tramos declarados retrocedieron 0,12 s cada uno** y
        # la pieza engordo 1,72 s de aire de entrada, con `colas` sin poder
        # devolverlos porque a el si le para la marca. Se pregunta aqui, igual
        # que en `Aritmetica.pasada_callada`.
        #
        # Y no se pierde nada: `fijar.declarar` ya pasa cada tramo por
        # `_a_la_voz` al declararlo, asi que un tramo declarado llega recortado.
        if tij.protegido(i):
            nuevos.append((t, d))
            continue
        cinta = t.cinta or rutas.TOMAS.get(slug)
        trozos = fijar._a_la_voz(cinta, t.desde, t.hasta) if cinta else None
        # **Banda muerta del margen** (C-566): `a_la_voz` deja 0,12 s alrededor
        # de la voz, y un borde que ya esta dentro de ese margen saltaba de un
        # lado al otro en cada pasada —reel-22 e2, 139,625 / 139,745—. Sólo se
        # recoloca lo que se sale del margen o se parte en varios trozos.
        if (not trozos or len(trozos) == 1
                and abs(trozos[0][0] - t.desde) <= MARGEN_VOZ
                and abs(trozos[0][1] - t.hasta) <= MARGEN_VOZ):
            nuevos.append((t, d))
            continue
        quitado += t.dura - sum(y - x for x, y in trozos)
        # **Se escribe si el borde cambio, no si sobro silencio.** `quitado`
        # puede ser NEGATIVO y ése es el caso bueno: el ajuste a la frontera de
        # palabra (C-135) **alarga**. Parando en `quitado < 0.05`, las seis
        # piezas daban negativo y el guarda tiraba 54 bordes ya calculados.
        if (len(trozos) != 1 or abs(trozos[0][0] - t.desde) > 0.005
                or abs(trozos[0][1] - t.hasta) > 0.005):
            cambia = True
        nuevos.extend((Tramo.de_lista(x, t.cinta), d) for x in trozos)
    if not cambia:
        return 0
    if ver:
        print(f"  {slug}: {'quitaria' if quitado > 0 else 'anadiria'}"
              f" {abs(quitado):.1f}s recolocando bordes")
        return quitado
    tij.rehacer(nuevos)
    tij.guardar()
    registro.nota("costuras", "aire muerto fuera",
                  detalle=f"{slug}: {quitado:.1f}s")
    return quitado


def cerrar_palabras(slug, ver=False):
    """Alarga el corte de salida hasta que la palabra termina de sonar.

    **Se llamaba `palabras_enteras` y tapaba a la garantia del mismo nombre.**
    Dos funciones con un nombre en un fichero no dan error: la segunda gana y la
    primera deja de existir. Asi que `Aritmetica.palabras_enteras` —«ningun corte
    cae dentro de una palabra»— no corria en el paso **ni en la puerta**:
    `revisada.LosCortes` la pide por este nombre y recibia esta otra, que solo
    mira salidas y necesita un wav que en esta maquina no esta. De ahi la queja
    de Jaime sobre `reel-03` y de ahi que `costuras.py 3 --ver` contestara cero
    con tres entradas sucias delante. Son dos cosas distintas y ahora se llaman
    distinto: **esto cierra la salida por sonido; aquello saca el corte de dentro
    de la palabra por tiempo.**

    **Es la queja que Jaime repitio toda la noche**: *«el corte se come el final
    de las palabras»*, *«los remates estan cortados, no se deja terminar las
    frases, y eso rompe todo el flow»*.

    Y no lo cogia nadie. `a_lo_callado` busca el minimo de una ventana de ±120
    ms y se conforma con el: cuando la silaba dura mas que la ventana, devuelve
    el punto menos malo y da el corte por bueno. Medido sobre las siete piezas:
    **30 de 132 salidas cortaban con la voz entre -7 y -14 dB**, o sea a pleno
    volumen, y el paso decia que estaban limpias.

    Aqui no se busca un minimo: se avanza hasta que deja de sonar, que es la
    regla que el dio — *«no por whisper, por sonido»*. Cuesta 113 ms de media y
    2,4 s en el lote entero.

    Lo que NO hace: recortar. Solo alarga, y como mucho `ALARGA`. Un corte que
    sigue sonando despues de medio segundo no es una palabra sin cerrar, es
    otra cosa — se cuenta y se dice, no se adivina.
    """
    from dominio import senal as _se
    from dominio.senal import Senal
    tij = Tijera(slug)
    if not tij.existe:
        return 0
    # **Y no se alarga sobre el trozo siguiente de la MISMA cinta.**
    #
    # Sin esta cota el paso fabricaba solapes: `sin_solapes` los cerraba
    # dejando el corte en pleno sonido, `a_lo_callado` lo movia, y el cosido no
    # asentaba — cuatro piezas de siete dieron el aviso. Alargar la palabra no
    # puede costar el trozo de al lado.
    topes = {}
    for i in range(len(tij)):
        t = tij.tramo(i)
        sig = [tij.tramo(j).desde for j in range(len(tij))
               if j != i and tij.tramo(j).cinta == t.cinta
               and tij.tramo(j).desde >= t.hasta]
        topes[i] = min(sig) - 0.02 if sig else None
    ondas, cerrados, sonando = {}, 0, 0
    for i in range(len(tij)):
        # **Lo declarado y lo aprobado no se cierran aqui** (C-566): su borde
        # se resolvio al declararlo (`fijar`) o lo vio Jaime. Moverlo era la
        # deriva de reel-22 e4, 179,916 → 180,091 → 180,206.
        if tij.protegido(i):
            continue
        t = tij.tramo(i)
        cinta = t.cinta or rutas.TOMAS.get(slug)
        if cinta and cinta not in ondas:
            try:
                ondas[cinta] = Senal(cinta)
            except Exception:                      # noqa: BLE001
                ondas[cinta] = None
        onda = ondas.get(cinta)
        tope = topes.get(i)
        margen = ALARGA if tope is None else min(ALARGA, max(0.0, tope - t.hasta))
        # **Primero, si el borde cayo en el arranque de la siguiente** (C-558):
        # entonces el hueco esta detras y se vuelve a el; no hay palabra que
        # cerrar. Solo si no, se alarga hasta que calle.
        atras = onda.antes_calla(t.hasta) if onda else None
        if atras is None or atras - t.desde <= 0.25:
            atras = None
        hasta = atras or (onda.donde_calla(t.hasta, maximo=margen)
                          if (onda and margen > 0) else None)
        if hasta is None:
            if onda and onda.suena(t.hasta) > SUENA:
                sonando += 1
            continue
        # Trozo a trozo y por la tijera, que no reescribe la lista entera ni
        # deja tocar lo protegido.
        if ver or tij.mover(i, Tramo(t.desde, hasta, t.cinta)):
            cerrados += 1
    if not cerrados:
        return 0
    if ver:
        print(f"  {slug}: cerraria {cerrados} palabra(s) en los bordes")
        return cerrados
    tij.guardar()
    registro.nota("costuras", "palabras cerradas en los bordes",
                  detalle=f"{slug}: {cerrados} borde(s), {sonando} sin cerrar")
    print(f"  {slug}: {cerrados} palabra(s) cerradas"
          + (f", {sonando} siguen sonando" if sonando else ""))
    return cerrados


def bordes_en_sonido(slug):
    """Las SALIDAS que cortan voz. **Umbral absoluto, no vecindad.**

    La puerta preguntaba «¿hay algo mas callado a 120 ms?», y esa no es la
    pregunta: un borde a -105 dBFS —silencio de sobra— la fallaba igual porque
    veinte milisegundos mas alla habia -123. Reel-07 se quedo sin renderizar
    por eso, con sus tres bordes en silencio.

    Es C-171 otra vez: **optimizar dentro de una ventana no es cumplir un
    umbral**. Aqui se pregunta lo unico que se oye — si al cortar queda voz
    colgando.

    **Solo salidas.** Entrar donde antes habia voz es lo que un montaje es: se
    recoge la frase a mitad de cinta. Lo que suena partido es salir mientras la
    palabra sigue — como Jaime lo nombro: *«el corte se come final de las
    palabras»*. Contando entradas salian 36 de 36 y no media nada.
    """
    import json

    from dominio.senal import SUENA, Senal

    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return []
    edl = json.load(open(ruta, encoding='utf-8'))
    ondas, sucios = {}, []
    for i, ((_a, b), det) in enumerate(zip(edl['segmentos'], edl['detalle'])):
        cinta = det.get('toma')
        # Y si el trozo siguiente sigue ahí mismo, no es una salida (C-545).
        if not cinta or _bordes.sigue_ahi(edl, i):
            continue
        if cinta not in ondas:
            ondas[cinta] = Senal(cinta)
        # **Sin `except` mudo.** Uno se trago un `NameError` aqui y la funcion
        # devolvia «0 bordes sucios» — la respuesta que uno quiere oir, dada
        # por un fallo de programacion. Si medir falla, que se vea.
        if ondas[cinta].suena(b) > SUENA:
            sucios.append((cinta, round(b, 3)))
    return sucios


def _pasada_callado(slug, ver, minimo):
    """Una pasada: cada corte al mínimo de su ventana. `(n, dB)`.

    `GANA` es cuándo merece la pena mover; `PUERTA`, cuándo se oye sucio.
    """
    bar = GANA if minimo is None else minimo
    return Aritmetica(slug, ver).pasada_callada(bar)


#: Tope de pasadas. Con la ventana de 120 ms converge en dos o tres; el tope
#: existe para que un caso raro no cuelgue el montaje, no porque se espere.
VUELTAS_CALLADO = 6


def a_lo_callado(slug, ver=False, minimo=None):
    """Pega los cortes al punto callado **hasta que deja de moverlos**.

    Una pasada no era un punto fijo —21 movidos, luego 10, luego 6— y eso
    importa: **la puerta pregunta por este paso en seco** (`verificar.py`), y un
    paso que no converge es una puerta que no se puede pasar.
    """
    total, medio = 0, []
    for _ in range(1 if ver else VUELTAS_CALLADO):
        n, db = _pasada_callado(slug, ver, minimo)
        if not n:
            break
        total += n
        if db:
            medio.append(db)
    if not total:
        return 0
    db = sum(medio) / len(medio) if medio else 0.0
    if ver:
        print(f"  {slug}: moveria {total} corte(s), {db:.0f} dB mas callados")
        return total
    registro.nota("costuras", "cortes pegados a lo callado",
                  detalle=f"{slug}: {total} corte(s), {db:.0f} dB")
    print(f"  {slug}: {total} corte(s) pegados a lo callado ({db:.0f} dB)")
    return total


def _brolls_posibles(tij, duras):
    """Las costuras que **podrían** llevar B-roll, con su razón. No las asigna.

    Jaime: *«hacer B-rolls con pedazos del video donde yo salgo en silencio… es
    una alternativa al glitch»*, y es mejor: resuelve con material real en vez de
    tapar. **Pero se propone, no se asigna** (C-88) — *«no tantas»*. Cero vale.
    """
    try:
        import consulta as _cs

        # «Un par de segundos», que es lo que Jaime pidió: más deja de ser una
        # transición y se convierte en una pausa.
        libres = _cs.brolls(1.8, 3.0, cintas=sorted(
            {tij.tramo(i).cinta for i in range(len(tij)) if tij.tramo(i).cinta}))
    except Exception:                              # noqa: BLE001
        libres = []
    compone = set()
    try:
        import basedatos

        cx = basedatos.abrir("ads/decisiones.db")
        compone = {r[0] for r in cx.execute(
            "select etapa_orden from escena_desc where video_slug = ?"
            " and componente is not null", (tij.slug,))}
        cx.close()
    except Exception:                              # noqa: BLE001
        pass
    posibles = [(i, tij.beat(i), tij.beat(i + 1),
                 "enfasis" if tij.beat(i) in compone else "separacion")
                for i in duras
                if i + 1 < len(tij) and tij.beat(i) != tij.beat(i + 1)]
    posibles.sort(key=lambda x: 0 if x[3] == "enfasis" else 1)
    return [{"costura": i, "entre": [b_ant, b_sig], "razon": razon,
             "toma": b0["toma"], "desde": b0["desde"], "hasta": b0["hasta"],
             "dura": b0["dura"]}
            for (i, b_ant, b_sig, razon), b0 in zip(posibles[:3], libres)]


def arreglar(slug, ver=False):
    """Mueve lo que se pueda sin perder voz; marca lo que no tuvo arreglo."""
    if not Tijera(slug).existe:
        return
    # **Primero el aire, luego las costuras**: quitar un silencio cambia dónde
    # cae cada empalme. Y después, a lo callado — la voz y la palabra (C-135,
    # C-137) deciden QUÉ entra; eso, DÓNDE se pega la tijera.
    sin_aire(slug, ver=ver)
    # **Los tres se asientan; encadenarlos no basta.**
    #
    # Cada uno crea trabajo para los otros: mover un borde al punto callado
    # puede dejar dos trozos pisandose, y cerrar ese solape deja un corte en
    # pleno sonido. Corriendolos una vez en fila, el ultimo de la fila deja
    # siempre algo detras — y la puerta lo veia: reel-01 salia del cosido con
    # tres cortes sucios que el propio cosido acababa de fabricar al cerrar un
    # solape de 80 ms.
    #
    # Se repite hasta que nadie mueve nada, con tope: si en cuatro vueltas no
    # converge, es que dos reglas se estan deshaciendo la una a la otra y eso hay
    # que verlo, no esconderlo dando vueltas.
    # **Cerrar la palabra va ANTES del bucle, y no dentro.**
    #
    # `a_lo_callado` ancla su ventana al corte que trae el montaje, asi que si
    # las dos corrieran juntas se desharian la una a la otra y el cosido no
    # asentaria — que es justo lo que avisa el `else` de abajo. Corriendo antes,
    # el borde queda a -22/-33 dB y ya no hay 3 dB que ganar: `a_lo_callado` lo
    # deja donde esta y el bucle converge igual.
    cerrar_palabras(slug, ver=ver)
    for _ in range(4):
        movidos = a_lo_callado(slug, ver=ver) or 0
        cerrados = sin_solapes(slug, ver=ver) or 0
        # Y el eco del rearranque, que es de la misma familia que el solape: audio
        # que suena dos veces. La diferencia es que el solape se pisa en el
        # tiempo y el eco se repite en las palabras.
        ecos = sin_eco(slug, ver=ver) or 0
        if not movidos and not cerrados and not ecos:
            break
    else:
        registro.aviso("costuras", "el cosido no se asienta",
                       detalle=f"{slug}: cuatro vueltas y sigue moviendo — dos"
                               f" reglas se estan deshaciendo la una a la otra",
                       eco=True)
    tij = Tijera(slug)                   # el fichero cambió: se relee
    arit = Aritmetica(slug, ver)
    movidas, duras, total = 0, [], 0
    for i in range(len(tij) - 1):
        c = Costura(tij.tramo(i), tij.tramo(i + 1), arit.habla,
                    fijada=tij.fijado(i) or tij.fijado(i + 1))
        if not c.es_empalme:
            continue
        total += 1
        if not c.audible:
            continue
        mejor = c.mejor()
        if mejor is None or mejor.audible:
            duras.append(i)              # una costura declarada llega aquí
            continue
        movidas += 1
        # Sin flechas unicode: la consola sale en cp1252 y un `→` mataba el
        # paso entero con `UnicodeEncodeError` justo al tener algo que contar.
        print(f"  {slug} costura {i}: movida - tono {c.tono} a {mejor.tono}"
              f" - ritmo {c.ritmo} a {mejor.ritmo}")
        if not ver:
            tij.mover(i, mejor.antes)
            tij.mover(i + 1, mejor.despues)
    # **Lo que no tuvo arreglo ni B-roll se marca**, y el spec pone ahí el
    # glitch y el cambio de encuadre, los dos juntos.
    if not ver:
        tij.anotar("brolls_posibles", _brolls_posibles(tij, duras) if duras else [])
        tij.anotar("brolls", None)
        tij.anotar("costuras_duras", duras)
        tij.guardar()
        cuantos = len(tij.m.edl.get("brolls_posibles") or [])
        if cuantos:
            print(f"  {slug}: {cuantos} costura(s) admiten B-roll"
                  f" — lo decide la composicion")
        if duras:
            registro.nota("costuras", "costuras que se disimulan",
                          detalle=f"{slug}: {len(duras)} de {total}")
    print(f"{slug}: {total} empalmes · {movidas} movidas · {len(duras)} a disimular")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--bordes", action="store_true",
                    help="lleva entradas y salidas a la frontera de frase")
    ap.add_argument("--palabras", action="store_true",
                    help="saca los cortes de dentro de una palabra")
    a = ap.parse_args()
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        if a.palabras:
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
            mudos(slug, ver=a.ver)
        elif a.bordes:
            bordes(slug, ver=a.ver)
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
        else:
            # **El paso completo: lo que corre la fase `cosido`.** Las
            # garantías van antes del optimizador; al revés, afina una costura
            # que después se mueve. Y **`bordes` NO va aquí, a propósito**:
            # decide, y eso es criterio.
            sin_solapes(slug, ver=a.ver)
            palabras_enteras(slug, ver=a.ver)
            ataques(slug, ver=a.ver)    # después de cuadrar a palabra entera,
            colas(slug, ver=a.ver)      # que es lo que deja el corte pegado
            mudos(slug, ver=a.ver)
            arreglar(slug, ver=a.ver)


if __name__ == "__main__":
    main()
