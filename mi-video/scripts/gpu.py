"""La tarjeta corriendo whisper, y el sello dice si estuvo.

Regla de Jaime, dicha dos veces y la segunda ya sin rodeos: *«estas utilizando
la tarjeta grafica, no me parece sensato que te demores tanto»*, y despues *«el
objetivo es dejar de utilizar la CPU para correr el whisper, toma demasiado
tiempo que se puede ahorrar»*.

No la estaba usando. C-56 midio por que y lo dio por cerrado: la release publica
CPU, BLAS y cuBLAS —que es NVIDIA— y aqui hay una Radeon RX 5600 XT; compilar el
backend de Vulkan con GCC llevaba horas y se abandono. **Eso era cierto y ya no
lo es**: lo que faltaba era una cabecera, `spirv/unified1/spirv.hpp`, que estaba
en la maquina y no en el camino de busqueda. Con ella el build entero son 309
pasos y no llega a la hora.

## Lo que se gana, medido

Misma ventana de 30 s, mismo `medium`, mismas banderas que usa el paso 1, y el
lado de CPU es `whisper-cli-cpu`, o sea **lo que se corria antes**:

    CPU 12 hilos    15,8 s    encode 8.549 ms    decode 5.241 ms
    Vulkan           8,6 s    encode 4.539 ms    decode 2.043 ms    **1,84x**

Sobre ocho ventanas seguidas del reel 2: 133,8 s contra 69,8 s, **1,92x**.

## Y el texto NO sale identico. Por que aun asi vale

Primero se midio una ventana, salio 1,000 de parecido y por poco queda escrito
aqui que «da lo mismo». Sobre ocho ventanas la verdad es otra: **3 identicas,
media 0,91, y una en 0,56**. Escribirlo como identico habria sido una medida de
una muestra vendida como ley.

Lo que hay detras: los dos backends son **deterministas** —CPU contra CPU 1,0000
y GPU contra GPU 1,0000, comprobado— asi que no es azar. Es que con decodificado
voraz (`-bs 1`) una diferencia de coma flotante en el logit cambia un token, y a
partir de ahi la frase se va por otro lado.

**Y eso es exactamente el material con el que este paso ya trabaja.** El acuerdo
entre las tres pasadas de una misma corrida —mismo binario, mismas banderas, solo
ventanas distintas— es **0,817 de media sobre 679 tramos**, con el 42% por debajo
de 0,90. La distancia CPU/GPU (0,91) es **mas pequena que el desacuerdo que
`medoide()` arbitra en cada tramo**. La tarjeta no es una pasada peor: es una
pasada distinta, dentro del margen para el que se diseno la votacion.

Mirados uno a uno los diffs tampoco hay un ganador: en la ventana del 0,56 la
CPU acaba en «y factura ciento temblanton», que no es una palabra, y la GPU en
«y factura 180.000 al ano»; en otra la CPU oye un «vale, 180 mil al ano» que la
GPU se come. Se reparten los aciertos.

Lo que **si** cambia el diseno: el transcript declara ahora `dispositivo`, y una
corrida no mezcla los dos. Comparar dos corridas sin saber de donde sale cada
una no significaba nada.

Tres cosas mas medidas, para no volver a mirarlas:

- **Los hilos ya no mandan.** Con la tarjeta puesta, 4 hilos (8,5 s) y 12 hilos
  (8,7 s) dan lo mismo: el encoder dejo de estar en la CPU. `HILOS = 12` se
  queda porque sigue siendo el valor bueno cuando se cae a CPU.
- **Dos ventanas a la vez en la tarjeta van PEOR**, no mejor: 22,6 s las dos
  frente a 8,7 s cada una en fila. La cola es la GPU, y ademas dos `medium` no
  caben comodos en 6 GB. El paso 1 sigue yendo de una en una.
- **`-fa` ya no estorba.** C-56 lo midio peor en CPU (18,1 -> 22,6 s) con el
  binario de entonces; con b4938 es al reves —16,2 s con `-fa` contra 18,4 sin
  el— y en GPU da igual. Se deja el de por defecto, que es `-fa`.

## Lo que este modulo hace, y lo que no

No decide nada sobre el video. Contesta tres preguntas mecanicas, y las contesta
**preguntandoselo al binario**, no mirando si hay un fichero en el disco:

    esta()          hay tarjeta y whisper la ve?  (y si no, por que no)
    whisper()       con que binario se llama, ya resuelto
    sello()         que la produjo, para que quede en el transcript

## Por que hay DOS binarios y no uno con una bandera

Porque medirlo dijo que no da igual. La build de Vulkan es estatica y **no trae
los backends de CPU por microarquitectura** que si trae la release: forzarle
`-ng` sobre la misma ventana da 22,9 s, contra los 15,8 s de la build de CPU.
O sea que un `-ng` como plan B habria dejado la caida **mas lenta que antes de
todo esto**, que es exactamente la clase de mejora que empeora.

Asi que conviven: `whisper-cli.exe` es la de Vulkan y `whisper-cli-cpu.exe` la
de CPU con sus DLL. `whisper()` devuelve la que toca y nadie mas tiene que
saberlo.

El sello importa tanto como la velocidad. `comparar.py` existe para contrastar
dos corridas, y sin saber cual salio de la tarjeta y cual de la CPU la
comparacion no tiene sentido — es el mismo motivo por el que el transcript ya
declara `modelo`, `paso` y `pasadas`.

    python scripts/gpu.py                        # que hay
    python scripts/gpu.py --medir --wav v.wav    # CPU contra GPU, misma ventana

Y se apaga con `VIDEO_GPU=0`, igual que las rutas se mueven con `VIDEO_ORIGEN`:
para volver a la CPU sin editar un script.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import time
import wave

sys.path.insert(0, os.path.dirname(__file__))
import registro  # noqa: E402
import rutas  # noqa: E402

W = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
CLI = os.path.join(W, "whisper-cli.exe")
# La de CPU con sus backends por microarquitectura, para cuando no haya tarjeta.
# Ver «Por que hay DOS binarios» arriba: no es un lujo, es no empeorar la caida.
#
# **Y va en su propia carpeta, obligatoriamente.** La build de Vulkan es
# estatica pero sigue cargando cualquier `ggml-*.dll` que encuentre a su lado, y
# las de la release estan compiladas con MSVC: juntarlas mata a la de Vulkan con
# un `GGML_ASSERT(prev != ggml_uncaught_exception) failed` que ni siquiera
# menciona una DLL. Sale con codigo 0, ademas — el fallo de C-48 otra vez.
CLI_CPU = os.path.join(W, "cpu", "whisper-cli.exe")
# El barato para preguntar: sondear con `medium` seria leer 1,5 GB para una
# pregunta que se contesta antes de transcribir nada.
SONDA = os.path.join(W, "ggml-small.bin")

# Lo que ggml imprime al registrar el backend. Es la unica prueba de que la
# tarjeta esta puesta: que exista el binario no dice nada, y que exista el
# driver tampoco (aprendizaje 18 — la ausencia de fallo no es una confirmacion).
TARJETA = re.compile(r"ggml_vulkan: \d+ = ([^|]+?)\s*\|")
USANDO = re.compile(r"using (\w+) backend")

APAGADA = os.environ.get("VIDEO_GPU", "1") == "0"


def _wav_de_sonda():
    """Un segundo de silencio, escrito aqui: la sonda no depende de ffmpeg."""
    p = os.path.join(rutas.temporal("gpu"), "sonda.wav")
    if not os.path.exists(p):
        with wave.open(p, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(b"\0" * 32000)
    return p


def _sondar():
    """Arranca whisper de verdad y lee lo que dice de si mismo."""
    if not os.path.exists(CLI):
        return {"tarjeta": None, "backend": None,
                "por_que": ("no hay build de Vulkan en whisper.cpp/  ->  la"
                            " receta esta en docs/entorno.md")}
    if not os.path.exists(SONDA):
        return {"tarjeta": None, "backend": None,
                "por_que": f"falta {SONDA}, que es con lo que se sondea"}
    r = subprocess.run([CLI, "-m", SONDA, "-f", _wav_de_sonda(), "-l", "es",
                        "-nf", "-t", "2"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    err = (r.stderr or b"").decode("utf8", "replace")
    tarjeta = TARJETA.search(err)
    usando = USANDO.search(err)
    if not tarjeta or not usando or usando.group(1).lower().startswith("cpu"):
        return {"tarjeta": tarjeta.group(1).strip() if tarjeta else None,
                "backend": None,
                "por_que": ("el binario corre en CPU: es una build sin backend"
                            " de GPU  ->  docs/entorno.md, gotcha 4")}
    return {"tarjeta": tarjeta.group(1).strip(), "backend": usando.group(1),
            "por_que": ""}


def esta(refrescar=False):
    """Que hay, y si no hay tarjeta **por que no**.

    Se guarda contra la huella del binario —tamano y fecha— porque la respuesta
    solo cambia cuando cambia la build, y sondear cuesta unos segundos que no
    tiene sentido pagar en cada una de las 378 ventanas de una corrida.
    """
    if APAGADA:
        return {"tarjeta": None, "backend": None,
                "por_que": "apagada a mano con VIDEO_GPU=0"}
    huella = (f"{os.path.getsize(CLI)}:{int(os.path.getmtime(CLI))}"
              if os.path.exists(CLI) else "sin-binario")
    cache = os.path.join(rutas.temporal("gpu"), "estado.json")
    if not refrescar and os.path.exists(cache):
        try:
            d = json.load(open(cache, encoding="utf-8"))
            if d.get("huella") == huella:
                return d
        except Exception:                          # noqa: BLE001
            pass
    d = _sondar()
    d["huella"] = huella
    json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d


def whisper():
    """El binario que toca, ya resuelto. **El unico sitio que elige.**

    Los ocho scripts que llaman a whisper escribian la ruta a mano, y esa es la
    forma en que C-56 se convirtio en un fallo: cuando `main.exe` paso a ser un
    stub que sale con exito sin transcribir, hubo que corregirlo en ocho sitios.
    Un solo seam hace que el proximo cambio de binario sea una linea.
    """
    if esta()["backend"] or not os.path.exists(CLI_CPU):
        return [CLI]
    return [CLI_CPU]


def sello():
    """Que produjo este transcript. Va al fichero, no a la pantalla."""
    d = esta()
    return f"{d['backend'].lower()}:{d['tarjeta']}" if d["backend"] else "cpu"


# ── decodificar video por la tarjeta ────────────────────────────────────────
# El otro sitio donde la CPU hacia trabajo de tarjeta, y es el mismo motivo: los
# brutos son 4K y **todo lo que mide un frame los decodifica enteros en CPU**.
#
# Medido sobre el bruto del reel 1, con las formas de llamada que usan de verdad
# los scripts, no con una inventada:
#
#   un frame con busqueda (medir-sujeto, focus-check, punch-ins, reading-detect)
#       1,47 s -> 0,65 s   **2,27x**   salida bit a bit igual en 4 instantes
#   barrido con signalstats (light-analysis), 120 s de cinta
#       85,5 s -> 30,8 s   **2,77x**   las 725 lineas de numeros, identicas
#
# **Y hay una condicion, que casi se cuela.** Una prueba dio «mismo tamano,
# bytes distintos» y la causa no era la tarjeta: era que la prueba no fijaba el
# formato de salida. Con aceleracion los frames vuelven en NV12, asi que sin un
# `format=` explicito ffmpeg puede entregar otro empaquetado.
#
# **Y la condicion no es la que estaba escrita aqui.** Decia que declarar el
# formato bastaba —«`format=gray`, `-pix_fmt rgb24`, identica pixel a pixel: 0
# de 4.369.920 distintos»— y eso es falso para `rgb24`. Medido de nuevo sobre
# tres frames de `hook-zoom.mp4`: **6.165.139 de 6.220.800 pixeles distintos, el
# 99,1%**, diferencia media 1,11 por canal y maxima 39.
#
# La condicion real es **no cruzar croma**. `format=gray` se queda con el plano
# Y, que es identico en NV12 y en yuv420p, y `format=yuv420p` para recodificar
# tampoco lo cruza; por eso las trece llamadas que ya usan esto salen iguales.
# `rgb24` si lo cruza, y swscale interpola el croma entrelazado de NV12 distinto
# del planar. Esos pixeles alimentan la segmentacion y acaban en el frame
# entregado.
#
# Asi que esto no se enchufa a cualquier ffmpeg: se enchufa al que **no cruza
# croma**. Y la unica ruta `rgb24` del repo —`text-behind.py`— ademas no lo
# necesita: medida, la tarjeta va mas LENTA (0,74 s -> 0,86 s, 0,86x) y el
# decodificado es el 1,6% de su corrida.
DECODIFICADOR = ["-hwaccel", "d3d11va"]


def _sondar_video():
    """Decodifica de verdad un h264 diminuto con la tarjeta. Si no, no vale.

    **No cuelga de `esta()`**, y estuvo a punto: son dos caminos distintos.
    `esta()` dice si whisper tiene backend de Vulkan; esto dice si ffmpeg sabe
    decodificar por D3D11. Puede haber lo segundo sin lo primero —basta el
    driver— y atarlos habria tirado 2,5x por una comprobacion que no tocaba.

    `ffmpeg -hwaccels` tampoco sirve: lista lo que el binario trae compilado,
    no lo que la maquina hace. Aqui salen siete y esta tarjeta no hace ni cuda
    ni qsv ni vaapi.
    """
    muestra = os.path.join(rutas.temporal("gpu"), "sonda.mp4")
    if not os.path.exists(muestra):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                            "-i", "testsrc=size=320x240:rate=5:duration=1",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", muestra],
                           capture_output=True)
        if r.returncode or not os.path.exists(muestra):
            return {"decodificador": None,
                    "por_que": "no se pudo crear la muestra: ¿hay ffmpeg?"}
    r = subprocess.run(["ffmpeg", "-v", "error"] + DECODIFICADOR
                       + ["-i", muestra, "-vf", "format=gray",
                          "-f", "rawvideo", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        return {"decodificador": None,
                "por_que": f"d3d11va no decodifica: "
                           f"{(r.stderr or b'')[-120:].decode('utf8', 'replace')}"}
    return {"decodificador": DECODIFICADOR[1], "por_que": ""}


def video(refrescar=False):
    """Si la tarjeta puede decodificar video, y si no por que no."""
    if APAGADA:
        return {"decodificador": None, "por_que": "apagada con VIDEO_GPU=0"}
    cache = os.path.join(rutas.temporal("gpu"), "video.json")
    if not refrescar and os.path.exists(cache):
        try:
            return json.load(open(cache, encoding="utf-8"))
        except Exception:                          # noqa: BLE001
            pass
    d = _sondar_video()
    json.dump(d, open(cache, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return d


def decodifica():
    """Lo que hay que ponerle a ffmpeg ANTES del `-i`. Vacio es «en CPU».

    Va delante del `-i` a proposito: `-hwaccel` es una opcion de entrada y
    detras del fichero no hace nada — **y no avisa**, simplemente decodifica en
    CPU al doble de tiempo. Es la forma barata de creer que se acelero algo.
    """
    return list(DECODIFICADOR) if video()["decodificador"] else []


def aviso_si_cae(script):
    """Caerse a CPU sin decirlo es el fallo de C-48: lento y callado.

    Una corrida que iba a durar cuarenta minutos y dura ochenta no se nota
    mientras pasa; se nota al dia siguiente, y para entonces ya nadie sabe por
    que. Asi que la caida se anota, con el motivo, antes de empezar.
    """
    d = esta()
    if not d["backend"]:
        registro.aviso(script, "whisper va por CPU", detalle=d["por_que"],
                       eco=False)
    return d


# ── la medida ───────────────────────────────────────────────────────────────
# Las mismas banderas que usa `transcribir.pasada()`. Si alli cambian, aqui
# tambien: una medida con otras banderas no compara este paso, compara otro.
BANDERAS = ["-l", "es", "-mc", "0", "-ml", "1", "-sow", "-ojf", "-np", "-nf",
            "-bs", "1", "-bo", "1", "-t", "12", "-nfa"]


def _corre(wav, modelo, exe, etiqueta):
    salida = os.path.join(rutas.temporal("gpu"), etiqueta)
    t = time.perf_counter()
    from transcribir import ALINEA

    subprocess.run([exe, "-m", modelo, "-f", wav, "-of", salida] + BANDERAS
                   + ["-dtw", ALINEA[os.path.basename(modelo)]],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dt = time.perf_counter() - t
    if not os.path.exists(salida + ".json"):
        return dt, None
    d = json.load(open(salida + ".json", encoding="utf-8"))
    return dt, " ".join(w["text"].strip() for w in d.get("transcription", []))


# Suelo de parecido para dar la tarjeta por buena, y **sale de los datos**. El
# acuerdo entre las tres pasadas de una corrida normal es 0,817 de media sobre
# 679 tramos: por encima de ese numero la GPU discrepa menos de lo que la propia
# linea ya arbitra. Por debajo no es «otra pasada», es un backend roto.
#
# Empezo siendo 0,98 —el numero que salio de mirar UNA ventana— y habria
# rechazado la tarjeta que si sirve. Un umbral copiado de una sola muestra es
# una superstición con decimales.
SUELO = 0.80


def medir(wavs, modelo=None):
    """CPU contra GPU sobre las MISMAS ventanas. **Varias, no una.**

    Con una ventana esto decia 1,000 y la conclusion habria sido «da igual».
    Con ocho: 3 identicas, media 0,91, una en 0,56. La medida de una muestra no
    era falsa, era irrelevante — que es peor, porque no se nota.

    El lado de CPU es `whisper-cli-cpu.exe`, o sea **lo que se corria antes**, y
    no la build de Vulkan con `-ng`. Contra el `-ng` saldria 2,64x en vez de
    1,84x: una cifra inflada, porque mediria de propina los backends de CPU por
    microarquitectura que la build estatica no trae.
    """
    modelo = modelo or os.path.join(W, "ggml-medium.bin")
    cpu = CLI_CPU if os.path.exists(CLI_CPU) else CLI
    t_cpu = t_gpu = 0.0
    pareceres, iguales = [], 0
    for i, wav in enumerate(wavs):
        a_dt, a = _corre(wav, modelo, cpu, "medida-cpu")
        b_dt, b = _corre(wav, modelo, CLI, "medida-gpu")
        if not a or not b:
            return {"error": f"sin texto en {os.path.basename(wav)}"}
        t_cpu += a_dt
        t_gpu += b_dt
        r = difflib.SequenceMatcher(None, a.split(), b.split()).ratio()
        pareceres.append((os.path.basename(wav), round(r, 4)))
        iguales += r >= 1.0
    media = sum(r for _, r in pareceres) / len(pareceres)
    return {"cpu": round(t_cpu, 1), "gpu": round(t_gpu, 1),
            "veces": round(t_cpu / t_gpu, 2) if t_gpu else None,
            "igual": round(media, 3), "peor": min(r for _, r in pareceres),
            "identicas": f"{iguales}/{len(pareceres)}", "detalle": pareceres,
            "sirve": bool(media >= SUELO and t_gpu < t_cpu)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--medir", action="store_true",
                    help="CPU contra GPU sobre ventanas reales")
    ap.add_argument("--wav", nargs="+", metavar="WAV",
                    help="las ventanas con que medir (acepta comodines)")
    a = ap.parse_args()

    d = esta(refrescar=True)
    if d["backend"]:
        print(f"whisper va por {d['backend']} · {d['tarjeta']}")
    else:
        print(f"whisper va por CPU — {d['por_que']}")
    v = video(refrescar=True)
    if v["decodificador"]:
        print(f"video se decodifica por {v['decodificador']}")
    else:
        print(f"video se decodifica en CPU — {v['por_que']}")

    if not a.medir:
        return
    # Con una ventana la respuesta no vale: la primera medida salio 1,000 y la
    # de ocho salio 0,91. Se exige material de sobra, no un tono ni un trozo.
    if not a.wav or len(a.wav) < 4:
        raise SystemExit("hace falta --wav con AL MENOS cuatro ventanas de"
                         " material real: con una, la medida enganó una vez")
    m = medir(a.wav)
    if "error" in m:
        raise SystemExit(m["error"])
    for nombre, r in m["detalle"]:
        print(f"    {nombre:<16} igual {r:.4f}")
    print(f"  CPU {m['cpu']}s · GPU {m['gpu']}s · {m['veces']}x · parecido medio"
          f" {m['igual']} (peor {m['peor']}, idénticas {m['identicas']})")
    print("  " + (f"la tarjeta sirve: discrepa menos ({m['igual']}) de lo que"
                  f" discrepan entre sí las tres pasadas (0,817)"
                  if m["sirve"] else
                  f"la tarjeta NO sirve: parecido {m['igual']} por debajo de"
                  f" {SUELO}, o no es más rápida"))
    registro.nota("gpu", "medida CPU/GPU",
                  detalle=f"{m['cpu']}s -> {m['gpu']}s ({m['veces']}x),"
                          f" parecido medio {m['igual']} en {len(a.wav)} ventanas")


if __name__ == "__main__":
    main()
