/**
 * Theme toggle interaction handlers
 */

import type { VisEditor } from "../VisEditor.ts";

/**
 * Setup canvas-specific theme toggle
 */
export function setupThemeToggle(editor: VisEditor): void {
  const themeToggle = document.getElementById("canvas-theme-toggle");
  if (!themeToggle) {
    console.warn("[InteractionHandlers] Canvas theme toggle button not found");
    return;
  }

  // Get global theme first to use as default
  const globalTheme = localStorage.getItem("scitex-theme-preference") || "dark";
  const canvasThemeValue = localStorage.getItem("canvas-theme") || globalTheme;
  let canvasIsDark = canvasThemeValue === "dark";

  const updateThemeEmoji = (isDark: boolean) => {
    const themeIcon = themeToggle.querySelector(".theme-icon");
    if (themeIcon) {
      themeIcon.textContent = isDark ? "🌙" : "☀️";
    }
  };

  const updateDarkModeWarning = (isDark: boolean) => {
    const warning = document.getElementById("toolbar-dark-warning");
    if (warning) {
      warning.style.display = isDark ? "inline-flex" : "none";
    }
  };

  themeToggle.addEventListener("click", () => {
    canvasIsDark = !canvasIsDark;
    const canvasTheme = canvasIsDark ? "dark" : "light";
    localStorage.setItem("canvas-theme", canvasTheme);

    editor.updateCanvasTheme(canvasIsDark);
    updateThemeEmoji(canvasIsDark);
    updateDarkModeWarning(canvasIsDark);

    console.log(`[InteractionHandlers] Canvas theme toggled to ${canvasTheme}`);
  });

  // Apply initial theme state
  updateThemeEmoji(canvasIsDark);
  updateDarkModeWarning(canvasIsDark);
  editor.updateCanvasTheme(canvasIsDark);
  console.log(
    `[InteractionHandlers] Canvas theme restored to ${canvasThemeValue}`,
  );
}

/**
 * Apply saved themes on initialization
 */
export function applySavedThemes(editor: VisEditor): void {
  const savedTheme = localStorage.getItem("scitex-theme-preference") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);

  const savedCanvasTheme = localStorage.getItem("canvas-theme") || savedTheme;
  const canvasDarkMode = savedCanvasTheme === "dark";
  editor.updateCanvasTheme(canvasDarkMode);

  console.log("[InteractionHandlers] Themes applied");
}
