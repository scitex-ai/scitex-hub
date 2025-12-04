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
} from "./monaco-init.js";

export {
  setupMonacoEditorListeners,
  setupCitationDropZone,
  setupCitationProtection,
  setupSuggestionWidgetObserver,
} from "./monaco-features.js";

export { EditorHistory } from "./editor-history.js";
export { CursorManager } from "./cursor-manager.js";
export { EditorContent } from "./editor-content.js";
export { EditorConfig } from "./editor-config.js";
export { SpellCheckIntegration } from "./spell-check-integration.js";
