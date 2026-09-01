"""Reapunta las agujas cuyo mecanismo se mudó de fichero. **Sin adivinar.**

## Por qué existe

Partir un monolito mueve código, y con el código se mueven las agujas: los
literales que `guardas.mjs`, `contratos.py` y `verdad.py` usan para comprobar que
un mecanismo sigue vivo. En una sola noche se movieron más de ochenta, y
reapuntarlas a mano tiene dos problemas: es lento y **se hace de memoria**, que
es como se cuela una aguja apuntando a un sitio donde el literal no está.

## La regla, y es lo único que hace esto seguro

**Sólo reapunta cuando el literal aparece en EXACTAMENTE un fichero.**

- En ninguno → el mecanismo se perdió de verdad. Eso no se arregla moviendo la
  aguja: se mira. Se informa y no se toca.
- En dos o más → hay una copia, que es peor que perderlo. Se informa y no se
  toca.

Una aguja que se reapunta sola cuando el mecanismo desapareció convierte el
guarda en un sello de goma, y este proyecto ya tiene bastantes maneras de que
algo parezca comprobado sin estarlo.

## El fallo que cometió en su primer ensayo, y por eso está escrito aquí

Reapuntaba agujas huérfanas a `verdad.py` porque el literal aparece allí… **en la
propia declaración**. El guarda pasaba a comprobarse a sí mismo. Por eso
`_sin_declaraciones()` quita las llamadas `Aguja(...)` antes de buscar: dentro de
una, el literal es una declaración, no un mecanismo.

Excluir el fichero entero sería demasiado grueso —`contrato/piezas.py` tiene
código de verdad además de declaraciones—, así que lo que se quita es la llamada,
no el fichero.

    python scripts/reapuntar.py          # dice qué haría
    python scripts/reapuntar.py --hazlo  # lo hace
"""
import argparse
import glob
import io
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

#: Dónde puede vivir un mecanismo.
CODIGO = ("scripts/*.py", "scripts/*/*.py", "scripts/*/*/*.py",
          "scripts/*.mjs", "scripts/*/*.mjs", "scripts/*.sh",
          "scripts/*.sql",   # el esquema es codigo: se declara y se comprueba

          "src/*.ts*", "src/*/*.ts*", "src/*/*/*.ts*")


def _sin_declaraciones(cuerpo):
    """Quita las llamadas `Aguja(...)`: ahí el literal es declaración.

    Sin expresión regular a propósito. La llamada puede llevar comillas de los
    dos tipos, saltos de línea y paréntesis dentro, y un patrón que intente
    cubrir todo eso se rompe justo en el caso raro — que es el que importa.
    """
    fuera, i = [], 0
    while True:
        k = cuerpo.find("Aguja(", i)
        if k < 0:
            fuera.append(cuerpo[i:])
            break
        fuera.append(cuerpo[i:k])
        prof, j = 0, k + len("Aguja")
        while j < len(cuerpo):
            if cuerpo[j] == "(":
                prof += 1
            elif cuerpo[j] == ")":
                prof -= 1
                if prof == 0:
                    j += 1
                    break
            j += 1
        i = j
    return "".join(fuera)


#: **Los ficheros que DOCUMENTAN agujas no son sitios donde vive un mecanismo.**
#:
#: `guardas.mjs` explica su propia sintaxis con un ejemplo —«`beats.py` :: `def
#: deBeat(`»— y esta herramienta se lo tomo por codigo: reapunto la aguja a la
#: documentacion del guarda. Es el mismo fallo que ya cometio con `verdad.py`,
#: por otra puerta, asi que la leccion no era «quitar las llamadas `Aguja(`»
#: sino **no buscar donde solo se habla de agujas**.
NO_ES_CODIGO = ("scripts/guardas.mjs",)


