"""El cerrojo: ningún agente toca la línea a mano. Lo que no está permitido, no pasa.

    python hooks/no-a-mano.py            # PreToolUse: JSON de la herramienta por stdin
    python hooks/no-a-mano.py --probar   # los casos que lo prueban (corre al desplegar)

Jaime, 14-11-2026, tras doce horas para un vídeo de minuto y medio: *«siempre
que tú entras a manipular la máquina, siempre pasa lo mismo»*. Y el 16-11, sobre
la máquina publicada como habilidad: *«también tiene que ser radical la
imposibilidad de que tú lo toques o lo modifiques a mano»*.

**Era una lista de lo prohibido, y lo que no estaba en la lista pasaba** (C-734).
Ahora es al revés. Hay **zonas**: la línea en marcha, la base, los documentos de
escena, de pieza y de guion, las declaraciones, la carpeta de configuración y
este mismo cerrojo. Dentro de una zona sólo pasa lo declarado aquí:
- **leer**: un comando sin señales de escritura, y la base sólo con `mode=ro`;
- **las órdenes de la línea**, por su script (`PERMITIDOS`);
- **hacer de piñón**: escribir la respuesta de un pedido (`*.respuesta.json`);
- **apuntar una corrección** en el log de la configuración.

Cualquier otro intérprete, redirección, copia o consulta que escriba dentro de
una zona se deniega. El cerrojo se protege a sí mismo: no se edita desde una
sesión, ni el fichero ni los `settings` que lo enchufan.

Sale con 2 —y el motivo por stderr— si deniega; con 0 si deja pasar.
"""
import json
import os
import re
import sys

MOTIVO = ("Cerrojo: {que}. La línea no se toca a mano: si se para, se queda parada "
          "y se informa con el motivo. Lo que sí: arreglar el código en el repo y "
          "desplegar, contestar pedidos (*.respuesta.json) y anotar lo que dice "
          "Jaime con ticket.py --de.")

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _norm(s):
    return (s or "").replace("\\", "/").lower()


def _de_json(ruta, *claves, defecto=None):
    try:
        d = json.load(open(os.path.join(AQUI, ruta), encoding="utf-8"))
        for k in claves:
            d = d[k]
        return d
    except (OSError, ValueError, KeyError, TypeError):
        return defecto


#: La línea en marcha: la de `rutas.json` y, si no hay, la de siempre.
LINEA = _norm(_de_json("mi-video/rutas.json", "linea", "raiz", defecto="F:/linea")).rstrip("/")
CONFIG = "/" + _norm(_de_json("separacion.json", "raiz_configuracion",
                              defecto="configuracion")).strip("/") + "/"
ZONAS = (LINEA + "/", "/" + LINEA.replace(":", "", 1) + "/", CONFIG, ".db",
         "/escenas/e", "pieza.json", "guion.json", "estado.json", "frames.json",
         "glosario.json", "decisiones.db", "apoyo.json")
#: El cerrojo mismo y lo que lo enchufa.
PROPIO = ("hooks/no-a-mano.py", "hooks/hooks.json", ".claude/settings.json",
          ".claude/settings.local.json", ".claude/hooks/")

#: Escritura permitida dentro de una zona, por la herramienta de ficheros.
ESCRIBE_SI = (re.compile(r"/work/servicio/[^/]+/[^/]+\.respuesta\.json\Z"),
              re.compile(re.escape(CONFIG) + r"docs/correcciones\.md\Z"))
#: Las órdenes de la línea que puede dar un agente, por el nombre del script.
PERMITIDOS = {"donde.py", "monitor.py", "verdad.py", "cola.py", "desplegar.py",
              "arrancar.sh", "consulta.py", "tablero.py", "ticket.py", "guia.py",
              "separacion.py", "tamano.py", "alcance.py", "guardas.mjs"}
INTERPRETE = re.compile(r"^(?:\S+=\S+\s+)*(python3?|py|node|bash|sh|pwsh|powershell|npx|"
                        r"npm|cmd|uv|deno|bun)(\.exe)?\b")
ESCRIBE = re.compile(r"(^|[\s;&|(])(cp|mv|rm|tee|touch|ln|mkdir|rmdir|sed\s+-i|ffmpeg|"
                     r"copy-item|move-item|remove-item|new-item|set-content|add-content|"
                     r"out-file|rename-item|truncate|dd|install|rsync|robocopy|xcopy)\b"
                     r"|>|\.write|open\([^)]*['\"][wax+]|unlink|rmtree|replace\(|"
                     r"os\.remove|shutil|\.rename|\.commit\(|writefile|appendfile")
SQL = re.compile(r"\b(insert\s+(or\s+\w+\s+)?into|delete\s+from|update\s+\w+\s+set|"
                 r"drop\s+table|alter\s+table|create\s+table|replace\s+into)\b")


class Denegado(Exception):
    pass


def _niega(que):
    raise Denegado(que)


def _en_zona(r):
    return any(z in r for z in ZONAS)


def fichero(ruta):
    r = _norm(ruta)
    if any(p in r for p in PROPIO):
        _niega(f"editar {ruta}: el cerrojo no se toca desde una sesión")
    if _en_zona(r) and not any(p.search(r) for p in ESCRIBE_SI):
        _niega(f"escribir en {ruta}, que es la línea, la base, un documento de la "
               "pieza o la configuración")


def _segmentos(c):
    """Los trozos de un comando, cortando por `&&`, `||`, `;`, `|` fuera de comillas."""
    out, actual, q, i = [], "", None, 0
    while i < len(c):
        ch = c[i]
        if q:
            q = None if ch == q else q
        elif ch in "\"'":
            q = ch
        elif ch in ";|&\n":
            out.append(actual)
            actual, i = "", i + (2 if c[i:i + 2] in ("&&", "||") else 1)
            continue
        actual += ch
        i += 1
    return [s.strip() for s in out + [actual] if s.strip()]


