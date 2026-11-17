"""Publica la máquina en GitHub: sólo la máquina, en todo su historial.

    python scripts/maquina_publica.py --ver       # filtra en una copia y dice qué saldría
    python scripts/maquina_publica.py --primera   # la primera vez: reemplaza lo que haya
    python scripts/maquina_publica.py             # las siguientes: avanza sobre lo publicado

Jaime, 16-11-2026: *«a git solo va el esqueleto»*, y el repositorio público va
**sin la base**. El historial local no se toca: es el registro completo y
privado. Lo que se publica es una copia filtrada de él (C-735):
- fuera, de **todos** los commits, lo que `separacion.json` declara configuración
  o producto, y lo que el `.gitignore` de hoy ignora (la base, los vídeos, los
  datos de la línea), aunque en su día entrara;
- el correo de autor pasa al anónimo de GitHub;
- el texto personal que quedó en el código de entonces se sustituye
  (`SUSTITUYE`).

El filtrado es determinista: el mismo historial da los mismos commits, así que
cada publicación avanza sobre la anterior sin forzar.

Antes de subir comprueba que en la copia no queda ningún `.db`, vídeo, imagen,
fichero de configuración, correo, ni nada de `SUSTITUYE`, y si queda, no sube.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from separacion import REPO, Separacion  # noqa: E402

REMOTO = "git@github.com:jaolartem/Video-edition.git"
AUTOR = "jaolartem <110577537+jaolartem@users.noreply.github.com>"
COPIA = os.environ.get("VIDEO_PUBLICAR", "F:/tmp-video/publicar")
FILTER_REPO = os.environ.get("FILTER_REPO", "F:/tmp-video/herramientas/filter-repo")
#: Lo personal que quedó en el código de entonces: se cambia en todo el historial.
SUSTITUYE = [
    ("", ""),
    ("Los informes largos pierden lo importante", "Los informes largos pierden lo importante"),
]
#: Lo que no puede quedar en la copia publicada.
NO_SALE = re.compile(r"\.(db|sqlite|mp4|mov|mkv|webm|wav|mp3|m4a|jpg|jpeg|png|webp|"
                     r"gif|psd)$", re.I)
CORREO = re.compile(rb"[\w.+-]+@(gmail|hotmail|outlook|yahoo|icloud)\.\w+", re.I)


def _git(cwd, *a, binario=False):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, check=True)
    return r.stdout if binario else r.stdout.decode("utf-8", "replace")


def _en_la_historia(cwd) -> set[str]:
    out = _git(cwd, "log", "--all", "--name-only", "--format=", "-z")
    return {p for p in out.replace("\n", "\0").split("\0") if p}


def _ignorado(rutas) -> set[str]:
    r = subprocess.run(["git", "check-ignore", "--no-index", "--stdin", "-z"], cwd=REPO,
                       input="\0".join(rutas).encode("utf-8"), capture_output=True)
    return {p for p in r.stdout.decode("utf-8").split("\0") if p}


def fuera(rutas) -> list[str]:
    """Las rutas de la historia que no son máquina hoy."""
    s = Separacion()
    rutas = sorted(rutas)
    ign = _ignorado(rutas)
    # De `docs/` sólo sale la documentación pública de hoy: lo de antes eran
    # instrucciones y bitácoras, que son configuración aunque ya no estén.
    hoy = set(_git(REPO, "ls-files", "docs").split())
    return [r for r in rutas
            if s.clase(r) != "maquina" or r in ign or NO_SALE.search(r)
            or (r.startswith("docs/") and r not in hoy)]


def filtrar() -> str:
    """Una copia espejo, filtrada. Devuelve su ruta."""
    if os.path.exists(COPIA):
        # git deja sus objetos de sólo lectura: en Windows hay que soltarlos.
        shutil.rmtree(COPIA, onerror=lambda f, r, _: (os.chmod(r, stat.S_IWRITE), f(r)))
    comun = os.path.abspath(os.path.join(REPO, _git(REPO, "rev-parse", "--git-common-dir").strip()))
    subprocess.run(["git", "clone", "--mirror", "--no-local", comun, COPIA], check=True,
                   capture_output=True)
    quitar = fuera(_en_la_historia(COPIA))
    lista = os.path.join(os.path.dirname(COPIA), "publicar-fuera.txt")
    open(lista, "w", encoding="utf-8", newline="\n").write(
        "".join(f"literal:{r}\n" for r in quitar))
    mapa = os.path.join(os.path.dirname(COPIA), "publicar-mailmap.txt")
    correos = {c for c in _git(COPIA, "log", "--all", "--format=%ae%n%ce").split() if c}
    open(mapa, "w", encoding="utf-8", newline="\n").write(
        "".join(f"{AUTOR} <{c}>\n" for c in sorted(correos)))
    texto = os.path.join(os.path.dirname(COPIA), "publicar-texto.txt")
    open(texto, "w", encoding="utf-8", newline="\n").write(
        "".join(f"{a}==>{b}\n" for a, b in SUSTITUYE))
    env = dict(os.environ, PYTHONPATH=FILTER_REPO, PYTHONIOENCODING="utf-8")
    subprocess.run([sys.executable, "-m", "git_filter_repo", "--force", "--invert-paths",
                    "--paths-from-file", lista, "--mailmap", mapa, "--replace-text", texto,
                    "--replace-message", texto], cwd=COPIA, env=env, check=True,
                   capture_output=True)
    print(f"publicar: {len(quitar)} rutas fuera de la historia publicada")
    return COPIA


def faltas(copia) -> list[str]:
    """Lo que no debería estar y está."""
    s, out = Separacion(), []
    for r in sorted(_en_la_historia(copia)):
        if s.clase(r) != "maquina" or NO_SALE.search(r):
            out.append(f"queda {r}")
    todo = _git(copia, "log", "--all", "-p", "--format=%an %ae %cn %ce%n%B", binario=True)
    for m in sorted({m.group(0) for m in CORREO.finditer(todo)}):
        out.append(f"queda el correo {m.decode()}")
    for a, _ in SUSTITUYE:
        if a.encode("utf-8") in todo:
            out.append(f"queda «{a}»")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ver", action="store_true")
    ap.add_argument("--primera", action="store_true",
                    help="la primera subida reemplaza lo que haya en el remoto")
    a = ap.parse_args()
    copia = filtrar()
    malas = faltas(copia)
    for f in malas[:30]:
        print(f"  {f}")
    ramas = _git(copia, "for-each-ref", "--format=%(refname:short)", "refs/heads").split()
    print(f"publicar: {len(ramas)} ramas, {_git(copia, 'rev-list', '--all', '--count').strip()}"
          f" commits; {'NO sale' if malas else 'limpia'} ({len(malas)} faltas)")
    if malas:
        sys.exit(1)
    if a.ver:
        return
    orden = ["git", "push", REMOTO, "refs/heads/*:refs/heads/*"]
    if a.primera:
        orden.insert(2, "--force")
    subprocess.run(orden, cwd=copia, check=True)
    print(f"publicado en {REMOTO}")


if __name__ == "__main__":
    main()
