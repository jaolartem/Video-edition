// Descarga whisper.cpp y el modelo de transcripción.
//
// Nota: @remotion/install-whisper-cpp falla al extraer en Windows si la ruta
// del proyecto contiene espacios (no entrecomilla el Expand-Archive de
// PowerShell). Como "Edicion de video" los tiene, extraemos a mano.
import path from "path";
import fs from "fs";
import { execFileSync } from "child_process";
import { downloadWhisperModel } from "@remotion/install-whisper-cpp";

const WHISPER_VERSION = "1.5.5";
// Multilingüe (incluye español). Para audio solo en inglés, "medium.en" es
// más rápido y preciso. Los modelos .en NO entienden español.
const MODEL = process.env.WHISPER_MODEL ?? "medium";

const to = path.join(process.cwd(), "whisper.cpp");
const zip = path.join(process.cwd(), "whisper-bin-x64.zip");

if (!fs.existsSync(path.join(to, "whisper-cli.exe"))) {
  const url = `https://github.com/ggerganov/whisper.cpp/releases/download/v${WHISPER_VERSION}/whisper-bin-x64.zip`;
  console.log("Descargando whisper.cpp…");
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Descarga falló: ${res.status}`);
  fs.writeFileSync(zip, Buffer.from(await res.arrayBuffer()));

  console.log("Extrayendo…");
  execFileSync("powershell", [
    "-NoProfile", "-Command",
    "Expand-Archive", "-Force", "-LiteralPath", zip, "-DestinationPath", to,
  ]);
  fs.unlinkSync(zip);
}
console.log("OK: whisper.cpp listo");

console.log(`Descargando modelo "${MODEL}" (puede tardar)…`);
await downloadWhisperModel({ model: MODEL, folder: to });
console.log("OK: modelo listo");
