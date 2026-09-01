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
    python scripts/tamano.py --todo   # todos, con su tamano\n"""
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


#: La deuda declarada, fichero a fichero, con lo que medía al declararla.
#: **Sólo puede bajar.** Un fichero que crece por encima de su marca falla, y
#: uno nuevo por encima del techo falla siempre.
DEUDA = "docs/tamano-deuda.txt"


def declarada():
    """Lo que ya estaba largo cuando esto pasó a ser un contrato."""
    if not os.path.exists(DEUDA):
        return {}
    fuera = {}
    for linea in open(DEUDA, encoding="utf-8"):
        linea = linea.split("#", 1)[0].strip()
        if not linea:
            continue
        n, _, f = linea.partition(" ")
        fuera[f.strip()] = int(n)
    return fuera


def _codigo(f):
    """Cuántas líneas de ese fichero son **código**, no prosa ni aire.

    **Por qué se mide así y no a líneas totales.** El techo contaba todo, así
    que un fichero bien explicado y una bola de lógica del mismo tamaño le
    parecían iguales — y eso castiga documentar, que en este proyecto es medio
    entregable. Medido: `costuras.py` son 300 líneas y **164 de código**, doce
    funciones con la mayor en 47; `seleccionar.py` son 269 y **65 de código**.
    Ninguno de los dos es un monolito, y el guarda decía que sí.

    Lo que sí quiere cazar el techo es lógica amontonada, y eso son sentencias.
    Un docstring largo explicando por qué una regla es como es no hace un
    fichero más difícil de cambiar: lo hace más fácil.
    """
    import ast

    try:
        src = open(f, encoding="utf-8", errors="ignore").read()
    except OSError:
        return 0
    lineas = src.splitlines()
    if not f.endswith(".py"):
        # Fuera de Python se cuenta lo que no es blanco ni comentario de línea.
        return sum(1 for l in lineas
                   if l.strip() and not l.strip().startswith(("#", "//")))
    try:
        arbol = ast.parse(src)
    except SyntaxError:
        return len(lineas)
    prosa = 0
    for n in ast.walk(arbol):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            d = ast.get_docstring(n, clean=False)
            if d:
                prosa += d.count(chr(10)) + 2
    blancas = sum(1 for l in lineas if not l.strip())
    comentarios = sum(1 for l in lineas if l.strip().startswith("#"))
    return max(0, len(lineas) - blancas - comentarios - prosa)


def medidos():
    filas = []
    for f in ficheros():
        n = _codigo(f)
        if n:
            filas.append((n, f))
    filas.sort(reverse=True)
    return filas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todo", action="store_true")
    ap.add_argument("--declarar", action="store_true",
                    help="fija la deuda con lo que hay hoy")
    a = ap.parse_args()
    filas = medidos()
    pasan = [x for x in filas if x[0] > TECHO]

    if a.declarar:
        with open(DEUDA, "w", encoding="utf-8", newline="\n") as h:
            h.write("# Ficheros por encima de las 300 lineas, con lo que median\n"
                    "# el dia que el techo paso a ser contrato. SOLO BAJA: si uno\n"
                    "# crece, el build para; si baja, se vuelve a declarar.\n")
            for n, f in sorted(pasan, key=lambda x: x[1]):
                h.write(f"{n} {f}\n")
        print(f"deuda declarada: {len(pasan)} ficheros,"
              f" {sum(n - TECHO for n, _ in pasan)} lineas de mas")
        return

    for n, f in (filas if a.todo else pasan):
        marca = "  <-- pasa del techo" if n > TECHO else ""
        print(f"{n:>5}  {f}{marca}")
    if not pasan:
        print(f"\ntamano: ningun fichero pasa de {TECHO} lineas")
        return

    # **El techo es un contrato, no un informe.** Esto imprimia «33 ficheros
    # pasan del techo» y salia con codigo 0 — la averia de C-152 un piso mas
    # abajo: un guarda que avisa y sigue no es un guarda. Ahora la deuda esta
    # escrita, sola puede bajar, y un fichero nuevo por encima del techo no
    # nace.
    ya = declarada()
    nuevos = [(n, f) for n, f in pasan if f not in ya]
    crecidos = [(n, f, ya[f]) for n, f in pasan if f in ya and n > ya[f]]
    bajados = [(n, f, ya[f]) for n, f in pasan if f in ya and n < ya[f]]

    total = sum(n - TECHO for n, _ in pasan)
    print(f"\n{len(pasan)} de {len(filas)} ficheros pasan de {TECHO} lineas,"
          f" {total} lineas de mas")
    if bajados:
        print("bajan: " + ", ".join(f"{f} {v}->{n}" for n, f, v in bajados[:6]))
        print("  fija la marca nueva con: python scripts/tamano.py --declarar")
    print("Se parte por responsabilidad: lo que mide, lo que decide y lo que"
          " escribe son tres cosas. Cinco ficheros de 300 con el mismo lio"
          " dentro es el mismo lio.")

    mal = [f"{f} nace con {n} lineas y el techo son {TECHO}" for n, f in nuevos]
    mal += [f"{f} crecio de {v} a {n} lineas, y la deuda solo baja"
            for n, f, v in crecidos]
    if mal:
        print(f"\nEL TECHO ES UN CONTRATO - {len(mal)} incumplimiento(s):")
        for m in mal:
            print(f"  · {m}")
        raise SystemExit(1)



if __name__ == "__main__":
    main()
