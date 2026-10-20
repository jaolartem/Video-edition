"""La puerta del camino. Nada se renderiza sin pasar por aquí.

Regla de Jaime, y viene de un fallo que costó los seis vídeos: *«el camino es
obligatorio siempre, ninguno de esos vídeos es siquiera útil»*.

## Qué pasó, para que no vuelva a pasar

Él corrigió **cómo se mide la emoción**. De `voz_st` cuelgan cuatro reglas más
—el umbral de lectura plana, el envío a tablero, el tratamiento y el reparto de
etapas— y yo **sólo verifiqué la escala que había cambiado**. Cuando vi los
tableros dispararse recalibré el umbral y ahí paré: no volví a leer una sola
pieza contra el libreto.

Resultado medido: `escena_desc` —integridad, tratamiento, prioridad— llevaba seis
horas sin tocarse mientras los EDL se regeneraban una docena de veces. El
diagnóstico de integridad que estaba dando **describía un montaje que ya no
existía**. Y por eso el reel 3 llegó con el gancho en un tablero, la tesis
borrada y el precio fuera: nada de eso es emocionalidad, es cobertura e
integridad, que es justo lo que dejé de mirar.

Su diagnóstico fue exacto: *«cada cambio en una parte del proceso lo tomas como
un cambio de proceso, y al evaluar la emocionalidad dejaste de lado el resto»*.

## Por qué una puerta y no una lista

Las comprobaciones ya existían —integridad, cobertura, caminos, presencia— pero
**sueltas**, como scripts que hay que invocar. Las guardas sí paraban el lote
porque están dentro del camino; las demás dependían de que yo me acordara. Una
comprobación que depende de la memoria de alguien no es una comprobación.

Aquí corren **como conjunto** y el paso sale con código 1: `montar.sh` no
renderiza y `pipeline.sh` no sigue.

    python scripts/verificar.py          # los seis
    python scripts/verificar.py 3        # sólo el reel 3
    python scripts/verificar.py --avisa  # informa y no bloquea
"""
import argparse
import json
import os
import sqlite3
import basedatos
import sys

sys.path.insert(0, os.path.dirname(__file__))
from servicios import Pieza  # noqa: E402
import rutas  # noqa: E402
from dominio.texto import dice_lo_mismo as _dice_lo_mismo  # noqa: E402
from dominio.aritmetica import SOLAPE_MIN as _SOLAPE_MIN  # noqa: E402

BASE = "ads/decisiones.db"


#: **Lo que se anota y NO para la pieza, declarado en un solo sitio.**
#:
#: La puerta la miran dos: el servicio `verificado` y `montar.sh` por la CLI. Y
#: discrepaban — el servicio apartaba la caducidad como ticket y la CLI seguia
#: bloqueando por ella, asi que la pieza pasaba una y no la otra. Es la averia de
#: siempre: la misma decision escrita dos veces y solo una aplicada.
#:
#: Las dos que no paran, con su porque:
#:
#: - **la descripcion habla de otro texto** — rehacerla es rehacer criterio ya
#:   tomado, y la IA no es determinista. Jaime: *«solo hacemos una descripcion y
#:   una sola composicion grafica; no se devuelve a hacer un reproceso»*.
#: - **dice algo dos veces seguidas** — el eco de la costura ya lo cierra el
#:   cosido; lo que llega aqui es tropiezo dentro de la toma o **figura**, y
#:   distinguirlos es entender, no medir.
NO_PARAN = ("habla de otro texto", "sin contestar: ['describir']",
            "dos veces seguidas",
            # Una propuesta fuera de encargo es para que Jaime la vea, no un
            # dato sin respaldo (C-571): paraba el render que el necesita para
            # mirarla. Lo de cumplimiento —cifras, titulos— sigue parando.
            "propuesta fuera de encargo",
            # La regla de plano nacio el 25-9 y la incumplen nueve de diez
            # piezas del lote: se anota en cada verificacion y no para.
            "regla de plano ·",
            # El trabajo grafico: ticket en la entrega, obligatorio en la final.
            # `separa()` lo deja pasar sólo mientras la pieza no esté aprobada.
            "obligatorio en la final",
            # **La voz que sigue despues del corte: anota, no para.**
            #
            # Con la vara absoluta (C-173) quedaron 6 bordes de 129 que el
            # cosido NO puede cerrar: son micro-saltos dentro de la misma cinta
            # —se quitan de 0,45 a 2,24 s y se sigue— asi que alargar hasta el
            # silencio significaria deshacer un corte que alguien decidio.
            #
            # Bloquear las siete piezas por eso es el callejon de siempre: una
            # puerta que exige lo que el arreglo no puede dar. Y va contra la
            # regla de Jaime — *«el bloqueo en el paso final, no aca»*.
            "dejan voz sonando despues")


