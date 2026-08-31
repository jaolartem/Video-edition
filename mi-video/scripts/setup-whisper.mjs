// Descarga el whisper de CPU y el modelo de transcripción.
//
// Nota: @remotion/install-whisper-cpp falla al extraer en Windows si la ruta
// del proyecto contiene espacios (no entrecomilla el Expand-Archive de
// PowerShell). Como "Edicion de video" los tiene, extraemos a mano.
//
// **Y esto instala el camino LENTO, a propósito.** El que corre de verdad es
// `whisper.cpp/whisper-cli.exe`, la build con Vulkan que va por la tarjeta
// —1,84× medido, mismo texto— y que no sale de aquí porque no existe release
// pública con Vulkan para Windows: se compila, y la receta está en
// `docs/entorno.md`. Esto de aquí es la caída: la release de CPU con sus
// backends por microarquitectura, que sigue siendo la mejor CPU disponible.
//
// Por eso va a `whisper.cpp/cpu/` y no a `whisper.cpp/`. No es orden: la build
// de Vulkan es estática pero **carga cualquier `ggml-*.dll` que encuentre a su
// lado**, y las de la release están compiladas con MSVC. Juntarlas la mata con
// un `GGML_ASSERT(prev != ggml_uncaught_exception) failed` que no menciona
// ninguna DLL y que **sale con código 0**. Es el fallo de C-48 otra vez: rápido
// de provocar, lentísimo de diagnosticar.
import path from "path";
import fs from "fs";
import { execFileSync } from "child_process";
import { downloadWhisperModel } from "@remotion/install-whisper-cpp";

const WHISPER_VERSION = "1.5.5";
// Multilingüe (incluye español). Para audio solo en inglés, "medium.en" es
// más rápido y preciso. Los modelos .en NO entienden español.
const MODEL = process.env.WHISPER_MODEL ?? "medium";

// Los modelos viven arriba: los comparten las dos builds y pesan 2 GB.
const to = path.join(process.cwd(), "whisper.cpp");
const cpu = path.join(to, "cpu");
const zip = path.join(process.cwd(), "whisper-bin-x64.zip");

if (!fs.existsSync(path.join(cpu, "whisper-cli.exe"))) {
  const url = `https://github.com/ggerganov/whisper.cpp/releases/download/v${WHISPER_VERSION}/whisper-bin-x64.zip`;
  console.log("Descargando whisper.cpp (CPU)…");
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Descarga falló: ${res.status}`);
  fs.writeFileSync(zip, Buffer.from(await res.arrayBuffer()));

  console.log("Extrayendo…");
  fs.mkdirSync(cpu, { recursive: true });
  execFileSync("powershell", [
    "-NoProfile", "-Command",
    "Expand-Archive", "-Force", "-LiteralPath", zip, "-DestinationPath", cpu,
  ]);
  fs.unlinkSync(zip);

  // `main.exe` ya no es whisper: es un stub que avisa de estar deprecado y
  // **sale con éxito sin transcribir** (C-56). Se borra al instalar para que no
  // pueda volver a llamarse por costumbre.
  for (const stub of ["main.exe", "bench.exe"]) {
    const p = path.join(cpu, stub);
    if (fs.existsSync(p)) fs.rmSync(p);
  }
}
console.log("OK: whisper de CPU listo en whisper.cpp/cpu");

if (!fs.existsSync(path.join(to, "whisper-cli.exe"))) {
  console.log(
    "AVISO: no hay build de Vulkan en whisper.cpp/. Todo irá por CPU, que es"
    + " 1,84× más lento. La receta para compilarla está en docs/entorno.md.",
  );
}

console.log(`Descargando modelo "${MODEL}" (puede tardar)…`);
await downloadWhisperModel({ model: MODEL, folder: to });
console.log("OK: modelo listo");
