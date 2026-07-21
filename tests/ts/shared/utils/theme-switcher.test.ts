/**
 * Tests for static/shared/ts/utils/theme-switcher.ts
 *
 * Focus: the stx-theme key convergence (scitex-ui ThemeProvider parity).
 * The module self-initializes on import (initTheme -> fetch), so each
 * test resets modules, seeds localStorage, mocks fetch, and imports
 * fresh. Behavior is exercised through the public window.SciTeX.theme
 * API — the module exports nothing else.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

const CANONICAL_KEY = "stx-theme";
const LEGACY_KEY = "scitex-theme-preference";

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

  it("cleans an invalid stored value to light on the canonical key", async () => {
    localStorage.setItem(CANONICAL_KEY, "system");
    await importFresh();
    expect(window.SciTeX.theme.get()).toBe("light");
    expect(localStorage.getItem(CANONICAL_KEY)).toBe("light");
  });

  it("applies the resolved theme to the document root", async () => {
    localStorage.setItem(CANONICAL_KEY, "dark");
    await importFresh();
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
