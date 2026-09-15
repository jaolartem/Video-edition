"""Ajustar un tramo declarado a lo que la cinta hace de verdad.

**Por qué está aquí y no en `fijar.py`.** Eran dos funciones privadas del paso
que escribe, y sin embargo `costuras.py` ya las llamaba por la puerta de atrás
—`fijar._a_la_voz(...)`— porque no había otra. Un paso que escribe no puede ser
además la única fuente de una medida que otros necesitan: o se copia, o se entra
por detrás, y las dos acaban igual.

Aquí no se escribe nada. Se le da un tramo declarado —lo que alguien dijo que
quería— y devuelve dónde cae de verdad: pegado a la frontera de palabra si está
cerca, y partido donde el hablante se calla más de la cuenta.

**La vara es la onda, no el transcript.** `a_la_palabra` sí pregunta al
transcript, y por eso sólo mueve el borde si ya estaba a menos de `cerca`: los
transcripts de este proyecto traen palabras de duración cero y otras estiradas
sobre un silencio, así que darles la última palabra deja frases sin su cifra.
`a_la_voz` mide la señal.
"""
import json
import os

# Cuanto se puede retroceder para no entrar a mitad de frase. Mas que esto y
# lo que se recupera ya no es la cabeza de lo que se dice: es lo anterior.
RETROCESO = 1.5
# Por encima de esto un silencio deja de ser una pausa del hablante y pasa a ser
# aire muerto: se parte el tramo y se deja fuera.
HUECO = 1.2


def a_la_palabra(toma, ini, fin, cerca=0.45, voz=None):
    """Mueve los bordes a la frontera de palabra mas cercana.

    Solo si esta a menos de `cerca`: por encima de eso el borde no parte una
    silaba, esta donde alguien lo puso a proposito, y moverlo seria decidir por
    el. Devuelve `(ini, fin)` tal cual si no hay transcript.
    """
    import transcribir as _tr

    try:
        pal = _tr.exigir(toma)["segmentos"]
    except SystemExit:
        return ini, fin
    # Al entrar: si el borde cae dentro de una palabra, o justo despues de que
    # empiece, se entra donde empieza. Si esa palabra ya va por la mitad, se
    # entra cuando acaba.
    # **Y la entrada también la juzga la onda** (C-482), con las mismas dos
    # preguntas que `Habla.fuera_de_palabra` (C-481). Aquí solo se preguntaba
    # por la salida, así que lo que el compositor midió en reel-16 e2 —217,14,
    # el cierre de la /p/ de «porque», y 272,30, el silencio antes de «sin»— se
    # guardaba como 217,091 y 272,528: la cola de «presta» y «sin» sin «si-».
    from dominio import bordes as _bo
    for w in pal:
        x, y = w["start"], w["end"]
        if x < ini < y and y - x < 2.0:
            if _bo.callado_antes(toma, ini):
                break                       # la palabra de delante ya acabó
            if (ini - x) < (y - ini) and (ini - x) <= cerca:
                # Desde un poco ANTES del arranque que da el transcript: si ya
                # era exacto, la caída está justo antes y no dentro de la palabra
                # (reel-10 e2: sin esto entraba 85 ms dentro, en 38,992).
                q = _bo.mas_quieto(toma, x - 0.04, x + 0.08)
                ini = q if q is not None and q < y else x
            elif (y - ini) <= cerca:
                ini = y
            break
    for w in pal:
        x, y = w["start"], w["end"]
        if not (x < fin < y):
            continue
        # **El final de la palabra puede tragarse la pausa siguiente.** El
        # alineador estira la ultima palabra de una frase sobre el silencio, asi
        # que su `end` no es donde deja de sonar. Si se ajustara ahi entrarian
        # segundos mudos, y por eso el filtro de `cerca` lo descartaba y el
        # borde se quedaba partido: «al» sin «año», «en» sin «Ontario».
        #
        # La salida no es rendirse: es **acotar**. La palabra acaba, de verdad,
        # donde acaba el tramo de habla que la contiene. Lo dijo el paso que lo
        # sufrio dos vueltas seguidas: «cuando el acaba de la palabra absorbe
        # una pausa, acotar en vez de rendirse».
        real = y
        for a2, b2 in (voz or []):
            if a2 <= x < b2:
                real = min(y, b2)
                break
        # **Y el bloque de habla no siempre acota nada.** El detector cose
        # «semanales por no saber algo» en un solo bloque de 3,9 s, asi que
        # `min(y, b2)` deja `real` en el `end` del texto — y ahi el texto miente
        # por 0,2 s: en reel-01 «semanales» figura acabando en 571,209 y deja de
        # sonar en 571,00. Esos 0,2 s son el «por» siguiente, o sea que alargar
        # hasta el `end` no cerraba la palabra: traia el arranque de la de al
        # lado y el corte salia encima de la voz.
        #
        # Se le pregunta a la ONDA, con la vara del que juzga: si en el borde ya
        # no suena, la palabra acabo y el borde se queda donde esta. Ni se
        # alarga —no hay nada que cerrar— ni se retrocede al principio de la
        # palabra, que es lo que dejaba «550» sin decir y «mas» sin su «y».
        if _bo.callado(toma, fin):
            pass
        elif (real - fin) <= cerca:
            fin = real
        elif (fin - x) <= cerca:
            fin = x
        break
    return ini, fin


