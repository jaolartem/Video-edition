"""El tamaño de cada fichero. Trescientas líneas es el techo.

Regla de Jaime: *«máximo 300 líneas por script; el principal es un camino de
fases, no un monolito de servicios desconectados»*. Y la que la explica:
*«buscamos construir y mantener servicios, no un monolito, no spaghetti — eso
significa POO»*.

## Por qué un número y no «que sea corto»

Porque «corto» no se comprueba. Un fichero de mil quinientas líneas no se lee
entero nunca, así que nadie sabe lo que hace: se le añade al final y se confía.
`seleccionar.py` llegó a 1.591 y por eso pudo tener el peso de un extremo roto
diez veces por debajo de lo que debía sin que se notara — la línea estaba ahí,
sólo que a seiscientas líneas de donde se leía.

El techo no es estético: es lo que hace que un fichero **quepa en la cabeza** de
quien lo va a cambiar.

## Cómo se baja de ahí, y cómo no

**No partiendo por líneas.** Un fichero de 1.500 cortado en cinco de 300 es el
mismo spaghetti en cinco platos. Se parte por **responsabilidad**: lo que mide,
lo que decide y lo que escribe son tres cosas, y casi siempre están mezcladas.

El orden es el del daño: primero lo que se toca a menudo y más pesa.

    python scripts/tamano.py          # lo que pasa del techo
    python scripts/tamano.py --todo   # todos, con su tamano
"""
import argparse
import os

TECHO = 300
MIRA = ("scripts", "src")
EXT = (".py", ".mjs", ".sh", ".tsx", ".ts")

# Lo que no cuenta: generado, de terceros o datos disfrazados de codigo.
SALTA = ("node_modules", ".parcel-cache", "package-lock", "servicios/__pycache__")


def ficheros():
    for raiz in MIRA:
        for d, _, fs in os.walk(raiz):
            if any(x in d.replace("\\", "/") for x in SALTA):
                continue
            for f in fs:
                if f.endswith(EXT) and not any(x in f for x in SALTA):
                    yield os.path.join(d, f).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true")
    a = ap.parse_args()
    filas = []
    for f in ficheros():
        try:
            n = sum(1 for _ in open(f, encoding="utf-8", errors="ignore"))
        except OSError:
            continue
        filas.append((n, f))
    filas.sort(reverse=True)
    pasan = [x for x in filas if x[0] > TECHO]
    for n, f in (filas if a.todo else pasan):
        marca = "  <-- pasa del techo" if n > TECHO else ""
        print(f"{n:>5}  {f}{marca}")
    if not pasan:
        print(f"\ntamano: ningun fichero pasa de {TECHO} lineas")
        return
    total = sum(n - TECHO for n, _ in pasan)
    print(f"\n{len(pasan)} de {len(filas)} ficheros pasan de {TECHO} lineas"
          f" · {total} lineas de mas en total")
    print("Se parte por responsabilidad —lo que mide, lo que decide y lo que"
          " escribe—,\nno por lineas: cinco ficheros de 300 con el mismo lio"
          " dentro es el mismo lio.")


if __name__ == "__main__":
    main()
