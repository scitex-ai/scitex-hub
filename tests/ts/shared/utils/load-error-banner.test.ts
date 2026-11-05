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

  it("sits above the bottom nav instead of covering it (dock clearance)", async () => {
    await importFresh();
    const script = document.createElement("script");
    script.src = "http://x/static/vite/missing-abc123.js";
    document.body.append(script);
    script.dispatchEvent(new Event("error", { bubbles: false, cancelable: false }));
    const el = banner();
    expect(el).not.toBeNull();
    // The site dock owns the bottom edge (CCT4814/4815): the banner must
    // clear it via the shared token, never sit on the nav.
    const posStyle = (el?.getAttribute("style") ?? "").replace(/\s+/g, "");
    expect(posStyle).toContain("bottom:calc(var(--site-dock-scroll-clearance,0px)+16px)");
  });

  it.each([
    "https://static.cloudflareinsights.com/beacon.min.js",
    "https://static.cloudflareinsights.com/beacon.min.js/vce701823e78c4301a35b7e07294d87301792088814092",
    "https://static.cloudflareinsights.com/beacon.min.js?fixture=analytics",
  ])("ignores optional analytics but still reports the next required script: %s", async (src) => {
    await importFresh();
    const analytics = document.createElement("script");
    analytics.src = src;
    document.body.append(analytics);
    analytics.dispatchEvent(new Event("error"));
    expect(banner()).toBeNull();

    const required = document.createElement("script");
    required.src = "https://scitex.example/static/vite/required-app.js";
    document.body.append(required);
    required.dispatchEvent(new Event("error"));
    expect(banner()?.textContent).toContain("required-app.js");
    expect(document.querySelectorAll("#stx-load-error-banner")).toHaveLength(1);
  });

  it.each([
    "https://scitex.example/static/beacon.min.js",
    "https://static.cloudflareinsights.com.other.example/beacon.min.js",
    "https://static.cloudflareinsights.com/required-app.js",
    "https://challenges.cloudflare.com/turnstile/v0/api.js",
  ])("keeps required and unrelated resource failures visible: %s", async (src) => {
    await importFresh();
    const script = document.createElement("script");
    script.src = src;
    document.body.append(script);
    script.dispatchEvent(new Event("error"));
    expect(banner()?.textContent).toContain(src.split("/").pop());
  });

  it("honors the host's analytics role without consuming a required failure", async () => {
    await importFresh();
    const analytics = document.createElement("script");
    analytics.src = "https://analytics.example/script.js";
    analytics.setAttribute("data-stx-resource-role", "analytics");
    document.body.append(analytics);
    analytics.dispatchEvent(new Event("error"));
    expect(banner()).toBeNull();
    const required = document.createElement("script");
    required.src = "https://scitex.example/required-app.js";
    document.body.append(required);
    required.dispatchEvent(new Event("error"));
    expect(banner()?.textContent).toContain("required-app.js");
  });

  it("keeps an explicitly required application script visible", async () => {
    await importFresh();
    const required = document.createElement("script");
    required.src = "https://scitex.example/required-app.js";
    required.setAttribute("data-stx-resource-role", "application");
    document.body.append(required);
    required.dispatchEvent(new Event("error"));
    expect(banner()?.textContent).toContain("required-app.js");
  });
});
