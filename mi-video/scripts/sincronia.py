"""Poner la voz encima de la imagen, no al lado.

Jaime, oyendo la primera entrega del lote: *«r-01 tiene el audio desfasado del
video»*.

## Por que existe este fichero

`voz-limpia.py` sabe **integrar** la voz que vuelve de Adobe; `desfase.py` sabe
**medir** cuanto va una pista por delante o por detras de otra. Faltaba el trozo
de en medio: decidir cuanto hay que moverla y moverla. Estaba escrito dentro de
`voz-limpia.py` y lo dejo en 340 lineas, cuarenta por encima del techo — que es
la senal de que ahi habia una responsabilidad de mas, no de que sobrara sitio.

## Que iba mal

`_corresponde()` cruza las envolventes con `mode="full"` y se queda con **el
pico**. El pico dice si es el mismo audio; **donde cae** dice si esta en su
sitio, y ese numero se descartaba en la misma linea en que se calculaba. La
misma voz movida 2,4 s puntua `1,00`: encaja perfecta, en otro momento.

Medido el 4 de septiembre sobre lo entregado, seis de siete iban movidas:

    R1  +2,40 s      R5  -0,48 s
    R2  +1,86 s      R3  -0,22 s
    R4  +1,70 s      R6  -0,22 s
    R7  -0,08 s  (la unica en su sitio)

Dos causas y la misma cura. Las grandes son voz exportada de un corte ANTERIOR y
mas largo, con material de sobra por delante. Las pequenas son que la
herramienta de limpieza se come el silencio de entrada, y con el se lleva el
punto de partida.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import desfase  # noqa: E402

#: Un frame a 30 fps. Por debajo de esto la imagen no tiene donde ensenar el
#: desfase; por encima si, y a partir de una decima se oye.
AL_FRAME = 0.034

#: Cuantas veces se intenta. Una sola pasada dejo a reel-05 en +0,28 s: el pico
#: de la primera medida es un compromiso entre el arranque y el resto, y una vez
#: casado el grueso la segunda medida ya ve el residuo limpio. Tres es de sobra
#: —las siete convergen en dos— y pone un final a la cuenta.
INTENTOS = 3

#: La banda donde vive la voz. **La medida se hace SOLO aqui**, y no es un
#: detalle: la entrega lleva musica, y una cama de cuerdas mete su propia
#: envolvente en el cruce. Con la pieza entera reel-05 daba +0,28 s de mediana
#: con nueve ventanas; con la banda de voz da lo mismo, pero ahora se sabe que
#: es la voz quien lo dice.
BANDA = "highpass=f=300,lowpass=f=3000"

#: Deriva a partir de la cual se corrige el ritmo, como fraccion. 0,2 % sobre una
#: pieza de 80 s son 160 ms de punta a punta: justo donde se empieza a ver.
RITMO_MIN = 0.002

#: Y hasta donde puede llegar antes de dejar de ser deriva. La causa conocida es
#: el redondeo a frame entero de cada tramo: veinticuatro tramos por 33 ms sobre
#: un minuto son **1,3 %** en el peor caso, y lo medido en las siete va de 0 a
#: 1,33 %. Por encima del 3 % ya no es redondeo — es que la pista es de otra
#: cosa, y estirarla un 15 % para que cuadre es exactamente lo que dejo a
#: reel-07 en 53,6 s de los 63 que dura. Se dice, no se estira.
RITMO_MAX = 0.03

#: Lo peor que se admite, ya alineada. Dos frames y medio: la norma de emision
#: (ITU-R BT.1359) da por invisible hasta 45 ms de adelanto y 125 ms de retraso,
#: y esto lo deja dentro por los dos lados.
PEOR = 0.09

#: Y se mide en el percentil 80, no en el maximo. Es la misma leccion que la
#: pendiente por Theil-Sen, otra vez: una ventana sola que engancha en una frase
#: repetida se va dos segundos, y con el maximo esa ventana tumbaba reel-01
#: (0,68), reel-04 (2,04) y reel-07 (2,58) — las tres con las otras ocho
#: ventanas en cero. Un desfase de verdad mueve todas las ventanas, no una.
CUANTIL = 0.8


def _banda(src, tempo=None):
    """La envolvente de `src` en la banda de la voz, a 50 muestras por segundo.

    `tempo` devuelve la pista a su velocidad natural antes de medir, que es lo
    que hace falta para mirar una entrega ya acelerada contra su corte.
    """
    import numpy as np

    tmp = os.path.join(os.environ.get("TMPDIR", "F:/tmp-video"), "_banda.wav")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    af = BANDA + (f",atempo={tempo:.6f}" if tempo else "")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", af,
                    "-vn", "-ac", "1", "-ar", "1000", tmp], check=True)
    import wave
    with wave.open(tmp) as w:
        x = np.frombuffer(w.readframes(w.getnframes()),
                          dtype=np.int16).astype(float)
    m = len(x) // 20 * 20
    if not m:
        return None
    e = np.abs(x[:m]).reshape(-1, 20).mean(1)
    return e - e.mean()


def _cuanto(f):
    """Lo que dura un fichero, en segundos. 0 si no se puede leer."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", f],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def entregada(n, velocidad=1.0):
    """El peor desfase de la ENTREGA contra su corte. `None` si no se pudo medir.

    ## Por que se mide aqui y no en la entrada

    Todo lo demas de este fichero mira el WAV que va a entrar. Esto mira **el
    fichero que Jaime abre**, que es otra pregunta: entre los dos hay el mezclado
    con los efectos, la aceleracion y dos pasadas de nivelado, y cualquiera de
    los tres puede mover la voz sin que nadie se entere.

    Es la leccion 51 del proyecto —*medir la entrega, no suponerla*— que ya
    estaba aplicada al volumen y no a la sincronia. El coste de no tenerla se
    pago hoy tres veces: las seis piezas se rehicieron tres veces porque yo
    media el desfase a mano, por fuera, y una de esas veces con la mediana, que
    escondio que reel-04 iba dos segundos corrido en su primer tercio.

    Una comprobacion que vive fuera del proceso no es una comprobacion: es una
    costumbre, y se pierde en cuanto hay prisa.
    """
    import numpy as np

    corte, pieza = referencia(n), f"out/entrega/reel-R{n}.mp4"
    if not (os.path.exists(corte) and os.path.exists(pieza)):
        return None
    # **La velocidad se mide, no se supone.** El parametro dice a que ritmo
    # DEBERIA ir la entrega, y una pieza que todavia no ha pasado por el paso de
    # acelerar va a 1,0 — medirla como si fuera 1,15x da un desfase inventado.
    # Paso con reel-02 recien renderizada: 5,47 s de desfase declarados sobre un
    # fichero que estaba perfectamente en su sitio, solo que sin acelerar.
    #
    # Se compara la duracion real contra la del corte y se usa lo que salga, con
    # el declarado como red por si alguna de las dos no se puede leer. Una
    # comprobacion que grita donde no hay problema se deja de mirar.
    # **La velocidad se mide, no se supone.** El parametro dice a que ritmo
    # DEBERIA ir la entrega, y una pieza que todavia no ha pasado por el paso de
    # acelerar va a 1,0: medirla como si fuera 1,15x da un desfase inventado.
    # Paso con reel-02 recien renderizada — 5,47 s declarados sobre un fichero
    # que estaba en su sitio, solo que sin acelerar.
    #
    # La proporcion de duraciones **elige entre los dos ritmos posibles**; no es
    # el ritmo. Usarla tal cual fue el segundo intento fallido: las colas mudas
    # no son iguales en los dos ficheros, asi que 85,45 contra 86,00 da 0,994 y
    # con eso se corrige un 0,6 % que no existe — 0,32 s de desfase inventado,
    # menos que antes y falso igual. Los dos candidatos estan a 15 puntos uno de
    # otro, asi que basta con quedarse con el mas cercano.
    real = _cuanto(corte), _cuanto(pieza)
    if all(real):
        medida = real[0] / real[1]
        velocidad = min((1.0, velocidad), key=lambda v: abs(medida - v))
    p = perfil(corte, pieza, tempo=1.0 / velocidad if velocidad != 1.0 else None)
    if len(p) < 4:
        return None
    return float(np.quantile(sorted(abs(o) for _, o in p), CUANTIL))


