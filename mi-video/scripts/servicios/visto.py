"""El DISEÑADOR mira la pieza ya renderizada. Es su segundo momento, no otro rol.

Regla de Jaime, y viene de recibir un reel-01 de 143 s con silencios dentro,
redundancia sin revisar y los cuadros mal puestos: *«el agente no lo revisó antes
de componerlo, ¿o qué pasó? esto es un claro retroceso»*, *«asegúrate de que las
piezas del renderizado sean revisadas por el último agente y que todo esté en el
pipeline»*, y lo que fija quién: ***«que lo revise el diseñador como paso
final»***.

Y tiene sentido que sea él: **compuso la pieza, así que es el único que puede
decir si lo que salió es lo que diseñó.** Un revisor nuevo tendría que deducir la
intención desde el resultado, que es justamente lo que no se puede hacer.

Por eso no es un contrato aparte: es el mismo `DISENO` en un segundo momento
—`disenado` monta, `visto` comprueba—, igual que el contrato del corte tiene
tres. Un contrato por paso, y el paso se repite hasta que pase.

## Por qué al final y no antes

Todos los pasos anteriores juzgan **lo que se va a montar**: el corte, el texto,
la descripción, el diseño. Ninguno mira **lo que salió**. Y hoy quedó claro que
son cosas distintas — se puede tener el corte limpio, la descripción correcta y
el diseño hecho, y entregar una pieza con silencios de seis segundos porque un
paso se saltó.

Éste mira el artefacto. Es la misma regla que ya gobierna la fase `montado`
—*«el render tiene que ser más nuevo que el EDL del que sale»*— llevada al
contenido: **no basta con que el fichero exista, tiene que decir lo que se
decidió.**

## Qué recibe, y todo sale de medidas que ya existen

    dura          lo que dura de verdad el fichero entregado
    aire          el silencio más largo y cuántos hay, medidos sobre la onda
    costuras      cuánto salta la voz en cada unión, en semitonos y pal/s
    repetido      lo que la pieza dice dos veces, con la entrega de cada una
    se_ve         qué tablero o panel hay en cada momento, y sobre qué texto
    motivos       lo que la puerta dejó abierto y se renderizó igual

Nada de esto es nuevo: son `suena.py`, `consulta.repetido` y el spec. Lo que
faltaba no era la medida, era **alguien que las mirara juntas con la pieza
delante**.

## Qué decide

Una sola cosa, y por eso es barato: **si esto se le puede enseñar a Jaime**. El
criterio humano es el escalón más caro del embudo, y gastarlo en una pieza que
tiene un silencio de seis segundos es tirarlo.

Si dice que no, la pieza vuelve a la fase que corresponda con el motivo escrito
— no se queda parada esperando a que alguien se acuerde.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402

#: El mismo prompt del diseño: es su segundo momento, no otro oficio.
PROMPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "disenar.prompt.md")


def dossier(pieza: Pieza) -> dict | None:
    """Lo que se ve y se oye en el fichero entregado. Del artefacto, no del plan."""
    import rutas
    import suena

    n = pieza.n
    mp4 = rutas.salida("entrega", f"reel-R{n}.mp4")
    if not os.path.exists(mp4):
        mp4 = rutas.salida("reels", f"reel-R{n}.mp4")
    if not os.path.exists(mp4):
        return None

    d = {"pieza": pieza.slug, "fichero": os.path.basename(mp4)}
    # **Y los fotogramas, porque este paso es de mirar.** El prompt que recibe
    # cierra con «antes de contestar: MIRALO» y el pedido no traia una sola
    # imagen: se juzgaba con numeros la unica cosa que existe para verse.
    # `fotogramas.sacar` estaba escrito para esto —cinco por escena, del render
    # entregado— y no lo llamaba nadie. Jaime: *«que tome cinco fotogramas
    # repartidos de la escena, va a verlos, y con esos decide»*.
    try:
        import fotogramas

        tiros, por_que = fotogramas.sacar(n)
        d["mira"] = tiros if tiros else []
        if por_que:
            d["sin_fotogramas"] = por_que
    except Exception as e:                         # noqa: BLE001
        d["mira"] = []
        d["sin_fotogramas"] = f"{type(e).__name__}: {e}"[:160]
    # Una pasada de ffmpeg para las cuatro medidas, no una por medida: los
    # tres filtros miden y dejan pasar, asi que en serie dicen lo mismo.
    d.update(suena.pasada(mp4))
    d["costuras"] = suena.costuras(pieza.slug)

    # Lo que se dice dos veces, con la entrega de cada una al lado.
    try:
        import consulta

        d["repetido"] = consulta.repetido(pieza.slug)
    except Exception as e:                         # noqa: BLE001
        d["repetido"] = [{"error": str(e)[:120]}]

    # Lo que hay en pantalla y sobre qué texto cae. Del spec, que es lo que el
    # render consumió — no de la base, que es lo que se pidió.
    try:
        spec = json.load(open("src/reels.json", encoding="utf-8"))
        r = next((x for x in spec if x.get("id") == f"Reel-R{n}"), {})
        d["dura"] = r.get("duracion")
        d["motivos_abiertos"] = r.get("bloqueado") or []
        caps = r.get("captions") or []
        d["se_ve"] = [{
            "en": round(b["at"] / 30, 1),
            "dura": round(b.get("duration", 0) / 30, 1),
            "forma": b.get("kind"),
            "cubre": (b.get("props") or {}).get("cubre", "pleno"),
            "mientras_dice": " ".join(
                c["text"] for c in caps
                if c["at"] < b["at"] + b.get("duration", 0)
                and c["at"] + c["duration"] > b["at"])[:120],
        } for b in (r.get("boards") or [])]
    except Exception as e:                         # noqa: BLE001
        d["se_ve"] = [{"error": str(e)[:120]}]
    return d


class ServicioVisto(Servicio):
    nombre = "visto"

    def puede(self, pieza: Pieza):
        import rutas

        hay = any(os.path.exists(rutas.salida(c, f"reel-R{pieza.n}.mp4"))
                  for c in ("entrega", "reels"))
        return (True, "") if hay else (False, "todavia no hay render que mirar")

    def correr(self, pieza: Pieza) -> Resultado:
        import servicio as contrato

        d = dossier(pieza)
        if d is None:
            return Resultado(False, motivo="no hay fichero entregado")
        prompt = (open(PROMPT, encoding="utf-8").read()
                  if os.path.exists(PROMPT) else "")
        # **Y va por su propia carpeta, no por la de `disenar`.**
        #
        # Compartia el fichero de pedido con el paso de diseno «porque es su
        # contrato», y un contrato compartido no es una carpeta compartida: los
        # dos escriben `disenar/<slug>.pedido.json`, asi que **el ultimo que pasa
        # borra la pregunta del otro**. Paso el 1 de septiembre: el pedido del
        # gancho de reel-01 aparecio sin `tableros`, sin `arco`, sin `canon` y
        # sin `topes` — lo habia sobrescrito esto — y quien componia tuvo que ir
        # a buscar el bueno al archivo para poder trabajar.
        #
        # No se ve venir porque no falla: el fichero existe, es JSON valido y le
        # faltan la mitad de los datos. Y la respuesta que vuelva se archiva
        # contra el pedido equivocado.
        r = contrato.pedir("visto", pieza.slug, prompt, d)
        if r is None:
            return Resultado(
                False,
                motivo="espera revision del render -> "
                       + contrato.ruta_pedido("visto", pieza.slug))
        return aplicar(pieza, r)


def aplicar(pieza: Pieza, veredicto) -> Resultado:
    """`se_ensena` pasa; si no, vuelve a la fase que el agente diga y con motivo.

    **Vuelve, no se queda parada.** Una pieza que no se puede enseñar y no vuelve
    a ningún sitio es una pieza que espera a que alguien se acuerde, y eso en
    este proyecto significa que no pasa nunca.
    """
    v = veredicto[0] if isinstance(veredicto, list) and veredicto else veredicto
    if not isinstance(v, dict):
        return Resultado(False, motivo="veredicto ilegible")
    # **Sin `se_ensena` no hay veredicto, y la ausencia no es un «no».** El
    # diseñador contestaba con la forma de `disenar` —`pieza`, `tableros`,
    # `mirado`— porque el prompt compartido nunca le pidio otra, y esto lo leia
    # como «no se enseña: sin motivo». Mientras el «no» no se atendia (C-376) la
    # pieza solo se paraba; atendido, reel-01, 03, 04 y 05 volvieron a `cosido`
    # el 11-9 por un no que nadie dijo. Una respuesta sin la clave se vuelve a
    # pedir; no mueve la pieza.
    if "se_ensena" not in v:
        return Resultado(False, motivo="veredicto ilegible: la respuesta no trae"
                                       " `se_ensena`")
    por_que = (v.get("por_que") or "sin motivo")[:200]
    if v.get("se_ensena"):
        return Resultado(True, salida=f"se puede enseñar: {por_que}")
    # **Y el «no» se le dice a alguien: es un tiquet.** Devolver la pieza sin
    # el motivo era mandarla a un paso que no tenia nada nuevo que contestar:
    # reel-03, 11-9, cruzo `descrito`, `disenado`, `cortado` y `verificado` en
    # el mismo minuto, con el gancho igual de roto, camino de otro render y otro
    # «no». El tiquet es la puerta que ya existe —la misma que las
    # observaciones de Jaime—: viaja en el pedido de quien lo atiende, y
    # `vencidas` retiene la pieza si ese paso pasa sin cerrarlo.
    #
    # `vuelve_a` nombra el paso que lo atiende, como en cualquier tiquet; la
    # pieza se coloca justo antes (`antes_de`). Uno abierto por pieza: un «no»
    # repetido no abre otro.
    from dominio import ticket
    from dominio.fase import antes_de, camino

    atiende = v.get("vuelve_a")
    if atiende not in {f["nombre"] for f in camino()}:
        atiende = "descrito"
    if not any((t.get("dijo") or "").startswith("visto ·")
               for t in ticket.abiertos(pieza.slug)):
        ticket.abrir(pieza.slug,
                     f"visto · el diseñador no la enseña: {v.get('por_que') or 'sin motivo'}",
                     etapa="pieza", tipo="objecion", vuelve_a=atiende)
    return Resultado(False, motivo=f"no se enseña: {por_que}",
                     volver_a=antes_de(atiende), salida=por_que)
