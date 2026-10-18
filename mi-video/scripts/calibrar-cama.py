"""A qué nivel entra la cama de cada pieza, midiéndolo en vez de tanteando.

Jaime, después de oír R5, R6 y R7: *«el volumen alto sobresale por encima de la
voz y no la acompaña»*, y *«bájale dos punticos al volumen de la música en
todos: que se escuche pero que no cobre protagonismo»*.

## Por qué hace falta un bucle y no un número

`src/brand/cama.json` guarda dos cosas distintas —lo dice él mismo—: `por_defecto`
es el **nivel** al que se lleva el pasaje más fuerte de la obra, y `objetivo_db`
la **separación** que se quiere oír bajo la voz. La conversión entre las dos
depende de la obra, no del número: con `-19` puesto en las siete, reel-04 sale a
17,8 dB y reel-06 a 28,8. Once decibelios de diferencia con el mismo valor.

Así que el nivel de una pieza no se puede elegir: se busca. Se mide la entrega,
se mueve el nivel, se vuelve a medir. Eso es lo que se hacía a mano —tres o
cuatro corridas de `musica.sh` con `MUSI=` por delante, apuntando el resultado en
un papel— y por eso el propio `musica.sh` decía *«hasta que ese bucle viva aquí,
`MUSI` se puede pasar por fuera»*. Vive aquí.

## Cómo busca

Dos puntos y una recta. La relación entre nivel y separación es lineal en el
rango útil —medido en reel-06: `-19` da 28,8 dB y `-9` da 19,7, o sea 0,91 dB de
separación por dB de nivel; y en reel-07: `-19` da 35,2, `-5` da 23,5 y `+1,6`
da 17,5, con pendiente 0,84 sostenida en los tres—, así que con dos medidas se
sabe dónde caer y la tercera lo confirma.

**Y se para en cuanto entra**, porque cada vuelta es una mezcla entera.

## Lo que no hace

No decide si suena bien: decide si suena **donde se dijo**. La ventana útil del
lote son cuatro o cinco decibelios y los dos extremos los puso él con el oído
—19 dB es «la música no se escucha» y 13,6 dB es «sigue muy fuerte»—, así que
mover `objetivo_db` sigue siendo cosa suya.

    python scripts/calibrar-cama.py 7        # busca el nivel de reel-07
    python scripts/calibrar-cama.py          # las siete
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cama  # noqa: E402
import remezclar  # noqa: E402

#: Cuánto puede apartarse del objetivo sin volver a mezclar. Es la misma
#: tolerancia con la que `musica.sh` dice «FUERA»: por debajo de eso no se oye.
TOLERA = 1.5

#: El salto de tanteo para el segundo punto, en dB. Diez es bastante para que la
#: pendiente se note por encima del ruido de medida y poco para no salirse del
#: rango donde la recta vale.
SALTO = 10.0

#: Cuántas mezclas se consienten por pieza. Con dos puntos y una recta, la
#: tercera es la que confirma; si a la cuarta no ha entrado, el problema no es
#: el nivel y hay que mirar la obra.
VUELTAS = 4

#: Fuera de esto no se pone un nivel: son valores de normalización en LUFS y un
#: extremo delata que se está compensando otra cosa. reel-07 necesita +1,6
#: porque su fichero de música está muy bajo, y eso ya es el borde.
RANGO = (-40.0, 6.0)


def _mide(n, musi):
    """Mezcla reel-n con ese nivel y devuelve la separación medida, o None."""
    entorno = dict(os.environ, MUSI=str(musi))
    import rutas  # el interprete se resuelve, no se hereda: C-349, C-548
    subprocess.run([rutas.interprete(), "scripts/musica.sh", str(n)],
                   capture_output=True, env=entorno)
    # La referencia es la voz que entro en la mezcla, no el stem del bruto:
    # ese es de otro montaje en cuanto se recorta algo, y entonces la medida se
    # niega a contestar — cinco de las siete se quedaron sin calibrar por eso.
    return remezclar.distancia(f"out/entrega/reel-R{n}.mp4",
                               f"out/entrega/.sin-musica/reel-R{n}.mp4")


def _guardar(slug, musi, por_que, objetivo=None):
    """Deja el nivel de esa pieza en el fichero, con lo que se midió.

    **Y contra qué objetivo se midió**, que es lo que permite saber después si
    sigue valiendo sin volver a mezclar. Ver `cama.al_dia`. C-501.
    """
    with open(cama.FICHERO, encoding="utf-8") as f:
        d = json.load(f)
    d.setdefault("piezas", {})[slug] = round(musi, 1)
    if objetivo is not None:
        d.setdefault("medido_contra", {})[slug] = objetivo
    d[f"_{slug.replace('-', '_')}_medido"] = por_que
    with open(cama.FICHERO, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(d, ensure_ascii=False, indent=1) + "\n")


def calibrar(n, objetivo=None):
    """Busca el nivel de reel-n hasta caer en el objetivo. Devuelve (musi, sep)."""
    slug = f"reel-{n:02d}"
    objetivo = objetivo if objetivo is not None else cama.objetivo(slug)
    musi = float(cama.nivel(slug))
    puntos = []
    for vuelta in range(VUELTAS):
        sep = _mide(n, musi)
        if sep is None:
            print(f"  {slug}: no se puede medir — su stem de voz no corresponde"
                  f" a la entrega (C-243). No se toca el nivel.")
            return None, None
        print(f"  {slug}: {musi:+.1f} -> {sep:.1f} dB")
        puntos.append((musi, sep))
        if abs(sep - objetivo) <= TOLERA:
            if len(puntos) > 1:
                _guardar(slug, musi, _acta(slug, puntos, objetivo), objetivo)
            return musi, sep
        if len(puntos) == 1:
            # Primer tanteo: hacia donde hay que ir lo dice el signo. Más nivel
            # es menos separación, así que se mueve al revés del error.
            musi += SALTO if sep > objetivo else -SALTO
        else:
            (x0, y0), (x1, y1) = puntos[-2], puntos[-1]
            if abs(y1 - y0) < 0.2:
                print(f"  {slug}: la separacion no se mueve con el nivel"
                      f" ({y0:.1f} -> {y1:.1f}); no es la cama. Se deja como esta.")
                return None, None
            # Secante. Ojo con el signo: se busca cuanto hay que MOVERSE
            # desde x1, o sea `(objetivo - y1)` por la inversa de la pendiente.
            # Al reves —`(y1 - objetivo)`— la recta apunta al lado contrario y
            # cada vuelta se aleja: reel-01 iba de -19 a -9 y volvia a -19,8.
            musi = x1 + (objetivo - y1) * (x1 - x0) / (y1 - y0)
        musi = max(RANGO[0], min(RANGO[1], musi))
    print(f"  {slug}: cuatro mezclas sin entrar; mirar la obra, no el numero.")
    return None, None


def _acta(slug, puntos, objetivo):
    camino = ", ".join(f"{x:+.1f} -> {y:.1f} dB" for x, y in puntos)
    return (f"Medido, no elegido: {camino}. Objetivo {objetivo} dB con "
            f"{TOLERA} de tolerancia. El numero no es comparable con el de otra "
            f"pieza —depende de lo bajo que este su fichero de musica—; lo "
            f"comparable es el resultado. Si el corte cambia, hay que volver a "
            f"medir: `python scripts/calibrar-cama.py {slug[-1]}`.")


def main():
    import rutas
    ns = [int(x) for x in sys.argv[1:] if x.isdigit()] or rutas.piezas()
    mal = 0
    for n in ns:
        musi, sep = calibrar(n)
        if musi is None:
            mal += 1
    print(f"\ncalibrar: {len(ns) - mal} de {len(ns)} pieza(s) en su sitio")
    return 1 if mal else 0


if __name__ == "__main__":
    raise SystemExit(main())
