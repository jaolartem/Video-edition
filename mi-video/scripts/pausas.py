"""**Quitar y devolver las pausas del baile a una pista de voz.**

Jaime, 18-9-2026, al ver que cambiar el reparto le costaba otra pasada por Adobe:
*«desacóplalo, y luego repartes»*.

## Por qué existe

Las pausas que hacen que la pieza baile (`compas.json`) viven en el corte, así
que la voz exportada las llevaba dentro. Y con eso, **cambiar el ritmo
invalidaba el trabajo de Adobe**: el fichero limpio tenía los silencios viejos y
ya no encajaba. Pasó tres veces el 17 y el 18 de septiembre.

Pero una pausa **es silencio**, y el silencio se puede añadir a un fichero ya
limpio. Así que se separan los dos asuntos:

- **Al exportar** se quitan: Adobe recibe la voz seguida, sin las esperas.
- **Al integrar** se devuelven, en el sitio que diga `compas.json` HOY.

Con eso el reparto de las pausas deja de tocar lo que él limpia. Se puede mover
el ritmo tantas veces como haga falta sin pedirle una pasada más.

## Simétricas a propósito

`quitar` y `poner` son la misma lista de ventanas leída al derecho y al revés.
Si una se toca sin la otra, la voz vuelve corrida — y eso no se ve en el fichero,
se oye en la pieza. Por eso viven juntas y en un solo sitio.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compas  # noqa: E402


def _corre(orden):
    return subprocess.run(orden, capture_output=True).returncode == 0


def ventanas_hay(slug):
    """Las ventanas de esa pieza, o lista vacía. Para preguntar sin abrir nada."""
    return compas.ventanas(slug, reloj="corte")


def quitar(entrada, salida, slug):
    """La voz sin las pausas declaradas. `False` si la pieza no baila."""
    v = compas.ventanas(slug, reloj="corte")
    if not v:
        return False
    trozos, ant, filtros = [], 0.0, []
    for i, (a, b) in enumerate(v + [(None, None)]):
        fin = a if a is not None else None
        sel = f"atrim=start={ant:.3f}" + (f":end={fin:.3f}" if fin else "")
        filtros.append(f"[0:a]{sel},asetpts=PTS-STARTPTS[t{i}]")
        trozos.append(f"[t{i}]")
        if b is not None:
            ant = b
    cadena = ";".join(filtros) + ";" + "".join(trozos) + f"concat=n={len(trozos)}:v=0:a=1[out]"
    return _corre(["ffmpeg", "-y", "-v", "error", "-i", entrada,
                   "-filter_complex", cadena, "-map", "[out]",
                   "-c:a", "pcm_s16le", salida])


def poner(entrada, salida, slug):
    """La voz limpia con las pausas devueltas donde `compas.json` dice hoy."""
    v = compas.ventanas(slug, reloj="corte")
    if not v:
        return False
    # Los cortes en la pista SIN pausas: cada ventana empieza donde acabo lo
    # anterior menos lo que ya se quito.
    cortes, quitado = [], 0.0
    for a, b in v:
        cortes.append((a - quitado, b - a))
        quitado += b - a
    filtros, trozos, ant = [], [], 0.0
    for i, (en, dura) in enumerate(cortes):
        filtros.append(f"[0:a]atrim=start={ant:.3f}:end={en:.3f},asetpts=PTS-STARTPTS[v{i}]")
        filtros.append(f"anullsrc=r=48000:cl=mono,atrim=duration={dura:.3f}[s{i}]")
        trozos += [f"[v{i}]", f"[s{i}]"]
        ant = en
    filtros.append(f"[0:a]atrim=start={ant:.3f},asetpts=PTS-STARTPTS[vf]")
    trozos.append("[vf]")
    cadena = ";".join(filtros) + ";" + "".join(trozos) + f"concat=n={len(trozos)}:v=0:a=1[out]"
    return _corre(["ffmpeg", "-y", "-v", "error", "-i", entrada,
                   "-filter_complex", cadena, "-map", "[out]",
                   "-c:a", "pcm_s16le", salida])


def poner_si_baila(wav, n):
    """La voz con sus pausas devueltas, o la misma si esa pieza no baila.

    Se lleva la pregunta, la ruta temporal y el aviso para que quien la llama
    sean dos líneas: el techo de 300 de `voz-limpia.py` es un contrato.
    """
    import os

    slug = f"reel-{n:02d}"
    if not ventanas_hay(slug):
        return wav
    con = os.path.join("F:/tmp-video",
                       os.path.basename(wav).replace(".wav", "-bailada.wav"))
    if not poner(wav, con, slug):
        return wav
    print(f"R{n}: pausas del baile devueltas ({len(ventanas_hay(slug))})")
    return con
