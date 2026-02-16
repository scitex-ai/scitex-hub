/**
 * Editor Theme Module for Writer
 * Re-exports shared Monaco theme configuration (identical to Console)
 *
 * Single source of truth: static/shared/ts/monaco/MonacoTheme.ts
 */

console.log("[DEBUG] EditorTheme.ts loaded");

export {
  setupMonacoTheme,
  initializeMonacoThemes,
  setupMonacoThemeObserver,
  defineScitexDarkTheme,
  defineScitexLightTheme,
  MONACO_COLORS,
  getThemeForMode,
  getCurrentThemeMode,
} from "/static/shared/ts/monaco/MonacoTheme.js";

// EOF
