/**
 * Writer Config Module Index
 * Exports all configuration constants and utilities
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/config/index.ts loaded"
);

export {
  doctypeToDirectory,
  skipFiles,
  skipDirs,
  nonEditableFiles,
  doctypeDirs,
  systemDirs,
  isNonEditableFile,
  getDoctypePath,
  getDoctypeFromPath,
} from "./doctype-config.js";
