"""La revisión: lee, dicta veredicto, y lo que se arregla con código se arregla.

**Cómo lo fijó Jaime**, el 1 de septiembre, corrigiéndome cuando yo lo había
dejado en «preguntar»:

> *«Pero no las revisa: lee y da un veredicto, abre un ticket para cosas grandes
> y corrige lo que se puede corregir por código, que es casi todo.»*

Y antes, qué mira: *«revisar revisa CC, descripciones y empalmes —además que
tenga sonido en todo lo que dice—; probablemente sea fácil para revisar comprobar
la regla de redundancia en el CC, que ya está trabajado desde antes»*.

## El reparto, y no es negociable

De esas cinco, **tres las decide el código** —CC, empalmes y que suene lo que
dice— porque son cuentas. Las otras dos, descripciones y redundancias, tienen
criterio: *«descripciones y redundancias por LLM, que tienen criterio; lo demás
por código»*.

Así que aquí no se pregunta «¿qué te parece?». Se manda cada caso con la mitad
medible ya resuelta —qué etapa, sobre qué texto se escribió, cuál de las dos
características le falta a esa repetición— y lo que vuelve es un **veredicto**.

## Y un veredicto tiene exactamente dos salidas

- **`corregir`** — trae el texto que sobra, y lo ejecuta el código por
  `Recorte`, que lo ancla en `revision` y sobrevive a que la pieza se vuelva a
  montar. Es el caso normal: *«casi todo»*.
- **`ticket`** — lo grande, lo que no se arregla cortando. Va a la tabla de
  tickets con su etapa y viaja con la pieza hasta que Jaime lo vea.

No hay tercera. Un veredicto que no cabe en ninguna de las dos es una opinión
sin ejecutor, y ésas son las que se pierden — es C-113, y este paso existe en
parte para no repetirla.

## Lo que NO hace

No vuelve a describir, no recompone y no mueve bordes. *«Las correcciones son
puntuales, no es una recomposición, no quiero volver a correr todo.»*
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioRevisar(Servicio):
    """Fase 12. Lee lo que tiene criterio y ejecuta lo que no lo necesita."""

    nombre = "revisado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import servicio as contrato

        from dominio.revisada import Revisada

        r = Revisada(pieza)
        # **Primero lo que decide el código, y para si algo para.** Mandar a
        # leer una pieza con un hueco de dos segundos sin voz es pedir criterio
        # sobre material roto: lo que conteste va a hablar de otra cosa.
        paran = [f for f in r.faltas() if f.para]
        if paran:
            uno = paran[0]
            return Resultado(False, motivo=f"{uno.que}"[:140] +
                             (f" (+{len(paran) - 1} mas)" if len(paran) > 1
                              else ""))
        casos = r.preguntas()
        if not casos:
            return Resultado(True, salida="revisada: nada que dictaminar")
        datos = {
            "pieza": pieza.slug,
            "casos": [{"etapa": f.etapa, "que": f.que} for f in casos],
            "montaje": _montaje(pieza.slug),
        }
        prompt = _prompt()
        v = contrato.pedir("revisar", pieza.slug, prompt, datos)
        if v is None:
            return Resultado(
                False,
                motivo="espera el veredicto -> "
                       + contrato.ruta_pedido("revisar", pieza.slug))
        return _aplicar(pieza, v)


def _prompt() -> str:
    p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "revisar.prompt.md")
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _montaje(slug: str) -> list:
    """Lo que se oye, etapa a etapa. Es contra lo que se dictamina."""
    try:
        from dominio.montaje import Montaje

        m = Montaje(slug)
        fuera = {}
        for tr, d in m.tramos():
            b = d.get("beat")
            if b is None:
                continue
            fuera[b] = (fuera.get(b, "") + " " + (m.texto(tr) or "")).strip()
        return [{"etapa": b, "dice": t} for b, t in sorted(fuera.items())]
    except Exception:                              # noqa: BLE001
        return []


def _aplicar(pieza: Pieza, veredictos) -> Resultado:
    """Ejecuta lo que se corrige y abre ticket de lo grande. Nada se queda."""
    from dominio import ticket as tk
    from dominio.correccion import Recorte

    cortados, abiertos, fallidos = 0, 0, []
    for v in (veredictos or []):
        if not isinstance(v, dict):
            continue
        ancla = (v.get("corregir") or "").strip()
        if ancla:
            hecho = Recorte(pieza.slug, ancla,
                            str(v.get("por_que") or "veredicto de la revision"),
                            ).correr()
            if hecho.startswith("cortado"):
                cortados += 1
            else:
                # **Un recorte que no ancla no se calla.** Si se perdiera aqui,
                # el veredicto existiria y no habria pasado nada — que es la
                # forma exacta en que este proyecto pierde decisiones.
                fallidos.append(ancla[:60])
                tk.abrir(pieza.slug,
                         f"la revision mando cortar «{ancla[:120]}» y no se pudo"
                         f" anclar en el montaje de hoy", None, "objecion")
                abiertos += 1
            continue
        grande = (v.get("ticket") or "").strip()
        if grande:
            seg = v.get("segundo")
            try:
                seg = float(seg) if seg is not None else None
            except (TypeError, ValueError):
                seg = None
            tk.abrir(pieza.slug, grande[:2000], seg, "objecion")
            abiertos += 1
    parte = f"{cortados} corregido(s) por codigo, {abiertos} ticket(s)"
    if fallidos:
        parte += f" — sin anclar: {', '.join(fallidos[:2])}"
    if cortados:
        # El corte cambio, asi que se vuelve a coser. No se vuelve a revisar:
        # este paso pregunta una vez, como el repaso.
        return Resultado(True, volver_a="cosido", salida=parte)
    return Resultado(True, salida=parte)
