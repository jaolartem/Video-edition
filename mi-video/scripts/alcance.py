"""El alcance de un cambio: ¿se incluyó una instrucción, o se reconstruyó?

Regla de Jaime: *«si te doy instrucciones cambias la máquina, no la rehaces;
buscas la mejor manera de incluir lo que te digo»*.

La regla es fácil de aceptar y difícil de cumplir, porque reconstruir **se siente
más limpio**: si el criterio cambió, regenerar todo parece lo riguroso. No lo es.
El 29 de agosto una corrección sobre cómo se mide la emoción acabó regenerando
los seis EDL y dejando las descripciones de escena hablando de un montaje que ya
no existía. La instrucción tocaba una vara; la respuesta tocó el lote entero.

## Qué mide esto

Lo que hay sin comprometer, repartido en tres cosas que no valen lo mismo:

    codigo      scripts, componentes — cambiar aquí es cambiar la máquina
    decisiones  ads/*.json, la base — cambiar aquí es cambiar el producto
    documentos  docs, CLAUDE.md, skills — cambiar aquí es cambiar el acuerdo

Y avisa cuando el reparto delata una reconstrucción: **muchas decisiones tocadas
con poco código** es haber rehecho piezas en vez de arreglar el mecanismo que las
produce, y es exactamente el patrón que la regla prohíbe.

No bloquea nada: es un espejo. Se mira antes de cerrar un cambio, y si el número
no cuadra con lo que se pidió, lo honesto es decirlo — no justificarlo.

    python scripts/alcance.py
"""
import argparse
import os
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Cuántas piezas tocadas empiezan a oler a reconstrucción cuando el código
# apenas se movió. Cuatro de seis es «rehice el lote»; una o dos es trabajo
# normal sobre una pieza concreta.
MUCHAS_PIEZAS = 3


def cambios():
    r = subprocess.run(["git", "status", "--porcelain"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=RAIZ)
    return [ln[3:].strip().strip('"') for ln in r.stdout.splitlines() if ln.strip()]


def clasificar(fs):
    codigo, decisiones, documentos, otros = [], [], [], []
    for f in fs:
        if "/scripts/" in f or "/src/" in f:
            codigo.append(f)
        elif "/ads/" in f or f.endswith(".db"):
            decisiones.append(f)
        elif f.startswith("docs/") or f.endswith(".md") or f.startswith("skills/"):
            documentos.append(f)
        else:
            otros.append(f)
    return codigo, decisiones, documentos, otros


def main():
    argparse.ArgumentParser().parse_args()
    fs = cambios()
    if not fs:
        print("alcance: nada sin comprometer")
        return
    codigo, decisiones, documentos, otros = clasificar(fs)
    piezas = {f.split("/ads/")[1].split("/")[0]
              for f in decisiones if "/ads/" in f and "/" in f.split("/ads/")[1]}
    print(f"alcance: {len(fs)} fichero(s) sin comprometer")
    for nombre, grupo in (("codigo", codigo), ("decisiones", decisiones),
                          ("documentos", documentos), ("otros", otros)):
        if grupo:
            print(f"  {nombre:<11} {len(grupo):>3}   "
                  + ", ".join(os.path.basename(x) for x in grupo[:4])
                  + (" …" if len(grupo) > 4 else ""))
    if piezas:
        print(f"  piezas tocadas: {sorted(piezas)}")
    # El aviso, que es para lo que existe esto.
    if len(piezas) >= MUCHAS_PIEZAS and len(codigo) <= 2:
        print(f"\n  ojo: {len(piezas)} piezas tocadas con {len(codigo)} fichero(s)"
              f" de codigo.\n  Eso es rehacer producto en vez de arreglar el"
              f" mecanismo que lo produce —\n  «cambias la maquina, no la"
              f" rehaces». Si la instruccion era de una tuerca,\n  el numero no"
              f" cuadra.")


if __name__ == "__main__":
    main()
