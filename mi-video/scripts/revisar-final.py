"""Escucha el ARRANQUE y el CIERRE de cada reel montado.

Los dos extremos son los que deciden: el arranque, si alguien se queda; el
cierre, si alguien actúa. Y es donde más barato sale equivocarse sin enterarse —
`reel-01` terminaba en «cada semana le podría estar costando, cada semana le
puede estar costando, cada semana», tres intentos y cortado a mitad.

Se transcribe el trozo, no el fichero entero: sobre el fichero completo whisper
alucina y no prueba nada.
"""
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
import rutas  # noqa: E402

W = os.path.join(os.path.dirname(__file__), "..", "whisper.cpp")
# Nunca en C:: es el disco de arranque y ya se lleno una vez a mitad de render.
WAV = os.path.join(rutas.TEMPORAL, "revisar-final.wav")
VENTANA = 6.0


def dur(p):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())


def oir(p, ini, fin):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{ini}", "-to", f"{fin}",
                    "-i", p, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                    WAV], check=True)
    # whisper.cpp escribe UTF-8; sin decirlo, Python lo lee con la consola de
    # Windows y «dólares» sale «dÃ³lares».
    r = subprocess.run([os.path.join(W, "whisper-cli.exe"), "-m",
                        os.path.join(W, "ggml-medium.bin"), "-l", "es",
                        "-mc", "0", "-nt", "-f", WAV],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return " ".join(r.stdout.split())


for p in sys.argv[1:]:
    d = dur(p)
    print(f"\n=== {os.path.basename(p)}  {d:.1f}s ===")
    print(f"  abre : {oir(p, 0, VENTANA)}")
    print(f"  cierra: {oir(p, max(0, d - VENTANA), d)}")
