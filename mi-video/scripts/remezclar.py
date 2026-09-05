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

from beats import VELOCIDAD  # noqa: E402

#: El máster aprobado: la copia de lo que Jaime miró, traída de Drive.
APROBADO = "out/entregado-19h/reel-R{n}.mp4"
VOZ = "out/audio-voz/{s}-voz.wav"
EFECTOS = "out/audio-voz/reel-R{n}-efectos.wav"
MUSICA = "public/musica/{s}.mp3"
SALIDA = "out/entrega/reel-R{n}.mp4"

#: Cuántos dB por debajo de su voz tiene que quedar la cama, medido en la
#: entrega. 14 son los de reel-04, la única que no ha levantado queja: a 5 le
#: «lastima» y a 19 «no se escucha».
OBJETIVO = 14.0

#: Cuánto puede desviarse antes de volver a intentarlo.
MARGEN = 1.5

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

    a, b = marco(voz), marco(mp4, tempo=1 / VELOCIDAD)
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
    voz, efe = VOZ.format(s=s), EFECTOS.format(n=n)
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
    entradas = ["-i", APROBADO.format(n=n), "-i", voz]
    partes = [f"[1:a]atempo={VELOCIDAD}[v]"]
    mezcla = "[v]"
    if hay_efe:
        entradas += ["-i", efe]
        partes.append(f"[2:a]atempo={VELOCIDAD}[e]")
        partes.append("[v][e]amix=inputs=2:normalize=0[ve]")
        mezcla = "[ve]"
    if hay_mus:
        entradas += ["-i", mus]
        i = 3 if hay_efe else 2
        partes.append(f"[{i}:a]volume={ganancia:.1f}dB,{TALLA}[m]")
        partes.append(f"{mezcla}[m]amix=inputs=2:normalize=0[mix]")
        mezcla = "[mix]"
    partes.append(f"{mezcla}loudnorm=I=-14:TP=-1.5:LRA=11[out]")
    return _correr(["ffmpeg", "-y", "-v", "error", *entradas,
                    "-filter_complex", ";".join(partes),
                    "-map", "0:v", "-map", "[out]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", destino])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--hazlo", action="store_true")
    a = ap.parse_args()
    tmp = os.environ.get("TMPDIR", "F:/tmp-video")
    os.makedirs(tmp, exist_ok=True)
    for n in (a.reels or range(1, 8)):
        s = f"reel-{n:02d}"
        base, voz = APROBADO.format(n=n), VOZ.format(s=s)
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
        salida = os.path.join(tmp, f"r{n}-remez.mp4")
        gan, nueva = 0.0, None
        for intento in range(INTENTOS):
            r = mezclar(n, gan, salida)
            if r.returncode or not os.path.exists(salida):
                print(f"     no se pudo mezclar: {r.stderr.strip()[:200]}")
                break
            nueva = distancia(salida, voz)
            if nueva is None:
                break
            print(f"     con {gan:+.1f} dB queda en {nueva:.1f} dB")
            if abs(nueva - OBJETIVO) <= MARGEN:
                break
            gan += nueva - OBJETIVO
        if nueva is None or not os.path.exists(salida):
            continue
        if abs(nueva - OBJETIVO) > MARGEN:
            print(f"     FUERA tras {INTENTOS} intentos: no se entrega")
            os.remove(salida)
            continue
        os.replace(salida, SALIDA.format(n=n))
        print(f"     -> {SALIDA.format(n=n)}  (imagen sin tocar)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
