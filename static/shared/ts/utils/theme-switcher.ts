/**
 * SciTeX Theme Switcher
 * Handles Light/Dark mode switching with localStorage persistence and database sync
 */

import { getCsrfToken } from "./csrf";

type Theme = "light" | "dark";

interface ThemeResponse {
  theme?: Theme;
  /**
   * "profile" — a REGISTERED user's saved preference (wins everywhere).
   * "default" — served fallback (anonymous / visitor-pool session);
   * must never override an explicit prior choice in this browser.
   */
  source?: "profile" | "default";
}

interface ThemeSaveResponse {
  success: boolean;
  /** false when the server kept the choice browser-only (visitor session). */
  persisted?: boolean;
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

  // Migration: Clean up old 'auto' or 'system' values from previous
  // implementation. Those were never an explicit light choice, so they
  // migrate to the DARK base default (operator mandate).
  if (stored && !["light", "dark"].includes(stored)) {
    console.log(`Migrating invalid theme value: "${stored}" → "${THEME_DARK}"`);
    localStorage.setItem(STORAGE_KEY, THEME_DARK);
    return THEME_DARK;
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
async function loadThemeFromDatabase(): Promise<ThemeResponse | null> {
  try {
    const response = await fetch("/auth/api/get-theme/");
    const data: ThemeResponse = await response.json();
    if (data.theme) {
      return data;
    }
  } catch (error) {
    console.warn("Failed to load theme from database:", error);
  }
  return null;
}

/**
 * Resolve the theme to apply at boot (pure — exported for tests).
 *
 * Precedence (operator mandate, card hub-theme-default-must-be-dark):
 * 1. A registered user's SAVED preference (server source "profile").
 * 2. An explicit prior choice in this browser (localStorage).
 * 3. The base default: DARK, on every viewport. A server-served
 *    default (source "default") carries the same value;
 *    prefers-color-scheme is deliberately not consulted so an OS
 *    light preference can never flip a first visit to light.
 *
 * Visitor-pool sessions get source "default" from the server, so a
 * recycled slot's stale profile row can never override this browser's
 * explicit choice (the desktop-light bug measured on prod 2026-07-22).
 */
export function resolveInitialTheme(
  db: ThemeResponse | null,
  stored: string | null,
): Theme {
  if (db && db.theme && db.source === "profile") {
    return db.theme;
  }
  if (stored === THEME_LIGHT || stored === THEME_DARK) {
    return stored;
  }
  return THEME_DARK;
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
      if (data.persisted === false) {
        // Visitor session: the server refuses to write onto the shared
        // pool account; the choice lives in this browser's localStorage.
        console.log(
          "Theme kept in this browser only (visitor session):",
          theme,
        );
      } else {
        console.log("Theme saved to database:", theme);
      }
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
  const db = await loadThemeFromDatabase();
  const theme = resolveInitialTheme(db, localStorage.getItem(STORAGE_KEY));

  // Only a real saved profile preference is synced into localStorage —
  // a served default must not masquerade as an explicit choice.
  if (db && db.theme && db.source === "profile") {
    localStorage.setItem(STORAGE_KEY, db.theme);
    localStorage.setItem(LEGACY_STORAGE_KEY, db.theme);
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
