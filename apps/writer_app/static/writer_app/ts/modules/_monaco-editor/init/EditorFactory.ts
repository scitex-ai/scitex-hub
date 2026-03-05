/**
 * Editor Factory Module
 * Handles creation and configuration of Monaco editor instances
 * Uses shared MONACO_EDITOR_DEFAULTS as base, with Writer-specific overrides
 */

// @ts-ignore - Resolved by Vite alias @/ -> static/shared/ts/
import { MONACO_EDITOR_DEFAULTS } from "@/monaco/_MonacoDefaults";

// Shared theme utilities (same as Console uses)
import {
  getCurrentThemeMode,
  getThemeForMode,
} from "/static/shared/ts/monaco/MonacoTheme.js";


/**
 * Create Monaco editor instance with proper configuration
 */
export function createMonacoEditor(
  monaco: any,
  container: HTMLElement,
  initialValue: string,
  config: any,
): any {
  // Use shared theme detection (same as Console)
  const mode = getCurrentThemeMode();
  const initialTheme = getThemeForMode(mode);

  const editor = monaco.editor.create(container, {
    // Shared defaults (Console standard: JetBrains Mono, minimap, tabSize 4, etc.)
    ...MONACO_EDITOR_DEFAULTS,

    // Writer-specific overrides
    value: initialValue,
    language: "latex",
    theme: initialTheme,
    tabSize: 2, // LaTeX standard: 2 spaces
    wrappingIndent: "indent",

    // Bracket features useful for LaTeX
    "bracketPairColorization.enabled": true,
    matchBrackets: "always",
    autoClosingBrackets: "always",
    autoClosingQuotes: "always",

    // Visual guides for LaTeX structure
    "guides.bracketPairs": true,
    "guides.indentation": true,

    // Folding for LaTeX sections
    folding: true,
    foldingStrategy: "indentation",

    // Widget rendering (prevents clipping in Writer layout)
    fixedOverflowWidgets: true,
  });

  return editor;
}
