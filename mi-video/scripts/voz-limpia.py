"""Reintegra la voz limpiada fuera, sin tocar el montaje.

Regla de Jaime, y viene de un fallo mío: *«el sonido se escucha con mucho eco la
voz, se perdieron factores y suena muy feo; voy a pasarlo por Adobe Podcast,
dame los audios de los vídeos sin arreglos, puros»*. Y después: *«en esa misma
carpeta te dejo los optimizados»*.

## Por qué la limpieza se hace fuera

Le puse a la voz una cadena de corrección —highpass, campana a 250 Hz, presencia
a 3200, de-esser— para responder a *«no se mejoró la calidad»*. Fue un error de
lectura: lo que había pedido era *«dejar el sonido de la voz un poco más
natural»*, y yo contesté con **más** procesado. El corte de 250 Hz es
exactamente lo que le quita el cuerpo a una voz masculina.

Una herramienta que hace **sólo** eso lo hace mejor. Así que el reparto queda:
el pipeline corta, sincroniza y mezcla; la limpieza de voz es un paso externo, y
esto la devuelve a su sitio.

## Lo que comprueba antes de tocar nada

**La duración.** Un fichero limpiado que no dura lo mismo desincroniza la pieza
entera, y eso no se ve hasta el render. Si difiere más de `TOLERANCIA`, se dice
y no se sustituye — un audio desplazado medio segundo es peor que uno con eco.

    python scripts/voz-limpia.py --ver     # que encontraria y si encaja
    python scripts/voz-limpia.py           # sustituye y masteriza
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
# **`rutas` va aqui, no dentro de `exportar()`.** `main()` lo usa para saber que
# piezas hay cuando no se le pasa ninguna, asi que el paso con numeros funcionaba
# y el paso entero —como lo llama la linea— moria con NameError despues de
# renderizar las siete: un import escondido en una rama solo existe en esa rama.
import rutas  # noqa: E402
import sincronia  # noqa: E402
from acelerar import _acelerar  # noqa: E402,F401

# **F: es la memoria de trabajo; G: es donde queda lo terminado.**
#
# Jaime lo fijo el 1 de septiembre, y con su imagen: *«F es memoria de trabajo…
# una RAM con superpoderes»*. Y la division entera: *«G solo para ediciones
# finales o para recoger; las de trabajo en F; terminamos y borramos todo de F y
# queda en G»*.
#
# La voz que el limpia es material de trabajo, asi que sale a F: y ahi se
# recoge. Estuvo saliendo a G: y ese es el error que la regla corrige: llenar de
# intermedios el sitio donde solo tiene que haber piezas terminadas.
#
# G: se sigue mirando al RECOGER —si el deja ahi el limpiado, vale igual—, pero
# ya no es donde se deja.
# **Y ahora si sale a F:.** El comentario de arriba decia que la regla
# estaba puesta y la lista seguia llevando G: — declarado y no hecho, otra
# vez. Jaime, al ver los exports de hoy: *«dejalos en F por favor»*.
CARPETAS = [
    "out/audio-puro",
    rutas.LIMPIAR,
]

# Cuanto puede diferir la duracion antes de considerarlo otro audio. Cuarenta
# milisegundos es medio frame: por debajo no se ve, por encima se nota en los
# labios.
# **Y el resto vive en la cola muda, que no puede desincronizar una palabra.**
#
# Eran 40 ms —«medio frame»— y la reconciliacion de la cola deja un residuo de
# ~44 ms: el `apad` y el contenedor redondean a limites de muestra y de frame, y
# el sobrante queda al FINAL, en silencio, sobre la tarjeta de cierre. Ahi no hay
# labios que despegar.
#
# 60 ms son menos de dos frames y siguen siendo imperceptibles; lo que la guarda
# tiene que impedir es una diferencia que arrastre la voz, y esa se ve en el
# rango de los cientos de milisegundos, no aqui. Rechazar por 4 ms de silencio
# obliga a Jaime a limpiar otra vez un audio que encaja.
TOLERANCIA = 0.06

#: Cuanto silencio se admite anadir al final. Mas que esto no es la tarjeta
#: de cierre: es que falta voz por algun sitio, y eso no se tapa callando.
HUECO_MAX = 3.0

#: Lo que se recorta sin comprobar si esta callado: 120 ms, tres frames y
#: medio. Por debajo de eso no hay palabra que perder, y lo que sobra suele
#: ser el redondeo del resampler al acelerar, no una cola de verdad.
MIGAJA = 0.12

# **La convencion de nombres, que la puso el.** Jaime: *«ya viste que la
# estructura de guardado es regular: el mismo nombre mas otra parte al final»*.
#
# Yo exporto `reel-01-voz.wav` y el devuelve `reel-01-voz-enhanced-v2.wav`. Asi
# que el limpiado es **cualquier fichero que empiece por el nombre base y sea
# mas largo**: no hay que obligarle a renombrar seis ficheros ni adivinar que
# sufijo pone cada herramienta.
BASE_VOZ = "{slug}-voz"


def _con_tiquets(piezas):
    """Las de esa lista con la composicion abierta, y cuantas notas. Vacia = congeladas.

    Se le pregunta a `dominio.abierto.suyas`, que es quien sabe cuales son SUS
    correcciones: contar filas de `revision` a pelo metia tambien las notas de
    maquina —esquema muerto, una medida que no se puede tomar— y esas no dicen
    nada de si la composicion esta cerrada. Con reel-01 pasaba: su unica nota
    abierta era de maquina y bloqueaba el export de la pieza entera.
    """
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "dominio"))
    from dominio import abierto

    # **Lo que bloquea es lo que cambia el CORTE, no cualquier tiquet.**
    #
    # La regla de Jaime —la voz se manda a Adobe una vez y al final— existe por un
    # motivo mecanico y uno solo: si el corte cambia, el stem que Adobe devuelve
    # deja de corresponder y la mezcla cae a la voz cruda sin avisar. Un tiquet
    # GRAFICO no toca el corte: el tablero, la placa y el gancho se dibujan sobre
    # el mismo audio.
    #
    # Bloquear por cualquier tiquet abierto retenia las siete voces por catorce
    # correcciones de dibujo, y eso no protege nada: retrasa. Se mira `accion`.
    CAMBIAN_EL_CORTE = {"cortar", "subtitulo"}
    fuera = []
    for n in piezas:
        s = f"reel-{n:02d}"
        k = sum(1 for t in abierto.suyas(s) if t[1] in CAMBIAN_EL_CORTE)
        if k:
            fuera.append((s, k))
    return fuera


def exportar(n):
    """Saca la voz del reel n **sin tocarla**: el paso 1 de los dos que pidio.

    Cada tramo se extrae del bruto tal cual y se pegan. Sin estirar, sin
    ecualizar, sin fundidos, sin musica y sin normalizar. Es lo que Jaime pidio
    con esas palabras: *«quiero el audio de la voz separado sin
    modificaciones»*.

    **Y a velocidad natural.** La primera vez le di el audio ya estirado a
    1,15x —resintetizado por `rubberband`— y encima paso por Adobe: dos
    resintesis encadenadas, y de ahi lo raro. El lote vuelve a ir a 1,15x, pero
    esto sale del CORTE y no de la entrega: la limpieza va antes de acelerar.
    """
    slug = f"reel-{n:02d}"
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return None
    import rutas as _ru
    edl = json.load(open(ruta, encoding="utf-8"))
    # **La voz se exporta del PLAN, que es lo que se renderiza.**
    #
    # Salia del EDL, y el EDL no es la pieza: `plan-reel` quita el aire de cada
    # corte antes de repartirlo en escenas. Medido en reel-01: el wav duraba
    # 109,2 s y el video 100,9. Eso no es un detalle de contabilidad — este wav
    # se manda a limpiar fuera y **vuelve para pegarse encima del montaje**, asi
    # que ocho segundos de mas significan que la voz limpia entra desfasada y
    # creciendo, que es exactamente el fallo que costo C-97 por la puerta de las
    # capas. Jaime lo vio al instante: *«entonces si no cuadra»*.
    #
    # Si no hay plan todavia se cae al EDL, que es mejor que no exportar nada.
    try:
        plan = json.load(open(f"work/scenes/{slug}/plan-full.json",
                              encoding="utf-8"))["escenas"]
    except Exception:                              # noqa: BLE001
        plan = None
    if plan:
        # Las escenas del plan no llevan de que cinta salen, asi que se resuelve
        # **por contenido**: la escena cae dentro del corte del EDL que la
        # engendro, y ese corte si sabe su cinta. Por indice no vale — el plan
        # parte un corte en varias escenas, asi que las listas no se
        # corresponden. Y con el remate del reel-01 viniendo de otra cinta, dar
        # por hecha la del reel seria traerse el audio equivocado.
        def _toma(e):
            for (x, y), d in zip(edl["segmentos"], edl["detalle"]):
                if e["origen_desde"] >= x - 0.05 and e["origen_hasta"] <= y + 0.05:
                    return d.get("toma")
            return edl["detalle"][0].get("toma")

        pares = [([e["origen_desde"], e["origen_hasta"]], {"toma": _toma(e)})
                 for e in plan]
    else:
        pares = list(zip(edl["segmentos"], edl["detalle"]))
    os.makedirs("out/audio-voz", exist_ok=True)
    os.makedirs("F:/tmp-video/voz", exist_ok=True)
    out = f"out/audio-voz/{BASE_VOZ.format(slug=slug)}.wav"
    # **La voz sale del CORTE, no de volver a pegar la cinta.**
    #
    # Salia recortando cada tramo del bruto segun el plan, en segundos exactos.
    # `render-hook.mjs` arma el corte recodificando esos mismos tramos, y cada
    # uno se redondea a frame entero: el sonido es el mismo, el reloj no. Sobre
    # veinticuatro tramos ese redondeo se suma —el plan de reel-01 dice 93,36 s
    # y el fichero mide 93,07— y la voz que vuelve de Adobe entra derivando.
    #
    # Y hay algo peor que la deriva: si el corte cambia despues de exportar, lo
    # que se mando a limpiar es de OTRO montaje. Medido el 4 de septiembre:
    # reel-04 iba 2,0 s corrido en sus primeros 25 s y bien en el resto,
    # reel-07 al reves. Un escalon asi no lo arregla mover ni estirar.
    #
    # `public/reel-NN.mp4` es el corte tal cual: misma cinta, mismo sonido sin
    # tocar, y **el reloj de la pieza por construccion**. Exportar de ahi hace
    # imposibles las dos averias a la vez.
    corte = f"public/{slug}.mp4"
    if os.path.exists(corte):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", corte, "-vn",
                        "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", out],
                       check=True)
        # **Y sin las pausas del baile.** Van en el corte, asi que salian dentro
        # de lo que Jaime manda a limpiar — y con eso, mover el ritmo tiraba su
        # pasada de Adobe: le paso tres veces. Una pausa es silencio y el
        # silencio se le devuelve DESPUES a un fichero ya limpio (C-527).
        import pausas as _pa
        tmp = out.replace(".wav", "-seguida.wav")
        if _pa.quitar(out, tmp, slug):
            os.replace(tmp, out)
            print(f"    {slug}: sin las pausas del baile — se devuelven al integrar")
        return _repartir(out)
    trozos = []
    for i, (r, d) in enumerate(pares):
        f = f"F:/tmp-video/voz/{slug}-{i:03d}.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", str(r[0]),
             "-i", f"{_ru.ORIGEN}/{d['toma']}.mp4",
             "-t", str(round(r[1] - r[0], 3)), "-vn",
             "-c:a", "pcm_s16le", "-ar", "48000", "-ac", "1", f], check=True)
        trozos.append(f)
    lista = f"F:/tmp-video/voz/{slug}.txt"
    open(lista, "w", encoding="utf-8").write(
        "\n".join("file '{}'".format(t) for t in trozos) + "\n")
    out = f"out/audio-voz/{BASE_VOZ.format(slug=slug)}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", lista, "-c", "copy", out], check=True)
    # **Y al lado, la misma voz con cabecera.** Jaime: *«normalizada si puede
    # servir»*, y sirve por un motivo concreto: el bruto viene pegado a 0 dBFS
    # —29.804 muestras planas en los dos primeros minutos del reel-01— y
    # meterle a Adobe Podcast un fichero sin un dB libre es pedirle que trabaje
    # sobre lo ya recortado.
    #
    # Es **ganancia lineal y nada mas**: se mide el pico y se baja hasta -3
    # dBTP. Sin compresor, sin limitador, sin `loudnorm` —que lleva uno
    # dentro—. La dinamica queda intacta y no hay una segunda resintesis antes
    # de la de Adobe, que es de donde salio 'lo raro' la primera vez.
    #
    # El fichero sin tocar NO se sustituye: se entregan los dos, porque el
    # de origen es el que pidio Jaime *«sin modificaciones»* y este es una
    # comodidad para el paso siguiente.
    _con_cabecera(out)
    # **A TODAS las carpetas, no a la primera.**
    #
    # Esto recorria `CARPETAS` y hacia `break` en la primera que existiera, que
    # es la local. La de Drive —donde Jaime los recoge— es la segunda, asi que
    # no recibia nada nunca. El paso decia «en out/audio-puro» y salia con
    # exito mientras el se pasaba tres dias oyendo los del 29 de agosto:
    # *«no has subido los nuevos, yo como bobo escuchando los viejos»*.
    #
    # Es la averia del render por la puerta del audio: el trabajo se hace, el
    # paso dice que si, y el fichero no llega a donde se consume. Se copian las
    # dos versiones —la intacta y la de cabecera— y **se dice a donde**.
    return _repartir(out)


def _repartir(out):
    """Cabecera y copia a TODAS las carpetas donde Jaime la recoge."""
    _con_cabecera(out)
    for carpeta in CARPETAS:
        # **La carpeta se crea, no se salta.** Esto hacia `continue` si no
        # existia, asi que al mover el destino a F: los tres exports salieron
        # diciendo «hecho» y no habia nada donde el iba a mirar. `CARPETAS` es
        # la lista de sitios DONDE SE DEJA, no un espejo opcional: si no existe,
        # el que falta es el directorio, no el fichero.
        os.makedirs(carpeta, exist_ok=True)
        shutil.copy2(out, carpeta)
        print('    -> ' + carpeta)
    return out



def _con_cabecera(wav, objetivo=-3.0):
    """Le baja el pico a `objetivo` dBTP. Solo ganancia, y SOBRE EL MISMO fichero.

    Escribia un `-norm.wav` al lado y quedaban catorce ficheros para siete
    piezas. Jaime: *«no quiero 14 archivos inoficiosos»*. Y no se pierde nada:
    la normalizada **es** la cruda con una ganancia, no hay proceso de por medio
    — ni compresor, ni limitador— asi que el original no aporta una segunda
    version, aporta un fichero mas que mantener.
    """
    medida = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", wav,
         "-af", "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    pico = None
    for linea in (medida.stderr or "").splitlines():
        if '"input_tp"' in linea:
            try:
                pico = float(linea.split(":")[1].strip().strip(',"'))
            except ValueError:
                pico = None
    if pico is None:
        return None
    ganancia = objetivo - pico
    # **Por un temporal.** ffmpeg se niega a escribir sobre el fichero que lee
    # —«Output same as Input #0 - exiting»— y con `check=True` eso reventaba la
    # exportacion entera en la primera pieza. Se escribe al lado y se sustituye.
    salida = wav + ".tmp.wav"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", wav,
         "-af", "volume={:+.2f}dB".format(ganancia), salida], check=True)
    os.replace(salida, wav)
    print("    cabecera {:+.2f} dB: pico {:.1f} -> {:.1f} dBTP".format(
        ganancia, pico, objetivo))
    return wav


def duracion(f):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", f], capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


#: Cuanto se tienen que parecer las dos envolventes para dar el audio por el
#: mismo. **Es la segunda red, no la primera**: la que separa de verdad es la
#: duracion, arriba.
#:
#: Empezo en 0,45 y con eso habria rechazado audio BUENO. Los numeros, sobre las
#: siete piezas y con las limpias que Jaime aprobo de oido:
#:
#:     corresponden   0,556  0,429  0,324  0,299  0,297  0,284  0,253
#:     de otro corte  0,206  0,179  0,141
#:
#: Adobe rehace la envolvente —quita ruido, nivela, cierra los huecos— asi que un
#: par correcto puede quedarse en 0,25. El margen entre las dos familias es
#: estrecho (0,21 contra 0,25), y por eso esto solo caza lo grosero: 0,24 deja
#: pasar todo lo bueno medido y para lo que no se parece en nada.
PARECIDO = 0.24


def _corresponde(video, wav):
    """Cuanto se parecen las dos ondas. `None` si no se pudo medir.

    La envolvente la calcula `desfase.envolvente`, que es la misma de siempre:
    aqui habia una segunda copia con sus propios numeros de ventana, y dos
    copias de una medida se separan en cuanto una se toca.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    a_, b_ = (sincronia.desfase.envolvente(video),
              sincronia.desfase.envolvente(wav))
    if a_ is None or b_ is None:
        return None
    corto, largo = (b_, a_) if len(b_) <= len(a_) else (a_, b_)
    return float(np.abs(np.correlate(largo, corto, mode="full")).max())


