"""Rehacer el AUDIO de una pieza aprobada, sin tocar su imagen.

Jaime, después de una noche en la que cada corrección de sonido le devolvía un
vídeo distinto: *«de entrada reconstruye los videos, no quiero otros videos,
quiero esos que vi»* y *«los quiero corregidos»*.

## El agujero que cierra

Para cambiar el nivel de la música había que volver a `musica.sh`, que parte del
**render**. Y si el corte se había movido —y se mueve: `costuras.py` no es
idempotente y desplaza los bordes 0,12 s por corrida— el render de hoy ya no era
el de ayer, así que la corrección de sonido devolvía otro montaje.

O sea que no existía la operación más obvia del oficio: **esta imagen está
aprobada, arregla sólo lo que se oye**. Sin ella, cualquier retoque de audio
arrastraba un re-render, y el re-render arrastraba otra pieza.

Aquí el vídeo se copia tal cual (`-c:v copy`): ni un frame se recodifica. Lo
único que se rehace es la pista.

## Cómo se decide el nivel de la música

Por la **distancia a su voz medida en el resultado**, no por un número fijo.
Medido el 5 de septiembre con `MUSI = -15` para las siete, la separación real
salió entre 2,3 y 19,7 dB: con la obra de reel-06 la cama se le subía encima
—*«R6 lastima, la música ahora opaca»*— y con la de reel-03 desaparecía —*«la
música no se escucha»*—. Un solo número no puede servir a siete obras distintas.

`OBJETIVO` son los ~14 dB de reel-04, que es la que no ha levantado queja.

    python scripts/remezclar.py 1          # ver qué haría
    python scripts/remezclar.py 1 --hazlo  # dejarlo hecho
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cama  # noqa: E402
from beats import VELOCIDAD  # noqa: E402

#: El máster aprobado: la copia de lo que Jaime miró, traída de Drive.
APROBADO = "out/entregado-19h/reel-R{n}.mp4"
#: La voz CRUDA. Sirve para medir —la envolvente es la misma— pero **no para
#: mezclar**: `out/audio-voz/{s}-voz.wav` es byte a byte el export sin tratar.
VOZ = "out/audio-voz/{s}-voz.wav"
EFECTOS = "out/audio-voz/reel-R{n}-efectos.wav"
MUSICA = "public/musica/{s}.mp3"
SALIDA = "out/entrega/reel-R{n}.mp4"

#: Cuántos dB por debajo de su voz tiene que quedar la cama, medido en la
#: entrega. **Se lee de `src/brand/cama.json`, que es donde vive.**
#:
#: Estaba escrito aquí a mano y ésa es la avería de siempre: `cama.json`
#: declaraba `objetivo_db` y **no lo leía nadie**, así que corregir la
#: separación en el sitio que el propio fichero anuncia como único no cambiaba
#: la mezcla. Medido el 5 de septiembre: el fichero decía 16 y este bucle seguía
#: apuntando a 14 — dos decibelios que existían sólo en el documento.
OBJETIVO = float(cama.leer()["objetivo_db"])

#: Cuánto puede desviarse antes de volver a intentarlo. **0,8, no 1,5**: con
#: margen ancho el bucle se conformaba con 14,9 y el fichero entregado medía
#: 16,2 — dentro de la tolerancia declarada y fuera de lo que suena bien.
MARGEN = 0.8

#: Cuanto puede diferir la voz limpia de la cruda para darla por la misma toma.
#: Adobe devuelve la misma duracion; medio segundo es margen de contenedor.
TOLERA = 0.5

#: Cuántas veces se prueba. Tres bastan: cada vuelta corrige el error medido, y
#: si a la tercera sigue fuera es que algo más está mal —el stem no corresponde,
#: la obra no tiene silencios— y entonces **no se entrega**, que es lo que hay
#: que hacer con una pieza que no se puede comprobar.
INTENTOS = 3

#: La talla de frecuencias que ya usa `musica.sh`, y por el mismo motivo: Jaime
#: pidió *«bajar el volumen de las frecuencias que interfieren con la voz»*, no
#: ponerle un efecto encima.
TALLA = ("equalizer=f=160:t=o:w=1.2:g=-20,equalizer=f=400:t=o:w=1.3:g=-20,"
         "equalizer=f=700:t=o:w=1.1:g=-18,equalizer=f=1600:t=o:w=1.4:g=-23")


def voz_de(slug):
    """La voz que va a la mezcla: la limpia si corresponde, la cruda si no.

    **Esto estaba mal y se le devolvio a Jaime sin la voz de Adobe.** La mezcla
    tomaba `out/audio-voz/{slug}-voz.wav`, que es el export CRUDO —el mismo que
    se le manda a limpiar—, asi que remezclar una pieza para arreglarle la
    musica le deshacia la limpieza de voz por la que habia pasado a mano.

    La limpia vive en `out/audio-puro/{slug}-voz-*.wav` y **tiene que cuadrar en
    duracion** con la cruda: si es de otro montaje entra desfasada, y una voz
    corrida es peor que una voz con eco.
    """
    import glob

    crudo = VOZ.format(s=slug)
    hay = [f for f in glob.glob(f"out/audio-puro/{slug}-voz-*.wav")
           if "-cola" not in f]
    if not (hay and os.path.exists(crudo)):
        return crudo, False
    d = dura(crudo)
    for f in sorted(hay, key=os.path.getmtime, reverse=True):
        if abs(dura(f) - d) < TOLERA and _mismo_corte(crudo, f):
            return f, True
    return crudo, False


def _mismo_corte(a, b):
    """¿Los dos wav dicen lo mismo? Se compara la FORMA, no la duración.

    **Durar igual no es ser el mismo.** El stem limpio de reel-02 medía 85,85 s,
    exactamente lo que el crudo de hoy, y era de otro corte: dos montajes de la
    misma pieza pueden coincidir al segundo sin parecerse en nada. Con él la
    separación de la cama salía **2,3 dB y no se movía al cambiar el nivel** —el
    síntoma de C-243 por dentro—, mientras que con el crudo daba 34,2.

    Y no es sólo la medida: `mezclar()` usa esta misma función para elegir qué
    voz entra en la pieza, así que un falso positivo aquí entrega la voz de otro
    montaje encima del vídeo de hoy.

    Se comparan las envolventes en tramos de 0,3 s. Donde uno calla el otro
    calla: si la correlación no llega a 0,8, son montajes distintos.
    """
    import numpy as np

    def env(f):
        crudo = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", f, "-vn", "-ac", "1", "-ar", "8000",
             "-f", "s16le", "-"], capture_output=True).stdout
        x = np.frombuffer(crudo, dtype=np.int16).astype(float) / 32768
        m = len(x) // 2400 * 2400
        return np.sqrt((x[:m].reshape(-1, 2400) ** 2).mean(1)) if m else None

    ea, eb = env(a), env(b)
    if ea is None or eb is None:
        return False
    k = min(len(ea), len(eb))
    if k < 20:
        return False
    ea, eb = ea[:k], eb[:k]
    if ea.std() < 1e-6 or eb.std() < 1e-6:
        return False
    return float(np.corrcoef(ea, eb)[0, 1]) > 0.8


def _correr(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def dura(f):
    r = _correr(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", f])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def distancia(mp4, voz):
    """Cuántos dB separan la cama de su voz, medido en el fichero entregado."""
    import numpy as np

    def marco(f, tempo=None):
        af = ["-af", f"atempo={tempo}"] if tempo else []
        crudo = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", f] + af
            + ["-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
            capture_output=True).stdout
        x = np.frombuffer(crudo, dtype=np.int16).astype(float) / 32768
        n, m = 2400, len(np.frombuffer(crudo, dtype=np.int16)) // 2400 * 2400
        if not m:
            return np.array([])
        return 20 * np.log10(np.sqrt((x[:m].reshape(-1, n) ** 2).mean(1)) + 1e-9)

    # **Los dos ficheros tienen que ser del MISMO montaje, o no se mide.**
    #
    # El metodo busca los huecos en la voz y lee ahi el nivel de la entrega, por
    # indice. Si la voz es de otro corte, esos indices caen donde el esta
    # hablando y sale un numero plausible que no describe nada. Medido en
    # reel-07 el 5-9-2026: el stem duraba 88,51 s contra los 80,96 equivalentes
    # de la entrega —siete segundos y medio— y la medida daba 2,4 dB de
    # separacion **con la musica a -60 LUFS**, o sea sin musica ninguna. Bajar
    # el nivel no movia el numero, y la guarda gritaba «FUERA» en cada corrida.
    #
    # Es C-233 otra vez: intersecar dos medidas de cosas distintas no falla, da
    # un resultado plausible. Aqui se prefiere no contestar.
    # La comparacion es por EXCESO, no por diferencia. La entrega puede durar
    # mas que la voz sin que pase nada —lleva la tarjeta del CTA y la cola muda,
    # y ahi no habla nadie: en reel-01 son catorce segundos legitimos—, pero la
    # voz NO puede durar mas que la pieza: si sobra, es de otro corte. Medir la
    # diferencia en los dos sentidos hacia que la guarda se negara en cuatro de
    # las siete por llevar CTA, que es justo lo contrario de lo que hace falta.
    # **El reloj de la referencia se deduce de su duracion, no se supone.**
    #
    # Habia una sola forma prevista —un stem del bruto, sin acelerar— y por eso
    # la entrega se ralentizaba para comparar. Pero la referencia BUENA es
    # `out/entrega/.sin-musica/reel-RN.mp4`, que es literalmente la voz que
    # entro en la mezcla: mismo corte, mismo reloj, sin musica. Con el stem,
    # cinco de las siete contestaban «no se puede medir» —el stem es de otro
    # montaje en cuanto se recorta algo— y `cama.json` acababa con numeros
    # «medidos» que no se podian volver a medir.
    dv, dm = dura(voz), dura(mp4)
    if abs(dv - dm) <= max(1.0, dm * 0.03):
        tempo = None                      # ya viene al reloj del montaje
    elif abs(dv - dm * VELOCIDAD) <= max(1.0, dm * 0.05):
        tempo = 1 / VELOCIDAD             # viene del bruto, sin acelerar
    else:
        # **Ni un reloj ni el otro: la referencia es de OTRO montaje.** Aqui se
        # prefiere no contestar (C-243): un numero plausible sacado de indices
        # que caen donde el esta hablando describe otra cosa, y en reel-07 dio
        # 2,4 dB de separacion con la musica a -60 LUFS, o sea sin musica.
        return None
    a, b = marco(voz), marco(mp4, tempo=tempo)
    k = min(len(a), len(b))
    if k < 20:
        return None
    a, b = a[:k], b[:k]
    # Los huecos donde él no habla son donde se oye la cama sola.
    huecos = a < -45
    if huecos.sum() < 5:
        return None
    return float(np.percentile(b, 90) - np.median(b[huecos]))


def base_de(n):
    return APROBADO.format(n=n)


def mezclar(n, ganancia, destino):
    """Vídeo tal cual + voz + efectos + música a esa ganancia."""
    s = f"reel-{n:02d}"
    voz, limpia = voz_de(s)
    if not limpia:
        print("     (con la voz cruda: no hay limpia que cuadre)")
    efe = EFECTOS.format(n=n)
    mus = MUSICA.format(s=s)
    # **Un stem de efectos que no cuadra NO entra.**
    #
    # Los efectos son el 1-2 % de la pista, pero van clavados a un frame: si el
    # stem es de otro montaje —reel-02 sobra 1,2 s, reel-07 son 63 s contra los
    # 88 que hacen falta— cada golpe cae fuera de sitio, y eso no suena a que
    # falte algo: suena a error. Se prefiere la pieza sin ellos y se dice.
    hay_mus = os.path.exists(mus)
    hay_efe = os.path.exists(efe) and abs(dura(efe) - dura(base_de(n)) * VELOCIDAD) < 0.6
    if os.path.exists(efe) and not hay_efe:
        print("     (sin efectos: su stem es de otro montaje)")
    largo = dura(APROBADO.format(n=n))
    entradas = ["-i", APROBADO.format(n=n), "-i", voz]
    partes = [f"[1:a]atempo={VELOCIDAD}[v]"]
    mezcla = "[v]"
    if hay_efe:
        entradas += ["-i", efe]
        partes.append(f"[2:a]atempo={VELOCIDAD}[e]")
        partes.append("[v][e]amix=inputs=2:normalize=0:duration=first[ve]")
        mezcla = "[ve]"
    if hay_mus:
        entradas += ["-i", mus]
        i = 3 if hay_efe else 2
        # **La musica se recorta a la pieza, y la mezcla dura lo que la voz.**
        #
        # Sin las dos cosas el mp3 entra entero y `amix` estira la pista hasta la
        # mas larga: medido, reel-01 salio con **370 s** de audio sobre 81 s de
        # video, y el nivelado midio sobre esos 370 s. El video estaba perfecto y
        # el fichero era inservible — un fallo que no se ve mirando la imagen.
        partes.append(f"[{i}:a]atrim=0:{largo:.3f},volume={ganancia:.1f}dB,"
                      f"{TALLA}[m]")
        partes.append(f"{mezcla}[m]amix=inputs=2:normalize=0:duration=first[mix]")
        mezcla = "[mix]"
    # **`loudnorm` no es un limitador**, y su `TP` es una intencion: reel-01
    # salio a -0,3 dBTP con TP=-1,5 puesto. El limitador va detras y en 192 kHz,
    # que es donde se cazan los picos entre muestras — el mismo remate que hace
    # `musica.sh`, por el mismo motivo: un pico por encima de -1 lo distorsiona
    # el codec de la plataforma, y eso no se oye aqui, se oye publicado.
    partes.append(f"{mezcla}loudnorm=I=-14:TP=-1.5:LRA=11,aresample=192000,"
                  f"alimiter=limit=-1.5dB:level=disabled,aresample=48000[out]")
    return _correr(["ffmpeg", "-y", "-v", "error", *entradas,
                    "-filter_complex", ";".join(partes),
                    "-map", "0:v", "-map", "[out]", "-shortest",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", destino])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--hazlo", action="store_true")
    a = ap.parse_args()
    tmp = os.environ.get("TMPDIR", "F:/tmp-video")
    os.makedirs(tmp, exist_ok=True)
    import rutas
    for n in (a.reels or rutas.piezas()):
        s = f"reel-{n:02d}"
        # **La misma voz que se mezcla es la que se mide.** Aqui se cogia la
        # CRUDA y `mezclar()` usaba la limpia: dos referencias distintas, dos
        # numeros distintos para el mismo fichero —14,2 dentro del proceso,
        # 15,57 fuera— y me pase media hora buscandolo en `os.replace`.
        #
        # Una medida contra otra referencia no es una medida imprecisa: es otra
        # medida.
        base, voz = APROBADO.format(n=n), voz_de(s)[0]
        if not (os.path.exists(base) and os.path.exists(voz)):
            print(f"  R{n}: falta el aprobado o su voz")
            continue
        hoy = distancia(base, voz)
        if hoy is None:
            print(f"  R{n}: no se pudo medir la cama")
            continue
        falta = OBJETIVO - hoy
        print(f"  R{n}: la cama esta a {hoy:.1f} dB de su voz"
              f"  (objetivo {OBJETIVO:.0f}, corrige {-falta:+.1f} dB)")
        if not a.hazlo:
            continue
        # **Se mide y se corrige, no se calcula de una vez.**
        #
        # El primer intento tomaba la diferencia medida en la mezcla VIEJA y la
        # aplicaba como delta al mp3 crudo. No es el mismo punto de partida: la
        # música dentro del máster ya venía atenuada y tallada, así que el mismo
        # −2,8 dB que sonaba razonable dejó reel-06 a 36 dB, o sea muda. La
        # ganancia sólo se puede saber probándola.
        #
        # Es el mismo bucle que `musica.sh` ya hace con el volumen —masterizar,
        # medir, corregir— y por el mismo motivo: medir la entrega, no suponerla.
        # **Se mide SIEMPRE el fichero entregado, no el temporal.**
        #
        # El bucle probaba sobre el temporal y sólo al final movía el resultado.
        # Con reel-01 dio 14,2 dB recién movido y 15,57 en cualquier lectura
        # posterior —estable, tres veces—: leer un fichero justo después de
        # `os.replace` no devuelve lo mismo que leerlo después. Con margen ancho
        # eso pasaba por bueno y se entregaba 1,4 dB fuera.
        #
        # Ahora cada vuelta escribe el destino y mide el destino. Es más lento y
        # es la única forma de que el número que sale por pantalla sea el del
        # fichero que se publica — que es la regla de siempre aquí: medir la
        # entrega, no suponerla.
        destino, tmpf = SALIDA.format(n=n), os.path.join(tmp, f"r{n}.mp4")
        gan, nueva = 0.0, None
        for _intento in range(INTENTOS):
            r = mezclar(n, gan, tmpf)
            if r.returncode or not os.path.exists(tmpf):
                print(f"     no se pudo mezclar: {r.stderr.strip()[:200]}")
                break
            os.replace(tmpf, destino)
            nueva = distancia(destino, voz)
            if nueva is None:
                break
            print(f"     con {gan:+.1f} dB la entrega mide {nueva:.1f} dB")
            if abs(nueva - OBJETIVO) <= MARGEN:
                break
            gan += nueva - OBJETIVO
        if nueva is None:
            continue
        print(f"     -> {destino}  {nueva:.1f} dB  (imagen sin tocar)"
              + ("" if abs(nueva - OBJETIVO) <= MARGEN else "  · FUERA"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
