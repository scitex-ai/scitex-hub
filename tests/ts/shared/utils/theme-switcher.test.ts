/**
 * Tests for static/shared/ts/utils/theme-switcher.ts
 *
 * Two complementary suites, deliberately kept side by side:
 *
 * 1. resolveInitialTheme — the PURE boot-time precedence function
 *    (card hub-theme-default-must-be-dark):
 *      a. A registered user's SAVED preference (server source "profile").
 *      b. An explicit prior choice in this browser (localStorage).
 *      c. The DARK base default — on every viewport; a server-served
 *         default (source "default") must never override an explicit
 *         localStorage choice, and prefers-color-scheme is never consulted.
 *
 * 2. stx-theme key convergence — the STORAGE contract shared with
 *    scitex-ui's ThemeProvider (card hub-scitex-ui-070-theme-key-convergence).
 *    Exercised through the public window.SciTeX.theme API, since the
 *    module self-initializes on import and exports nothing else.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

const CANONICAL_KEY = "stx-theme";
const LEGACY_KEY = "scitex-theme-preference";

// The module runs initTheme() at import time; stub fetch first so the
// import-side get-theme call resolves deterministically (no network).
vi.stubGlobal(
  "fetch",
  vi.fn(() =>
    Promise.resolve({
      json: () => Promise.resolve({}),
    }),
  ),
);

const { resolveInitialTheme } = await import("@/utils/theme-switcher");

describe("resolveInitialTheme", () => {
  it("lets a registered user's saved light preference win over stored dark", () => {
    expect(
      resolveInitialTheme({ theme: "light", source: "profile" }, "dark"),
    ).toBe("light");
  });

  it("lets a registered user's saved dark preference win over stored light", () => {
    expect(
      resolveInitialTheme({ theme: "dark", source: "profile" }, "light"),
    ).toBe("dark");
  });

  it("keeps an explicit stored light choice over a served default", () => {
    // A visitor/anonymous session gets source "default" — a recycled
    // pool account's row must never override this browser's choice.
    expect(
      resolveInitialTheme({ theme: "dark", source: "default" }, "light"),
    ).toBe("light");
  });

  it("keeps an explicit stored dark choice over a served default", () => {
    expect(
      resolveInitialTheme({ theme: "dark", source: "default" }, "dark"),
    ).toBe("dark");
  });

  it("defaults a first visit to dark when nothing is stored", () => {
    expect(resolveInitialTheme(null, null)).toBe("dark");
  });

  it("defaults to dark when the server serves the default and nothing is stored", () => {
    expect(
      resolveInitialTheme({ theme: "dark", source: "default" }, null),
    ).toBe("dark");
  });

  it("treats a source-less response as a default, not a preference", () => {
    expect(resolveInitialTheme({ theme: "light" }, null)).toBe("dark");
  });

  it("ignores an invalid stored value and falls back to dark", () => {
    expect(resolveInitialTheme(null, "system")).toBe("dark");
  });
});

async function importFresh(): Promise<void> {
  vi.resetModules();
  // initTheme() fetches /auth/api/get-theme/ on import; an anonymous
  // visitor gets no theme back, which routes reads to localStorage.
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ json: async () => ({}) }));
  await import("@/utils/theme-switcher");
  // Let the initTheme() promise chain settle.
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe("theme-switcher stx-theme convergence", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("reads the canonical stx-theme key first", async () => {
    localStorage.setItem(CANONICAL_KEY, "light");
    localStorage.setItem(LEGACY_KEY, "dark");
    await importFresh();
    expect(window.SciTeX.theme.get()).toBe("light");
  });

  it("falls back to the legacy key and migrates it onto stx-theme", async () => {
    localStorage.setItem(LEGACY_KEY, "light");
    await importFresh();
    expect(window.SciTeX.theme.get()).toBe("light");
    expect(localStorage.getItem(CANONICAL_KEY)).toBe("light");
  });

  it("defaults to dark when neither key is set", async () => {
    await importFresh();
    expect(window.SciTeX.theme.get()).toBe("dark");
  });

  it("set() writes both keys (legacy kept in sync for one release cycle)", async () => {
    await importFresh();
    window.SciTeX.theme.set("light");
    expect(localStorage.getItem(CANONICAL_KEY)).toBe("light");
    expect(localStorage.getItem(LEGACY_KEY)).toBe("light");
  });

  it("cleans an invalid stored value to DARK on the canonical key", async () => {
    // NOTE: this expectation was "light" on the original 2026-07-21 branch.
    // It is deliberately NOT restored. PR #436 made DARK the base default on
    // every viewport (operator mandate), and getThemePreference() migrates any
    // non-light/dark value to THEME_DARK. Re-applying the stale "light"
    // expectation would have been a stale test dragging the source back to a
    // behaviour the dark-default card exists to prevent.
    localStorage.setItem(CANONICAL_KEY, "system");
    await importFresh();
    expect(window.SciTeX.theme.get()).toBe("dark");
    expect(localStorage.getItem(CANONICAL_KEY)).toBe("dark");
  });

  it("applies the resolved theme to the document root", async () => {
    localStorage.setItem(CANONICAL_KEY, "dark");
    await importFresh();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
