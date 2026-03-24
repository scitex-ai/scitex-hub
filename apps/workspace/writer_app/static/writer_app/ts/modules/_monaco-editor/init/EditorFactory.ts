/**
 * Editor Factory — Writer-specific overrides
 * Uses scitex-ui defaults with LaTeX-specific configuration.
 */

import { MONACO_EDITOR_DEFAULTS } from "scitex-ui/ts/app/monaco-editor/_MonacoDefaults";
import {
  getCurrentThemeMode,
  getThemeForMode,
} from "scitex-ui/ts/app/monaco-editor/_MonacoTheme";

/**
 * Create Monaco editor instance with Writer-specific config
 */
export function createMonacoEditor(
  monaco: any,
  container: HTMLElement,
  initialValue: string,
  config: any,
): any {
  const mode = getCurrentThemeMode();
  const initialTheme = getThemeForMode(mode);

  return monaco.editor.create(container, {
    ...MONACO_EDITOR_DEFAULTS,
    value: initialValue,
    language: "latex",
    theme: initialTheme,
    tabSize: 2,
    wrappingIndent: "indent",
    "bracketPairColorization.enabled": true,
    matchBrackets: "always",
    autoClosingBrackets: "always",
    autoClosingQuotes: "always",
    "guides.bracketPairs": true,
    "guides.indentation": true,
    folding: true,
    foldingStrategy: "indentation",
    fixedOverflowWidgets: true,
  });
}
