"""Las instrucciones de Jaime: se registran, y se cierran con su aguja.

Regla del proyecto, y es la misma de `docs/correcciones.md`: una instrucción
contada no es una instrucción hecha. La tabla `regla` de `ads/decisiones.db` ya
guardaba las veintisiete anteriores —*«el gancho es uno»*, *«máximo 300 líneas
por script»*— con la columna que decide si está viva: `donde`, el fichero donde
el mecanismo la cumple.

Lo que faltaba era **la puerta**. Las filas estaban puestas a mano, así que
`automatizada = 1` significaba «alguien lo escribió», no «el código lo hace».
Aquí cerrar exige la aguja y **se comprueba que sigue en su sitio**: un trozo de
código literal que no se puede escribir por casualidad. Si la aguja no está, la
instrucción no se cierra y se dice por qué.

Es idempotente a propósito: las instrucciones se declaran abajo y `main()` las
sincroniza. No hay SQL suelto y volver a correrlo no duplica nada.

    python scripts/instruccion.py            # las declaradas, con su estado
    python scripts/instruccion.py --cerrar   # las escribe en la base
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime
import os
import sqlite3

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(RAIZ, "ads", "decisiones.db")


@dataclasses.dataclass(frozen=True)
class Aguja:
    """La línea literal que hace el trabajo. Un fichero se reescribe; ella no."""

    fichero: str
    linea: str

    def esta(self) -> bool:
        try:
            with open(os.path.join(RAIZ, self.fichero), encoding="utf-8") as f:
                return self.linea in f.read()
        except OSError:
            return False

    def __str__(self):
        return f"{self.fichero} :: {self.linea}"


@dataclasses.dataclass(frozen=True)
class Instruccion:
    """Una instrucción de Jaime, el paso al que le toca y dónde queda cumplida."""

    codigo: str
    paso: str
    clase: str
    enunciado: str
    agujas: tuple[Aguja, ...]

    def texto(self) -> str:
        return f"{self.codigo} ({self.paso}) · {self.enunciado}"

    def rotas(self) -> list[Aguja]:
        return [a for a in self.agujas if not a.esta()]


INSTRUCCIONES = (
    Instruccion(
        codigo="T-01",
        paso="disenar",
        clase="montaje",
        enunciado=(
            "Si en el audio se esta leyendo, ese tramo va cubierto con tablero:"
            " la cara no aparece en camara limpia mientras se lee. El disparador"
            " es el AUDIO —la secuencia literal contra el libreto— no el frame,"
            " para que el compositor identifique los tramos sin juzgar la mirada"
            " plano a plano. El unico que no se cubre es el gancho: ahi se elige"
            " otra apertura."
        ),
        agujas=(
            Aguja("scripts/trato.py", "va cubierto con"),
            Aguja("scripts/lectura.mjs", "export const faltasDeCobertura"),
            Aguja("scripts/caminos.mjs", "faltasDeCobertura(ctx.det.trato, ctx.det)"),
            Aguja("scripts/describir.mjs", "esta etapa va CUBIERTA con tablero"),
        ),
    ),
    Instruccion(
        codigo="T-02",
        paso="disenar",
        clase="subtitulo",
        enunciado=(
            "Durante los tableros el subtitulo pasa a estilo tradicional"
            " discreto: cuerpo pequeno, sin caja ni contorno, apoyado en el borde"
            " inferior de la ZONA SEGURA y no del cuadro. El tablero es la capa"
            " de informacion y el subtitulo solo acompana. Por implicacion,"
            " ningun tablero baja hasta esa franja — del 54,6% al 65% de la"
            " altura, declarada en src/brand/franja.json y en ningun otro sitio."
        ),
        agujas=(
            Aguja("src/brand/franja.json", '"suelo": 0.65'),
            Aguja("src/components/CaptionDiscreta.tsx", "bottom: franja.desdeAbajo"),
            Aguja("src/components/ZonaTablero.tsx", "bottom: franja.reserva"),
            Aguja("src/Ad.tsx", "bajoTablero"),
        ),
    ),
    Instruccion(
        codigo="T-03",
        paso="disenar",
        clase="tablero",
        enunciado=(
            "El pie de fuente va FUERA de la zona segura, pegado por debajo de"
            " su suelo (65% de la altura, 1248 px) y no al fondo del cuadro, que"
            " es donde la interfaz de Meta lo tapa. UNA linea, JetBrains Mono,"
            " azul secundario sobre banda propia, y redactada en AFIRMATIVO"
            " -«basado en X datos bajo X condiciones»- con la cifra y el tramo"
            " exactos. Jaime: «no me interesa que lo lean, solo que sepan que"
            " existe», y «ahora que si lo leen, pues que este bien leido»: no se"
            " abrevia hasta que deje de decir nada, lo que no cabe sale como"
            " falta. Y un ACENTO por tablero: si hay tres cosas en oro, dos"
            " sobran."
        ),
        agujas=(
            Aguja("src/brand/pie.json", '"max_caracteres": 97'),
            Aguja("src/brand/franja.ts",
                  "sueloPx: Math.round(SUELO * layout.height),"),
            Aguja("src/components/PieTablero.tsx",
                  "top: franja.sueloPx + PIE.hueco,"),
            Aguja("src/components/Tablero.tsx", "<PieTablero linea="),
            Aguja("scripts/reels/cifras.mjs", 'const DESTINO = "pie";'),
            Aguja("src/components/Remate.tsx",
                  "acento ? color.gold : color.lightNeutral"),
        ),
    ),
    Instruccion(
        codigo="T-04",
        paso="disenar",
        clase="subtitulo",
        enunciado=(
            "El cuadro negro del subtitulo deja de ser el tratamiento UNICO:"
            " «los CC estan feos; pueden ser a negativo solamente para variar el"
            " cuadro negro, unos CC que se compongan mejor respecto a la"
            " composicion», «hay varios que quedarian bien sin el cuadro, otras"
            " a las que le queda bien y otras a las que le quedaria mejor"
            " negativo», y el limite: «no te cierres a un solo sistema, pero"
            " debe ser coherente con el resto del video». Cual toca lo decide lo"
            " que hay DETRAS en esa escena y se MIDE, no se opina: la luz, el"
            " grano y el movimiento de la banda que el cc ocupa. Y el negativo"
            " solo entra donde de verdad da contraste — `difference` con blanco"
            " devuelve 1-fondo, asi que muere en el gris medio. La coherencia"
            " manda sobre la variedad: el tratamiento es de la escena, con"
            " histeresis, y una escena corta hereda."
        ),
        agujas=(
            Aguja("src/brand/cc.json", '"contraste": 0.35'),
            Aguja("src/brand/cc.ts", 'mixBlendMode: "difference"'),
            Aguja("scripts/dominio/trasfondo.py",
                  "np.abs(1.0 - 2.0 * porFrame).mean()"),
            Aguja("scripts/reels/cc.mjs",
                  "export const trato = (m, anterior, oro = false) => {"),
            Aguja("src/components/captionBand/Plana.tsx", "...pintaDelCc(trato),"),
            Aguja("scripts/reels-spec.mjs",
                  "pieza.captions = trataElCc(pieza, slug, bajarEnElGancho("),
        ),
    ),
    Instruccion(
        codigo="T-05",
        paso="seleccionar",
        clase="montaje",
        enunciado=(
            "Si salgo leyendo hay que buscar otras tomas (Jaime, 10-9-2026). En"
            " las piezas que lo declaran —lectura: otra_toma— una toma que lee"
            " su parrafo no compite; si una etapa solo tiene tomas leidas,"
            " vuelve la leida y se pide la grabacion que falta, porque todo esta"
            " grabado sin leer. Lo leido no se tapa con tablero. Sustituye a"
            " T-01 en esas piezas; las siete de venta siguen con T-01."
        ),
        agujas=(
            Aguja("scripts/dominio/seleccion/corrida.py",
                  'prohibidas = (self.leidas() if self.frame.get("lectura") == "otra_toma"'),
            Aguja("scripts/dominio/seleccion/corrida.py", "def pide_otra_toma("),
            Aguja("scripts/fijar.py",
                  "_fuera = _leidos_declarados(slug, por_beat, transcribir)"),
            Aguja("scripts/seleccionar.py", "pide_otra_toma(c.slug, b, toma, lect)"),
        ),
    ),
)


def _con():
    return sqlite3.connect(BASE)


def cerrar(i: Instruccion, con=None) -> list[Aguja]:
    """Cierra una instrucción: comprueba la aguja y la deja viva en la base.

    Devuelve las agujas rotas. Si hay alguna **no escribe nada**: cerrar una
    instrucción cuyo mecanismo no existe es exactamente el fallo que este
    fichero viene a impedir.
    """
    rotas = i.rotas()
    if rotas:
        return rotas
    propia = con is None
    con = con or _con()
    hoy = datetime.date.today().isoformat()
    donde = " · ".join(str(a) for a in i.agujas)
    fila = con.execute("select id from regla where enunciado = ?",
                       (i.texto(),)).fetchone()
    if fila:
        con.execute("update regla set automatizada = 1, donde = ?, clase = ?,"
                    " fecha = ? where id = ?", (donde, i.clase, hoy, fila[0]))
    else:
        con.execute("insert into regla (clase, enunciado, automatizada, donde,"
                    " fecha) values (?, ?, 1, ?, ?)",
                    (i.clase, i.texto(), donde, hoy))
    con.commit()
    if propia:
        con.close()
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cerrar", action="store_true",
                    help="escribe en la base las que tienen su aguja en pie")
    a = ap.parse_args()
    malas = 0
    con = _con() if a.cerrar else None
    for i in INSTRUCCIONES:
        rotas = cerrar(i, con) if a.cerrar else i.rotas()
        estado = "CERRADA" if not rotas else f"{len(rotas)} aguja(s) rotas"
        print(f"  {i.codigo} ({i.paso}) · {i.clase:<10} {estado}")
        for r in rotas:
            print(f"      falta  {r}")
        malas += len(rotas)
    if con:
        con.close()
    print(f"\ninstruccion: {len(INSTRUCCIONES)} declaradas · "
          f"{'todas con su aguja en pie' if not malas else f'{malas} agujas rotas'}")
    if malas:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
