/**
 * Writer Tree Module Index
 * Exports file tree integration components
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/writer/tree/index.ts loaded"
);

export {
  getCurrentDoctype,
  setCurrentDoctype,
  getCurrentSectionIndex,
  setCurrentSectionIndex,
  filterFileTreeDOM,
  syncAllFromPath,
  handleDoctypeChange,
  handleFileSelect,
  setupTreeFilterObserver,
} from "./file-tree-integration.js";