def _cuerpos():
    fuera = {}
    for patron in CODIGO:
        for f in glob.glob(os.path.join(RAIZ, "mi-video", patron)):
            if "__pycache__" in f or "node_modules" in f:
                continue
            rel = os.path.relpath(f, os.path.join(RAIZ, "mi-video"))
            if rel.replace(os.sep, "/") in NO_ES_CODIGO:
                continue
            cuerpo = io.open(f, encoding="utf-8", errors="replace").read()
            fuera[rel.replace(os.sep, "/")] = _sin_declaraciones(cuerpo)
    return fuera


def _di(msg):
    """Escribe sin morir en una consola cp1252. Es un gotcha del proyecto."""
    import sys

    cod = getattr(sys.stdout, "encoding", None) or "utf-8"
    print(msg.encode(cod, "replace").decode(cod))


def donde_vive(literal, cuerpos):
    return sorted(f for f, s in cuerpos.items() if literal in s)


def _del_log(texto):
    for m in re.finditer(r"`(mi-video/[^`]+?)` (!?):: `([^`]+)`", texto):
        yield m.group(0), m.group(1), m.group(2), m.group(3)


def revisar(hazlo=False):
    cuerpos = _cuerpos()
    movidas = perdidas = copiadas = 0

    log = os.path.join(RAIZ, "docs", "correcciones.md")
    t = io.open(log, encoding="utf-8").read()
    for entero, ruta, negada, literal in list(_del_log(t)):
        if negada:                          # `!:` exige que NO esté
            continue
        corta = ruta[len("mi-video/"):]
        if corta in cuerpos and literal in cuerpos[corta]:
            continue
        vive = donde_vive(literal, cuerpos)
        if len(vive) == 1:
            t = t.replace(entero, "`mi-video/" + vive[0] + "` :: `" + literal + "`")
            _di(f"  mover  {corta} -> {vive[0]}   [{literal[:48]}]")
            movidas += 1
        elif not vive:
            _di(f"  PERDIDA  [{literal[:58]}]  (decia {corta})")
            perdidas += 1
        else:
            _di(f"  EN {len(vive)} SITIOS  [{literal[:40]}] -> {', '.join(vive)}")
            copiadas += 1
    if hazlo and movidas:
        io.open(log, "w", encoding="utf-8", newline="\r\n").write(t)

    comilla_escapada = chr(92) + '"'
    for patron in ("mi-video/scripts/verdad.py",
                   "mi-video/scripts/contrato/*.py",
                   "mi-video/scripts/contrato/*/*.py"):
        for f in glob.glob(os.path.join(RAIZ, patron)):
            s = io.open(f, encoding="utf-8").read()
            orig = s
            for m in re.finditer(r'Aguja\(\s*"([^"]+)",\s*\n?\s*(["\'])(.*?)\2',
                                 s, re.S):
                ruta, comilla, literal = m.group(1), m.group(2), m.group(3)
                real = literal.replace(comilla_escapada, '"')
                if ruta in cuerpos and real in cuerpos[ruta]:
                    continue
                vive = donde_vive(real, cuerpos)
                if len(vive) == 1:
                    s = s.replace('Aguja("' + ruta + '", ' + comilla + literal,
                                  'Aguja("' + vive[0] + '", ' + comilla + literal)
                    _di(f"  mover  {os.path.basename(f)}: {ruta} -> {vive[0]}"
                        f"   [{real[:40]}]")
                    movidas += 1
                elif not vive:
                    _di(f"  PERDIDA  [{real[:52]}]  ({os.path.basename(f)})")
                    perdidas += 1
                else:
                    _di(f"  EN {len(vive)} SITIOS  [{real[:38]}]")
                    copiadas += 1
            if hazlo and s != orig:
                io.open(f, "w", encoding="utf-8", newline="\r\n").write(s)

    print("\nreapuntar: " + str(movidas) + " se mudaron, " + str(perdidas)
          + " perdidas de verdad, " + str(copiadas) + " en mas de un sitio")
    if not hazlo and movidas:
        print("  (era el ensayo: corre con --hazlo)")
    return perdidas + copiadas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hazlo", action="store_true")
    revisar(ap.parse_args().hazlo)


if __name__ == "__main__":
    main()