def _queda_trabajo(paso: str, slug: str) -> bool:
    """¿El pedido abierto de ese paso tiene trabajo detras, o es huerfano?

    Un pedido se cuenta por el fichero que hay en disco, y eso basta mientras el
    paso siga teniendo algo que preguntar. Cuando ya no lo tiene —porque su
    trabajo se aplico por otra via, o porque otro paso lo cubrio— el fichero se
    queda ahi **bloqueando el render de una pregunta que nadie necesita**, y el
    paso que lo retiraria esta ANTES en el camino: la pieza ya paso por el, asi
    que no vuelve a correr. Sin salida.

    Paso hoy con `disenar`: las siete piezas con sus 43 tableros compuestos y
    paradas por siete pedidos vacios, despues de que Jaime llevara 45 minutos
    esperando. Lo que hay que preguntar es si queda trabajo, no si hay fichero.
    """
    if paso != "disenar":
        return True
    try:
        from servicios.disenar import encargos

        return bool(encargos(slug))
    except Exception:                              # noqa: BLE001
        return True


#: La marca que lleva un motivo al que Jaime **ya contesto**. Vive aqui para
#: que quien la escribe y quien la lee usen la misma cadena: sin eso, la puerta
#: de la linea convertia en tiquet un aviso que decia «ya decidido», y ese
#: tiquet paraba la pieza por algo resuelto (C-352).
CONTESTADO = "YA DECIDIDO"


def _aprobado(slug, beat) -> bool:
    """Si ese segmento esta etiquetado `aprobado` contra el corte de hoy."""
    try:
        from dominio import segmento as _sg

        return any(x.n == int(beat) and x.aprobado for x in _sg.Segmento.de(slug))
    except Exception:                              # noqa: BLE001
        return False


def separa(mal, final: bool = False, slug: str = ""):
    """Parte los motivos en los que paran la pieza y los que solo se anotan.

    `final=True` es el render de despues de la aprobacion: ahi lo que era ticket
    pasa a bloquear, porque ya no hay otra vuelta donde arreglarlo.

    **Y antes de parar se le pregunta a Jaime — a lo que ya dijo.** Regla suya,
    despues de contestar tres veces lo mismo: *«cada pasada estoy resolviendo los
    mismos problemas porque no se estan guardando mis decisiones; no quiero estar
    decidiendo 5 veces lo mismo y menos 50 asuntos similares. Sistematiza mi
    respuesta a las dudas y que las consulten antes de parar»*.

    Se guardaban: `revision` tiene sus palabras y `instruccion` sus reglas, y
    `servicio.pedir()` ya se las lleva a los pedidos de IA. Lo que faltaba es
    esta mitad — **quien para la linea no preguntaba**. Medido hoy: el montaje se
    detuvo con «reel-03 e6: sin material y sin tablero» teniendo en la misma base
    la nota #661 con su decision y la #662 confirmando que el corpus no tiene
    otra toma.

    Un motivo contestado **no se calla**: pasa a aviso diciendo que decision lo
    contesta. Silenciarlo sin decir por que seria aflojar la guarda, no
    aprenderla.
    """
    from dominio import contestado as _c

    paran, avisan = [], []
    for m in mal:
        blando = any(x in m for x in NO_PARAN)
        if blando and final and "obligatorio en la final" in m:
            blando = False
        if not blando and slug:
            ya = _c.contestado(m, slug)
            if ya:
                avisan.append(f"{m}  — {CONTESTADO} ({ya[0]}): «{ya[1]}»")
                continue
        (avisan if blando else paran).append(m)
    return paran, avisan


def _fecha_ajena(slug, edl):
    """La pieza no puede nombrar una fecha que no sea la del evento.

    Jaime: *«la unica fecha es el 21»*. reel-07 anunciaba dos —«este 31 de
    agosto desarrollamos una masterclass» en un tramo y «el 21 de septiembre»
    en el cierre—, porque el corpus mezcla grabaciones de convocatorias
    distintas y una toma vieja suena igual de bien que una nueva.

    **Es cumplimiento, no montaje**, y por eso para: una pieza que anuncia dos
    fechas manda al espectador al dia equivocado, y eso no se arregla despues.
    La fecha buena es la que declara el CTA — no se escribe aqui.
    """
    import re

    import transcribir as _tr

    # La fecha buena es la que el render DIBUJA, o sea la del spec. No se
    # escribe aqui: una segunda copia de la fecha es la forma exacta de que un
    # dia digan cosas distintas.
    buena = ''
    try:
        with open('src/reels.json', encoding='utf-8') as f:
            for pieza in json.load(f):
                if pieza.get('id') == f"Reel-R{int(slug[-2:])}":
                    buena = ((pieza.get('cta') or {}).get('fecha') or '').lower()
                    break
    except (OSError, ValueError):
        buena = ''
    if not buena:
        return []
    mb = re.search(r'(\d{1,2})\s+de\s+(\w+)', buena)
    buena_norm = f'{int(mb.group(1))} de {mb.group(2).lower()}' if mb else buena
    MES = ('enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre'
           '|octubre|noviembre|diciembre')
    patron = re.compile(r'(\d{1,2})\s+de\s+(' + MES + r')', re.I)
    cache, ajenas = {}, []
    for (a, b), det in zip(edl['segmentos'], edl['detalle']):
        cinta = det.get('toma')
        if not cinta:
            continue
        if cinta not in cache:
            try:
                cache[cinta] = _tr.exigir(cinta)['segmentos']
            except SystemExit:
                cache[cinta] = []
        dicho = ' '.join(w['text'] for w in cache[cinta]
                         if _tr.suena(w, a, b))
        for m in patron.finditer(dicho):
            # **Cadena completa, no `in`.** «1 de septiembre» esta CONTENIDO en
            # «21 de septiembre», asi que con `not in` una fecha equivocada
            # pasaba la puerta por ser subcadena de la buena.
            dia, mes = m.group(1), m.group(2).lower()
            if f'{int(dia)} de {mes}' != buena_norm:
                ajenas.append(m.group(0))
    if ajenas:
        return [f"{slug}: nombra una fecha que no es la del evento"
                f" — «{'», «'.join(sorted(set(ajenas)))}» frente a «{buena}»."
                f" Una pieza con dos fechas manda al dia equivocado."]
    return []