def perfil(ref, wav, paso=8, tempo=None):
    """El desfase medido en varios puntos de la pieza: `[(segundo, desfase)]`.

    **Una sola medida global no basta**, y por eso existe esto. `desfase.entre`
    cruza la pista entera y devuelve el desfase que mejor cuadra en promedio; si
    la voz ademas corre a otro paso, ese promedio es el punto medio de una recta
    y deja los dos extremos fuera. Medido en reel-05 despues de alinear: +0,62 s
    al principio, -0,22 s al final, y la medida global decia cero.
    """
    import numpy as np

    a_, b_ = _banda(ref), _banda(wav, tempo)
    if a_ is None or b_ is None:
        return []
    fuera, M, L = [], 300, 400          # 6 s de busqueda, 8 s de ventana
    for t in range(3, int(min(len(a_), len(b_)) / 50) - 10, paso):
        s = t * 50
        lo = max(0, s - M)
        x, y = a_[s:s + L], b_[lo:s + L + M]
        if len(y) < len(x) + 1 or len(x) < L:
            continue
        c = np.correlate(y, x, "valid")
        k = int(np.argmax(c))
        if c[k] / (np.abs(c).mean() + 1e-9) >= 3.5:
            fuera.append((t, (k - (s - lo)) * 0.02))
    return fuera


