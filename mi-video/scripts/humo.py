"""Prueba de humo: que las guardas responden y que el camino lleva la pieza.

Jaime, 9-9-2026, despues de cinco corridas que descubrieron cinco averias en
fila: *«¿cuantas veces mas necesitas recorrer?»*, y despues: *«por favor haz una
prueba de humo»*. Es la respuesta a las dos: en vez de renderizar para saber si
algo funciona, se comprueba aqui en segundos y sin gastar una corrida.

**No sustituye a `guardas.mjs`.** Aquella comprueba que la aguja de cada
correccion sigue en el codigo —que el mecanismo no se perdio en una
reescritura—; esto **lo ejecuta** y mira lo que devuelve. Una aguja puede estar
puesta y la funcion hacer lo contrario.

    python scripts/humo.py            # y sale 1 si algo esta roto
"""
from __future__ import annotations

import io
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PIEZA = "reel-03"


class Humo:
    """Las pruebas y su cuenta. Cada una dice que midio, no si 'paso'."""

    def __init__(self):
        self.en_pie, self.rotas = [], []

    def mide(self, cual, cierto, dice):
        (self.en_pie if cierto else self.rotas).append(
            f"{'OK  ' if cierto else 'MAL '} {cual}: {dice}")
        return cierto

    def cuenta(self):
        print("\n".join(self.en_pie + self.rotas))
        print(f"\nhumo: {len(self.en_pie)} en pie · {len(self.rotas)} rotas")
        return 1 if self.rotas else 0


def _perdida_no_se_calla(h):
    from dominio import contestado as c

    m = f"{PIEZA} e1: el tramo fijado [340.711-342.191] no dejo rastro en el corte."
    h.mide("C-341", c.contestado(m, PIEZA) is None,
           "una decision perdida NO la contesta otra decision")
    h.mide("C-341", c.contestado(f"{PIEZA} e6: sin material y sin tablero",
                                 PIEZA) is not None,
           "y la duda legitima si la contesta su nota")


def _las_dos_puertas_leen_igual(h):
    """La puerta a mano y la de la linea tienen que decir lo mismo.

    `separa` solo consulta lo que Jaime ya decidio si se le pasa la pieza, y el
    servicio la llamaba sin ella: `verificar.py 3` daba «todo en pie» y la
    linea paraba esa misma pieza por un motivo que la nota #661 contesta desde
    el 5-9. Dos respuestas distintas de la misma regla — y la que se mira a
    mano era la que no mandaba. C-351.
    """
    import inspect

    import verificar
    from servicios import verificar as sv

    fuente = inspect.getsource(sv.ServicioVerificar.correr)
    h.mide("C-351", "slug=pieza.slug" in fuente,
           "el servicio le pasa la pieza a `separa`")
    mal = ["reel-03 e6: sin material y sin tablero"]
    h.mide("C-351",
           verificar.separa(mal, slug="reel-03")[0] == []
           and verificar.separa(mal)[0] != [],
           "y con la pieza delante deja de parar lo ya contestado")


def _la_maquina_no_se_aprueba_sola(h):
    """Aprobar es de una persona, y ahora se pregunta en un solo sitio.

    `puertas._aprobada` leia la tabla `aprobacion` y `estado.json` publicaba su
    propia cuenta por segmentos: dos respuestas a la misma pregunta. Al unirlas
    en el marcador —la fuente unica— habia que conservar la guarda que la tabla
    daba gratis: la linea no puede etiquetar `aprobado` y abrirse la puerta.
    """
    from dominio import segmento as sg

    h.mide("C-354", sg.es_suya("jaime") and sg.es_suya("Jaime")
           and sg.es_suya("jaime · aprobo la pieza el 7-9-2026"),
           "una etiqueta de una persona cuenta como aprobacion")
    h.mide("C-354",
           not sg.es_suya("la linea") and not sg.es_suya("servicio")
           and not sg.es_suya("compositor") and not sg.es_suya("")
           and not sg.es_suya("alguien que no existe"),
           "y una de un oficio, un paso o un desconocido, no")
    # **Y el derecho es del TIPO, no del nombre.** C-363: si entra otra
    # persona, aprueba por ser persona y no por llamarse como se llame.
    from dominio.autor import Autor, puede

    h.mide("C-363", (Autor.de("jaime") or Autor.de("x")).tipo == "persona"
           and puede("jaime", "aprobar") and not puede("compositor", "aprobar"),
           "la agencia cuelga del tipo, no del nombre")
    h.mide("C-404", puede("disenador", "aprobar"),
           "el diseñador aprueba tramos contra el vídeo (Jaime, 12-9)")
    h.mide("C-363", puede("compositor", "decidir criterio")
           and puede("la linea", "medir") and not puede("la linea", "decidir criterio"),
           "y cada tipo puede lo suyo: la linea mide, el oficio decide")


