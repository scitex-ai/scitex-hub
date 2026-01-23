/**
 * Shared Monaco Theme Configuration
 * Single source of truth for Monaco editor themes across all SciTeX modules
 * Used by /code/, /writer/, /vis/, and other Monaco-enabled pages
 */

console.log("[DEBUG] shared/monaco/MonacoTheme.ts loaded");

/**
 * Monaco theme color constants
 * workspace-bg-monaco: #1e1e1e (dark) / #ffffff (light)
 */
export const MONACO_COLORS = {
  dark: {
    background: "#1e1e1e",
    gutterBackground: "#1e1e1e",
    lineHighlight: "#2d2d2d",
    lineNumber: "#858585",
    lineNumberActive: "#c6c6c6",
    selection: "#264f78",
    selectionInactive: "#3a3d41",
  },
  light: {
    background: "#ffffff",
    gutterBackground: "#ffffff",
    lineHighlight: "#f5f5f5",
    lineNumber: "#6e7681",
    lineNumberActive: "#24292f",
    selection: "#add6ff",
    selectionInactive: "#e5ebf1",
  },
} as const;

/**
 * Define SciTeX dark theme for Monaco
 * Extends vs-dark with consistent workspace colors
 */
export function defineScitexDarkTheme(monaco: any): void {
  monaco.editor.defineTheme("scitex-dark", {
    base: "vs-dark",
    inherit: true,
    rules: [
      // LaTeX syntax highlighting rules
      { token: "comment.latex", foreground: "6A9955", fontStyle: "italic" },
      { token: "keyword.latex", foreground: "569CD6" },
      { token: "keyword.control.latex", foreground: "C586C0" },
      { token: "keyword.section.latex", foreground: "DCDCAA", fontStyle: "bold" },
      { token: "keyword.math.latex", foreground: "9CDCFE" },
      { token: "string.math.latex", foreground: "CE9178" },
      { token: "type.identifier.latex", foreground: "4EC9B0" },
      { token: "delimiter.curly.latex", foreground: "FFD700" },
      { token: "delimiter.square.latex", foreground: "DA70D6" },
      { token: "number.latex", foreground: "B5CEA8" },
      { token: "operator.latex", foreground: "D4D4D4" },
    ],
    colors: {
      "editor.background": MONACO_COLORS.dark.background,
      "editorGutter.background": MONACO_COLORS.dark.gutterBackground,
      "editor.lineHighlightBackground": MONACO_COLORS.dark.lineHighlight,
      "editorLineNumber.foreground": MONACO_COLORS.dark.lineNumber,
      "editorLineNumber.activeForeground": MONACO_COLORS.dark.lineNumberActive,
      "editor.selectionBackground": MONACO_COLORS.dark.selection,
      "editor.inactiveSelectionBackground": MONACO_COLORS.dark.selectionInactive,
    },
  });
}

/**
 * Define SciTeX light theme for Monaco
 * Extends vs with consistent workspace colors
 */
export function defineScitexLightTheme(monaco: any): void {
  monaco.editor.defineTheme("scitex-light", {
    base: "vs",
    inherit: true,
    rules: [
      // LaTeX syntax highlighting rules (light theme)
      { token: "comment.latex", foreground: "008000", fontStyle: "italic" },
      { token: "keyword.latex", foreground: "0000FF" },
      { token: "keyword.control.latex", foreground: "AF00DB" },
      { token: "keyword.section.latex", foreground: "795E26", fontStyle: "bold" },
      { token: "keyword.math.latex", foreground: "001080" },
      { token: "string.math.latex", foreground: "A31515" },
      { token: "type.identifier.latex", foreground: "267F99" },
      { token: "delimiter.curly.latex", foreground: "B8860B" },
      { token: "delimiter.square.latex", foreground: "800080" },
      { token: "number.latex", foreground: "098658" },
      { token: "operator.latex", foreground: "000000" },
    ],
    colors: {
      "editor.background": MONACO_COLORS.light.background,
      "editorGutter.background": MONACO_COLORS.light.gutterBackground,
      "editor.lineHighlightBackground": MONACO_COLORS.light.lineHighlight,
      "editorLineNumber.foreground": MONACO_COLORS.light.lineNumber,
      "editorLineNumber.activeForeground": MONACO_COLORS.light.lineNumberActive,
      "editor.selectionBackground": MONACO_COLORS.light.selection,
      "editor.inactiveSelectionBackground": MONACO_COLORS.light.selectionInactive,
    },
  });
}

/**
 * Initialize all SciTeX Monaco themes
 * Call this once when Monaco is loaded
 */
export function initializeMonacoThemes(monaco: any): void {
  defineScitexDarkTheme(monaco);
  defineScitexLightTheme(monaco);
  console.log("[MonacoTheme] SciTeX themes registered: scitex-dark, scitex-light");
}

/**
 * Get the appropriate theme name based on current site theme
 */
export function getThemeForMode(mode: "dark" | "light"): string {
  return mode === "dark" ? "scitex-dark" : "scitex-light";
}

/**
 * Get current site theme mode from data-theme attribute
 */
export function getCurrentThemeMode(): "dark" | "light" {
  return document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
}

/**
 * Setup theme observer to auto-switch Monaco theme when site theme changes
 */
export function setupMonacoThemeObserver(monaco: any): void {
  const themeObserver = new MutationObserver(() => {
    const mode = getCurrentThemeMode();
    const themeName = getThemeForMode(mode);
    monaco.editor.setTheme(themeName);
    console.log("[MonacoTheme] Auto-switched to:", themeName);
  });

  themeObserver.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });

  console.log("[MonacoTheme] Theme observer installed");
}

/**
 * Full Monaco theme setup - call this after Monaco is loaded
 * Registers themes and sets up auto-switching
 */
export function setupMonacoTheme(monaco: any): void {
  initializeMonacoThemes(monaco);
  setupMonacoThemeObserver(monaco);

  // Set initial theme based on current site theme
  const mode = getCurrentThemeMode();
  const themeName = getThemeForMode(mode);
  monaco.editor.setTheme(themeName);
  console.log("[MonacoTheme] Initial theme set to:", themeName);
}

// EOF