def a_la_voz(toma, a, b, margen=0.12):
    """Recorta los bordes de un tramo hasta donde de verdad se habla.

    ## Por que esto no puede ser responsabilidad de quien propone

    Un borde se propone copiando los segundos de una palabra del transcript, y
    **ese final esta inflado**: el alineador estira la ultima palabra de cada
    frase sobre el silencio que viene detras. Medido en la cinta de reel-06,
    `ano` dura de 319,14 a 326,20 —siete segundos para una palabra— y `Ontario.`
    de 417,89 a 424,20. Copiar ese final es tragarse la pausa entera.

    El resultado no es un corte peor: es una pieza que **se queda muda**. reel-06
    llevaba 15 s de silencio dentro, dos de ellos con un tablero encima, o sea
    con el espectador mirando algo que nadie le explica. Y no se ve leyendo el
    texto, porque por texto la frase esta completa.

    Asi que no se le pide a quien propone que lo tenga en cuenta —eso es un paso
    que depende de que alguien se acuerde—: se recorta aqui, que es por donde
    pasan todos los caminos que declaran una etapa. Es C-101 otra vez: cuando
    dos medidas del mismo hecho discrepan, gana la que mide el hecho. El
    transcript mide texto y **rellena** los tiempos que no sabe; el detector de
    voz mide la onda.

    **Solo los bordes.** Un silencio en medio es una pausa del hablante y es
    suya; quitarla es otra decision y la toma otro paso.

    Devuelve `None` si en ese tramo no se habla en absoluto.
    """
    # **Se le pregunta a la cinta, que es su dueña.** Esto abría
    # `work/cuts/<toma>.json` a mano y leía `["segmentos"]`, que es lo mismo
    # que `Cinta.habla()` — uno de los 32 sitios que se sirven solos del disco.
    #
    # **Y hay que saber cuál de las dos se está pidiendo.** `Cinta` declara dos
    # respuestas a «dónde suena» que se llevan `HOLGURA` = 0,285 s a cada lado:
    # `habla()` es lo que el detector conservó —con el silencio pegado— y
    # `voz()` es donde de verdad ataca la voz. Esta función usa la primera y se
    # llama `a_la_voz`, mientras `plan-reel::conHabla` usa la segunda para
    # recortar lo mismo. Por eso lo que este paso deja, aquél lo vuelve a
    # recortar: dos definiciones de dónde empieza la voz sobre el mismo tramo.
    #
    # **Cambiarlo mueve todos los bordes** —0,285 menos `MARGEN` = 0,225 s por
    # extremo— y eso no se decide sin oírlo: se mide corriendo la línea con
    # `Cinta.voz()` aquí y comparando las costuras con `suena.py`. Queda
    # declarado, no hecho. Lo que sí cambia hoy es que la definición se pide en
    # vez de leerse del disco, así que el día que se mueva, se mueve en un
    # sitio.
    from .cinta import Cinta

    cinta = Cinta(str(toma))
    if not os.path.exists(cinta.cortes):
        return (a, b)
    try:
        voz = cinta.habla()
    except (OSError, KeyError, json.JSONDecodeError):
        return (a, b)
    dentro = [(max(a, x), min(b, y)) for x, y in voz if min(b, y) - max(a, x) > 0.01]
    if not dentro:
        return None
    # **Y no se entra a mitad de una frase.** Si el borde cae DENTRO de un
    # tramo de habla, lo que se corta no es silencio: es el principio de lo que
    # se esta diciendo. Se retrocede hasta donde ese tramo empieza.
    #
    # Es la otra cara de lo mismo que C-129, y la mas cara: el alineador estira
    # una palabra sobre el silencio que la precede igual que sobre el que la
    # sigue. En la cinta de reel-05 la palabra «14» figura de 519,62 a 532,38
    # —doce segundos— y el corte entraba en 532,3, dentro de ella. Resultado: la
    # pieza decia «mil dolares de impuesto adicional» y **la cifra no aparecia
    # ni en el trozo ni en `antes`**, porque por texto la palabra cruzaba el
    # borde. Tres pasadas la dieron por no grabada. La cinta dice «14 mil».
    #
    # El limite existe para no arrastrar la frase anterior: si el tramo empezo
    # mucho antes, el borde se puso ahi por una razon y no se toca.
    ini = max(a, min(x for x, _ in dentro) - margen)
    fin = min(b, max(y for _, y in dentro) + margen)
    # **Y no se entra ni se sale a mitad de palabra.**
    #
    # El recorte a la voz deja el borde donde hay sonido, pero el sonido de una
    # palabra empieza antes de que la palabra se entienda: entrar en mitad de
    # «estratega» deja «tratega», y salir en mitad de «Ontario» deja «Onta».
    # Los agentes lo han devuelto vuelta tras vuelta —«estratega», «mas», «año»,
    # «Ontario», «20»— y siempre es lo mismo: un corte que cae dentro del tramo
    # de una palabra.
    #
    # Se ajusta a la frontera mas cercana **dentro de un margen corto**: si la
    # palabra que cruza el borde apenas ha empezado, se entra despues de ella;
    # si ya casi ha acabado, se entra antes. Mas lejos que eso no se toca — ahi
    # ya no es una silaba partida, es contenido, y eso lo decide el paso.
    ini, fin = a_la_palabra(toma, ini, fin, voz=voz)
    for x, y in voz:
        if x < a < y and a - x <= RETROCESO:
            ini = min(ini, max(0.0, x - margen))
            break
        # **Y lo que queda fuera del techo se dice, no se acepta callando.**
        #
        # El tope existe para no arrastrar la frase anterior, y esta bien que
        # exista; lo que estaba mal es que por encima de el este paso no
        # distinguia «el borde se puso ahi a proposito» de «el borde cayo a
        # mitad de frase y nadie lo vio». Los dos salian iguales: en silencio.
        #
        # reel-05 e2 entraba 3,12 s dentro de un bloque de voz de 5,755 s
        # —cinco veces RETROCESO— y por eso la pieza empezaba el caso en «...
        # tres casas en un mismo trimestre», sin nombrar al realtor que su
        # propio tablero rotula. Jaime lo pidio dos veces. No se mueve el borde
        # —eso seria decidir por quien lo puso— pero se cuenta cuanta frase se
        # queda fuera, que es lo unico que hacia falta para verlo antes de
        # montar.
        if x < a < y:
            print(f"  aviso {toma} [{a:.3f}]: entra {a - x:.2f} s en el bloque"
                  f" de voz de {x:.3f} y RETROCESO son {RETROCESO} s")
            break
    if fin - ini <= 0.2:
        return None
    # **Y un silencio largo DENTRO tampoco es una pausa: es aire muerto.**
    #
    # Esto solo recortaba los bordes, con el argumento de que un hueco en medio
    # es una pausa del hablante y es suya. Cierto hasta cierta duracion: siete
    # segundos no son una pausa. reel-04 llevaba 18,3 s mudos sobre 83, dos de
    # ellos con un tablero encima, y **cuatro vueltas de revision no lo vieron**
    # porque por texto el trozo parece una frase entera — el `hasta` estaba
    # clavado en la marca de la palabra siguiente.
    #
    # Se agrupan los tramos de voz que estan a menos de `HUECO` unos de otros;
    # cada grupo sale como un tramo. Deja de ser trabajo que alguien tiene que
    # ver y repetir en cada vuelta.
    grupos, act = [], []
    for x, y in dentro:
        if act and x - act[-1][1] > HUECO:
            grupos.append(act)
            act = []
        act.append((x, y))
    if act:
        grupos.append(act)
    trozos = []
    for g in grupos:
        x = max(ini, g[0][0] - margen)
        y = min(fin, g[-1][1] + margen)
        if y - x > 0.25:
            # **El ajuste a la palabra va AQUI, sobre el tramo que sale.**
            #
            # Estaba arriba, y despues de el pasaban dos cosas que lo deshacian:
            # el `RETROCESO` tira `ini` hacia el arranque del tramo de voz, y
            # estas dos lineas construyen el borde definitivo desde los tramos
            # de voz —`g[0][0] - margen`— en vez de desde el borde ya ajustado.
            # O sea que el ajuste solo sobrevivia cuando era el que mandaba.
            #
            # C-135 lo dejo escrito y el codigo hacia lo contrario: «primero se
            # recorta a la voz medida sobre la onda, LUEGO se ajusta a la
            # palabra». Aqui hacia voz, palabra, y voz otra vez.
            #
            # Medido sobre las seis piezas: 28 bordes a menos de 0,45 s de una
            # frontera —o sea, dentro del margen que este paso si toca— seguian
            # cayendo dentro de una palabra, y casi todos de entrada, que es el
            # lado que el `RETROCESO` mueve.
            x, y = a_la_palabra(toma, x, y, voz=voz)
            trozos.append((round(x, 3), round(_al_silencio(toma, y), 3)))
    return trozos or None