def _script(s):
    m = re.search(r"([\w.-]+\.(?:py|mjs|sh|js))\b", s)
    return m.group(1) if m else None


def _orden(s):
    """Un trozo de comando dentro de una zona: ¿qué lo deja pasar?"""
    if s.startswith("cd ") or s == "cd":
        return
    if "--volver" in s:
        _niega("devolver una pieza de fase con --volver")
    if "ticket.py" in s and re.search(r"--(cerrar|ruta|estado)\b", s):
        _niega("cerrar o reencaminar tiquets: los cierra Jaime")
    if "ticket.py" in s and "--ver" not in s and "--de" not in s:
        _niega("abrir un tiquet sin `--de`: sólo se anota lo que dice Jaime")
    if "guia.py" in s and "--aprobar" in s and "--de" not in s:
        _niega("aprobar la guía sin `--de`: la aprobación es de Jaime, con sus palabras")
    if SQL.search(s) or ("sqlite" in s and "mode=ro" not in s) or "basedatos.abrir" in s:
        _niega("tocar la base: sólo se lee, y con mode=ro")
    if "import servicios" in s or "from servicios" in s:
        _niega("llamar a un paso de la línea a mano")
    if INTERPRETE.search(s):
        guion = _script(s)
        if guion in PERMITIDOS:
            return
        if guion or ESCRIBE.search(s) or not re.search(r"\s-(c|e)\s", s + " "):
            _niega(f"correr `{guion or s[:40]}` sobre la línea: sólo pasan sus órdenes"
                   f" ({', '.join(sorted(PERMITIDOS))})")
        return  # código en línea que sólo lee
    if ESCRIBE.search(s):
        _niega("escribir en la línea, la base o la configuración desde un comando")


def comando(cmd):
    c = re.sub(r"\d?>\s*(/dev/null|&\d|\$null|nul)\b", " ", _norm(cmd))
    if any(p in c for p in PROPIO) and (ESCRIBE.search(c) or "git rm" in c
                                        or "git checkout" in c or "git restore" in c):
        _niega("tocar el cerrojo desde un comando")
    if not _en_zona(c):
        return
    for s in _segmentos(c):
        _orden(s)


def decide(d):
    t, i = d.get("tool_name", ""), d.get("tool_input") or {}
    if t in ("Write", "Edit", "NotebookEdit", "MultiEdit"):
        fichero(i.get("file_path") or i.get("notebook_path"))
    elif t in ("Bash", "PowerShell") or t.startswith("mcp__terminal__run_in_terminal"):
        comando(i.get("command"))


CASOS = [
    ("Write", {"file_path": "F:/linea/datos/ads/reel-23/x.json"}, False),
    ("Write", {"file_path": "F:/linea/codigo/mi-video/work/servicio/disenar/reel-23.respuesta.json"}, True),
    ("Edit", {"file_path": "F:/Edicion de video/configuracion/docs/canon.md"}, False),
    ("Edit", {"file_path": "F:/Edicion de video/configuracion/docs/correcciones.md"}, True),
    ("Write", {"file_path": "F:/x/mi-video/ads/reel-23/escenas/e02.json"}, False),
    ("Edit", {"file_path": "F:/x/hooks/no-a-mano.py"}, False),
    ("Edit", {"file_path": "F:/x/.claude/settings.json"}, False),
    ("Write", {"file_path": "F:/x/mi-video/scripts/guia.py"}, True),
    ("Bash", {"command": "sqlite3 F:/linea/datos/ads/decisiones.db \"update video set x=1\""}, False),
    ("Bash", {"command": "cd F:/linea/codigo/mi-video && python scripts/donde.py"}, True),
    ("Bash", {"command": "cd F:/linea/codigo/mi-video && python scripts/avanzar.py 23"}, False),
    ("Bash", {"command": "cp a.json F:/linea/datos/work/x.json"}, False),
    ("Bash", {"command": "ls F:/linea/datos/out && tail -5 F:/linea/datos/work/disparador.log"}, True),
    ("Bash", {"command": "python -c \"import sqlite3; sqlite3.connect('file:F:/linea/datos/ads/decisiones.db?mode=ro', uri=True)\""}, True),
    ("Bash", {"command": "python -c \"open('F:/linea/datos/ads/x','w').write('1')\""}, False),
    ("Bash", {"command": "cd F:/linea/codigo/mi-video && python scripts/dominio/ticket.py reel-03 30 \"x\" --de entrega"}, True),
    ("Bash", {"command": "cd F:/linea/codigo/mi-video && python scripts/dominio/ticket.py --cerrar 4 x"}, False),
    ("PowerShell", {"command": "Set-Content F:\\linea\\datos\\x.txt 1"}, False),
    ("Bash", {"command": "git rm hooks/no-a-mano.py"}, False),
    ("Bash", {"command": "python scripts/desplegar.py --aunque-haya-pedidos"}, True),
]


def probar():
    malos = 0
    for t, i, pasa in CASOS:
        try:
            decide({"tool_name": t, "tool_input": i})
            ok = pasa
        except Denegado:
            ok = not pasa
        if not ok:
            malos += 1
            print(f"  NO {t} {i} debía {'pasar' if pasa else 'denegarse'}")
    print(f"cerrojo: {len(CASOS) - malos}/{len(CASOS)} casos en pie")
    return 1 if malos else 0


def main():
    sys.stderr.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    if "--probar" in sys.argv:
        sys.exit(probar())
    try:
        d = json.load(sys.stdin)
    except ValueError:
        return
    try:
        decide(d)
    except Denegado as e:
        print(MOTIVO.format(que=e), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
