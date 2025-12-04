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
} from "./monaco-init.ts";

export {
  setupMonacoEditorListeners,
  setupCitationDropZone,
  setupCitationProtection,
  setupSuggestionWidgetObserver,
} from "./monaco-features.ts";

export { EditorHistory } from "./editor-history.ts";
export { CursorManager } from "./cursor-manager.ts";
export { EditorContent } from "./editor-content.ts";
export { EditorConfig } from "./editor-config.ts";
export { SpellCheckIntegration } from "./spell-check-integration.ts";
