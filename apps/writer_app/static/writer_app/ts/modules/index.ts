/**
 * Writer Modules Index
 * Centralized export of all writer-specific modules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/index.ts loaded",
);
export { WriterEditor, type EditorConfig } from "./editor.ts";
export { EnhancedEditor, type MonacoEditorConfig } from "./monaco-editor.ts";
export { SectionsManager, type Section } from "./sections.ts";
export { CompilationManager, type CompilationOptions } from "./compilation.ts";
export {
  FileTreeManager,
  type FileTreeNode,
  type FileTreeOptions,
} from "./file_tree/index.ts";
export { LatexWrapper, type LatexWrapperOptions } from "./latex-wrapper.ts";
export { PDFPreviewManager, type PDFPreviewOptions } from "./pdf-preview/index.ts";
export { PanelResizer } from "./panel-resizer.ts";
export {
  EditorControls,
  type EditorControlsOptions,
} from "./editor-controls/index.ts";
export { CitationsPanel, type Citation } from "./citations-panel.ts";
export { FiguresPanel, type Figure } from "./figures-panel.ts";
export { TablesPanel, type Table } from "./tables-panel.ts";
export { TablePreviewModalOrchestrator } from "./table-preview-modal.ts";
export {
  StatusLampManager,
  statusLamp,
  type CompileStatus,
} from "./status-lamp.ts";
export {
  CompilationSettingsManager,
  compilationSettings,
  type CompilationSettings,
} from "./compilation-settings.ts";
export {
  StatePersistenceManager,
  statePersistence,
} from "./state-persistence.ts";
export {
  PDFScrollZoomHandler,
  type PDFScrollZoomOptions,
  type PDFColorMode,
  type PDFColorTheme,
} from "./pdf-scroll-zoom.ts";
export { GitHistoryManager } from "./git-history.ts";

// New modular exports
export {
  setupDragAndDrop,
  setupPDFScrollPriority,
} from "./drag-drop.ts";
export {
  getPageTheme,
  filterThemeOptions,
  applyCodeEditorTheme,
  setupThemeListener,
  setupKeybindingListener,
} from "./theme-manager.ts";
export {
  scheduleSave,
  scheduleAutoCompile,
  saveSections,
  setLoadingContent,
  getLoadingContent,
} from "./auto-save.ts";
export {
  showCommitModal,
  closeCommitModal,
  handleGitCommit,
  showCompilationOptionsModal,
} from "./modals.ts";
export {
  setupWorkspaceInitialization,
  waitForMonaco,
} from "./workspace-init.ts";
