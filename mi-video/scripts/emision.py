"""**El control de emisión: lo que una cadena mide antes de emitir, escena a escena.** C-596.

Jaime, 19-10-2026, eligiendo el criterio de cine y televisión para cerrar W40:
el control de emisión **por código** —lo medible no lo mira un agente—. Y lo que
lo ordena, de la misma mañana: *«si hay un error es un error en una escena
concreta»*. Así que cada medida se parte por las escenas del plan
(`fotogramas.escenas`) y cada fallo sale con su escena, su etapa y la fase que
lo arregla:

    sonoridad  la pieza: −14 ±1,5 LUFS integrados        nivelado
    pico       la pieza: ≤ −1 dBTP (`suena.PICO_MAX`)    nivelado
    nivel      la escena a más de 4 LU de la pieza       sólo avisa: lo ve el visto
    silencio   ≤ `suena.AIRE_MAX`                         cosido
    negro      > 0,5 s (`blackdetect`)                    cortado
    congelado  > 0,5 s (`freezedetect`)                   cortado
    lectura    tablero, panel o recorte más corto que
               lo que cuesta leerlo (`lectura.json`)      disenado
    formato    1080×1920, 30 fps, duración del spec ±0,1 s   montado (escena 0: la pieza)

**El nivel por escena avisa, no devuelve.** Con ±1,5 LUFS por escena, reel-21
abría tres tiquets a `cosido`: el gancho a −19,0, que sí se oye, y dos escenas a
−12,0 y −12,2, que son una voz variando. `cosido` mueve bordes y no cambia
niveles, así que la escena daba la vuelta entera para acabar igual; y el nivel
por escena lo iguala la voz limpia tras aprobar (#91). Lo que se separa más de
`SEPARA_LU` de la pieza va al documento, con cuánto y hacia dónde, y lo decide
quien lo mira.

**Una pasada.** La imagen se lee en la misma de `suena` (`suena.traza`): los
filtros miden y dejan pasar, y el render ya se decodificaba entero para oírlo.

**Una medida, un sitio.** El documento de revisión (`dominio/documento.py`)
lee `por_escena` y no mide otra vez; y lo que pide leerse lo cuenta
`Documento._capas`, la cuenta que el documento enseña, para que la alerta y la
cifra que ve el agente no puedan discrepar. El parte se guarda con la huella de
lo que midió (`work/emision/`): mientras render, spec y plan no cambien, se lee.

    python scripts/emision.py 19            # el parte; sale con 1 si hay fallos
    python scripts/emision.py 19 --atender  # y un tiquet por fallo (`medido`)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fotogramas  # noqa: E402
import rutas  # noqa: E402
import suena  # noqa: E402
from dominio.documento import CAPAS, Documento  # noqa: E402

FPS = 30
ANCHO, ALTO = 1080, 1920
HOLGURA_LUFS = 1.5
#: Lo que una escena se puede separar de la integrada de su pieza sin avisar.
SEPARA_LU = 4.0
HOLGURA_DURA = 0.1
#: Negro o imagen quieta más larga que esto es un hueco en la emisión.
QUIETO_MAX = 0.5
IMAGEN = f"blackdetect=d={QUIETO_MAX}:pix_th=0.10,freezedetect=n=-60dB:d={QUIETO_MAX}"
#: Lo que firma un tiquet de este paso: así se reconoce el suyo al volver.
MARCA = "emisión"
#: Las reglas que son del oído; el resto se ve. Es el `tipo` del tiquet.
SUENA = ("sonoridad", "pico", "silencio")
_BLOQUE = re.compile(r"t:\s*([\d.]+)\s+TARGET:\S+ LUFS\s+M:\s*(-?[\d.]+)"
                     r".*?FTPK:((?:\s+-?(?:[\d.]+|inf))+)\s+dBFS")


@dataclass(frozen=True)
class Alerta:
    """Un fallo de emisión: qué regla, quién lo arregla y en qué segundo.

    `puerta=False` es un aviso: va al documento y no abre tiquet."""
    regla: str
    quien: str
    dice: str
    en: float | None = None
    puerta: bool = True


def integrada(ms) -> float | None:
    """LUFS integrados de bloques momentáneos (400 ms cada 100 ms), con las dos
    puertas de EBU R128: la absoluta de −70 y la relativa de −10 LU."""
    z = [10 ** (m / 10) for m in ms if m > -70]
    if not z:
        return None
    rel = 10 * math.log10(sum(z) / len(z)) - 10
    z = [x for x in z if 10 * math.log10(x) > rel]
    return round(10 * math.log10(sum(z) / len(z)), 1)


def _tramos(t, empieza, acaba, fin):
    """`[(desde, hasta)]` de un detector; el que no cierra, llega al final."""
    ini = [float(x) for x in re.findall(empieza + r":\s*(-?[\d.]+)", t)]
    fins = [float(x) for x in re.findall(acaba + r":\s*([\d.]+)", t)]
    return [(max(a, 0.0), fins[i] if i < len(fins) else fin) for i, a in enumerate(ini)]


def _escena_de(a, b, escenas):
    """La escena donde más cae el tramo; la cola tras la última, a la última."""
    return max(escenas, key=lambda e: min(b, e["hasta"]) - max(a, e["desde"]))["n"]


class Emision:
    """El parte de una pieza: el render y el spec, medidos por escena."""

    def __init__(self, n: int):
        self.n, self.slug = int(n), f"reel-{int(n):02d}"
        self.mp4 = next((m for m in (rutas.salida(c, f"reel-R{self.n}.mp4")
                                     for c in ("entrega", "reels"))
                         if os.path.exists(m)), None)
        try:
            spec = json.load(open("src/reels.json", encoding="utf-8"))
        except (OSError, ValueError):
            spec = []
        self.spec = next((x for x in spec if x.get("id") == f"Reel-R{self.n}"), {})
        self.escenas = fotogramas.escenas(self.slug)

    def huella(self) -> str:
        """Lo que se midió: el render, el spec, el plan y las varas."""
        plan = f"work/scenes/{self.slug}/plan-full.json"
        st = [(os.path.getsize(f), os.path.getmtime(f)) if f and os.path.exists(f)
              else None for f in (self.mp4, plan, "src/brand/lectura.json")]
        varas = (suena.OBJETIVO_LUFS, suena.PICO_MAX, suena.AIRE_MAX, IMAGEN, HOLGURA_LUFS,
                 SEPARA_LU)
        return hashlib.sha1(json.dumps([self.mp4, st, varas, self.spec], sort_keys=True,
                                       default=str).encode()).hexdigest()[:16]

    def formato(self) -> dict:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                            "-show_entries", "stream=width,height,r_frame_rate"
                            ":format=duration", "-of", "json", self.mp4],
                           capture_output=True, text=True)
        j = json.loads(r.stdout or "{}")
        s = (j.get("streams") or [{}])[0]
        a, _, b = (s.get("r_frame_rate") or "0/1").partition("/")
        return {"ancho": s.get("width"), "alto": s.get("height"),
                "fps": round(int(a) / int(b or 1), 2),
                "dura": round(float((j.get("format") or {}).get("duration") or 0), 2),
                "spec": round(round(float(self.spec.get("duracion") or 0) * FPS) / FPS, 2)}

    def _pieza(self, f) -> list:
        mal = []
        if (f["ancho"], f["alto"]) != (ANCHO, ALTO):
            mal.append(f"{f['ancho']}×{f['alto']} y no {ANCHO}×{ALTO}")
        if f["fps"] != FPS:
            mal.append(f"{f['fps']} fps y no {FPS}")
        # La entrega lleva las pausas del compas y la cola de la mezcla, igual
        # que en `version.cuadra_con_el_json` (C-597): sin ellas, reel-18 volvia
        # a `montado` con 53,80 s contra un spec de 53,13 y un render de 53,18.
        # Y con el mismo margen relativo que `version` (C-601): el codificador
        # rellena hasta el cuadro siguiente, y reel-18 salio 0,73 s sobre un
        # spec de 61,27 con 0,60 de cola: 0,03 por encima de 0,1 fijo.
        import cama
        import compas
        from dominio.version import MARGEN
        slug = str(self.spec.get("video") or "").replace(".mp4", "")
        debe = f["spec"] + compas.total(slug)
        if abs(f["dura"] - debe) > max(HOLGURA_DURA, debe * MARGEN) + cama.cola(slug):
            mal.append(f"dura {f['dura']:.2f} s y el spec {f['spec']:.2f} s")
        return [Alerta("formato", "montado", "; ".join(mal))] if mal else []

    def _lectura(self) -> list:
        lee = json.load(open("src/brand/lectura.json", encoding="utf-8"))
        return [c for c in Documento._capas(self.spec, lee) if c["capa"] in CAPAS.values()]

    def medir(self) -> dict:
        """`{escena: {"etapa", "desde", "hasta", "alertas", "medido"}}`; la 0 es la pieza."""
        escenas = self.escenas or [{"n": 0, "desde": 0.0, "hasta": 1e9, "etapa": None}]
        parte = {e["n"]: {"etapa": e["etapa"], "desde": round(e["desde"], 2),
                          "hasta": round(e["hasta"], 2), "alertas": [], "medido": {}}
                 for e in escenas}
        parte.setdefault(0, {"etapa": "pieza", "desde": 0.0, "hasta": None,
                             "alertas": [], "medido": {"render": self.mp4}})
        fallos = {k: [] for k in parte}
        for c in self._lectura():
            k = _escena_de(c["desde"], c["desde"] + 0.01, escenas)
            parte[k]["medido"].setdefault("lectura", []).append(
                {x: c[x] for x in ("capa", "kind", "desde", "dura", "pide")})
            if c["dura"] < c["pide"]:
                fallos[k].append(Alerta("lectura", "disenado", f"{c['capa']} «{c['kind']}»"
                                        f" dura {c['dura']} s y pide {c['pide']} s", c["desde"]))
        if self.mp4:
            self._render(parte, fallos, escenas)
        for k, d in parte.items():
            d["alertas"] = [asdict(a) for a in _juntas(fallos[k])]
        return parte

    def _render(self, parte, fallos, escenas):
        f = self.formato()
        t = suena.traza(self.mp4, vf=IMAGEN)
        global_ = {**suena.onda(t), **f}
        parte[0].update(hasta=f["dura"], medido={**parte[0]["medido"], **global_})
        fallos[0] += self._pieza(f)
        toda, pico = global_.get("sonoridad"), global_.get("pico_real")
        if toda is not None and abs(toda - suena.OBJETIVO_LUFS) > HOLGURA_LUFS:
            fallos[0].append(Alerta("sonoridad", "nivelado", f"{toda} LUFS integrados, fuera"
                                    f" de {suena.OBJETIVO_LUFS:.0f} ±{HOLGURA_LUFS}"))
        if pico is not None and pico > suena.PICO_MAX:
            fallos[0].append(Alerta("pico", "nivelado", f"pico {pico} dBTP, por encima"
                                    f" de {suena.PICO_MAX:.0f}"))
        bloques = [(float(a), float(m), max(float(x) for x in pk.split()))
                   for a, m, pk in _BLOQUE.findall(t)]
        for e in self.escenas:
            dentro = [b for b in bloques if b[0] - 0.4 >= e["desde"] - 0.05
                      and b[0] <= e["hasta"] + 0.05]
            lufs = integrada([m for _, m, _ in dentro])
            pico = max((p for *_, p in dentro), default=None)
            parte[e["n"]]["medido"].update(lufs=lufs, pico=pico)
            if lufs is not None and toda is not None and abs(lufs - toda) > SEPARA_LU:
                fallos[e["n"]].append(Alerta(
                    "nivel", "visto", f"{abs(lufs - toda):.1f} LU por"
                    f" {'debajo' if lufs < toda else 'encima'} de la pieza ({lufs} frente a"
                    f" {toda} LUFS)", round(e["desde"], 1), puerta=False))
        negro = _tramos(t, "black_start", "black_end", f["dura"])
        quieto = [q for q in _tramos(t, "freeze_start", "freeze_end", f["dura"])
                  if not any(a - 0.1 <= q[0] and q[1] <= b + 0.1 for a, b in negro)]
        for regla, tramos, tope, quien in (
                ("silencio", _tramos(t, "silence_start", "silence_end", f["dura"]),
                 suena.AIRE_MAX, "cosido"),
                ("negro", negro, QUIETO_MAX, "cortado"),
                ("congelado", quieto, QUIETO_MAX, "cortado")):
            for a, b in tramos:
                k = _escena_de(a, b, escenas)
                med = parte[k]["medido"]
                med[regla] = round(max(med.get(regla, 0), b - a), 2)
                if b - a > tope:
                    fallos[k].append(Alerta(regla, quien, f"{b - a:.1f} s de {regla} desde el"
                                            f" {a:.1f} (tope {tope} s)", round(a, 1)))


def _juntas(alertas) -> list:
    """Una alerta por regla y escena: un tiquet por cosa, no uno por medida."""
    por = {}
    for a in alertas:
        y = por.get(a.regla)
        por[a.regla] = a if y is None else Alerta(a.regla, y.quien, f"{y.dice}; {a.dice}",
                                                  y.en, y.puerta)
    return list(por.values())


def por_escena(n) -> dict:
    """El parte de la pieza `n` por escena, medido o leído si nada cambió."""
    em = Emision(n)
    f = os.path.join(rutas.TRABAJO, "emision", f"{em.slug}.json")
    huella = em.huella()
    try:
        guardado = json.load(open(f, encoding="utf-8"))
        if guardado.get("huella") == huella:
            return {int(k): v for k, v in guardado["escenas"].items()}
    except (OSError, ValueError, KeyError):
        pass
    parte = em.medir()
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        json.dump({"huella": huella, "escenas": parte}, fh, ensure_ascii=False, indent=1)
    return parte


def _clave(k, regla) -> str:
    return f"{MARCA} {'pieza' if not k else f'e{k}'}: {regla}"


def atender(n) -> tuple[list, str | None]:
    """Un tiquet por fallo a la fase que lo arregla; `(dicho, última línea)`.

    **Una vuelta por fallo, como la puerta del tiquet** (`puertas.por_atender`):
    abrir el tiquet ya lleva la pieza atrás y lo anota. Si al volver a medir el
    fallo sigue, ese paso ya tuvo su turno con el tiquet delante y repetirlo no
    lo arregla: se queda para Jaime, igual que el tope de `montar.sh`. El que ya
    pasa se cierra diciendo que se midió.
    """
    from dominio import segmento, ticket
    from dominio.fase import camino

    slug, parte = f"reel-{int(n):02d}", por_escena(n)
    fallos = [(k, d, a) for k, d in parte.items() for a in d["alertas"]
              if a.get("puerta", True)]
    suyos = [t for t in ticket.abiertos(slug) if (t.get("dijo") or "").startswith(MARCA)]
    claves = {_clave(k, a["regla"]) for k, _, a in fallos}
    dicho, vuelven, siguen = [], [], []
    for t in suyos:
        if t["dijo"].split(" — ")[0] not in claves:
            try:
                ticket.contestar(t["id"], "medido: ya pasa el control de emisión",
                                 estado="arreglado", medida="emision")
                dicho.append(f"  #{t['id']} cerrado, ya pasa: {t['dijo'][:70]}")
            except Exception as e:                 # noqa: BLE001 — se dice, no se calla
                dicho.append(f"  #{t['id']} sigue abierto: {e}")
    for k, d, a in fallos:
        clave = _clave(k, a["regla"])
        ya = next((t for t in suyos if t["dijo"].split(" — ")[0] == clave), None)
        # **Y si alguien lo encaminó a otra fase, manda esa** (C-602): reel-18,
        # 19-10, el #725 (firma de 0,76 s) se mandó a `revisado` para Jaime y
        # esto devolvía la pieza a `disenado` cada medio minuto, en bucle.
        if ya and (ya.get("devuelto") or (ya.get("vuelve_a") or "") != a["quien"]):
            siguen.append(f"#{ya['id']} {clave}")
            continue
        i = ticket.abrir(slug, f"{clave} — {a['dice']}", segundo=a["en"],
                         tipo="suena" if a["regla"] in SUENA else "objecion",
                         vuelve_a=a["quien"], cierra_con="emision",
                         etapa=d["etapa"] if k else "pieza")
        dicho.append(f"  #{i} {clave} -> {a['quien']}: {a['dice']}")
        vuelven.append(a["quien"])
    if vuelven and segmento.aprobada(slug):
        return dicho, f"emision: {slug} está APROBADA y no la reabre una medida; sube a Jaime"
    if vuelven:
        orden = [f["nombre"] for f in camino()]
        fase = min(vuelven, key=lambda x: orden.index(x) if x in orden else len(orden))
        return dicho, f"volver_a: {fase} — {len(vuelven)} fallo(s) de emisión en {slug}"
    if siguen:
        return dicho, (f"emision: {slug} ya volvió por esto y sigue igual; se queda"
                       f" aquí para Jaime: {', '.join(siguen)}")
    return dicho, None


def _linea(k, d) -> str:
    m = d["medido"]
    if not k:
        return (f"  pieza            {m.get('ancho')}×{m.get('alto')}  {m.get('fps')} fps"
                f"  {m.get('dura')} s (spec {m.get('spec')})  {m.get('sonoridad')} LUFS"
                f"  pico {m.get('pico_real')}") if m.get("ancho") else "  pieza            sin render"
    cifras = "  ".join(f"{x} {m[x]}" for x in ("lufs", "pico", "silencio", "negro",
                                               "congelado") if m.get(x) is not None)
    lee = " ".join(f"{c['kind'] or c['capa']} {c['dura']}/{c['pide']} s"
                   for c in m.get("lectura", []))
    return f"  e{k} (etapa {d['etapa']})".ljust(19) + \
        f"{d['desde']:>5}–{d['hasta']} s  {cifras}  {lee}".rstrip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("reels", nargs="+", type=int)
    ap.add_argument("--atender", action="store_true",
                    help="abre un tiquet por fallo; sin esto, sólo mira")
    a = ap.parse_args()
    mal, avisos, ultima = 0, 0, None
    for n in a.reels:
        parte = por_escena(n)
        print(f"\nreel-{n:02d}  {parte[0]['medido'].get('render') or 'sin render'}")
        for k in sorted(parte):
            print(_linea(k, parte[k]))
            for x in parte[k]["alertas"]:
                para = x.get("puerta", True)
                mal, avisos = mal + para, avisos + (not para)
                print(f"      {'·' if para else '~'} {x['regla']}: {x['dice']} ->"
                      f" {x['quien'] if para else 'aviso, sin tiquet'}")
        if a.atender:
            dicho, ultima = atender(n)
            for x in dicho:
                print(x)
    print((f"\n{mal} fallo(s) de emisión" if mal else "\npasa el control de emisión")
          + (f" · {avisos} aviso(s) para el visto" if avisos else ""))
    if ultima:
        print(ultima)
    sys.exit(1 if mal else 0)


if __name__ == "__main__":
    main()
