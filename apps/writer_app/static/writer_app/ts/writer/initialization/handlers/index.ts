/**
 * FileTreeSetup Handlers Index
 * Re-exports all handler modules
 */

export {
  createFileSelectHandler,
  type FileSelectDependencies,
} from "./FileSelectHandler";

export {
  setupDoctypeChangeWithTree,
  setupDoctypeChangeWithoutTree,
  type DoctypeChangeDependencies,
} from "./DoctypeChangeHandler";

export {
  WRITER_ALLOWED_EXTENSIONS,
  DOCTYPE_FOLDER_MAP,
  getDoctypeFolder,
  createWriterTreeConfig,
} from "./TreeConfiguration";

console.log("[DEBUG] FileTreeSetup handlers index loaded");
