/** Floating Chat panel lifecycle around parent navigation. */

import { beforeEach, describe, expect, it, vi } from "vitest";

import { initChatPanel } from "@/components/_site-dock/chat-panel";
import { EMBED_PARENT_NAVIGATION } from "@/components/_site-dock/embed-navigation";

const SETTINGS = "/accounts/settings/ai-providers/";

function mountPanel() {
  document.body.innerHTML = `
    <nav data-site-dock>
      <a href="/chat/" data-dock-chat-toggle aria-expanded="false">Chat</a>
    </nav>
    <section data-dock-chat-panel hidden>
      <button data-dock-chat-minimize>Minimize</button>
      <button data-dock-chat-maximize data-label-max="Maximize" data-label-restore="Restore">Maximize</button>
      <button data-dock-chat-close>Close</button>
      <iframe data-dock-chat-frame></iframe>
    </section>`;
  const dock = document.querySelector<HTMLElement>("[data-site-dock]")!;
  dock.getBoundingClientRect = () =>
    ({ left: 100, top: 700, width: 380, height: 80 }) as DOMRect;
  return {
    dock,
    toggle: document.querySelector<HTMLElement>("[data-dock-chat-toggle]")!,
    panel: document.querySelector<HTMLElement>("[data-dock-chat-panel]")!,
    frame: document.querySelector<HTMLIFrameElement>("[data-dock-chat-frame]")!,
    close: document.querySelector<HTMLButtonElement>("[data-dock-chat-close]")!,
    maximize: document.querySelector<HTMLButtonElement>("[data-dock-chat-maximize]")!,
  };
}

function trustedNavigation(frame: HTMLIFrameElement): MessageEvent {
  return new MessageEvent("message", {
    origin: window.location.origin,
    source: frame.contentWindow,
    data: { type: EMBED_PARENT_NAVIGATION, href: SETTINGS },
  });
}

describe("floating Chat parent-navigation recovery", () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.stubGlobal(
      "matchMedia",
      vi.fn(() => ({ matches: false, addEventListener: vi.fn() })),
    );
  });

  it("closes and resets before navigating, and coalesces repeated clicks", () => {
    const ui = mountPanel();
    const navigate = vi.fn();
    initChatPanel(ui.dock, { navigate });
    ui.toggle.click();
    ui.maximize.click();
    expect(ui.panel.hidden).toBe(false);
    expect(ui.frame.getAttribute("src")).toContain("/chat/?embed=1");

    const event = trustedNavigation(ui.frame);
    window.dispatchEvent(event);
    window.dispatchEvent(event);

    expect(navigate).toHaveBeenCalledTimes(1);
    expect(navigate).toHaveBeenCalledWith(SETTINGS);
    expect(ui.panel.hidden).toBe(true);
    expect(ui.toggle.getAttribute("aria-expanded")).toBe("false");
    expect(ui.panel.classList.contains("is-maximized")).toBe(false);
    expect(ui.frame.hasAttribute("src")).toBe(false);
    expect(sessionStorage.getItem("stx-site-dock-chat-open")).toBeNull();
    expect(sessionStorage.getItem("stx-site-dock-chat-max")).toBeNull();
  });

  it("Back or Cancel restores a fresh panel that can navigate again", () => {
    const ui = mountPanel();
    const navigate = vi.fn();
    initChatPanel(ui.dock, { navigate });
    ui.toggle.click();
    window.dispatchEvent(trustedNavigation(ui.frame));

    window.dispatchEvent(new Event("pageshow"));
    ui.toggle.click();
    expect(ui.panel.hidden).toBe(false);
    expect(ui.frame.getAttribute("src")).toContain("/chat/?embed=1");
    window.dispatchEvent(trustedNavigation(ui.frame));

    expect(navigate).toHaveBeenCalledTimes(2);
  });

  it("Close discards a nested frame and reopen starts canonical Chat", () => {
    const ui = mountPanel();
    initChatPanel(ui.dock, { navigate: vi.fn() });
    ui.toggle.click();
    ui.frame.setAttribute("src", "/accounts/settings/ai-providers/");

    ui.close.click();
    expect(ui.panel.hidden).toBe(true);
    expect(ui.frame.hasAttribute("src")).toBe(false);

    ui.toggle.click();
    expect(ui.panel.hidden).toBe(false);
    expect(ui.frame.getAttribute("src")).toContain("/chat/?embed=1");
    expect(ui.frame.getAttribute("src")).not.toContain("ai-providers");
  });
});
