"""Volver a medir después del caro: ¿sigue siendo interesante o era un falso positivo?

Regla de Jaime, y cierra el embudo por el otro lado: *«por eso se vuelve a medir
después de que se hizo el proceso, a ver si sigue siendo interesante o era un
falso positivo, y si era un falso positivo se pasa al siguiente»*. Y la segunda
mitad, que es la que exige criterio: *«ahí es cuando necesitas criterio para
saber si se escucha o no entrecortado, y para definir si compones o no compones
la escena»*.

## Por qué hace falta medir dos veces

El barato elige con información incompleta: un tramo puede parecer entregado
porque el transcript de una pasada se comió las pausas, o parecer limpio porque
no se oyeron los tropiezos. Después del caro **el mismo tramo se ve distinto**, y
lo que se eligió por una promesa que no se cumple hay que soltarlo.

Sin esta vuelta, el embudo sólo estrecha: elige, refina y monta lo que eligió
aunque el refinado diga que no. Con ella, el embudo **también corrige**.

## Lo que se mide y lo que se juzga

Se mide: recorrido de F0, movimiento de tono, ritmo, continuidad, y cuánto han
cambiado respecto a antes del refinado. Eso es señal.

Se juzga —y por eso es un servicio de IA, no un umbral—: **si se escucha
entrecortado** y **si la escena se compone o no**. Un tramo con tres costuras
puede sonar entero si caen entre ideas, y uno con una sola puede sonar roto si
cae a mitad. Ningún número distingue eso.

El veredicto llega por contrato: `falso_positivo`, `entrecortado`, `compone` y el
porqué de cada uno.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import registro  # noqa: E402
from .base import Pieza, Resultado, Servicio  # noqa: E402

PROMPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "revalidar.prompt.md")


class ServicioRevalidar(Servicio):
    nombre = "revalidado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import revalidar
        import servicio as contrato

        filas = revalidar.dossier(pieza.slug)
        if not filas:
            return Resultado(False, motivo="el dossier sale vacio")
        # **El bucle corre ANTES de preguntar, y su historial va en el pedido.**
        #
        # Jaime: *«luego el LLM hace lo mismo, pero recibiendo la info de la
        # primera pasada; con eso puede tomar mejores decisiones y componer por
        # alguno de los caminos alguna de las opciones»*.
        #
        # O sea que el LLM no empieza en blanco: llega cuando la maquina ya
        # midio el montaje, lo comparo con las candidatas y —si no ganaba— probo
        # otras pasandolas por el barrido caro. Preguntar antes de eso es pedir
        # una opinion sobre datos que todavia no existen.
        #
        # Y el coste se paga solo donde hace falta: `rondas` no afina nada si el
        # montaje ya gana por encima del ruido del detector.
        for f in filas:
            try:
                f["historial"] = revalidar.rondas(pieza.slug, f["beat"])
            except Exception as e:                 # noqa: BLE001
                f["historial"] = [{"error": str(e)[:160]}]
        prompt = (open(PROMPT, encoding="utf-8").read()
                  if os.path.exists(PROMPT) else "")
        r = contrato.pedir("revalidar", pieza.slug, prompt, filas)
        if r is None:
            return Resultado(
                False,
                motivo="espera veredicto -> "
                       + contrato.ruta_pedido("revalidar", pieza.slug))
        return Resultado(True, salida=aplicar(pieza, r))


def aplicar(pieza: Pieza, veredictos) -> str:
    """Lo que el veredicto desencadena, y son tres cosas distintas.

    - `falso_positivo` — la etapa se descarta y **entra la siguiente
      candidata**. Se apunta en `descartado`, que es lo que `seleccionar.py` lee
      para no volver a elegirla.
    - `entrecortado` — no se descarta la toma: se marca la costura para que
      `costuras.py` la mueva o la disimule. Romper por una costura seria volver
      a descartar por número de cortes, que ya costo una correccion.
    - `compone` — la escena lleva composición. Es lo que decide si esa etapa se
      monta con figura y tablero o va a plano seco.
    - `tramos` / `elegida` — **el corte cambia**. Es la decisión principal del
      paso y no se aplicaba: el servicio medía, preguntaba, recibía «entra la
      candidata 1» … y dejaba el montaje como estaba. Jaime lo pidió así —*«ahí
      decide si cambia de candidato del segmento o si lo mantiene»*— y sin esto
      la mitad de la respuesta se perdía en silencio.

      Se aplica **declarándolo**, no editando el EDL: entra por `fijar`, que lo
      mide contra las demás, lo registra con su porqué y sobrevive a que la
      selección se rehaga.
    """
    import datetime
    import sqlite3

    con = sqlite3.connect("ads/decisiones.db")
    ahora = datetime.datetime.now().isoformat(timespec="seconds")
    falsos, cortados, componen, cambiados = 0, 0, 0, 0
    for v in veredictos:
        beat = v.get("beat")
        if beat is None:
            continue
        if v.get("falso_positivo"):
            con.execute(
                "insert or replace into descartado (video_slug, etapa_orden,"
                " desde, hasta, motivo, fecha) values (?,?,?,?,?,?)",
                (pieza.slug, beat, v.get("desde") or 0, v.get("hasta") or 0,
                 "falso positivo al revalidar: "
                 + (v.get("por_que") or "")[:120], ahora))
            falsos += 1
        if v.get("entrecortado"):
            cortados += 1
        # El corte nuevo: o los tramos que propone, o el rango de la
        # candidata que elige. Lo segundo solo si no dijo tramos.
        nuevos = [t for t in (v.get("tramos") or []) if len(t) == 2]
        if not nuevos and int(v.get("elegida") or 1) != 1:
            r = con.execute(
                "select f.desde, f.hasta, t.nombre from candidato c"
                "  join etapa e on e.id = c.etapa_id"
                "  join video vi on vi.id = e.video_id"
                "  join fragmento f on f.id = c.fragmento_id"
                "  join toma t on t.id = f.toma_id"
                " where vi.slug = ? and e.orden = ? and c.puesto = ?",
                (pieza.slug, beat, int(v["elegida"]))).fetchone()
            if r:
                nuevos = [[r[0], r[1]]]
                v["toma"] = r[2]
        if nuevos:
            import fijar

            # **La lista entera, de una vez.** Antes esto borraba a mano y luego
            # fijaba en bucle; el borrado vive ahora dentro de `declarar`, que
            # es donde no se puede olvidar (ver su docstring).
            toma = v.get("toma") or (pieza.edl or {}).get("detalle", [{}])[0].get("toma")
            fijar.declarar(pieza.slug, beat, toma, nuevos,
                           (v.get("edicion") or v.get("por_que") or "")[:200],
                           quien="revalidado")
            cambiados += 1
        # **Un falso positivo que no cambia nada no es una decision: es un
        # aviso perdido.** Marcarlo solo escribe en `descartado` y deja la pieza
        # igual, asi que la etapa que se declaro mala sigue sonando igual de mal
        # en la corrida siguiente — y en la siguiente.
        #
        # Y lo mismo con `edicion` cuando describe un BORDE. Es prosa: se guarda
        # como el porque de la declaracion y **no la ejecuta nadie**. Todo lo
        # que se escribio ahi durante una tarde —«entra despues de X», «cierra
        # en Y», «suelta el conector»— no llego nunca al montaje, y los mismos
        # bordes volvian corrida tras corrida. Lo que mueve un borde es `tramos`
        # y solo `tramos`.
        if (v.get("falso_positivo") or v.get("entrecortado")) and not nuevos:
            registro.aviso(
                "revalidar", "veredicto sin efecto: la etapa se queda como esta",
                detalle=f"{pieza.slug} e{beat}: se marco"
                        f"{' falso positivo' if v.get('falso_positivo') else ''}"
                        f"{' entrecortado' if v.get('entrecortado') else ''}"
                        f" y no vino ni `tramos` ni otra candidata."
                        f" Lo que dice `edicion` no lo aplica nadie:"
                        f" {(v.get('edicion') or '(vacio)')[:90]}")
        if v.get("compone"):
            con.execute(
                "update escena_desc set remedio = coalesce(remedio,'tablero')"
                " where video_slug = ? and etapa_orden = ?", (pieza.slug, beat))
            componen += 1
    con.commit()
    con.close()
    if cambiados:
        import fijar

        fijar.aplicar(pieza.slug)
    return (f"{cambiados} corte(s) cambiados, "
            f"{falsos} falso(s) positivo(s) a la siguiente candidata, "
            f"{cortados} entrecortada(s), {componen} con composicion")
