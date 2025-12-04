/**
 * Editor Theme Module for Writer
 * Re-exports shared Monaco theme configuration
 *
 * NOTE: Theme definitions are now in static/shared/ts/monaco/MonacoTheme.ts
 * This file provides backward-compatible exports for writer_app
 */

console.log("[DEBUG] EditorTheme.ts loaded");

// Re-export from shared Monaco theme (compiled JS in /static/shared/ts/monaco/)
export {
  defineScitexDarkTheme as defineScitexTheme,
  defineScitexLightTheme,
  setupMonacoThemeObserver as setupThemeObserver,
  initializeMonacoThemes,
  setupMonacoTheme,
  MONACO_COLORS,
  getThemeForMode,
  getCurrentThemeMode,
} from "/static/shared/ts/monaco/MonacoTheme.ts";

// EOF
