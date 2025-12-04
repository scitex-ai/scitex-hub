/**
 * FileTreeSetup Handlers Index
 * Re-exports all handler modules
 */

export {
  createFileSelectHandler,
  type FileSelectDependencies,
} from "./FileSelectHandler.js";

export {
  setupDoctypeChangeWithTree,
  setupDoctypeChangeWithoutTree,
  type DoctypeChangeDependencies,
} from "./DoctypeChangeHandler.js";

export {
  WRITER_ALLOWED_EXTENSIONS,
  DOCTYPE_FOLDER_MAP,
  getDoctypeFolder,
  createWriterTreeConfig,
} from "./TreeConfiguration.js";

console.log("[DEBUG] FileTreeSetup handlers index loaded");
