/**
 * Shared Monaco Configuration
 * Single source of truth for Monaco editor setup across SciTeX
 */

export {
  MONACO_COLORS,
  defineScitexDarkTheme,
  defineScitexLightTheme,
  initializeMonacoThemes,
  getThemeForMode,
  getCurrentThemeMode,
  setupMonacoThemeObserver,
  setupMonacoTheme,
} from "./MonacoTheme";

export { MONACO_EDITOR_DEFAULTS } from "./MonacoDefaults";

// EOF
