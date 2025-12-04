/**
 * Monaco Editor Initialization Orchestrator
 * Coordinates all Monaco editor setup modules
 */

console.log("[DEBUG] monaco-editor/init/index.ts (orchestrator) loaded");

// Import all modules
import { registerLatexLanguage } from "./LanguageRegistration.js";
import { registerLatexCompletionProvider } from "./CompletionProvider.js";
import { registerCitationCompletionProvider } from "./CitationCompletion.js";
import { registerCitationHoverProvider } from "./CitationHover.js";
import { defineScitexTheme, defineScitexLightTheme, setupThemeObserver } from "./EditorTheme.js";
import { createMonacoEditor } from "./EditorFactory.js";

// Re-export all functions for backward compatibility
export {
  registerLatexLanguage,
  registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  defineScitexTheme,
  defineScitexLightTheme,
  setupThemeObserver,
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
  config: any
): any {
  console.log("[Monaco] Starting initialization...");

  // Step 1: Register LaTeX language
  registerLatexLanguage(monaco);

  // Step 2: Register completion providers
  registerLatexCompletionProvider(monaco);
  registerCitationCompletionProvider(monaco);

  // Step 3: Register hover providers
  registerCitationHoverProvider(monaco);

  // Step 4: Define custom themes
  defineScitexTheme(monaco);
  defineScitexLightTheme(monaco);

  // Step 5: Setup theme observer for auto-switching
  setupThemeObserver(monaco);

  // Step 6: Create editor instance
  const editor = createMonacoEditor(monaco, container, initialValue, config);

  console.log("[Monaco] Initialization complete");
  return editor;
}
