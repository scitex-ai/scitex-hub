/**
 * Writer Modules Index
 * Centralized export of all writer-specific modules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/index.ts loaded",
);
export { WriterEditor, type EditorConfig } from "./editor.js";
export { EnhancedEditor, type MonacoEditorConfig } from "./monaco-editor.js";
export { SectionsManager, type Section } from "./sections.js";
export { CompilationManager, type CompilationOptions } from "./compilation.js";
export {
  FileTreeManager,
  type FileTreeNode,
  type FileTreeOptions,
} from "./file_tree/index.js";
export { LatexWrapper, type LatexWrapperOptions } from "./latex-wrapper.js";
export { PDFPreviewManager, type PDFPreviewOptions } from "./pdf-preview/index.js";
export { PanelResizer } from "./panel-resizer.js";
export {
  EditorControls,
  type EditorControlsOptions,
} from "./editor-controls/index.js";
export { CitationsPanel, type Citation } from "./citations-panel.js";
export { FiguresPanel, type Figure } from "./figures-panel.js";
export { TablesPanel, type Table } from "./tables-panel.js";
export { TablePreviewModalOrchestrator } from "./table-preview-modal.js";
export {
  StatusLampManager,
  statusLamp,
  type CompileStatus,
} from "./status-lamp.js";
export {
  CompilationSettingsManager,
  compilationSettings,
  type CompilationSettings,
} from "./compilation-settings.js";
export {
  StatePersistenceManager,
  statePersistence,
} from "./state-persistence.js";
export {
  PDFScrollZoomHandler,
  type PDFScrollZoomOptions,
  type PDFColorMode,
  type PDFColorTheme,
} from "./pdf-scroll-zoom.js";
export { GitHistoryManager } from "./git-history.js";

// New modular exports
export {
  setupDragAndDrop,
  setupPDFScrollPriority,
} from "./drag-drop.js";
export {
  getPageTheme,
  filterThemeOptions,
  applyCodeEditorTheme,
  setupThemeListener,
  setupKeybindingListener,
} from "./theme-manager.js";
export {
  scheduleSave,
  scheduleAutoCompile,
  saveSections,
  setLoadingContent,
  getLoadingContent,
} from "./auto-save.js";
export {
  showCommitModal,
  closeCommitModal,
  handleGitCommit,
  showCompilationOptionsModal,
} from "./modals.js";
export {
  setupWorkspaceInitialization,
  waitForMonaco,
} from "./workspace-init.js";
