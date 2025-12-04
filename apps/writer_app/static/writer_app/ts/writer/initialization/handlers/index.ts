/**
 * FileTreeSetup Handlers Index
 * Re-exports all handler modules
 */

export {
  createFileSelectHandler,
  type FileSelectDependencies,
} from "./FileSelectHandler.ts";

export {
  setupDoctypeChangeWithTree,
  setupDoctypeChangeWithoutTree,
  type DoctypeChangeDependencies,
} from "./DoctypeChangeHandler.ts";

export {
  WRITER_ALLOWED_EXTENSIONS,
  DOCTYPE_FOLDER_MAP,
  getDoctypeFolder,
  createWriterTreeConfig,
} from "./TreeConfiguration.ts";

console.log("[DEBUG] FileTreeSetup handlers index loaded");