# Cual de los ficheros de la carpeta es su voz limpia: `candidato.py`.
def candidato(n):
    import candidato as _c
    return _c.de(n, CARPETAS, BASE_VOZ)


def integrar(n, ver=False):
    video = f"out/reels/reel-R{n}.mp4"
    if not os.path.exists(video):
        return False
    wav = candidato(n)
    if not wav:
        print(f"R{n}: sin audio limpiado todavia")
        return False
    # Salio a limpiar seguida, asi que se le devuelven las pausas del baile
    # antes de mirar si encaja, con el reparto de HOY: `pausas.py` (C-527).
    import pausas as _pa
    wav = _pa.poner_si_baila(wav, n)
    # **Y la voz limpia tiene que ser DE ESTE corte.**
    #
    # La limpieza se exporta desde `public/reel-NN.mp4`, asi que una que sea mas
    # vieja que ese fichero se hizo sobre otro montaje. Las guardas de abajo
    # comparan segundos y eso no lo ven: el 7-9-2026 las siete piezas se
    # entregaron con la voz del corte del dia anterior, seis con 0,2-0,5 s de
    # deriva —que se oye como el subtitulo adelantado; Jaime: *«el cc esta
    # desfasado»*— y reel-03 con 2,33 s, o sea **el gancho entero mudo**:
    # *«se ve la imagen pero no se escucha mi voz»*.
    #
    # Es C-308 en el audio: lo que no sabe de que corte es, sobrevive al corte.
    # Y aqui se prefiere la voz cruda EN SU SITIO a una limpia de otro montaje,
    # que es la misma regla que ya aplica `distancia` al negarse a medir.
    #
    # **Pero la fecha no es el corte: es cuando se escribio el fichero.** Jaime,
    # 14-9-2026, despues de que esto le tumbara la misma voz tres veces:
    # *«cambia la guarda pero compara que sea la misma»*. Un re-render por un
    # cambio VISUAL —aquel dia, el recorte de e6 a blanco y negro— reescribe
    # `public/reel-NN.mp4` con los mismos 149.348.250 bytes y los mismos
    # 58,621 s, y con eso la fecha acusa a una voz que corresponde al corte
    # hasta la decima de milisegundo. Tres vueltas de Adobe para nada.
    #
    # Asi que cuando la fecha sospecha, se MIDE: `_corresponde` compara las dos
    # ondas y ya estaba en este fichero —corriendo mas abajo, donde nunca se
    # llegaba porque esto cortaba antes—. No es aflojar el seguro: es cambiarlo
    # de senal. Medido el mismo dia sobre reel-13: la voz buena da 0,98 contra
    # su corte y la de otra pieza 0,11, con el umbral en 0,24. La fecha no
    # separaba nada; la onda separa por 8,7 veces.
    #
    # Y si no se puede medir, se rechaza: no medir no es aprobar (C-243).
    if os.path.getmtime(wav) < os.path.getmtime(f"public/reel-{n:02d}.mp4"):
        casa = _corresponde(f"public/reel-{n:02d}.mp4", wav)
        if casa is None or casa < PARECIDO:
            print(f"R{n}: la voz limpia es mas vieja que el corte Y no es la"
                  f" misma onda ({'no se pudo medir' if casa is None else f'parecido {casa:.2f}, hace falta {PARECIDO}'}):"
                  f" se hizo sobre otro montaje. No se sustituye: sale con su"
                  f" voz cruda, en su sitio. Vuelve a limpiarla desde el corte"
                  f" de hoy.")
            registro.aviso("voz-limpia", "voz limpiada de otro corte",
                           detalle=f"R{n}: {os.path.basename(wav)}"
                                   f" (parecido {casa})", eco=False)
            return False
        print(f"R{n}: la voz limpia es mas vieja que el corte, pero es la misma"
              f" onda (parecido {casa:.2f}): el corte se reescribio sin cambiar"
              f" el sonido. Sigue.")
    # **Primero se pone en su sitio, y despues se mide si cabe.**
    #
    # El orden importa y estaba al reves. Las guardas de duracion de abajo
    # comparan segundos, asi que una pista movida dos segundos las pasa si dura
    # lo mismo — y peor: `_sin_cola_muda()` le quita de la cola justo lo que le
    # sobraba por delante y **fabrica** el fichero que pasa la guarda.
    #
    # Alinear antes deja la cola diciendo la verdad: si despues de casar el
    # arranque sigue sobrando o faltando material, eso ya es contenido y ahi si
    # se para.
    wav, movido, ventanas, motivo = sincronia.encajar(n, wav)
    if motivo:
        print(f"R{n}: NO encaja — {motivo}. No se sustituye: iria desfasada.")
        registro.aviso("voz-limpia", "voz limpiada desfasada del corte",
                       detalle=f"R{n}: {motivo}", eco=False)
        return False
    if abs(movido) > sincronia.AL_FRAME:
        print(f"R{n}: la voz iba {movido:+.2f}s del corte — alineada")
        registro.nota("voz-limpia", "voz limpiada alineada al corte",
                      detalle=f"R{n}: {movido:+.2f}s")
    dv, da = duracion(video), duracion(wav)
    # **Lo que sobra esta al final, y es silencio.** Jaime, sobre la herramienta
    # con la que limpia: *«lo que le sobra a la pista del audio esta en la ultima
    # parte, siempre agrega silencios al final»*.
    #
    # Sin esto, un limpiado correcto se rechazaba entero por una cola muda que no
    # cambia una sola palabra — y el unico camino que quedaba era pedirle que lo
    # limpiara otra vez, o sea tirar trabajo suyo por algo que la maquina puede
    # quitar sola. Se recorta la cola y se vuelve a medir; si aun asi no cuadra,
    # la diferencia esta dentro y ahi si hay que parar.
    #
    # **Y con TOPE, que es lo que faltaba.** Recortar sin limite borra la unica
    # prueba de que la pista es de otro montaje: la de reel-01 sobraba 6,6 s
    # —no es una cola, es otra edicion—, se recorto a la duracion justa y paso
    # la guarda con contenido de una version anterior. Jaime lo oyo y lo dijo en
    # una frase: *«si el audio no esta bien el video no esta bien»*.
    #
    # Mismo tope que para completar: por encima de `HUECO_MAX` la diferencia ya
    # no es la cola, es que sobra o falta algo dentro.
    if round(da - dv, 3) > TOLERANCIA:
        if da - dv > HUECO_MAX:
            print(f"R{n}: NO encaja — al audio le sobran {da - dv:.2f}s, mas de"
                  f" los {HUECO_MAX}s que puede ser cola muda. Eso no es una"
                  f" cola: es otro montaje. No se recorta para que quepa.")
            registro.aviso("voz-limpia", "audio limpiado de otro montaje",
                           detalle=f"R{n}: sobran {da - dv:.2f}s", eco=False)
            return False
        podado = _sin_cola_muda(wav, dv)
        if podado:
            wav, da = podado, duracion(podado)
    # **Y si falta cola, se completa con silencio.**
    #
    # El caso contrario y por la misma razon: el video acaba con la tarjeta de
    # cierre, donde no habla nadie, asi que la voz limpiada dura MENOS que la
    # pieza. Medido en reel-01: 104,40 s de voz contra 105,59 de video — 1,19 s
    # que son tarjeta, no palabra. Rechazar por eso obliga a Jaime a limpiar otra
    # vez un audio que esta bien.
    #
    # Se completa **con silencio y solo al final**, y solo si falta poco: por
    # encima de `HUECO_MAX` la diferencia ya no es la cola, es que sobra o falta
    # algo dentro, y ahi si hay que parar.
    elif round(dv - da, 3) > TOLERANCIA:
        if dv - da > HUECO_MAX:
            pass
        else:
            rellenado = _con_cola_muda(wav, dv)
            if rellenado:
                wav, da = rellenado, duracion(rellenado)
    # **Se compara redondeado al milisegundo.** Con `>` a pelo, una diferencia
    # de exactamente 0,04 s fallaba por el ruido de coma flotante: 0,0400001 es
    # mayor que 0,04 y la guarda rechazaba un audio que encajaba al frame. Una
    # comparacion de frontera que depende de un decimal invisible no es una
    # guarda: es un accidente que da la razon al azar.
    if round(abs(dv - da), 3) > TOLERANCIA:
        print(f"R{n}: NO encaja — el video dura {dv:.2f}s y el audio {da:.2f}s"
              f" ({abs(dv - da):.2f}s de diferencia). No se sustituye:"
              f" desincronizaria la pieza entera.")
        registro.aviso("voz-limpia", "audio limpiado con otra duracion",
                       detalle=f"R{n}: {dv:.2f} vs {da:.2f}", eco=False)
        return False
    # **Y encajar de duracion no es encajar.** Jaime, oyendo la entrega: *«el
    # audio del primero esta completamente desfasado»*.
    #
    # La guarda de arriba solo compara segundos, y con eso una pista de OTRO
    # montaje pasa si por casualidad dura lo mismo. Peor: este script recorta la
    # cola cuando sobra, asi que **fabrica** el fichero que hace pasar la guarda.
    # Medido en las siete: la de reel-01 duraba 102,92 s contra 96,34 del corte,
    # se recorto a 96,43 y entro con contenido de una edicion anterior.
    #
    # Aqui se comprueba que sea EL MISMO AUDIO: se cruzan las envolventes y el
    # pico dice si corresponden. Es la misma medida que `desfase.py` usa para
    # casar dos camaras, y aqui contesta la pregunta gemela.
    # **Y sólo cuando el perfil no pudo contestar.** `sincronia.encajar` mide el
    # desfase en nueve puntos repartidos por la pieza; si engancha en cuatro o
    # más, eso ya prueba que el contenido es el mismo — una pista de otro
    # montaje no cuadra en nueve sitios ni por casualidad. El parecido global,
    # además, castiga a la pista que hubo que acompasar: `rubberband` cambia la
    # forma de la onda, y reel-05 salía a 0,22 con la sincronía medida en dos
    # centésimas. Seguir bloqueando por ahí sería rechazar la pista **por estar
    # arreglada**.
    casa = _corresponde(video, wav) if ventanas < 4 else None
    if casa is not None and casa < PARECIDO:
        print(f"R{n}: NO encaja — dura lo mismo ({da:.2f}s) pero el audio es de"
              f" OTRO montaje (parecido {casa:.2f}, hace falta {PARECIDO}). No se"
              f" sustituye: iria desfasado de principio a fin.")
        registro.aviso("voz-limpia", "audio limpiado de otro montaje",
                       detalle=f"R{n}: parecido {casa:.2f}", eco=False)
        return False
    print(f"R{n}: {os.path.basename(wav)} encaja ({da:.2f}s"
          + (f", parecido {casa:.2f})" if casa is not None else ")"))
    if ver:
        return True
    tmp = f"F:/tmp-video/reel-R{n}-voz.mp4"
    # **Se MEZCLA la voz limpia con los efectos, no se sustituye la pista.**
    #
    # Esto hacia `-map 0:v -map 1:a`: video del render y audio SOLO del wav.
    # Y los efectos viven dentro del render, asi que al meter la voz de Adobe
    # se iban los seis o siete de cada pieza — en las seis entregadas no habia
    # ni uno. Jaime: *«falto la musica… igual que los efectos de sonido»*.
    #
    # No se pueden rescatar de lo entregado —el render trae voz y efectos ya
    # mezclados— asi que `scripts/efectos.mjs` vuelve a renderizar la misma
    # composicion con el plano mudo (`volumen: 0`) y deja los efectos solos.
    # Si esa pista no esta, se sustituye como antes y **se dice**.
    sfx = f"out/audio-voz/reel-R{n}-efectos.wav"
    if os.path.exists(sfx):
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav, "-i", sfx,
             "-filter_complex", "[1:a][2:a]amix=inputs=2:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", tmp],
            check=True)
    else:
        print(f"    R{n}: SIN pista de efectos — corre `node scripts/efectos.mjs {n}`")
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", wav,
             "-map", "0:v", "-map", "1:a", "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", tmp],
            check=True)
    os.replace(tmp, video)
    registro.nota("voz-limpia", "voz limpiada reintegrada",
                  detalle=f"R{n}: {os.path.basename(wav)}")
    return True


