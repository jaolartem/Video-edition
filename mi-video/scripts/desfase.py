"""Cuanto va por delante un angulo respecto a otro, medido por el SONIDO.

Jaime, cerrando la forma de entregar el material: *«para eso, de aca en adelante
subo cada video grabado de esta forma en una carpeta con los videos que lo
componen»*. Y antes, sobre por que: *«puede que en el futuro tenga una escena
grabada con dos camaras al tiempo»*.

Una carpeta con dos angulos no sirve de nada mientras no se sepa **por donde
casan**. Dos camaras arrancan cuando le da a cada boton, asi que sus relojes
empiezan separados por segundos: cortar de una a otra por el tiempo de fichero
pone al sujeto diciendo otra cosa.

## Por que por el sonido y no por la imagen

Porque las dos camaras oyen **lo mismo** y ven cosas distintas. La onda es la
misma senal grabada dos veces, asi que basta con deslizar una sobre otra hasta
que encajen. Comparar imagenes seria comparar dos encuadres que por definicion
no se parecen — que es justo para lo que se puso la segunda camara.

## Como se mide

1. Se saca el audio de cada angulo a 1 kHz mono. No hace falta mas: lo que se
   compara es **donde sube y baja el volumen**, no como suena.
2. Se calcula la envolvente en ventanas de 20 ms y se le quita la media, para
   que dos camaras con ganancias distintas se comparen igual.
3. Se cruzan las dos envolventes y el pico dice el desfase.

Y sale con su **confianza**: el pico dividido por lo que vale un cruce
cualquiera. Por debajo de `CLARO` no se afirma nada — dos angulos de momentos
distintos tambien dan un pico, solo que flojo, y un desfase inventado es peor
que ninguno porque nadie lo comprueba despues.

    python scripts/desfase.py 20260903_120000        # una grabacion entera
    python scripts/desfase.py --a A.mp4 --b B.mp4    # dos ficheros sueltos
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rutas  # noqa: E402

#: Frecuencia a la que se compara. 1 kHz es de sobra para una envolvente y hace
#: que una cinta de tres minutos quepa en memoria sin pensarlo.
SR = 1000
#: Ventana de la envolvente, en muestras. 20 ms: mas corta persigue el ruido,
#: mas larga difumina el ataque de una consonante, que es lo que da el pico.
VENTANA = 20
#: Por debajo de esto no se afirma un desfase, y **el numero esta medido**, no
#: elegido: diez pares de audio de este mismo corpus, cuatro del mismo momento
#: con desfase conocido y seis de grabaciones distintas.
#:
#:     mismo momento   17.8  23.4  23.9  51.2   <- y los cuatro desfases exactos
#:     distintas        5.0   5.1   5.5   5.8   6.4   7.3
#:
#: Empezo en 4.0 a ojo y con eso **dos grabaciones distintas daban «claro: true»
#: con 5,4x**: el metodo siempre contesta algo, asi que sin una vara medida lo
#: que devuelve con material que no casa es ruido con cara de medida.
#:
#: **Y luego bajo de 12 a 10 por una prueba con video de verdad**, no con wav:
#: dos angulos re-comprimidos a AAC, uno a la mitad de volumen, dieron 12,6 —
#: acertando el desfase al centesimo—. La compresion se come parte de la
#: envolvente, asi que un caso bueno puede quedar mas cerca del corte de lo que
#: sugieren los wav. 10 deja margen por los dos lados: el falso mas alto medido
#: es 7,3 y el verdadero mas flojo, 12,6.
CLARO = 10.0
#: Donde se guarda lo medido, junto a los otros derivados de cada cinta.
CARPETA = os.path.join(rutas.TRABAJO, "desfase")


def envolvente(video):
    """La envolvente de volumen de un video, ya normalizada."""
    import numpy as np

    crudo = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", video, "-vn",
         "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        capture_output=True, check=True).stdout
    x = np.frombuffer(crudo, dtype=np.int16).astype(np.float32)
    if not len(x):
        return None
    # Energia por ventana: `|x|` promediado es tan bueno como el RMS aqui y no
    # exagera los picos, que en dos camaras con ganancia distinta es lo que mas
    # separa a las dos curvas.
    n = len(x) // VENTANA
    e = np.abs(x[: n * VENTANA]).reshape(n, VENTANA).mean(axis=1)
    # Quitar la media es lo que hace comparables dos ganancias distintas: lo que
    # se cruza es la FORMA de la curva, no su altura.
    e -= e.mean()
    d = np.sqrt((e ** 2).sum())
    return e / d if d else None


def entre(a, b):
    """Cuanto hay que SUMAR al reloj de `b` para leerlo en el reloj de `a`.

    Positivo quiere decir que `b` empezo a grabar despues: su segundo 0 cae mas
    tarde en el mundo, asi que el segundo 10 de `b` es el segundo `10 + desfase`
    de `a`. Negativo, al reves.

    La regla practica, que es la que se usa al montar: **para cortar al angulo
    `b` en el segundo `t` de la pieza, se busca `t - desfase` dentro de `b`.**
    """
    import numpy as np

    ea, eb = envolvente(a), envolvente(b)
    if ea is None or eb is None:
        return {"error": "alguno de los dos angulos no tiene audio"}
    cruce = np.correlate(ea, eb, mode="full")
    i = int(np.argmax(np.abs(cruce)))
    pico = float(np.abs(cruce[i]))
    # La confianza es el pico contra lo que vale un cruce cualquiera. Sin esto
    # el metodo siempre contesta algo, y lo que contesta con dos grabaciones
    # distintas es ruido con cara de medida.
    fondo = float(np.abs(cruce).mean()) or 1e-9
    seguro = pico / fondo
    saltos = (i - (len(eb) - 1)) * VENTANA / SR
    return {
        "desfase_s": round(saltos, 3),
        "confianza": round(seguro, 1),
        "claro": seguro >= CLARO,
        "por": ("los dos angulos son el mismo momento" if seguro >= CLARO else
                f"el pico no destaca ({seguro:.1f}x, hace falta {CLARO}x):"
                " o no son el mismo momento, o uno no tiene sonido util"),
    }


def grabacion(toma):
    """El desfase de cada angulo respecto al PRINCIPAL, y se guarda.

    El principal es el primero por orden alfabetico —lo dice `rutas.angulos`— y
    su desfase es cero por definicion: es el reloj contra el que se mide todo lo
    demas, igual que la cinta unica lo era antes.
    """
    a = rutas.angulos(toma)
    if len(a) < 2:
        return {"toma": toma, "angulos": len(a),
                "nota": "un solo angulo: no hay nada que casar"}
    fuera = {"toma": toma, "principal": os.path.basename(a[0]), "angulos": {}}
    for otro in a[1:]:
        fuera["angulos"][os.path.basename(otro)] = entre(a[0], otro)
    os.makedirs(CARPETA, exist_ok=True)
    with open(os.path.join(CARPETA, f"{toma}.json"), "w",
              encoding="utf-8") as f:
        json.dump(fuera, f, ensure_ascii=False, indent=1)
    return fuera


def main():
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("toma", nargs="?", help="la grabacion, p. ej. 20260903_120000")
    p.add_argument("--a", help="un video suelto")
    p.add_argument("--b", help="el otro")
    args, _ = p.parse_known_args()
    if args.a and args.b:
        print(json.dumps(entre(args.a, args.b), ensure_ascii=False, indent=1))
    elif args.toma:
        print(json.dumps(grabacion(args.toma), ensure_ascii=False, indent=1))
    else:
        p.error("hace falta una grabacion, o --a y --b")


if __name__ == "__main__":
    main()
