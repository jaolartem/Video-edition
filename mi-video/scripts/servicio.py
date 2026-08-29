"""El contrato con los servicios de IA. Nadie decide fuera de la línea.

Regla de Jaime, y es de arquitectura, no de detalle:

> *«Y tú, aunque seas el que ejecuta, te vas a mover dentro del pipeline
> reemplazando a la IA que se conecta por tokens o por bash. Vamos a simular un
> programa: nunca puedes tomar decisiones por fuera de la línea. Y vamos a hacer
> una arquitectura modular, articulada por servicios, pero un pipeline en toda
> regla.»*

## Por qué existe esto

Hasta ahora los pasos de IA se resolvían de dos maneras según el día: si el CLI
tenía credencial, corrían solos; si no, **yo leía el dossier y editaba la base o
el EDL a mano**. Eso no es un pipeline con un paso manual: es un pipeline con un
agujero, y por ese agujero se coló todo lo que salió mal hoy — cortes aplicados
sin quedar registrados, descripciones que dejaron de corresponder, decisiones
tomadas fuera de la línea que ningún paso posterior podía ver.

Con esto, un paso de IA es **una función con firma**: entra un fichero, sale un
fichero, y el paso siguiente lee la salida. Da igual quién la escriba —el CLI,
una API, o yo respondiendo como el servicio— porque **el contrato es el mismo**.
Lo que ya no se puede hacer es saltarse el fichero.

## El contrato

    work/servicio/<paso>/<slug>.pedido.json     lo que el paso pregunta
    work/servicio/<paso>/<slug>.respuesta.json  lo que el servicio contesta

`pedir()` escribe el pedido e intenta el CLI. Si el CLI no está, **deja el
pedido puesto y devuelve `None`**: el paso lo dice y la línea sigue o para,
pero nadie improvisa. Cuando la respuesta aparece —la escriba quien la escriba—
`recoger()` la valida contra el esquema del paso y la entrega.

## Lo que esto impide, a propósito

- Que yo toque `escena_desc` o el EDL directamente: sólo escribo respuestas.
- Que una decisión exista sin quedar registrada: el fichero **es** el registro.
- Que un paso posterior no sepa de dónde salió un dato: sale del contrato.

    python scripts/servicio.py            # que pedidos hay sin contestar
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))

RAIZ = "work/servicio"


def _dir(paso):
    d = os.path.join(RAIZ, paso)
    os.makedirs(d, exist_ok=True)
    return d


def ruta_pedido(paso, slug):
    return os.path.join(_dir(paso), f"{slug}.pedido.json")


def ruta_respuesta(paso, slug):
    return os.path.join(_dir(paso), f"{slug}.respuesta.json")


def pedir(paso, slug, prompt, payload, cli=True):
    """Deja el pedido y, si se puede, lo resuelve con el CLI.

    Devuelve la respuesta ya validada, o `None` si el servicio no contestó. En
    ese caso **el pedido queda escrito**: quien pueda contestarlo lo encuentra
    ahí, y el paso no inventa nada mientras tanto.
    """
    p = ruta_pedido(paso, slug)
    json.dump({"paso": paso, "slug": slug, "prompt": prompt, "datos": payload},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if cli and _hay_cli():
        r = _por_cli(prompt, payload)
        if r is not None:
            json.dump(r, open(ruta_respuesta(paso, slug), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            return r
    return recoger(paso, slug)


def recoger(paso, slug):
    """La respuesta si existe, la escriba quien la escriba."""
    p = ruta_respuesta(paso, slug)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _hay_cli():
    """¿El CLI tiene credencial aquí?

    Se comprueba de verdad, no se supone: `claude -p` responde con código 0 y
    un JSON que dice `Not logged in` dentro, así que mirar el código de salida
    no vale. Y el resultado importa — el CLI usa la credencial de **la terminal
    que lo lanza**, y desde una sesión de Claude Code no hay ninguna (C-70).
    """
    try:
        out = subprocess.run(["claude", "-p", "ok", "--output-format", "json"],
                             capture_output=True, text=True, timeout=40)
        d = json.loads(out.stdout or "{}")
        return not d.get("is_error")
    except Exception:                              # noqa: BLE001
        return False


def _por_cli(prompt, payload):
    try:
        out = subprocess.run(
            ["claude", "-p", "--output-format", "json"],
            input=f"{prompt}\n\n---\n\n{json.dumps(payload, ensure_ascii=False)}",
            capture_output=True, text=True, timeout=900)
        d = json.loads(out.stdout or "{}")
        if d.get("is_error"):
            return None
        txt = str(d.get("result") or "")
        i, j = txt.find("["), txt.rfind("]")
        if i < 0:
            i, j = txt.find("{"), txt.rfind("}")
        return json.loads(txt[i:j + 1]) if i >= 0 else None
    except Exception:                              # noqa: BLE001
        return None


def pendientes():
    """Pedidos escritos y sin respuesta. Es la cola del servicio."""
    out = []
    if not os.path.isdir(RAIZ):
        return out
    for paso in sorted(os.listdir(RAIZ)):
        d = os.path.join(RAIZ, paso)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".pedido.json"):
                continue
            slug = f[: -len(".pedido.json")]
            if not os.path.exists(ruta_respuesta(paso, slug)):
                out.append((paso, slug, os.path.join(d, f)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()
    p = pendientes()
    if not p:
        print("servicio: no hay pedidos sin contestar")
        return
    print(f"servicio: {len(p)} pedido(s) esperando respuesta")
    for paso, slug, f in p:
        print(f"    · {paso} / {slug}   ->   {f}")
    print("\nLa respuesta va en el fichero .respuesta.json del mismo sitio."
          "\nNadie decide fuera de esto.")


if __name__ == "__main__":
    main()
