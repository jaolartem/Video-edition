"""El cerrojo: la sesión no empuja la línea a mano.

Jaime, 14-11-2026, tras doce horas para un vídeo de minuto y medio: *«siempre
que tú entras a manipular la máquina, siempre pasa lo mismo»*. Ese día la sesión
declaró a mano el contenido de una pieza, la devolvió de fase cinco veces,
escribió en la base y abrió tiquets con criterio propio; cada intervención
arreglaba algo y rompía otra cosa.

Mi papel es cuidar la máquina (código, en el repo, por `desplegar.py`) y hacer
de piñón (contestar pedidos con agentes, con el encargo de `cola.py`). Lo demás
lo hace la línea. Si la línea se para, se queda parada y se le cuenta a Jaime.

PreToolUse: lee el JSON de la herramienta por stdin. Sale con 2 —y el motivo por
stderr— si la llamada toca la máquina por dentro; con 0 en cualquier otro caso.
"""
import json
import re
import sys

MOTIVO = ("Cerrojo (CLAUDE.md, «Lo que no hago»): {que}. La línea no se empuja a "
          "mano: si se para, se queda parada y se informa a Jaime con el motivo. "
          "Lo que sí: arreglar código en el repo y desplegar, o contestar pedidos "
          "con agentes y el encargo de cola.py.")

#: Ficheros que son memoria de la línea o declaración de Jaime, no código.
DATOS = ("f:/linea/datos", "f:/linea/codigo", "/f/linea/datos", "/f/linea/codigo")
DECLARACIONES = ("frames.json", "glosario.json", "decisiones.db", "apoyo.json")

#: Lo que delata que un comando escribe.
ESCRIBE = re.compile(r"(^|[\s;&|(])(cp|mv|rm|tee|touch|sed\s+-i|ffmpeg|copy-item|"
                     r"move-item|remove-item|new-item|set-content|out-file)\b|>"
                     r"|\.write\(|open\([^)]*['\"]w")
SQL = re.compile(r"\b(insert\s+(or\s+\w+\s+)?into|delete\s+from|update\s+\w+\s+set|"
                 r"drop\s+table|alter\s+table)\b")


def _bloquea(que):
    print(MOTIVO.format(que=que), file=sys.stderr)
    sys.exit(2)


def _fichero(ruta):
    r = (ruta or "").replace("\\", "/").lower()
    if any(r.startswith(d) or f"{d}/" in r for d in DATOS):
        _bloquea(f"escribir en {ruta}, que es la línea en marcha")
    if r.endswith(DECLARACIONES):
        _bloquea(f"editar a mano {ruta}: es declaración de Jaime o memoria de la "
                 "línea; entra por su script (`guion.py`, la ingesta), no por mí")


def _comando(cmd):
    c = (cmd or "").replace("\\", "/").lower()
    # Tirar la salida de errores no es escribir: `2>/dev/null`, `2>&1`.
    c = re.sub(r"\d?>\s*(/dev/null|&\d|\$null)", " ", c)
    if "--volver" in c:
        _bloquea("devolver una pieza de fase con --volver")
    if "ticket.py" in c and re.search(r"--(cerrar|ruta|estado)\b", c):
        _bloquea("cerrar o reencaminar tiquets: los atiende la línea")
    if "ticket.py" in c and "--ver" not in c and "--de" not in c:
        _bloquea("abrir un tiquet sin `--de`: sólo se anota lo que dice Jaime, "
                 "con su segundo")
    if re.search(r"\bdb\.py\b", c) or "basedatos.abrir" in c or "sqlite3" in c \
            or SQL.search(c):
        _bloquea("tocar la base directamente")
    if "from servicios" in c or "import servicios" in c:
        _bloquea("llamar a un paso de la línea a mano")
    if any(d in c for d in DATOS) and ESCRIBE.search(c):
        _bloquea("escribir en la línea en marcha desde un comando")
    if any(x in c for x in DECLARACIONES) and ESCRIBE.search(c):
        _bloquea("reescribir una declaración desde un comando")


def main():
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return
    t, i = d.get("tool_name", ""), d.get("tool_input") or {}
    if t in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        _fichero(i.get("file_path") or i.get("notebook_path"))
    elif t in ("Bash", "PowerShell"):
        _comando(i.get("command"))
    elif t.startswith("mcp__terminal__run_in_terminal"):
        _comando(i.get("command"))


if __name__ == "__main__":
    main()
