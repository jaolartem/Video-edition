"""Verifica un render troceandolo, no de una pasada.

Regla del proyecto (aprendizaje 1 de la seccion de revision): **la
transcripcion de un fichero entero no es prueba de nada — la de sus trozos,
si.** Whisper alucina sobre clips cortos tomados enteros; en un render de 8 s
llego a repetir «eso no es mala suerte» tres veces. Troceado de dos en dos
segundos aparecio la frase real.

Comprueba los dos extremos que exige la regla de gancho: que abra donde debe y
que **cierre la frase**. Un gancho que corta a mitad de idea no se manda.
"""
import subprocess, sys, json, os, shutil

sys.path.insert(0, os.path.dirname(__file__))
import gpu  # noqa: E402
import rutas  # noqa: E402

WH = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
# El binario lo elige `gpu.py`, que es el unico que sabe si hay tarjeta.
MAIN = gpu.whisper()[0]
MODEL = os.path.join(WH, "ggml-medium.bin")
VENTANA = 2.0
# Solape entre ventanas. Sin el, la ULTIMA ventana era el resto —a veces 0,8 s—
# y whisper devuelve vacio para trozos tan cortos: parecia que el gancho acababa
# en silencio cuando lo que fallaba era la ventana. Con solape, cada instante
# —el final incluido— cae dentro de al menos una ventana de tamano completo.
SOLAPE = 1.0
# Por debajo de esto un trozo no da lectura fiable, asi que no se pide.
MINIMO = 1.4


def dur(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
    return float(out.stdout.strip())


def trozo(path, ini, fin, wav):
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{ini}", "-to", f"{fin}",
         "-i", path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
        check=True)


def transcribir(wav):
    # -mc 0: sin contexto entre ventanas. Con contexto, un trozo arrastra lo
    # que "leyo" en el anterior y se inventa la continuidad — que es justo lo
    # que este metodo intenta descartar.
    subprocess.run(
        [MAIN, "-m", MODEL, "-l", "es", "-mc", "0", "-nt", "-oj",
         "-of", wav[:-4], "-f", wav],
        capture_output=True, check=True)
    with open(wav[:-4] + ".json", encoding="utf-8") as fh:
        data = json.load(fh)
    return " ".join(s["text"].strip() for s in data["transcription"]).strip()


def main(path):
    total = dur(path)
    tmp = rutas.temporal("verif-" + os.path.basename(path).replace(".mp4", ""))
    print(f"\n=== {os.path.basename(path)}  ({total:.2f}s) ===")
    texto = []
    try:
        t = 0.0
        while True:
            fin = min(t + VENTANA, total)
            # La ultima ventana se ANCLA AL FINAL en vez de encogerse: asi el
            # cierre se lee dentro de una ventana entera, que es justo lo que
            # hay que comprobar.
            if fin - t < MINIMO:
                t = max(0.0, total - VENTANA)
                fin = total
            wav = os.path.join(tmp, f"c{int(t*10):04d}.wav")
            trozo(path, t, fin, wav)
            txt = transcribir(wav)
            print(f"  [{t:5.1f}–{fin:5.1f}]  {txt}")
            texto.append(txt)
            if fin >= total:
                break
            t += VENTANA - SOLAPE
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    completo = " ".join(texto)
    print(f"  --> {completo}")
    # El cierre: si acaba sin puntuacion terminal, la frase probablemente
    # sigue. No es prueba —Whisper puntua a su criterio— pero es la senal
    # barata de "mira esto dos veces".
    if completo and completo.rstrip()[-1] not in ".?!…":
        print("  AVISO: no cierra con puntuacion terminal — revisar el final")

    # Alucinacion de despedida = hay silencio en la ventana.
    #
    # Whisper aprendio de video de YouTube, asi que cuando se queda sin voz
    # rellena con la coletilla del final. En gancho-R6 salio «Gracias por ver el
    # video. ¡Hasta la proxima!» — y no era que el gancho acabara mudo, sino que
    # dentro de la ventana habia medio segundo de silencio. **La alucinacion es
    # un detector de silencio gratis**: no dice donde, pero dice que hay.
    DESPEDIDAS = ("gracias por ver", "hasta la proxima", "hasta la próxima",
                  "suscrib", "no olvides", "subtitulos realizados")
    bajo = completo.lower()
    if any(x in bajo for x in DESPEDIDAS):
        print("  AVISO: coletilla de despedida en el texto — es alucinacion "
              "sobre SILENCIO. Mirar el nivel por tramos, no el texto.")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
