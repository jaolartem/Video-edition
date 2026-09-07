/**
 * **El informe por pieza: lo que hay que mirar, y no para nada.**
 *
 * Salió de `puerta.mjs` porque son dos trabajos y el fichero llegó al techo de
 * `scripts/tamano.py` con los dos dentro. La separación ya estaba escrita en su
 * primera línea —*«lo demás que este fichero imprime no para nada: es el
 * informe por pieza»*— y por eso el corte no es por líneas: **lo que para** se
 * queda allí, **lo que cuenta** viene aquí.
 *
 * Nada de esto bloquea una entrega. Existe para que un defecto no haya que
 * buscarlo: la línea de cada pieza, el encaje de cada segmento contra su etapa,
 * las escenas a plano seco y los beats sin tratamiento.
 */
import { FPS } from "./reloj.mjs";
import { DICE } from "./texto.mjs";
import { marcoDe } from "./material.mjs";
import { sinTrato } from "./escenas.mjs";

/**
 * Suelo de encaje de un segmento en su etapa: por debajo, lo grabado no cabe
 * dentro de lo que el guion espera ahí. Es el mismo umbral con que
 * `seleccionar.py` admite una candidata, y por eso significa lo mismo en los dos
 * sitios.
 */
const ENCAJE = 0.14;
/**
 * Y cuánto de lo ALCANZABLE hay que cubrir. Es el mismo criterio relativo con
 * que `beats.py` deja competir a una candidata: lo que importa no es el valor
 * absoluto, es la distancia al mejor posible.
 */
const RELATIVO = 0.5;

/**
 * **Un segmento encaja si hace su trabajo, no si repite el libreto.**
 *
 * La cobertura sola mide literalidad: comparada contra un párrafo largo, decir
 * sólo lo esencial puntúa bajo aunque la etapa quede cumplida. En el reel 2 la
 * etapa 2 dice «por cada 100 dólares se quedan con 67» —que es exactamente lo
 * que el libreto pide ahí— y sacaba 0,10 porque el párrafo además habla de la
 * mansión, el yate y Muskoka.
 *
 * Así que se mira contra **lo alcanzable en esa etapa** (`cubre_max`), y además
 * se acepta el segmento que trae el dato que la etapa declara.
 */
const encaja = (u) =>
  u.dice ||
  (u.cobertura ?? 0) >= Math.max(ENCAJE, RELATIVO * (u.cubre_max ?? 0));

/** La línea de cada pieza y lo que hay que mirar en ella. No para nada. */
export function informe(r, m) {
  console.log(
    `${r.id}  ${r.duracion.toFixed(1)}s  ${m.visibles}/${r.captions.length} cc (${r.compuestos} compuestos)  mudo max ${(m.dur / FPS).toFixed(1)}s  ` +
    `rotulo entra en ${(r.entra / FPS).toFixed(1)}s  ` +
    `${r.paneles.length} panel(es) · ${r.boards.length} tablero(s)${r.boards.length ? " en " + r.boards.map((b) => (b.at / FPS).toFixed(1) + "s").join(",") : ""}  ` +
    `CTA ${r.cta ? "en " + r.cta.at.toFixed(1) + "s" : "NO HAY (falta el copy del cierre)"}`,
  );
  /**
   * **La cifra es secundaria respecto al segmento.** Jaime: *«no creo que las
   * cifras sean el parámetro para medir; lo que tenemos que encontrar son los
   * segmentos específicos de lo grabado que caben dentro de los segmentos
   * esperados por el guion. Acá hay falsos positivos»*.
   *
   * Medido: «estructura. 30.000 dolares no de ventas de estructura» **contiene
   * el 30** y es un tropiezo de cuatro segundos con cobertura -0,07. Así que la
   * cifra es aviso y la puerta baja a donde está la unidad de análisis.
   */
  const exige = marcoDe(`reel-0${r.id.slice(-1)}`)?.debe_decir ?? [];
  const dicho = DICE(r.captions.map((c) => c.text).join(" "));
  // Mismo criterio que en `beats.py`: el termino admite alternativas con `|`,
  // porque lo que se comprueba es la intencion comunicativa y no la letra.
  const faltan = exige.filter(
    (t) => !String(t).split("|").some((x) => dicho.includes(DICE(x))),
  );
  if (faltan.length) {
    console.log(
      `    aviso: no suena ${faltan.map((x) => `«${x}»`).join(", ")}.` +
      ` Es un dato declarado, no el criterio: lo que decide es si cada segmento` +
      ` encaja en su etapa.`,
    );
  }
  const det = r.edl?.detalle ?? [];
  if (det.length) {
    const flojas = det.filter((u) => !encaja(u));
    /**
     * **Parecerse poco al libreto no es un defecto.** Jaime separó tres cosas:
     * *«una cosa el libreto o el mensaje esperado, otra el mensaje entregado,
     * otra la intención comunicativa; se respeta la última»*. La cobertura mide
     * el parecido con el mensaje ESPERADO, que es la preferencia, no el
     * criterio. Llamarlo «flojo» hacía perseguir el parecido y no el sentido.
     */
    console.log(
      `    encaje por segmento: ` +
      det.map((u) => `${u.beat}:${(u.cobertura ?? 0).toFixed(2)}`).join(" ") +
      (flojas.length
        ? `  · mas lejos del libreto: ${flojas.map((u) => u.beat).join(",")}`
        + ` (no es defecto: lo que decide es la integridad)`
        : ""),
    );
  }
  const secas = (r.escenas ?? []).filter((e) => e.trato === "—");
  if (secas.length) {
    console.log(
      `    escenas a plano seco: ${secas.map((e) => `${e.n} (${(e.a / FPS).toFixed(1)}-${(e.b / FPS).toFixed(1)}s)`).join(", ")}` +
      ` — cada escena tiene que llevar tablero, animacion o texto animado.`,
    );
  }
  const pelados = sinTrato(r);
  if (pelados.length) {
    console.log(
      `    beats sin tratamiento: ${pelados.join(", ")} - ni tablero, ni panel, ` +
      `ni idea fuerza, ni marca. Plano seco todo el beat.`,
    );
  }
}