#: Cuanto se puede alargar una salida buscando silencio. Mas que esto ya no es
#: la cola de la palabra: es la siguiente.
HASTA_CALLAR = 0.45


def _al_silencio(toma, fin):
    """**La salida, llevada a donde la onda calla.**

    Quien propone el borde lo copia del transcript, que miente justo ahi: el
    compositor movio tres veces los de reel-10, 14 y 15 y la verificacion, que
    mide la onda, los siguio parando «encima de la voz» (C-437). Medir es de la
    maquina: se avanza de 20 en 20 ms hasta que `bordes.callado` diga que ya no
    suena, con la misma vara del que juzga. Si no calla en `HASTA_CALLAR`, las
    palabras van pegadas y el borde se queda donde estaba: eso ya no es medir,
    es decidir, y vuelve al compositor.
    """
    from dominio import bordes as _bo

    if _bo.callado(toma, fin):
        return fin
    # **Y no se entra en la palabra siguiente.** Donde dos palabras van pegadas
    # la onda no calla hasta despues de la segunda, y avanzar hasta ahi la
    # devolvia: el «Usted» que el compositor corto en reel-08 e4 (C-447). El
    # techo es el arranque de la palabra que empieza despues del borde.
    tope = fin + HASTA_CALLAR
    try:
        import transcribir as _tr
        sig = [w["start"] for w in _tr.exigir(toma)["segmentos"]
               if w["start"] > fin + 0.03]
        if sig:
            tope = min(tope, min(sig) + 0.06)
    except (SystemExit, Exception):  # noqa: BLE001 — sin transcript, sin techo
        pass
    t = fin
    while t < tope:
        t += 0.02
        if _bo.callado(toma, t):
            return t
    return fin