def _sin_cola_muda(wav: str, objetivo: float):
    """Quita la cola muda del final hasta dejarlo en `objetivo` segundos.

    Se comprueba que lo que se quita **esta callado de verdad** antes de tocarlo:
    recortar por duracion sin mirar la onda seria cortar voz para que cuadre un
    numero, que es la peor manera de arreglar una desincronia.
    """
    fin = duracion(wav)
    if fin is None or fin <= objetivo:
        return None
    # **Una migaja se recorta sin preguntar si esta callada.**
    #
    # La comprobacion de abajo existe para no cortar VOZ, y por debajo de
    # `MIGAJA` no hay voz que cortar: en 120 ms —tres frames y medio— no cabe una
    # palabra ni una silaba entera.
    #
    # Sin esto, reel-07 se rechazaba entero por 70 ms. Y esos 70 ms no son una
    # cola: son el redondeo del resampler al acelerar a 1,15x, que no puede
    # aterrizar en la duracion exacta. La guarda estaba rechazando su propio
    # artefacto y mandando a Jaime a limpiar otra vez un audio que estaba bien.
    if fin - objetivo <= MIGAJA:
        return _recorta(wav, objetivo)
    try:
        r = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", str(objetivo), "-i", wav,
             "-af", f"volumedetect", "-f", "null", "-"],
            capture_output=True, text=True)
        pico = [x for x in (r.stderr or "").splitlines() if "max_volume" in x]
        if pico and float(pico[0].split(":")[-1].replace("dB", "").strip()) > -45.0:
            registro.aviso("voz-limpia", "la cola de mas NO esta callada",
                           detalle=f"{os.path.basename(wav)}: {pico[0].strip()}",
                           eco=True)
            return None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None
    return _recorta(wav, objetivo)