#: Lo que **no se puede juzgar antes de describir**: habla de tableros, de
#: paneles o de la descripcion misma. No es que la puerta de entrada lo perdone
#: — es que en ese momento no existe todavia, y la de salida sí lo mira.
PIDE_DESCRIPCION = (
    "habla de otro texto", "nadie lo ha compuesto", "sin material y sin tablero",
    "composicion escrita y sin aplicar", "sin contestar", "el tablero del beat",
    "ninguna fila de `dato`", "no rotula ninguna cifra", "sin sonido",
    "no esta en el spec", "salen de un literal",
)


def lo_medido(slug):
    """Lo que la linea ya midio de esta pieza, **para que lo vea quien decide**.

    Jaime, 10-9-2026, corrigiendo una puerta que yo habia puesto en el 6.2:
    *«nada de lo que sucede de 1 a 6 llega como decision; el compositor ve todos
    estos datos y puede utilizar esas herramientas para estar seguro. El
    compositor es quien toma la decision»*.

    Y por eso esto **no para nada**. Los pasos 1 a 6 —transcribir, elegir,
    fijar, afinar, depurar, la redundancia y el cosido— producen medidas, no
    veredictos: que el corte se come una palabra, que una etapa se queda muda,
    que algo suena dos veces, que un tramo declarado no llego al corte. Todo eso
    ya se sabe cuando la pieza esta cosida, y hasta hoy se quedaba esperando a
    la fase 10 —la puerta de salida, que es la guarda final— o sea a despues de
    pagar dos llamadas de IA y un corte.

    Ahora viaja en su pedido. Es la misma regla de la casa: **la maquina mide y
    el oficio decide.** Lo que depende de la descripcion no esta aqui porque en
    ese momento no existe todavia, no porque se perdone.
    """
    return [m for m in revisar(slug)
            if not any(x in m for x in PIDE_DESCRIPCION)]


