/**
 * Tests for static/shared/ts/utils/load-error-banner.ts
 *
 * The banner is the UX-standard fallback: a failed resource must render an
 * error state, never a blank region. Exercised through real DOM events in
 * jsdom (the module self-initializes on import like theme-switcher).
 */

import { describe, it, expect, vi, beforeEach } from "vitest";

async function importFresh(): Promise<void> {
  vi.resetModules();
  document.body.innerHTML = "";
  await import("@/utils/load-error-banner");
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function banner(): HTMLElement | null {
  return document.getElementById("stx-load-error-banner");
}

describe("load-error-banner", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
  });

  it("shows the banner with reload when a script fails to load", async () => {
    await importFresh();
    expect(banner()).toBeNull();
    const script = document.createElement("script");
    script.src = "http://x/static/vite/missing-abc123.js";
    document.body.append(script);
    script.dispatchEvent(new Event("error", { bubbles: false, cancelable: false }));
    // Capture listeners fire synchronously on dispatch.
    const el = banner();
    expect(el).not.toBeNull();
    expect(el?.textContent).toContain("missing-abc123.js");
    expect(el?.textContent).toContain("Reload");
  });

  it("shows once for repeated failures", async () => {
    await importFresh();
    for (let i = 0; i < 3; i++) {
      const link = document.createElement("link");
      document.body.append(link);
      link.dispatchEvent(new Event("error"));
    }
    expect(document.querySelectorAll("#stx-load-error-banner")).toHaveLength(1);
  });

  it("ignores non-resource errors", async () => {
    await importFresh();
    document.body.dispatchEvent(new Event("error"));
    expect(banner()).toBeNull();
  });

  it("reloads on button click", async () => {
    await importFresh();
    const script = document.createElement("script");
    document.body.append(script);
    script.dispatchEvent(new Event("error"));
    const reload = [...(banner()?.querySelectorAll("button") ?? [])].find(
      (b) => b.textContent === "Reload",
    );
    expect(reload).toBeDefined();
    const spy = vi.fn();
    Object.defineProperty(window, "location", {
      value: { reload: spy },
      writable: true,
    });
    reload?.click();
    expect(spy).toHaveBeenCalled();
  });

  it("never blocks inputs beneath it (mobile: pointer-events passthrough)", async () => {
    await importFresh();
    const script = document.createElement("script");
    script.src = "http://x/static/vite/missing-abc123.js";
    document.body.append(script);
    script.dispatchEvent(new Event("error", { bubbles: false, cancelable: false }));
    const el = banner();
    expect(el).not.toBeNull();
    // The bottom-fixed box must let taps reach inputs under it. (Asserted
    // on the serialized style attribute with whitespace stripped: jsdom's
    // CSSOM drops these two properties from the .style object, but browsers
    // honor the authored declarations.)
    const styleText = (el?.getAttribute("style") ?? "").replace(/\s+/g, "");
    expect(styleText).toContain("pointer-events:none");
    // ...while both actions stay tappable.
    const buttons = [...(el?.querySelectorAll("button") ?? [])];
    expect(buttons).toHaveLength(2);
    for (const b of buttons) {
      const btnStyle = (b.getAttribute("style") ?? "").replace(/\s+/g, "");
      expect(btnStyle).toContain("pointer-events:auto");
    }
  });

  it("wraps long unbroken resource tokens instead of overflowing", async () => {
    await importFresh();
    const link = document.createElement("link");
    (link as HTMLLinkElement).href =
      "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap";
    document.body.append(link);
    link.dispatchEvent(new Event("error", { bubbles: false, cancelable: false }));
    const el = banner();
    expect(el).not.toBeNull();
    expect(el?.textContent).toContain("css2?family=JetBrains+Mono");
    const wrapStyle = (el?.getAttribute("style") ?? "").replace(/\s+/g, "");
    expect(wrapStyle).toContain("overflow-wrap:anywhere");
    expect(wrapStyle).toContain("word-break:break-word");
  });
});