def _recorta(wav: str, objetivo: float):
    """Deja el wav en `objetivo` segundos. Sin juicio: eso lo hace quien llama.

    **Se RECODIFICA, no se copia.** Con `-c copy` ffmpeg no corta este material:
    devuelve el fichero entero con la misma duracion y **sale con exito**, asi que
    el paso creia haber recortado y volvia a medir lo mismo. Comprobado sobre
    reel-07:

        origen          57,429 s
        con -c copy     57,429 s   <- no hizo nada, y no lo dijo
        recodificado    57,360 s   <- exacto

    El corte cae donde cae, no en un limite de paquete, y copiar no puede partir
    un paquete. Es PCM: recodificar no pierde nada.

    Y por eso el recorte de cola no funciono nunca en los casos que lo
    necesitaban. Los que si cuadraban lo hacian por otra via.
    """
    salida = wav.rsplit(".", 1)[0] + "-sin-cola." + wav.rsplit(".", 1)[1]
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", wav, "-t",
                        str(objetivo), "-c:a", "pcm_s16le", salida],
                       capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    # Y se comprueba que de verdad quedo mas corto: un recorte que no recorta es
    # lo que este arreglo viene a cerrar, y no se puede volver a creer sin mirar.
    d = duracion(salida)
    if d is None or d > objetivo + 0.02:
        return None
    return salida



