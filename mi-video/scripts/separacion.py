"""Máquina, configuración y producto: cada uno en su sitio, y comprobado.

    python scripts/separacion.py --comprobar    # falla si se mezclan
    python scripts/separacion.py --configurar   # trae la configuración al árbol
    python scripts/separacion.py --gitignore    # rehace el bloque de .gitignore

Jaime, 16-11-2026: *«a git solo va el esqueleto, lo funcional y lo ejecutado
debe ir en otra carpeta y en otro registro… esa separación tiene que ser
explícita; eso permite que se confunda la estructura con el producto»*, y *«una
cosa es lo que hace el proyecto y otra muy distinta las instrucciones o lo que
hago yo dentro de lo que utilizo ese proyecto»*.

**Lo declara `separacion.json`**, en la raíz del repo. Lo que no está en
`configuracion` ni en `producto` es máquina. La configuración vive en su propia
carpeta con su propio git, con las mismas rutas que tendría en el árbol, y entra
de dos maneras:
- **en la línea**, `desplegar.py` compone el árbol del commit de la máquina con
  el del commit de la configuración (`arbol_configuracion`);
- **en desarrollo**, `--configurar` la copia al árbol **de sólo lectura**. Una
  copia que se edita en el árbol se perdería en la siguiente vuelta, así que el
  sistema no deja editarla y `--comprobar` falla si alguien lo consiguió.

El código no cambia de rutas: `docs/canon.md` sigue siendo `docs/canon.md`. Lo
que cambia es de dónde sale, y eso queda escrito aquí.
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile

#: La raíz del repo: `mi-video/scripts/separacion.py` → dos `dirname` más.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFIESTO = os.path.join(REPO, "separacion.json")
MARCA_ABRE, MARCA_CIERRA = "# >>> separacion.json", "# <<< separacion.json"
#: Lo que es del propio git de la configuración, no del árbol de la máquina.
META = {".gitignore", ".gitattributes", "README.md"}


def _git(cwd, *a) -> str:
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def _patron(glob: str) -> re.Pattern:
    out, i = "", 0
    while i < len(glob):
        if glob.startswith("**", i):
            out, i = out + ".*", i + 2
        elif glob[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif glob[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(glob[i]), i + 1
    return re.compile(out + r"\Z")


class Separacion:
    """Lo que dice `separacion.json`, y cómo se cumple."""

    def __init__(self, manifiesto: str = MANIFIESTO):
        self.d = json.load(open(manifiesto, encoding="utf-8"))
        self.globs = {"producto": self.d["producto"],
                      "configuracion": [g for k, gs in self.d["configuracion"].items()
                                        if not k.startswith("_") for g in gs]}
        self._re = {c: [_patron(g) for g in gs] for c, gs in self.globs.items()}

    def clase(self, ruta: str) -> str:
        r = ruta.replace("\\", "/")
        for c in ("producto", "configuracion"):
            if any(p.match(r) for p in self._re[c]):
                return c
        return "maquina"

    @staticmethod
    def raiz_configuracion(d: dict | None = None) -> str:
        if os.environ.get("VIDEO_CONFIG"):
            return os.environ["VIDEO_CONFIG"]
        comun = os.path.abspath(os.path.join(REPO, _git(REPO, "rev-parse",
                                                        "--git-common-dir").strip()))
        rel = (d or json.load(open(MANIFIESTO, encoding="utf-8")))["raiz_configuracion"]
        return os.path.join(os.path.dirname(comun), rel)

    @property
    def raiz(self) -> str:
        return self.raiz_configuracion(self.d)

    def de_configuracion(self) -> list[str]:
        """Los ficheros que guarda el git de la configuración."""
        if not os.path.isdir(os.path.join(self.raiz, ".git")):
            return []
        return [f for f in _git(self.raiz, "ls-files").splitlines() if f and f not in META]

    # -- lo que se comprueba ------------------------------------------------
    def faltas(self) -> list[str]:
        out = []
        for f in _git(REPO, "ls-files").splitlines():
            c = self.clase(f)
            if c != "maquina":
                out.append(f"git versiona {f}, que es {c}")
        conf = self.de_configuracion()
        if not conf:
            out.append(f"no hay configuración en {self.raiz} (o no tiene git)")
        for f in conf:
            if self.clase(f) != "configuracion":
                out.append(f"la configuración guarda {f}, que el manifiesto no declara")
            aqui = os.path.join(REPO, f)
            if not os.path.exists(aqui):
                out.append(f"falta {f} en el árbol: corre separacion.py --configurar")
            elif open(aqui, "rb").read() != open(os.path.join(self.raiz, f), "rb").read():
                out.append(f"{f} difiere de la configuración: se edita en {self.raiz}")
        if self._bloque() not in open(os.path.join(REPO, ".gitignore"), encoding="utf-8").read():
            out.append(".gitignore no lleva el bloque de separacion.json: --gitignore")
        return out

    # -- lo que se hace -----------------------------------------------------
    def configurar(self) -> tuple[int, list[str]]:
        """Copia la configuración al árbol, de sólo lectura. `(copiados, choques)`."""
        n, choques = 0, []
        for f in self.de_configuracion():
            origen, aqui = os.path.join(self.raiz, f), os.path.join(REPO, f)
            if os.path.exists(aqui):
                if open(aqui, "rb").read() == open(origen, "rb").read():
                    os.chmod(aqui, stat.S_IREAD)
                    continue
                if os.path.getmtime(aqui) > os.path.getmtime(origen):
                    choques.append(f)  # se editó la copia después: no se pisa
                    continue
                os.chmod(aqui, stat.S_IWRITE | stat.S_IREAD)
            os.makedirs(os.path.dirname(aqui), exist_ok=True)
            shutil.copy2(origen, aqui)
            os.chmod(aqui, stat.S_IREAD)
            n += 1
        return n, choques

    def _bloque(self) -> str:
        lineas = [MARCA_ABRE, "# Generado por scripts/separacion.py --gitignore: no se edita a mano.",
                  "# la carpeta de la configuración, con su propio git",
                  "/" + self.d["raiz_configuracion"].strip("/") + "/"]
        for c in ("configuracion", "producto"):
            lineas += [f"# {c}"] + ["/" + g for g in self.globs[c]]
        return "\n".join(lineas + [MARCA_CIERRA])

    def gitignore(self) -> None:
        r = os.path.join(REPO, ".gitignore")
        t = open(r, encoding="utf-8").read()
        if MARCA_ABRE in t:
            t = t[:t.index(MARCA_ABRE)] + t[t.index(MARCA_CIERRA) + len(MARCA_CIERRA):].lstrip("\n")
        open(r, "w", encoding="utf-8", newline="\n").write(t.rstrip("\n") + "\n\n" + self._bloque() + "\n")

    def arbol_configuracion(self) -> tuple[str, dict]:
        """`(sha, {ruta: bytes})` del commit de la configuración, limpia."""
        if _git(self.raiz, "status", "--porcelain"):
            raise SystemExit(f"separacion: la configuración ({self.raiz}) tiene cambios sin"
                             " commit; se despliega un commit, no un árbol a medias.")
        sha = _git(self.raiz, "rev-parse", "HEAD").strip()
        tar = subprocess.run(["git", "archive", sha], cwd=self.raiz,
                             capture_output=True, check=True).stdout
        out = {}
        with tarfile.open(fileobj=io.BytesIO(tar)) as t:
            for m in t.getmembers():
                if m.isfile() and m.name not in META:
                    out[m.name] = t.extractfile(m).read()
        return sha, out


def main(argv=None) -> int:
    a = set(argv if argv is not None else sys.argv[1:])
    s = Separacion()
    if "--gitignore" in a:
        s.gitignore()
        print("separacion: bloque de .gitignore al día")
    if "--configurar" in a:
        n, choques = s.configurar()
        print(f"separacion: {n} ficheros de configuración copiados desde {s.raiz}")
        for f in choques:
            print(f"  NO se pisa {f}: la copia del árbol es más nueva que la configuración")
        if choques:
            return 1
    if "--comprobar" in a or not a:
        faltas = s.faltas()
        for f in faltas:
            print(f"  separacion: {f}")
        print(f"separacion: {'no pasa' if faltas else 'en orden'} ({len(faltas)} faltas)")
        return 1 if faltas else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