def _el_marcador_propone_y_no_firma(h):
    """Un fichero no prueba quien lo escribio, asi que no puede aprobar.

    Jaime, 10-9-2026: *«la guarda es el Json, y lo que verifica y garantiza
    integridad es que solo se pueda modificar con los permisos»*, y despues:
    *«elimina todas las guardas sintomaticas, busquemos refuerzos
    estructurales»*.

    Esto no comprueba que nada haya salido mal: **ejecuta el ataque**. Un oficio
    tiene `Write` sobre el marcador; escribe ahi que la etapa esta aprobada y
    firma «jaime». Si el sistema lo acepta, la firma no vale nada.

    Aguanta por dos cosas a la vez, y hacen falta las dos: el lector va a la
    base y no al fichero —antes iba al fichero, asi que el permiso se
    comprobaba al escribir y se regalaba al leer—, y la puerta rechaza que un
    oficio firme por una persona. C-369.
    """
    import json

    from dominio import estado, segmento as sg

    slug = PIEZA
    estado.escribe(slug)
    d = estado.lee(slug)
    abierto = next((f for f in d.get("segmentos") or [] if not f["aprobado"]), None)
    if not abierto:
        h.mide("C-369", True, "no hay segmento abierto con el que probar")
        return
    n = abierto["etapa"]
    abierto["etiqueta"] = abierto["propone"] = "aprobado"
    abierto["por"] = "jaime"
    json.dump(d, open(estado.ruta(slug), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    estado.aplica(slug)
    seg = next(x for x in sg.Segmento.de(slug) if x.n == n)
    h.mide("C-369", seg.etiqueta != "aprobado",
           "un oficio no aprueba escribiendolo en el marcador")
    h.mide("C-369", not sg.aprobada(slug),
           "y la pieza no queda aprobada por un fichero")
    estado.escribe(slug)


def _una_atascada_no_para_la_tanda(h):
    """Una pieza atascada no puede costarle el turno a las otras seis.

    Jaime, 10-9-2026, viendo la corrida: la regla ya estaba escrita en
    `_recorrer` —*«apagar el reparto por una es dejar de repartir»*— y la
    condicion miraba la bandera `--despachar` en vez de cuantas piezas hay en
    juego. reel-02 se atasco en su corte y la corrida murio con reel-03 y
    reel-06 en `verificado`, listas para montar y sin llegar a su turno.

    No se comprueba leyendo el codigo: se ejecuta el reparto con una pieza
    plantandose y se mira que las demas hayan avanzado. C-370.
    """
    import registro

    h.mide("C-370", "planta=solo_una" in open(
        "scripts/avanzar.py", encoding="utf-8").read(),
        "plantarse depende de cuantas piezas hay, no de una bandera")
    # Y el aviso no se calla: una atascada sale en el parte aunque el reparto siga.
    hubo = registro.atascadas({1: {"slug": "reel-01", "motivo": "x"},
                               2: {"slug": "reel-02",
                                   "motivo": "lleva dos intentos fallando"}})
    h.mide("C-370", hubo == 1, "y la atascada sale en el parte, no en silencio")


def _un_paso_que_falla_deja_su_diagnostico(h):
    """El motivo es una etiqueta; el diagnostico es lo que el paso dijo.

    `montar.sh` muere con `set -e` dentro de `render.mjs`, asi que su ultima
    linea de stdout es «bundle listo en 13.0 s» —progreso— y eso quedo escrito
    como la causa de que reel-03 y reel-06 no se montaran. El error de node
    estaba en stderr y se tiraba al salir del paso.

    No se comprueba leyendo: se ejecuta un paso que falla igual —progreso en
    stdout, error en stderr— y se mira que el error este en el registro. C-371.
    """
    import registro
    import servicios

    guion = "work/humo-falla.py"
    os.makedirs("work", exist_ok=True)
    open(guion, "w", encoding="utf-8").write(chr(10).join([
        "import sys",
        "print('bundle listo en 13.0 s')",
        "print('Error: la fuente no existe', file=sys.stderr)",
        "raise SystemExit(1)"]))
    r = servicios.ServicioScript("montado", guion).correr(servicios.Pieza(99))
    h.mide("C-371", not r.ok and "bundle listo" in r.motivo,
           "el motivo sigue siendo la ultima linea de stdout")
    con = registro._con()
    fila = con.execute("select detalle from incidencia where toma='reel-99'"
                       " order by id desc limit 1").fetchone()
    con.execute("delete from incidencia where toma='reel-99'")
    con.commit()
    con.close()
    os.remove(guion)
    h.mide("C-371", bool(fila) and "la fuente no existe" in (fila[0] or ""),
           "y lo que dijo por stderr queda en el registro, no se pierde")


def _lo_que_no_se_dibuja_no_se_renderiza(h):
    """Lo que la comprobacion barata da por roto no llega al peldano caro.

    `revisarTablero` comprueba **solo lo que rompe el render** —lo dice de si
    misma— y sus faltas viajaban en el mismo saco que las demas, que no para
    el lote. Asi que reel-03 murio en el frame 550 por «Techo necesita
    titulo», impreso mas arriba en la misma corrida.

    Se ejecuta la guarda de `montar.sh` —su propia expresion, sacada del
    fichero— y se compara el `rompe` del spec con lo que dice la fuente de esas
    faltas. C-372.
    """
    import json
    import re
    import subprocess

    falso = "work/humo-spec.json"
    json.dump([{"id": "Reel-R9", "rompe": ["«X» necesita `y` y no llega"]}],
              open(falso, "w", encoding="utf-8"))
    texto = open("scripts/montar.sh", encoding="utf-8").read()
    m = re.search(r'ROMPE=\$\(node -e "(.+?)"\)', texto)
    expr = m.group(1).replace("src/reels.json", falso).replace("$n", "9")
    out = subprocess.run(["node", "-e", expr], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    os.remove(falso)
    h.mide("C-372", "necesita" in out.stdout,
           "montar.sh lee `rompe` y para antes de pagar el render")
    # Y el spec lo trae de donde nace: las faltas de `revisarTablero`.
    import rutas
    slugs = json.dumps([f"reel-{n:02d}" for n in rutas.piezas()])
    dice = subprocess.run(
        ["node", "--input-type=module", "-e",
         "import {tablerosDe} from './scripts/reels/base.mjs';"
         "import {idDe} from './scripts/reels/material.mjs';"
         f"const mal={slugs}.filter(s=>tablerosDe(s).faltas.length).map(s=>idDe(s));"
         "console.log(JSON.stringify(mal));"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    try:
        nacen = set(json.loads(dice.stdout.strip().splitlines()[-1]))
    except Exception:                              # noqa: BLE001
        nacen = None
    spec = json.load(open("src/reels.json", encoding="utf-8"))
    marcadas = {r["id"] for r in spec if r.get("rompe")}
    h.mide("C-372", nacen is not None and nacen == marcadas,
           f"y el spec marca exactamente las que nacen rotas: {sorted(marcadas)}")

def _documentar_no_engorda_el_fichero(h):
    """El techo cuenta sentencias, y en `.mjs` contaba tambien la prosa.

    `tamano.py` exime el docstring en Python porque *«un docstring largo no hace
    un fichero mas dificil de cambiar»*, y en `.mjs` no eximia el bloque JSDoc:
    el mismo fichero pesaba mas explicado con `/**` que con `//`, y la unica
    salida era documentar peor. C-373.
    """
    import tamano

    prueba = "work/humo-jsdoc.mjs"
    open(prueba, "w", encoding="utf-8").write(chr(10).join([
        "/**", " * Por que esta regla es como es, en tres lineas", " */",
        "export const uno = 1;"]))
    n = tamano._codigo(prueba)
    os.remove(prueba)
    h.mide("C-373", n == 1, f"el JSDoc no cuenta: {n} sentencia(s) de 4 lineas")


def _prueba_movida_va_al_compositor(h):
    import fijar

    visto = {}
    antes, fijar._al_compositor = fijar._al_compositor, (
        lambda slug, movidas: visto.update(movidas))
    try:
        fjs = [dict(f) for f in fijar.fijados(PIEZA)]
        for f in fjs:
            if f["beat"] == 1 and 340 < f["desde"] < 341:
                f["huella"] = "0000deadbeef"
        vivas = fijar._con_prueba_viva(PIEZA, fjs)
    finally:
        fijar._al_compositor = antes
    h.mide("C-342", 1 not in {f["beat"] for f in vivas},
           "la etapa con la prueba movida se queda FUERA")
    h.mide("C-342", visto.get(1) == 1, "y su encargo va al compositor")


def _declarado_no_se_quita(h):
    from dominio.tijera import Tijera

    tij = Tijera(PIEZA)
    i = next((k for k in range(len(tij)) if tij.fijado(k)), None)
    antes = len(tij)
    h.mide("C-343", i is not None and tij.quitar({i}) == 0 and len(tij) == antes,
           f"quitar un trozo declarado devuelve 0 y no toca la lista ({antes})")


def _tiquet_sellado(h):
    from dominio import ticket as t

    h.mide("C-344", bool(t._huella(PIEZA)), "el corte se sabe sellar")
    h.mide("C-344", t.caducar(PIEZA) == [],
           "y caducar no mata al que lleva la huella de hoy")


def _vuelve_al_punto(h):
    from dominio.fase import antes_de

    h.mide("C-345", antes_de("descrito") == "repasado",
           "antes de «descrito» es «repasado»")
    h.mide("C-345", antes_de("disenado") == "descrito",
           "antes de «disenado» es «descrito»")


def _pregunta_quemada(h):
    from dominio import disparo, oficio

    class Falso:
        huella = ("humo", 1)

        def llama(self):
            return False

        def __str__(self):
            return "oficio de humo"

    de, disparo._LLAMADOS[Falso.huella] = oficio.Oficio.de, (0, 0.0)
    oficio.Oficio.de = staticmethod(lambda slug: Falso())
    bash, oficio.POR_BASH = oficio.POR_BASH, True
    try:
        for _ in range(4):
            disparo.llama(PIEZA)
        veces = disparo._LLAMADOS[Falso.huella][0]
        h.mide("C-346", veces == disparo.TOPE + 1,
               f"{disparo.TOPE} llamadas y luego calla, dicho en voz alta")
        disparo._LLAMADOS[Falso.huella] = (veces, time.time()
                                           - disparo.REINTENTO - 1)
        disparo.llama(PIEZA)
        h.mide("C-346", disparo._LLAMADOS[Falso.huella][0] == 1,
               f"y pasado el plazo ({disparo.REINTENTO // 60} min) repregunta")
    finally:
        oficio.Oficio.de, oficio.POR_BASH = de, bash
        disparo._LLAMADOS.pop(Falso.huella, None)


def _marcador_viaja(h):
    import servicio

    m = servicio._marcador(PIEZA)
    h.mide("C-347", bool(m) and m["fichero"] == f"ads/{PIEZA}/estado.json",
           "el pedido lleva la ruta del marcador y su etiqueta")
    servicio._piso_cache = None
    h.mide("C-347", "El marcador: el JSON que viaja" in servicio._piso(),
           "y el piso le dice al oficio que lo lea y lo escriba")


def _interprete_resuelto(h):
    """El paso `.sh` no depende de la consola desde la que se llamo."""
    import rutas

    sh = rutas.interprete()
    h.mide("C-349", bool(sh) and os.path.exists(sh),
           f"un paso .sh sabe con que correrse: {sh}")


def _camino_lleva_el_adelanto(h):
    """Lo unico que no es una guarda: que la pieza de hoy lleva lo declarado."""
    edl = json.load(open(f"ads/{PIEZA}/edl-sell.json", encoding="utf-8"))
    h.mide("camino", any(340 < a < 341 for a, _ in edl["segmentos"]),
           f"el EDL lleva el adelanto ({edl.get('duracion_montada_s')} s,"
           f" {len(edl['segmentos'])} segmentos)")
    plan = f"work/scenes/{PIEZA}/plan-full.json"
    if os.path.exists(plan):
        p = json.load(open(plan, encoding="utf-8"))
        h.mide("camino", p["escenas"][0].get("montado_desde") == 0
               and 340 < p["escenas"][0].get("origen", [0])[0] < 341
               if isinstance(p["escenas"][0].get("origen"), list)
               else p["escenas"][0].get("montado_desde") == 0,
               f"el plan abre por el adelanto ({len(p['escenas'])} escenas)")


def _ilegible_vuelve_a_la_cola(h):
    """Una respuesta que no se puede leer no puede dejar a la pieza sin cola.

    `pendientes()` cuenta un pedido como servido **porque existe su respuesta al
    lado**, no porque se pueda leer. Con el JSON roto ahi, el pedido desaparecia
    de la cola, `turno.py` no lo ofrecia y nadie tenia a quien llamar: la pieza
    esperaba a nadie y sin una linea que lo dijera. C-496.
    """
    import glob
    import shutil

    import servicio

    carpeta = os.path.join("work", "servicio", "disenar")
    os.makedirs(carpeta, exist_ok=True)
    pedido = os.path.join(carpeta, "humo-99.pedido.json")
    respuesta = os.path.join(carpeta, "humo-99.respuesta.json")
    try:
        io.open(pedido, "w", encoding="utf-8").write('{"paso": "disenar"}')
        io.open(respuesta, "w", encoding="utf-8").write('{"roto": ')
        antes = [s for p, s, _ in servicio.pendientes() if s == "humo-99"]
        h.mide("C-496", not antes,
               "con la respuesta rota ahi, el pedido NO sale en la cola")
        h.mide("C-496", servicio.recoger("disenar", "humo-99") is None,
               "y recoger no se inventa una respuesta")
        despues = [s for p, s, _ in servicio.pendientes() if s == "humo-99"]
        h.mide("C-496", bool(despues),
               "pero la aparta y el pedido vuelve a la cola")
        h.mide("C-496", bool(glob.glob(os.path.join(
            carpeta, "usadas", "humo-99.*.rechazada.respuesta.json"))),
            "y queda archivada como rechazada, no borrada")
    finally:
        for f in (pedido, respuesta):
            if os.path.exists(f):
                os.remove(f)
        for f in glob.glob(os.path.join(carpeta, "usadas", "humo-99.*")):
            os.remove(f)
        if os.path.isdir(carpeta) and not os.listdir(carpeta):
            shutil.rmtree(carpeta, ignore_errors=True)


def _un_buzon_sin_oficio_no_existe(h):
    """Cada buzon declarado dice quien lo atiende y que fase mueve.

    Estaba escrito en tres sitios y el mismo hueco se abrio tres veces: C-394
    por `revalidar`, C-397 por `repaso` y `fuentes`, que llego hasta hoy. Un
    buzon sin oficio escribe su pedido y no llama a nadie. C-496.
    """
    import avanzar
    import turno
    from dominio import oficio

    h.mide("C-496", all(len(v) == 2 and all(v) for v in oficio.BUZONES.values()),
           f"los {len(oficio.BUZONES)} buzones declaran oficio Y fase")
    h.mide("C-496", set(oficio.DE) == set(avanzar.DE_QUIEN)
           == set(turno.BUZON.values()),
           "y las tres vistas salen de la misma tabla")


def _un_seguro_que_no_puede_fallar_no_es_un_seguro(h):
    """Los dos que prometían parar y no podían. C-500.

    `pipeline.sh` llama a `modelo.py` con `|| exit 1` y `main()` devolvía
    `None`: salía con 0 dijera lo que dijera. Y `montar.sh` tenía una rama
    `if [ "$FINAL" = "1" ]` con `FINAL=` sin asignar en ningún sitio del repo.
    Los dos llevaban meses escritos como si protegieran.
    """
    import inspect

    import modelo

    fuente = inspect.getsource(modelo.main)
    h.mide("C-500", "return 1" in fuente and "return 0" in fuente,
           "modelo.main() sale con codigo, que es lo que pipeline.sh esperaba")
    # Mirando CODIGO, no el comentario que cuenta la historia: el propio
    # aviso de montar.sh cita la rama, y buscarla en el texto entero se caza
    # a si misma.
    guion = [l for l in io.open(os.path.join("scripts", "montar.sh"),
                                encoding="utf-8").read().splitlines()
             if not l.lstrip().startswith("#")]
    h.mide("C-500", not any("$FINAL" in l for l in guion),
           "y montar.sh ya no tiene la rama que nunca corria")


def _el_segundo_dice_de_que_video_es(h):
    """Las dos escalas, y una sola VELOCIDAD en todo Python. C-501.

    La entrega va acelerada y el montaje no —medido sobre las siete piezas, un
    factor de 1,13 a 1,20—, así que «el segundo 30» son dos sitios distintos.
    Había tres constantes llamadas `VELOCIDAD`: una en 1,15 que sí acelera, y
    dos en 1,0 que sólo dividían por uno.
    """
    import glob

    import beats
    from dominio import ticket as _tk

    con_nombre = []
    for f in glob.glob(os.path.join("scripts", "**", "*.py"), recursive=True):
        for l in io.open(f, encoding="utf-8", errors="replace"):
            if l.startswith("VELOCIDAD ="):
                con_nombre.append(f.replace(chr(92), "/"))
    h.mide("C-501", con_nombre == ["scripts/beats.py"],
           f"una sola VELOCIDAD en Python: {con_nombre or 'ninguna'}")
    treinta, movido = _tk.a_montaje(30, "entrega")
    h.mide("C-501", abs(treinta - 30 * beats.VELOCIDAD) < 1e-6 and movido > 0,
           f"30s de la entrega son {treinta}s del montaje ({movido:+}s)")
    h.mide("C-501", _tk.a_montaje(30, "montaje") == (30.0, 0.0),
           "y 30s del montaje no se mueven")


def main():
    import humo_del_corte as _del_corte

    h = Humo()
    for f in (_perdida_no_se_calla, _las_dos_puertas_leen_igual,
              _la_maquina_no_se_aprueba_sola,
              _el_marcador_propone_y_no_firma,
              _una_atascada_no_para_la_tanda,
              _un_paso_que_falla_deja_su_diagnostico,
              _lo_que_no_se_dibuja_no_se_renderiza,
              _documentar_no_engorda_el_fichero,
              _prueba_movida_va_al_compositor,
              _declarado_no_se_quita, _tiquet_sellado, _vuelve_al_punto,
              _pregunta_quemada, _marcador_viaja, _interprete_resuelto,
              _camino_lleva_el_adelanto,
              _ilegible_vuelve_a_la_cola,
              _un_buzon_sin_oficio_no_existe,
              _un_seguro_que_no_puede_fallar_no_es_un_seguro,
              _el_segundo_dice_de_que_video_es,
              _del_corte._lo_firmado_se_puede_volver_a_poner,
              _del_corte._el_corte_nace_derivado):
        try:
            f(h)
        except Exception as e:                     # noqa: BLE001
            h.mide(f.__name__, False, f"revento: {type(e).__name__}: {e}")
    return h.cuenta()


if __name__ == "__main__":
    raise SystemExit(main())