def _con_cola_muda(wav: str, objetivo: float):
    """Alarga el audio con silencio hasta `objetivo`. Nada mas."""
    salida = wav.rsplit(".", 1)[0] + "-con-cola." + wav.rsplit(".", 1)[1]
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", wav, "-af",
             f"apad=whole_dur={objetivo}", "-t", str(objetivo), salida],
            capture_output=True, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return salida



#: Cuanto se acelera la pieza. **No se declara aqui: se lee de `beats`**, que es
#: donde vive la velocidad del montaje y que ya avisa por que: *«estaba repetido
#: en seis ficheros, que es como se acaba teniendo dos velocidades distintas en
#: el mismo montaje»*.
#:
#: Y es lo que paso. Jaime fijo 1,15 el 1 de septiembre y lo revoco despues
#: —*«ninguno hay que acelerar la verdad»*—; `beats` y `revision` bajaron a 1,0
#: y **este fichero se quedo en 1,15**. Como `_acelerar` escribe en
#: `out/entrega/`, las siete entregas siguieron saliendo estiradas por
#: `rubberband` sobre una voz ya reconstruida por Adobe: las dos resintesis
#: encadenadas que `beats` dice haber quitado de la cadena.
#:
#: Medido el 4 de septiembre, entrega contra render: 81,20/93,37 · 74,40/85,47 ·
#: 45,10/51,80 · 56,70/65,10 · 72,40/83,20 · 59,20/68,00 · 76,70/88,17. Las
#: siete a 0,870, que es 1/1,15 clavado.
from beats import VELOCIDAD  # noqa: E402,F401


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--igual", action="store_true",
                    help="exporta aunque la composicion siga abierta")
    ap.add_argument("--exportar", action="store_true",
                    help="paso 1: saca la voz sin modificar a la carpeta")
    a = ap.parse_args()
    if a.exportar:
        # **El export es el ULTIMO paso, y con el corte congelado.**
        #
        # Jaime: *«antes de pasarlos quiero ver la composicion completa; con eso
        # lo dejamos como paso final una sola vez»*. No es preferencia: cada vez
        # que cambia el corte, el stem que Adobe devuelve deja de corresponder y
        # la mezcla cae a la voz cruda sin avisar — medido hoy en seis de las
        # siete. Exportar antes de congelar es tirar su trabajo y el de Adobe.
        #
        # Se avisa y se para; `--igual` lo salta para tantear una pieza.
        abiertos = _con_tiquets(a.reels or rutas.piezas())
        if abiertos and not a.igual:
            print("  NO se exporta: estas piezas tienen la composicion abierta")
            for s_, k in abiertos:
                print(f"    {s_}: {k} tiquet(s) sin cerrar")
            print("  La voz va DESPUES de que Jaime vea la composicion, y para"
                  " las siete de una vez. Con --igual se exporta igualmente.")
            return
        for n in (a.reels or rutas.piezas()):
            f = exportar(n)
            if f:
                d = duracion(f)
                print(f"R{n}: {os.path.basename(f)}  {d:.2f}s sin modificar")
        print(f"\nen {CARPETAS[0]}")
        return
    hechos, pedidos = [], (a.reels or rutas.piezas())
    for n in pedidos:
        if integrar(n, ver=a.ver):
            hechos.append(n)
    # **Y se entrega tambien lo que no pudo cambiar de voz.** La aceleracion y
    # el nivelado colgaban de que la voz limpia entrara, asi que una pieza con
    # la pista desfasada —o que aun no hubiera pasado por Adobe— no tenia camino
    # a la entrega: se quedaba sin 1,15x y sin -14 LUFS, o peor, con la entrega
    # vieja en su sitio. Un paso que solo sabe terminar el caso bueno deja el
    # malo a medias y en silencio. El audio del corte esta en sincronia por
    # construccion, asi que sale pieza correcta con la voz sin limpiar:
    # `integrar` ya dijo por que no sustituyo, y esto no lo tapa, lo entrega.
    if pedidos and not a.ver:
        # **La aceleracion va ANTES de la musica, no despues.**
        #
        # Jaime: *«la velocidad vamos a aumentarla a 1.15»*. Acelerar el
        # master ya mezclado subiria tambien la musica un 15 %, y una pista
        # acelerada suena a pista acelerada: cambia el tono y el caracter de
        # algo que se eligio como es. Se acelera la pieza con su voz, y la
        # musica entra despues a su velocidad natural sobre el resultado.
        for n in pedidos:
            _acelerar(n)
        print(f"\nmasterizando {len(pedidos)}: {pedidos}"
              + (f"  ·  con voz limpia: {hechos}" if hechos != pedidos else ""))
        # **Y si el nivelado no corre, se dice.** Esto iba sin `check` y sin
        # mirar la salida: las cinco piezas salieron a -21 LUFS —siete por
        # debajo del objetivo— y el paso termino con exito. `musica.sh` ademas
        # devuelve 0 aunque no encuentre el fichero, asi que el codigo de
        # salida solo no basta: se comprueba que haya dicho algo de cada pieza.
        r = subprocess.run([rutas.interprete(), "scripts/musica.sh",  # C-548
                            *[str(x) for x in pedidos]],
                           capture_output=True, text=True, encoding="utf-8")
        print(r.stdout or "", end="")
        if r.stderr:
            print(r.stderr.strip()[:400])
        # **Y se mira la ENTREGA, que es lo que el abre.** El nivelado ya se
        # comprobaba aqui —leccion 51, *medir la entrega, no suponerla*— y la
        # sincronia no, aunque entre el wav que entra y el fichero que sale hay
        # la mezcla, la aceleracion y dos pasadas de nivelado.
        sincronia.informe(pedidos, VELOCIDAD)
        dichas = sum(1 for n in pedidos if f"R{n} " in (r.stdout or ""))
        if r.returncode or dichas < len(pedidos):
            raise SystemExit(
                f"\nPARA: el nivelado contesto por {dichas} de {len(pedidos)}"
                f" pieza(s) (codigo {r.returncode}). Sin el, la entrega se queda"
                f" al nivel del corte —medido: -21 LUFS contra -14— y eso no se"
                f" ve en el video, se oye al publicarlo.")


if __name__ == "__main__":
    main()