def ritmo(puntos):
    """Cuanto corre de mas la voz, como factor de tempo. 1,0 = al mismo paso.

    La pendiente sale por **Theil-Sen** —la mediana de las pendientes de todos
    los pares— y no por minimos cuadrados. No es purismo: una sola ventana que
    engancha en una frase repetida se va dos segundos, y con `polyfit` esa
    ventana sola daba derivas de +5 % y +7 % en reel-04 y reel-07, que sobre un
    minuto serian tres segundos de desvio que nadie ha oido. La mediana la
    ignora sin tener que decidir cual era la mala.
    """
    import numpy as np

    if len(puntos) < 4:
        return 1.0
    pend = [(o2 - o1) / (t2 - t1)
            for i, (t1, o1) in enumerate(puntos)
            for (t2, o2) in puntos[i + 1:] if t2 != t1]
    return 1.0 + float(np.median(pend)) if pend else 1.0


def acompasar(wav: str, factor: float):
    """Estira o encoge la voz al paso del corte, **sin tocarle el tono**.

    `rubberband` y no `atempo`: sobre voz, `atempo` reasigna trozos de forma de
    onda y deja el timbre metalico — es la misma leccion que `render-hook.mjs`
    aprendio con *«la voz se escucha robotica»*. Aqui ademas el ajuste es del
    orden del 1 %, o sea inaudible si se hace bien y evidente si se hace mal.
    """
    fuera = os.path.join(
        os.environ.get("TMPDIR", "F:/tmp-video"),
        os.path.basename(wav).replace(".wav", "-acompasada.wav"))
    os.makedirs(os.path.dirname(fuera), exist_ok=True)
    try:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav,
                        "-af", f"rubberband=tempo={factor:.5f}", fuera],
                       check=True)
    except subprocess.CalledProcessError:
        return None
    return fuera if os.path.exists(fuera) else None


def referencia(n):
    """Contra que se mide: **el corte, no el render**.

    `voz-limpia.integrar()` termina con `os.replace(tmp, video)`, o sea que
    reescribe `out/reels/reel-RN.mp4` con la voz ya sustituida. Medir contra ese
    fichero es medir la pista contra si misma: da cero siempre, tambien cuando
    va movida dos segundos. `public/reel-NN.mp4` es el corte tal como salio de
    `render-hook.mjs`, con el sonido de la cinta, y nadie lo reescribe: ahi la
    imagen y el sonido son el mismo instante por construccion.
    """
    corte = f"public/reel-{n:02d}.mp4"
    return corte if os.path.exists(corte) else f"out/reels/reel-R{n}.mp4"


def retraso(ref, wav):
    """Cuanto llega TARDE `wav` respecto a `ref`, en segundos. `None` si no se pudo.

    Positivo: va por detras y hay que quitarle ese trozo por delante.
    Negativo: va por delante y hay que meterle silencio al principio.

    `desfase.entre(a, b)` devuelve lo que hay que **sumarle al reloj de `b`**
    para leerlo en el de `a`, que es el mismo numero con el signo contrario. Se
    invierte aqui, una vez, para que el signo diga **lo que hay que hacer** y no
    lo que pasa: positivo, sobra por delante y se quita.

    El signo estuvo invertido lo suficiente para verlo: reel-01 se rellenaba
    hasta 98 s en vez de recortarse a 93. Un signo al reves no falla, hace justo
    el doble de dano, y por eso la direccion se comprobo contra las siete piezas
    medidas por fuera antes de dar el arreglo por bueno.
    """
    m = desfase.entre(ref, wav)
    if not isinstance(m, dict) or "desfase_s" not in m:
        return None
    return -m["desfase_s"]


def mover(wav: str, cuanto: float, marca: str = "alineado"):
    """Corre la pista `cuanto` segundos y devuelve el fichero nuevo.

    **Se mueve, no se recorta a la duracion.** Es la distincion que faltaba:
    `_sin_cola_muda()` quita de la COLA lo que sobra, y en reel-01 lo que sobraba
    estaba en la CABEZA. Salia la peor combinacion posible — la pista duraba lo
    justo, pasaba las dos guardas, y sonaba 2,4 s corrida de principio a fin con
    el final cortado.
    """
    fuera = os.path.join(
        os.environ.get("TMPDIR", "F:/tmp-video"),
        os.path.basename(wav).replace(".wav", f"-{marca}.wav"))
    os.makedirs(os.path.dirname(fuera), exist_ok=True)
    if cuanto > 0:
        orden = ["ffmpeg", "-v", "error", "-y", "-ss", f"{cuanto:.3f}",
                 "-i", wav, fuera]
    else:
        orden = ["ffmpeg", "-v", "error", "-y", "-i", wav,
                 "-af", f"adelay={int(round(-cuanto * 1000))}:all=1", fuera]
    try:
        subprocess.run(orden, check=True)
    except subprocess.CalledProcessError:
        return None
    return fuera if os.path.exists(fuera) else None


