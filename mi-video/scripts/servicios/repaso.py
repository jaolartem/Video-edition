"""El ultimo repaso de redundancia, con la pieza ya cosida.

Regla de Jaime, y la pidio despues de ver la misma repeticion volver tres veces
en una tarde: *«revisemos si otra pasada extra de redundancia al final antes de
renderizar para revisar todo vale la pena hacerla — siempre»*.

## Por que hace falta un SEGUNDO repaso

`sin_redundancia` corre en la fase 5, sobre el corte recien depurado, y esta
bien ahi: es cuando la repeticion es mas barata de quitar. Pero **lo que se
juzga ahi no es lo que se oye al final**. Entre esa fase y el render pasan
`recortado`, `revalidado` y `cosido`, y cada uno rehace el corte:

- `fijar` reconstruye la etapa entera cuando entra una declaracion nueva, y con
  ella vuelve el texto que se habia recortado dentro.
- Una nota se estampa con la huella de su montaje (C-92), asi que en cuanto el
  corte cambia deja de aplicarse — con razon, pero el hueco queda.
- Cambiar de toma en una etapa mete texto que nadie ha leido todavia.

Medido en reel-01 en una sola tarde: «luego sube» volvio dos veces, «en Ontario,
un dueno de negocio en Ontario» aparecio al cambiar de toma, y la costura de la
etapa 2 acabo diciendo «estructura y y los que usan». Ninguno era un fallo del
primer repaso: los tres nacieron despues de el.

## Por que aqui y no justo antes del render

Va **entre `cosido` y `descrito`**, que es el ultimo punto donde el texto ya esta
cerrado y cortar todavia es barato. Un corte despues de `descrito` invalida las
descripciones —hablan de un texto que ya no es— y despues de `cortado` obliga a
rehacer los recortes y la voz. Aqui no cuesta nada de eso.

## Y no decide nadie mas que quien lee

Es el mismo contrato que la fase 5 —pedido fuera, respuesta dentro— porque la
razon no ha cambiado: reconocer que dos frases dicen lo mismo es comprender, no
comparar cadenas (C-81). Lo unico que cambia es **cuando se mira**.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .base import Pieza, Resultado, Servicio  # noqa: E402


class ServicioRepaso(Servicio):
    nombre = "repasado"

    def puede(self, pieza: Pieza):
        if not pieza.existe:
            return False, "sin EDL"
        return True, ""

    def correr(self, pieza: Pieza) -> Resultado:
        import redundancia
        import servicio as contrato

        filas = redundancia.dossier(pieza.slug)
        # Las etapas que el frame declara, para saber cual falta. Sale de la
        # base y no del montaje: el montaje es justo lo que puede haberla
        # perdido.
        try:
            import sqlite3 as _s3
            import basedatos

            _c3 = _s3.connect("ads/decisiones.db")
            estructura_beats = [r[0] for r in _c3.execute(
                "select e.orden from etapa e join video v on v.id = e.video_id"
                " where v.slug = ? order by e.orden", (pieza.slug,))]
            _c3.close()
        except Exception:                          # noqa: BLE001
            estructura_beats = []
        if not filas:
            return Resultado(True, salida="sin material que repasar")
        # **Y va la curva con el texto.** El contrato pregunta si el tono va con
        # el momento, y sin la curva delante eso no se puede contestar: la
        # intensidad es sin signo y el texto no dice como se dijo. Es el mismo
        # error que costo C-100 —medir la direccion y no pasarsela a quien
        # decide— y aqui seria peor, porque este es el ultimo que mira.
        try:
            import consulta

            curva = consulta.onda(pieza.slug)
        except Exception:                          # noqa: BLE001
            curva = []

        # **De la vuelta 2 en adelante se repasa lo que cambio, no la pieza.**
        # Jaime, viendo arrancar la septima vuelta del reel-01: *«el repaso debe
        # ser sobre lo que se cambio; ya el compositor reviso todo»*. Mandar la
        # pieza entera cada vez obliga a juzgarla desde cero, y releer lo que ya
        # paso no lo mejora: lo cambia. Ver `dominio/vuelta.py`.
        try:
            from dominio.vuelta import Vuelta

            cambio = Vuelta("repaso", pieza.slug, filas,
                            _dir_paso("repaso")).datos()
        except Exception as e:                     # noqa: BLE001
            # Y si no se puede comparar, se dice: repasar «lo que cambio» sin
            # saber que cambio es repasar a ciegas creyendo que no.
            import registro

            registro.aviso("repaso", "no se pudo comparar con la vuelta anterior",
                           detalle=f"{pieza.slug}: {type(e).__name__}: {e}"[:400],
                           eco=False)
            cambio = {}
        # **Lo que viaja, y es poco a proposito.** Jaime: *«repaso es una
        # mirada rapida de lo que ya se construyo, no una reconstruccion»*.
        #
        # Aqui viajaban ademas el libreto, los tableros, el corpus entero, los
        # cierres grabados, el evento y la estructura: 118 KB por pieza. Eran
        # correctos cuando este paso componia y reescribia — hacian falta para
        # decidir que decir. Ya no decide que decir: mira si el corte esta bien
        # cosido y si suena. Mandarselos es invitar a reconstruir la pieza, que
        # es exactamente lo que hay que dejar de hacer, y cobrarlo en tokens.
        #
        # Se queda el montaje —lo que se juzga—, la onda —la otra mitad de
        # «suena»— y lo que cambio desde la vuelta anterior.
        datos = {"montaje": filas, "onda": curva,
                 "lo_que_cambio": cambio}
        # **Tiene su propio contrato, y no es el de redundancia.** Jaime:
        # *«la revision de redundancia es revision de composicion, logica,
        # libreto, tono: es tu revision final»*. Reusar el prompt de la fase 5
        # pedia buscar frases repetidas, que es una de las cinco cosas que hay
        # que mirar aqui y la menos grave de todas.
        prompt = open(
            os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "repaso.prompt.md"),
            encoding="utf-8").read()
        # **Se pregunta UNA vez por pieza.** Jaime: *«no podemos tener un
        # reproceso en un repaso»*, y antes de eso *«el analisis de cada video
        # es caro»*. El bucle era este: el repaso abria un problema, la pieza
        # volvia a coserse, subia otra vez hasta aqui y se volvia a preguntar lo
        # mismo con el corte ya cambiado. Seis vueltas del reel-01 salieron de
        # ahi, y ninguna de las seis contestaba mal.
        #
        # Asi que si ya hay una respuesta archivada, este paso **no vuelve a
        # preguntar**: comprueba con la maquina si lo que abrio sigue abierto.
        if _ya_pregunto(pieza.slug):
            return _cerrar_tickets(pieza)
        r = contrato.pedir("repaso", pieza.slug, prompt, datos)
        if r is None:
            return Resultado(
                False,
                motivo=f"espera el repaso final -> "
                       f"{contrato.ruta_pedido('repaso', pieza.slug)}")
        # **Lo que vuelve son tickets, no cortes.** Jaime: *«que repasar revise
        # los cortes y el sonido, nada mas; que revise que esten bien, y si no,
        # que lo devuelva con ticket al anterior»*.
        #
        # Este paso dejo de editar. Arreglar aqui era lo que rehacia el corte, y
        # un corte nuevo pide otra lectura: el reproceso nacia de darle tijeras
        # al que inspecciona. Ahora senala el segundo y el arreglo lo hace el
        # paso que coso, que es el que sabe por que salio asi.
        from dominio import ticket as tk

        abiertos, para_jaime = 0, 0
        for x in (r or []):
            tipo = str(x.get("tipo") or "corte")
            if tipo not in ("corte", "suena", "dato"):
                tipo = "corte"
            dijo = str(x.get("dijo") or x.get("sube") or "").strip()
            if not dijo:
                continue
            porque = str(x.get("por_que") or "")[:400]
            seg = x.get("segundo")
            try:
                seg = float(seg) if seg is not None else None
            except (TypeError, ValueError):
                seg = None
            tk.abrir(pieza.slug, (dijo + (f" — {porque}" if porque else ""))[:2000],
                     seg, "suena" if tipo == "suena" else
                          ("dato" if tipo == "dato" else "objecion"))
            if tipo == "dato":
                para_jaime += 1
            else:
                abiertos += 1
        if para_jaime:
            print(f"  {pieza.slug}: {para_jaime} ticket(s) de contenido para Jaime")
        if not abiertos:
            return Resultado(True, salida="los cortes y el sonido estan bien")
        # **Vuelve al que coso, y una sola vez.** No se vuelve a preguntar
        # cuando regrese: los tickets los cierra la maquina midiendo, no otra
        # lectura. Ver `_cerrar_tickets`.
        return Resultado(True, volver_a="cosido",
                         salida=f"{abiertos} ticket(s) al paso que coso — no se"
                                f" vuelve a preguntar, se comprueba")


def _ya_pregunto(slug: str) -> bool:
    """¿Hay ya una respuesta de repaso archivada para esta pieza?"""
    import glob

    return bool(glob.glob(os.path.join(_dir_paso("repaso"), "usadas",
                                       f"{slug}.*.respuesta.json")))


def _cerrar_tickets(pieza) -> "Resultado":
    """Cierra con la maquina los tickets que el repaso abrio, sin preguntar.

    Un ticket de corte dice «en la etapa B algo suena partido». Despues de que
    `cosido` vuelva a pasar, **eso se mide**: `bordes_sucios` es el mismo
    detector que ve una palabra cortada, y no cuesta un token.

    Lo que no se puede medir no se cierra solo — se queda abierto y viaja con la
    pieza hasta Jaime, que es donde tenia que estar desde el principio. Cerrar
    por silencio seria justo lo que este paso existe para impedir.
    """
    from dominio import ticket as tk

    try:
        import consulta

        sucios = consulta.bordes_sucios(pieza.slug) or {}
    except Exception:                              # noqa: BLE001
        sucios = {}
    cerrados, quedan = 0, 0
    for t in tk.abiertos(pieza.slug):
        b = t.get("beat")
        if t.get("tipo") == "objecion" and b is not None and not sucios.get(str(b)):
            tk.contestar(t["id"], "el paso que cose volvio a pasar y la etapa ya"
                                  " no tiene ningun borde sucio: medido, no"
                                  " opinado", estado="arreglado", quien="la linea")
            cerrados += 1
        else:
            quedan += 1
    if quedan:
        return Resultado(True, salida=f"{cerrados} ticket(s) cerrados midiendo,"
                                      f" {quedan} siguen abiertos y viajan con"
                                      f" la pieza")
    return Resultado(True, salida=f"{cerrados} ticket(s) cerrados midiendo — los"
                                  f" cortes y el sonido estan bien")


def _dir_paso(paso: str) -> str:
    """La carpeta del paso, que es donde el motor archiva las vueltas usadas."""
    import servicio as contrato

    return os.path.dirname(contrato.ruta_pedido(paso, "reel-01"))