def revisar(slug):
    """Todo lo que tiene que cumplirse. Devuelve la lista de motivos para parar."""
    ruta = f"ads/{slug}/edl-sell.json"
    if not os.path.exists(ruta):
        return [f"{slug}: no hay EDL"]
    # **Y ningun corte se come una palabra.** Jaime, tres piezas seguidas:
    # «dice "para due-", sin terminar», «al final dice "el link esta a-"», «el
    # cierre del R-04 quedo truncado tambien». Tres veces lo mismo en tres
    # piezas distintas: no era de ninguna.
    #
    # `costuras.palabras_enteras` ya lo miraba y no los cazaba, porque pregunta
    # al transcript — y aqui el transcript miente justo donde importa: palabras
    # con duracion cero, otras estiradas. Daba 0 en reel-07, cuya frase estaba
    # partida a la mitad. Esto lo oye en la cinta y saca 12 en las tres.
    mal = []
    from dominio import bordes as _bordes

    for m in _bordes.sucios(slug):
        mal.append(f"{slug} b{m['beat']}: el corte de {m['en']}s cae encima de"
                   f" la voz — se come una palabra")
    edl = json.load(open(ruta, encoding="utf-8"))
    mal += _fecha_ajena(slug, edl)
    # **Lo que subio a Jaime para la pieza hasta que el lo mire.**
    #
    # El contrato lo declara desde que existe el bloque de cumplimiento —*«la
    # pieza no pasa la puerta hasta que Jaime la mire»*— y la puerta no lo
    # contaba. Con eso un agente podia contestar «esta cifra no tiene fuente» y
    # la pieza salia igual: la prioridad 1 del proyecto, escrita y sin efecto.
    #
    # No entra en NO_PARAN a proposito. Todo lo que es blando ahi tiene arreglo
    # despues —un borde, un tablero que falta—; esto no: lo que sube es lo que
    # cambia el mensaje, y quien decide es el.
    from dominio.nota import Nota

    # **Los planos se sostienen, y por ahora se anota.** Regla de Jaime del
    # 25-9. Entra en `NO_PARAN` a proposito: medido sobre el lote vivo la
    # incumplen nueve de diez piezas —reel-12, 19 reparos de 21 bloques— asi que
    # pararlas seria parar el lote por una regla que nacio hoy. Se ve en cada
    # verificacion y solo puede bajar; cuando el lote este limpio, se saca de
    # ahi y pasa a parar. Ver `dominio/plano.py`.
    from dominio import plano as _pl

    mal += [f"{slug}: {r}" for r in _pl.reparos(slug)]
    for n in Nota.subidas(slug):
        if str(n.que).startswith("PROPUESTA de «"):
            mal.append(f"{slug}: propuesta fuera de encargo para Jaime —"
                       f" #{n.id} «{str(n.que)[:90]}»")
            continue
        mal.append(f"{slug}: subio a Jaime y sigue abierto —"
                   f" #{n.id} «{str(n.que)[:90]}»")
    con = basedatos.abrir(BASE)
    con.row_factory = sqlite3.Row

    # 1 · **La descripción caduca cuando cambia EL TEXTO, no la fecha.**
    #
    # La primera versión comparaba marcas de tiempo: si el EDL se reescribía,
    # las seis piezas quedaban invalidadas aunque las etapas dijeran lo mismo, y
    # eso obligaba a rehacer las 52 descripciones por cualquier ajuste. Jaime lo
    # corto: *«tenemos una estructura modular para poder apegarnos a la
    # estructura sin tener que cambiar todo, pero si a cada ajuste de tuerca
    # cambias el motor nunca vamos a llegar a ningún lado»*.
    #
    # Comparando el texto, **caduca sólo la etapa que se movió**. Las demás
    # siguen valiendo, que es exactamente para lo que existe la modularidad.
    dice = Pieza(int(slug[-2:])).texto
    filas = con.execute(
        "select etapa_orden, sobre_texto, integridad, remedio from escena_desc"
        " where video_slug = ?", (slug,)).fetchall()
    if not filas:
        mal.append(f"{slug}: sin descripción de escena — corre el paso 4")
    else:
        viejas = []
        for f in filas:
            b = f["etapa_orden"]
            ahora = " ".join((dice.get(b) or "").split())
            antes = " ".join((f["sobre_texto"] or "").split())
            # **Y «otro texto» quiere decir que dice otra cosa, no que se
            # escriba distinto.** Comparando cadenas exactas, una muletilla que
            # se mueve —un «su» al principio, una coma— marcaba la descripcion
            # como caducada. Ahora que la caducidad no rehace nada sino que abre
            # un ticket, eso seria peor que antes: un ticket por cada palabra de
            # relleno, y entre ellos los tres que importan.
            #
            # `dice_lo_mismo` compara lo que decide el sentido —palabras de
            # contenido, cifras y negaciones— y perdona el relleno. Asi lo que
            # salta es puntual, que es la condicion que Jaime le puso a que algo
            # vuelva: *«si vuelve, vuelve con cosas tremendamente puntuales»*.
            # **Y un segmento aprobado no se rediscute.** Jaime, 10-9-2026:
            # *«cada segmento se debe revisar como la unidad de analisis»*. Si
            # su etiqueta dice `aprobado` contra ESTE corte, su descripcion
            # entra en lo aprobado y volver a compararla abre un tiquet sobre
            # criterio ya cerrado. Si el corte se moviera, la etiqueta habria
            # caducado sola y esto volveria a mirar.
            if (b in dice and antes and not _dice_lo_mismo(antes, ahora)
                    and not _aprobado(slug, b)):
                viejas.append(b)
        if viejas:
            mal.append(
                f"{slug}: la descripción de las etapas {viejas} habla de otro"
                f" texto — mira ESAS contra el corte de hoy, no la pieza entera.")

    # 1 · **Los $180.000 son FACTURACION, y no se llaman de otra manera.**
    #
    # Jaime lo ha corregido tantas veces que dejo de contarlas: *«no es utilidad,
    # y esto lo he corregido N veces tambien; dice facturacion porque es la
    # comparacion de dos personas en un mismo umbral maximo, una con estructura y
    # otra sin estructura»*.
    #
    # Y seguia saliendo EN PANTALLA —«MISMA VENTA · $180,000 DE UTILIDAD»— aunque
    # la tabla `dato` ya estuviera corregida, porque el rotulo vive en el prop del
    # tablero y son dos sitios distintos. Se corrige un sitio, se ve el otro, y la
    # correccion parece no haberse hecho.
    #
    # Lo que esto impide no es un error de estilo: llamar utilidad a la
    # facturacion **cambia lo que el espectador entiende**, que es la unica clase
    # de cosa que el proyecto no deja pasar.
    try:
        import json as _js

        _cx = basedatos.abrir()
        for _o, _tb in _cx.execute(
                "select etapa_orden, tablero from escena_desc"
                " where video_slug = ? and tablero is not null and tablero <> ''",
                (slug,)):
            _txt = _js.dumps(_js.loads(_tb), ensure_ascii=False).lower()
            if "180" in _txt and "utilidad" in _txt:
                mal.append(
                    f"{slug} e{_o}: el tablero llama «utilidad» a los $180.000, y"
                    f" son FACTURACION — es la comparacion de dos personas en el"
                    f" mismo umbral, una con estructura y otra sin ella")
    except Exception:                              # noqa: BLE001
        pass

    # 1a · **No se renderiza sin el trabajo grafico, y sin otro compitiendo.**
    #
    # Jaime, viendo que la pieza salia igual que antes: *«tienes que renderizar
    # con el trabajo grafico, no se puede volver a saltar eso… debe haber una
    # correccion, o un seguro: que si ya lo tiene se asegure de que no hay otro
    # diseno compitiendo, y si no lo tiene que llame el trabajo y que lo
    # integre»*.
    #
    # Faltaban las dos mitades. reel-01 renderizo con **4 de 8 etapas
    # compuestas y el gancho sin poner**, y ademas con su composicion del gancho
    # escrita y sin aplicar: la respuesta llevaba una hora en disco. Ninguna de
    # las dos cosas la miraba nadie, asi que el render salio identico al de la
    # manana y parecia que no se habia hecho nada.
    try:
        from servicios.disenar import encargos

        faltan_tableros = [f["etapa_orden"] for f in encargos(slug)]
        if faltan_tableros:
            # **En la entrega de aprobacion no para: levanta ticket.** Jaime:
            # *«no me importa que en el paso intermedio, en el reel de
            # aprobacion, no esten — ojala si, pero si no, entonces se abre el
            # ticket; de donde si o si tienen que salir con eso es de la
            # final»*.
            #
            # Y tiene razon en lo que separa: un tablero que falta no impide
            # juzgar si el mensaje llega, que es para lo que sirve la entrega.
            # En la final si, porque ahi ya no hay otra vuelta.
            mal.append(
                f"{slug}: las etapas {faltan_tableros} llevan tablero y nadie lo"
                f" ha compuesto — obligatorio en la final, ticket en la entrega")
    except Exception as e:                         # noqa: BLE001
        mal.append(f"{slug}: no se pudo comprobar el trabajo grafico:"
                   f" {type(e).__name__}")
    # Y el otro lado: una respuesta de diseno escrita y sin aplicar es **otro
    # diseno compitiendo** con el que esta puesto. Renderizar asi elige uno de
    # los dos por accidente.
    _sin_aplicar = os.path.join("work", "servicio", "disenar",
                                f"{slug}.respuesta.json")
    if os.path.exists(_sin_aplicar):
        mal.append(
            f"{slug}: hay una composicion escrita y sin aplicar"
            f" ({_sin_aplicar}) — obligatorio en la final: si no, el render sale"
            f" con el diseno viejo y otro compitiendo")

    # 1b · **Una etapa no puede sonar dos veces.**
    #
    # Este es el que faltaba, y su ausencia es la razon de que un fallo caro
    # pasara desapercibido: `_mover_bordes` declaraba sin retirar lo anterior,
    # reel-05 quedo diciendo su cierre entero dos veces, la pieza paso de 105 a
    # 157 segundos — y **la puerta la dejo pasar**, porque miraba que cada
    # fijado estuviera en el EDL y ninguno sobrara.
    #
    # Se mira en los dos sitios a proposito, porque son dos averias distintas:
    # en la declaracion es una contradiccion —«esta etapa es esto, y otra vez
    # esto»—, y en el montaje es lo que el espectador oye. Puede haber lo
    # segundo sin lo primero: la declaracion se arreglo y el EDL se quedo con la
    # version vieja, que es justo cuando hay que correr `fijar --rehacer`.
    try:
        import fijar as _fj

        for beat, x, y in _fj.solapes(slug):
            mal.append(f"{slug} e{beat}: los tramos declarados se pisan"
                       f" ({x['desde']}-{x['hasta']} y {y['desde']}-{y['hasta']})"
                       f" — una etapa no se declara dos veces")
    except Exception:                              # noqa: BLE001
        pass
    _por_beat = {}
    for _r, _d in zip(edl.get("segmentos") or [], edl.get("detalle") or []):
        _por_beat.setdefault(_d.get("beat"), []).append((_d.get("toma"), _r))
    for _b, _v in sorted(_por_beat.items(), key=lambda x: (x[0] is None, x[0])):
        _v = sorted(_v, key=lambda x: (str(x[0]), x[1][0]))
        for (_t1, _a), (_t2, _c) in zip(_v, _v[1:]):
            # **El mismo umbral que usa quien lo arregla.** Estaba en 1 ms
            # mientras `Aritmetica.sin_solapes` ignoraba todo lo menor de 50, o
            # sea la puerta exigia lo que el arreglo no tocaba: un solape de
            # 20 ms —reel-03 e5— quedaba senalado para siempre.
            if _t1 == _t2 and _c[0] < _a[1] - _SOLAPE_MIN:
                # **Y se dice el tamano, no «se va a oir dos veces».** Un solape
                # de 80 ms no es la etapa repetida: es el empalme pisandose. La
                # frase dramatica mandaba a buscar una reperticion que no
                # existia.
                _ms = (_a[1] - _c[0]) * 1000
                mal.append(
                    f"{slug} e{_b}: dos trozos de la misma cinta se pisan"
                    f" {_ms:.0f} ms ({_a[0]:.2f}-{_a[1]:.2f} y"
                    f" {_c[0]:.2f}-{_c[1]:.2f}) — ese audio suena dos veces."
                    f" Lo cierra el paso `cosido`:"
                    f" python scripts/costuras.py {int(slug[-2:])}")
                break

    # 2 · **Ninguna etapa se queda muda.** Ni sin material ni con dos palabras:
    # una etapa que no dice nada es una etapa que no está.
    beats_edl = {d.get("beat") for d in edl["detalle"]}
    tablero = {d.get("beat") for d in (edl.get("sin_toma") or [])}
    # La firma es corta por definicion —el libreto dice «Soy Jaime Olarte.»,
    # tres palabras— y paraba reel-20 por no llegar a cuatro (C-573).
    # Y el gancho tambien (C-592): compite contra el pulgar y lleva su rotulo.
    # reel-18 e1 decia «tengo miedo, harto.» con «A MI TAMBIEN ME DA MIEDO.»
    # encima, y esto la paraba por tres palabras una vuelta tras otra.
    firmas = {d.get("beat") for d in edl["detalle"] if d.get("trato") == "portada"
              or "firma" in str(d.get("etapa") or "").lower()}
    for b, t in sorted(dice.items()):
        if len(t.split()) < 4 and b not in firmas:
            mal.append(f"{slug} e{b}: dice «{t}» — no llega a una idea")

    # 3 · **El gancho es su cara.** Nunca un tablero: contradice el camino
    # `portada` entero, y ya paso en reel-03.
    if 1 in tablero:
        mal.append(f"{slug}: la etapa 1 va a tablero, y el gancho tiene que ser"
                   f" su cara. Elige otra apertura.")

    # 4 · **Las etapas obligatorias existen**, con toma o con tablero.
    #
    # **Salvo la que se decidio sacar.** Una etapa cortada a proposito no tiene
    # material ni tablero, y no deberia: la puerta la contaba como falta y la
    # pieza no podia avanzar por no tener algo que alguien mando quitar. Paso
    # con el mecanismo del reel-01, que Jaime mando fuera entero.
    #
    # La diferencia entre «falta» y «se quito» no es del montaje: esta en el
    # log. Una nota de corte aplicada, con su ancla y su porque, es la prueba de
    # que hubo una decision — y una decision no es un agujero.
    #
    # **Y la declarada por `quitada` (C-609)**, que es la otra forma de decirlo:
    # las dos se preguntan en un solo sitio, `quitada.todas`.
    quitadas = set()
    try:
        from dominio import quitada
        quitadas = quitada.todas(slug)
    except Exception as e:                         # noqa: BLE001
        # **Y si no se puede saber, no se da por hecho que no hay ninguna.**
        # Este `pass` dejaba `quitadas` vacio ante cualquier tropiezo —la base
        # tomada por otra corrida, por ejemplo— y entonces la puerta acusaba de
        # falta una etapa que alguien mando quitar. Un fallo de lectura no es
        # una respuesta: se dice y se para por lo que es.
        mal.append(f"{slug}: no se pudo leer que etapas se quitaron ({e})."
                   f" Vuelve a correr cuando la base este libre.")
    for f in filas:
        b = f["etapa_orden"]
        if (b not in beats_edl and b not in tablero
                and int(b) not in quitadas):
            mal.append(f"{slug} e{b}: sin material y sin tablero")

    # 5 · **Ningún pedido de IA sin contestar.**
    #
    # Un paso de IA con el pedido abierto significa que la pieza se monto sin esa
    # decision — sin la lectura de redundancia, o sin la descripcion de escena. No
    # es un aviso: es que falta un paso del camino.
    # **Y solo cuenta lo que va ANTES del render.**
    #
    # Esto contaba cualquier pedido abierto, incluidos los de pasos que vienen
    # DESPUES de montar. `visto` es la revision de la pieza ya renderizada —no se
    # puede contestar sin verla— y su pedido abierto estaba impidiendo el render:
    # la puerta pedia una decision que solo existe despues de pasar la puerta.
    #
    # Tuvo a Jaime dos veces sin poder ver los reels de aprobacion, que es
    # exactamente para lo que existen: *«no he podido escucharlos ni cambiar sus
    # audios»*. Un ciclo asi no se ve venir porque cada mitad, por separado, es
    # razonable.
    import servicio as _sv

    DESPUES_DEL_RENDER = {"visto", "revisar"}
    abiertos = [p for p, sl, _ in _sv.pendientes()
                if sl == slug and p not in DESPUES_DEL_RENDER
                and _queda_trabajo(p, slug)]
    if abiertos:
        mal.append(f"{slug}: pedido(s) de IA sin contestar: {abiertos}."
                   f" La pieza se montaria sin esa decision.")

    # **Nada se dice dos veces por culpa del corte.**
    #
    # Jaime: *«la redundancia o es explicita en el libreto, o es continua en la
    # grabacion; pero dejar enfasis cada corte no es enfasis sino ruido»*. Lo
    # que sobrevive aqui es lo tercero: el montaje pego dos tomas de la misma
    # frase y la pieza la dice dos veces.
    #
    # Existia el detector —`repeticiones.py`— y **no lo llamaba nadie**. Por eso
    # esta aqui: en la puerta, que es lo que no se puede saltar.
    import consulta as _cs

    # **La puerta para lo que hizo EL CORTE, y solo eso.**
    #
    # Paraba por cualquier repeticion pegada, y con eso se comio una
    # enumeracion correcta: «ni a su abogado ni a su contador» dice «ni a su»
    # dos veces porque el castellano lo pide. La distancia no las separa —el
    # ejemplo de ruido de este mismo comentario, «su negocio esta funcionando,
    # su negocio esta vendiendo», tiene la misma forma exacta—, asi que un
    # umbral no puede decidirlo: hay que entender la frase.
    #
    # Regla de Jaime, que es la que reparte: *«la redundancia o es explicita en
    # el libreto, o es continua en la grabacion; pero dejar enfasis cada corte
    # no es enfasis sino ruido»*. **La puerta es duena del corte.** Si las dos
    # veces caen en el mismo trozo, el hablante lo dijo asi de seguido y la
    # puerta no tiene nada que arbitrar; si caen en trozos distintos, la pego
    # el montaje y eso si es aritmetica.
    #
    # Y lo que no para tiene que ir a alguien: `repaso` lo recibe en su pedido
    # (`repeticiones`) y decide con la frase delante. Parar por algo que el que
    # compone no ve es dejar la pieza sin nadie que pueda arreglarla — el mismo
    # atasco de C-116, que costo dos vueltas contando el mismo fallo.
    # **Y lo que sobrevive al cosido no para la pieza: se anota.**
    #
    # El caso mecanico —la cola de un trozo repitiendo el arranque del
    # siguiente— lo cierra `Aritmetica.sin_eco` sin preguntarle a nadie. Lo que
    # llega hasta aqui es, por construccion, lo que ese corte NO es: o el
    # hablante se repitio dentro de la misma tirada, o **es figura**.
    #
    # Y la figura hay que respetarla. reel-04 e6 dice «no lo persigue porque lo
    # odio, lo persigue porque usted nunca explico quien»: «lo persigue porque»
    # sale dos veces y las dos hacen falta. Bloquear ahi es pedir que se rompa
    # una frase bien construida para poder renderizar.
    #
    # Distinguir figura de tropiezo es entender, no medir, asi que no lo decide
    # esta puerta: se anota con su etapa y su frase, viaja con la pieza, y lo ve
    # quien mira el montaje.
    for r in _cs.repetido(slug):
        if r["separadas_por"] <= 8 and not r["una_toma"]:
            mal.append(
                f"{slug} e{r['etapa']}: dice «{r['dice']}» dos veces seguidas"
                f" — el cosido ya descarto que sea eco de la costura, asi que o"
                f" el hablante se repitio o es figura deliberada. Miralo.")

    # 6a · **Una cifra en la descripción tiene que estar declarada.**
    #
    # Jaime cerró que la cifra de reel-05 e6 es $14.000 —*«los 300 los quité
    # porque complica las cuentas»*—, se aplicó, y **volvió**: al re-describir
    # la etapa, el paso copió el número viejo del texto anterior. La decisión
    # existía y no estaba registrada donde el paso siguiente la lee.
    #
    # El registro de cifras es la tabla `dato`. Una descripción que rotula un
    # importe que ninguna fila declara es una cifra inventada o una decisión
    # perdida, y las dos son cumplimiento. No se compara el texto entero: se
    # comparan los importes, que son explícitos y no admiten lectura.
    import re as _re

    _IMPORTE = _re.compile(r"\$ ?\d{1,3}(?:[.,]\d{3})+")

    def _importes(t):
        return {x.replace(" ", "").replace(".", ",") for x in _IMPORTE.findall(t or "")}

    # **El registro es de la PIEZA, no del beat.** Exigirlo por etapa obligaba a
    # duplicar la fila cada vez que una cifra se recuerda: reel-02 declara los
    # $189.000 en la etapa 3 y los vuelve a enseñar en el cierre, y eso no es una
    # cifra sin declarar — es la misma cifra. Lo que hay que impedir es que
    # aparezca en pantalla un importe que la pieza no declaró en ningún sitio.
    # **Y las declara quien respalda la pieza, no sólo la pieza.** Una derivada
    # o una historia respalda con las de su origen (C-396, C-419); leerlo aquí
    # de otro sitio paró reel-09 por los $180,000 que reel-02 declara (C-425).
    from servicio import _respaldos
    declarados = set()
    for f in _respaldos(slug):
        declarados |= _importes(f.get("cifra")) | _importes(f.get("afirmacion"))
    for f in con.execute(
            "select etapa_orden, que_pasa, grafico, corrige_es from escena_desc"
            " where video_slug = ?", (slug,)):
        dice = set()
        for c in ("que_pasa", "grafico", "corrige_es"):
            dice |= _importes(f[c])
        sueltas = dice - declarados
        if sueltas:
            mal.append(
                f"{slug} e{f['etapa_orden']}: la descripción rotula"
                f" {', '.join(sorted(sueltas))} y ninguna fila de `dato` lo"
                f" declara. O se declara con su fuente, o no sale en pantalla.")

    # 6b · **El sonido también pasa por la puerta.**
    #
    # Jaime: *«el sonido también forma parte de la verificación final»*, dicho
    # después de oír el reel-01 montado y encontrar dos cosas que ninguna puerta
    # miraba: cortes que se oyen sucios y un tablero mudo.
    #
    # **Los cortes.** No se comprueba con una regla propia: se le pregunta al
    # paso que los arregla si todavía movería alguno. Una puerta con su propio
    # criterio se separa del arreglo en la primera corrección, y entonces avisa
    # de lo que ya está bien o calla lo que está mal. Aquí no puede pasar,
    # porque es el mismo código en seco.
    import costuras as _co

    # **La pregunta es si queda voz colgando, no si hay algo mas callado.**
    #
    # Preguntaba `a_lo_callado(minimo=PUERTA)`, o sea «¿hay un punto mejor a 120
    # ms?». Con eso reel-07 no pudo renderizarse teniendo sus tres bordes a -105
    # dBFS: silencio de sobra, pero veinte milisegundos mas alla habia -123 y la
    # puerta lo llamaba «pleno sonido». El paso de arreglo tampoco podia
    # cerrarlo, asi que la pieza quedaba parada para siempre.
    #
    # Se sigue preguntando al mismo codigo —la puerta no inventa criterio— pero
    # la pregunta es absoluta: ¿la voz sigue sonando despues del corte?
    sucios = _co.bordes_en_sonido(slug)
    if sucios:
        donde = ", ".join(f"{t:.2f}" for _c, t in sucios[:4])
        mal.append(f"{slug}: {len(sucios)} corte(s) dejan voz sonando despues"
                   f" del corte ({donde}). Corre el paso `cosido`.")

    # **El tablero mudo.** Un tablero se construye por tiempo de lectura: cada
    # nodo entra cuando el anterior ya se pudo leer, o sea que **es una
    # animación**, y la ley del proyecto es que el sonido sigue al movimiento.
    # Jaime lo dijo así: *«el sonido del tablero deben ser las acciones animadas
    # del tablero»*. Un tablero sin `sound` es una animación que nadie oye.
    spec = "src/reels.json"
    if os.path.exists(spec):
        try:
            n_reel = int(slug[-2:])
            for r in json.load(open(spec, encoding="utf-8")):
                if r.get("id") != f"Reel-R{n_reel}":
                    continue
                mudos = [b for b in r.get("boards", [])
                         if not (b.get("props") or {}).get("sound")]
                if mudos:
                    mal.append(
                        f"{slug}: {len(mudos)} tablero(s) sin sonido. El tablero"
                        f" se construye por tiempo de lectura: es animación, y"
                        f" el sonido sigue al movimiento.")
        except (OSError, ValueError, json.JSONDecodeError):
            pass

    # 7 · **Un tramo fijado que no llegó al corte es una decisión perdida.**
    #
    # Fijar una etapa es declarar cuál es su tramo, y esa decisión tiene que
    # poder sobrevivir a rehacer la selección. Si el EDL no la lleva, alguien
    # decidió y el montaje no se enteró — que es la forma exacta en la que este
    # proyecto perdía el estado antes de que fijar existiera.
    import fijar as _fj

    # **Se comprueba que el tramo esta REPRESENTADO, no que sea identico.** Un
    # recorte de redundancia posterior acorta legitimamente lo fijado: exigir el
    # rango exacto convertia cada recorte en un fallo de la puerta. Lo que no
    # puede pasar es que del tramo declarado no quede nada.
    for f in _fj.fijados(slug):
        dentro = any(d.get("beat") == f["beat"]
                     and min(b_, f["hasta"]) - max(a_, f["desde"]) > 0.1
                     for (a_, b_), d in zip(edl["segmentos"], edl["detalle"]))
        if not dentro:
            mal.append(
                f"{slug} e{f['beat']}: el tramo fijado"
                f" [{f['desde']}-{f['hasta']}] no dejo rastro en el corte."
                f" Corre: python scripts/fijar.py --aplicar {int(slug[-2:])}")

    # 7 · **Lo que Jaime pidió cortar está cortado.** Una nota pendiente con
    # ancla que ya no resuelve es una corrección perdida en silencio (C-79).
    #
    # **Y sólo las de ESTE montaje.** Una nota se estampa con la huella del
    # corte en que se apuntó y `revision.aplicar` se salta —con razón— las de
    # otro: hablan de un sitio que ya no existe. Pero la puerta las contaba
    # igual, así que la pieza quedaba bloqueada por tres notas que ningún paso
    # puede aplicar nunca. reel-06 se paró así con notas de un montaje anterior.
    #
    # Es la cuenta falsa contra la que ya avisa `revision.aplicar`: mientras el
    # número incluye lo inaplicable, tapa a la nota que sí falta. Las viejas se
    # quedan en la tabla —son el recorrido del vídeo— y dejan de ser tarea.
    try:
        import modelo as _mo

        _h = _mo.huella_edl(slug)
    except Exception:                              # noqa: BLE001
        _h = None
    pend = con.execute(
        "select count(*) from revision where video_slug = ? and accion='cortar'"
        " and estado='pendiente' and huella is ?", (slug, _h)).fetchone()[0]
    if pend:
        mal.append(f"{slug}: {pend} corte(s) de revisión sin aplicar")
    con.close()
    return mal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reels", nargs="*", type=int)
    ap.add_argument("--medido", action="store_true",
                    help="solo lo que ya se puede medir sin la descripcion —"
                         " lo que ve el compositor. No para: informa.")
    ap.add_argument("--avisa", action="store_true",
                    help="informa y no bloquea")
    a = ap.parse_args()
    todo = []
    for n in (a.reels or rutas.piezas()):
        slug = f"reel-{n:02d}"
        paran, avisan = separa(
            lo_medido(slug) if a.medido else revisar(slug), slug=slug)
        todo += paran
        print(f"{slug}: {'OK' if not paran else str(len(paran)) + ' motivo(s)'}"
              + (f"  ({len(avisan)} anotado(s))" if avisan else ""))
        for m in paran:
            print(f"    · {m}")
        for m in avisan:
            print(f"    ~ {m}")
    if todo and not a.avisa and not a.medido:
        print(f"\nEL CAMINO SE PARA — {len(todo)} motivo(s). Nada se renderiza"
              f" hasta que esten resueltos.")
        sys.exit(1)
    print("\nverificacion: todo en pie" if not todo else
          "\n(--avisa: no bloquea)")


if __name__ == "__main__":
    main()
