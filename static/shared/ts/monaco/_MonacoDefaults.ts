/**
 * Shared Monaco Editor Defaults
 * Single source of truth for editor options across all SciTeX modules
 * Based on Console's editor configuration (the standard)
 */

/**
 * Default Monaco editor options shared by Console, Writer, and other pages.
 * Consumers should spread these defaults and override only what's needed.
 *
 * Usage:
 *   monaco.editor.create(container, {
 *     ...MONACO_EDITOR_DEFAULTS,
 *     language: "python",
 *     theme: initialTheme,
 *     // any page-specific overrides
 *   });
 */
export const MONACO_EDITOR_DEFAULTS = {
  automaticLayout: true,
  fontSize: 14,
  fontFamily: "'JetBrains Mono', 'Monaco', 'Menlo', monospace",
  minimap: { enabled: true },
  lineNumbers: "on" as const,
  renderWhitespace: "selection" as const,
  scrollBeyondLastLine: false,
  wordWrap: "on" as const,
  tabSize: 4,
  insertSpaces: true,
  glyphMargin: true,
  suggest: {
    showKeywords: true,
    showSnippets: true,
  },
  quickSuggestions: true,
  parameterHints: { enabled: true },
  formatOnPaste: true,
  formatOnType: true,
} as const;

// EOF