def encajar(n, wav):
    """Deja `wav` encima de la imagen de la pieza `n`.

    Devuelve `(fichero, movido_s, ventanas, motivo)`. `ventanas` es cuantos
    puntos de la pieza se pudieron medir: con cuatro o mas, la comprobacion del
    perfil ya prueba que el contenido es el mismo —una pista de otro montaje no
    engancha en nueve sitios— y quien llama puede ahorrarse el parecido global.

    **Se repite hasta que entra.** No es terquedad: la primera medida cruza la
    pista entera y su pico es un compromiso entre el arranque y el resto, asi
    que con un desfase grande deja un residuo. Medido en reel-05: una pasada la
    dejaba en +0,28 s, dos la ponen en cero.
    """
    ref = referencia(n)
    wav, total, motivo = _pegar(ref, wav)
    if motivo:
        return wav, total, 0, motivo
    # **El paso se mide DESPUES de casar el grueso, no antes.** Medirlo sobre una
    # pista corrida dos segundos fue el intento anterior y salio al reves: las
    # ventanas enganchan donde pueden, la mediana de pendientes se va, y a
    # reel-07 lo dejo en 53,6 s de los 63 que dura. Con el arranque ya en su
    # sitio, lo que queda en el perfil es deriva y solo deriva.
    #
    # De donde sale: `exportar()` arma la voz concatenando tramos de la cinta en
    # segundos exactos, y `render-hook.mjs` arma el corte recodificando esos
    # mismos tramos redondeados a frame entero. Sobre veinticuatro tramos el
    # redondeo se suma — medido en reel-01: el plan dice 93,36 s y el fichero
    # mide 93,07.
    paso = ritmo(perfil(ref, wav))
    if RITMO_MIN < abs(paso - 1.0) <= RITMO_MAX:
        acompasada = acompasar(wav, paso)
        if acompasada:
            wav = acompasada
            wav, mas, motivo = _pegar(ref, wav)
            total += mas
    if motivo:
        return wav, total, 0, motivo
    # **Y se comprueba lo que se prometio, en los mismos puntos donde se medio.**
    #
    # Esta es la verificacion que vale, y es mas fuerte que la del parecido
    # global: nueve ventanas repartidas por la pieza tienen que caer todas
    # dentro de un par de frames. Una pista de otro montaje no pasa esto ni por
    # casualidad — con el pico global si pasaba, que es como reel-01 llego a la
    # entrega con `parecido 1,00` y dos segundos y medio de retraso.
    p = perfil(ref, wav)
    if len(p) >= 4:
        import numpy as np
        peor = float(np.quantile(sorted(abs(o) for _, o in p), CUANTIL))
        if peor > PEOR:
            return wav, total, len(p), (
                f"despues de alinear sigue habiendo {peor:.2f}s de desfase"
                f" en la mayor parte de la pieza")
    return wav, total, len(p), None


def _pegar(ref, wav):
    """Casa el arranque, repitiendo hasta que entre en un frame."""
    total = 0.0
    for vuelta in range(INTENTOS):
        r = retraso(ref, wav)
        if r is None:
            return wav, total, "no se pudo medir el desfase"
        if abs(r) <= AL_FRAME:
            return wav, total, None
        movido = mover(wav, r, f"al{vuelta}")
        if not movido:
            return wav, total, f"va {r:+.2f}s del corte y no se pudo mover"
        wav, total = movido, total + r
    r = retraso(ref, wav)
    if r is not None and abs(r) > AL_FRAME:
        return wav, total, (f"sigue {r:+.2f}s del corte despues de"
                            f" {INTENTOS} intentos")
    return wav, total, None


def informe(piezas, velocidad=1.0):
    """Dice, pieza por pieza, si lo entregado esta en su sitio.

    Va al final del paso de audio a proposito: es lo ultimo que se sabe antes de
    que el fichero salga, y lo unico que mira **lo que se entrega** y no lo que
    entro. Hoy las seis piezas se rehicieron tres veces porque este numero lo
    calculaba yo por fuera, a mano — y una de esas veces con la mediana, que
    escondio que reel-04 iba dos segundos corrido en su primer tercio.
    """
    import registro

    for n in piezas:
        d = entregada(n, velocidad)
        if d is None:
            print(f"R{n}  sincronia: no se pudo medir")
        elif d > PEOR:
            print(f"R{n}  DESFASADA {d:.2f}s contra su corte — no la entregues")
            registro.aviso("sincronia", "entrega desfasada",
                           detalle=f"R{n}: {d:.2f}s", eco=True)
        else:
            print(f"R{n}  sincronia {d:.2f}s  ·  en su sitio")
