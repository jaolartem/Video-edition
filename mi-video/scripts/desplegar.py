"""Pone la línea al día con un commit. Es la única puerta entre desarrollo y producción.

    python scripts/desplegar.py                # HEAD, comprobado
    python scripts/desplegar.py --ver          # qué cambiaría, sin tocar nada
    python scripts/desplegar.py --raiz F:/tmp-video/prueba   # una línea aislada

Jaime, 23-10-2026: *«hay que separar la aplicación funcionando del desarrollo; la
aplicación no debe estar guiada por git»*. Hasta hoy la línea corría del mismo
checkout donde se desarrollaba: cada merge la rearrancaba (C-629), un commit a
medias paraba el despacho (91 vueltas cortadas en diez días) y el estado de cinco
piezas publicadas se quedó sin commitear en el working tree.

Ahora la línea vive en `<raiz>` (`rutas.json` → `linea.raiz`, `F:/linea`):

    <raiz>/codigo/   el árbol del commit, y nada más que eso
    <raiz>/datos/    ads/, work/, out/, public/ y reels.json: la memoria de la línea
    <raiz>/nodo/     node_modules, compartido entre despliegues

Dentro de `codigo/mi-video/` los datos entran por enlaces de directorio, así que
ningún script cambia de ruta: `ads/decisiones.db` sigue siendo `ads/decisiones.db`.

**Sólo se copia lo que cambió**, y con la hora de ahora. `cadena._codigo` caduca un
eslabón cuando su productor es más nuevo que el artefacto: copiar el árbol entero
le pondría a todo la misma hora y la línea rehízo todas las piezas. Así sólo
caduca lo que de verdad cambió.
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mi-video/
CFG = json.load(open(os.path.join(AQUI, "rutas.json"), encoding="utf-8"))

#: Los datos de la línea: entran en `codigo/mi-video/` por enlace, no se copian.
DATOS = ("ads", "work", "out", "public")
#: El spec es un fichero que Remotion importa desde `src/`: va por enlace duro.
SPEC = os.path.join("src", "reels.json")

#: Lo que mira el CÓDIGO. Es lo que `montar.sh` corría en producción antes de
#: cada lote y ahora salta con `ya_desplegado`: se paga una vez, aquí.
COMPROBACIONES = [
    ("guardas", ["node", "scripts/guardas.mjs"]),
    ("verdad", [sys.executable, "scripts/verdad.py"]),
    ("contratos", [sys.executable, "scripts/contratos.py"]),
    ("comprobado", [sys.executable, "scripts/comprobado.py", "--solo-huecos"]),
    ("tamano", [sys.executable, "scripts/tamano.py"]),
    ("lint", ["npm", "run", "lint"]),
]


def _git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True,
                          cwd=AQUI, check=True).stdout.strip()


def comprobar():
    """`None` si todo pasa; si no, el nombre de la que falló."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    for nombre, orden in COMPROBACIONES:
        r = subprocess.run(orden, cwd=AQUI, env=env, capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           shell=(orden[0] == "npm"))
        print(f"  {'ok ' if r.returncode == 0 else 'NO '} {nombre}")
        if r.returncode != 0:
            print("\n".join((r.stdout + r.stderr).strip().splitlines()[-15:]))
            return nombre
    r = subprocess.run([sys.executable, "-m", "pyflakes", "scripts/"], cwd=AQUI,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    malos = [x for x in r.stdout.splitlines() if "undefined name" in x]
    print(f"  {'ok ' if not malos else 'NO '} nombres")
    if malos:
        print("\n".join(malos))
        return "nombres"
    return None


def arbol(sha) -> dict:
    """`{ruta: bytes}` del commit, sin tocar el working tree.

    Desde la raíz del repo: `git archive` lanzado en `mi-video/` empaqueta sólo
    esa carpeta, y sin `docs/` ni `.claude/` el despliegue sale cojo.
    """
    tar = subprocess.run(["git", "archive", sha], cwd=os.path.dirname(AQUI),
                         capture_output=True, check=True).stdout
    out = {}
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        for m in t.getmembers():
            if m.isfile():
                out[m.name] = t.extractfile(m).read()
    return out


def _enlace(enlace, destino):
    """Un enlace de directorio (junction): no pide permisos de administrador."""
    os.makedirs(destino, exist_ok=True)
    if os.path.lexists(enlace):
        return
    os.makedirs(os.path.dirname(enlace), exist_ok=True)
    subprocess.run(["cmd", "/c", "mklink", "/J", os.path.normpath(enlace),
                    os.path.normpath(destino)], check=True, capture_output=True)


def enlazar(raiz):
    """Los datos, el nodo y las herramientas compartidas, dentro del código."""
    mv = os.path.join(raiz, "codigo", "mi-video")
    for d in DATOS:
        _enlace(os.path.join(mv, d), os.path.join(raiz, "datos", d))
    _enlace(os.path.join(mv, "node_modules"), os.path.join(raiz, "nodo", "node_modules"))
    for nombre, ruta in (CFG.get("linea", {}).get("compartido") or {}).items():
        if not nombre.startswith("_"):
            _enlace(os.path.join(mv, nombre), ruta)
    spec, dato = os.path.join(mv, SPEC), os.path.join(raiz, "datos", "reels.json")
    if not os.path.exists(dato):
        open(dato, "w", encoding="utf-8").write("[]\n")
    if not os.path.exists(spec):
        os.makedirs(os.path.dirname(spec), exist_ok=True)
        os.link(dato, spec)


def _ajusta(nuevo, raiz):
    """El `rutas.json` de la línea escribe en sus datos, no en el repo."""
    clave = "mi-video/rutas.json"
    cfg = json.loads(nuevo[clave])
    cfg["destino"] = f"{raiz}/datos/out".replace("\\", "/")
    nuevo[clave] = (json.dumps(cfg, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def sincronizar(nuevo, raiz, ver=False):
    """Escribe lo que cambió y borra lo que salió del árbol. `(escritos, borrados)`."""
    codigo = os.path.join(raiz, "codigo")
    manifiesto = os.path.join(raiz, "datos", "despliegue.manifiesto.json")
    try:
        antes = set(json.load(open(manifiesto, encoding="utf-8")))
    except (OSError, ValueError):
        antes = set()
    escritos, ahora = [], time.time()
    for ruta, contenido in sorted(nuevo.items()):
        destino = os.path.join(codigo, ruta)
        try:
            if open(destino, "rb").read() == contenido:
                continue
        except OSError:
            pass
        escritos.append(ruta)
        if not ver:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            open(destino, "wb").write(contenido)
            os.utime(destino, (ahora, ahora))
    borrados = sorted(antes - set(nuevo))
    if not ver:
        for ruta in borrados:
            try:
                os.remove(os.path.join(codigo, ruta))
            except OSError:
                pass
        json.dump(sorted(nuevo), open(manifiesto, "w", encoding="utf-8"))
    return escritos, borrados


def nodo(raiz):
    """`npm ci` sólo si cambió el lock; si no, el `node_modules` de antes vale."""
    d = os.path.join(raiz, "nodo")
    lock = os.path.join(AQUI, "package-lock.json")
    if os.path.exists(os.path.join(d, "node_modules")) and os.path.exists(
            os.path.join(d, "package-lock.json")) and open(
            lock, "rb").read() == open(os.path.join(d, "package-lock.json"), "rb").read():
        return False
    os.makedirs(d, exist_ok=True)
    for f in ("package.json", "package-lock.json"):
        shutil.copy2(os.path.join(AQUI, f), os.path.join(d, f))
    subprocess.run("npm ci --no-audit --no-fund", cwd=d, shell=True, check=True)
    return True


def en_vuelo(raiz):
    """Pedidos de la línea sin contestar: desplegar encima los dejaría desfasados."""
    mv = os.path.join(raiz, "codigo", "mi-video")
    if not os.path.exists(os.path.join(mv, "scripts", "servicio.py")):
        return []
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'scripts');"
                        " import servicio; print('\\n'.join(f'{p}/{s}' for p, s, _ in"
                        " servicio.pendientes()))"], cwd=mv, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return [x for x in r.stdout.splitlines() if x.strip()]


def anotar(raiz, sha, rama, comprobado):
    """`DESPLIEGUE` al lado de `rutas.json`, y una fila en la base de la línea."""
    import sqlite3

    fecha = time.strftime("%Y-%m-%dT%H:%M:%S")
    d = {"sha": sha, "rama": rama, "fecha": fecha, "comprobado": comprobado}
    json.dump(d, open(os.path.join(raiz, "codigo", "mi-video", "DESPLIEGUE"), "w",
                      encoding="utf-8"), ensure_ascii=False)
    base = os.path.join(raiz, "datos", "ads", "decisiones.db")
    if os.path.exists(base):
        cx = sqlite3.connect(base, timeout=30)
        cx.execute("create table if not exists despliegue (id integer primary key,"
                   " sha text not null, rama text, fecha text not null,"
                   " comprobado integer not null)")
        cx.execute("insert into despliegue (sha, rama, fecha, comprobado) values (?,?,?,?)",
                   (sha, rama, fecha, int(comprobado)))
        cx.commit()
        cx.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref", nargs="?", default="HEAD")
    ap.add_argument("--raiz", default=CFG.get("linea", {}).get("raiz", "F:/linea"))
    ap.add_argument("--ver", action="store_true", help="dice qué cambiaría y no toca nada")
    ap.add_argument("--sin-comprobar", action="store_true",
                    help="emergencia: queda escrito en DESPLIEGUE que no se comprobó")
    ap.add_argument("--aunque-haya-pedidos", action="store_true")
    a = ap.parse_args()
    raiz = a.raiz.replace("\\", "/").rstrip("/")
    sha, rama = _git("rev-parse", a.ref), _git("rev-parse", "--abbrev-ref", "HEAD")

    if not a.ver and not a.sin_comprobar:
        if _git("rev-parse", "HEAD") != sha or _git("status", "--porcelain",
                                                     "--untracked-files=no"):
            raise SystemExit("desplegar: se comprueba el working tree, así que tiene que"
                             f" estar limpio y en {sha[:7]}. Haz commit o cambia de rama.")
        print(f"desplegar {sha[:7]}: comprobaciones del código")
        if comprobar():
            raise SystemExit("desplegar: no pasa; la línea sigue con lo que tenía.")
    vuelo = en_vuelo(raiz)
    if vuelo and not (a.ver or a.aunque_haya_pedidos):
        raise SystemExit("desplegar: hay pedidos sin contestar en la línea; si cambia"
                         " su contrato se archivan como desfasados:\n    "
                         + "\n    ".join(vuelo) + "\nContéstalos o pasa --aunque-haya-pedidos.")

    nuevo = arbol(sha)
    _ajusta(nuevo, raiz)
    if not a.ver:
        enlazar(raiz)
    escritos, borrados = sincronizar(nuevo, raiz, ver=a.ver)
    print(f"desplegar {sha[:7]} -> {raiz}/codigo: {len(escritos)} ficheros cambian,"
          f" {len(borrados)} salen")
    for r in (escritos[:20] if a.ver else []):
        print(f"    + {r}")
    if a.ver:
        return
    if nodo(raiz):
        print("  node_modules reinstalado: cambió el package-lock")
    anotar(raiz, sha, rama, not a.sin_comprobar)
    print(f"desplegado. La línea corre {sha[:7]}; el disparador rearranca solo si"
          " estaba puesto.")


if __name__ == "__main__":
    main()
