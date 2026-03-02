/**
 * Monaco Editor Initialization Orchestrator
 * Coordinates all Monaco editor setup modules
 */

console.log("[DEBUG] monaco-editor/init/index.ts (orchestrator) loaded");

// Import all modules
import { registerLatexLanguage } from "./LanguageRegistration";
import { registerLatexCompletionProvider } from "./CompletionProvider";
import { registerCitationCompletionProvider } from "./CitationCompletion";
import { registerCitationHoverProvider } from "./CitationHover";
import { setupMonacoTheme } from "./EditorTheme";
import { createMonacoEditor } from "./EditorFactory";

// Re-export all functions
export {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  setupMonacoTheme,
  createMonacoEditor,
};

/**
 * Initialize all Monaco editor features
 * This is the main orchestrator function
 */
export function initializeMonacoEditor(
  monaco: any,
  container: HTMLElement,
  initialValue: string,
  config: any,
): any {
  console.log("[Monaco] Starting initialization...");

  // Step 1: Register LaTeX language
  registerLatexLanguage(monaco);

  // Step 2: Register completion providers
  registerLatexCompletionProvider(monaco);
  registerCitationCompletionProvider(monaco);

  // Step 3: Register hover providers
  registerCitationHoverProvider(monaco);

  // Step 4: Setup themes (both dark + light) and observer — identical to Console
  setupMonacoTheme(monaco);

  // Step 5: Create editor instance (uses shared defaults)
  const editor = createMonacoEditor(monaco, container, initialValue, config);

  console.log("[Monaco] Initialization complete");
  return editor;
}
