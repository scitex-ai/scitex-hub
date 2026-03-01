/**
 * Writer Modules Index
 * Centralized export of all writer-specific modules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/index.ts loaded",
);
export { WriterEditor, type EditorConfig } from "./editor";
export { EnhancedEditor, type MonacoEditorConfig } from "./monaco-editor";
export { SectionsManager, type Section } from "./sections";
export { CompilationManager, type CompilationOptions } from "./compilation";
export {
  FileTreeManager,
  type FileTreeNode,
  type FileTreeOptions,
} from "./file_tree/index";
export { LatexWrapper, type LatexWrapperOptions } from "./latex-wrapper";
export { PDFPreviewManager, type PDFPreviewOptions } from "./pdf-preview/index";
// PanelResizer removed — now uses shared HorizontalResizer
export {
  EditorControls,
  type EditorControlsOptions,
} from "./editor-controls/index";
export { CitationsPanel, type Citation } from "./citations-panel";
export { FiguresPanel, type Figure } from "./figures-panel";
export { TablesPanel, type Table } from "./tables-panel";
export { TablePreviewModalOrchestrator } from "./table-preview-modal";
export {
  StatusLampManager,
  statusLamp,
  type CompileStatus,
} from "./status-lamp";
export {
  CompilationSettingsManager,
  compilationSettings,
  type CompilationSettings,
} from "./compilation-settings";
export { StatePersistenceManager, statePersistence } from "./state-persistence";
export {
  PDFScrollZoomHandler,
  type PDFScrollZoomOptions,
  type PDFColorMode,
  type PDFColorTheme,
} from "./pdf-scroll-zoom";
export { GitHistoryManager } from "./git-history";

// New modular exports
export { setupDragAndDrop, setupPDFScrollPriority } from "./drag-drop";
export {
  getPageTheme,
  filterThemeOptions,
  applyCodeEditorTheme,
  setupThemeListener,
  setupKeybindingListener,
} from "./theme-manager";
export {
  scheduleSave,
  scheduleAutoCompile,
  saveSections,
  setLoadingContent,
  getLoadingContent,
} from "./auto-save";
export {
  showCommitModal,
  closeCommitModal,
  handleGitCommit,
  showCompilationOptionsModal,
} from "./modals";
export { setupWorkspaceInitialization, waitForMonaco } from "./workspace-init";
