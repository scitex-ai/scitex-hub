/**
 * Monaco Editor Initialization Module
 * Handles LaTeX language registration, configuration, themes, and completion providers
 *
 * This is a thin wrapper that re-exports from the modular init/ directory
 */

// Import and re-export all functions from the orchestrator
export {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  setupMonacoTheme,
  createMonacoEditor,
  initializeMonacoEditor,
} from "./init/index";
