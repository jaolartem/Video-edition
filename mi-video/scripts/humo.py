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
           and not sg.es_suya("disenador") and not sg.es_suya("")
           and not sg.es_suya("alguien que no existe"),
           "y una de un oficio, un paso o un desconocido, no")
    # **Y el derecho es del TIPO, no del nombre.** C-363: si entra otra
    # persona, aprueba por ser persona y no por llamarse como se llame.
    from dominio.autor import Autor, puede

    h.mide("C-363", (Autor.de("jaime") or Autor.de("x")).tipo == "persona"
           and puede("jaime", "aprobar") and not puede("compositor", "aprobar"),
           "la agencia cuelga del tipo, no del nombre")
    h.mide("C-363", puede("compositor", "decidir criterio")
           and puede("la linea", "medir") and not puede("la linea", "decidir criterio"),
           "y cada tipo puede lo suyo: la linea mide, el oficio decide")


def _lo_retirado_no_esta_en_el_catalogo(h):
    """Lo que Jaime retiro no puede seguir en la tabla esperando a que lo pidan.

    La cortinilla se retiro una vez, `camara.mjs :: RETIRADAS` lo declaraba con
    su sustituto, y el catalogo la seguia ofreciendo con cuatro etapas usandola.
    Es el mismo fallo que hizo salir reel-01 con una placa de 0,7 s: el menu la
    daba por muerta y el mecanismo seguia vivo. C-362.
    """
    import json
    import subprocess

    import basedatos

    try:
        r = json.loads(subprocess.run(
            ["node", "-e", "import('./scripts/camara.mjs').then(m =>"
                           " console.log(JSON.stringify(m.RETIRADAS || {})))"],
            capture_output=True, text=True, timeout=30).stdout.strip() or "{}")
    except Exception:                              # noqa: BLE001
        r = {}
    h.mide("C-362", bool(r), "hay retiradas declaradas y se pueden leer")
    cx = basedatos.abrir()
    vivas = {x[0] for x in cx.execute("select nombre from transicion")}
    h.mide("C-362", not (set(r) & vivas),
           "y ninguna sigue en el catalogo de transiciones")


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
        oficio.Oficio.de = de
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


def main():
    h = Humo()
    for f in (_perdida_no_se_calla, _las_dos_puertas_leen_igual,
              _la_maquina_no_se_aprueba_sola,
              _lo_retirado_no_esta_en_el_catalogo,
              _prueba_movida_va_al_compositor,
              _declarado_no_se_quita, _tiquet_sellado, _vuelve_al_punto,
              _pregunta_quemada, _marcador_viaja, _interprete_resuelto,
              _camino_lleva_el_adelanto):
        try:
            f(h)
        except Exception as e:                     # noqa: BLE001
            h.mide(f.__name__, False, f"revento: {type(e).__name__}: {e}")
    return h.cuenta()


if __name__ == "__main__":
    raise SystemExit(main())
