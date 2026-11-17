"""El cerrojo: ningún agente toca la línea a mano. Lo que no está permitido, no pasa.

    python hooks/no-a-mano.py            # PreToolUse: JSON de la herramienta por stdin
    python hooks/no-a-mano.py --probar   # los casos que lo prueban (corre al desplegar)

Jaime, 14-11-2026, tras doce horas para un vídeo de minuto y medio: *«siempre
que tú entras a manipular la máquina, siempre pasa lo mismo»*. Y el 16-11, sobre
la máquina publicada como habilidad: *«también tiene que ser radical la
imposibilidad de que tú lo toques o lo modifiques a mano»*.

**Era una lista de lo prohibido, y lo que no estaba en la lista pasaba** (C-734).
Ahora es al revés. Hay **zonas**, y son **la producción**: la línea en marcha,
la base, los documentos de escena, de pieza y de guion, y las declaraciones.
Dentro de una zona sólo pasa lo declarado aquí:
- **leer**: un comando sin señales de escritura, y la base sólo con `mode=ro`;
- **las órdenes de la línea**, por su script (`PERMITIDOS`);
- **hacer de piñón**: escribir la respuesta de un pedido (`*.respuesta.json`).

Cualquier otro intérprete, redirección, copia, consulta o `git` que escriba
dentro de una zona se deniega.

**Lo que se protege es la producción, no las herramientas** (C-754). Jaime,
17-11-2026: *«lo que debe estar cuidado y protegido no es el código, es la línea
de producción… tú no puedes tocar un video a mano, pero sí puedes editar y
manejar las herramientas que tocan los videos; y además actualizar la
documentación es parte de tu trabajo»*. El código, la configuración, las
instrucciones y este cerrojo se cambian en el repo y llegan a la línea por
`desplegar.py`, que corre `--probar`: así se cuida que nadie lo afloje.

Sale con 2 —y el motivo por stderr— si deniega; con 0 si deja pasar.
"""
import json
import os
import re
import sys

MOTIVO = ("Cerrojo: {que}. La línea no se toca a mano: si se para, se queda parada "
          "y se informa con el motivo. Lo que sí: arreglar el código en el repo y "
          "desplegar, contestar pedidos (*.respuesta.json) y anotar lo que dice "
          "el usuario con ticket.py --de.")

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#: El proyecto de la máquina: el abierto si es una máquina (tiene
#: `separacion.json`), si no el del propio cerrojo. Instalado como plugin en un
#: proyecto que no es la máquina, el cerrojo no hace nada.
BASE = next((d for d in (os.environ.get("CLAUDE_PROJECT_DIR"), AQUI)
             if d and os.path.isfile(os.path.join(d, "separacion.json"))), None)


def _norm(s):
    return (s or "").replace("\\", "/").lower()


def _de_json(ruta, *claves, defecto=None):
    try:
        d = json.load(open(os.path.join(BASE, ruta), encoding="utf-8"))
        for k in claves:
            d = d[k]
        return d
    except (OSError, ValueError, KeyError, TypeError):
        return defecto


#: La línea en marcha, la que declara la configuración (`rutas.json`).
LINEA = _norm(_de_json("mi-video/rutas.json", "linea", "raiz", defecto="")).rstrip("/")
#: Zonas por sitio: la línea entera. La configuración es herramienta (C-754).
SITIOS = tuple(z for z in (LINEA + "/" if LINEA else "", "/" + LINEA.replace(":", "", 1) + "/"
                           if LINEA else "") if z)
#: Zonas por nombre: sólo dentro de la máquina o de la línea, no en otro proyecto.
NOMBRES = (".db", "/escenas/e", "pieza.json", "guion.json", "estado.json", "frames.json",
           "glosario.json", "apoyo.json")

#: Escritura permitida dentro de una zona, por la herramienta de ficheros.
ESCRIBE_SI = (re.compile(r"/work/servicio/[^/]+/[^/]+\.respuesta\.json\Z"),)
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
    if any(z in r for z in SITIOS):
        return True
    absoluta = re.match(r"^([a-z]:/|/)", r)
    dentro = not absoluta or r.startswith(_norm(BASE).rstrip("/") + "/")
    return dentro and any(n in r for n in NOMBRES)


def fichero(ruta):
    r = _norm(ruta)
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
        _niega("cerrar o reencaminar tiquets: los cierra el usuario")
    if "ticket.py" in s and "--ver" not in s and "--de" not in s:
        _niega("abrir un tiquet sin `--de`: sólo se anota lo que dice el usuario")
    if "guia.py" in s and "--aprobar" in s and "--de" not in s:
        _niega("aprobar la guía sin `--de`: la aprobación es del usuario, con sus palabras")
    if SQL.search(s) or ("sqlite" in s and "mode=ro" not in s) or "basedatos.abrir" in s:
        _niega("tocar la base: sólo se lee, y con mode=ro")
    if "import servicios" in s or "from servicios" in s:
        _niega("llamar a un paso de la línea a mano")
    if re.search(r"\bgit\b.*\b(apply|checkout|restore|reset|rm|mv|clean|stash|am|"
                 r"cherry-pick|merge|pull|commit|switch|rebase)\b", s):
        _niega("escribir en la producción con git")
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
    ("Edit", {"file_path": "F:/Edicion de video/configuracion/docs/canon.md"}, True),
    ("Edit", {"file_path": "F:/Edicion de video/configuracion/CLAUDE.md"}, True),
    ("Write", {"file_path": "mi-video/ads/reel-23/escenas/e02.json"}, False),
    ("Write", {"file_path": "D:/otro-proyecto/datos.db"}, True),
    ("Edit", {"file_path": "F:/x/hooks/no-a-mano.py"}, True),
    ("Edit", {"file_path": "F:/x/.claude/settings.json"}, True),
    ("Bash", {"command": "cd F:/linea/codigo/mi-video && git apply cambio.patch"}, False),
    ("Bash", {"command": "git -C F:/linea/datos checkout -- ads/frames.json"}, False),
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
    ("Bash", {"command": "git commit -am 'cerrojo'"}, True),
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
    if BASE is None:
        return
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
