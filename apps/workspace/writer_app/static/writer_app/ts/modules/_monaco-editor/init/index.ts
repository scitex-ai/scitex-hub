/**
 * Monaco Editor Initialization Orchestrator
 * Uses scitex-ui for shared functionality, keeps citation providers local.
 */

// Shared from scitex-ui
import {
  registerLatexLanguage,
  registerLatexSnippetProvider,
  setupMonacoTheme,
} from "scitex-ui/ts/app/monaco-editor/index";

// Writer-specific (citation data needed)
import { registerCitationCompletionProvider } from "./CitationCompletion";
import { registerCitationHoverProvider } from "./CitationHover";

// Editor creation still uses scitex-ui defaults
import { createMonacoEditor } from "./EditorFactory";

// Re-export for consumers
export {
  registerLatexLanguage,
  registerLatexSnippetProvider as registerLatexCompletionProvider,
  registerCitationCompletionProvider,
  registerCitationHoverProvider,
  setupMonacoTheme,
  createMonacoEditor,
};

/**
 * Initialize all Monaco editor features
 */
export function initializeMonacoEditor(
  monaco: any,
  container: HTMLElement,
  initialValue: string,
  config: any,
): any {
  // Step 1: Register LaTeX language (from scitex-ui)
  registerLatexLanguage(monaco);

  // Step 2: Register completion providers
  registerLatexSnippetProvider(monaco);
  registerCitationCompletionProvider(monaco);

  // Step 3: Register hover providers
  registerCitationHoverProvider(monaco);

  // Step 4: Setup themes (from scitex-ui)
  setupMonacoTheme(monaco);

  // Step 5: Create editor instance
  const editor = createMonacoEditor(monaco, container, initialValue, config);

  return editor;
}
