/**
 * Writer Modules Index
 * Centralized export of all writer-specific modules
 */

export { WriterEditor, type EditorConfig } from "./_editor";
export { EnhancedEditor, type MonacoEditorConfig } from "./monaco-editor";
export { SectionsManager, type Section } from "./_sections";
export { CompilationManager, type CompilationOptions } from "./_compilation";
export {
  FileTreeManager,
  type FileTreeNode,
  type FileTreeOptions,
} from "./_file_tree/index";
export { LatexWrapper, type LatexWrapperOptions } from "./_latex-wrapper";
export { PDFPreviewManager, type PDFPreviewOptions } from "./pdf-preview/index";
// PanelResizer removed — now uses shared HorizontalResizer
export {
  EditorControls,
  type EditorControlsOptions,
} from "./_editor-controls/index";
export { CitationsPanel, type Citation } from "./citations-panel";
export { FiguresPanel, type Figure } from "./_figures-panel";
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
export {
  StatePersistenceManager,
  statePersistence,
} from "./_state-persistence";
export {
  PDFScrollZoomHandler,
  type PDFScrollZoomOptions,
  type PDFColorMode,
  type PDFColorTheme,
} from "./pdf-scroll-zoom";
export { GitHistoryManager } from "./_git-history";

// New modular exports
export { setupDragAndDrop, setupPDFScrollPriority } from "./_drag-drop";
export {
  getPageTheme,
  filterThemeOptions,
  applyCodeEditorTheme,
  setupThemeListener,
  setupKeybindingListener,
} from "./_theme-manager";
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
} from "./_modals";
export { setupWorkspaceInitialization, waitForMonaco } from "./workspace-init";
