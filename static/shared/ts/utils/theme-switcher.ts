/**
 * SciTeX Theme Switcher
 * Handles Light/Dark mode switching with localStorage persistence and database sync
 */

import { getCsrfToken } from "./csrf";

type Theme = "light" | "dark";

interface ThemeResponse {
  theme?: Theme;
}

interface ThemeSaveResponse {
  success: boolean;
}

interface SciTeXThemeAPI {
  toggle: () => void;
  set: (theme: Theme) => void;
  get: () => Theme;
  LIGHT: Theme;
  DARK: Theme;
}

declare global {
  interface Window {
    SciTeX: {
      theme: SciTeXThemeAPI;
    };
  }
}

// Canonical key converged with scitex-ui's ThemeProvider ("stx-theme").
// The legacy hub key is a published contract: still read (one-time
// migration) and written in sync for one release cycle — cached bundles
// and tool embeds listen on it. Remove LEGACY_STORAGE_KEY after the
// release that follows the one shipping this rename.
const STORAGE_KEY = "stx-theme";
const LEGACY_STORAGE_KEY = "scitex-theme-preference";
const THEME_LIGHT: Theme = "light";
const THEME_DARK: Theme = "dark";

/**
 * Get the current theme preference from localStorage
 */
function getThemePreference(): Theme {
  const stored =
    localStorage.getItem(STORAGE_KEY) ??
    localStorage.getItem(LEGACY_STORAGE_KEY);

  // Migration: Clean up old 'auto' or 'system' values from previous implementation
  if (stored && !["light", "dark"].includes(stored)) {
    console.log(
      `Migrating invalid theme value: "${stored}" → "${THEME_LIGHT}"`,
    );
    localStorage.setItem(STORAGE_KEY, THEME_LIGHT);
    return THEME_LIGHT;
  }

  if (stored && (stored === THEME_LIGHT || stored === THEME_DARK)) {
    // One-time migration: a legacy-only value gets copied onto the
    // canonical key so later reads never depend on the legacy key.
    if (!localStorage.getItem(STORAGE_KEY)) {
      localStorage.setItem(STORAGE_KEY, stored);
    }
    return stored as Theme;
  }

  return THEME_DARK; // Default to dark theme for new visitors
}

/**
 * Load theme preference from database (for authenticated users)
 */
async function loadThemeFromDatabase(): Promise<Theme | null> {
  try {
    const response = await fetch("/auth/api/get-theme/");
    const data: ThemeResponse = await response.json();
    if (data.theme) {
      return data.theme;
    }
  } catch (error) {
    console.warn("Failed to load theme from database:", error);
  }
  return null;
}

/**
 * Save theme preference to database (for authenticated users)
 */
async function saveThemeToDatabase(theme: Theme): Promise<void> {
  try {
    const csrfToken = getCsrfToken();
    const response = await fetch("/auth/api/save-theme/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken,
      },
      body: JSON.stringify({ theme }),
    });
    const data: ThemeSaveResponse = await response.json();
    if (data.success) {
      console.log("Theme saved to database:", theme);
    }
  } catch (error) {
    console.warn("Failed to save theme to database:", error);
  }
}

/**
 * Apply theme to the document
 */
function applyTheme(theme: Theme): void {
  if (theme === THEME_DARK) {
    document.documentElement.setAttribute("data-theme", "dark");
    document.documentElement.setAttribute("data-color-mode", "dark");
  } else {
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.setAttribute("data-color-mode", "light");
  }

  // Update toggle button if exists
  updateToggleButton();

  // Dispatch custom event for Monaco editor and terminal to listen to
  const event = new CustomEvent("theme-changed", {
    detail: { theme },
  });
  document.dispatchEvent(event);
}

/**
 * Set theme preference and apply
 */
function setThemePreference(preference: Theme): void {
  localStorage.setItem(STORAGE_KEY, preference);
  localStorage.setItem(LEGACY_STORAGE_KEY, preference);
  applyTheme(preference);
  // Save to database for authenticated users (async, don't wait)
  saveThemeToDatabase(preference);
}

/**
 * Toggle between themes: light <-> dark
 */
function toggleTheme(): void {
  const current = getThemePreference();
  const next = current === THEME_LIGHT ? THEME_DARK : THEME_LIGHT;
  setThemePreference(next);
}

/**
 * Update the toggle button appearance
 */
function updateToggleButton(): void {
  const toggleBtn = document.getElementById("theme-toggle");
  if (!toggleBtn) return;

  const theme = getThemePreference();

  // Update aria-label (accessibility)
  const labels = {
    light: "☀️ Light",
    dark: "🌙 Dark",
  } as const;

  // Note: title attribute removed to avoid duplicate tooltips with data-tooltip
  toggleBtn.setAttribute("aria-label", `Current theme: ${labels[theme]}`);

  // Update button content
  const icons = {
    light: "☀️",
    dark: "🌙",
  } as const;

  toggleBtn.innerHTML = icons[theme];
}

/**
 * Set up toggle button (call when DOM is ready)
 */
function setupToggleButton(): void {
  const toggleBtn = document.getElementById("theme-toggle");
  if (toggleBtn) {
    toggleBtn.addEventListener("click", function () {
      toggleTheme();
    });
    updateToggleButton();
  } else {
    console.warn("✗ Theme toggle button NOT found");
  }
}

/**
 * Initialize theme on page load
 */
async function initTheme(): Promise<void> {
  // Try to load from database first (for authenticated users)
  const dbTheme = await loadThemeFromDatabase();
  let theme: Theme;

  if (dbTheme) {
    // Use database theme and sync to localStorage
    theme = dbTheme;
    localStorage.setItem(STORAGE_KEY, dbTheme);
    localStorage.setItem(LEGACY_STORAGE_KEY, dbTheme);
  } else {
    // Fallback to localStorage
    theme = getThemePreference();
  }

  // Apply theme immediately to prevent flash
  applyTheme(theme);

  // Set up toggle button - handle both pre-loaded and post-loaded states
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupToggleButton);
  } else {
    // DOM already loaded
    setupToggleButton();
  }
}

// Initialize immediately (before DOM loads to prevent flash)
initTheme();

// Expose API for manual control and settings page
window.SciTeX = window.SciTeX || ({} as any);
window.SciTeX.theme = {
  toggle: toggleTheme,
  set: setThemePreference,
  get: getThemePreference,
  LIGHT: THEME_LIGHT,
  DARK: THEME_DARK,
};
