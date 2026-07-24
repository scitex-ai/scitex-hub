/**
 * Tests for static/shared/ts/utils/theme-switcher.ts
 *
 * Boot-time theme precedence (card hub-theme-default-must-be-dark):
 * 1. A registered user's SAVED preference (server source "profile").
 * 2. An explicit prior choice in this browser (localStorage).
 * 3. The DARK base default — on every viewport; a server-served
 *    default (source "default") must never override an explicit
 *    localStorage choice, and prefers-color-scheme is never consulted.
 */

import { describe, it, expect, vi } from "vitest";

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
