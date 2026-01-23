/**
 * Editor Factory Module
 * Handles creation and configuration of Monaco editor instances
 */

console.log("[DEBUG] EditorFactory.ts loaded");

/**
 * Create Monaco editor instance with proper configuration
 */
export function createMonacoEditor(
  monaco: any,
  container: HTMLElement,
  initialValue: string,
  config: any
): any {
  // Load saved theme preference or detect current theme
  const savedTheme = localStorage.getItem("monaco-editor-theme-writer");
  const isDarkMode =
    document.documentElement.getAttribute("data-theme") === "dark";
  const initialTheme = savedTheme || (isDarkMode ? "scitex-dark" : "scitex-light");

  const editor = monaco.editor.create(container, {
    value: initialValue,
    language: "latex",
    theme: initialTheme,
    lineNumbers: config.lineNumbers !== false ? "on" : "off",
    wordWrap: config.lineWrapping !== false ? "on" : "off",
    wrappingIndent: "indent", // Wrap with proper indentation
    tabSize: 2, // LaTeX standard: 2 spaces
    insertSpaces: true,

    // RAINBOW BRACKETS & BRACKET FEATURES (Emacs-style!)
    "bracketPairColorization.enabled": true,
    "bracketPairColorization.independentColorPoolPerBracketType": true,
    matchBrackets: "always", // Highlight matching brackets
    autoClosingBrackets: "always",
    autoClosingQuotes: "always",
    autoSurround: "languageDefined", // Auto-surround selected text

    // VISUAL GUIDES (Python/Elisp-style structure visualization)
    "guides.bracketPairs": true, // Vertical lines for bracket pairs
    "guides.highlightActiveBracketPair": true, // Highlight active pair
    "guides.indentation": true, // Show indentation guides

    // SMART EDITING FEATURES
    formatOnPaste: true, // Auto-format on paste
    formatOnType: true, // Auto-format while typing

    // UI & NAVIGATION
    automaticLayout: true,
    minimap: { enabled: false }, // Disable minimap
    folding: true, // Enable code folding
    foldingStrategy: "indentation", // Fold based on indentation
    scrollBeyondLastLine: false,
    fontSize: 14,
    lineHeight: 21, // Fixed: was 19, now 21 (1.5x fontSize for proper cursor alignment)
    fontFamily: 'Consolas, Monaco, "Courier New", monospace', // Fixed: use web-safe monospace fonts
    renderLineHighlight: "none",

    // AUTOCOMPLETE & SUGGESTIONS
    suggestOnTriggerCharacters: true,
    quickSuggestions: true,
    wordBasedSuggestions: false,
    fixedOverflowWidgets: true, // CRITICAL: Render widgets in body to prevent clipping
    suggest: {
      showIcons: true,
      showStatusBar: true, // Keep "show more" text visible
      maxVisibleSuggestions: 20, // Show up to 20 suggestions at once
      snippetsPreventQuickSuggestions: false,
      preselect: "first", // Preselect first item
    },

    // SCROLLBAR
    scrollbar: {
      vertical: "visible",
      horizontal: "visible",
      verticalScrollbarSize: 10,
      horizontalScrollbarSize: 10,
      alwaysConsumeMouseWheel: true,
    },
    mouseWheelScrollSensitivity: 1,
    fastScrollSensitivity: 5,
  });

  // Initialize theme toggle button
  setTimeout(() => {
    const toggleBtn = document.getElementById("monaco-theme-toggle");
    const themeIcon = toggleBtn?.querySelector(".theme-icon");
    if (themeIcon) {
      const isDark = initialTheme === "scitex-dark" || initialTheme === "vs-dark";
      themeIcon.textContent = isDark ? "🌙" : "☀️";
      toggleBtn?.setAttribute("title",
        isDark ? "Switch to light editor theme" : "Switch to dark editor theme"
      );
    }
  }, 100);

  return editor;
}
