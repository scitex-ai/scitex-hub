/**
 * Monaco Editor Modules Index
 * Centralized export of all Monaco editor modules
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/index.ts loaded",
);

export {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  defineScitexTheme,
  createMonacoEditor,
  setupThemeObserver,
} from "./monaco-init";

export {
  setupMonacoEditorListeners,
  setupCitationDropZone,
  setupCitationProtection,
  setupSuggestionWidgetObserver,
} from "./monaco-features";

export { EditorHistory } from "./editor-history";
export { CursorManager } from "./cursor-manager";
export { EditorContent } from "./editor-content";
export { EditorConfig } from "./editor-config";
export { SpellCheckIntegration } from "./spell-check-integration";
