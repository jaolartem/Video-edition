"""La forma del código: cuánto monolito queda y cuánto dominio sin tipar.

Regla de Jaime: *«no quiero monolitos, quiero servicios concretos»*, y antes
*«un techo de 300 líneas»*. Lo segundo se anunció en un commit y **no había nada
que lo comprobara**: quince ficheros ya estaban por encima cuando se auditó.

## Por qué avisa y no falla

Porque bloquear no arregla ninguno de los quince, y un build que falla siempre se
aprende a ignorar — que es peor que no tenerlo. Lo que sí funciona es que el
número **se vea en cada corrida**: un fichero que cruza el techo se nota el día
que lo cruza, no seis meses después.

Es la misma idea que `alcance.py`: un espejo, no una puerta.

## Las tres cosas que mira, y por qué esas

1. **Ficheros por encima del techo.** El monolito es medible.
2. **Clases contra funciones de módulo.** 18 clases en 24.854 líneas no es un
   estilo: es que el dominio no existe como tipo.
3. **Accesos `obj["campo"]`.** Ésta es la de fondo, y explica a las otras dos.
   Con 1.351 accesos sobre 186 nombres de campo no hay dónde mirar qué tiene una
   ventana candidata ni qué garantiza que esté — así que **partir un fichero
   grande reparte los mismos accesos sin tipo entre más ficheros**. Mueve el
   monolito, no lo deshace.

   Y ya cuesta: el mismo concepto se escribe de dos maneras según de dónde
   venga, `["start"]`/`["end"]` en el transcript y `["a"]`/`["b"]` en una
   ventana. Eso es lo que `dominio.py` viene a cerrar, y este número es el que
   dice cuánto queda.

    python scripts/forma.py            # el resumen
    python scripts/forma.py --detalle  # y qué fichero es cada cosa
"""
import argparse
import ast
import glob
import os
import re

# El techo que fijó Jaime. No es una regla de estilo: por encima de esto un
# fichero deja de caber en la cabeza de quien lo va a cambiar.
TECHO = 300


def _ficheros(patron):
    return [p for p in sorted(glob.glob(patron, recursive=True))
            if "__pycache__" not in p]


def python(raiz="scripts"):
    """Líneas, clases, funciones de módulo y accesos por clave, por fichero."""
    out = []
    for p in _ficheros(os.path.join(raiz, "**", "*.py")):
        src = open(p, encoding="utf-8").read()
        try:
            t = ast.parse(src)
        except SyntaxError:
            continue
        clases = [n for n in ast.walk(t) if isinstance(n, ast.ClassDef)]
        # Sólo las de módulo: los métodos ya cuentan como clase.
        funcs = [n for n in t.body if isinstance(n, ast.FunctionDef)]
        claves = [n.slice.value for n in ast.walk(t)
                  if isinstance(n, ast.Subscript)
                  and isinstance(n.slice, ast.Constant)
                  and isinstance(n.slice.value, str)]
        out.append({"fichero": p, "lineas": len(src.splitlines()),
                    "clases": len(clases), "funciones": len(funcs),
                    "claves": claves})
    return out


def js(raiz="scripts"):
    out = []
    for p in _ficheros(os.path.join(raiz, "*.mjs")):
        src = open(p, encoding="utf-8").read()
        out.append({"fichero": p, "lineas": len(src.splitlines()),
                    "clases": len(re.findall(r"^\s*class ", src, re.M))})
    return out


def resumen():
    py, mjs = python(), js()
    accesos = [k for f in py for k in f["claves"]]
    altos = sorted([f for f in py + mjs if f["lineas"] > TECHO],
                   key=lambda f: -f["lineas"])
    return {
        "ficheros": len(py) + len(mjs),
        "lineas": sum(f["lineas"] for f in py + mjs),
        "clases": sum(f["clases"] for f in py + mjs),
        "funciones": sum(f["funciones"] for f in py),
        "sobre_techo": altos,
        "lineas_sobre_techo": sum(f["lineas"] for f in altos),
        "accesos": len(accesos),
        "campos": len(set(accesos)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--detalle", action="store_true",
                    help="ensena que fichero es cada cosa")
    a = ap.parse_args()
    r = resumen()
    pct = r["lineas_sobre_techo"] * 100 // max(r["lineas"], 1)
    print(f"forma: {r['ficheros']} ficheros · {r['lineas']:,} lineas ·"
          f" {r['clases']} clases · {r['funciones']} funciones de modulo")
    print(f"  por encima de {TECHO} lineas: {len(r['sobre_techo'])} ficheros,"
          f" {r['lineas_sobre_techo']:,} lineas ({pct}% del codigo)")
    print(f"  dominio sin tipo: {r['accesos']:,} accesos obj[\"campo\"] sobre"
          f" {r['campos']} nombres distintos")
    if a.detalle:
        for f in r["sobre_techo"]:
            print(f"     {f['lineas']:>5}  {f['fichero']}")


if __name__ == "__main__":
    main()
