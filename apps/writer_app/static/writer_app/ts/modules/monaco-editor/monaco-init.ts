/**
 * Monaco Editor Initialization Module
 * Handles LaTeX language registration, configuration, themes, and completion providers
 *
 * This is a thin wrapper that re-exports from the modular init/ directory
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/monaco-editor/monaco-init.ts loaded",
);

// Import and re-export all functions from the orchestrator
export {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  defineScitexTheme,
  setupThemeObserver,
  createMonacoEditor,
  initializeMonacoEditor,
} from "./init/index.js";
