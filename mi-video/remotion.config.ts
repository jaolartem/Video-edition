/**
 * Note: When using the Node.JS APIs, the config file
 * doesn't apply. Instead, pass options directly to the APIs.
 *
 * All configuration options: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";
import { enableTailwind } from '@remotion/tailwind-v4';
import { aplicar } from "./scripts/temporal.mjs";

/**
 * **El temporal, lo primero, y para cualquiera que renderice.**
 *
 * `entorno.sh` lo ponia desde fuera, asi que solo protegia a `montar.sh` y a
 * `render.sh`: un `npx remotion still` escrito a mano se llevaba su bundle
 * —`public/` entero, ~1,7 GB por llamada— al TEMP del sistema. El 6 de
 * septiembre eso dejo 119 directorios, 27 GB, y `C:` a 0 bytes dos veces; la
 * segunda se llevo por delante `bash.exe`.
 *
 * El CLI carga este fichero en **todos** sus subcomandos —`render`, `still`,
 * `bundle`, `studio`— antes de empaquetar nada, asi que es la puerta por donde
 * pasa todo lo que se lanza a mano. La ruta sale de `rutas.json` (`temporal`) y
 * de `VIDEO_TMP`; aqui no se escribe ninguna. De paso avisa del sitio libre,
 * que es lo que faltaba: un render no deberia poder llenar el disco del sistema
 * sin haberlo dicho antes.
 *
 * La API de Node **no pasa por aqui** —lo dice la nota de arriba—, asi que
 * `scripts/render.mjs` llama a lo mismo por su cuenta.
 */
aplicar();

Config.setRspack(true);
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.overrideBundlerConfig(enableTailwind);
