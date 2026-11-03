/** Actual DOM event capture; no app-specific markup or persistent preference. */
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { SiteDock } from "@/components/site-dock";
import { MINIMIZED_CLASS, MINIMIZED_KEY } from "@/components/_site-dock/minimize";

const originalWidth = window.innerWidth;
function viewport(width: number): void {
  Object.defineProperty(window, "innerWidth", { value: width, configurable: true });
}
function setup(): { dock: HTMLElement; grip: HTMLElement; content: HTMLElement; action: HTMLElement; apps: HTMLElement } {
  document.body.innerHTML = `<main id="content"><article><button id="action">Action</button></article></main><nav data-site-dock><div id="apps"></div><button data-dock-grabber data-label-show="Show launcher" data-label-move="Move launcher"></button></nav>`;
  const dock = document.querySelector<HTMLElement>("[data-site-dock]")!;
  new SiteDock(dock).init();
  return { dock, grip: dock.querySelector<HTMLElement>("[data-dock-grabber]")!, content: document.querySelector<HTMLElement>("#content")!, action: document.querySelector<HTMLElement>("#action")!, apps: document.querySelector<HTMLElement>("#apps")! };
}
function scroll(content: HTMLElement, target: HTMLElement = content, user = true): void {
  if (user) target.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: 180 }));
  content.scrollTop += 180;
  content.dispatchEvent(new Event("scroll")); // Native element scroll is non-bubbling.
}
function tap(grip: HTMLElement): void {
  for (const type of ["pointerdown", "pointerup"]) {
    const event = new MouseEvent(type, { bubbles: true, cancelable: true, clientX: 180, clientY: 800, button: 0 });
    Object.defineProperty(event, "pointerId", { value: 1 });
    Object.defineProperty(event, "pointerType", { value: "touch" });
    grip.dispatchEvent(event);
  }
}

describe("phone content-scroll dock visibility", () => {
  beforeEach(() => { viewport(390); localStorage.clear(); sessionStorage.clear(); });
  afterEach(() => { viewport(originalWidth); document.body.innerHTML = ""; });

  it("captures a nested content scroll and preserves even a legacy expanded preference", () => {
    localStorage.setItem(MINIMIZED_KEY, "0");
    const { dock, content, action } = setup();
    const before = JSON.stringify(localStorage);
    scroll(content, action);
    expect({ minimized: dock.classList.contains(MINIMIZED_CLASS), storage: JSON.stringify(localStorage) }).toEqual({ minimized: true, storage: before });
  });

  it("does not collapse merely for programmatic scroll restoration", () => {
    const { dock, content } = setup();
    scroll(content, content, false);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("requires actual content movement after scroll intent", () => {
    const { dock, content } = setup();
    content.dispatchEvent(new WheelEvent("wheel", { bubbles: true, deltaY: 180 }));
    content.dispatchEvent(new Event("scroll"));
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("leaves desktop behavior unchanged", () => {
    viewport(1440);
    const { dock, content } = setup();
    scroll(content);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("does not minimize an already floating launcher", () => {
    const { dock, content } = setup();
    dock.classList.add("site-dock--floating");
    scroll(content);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("preserves a manually minimized preference", () => {
    localStorage.setItem(MINIMIZED_KEY, "1");
    const { dock, content } = setup();
    scroll(content);
    expect({ minimized: dock.classList.contains(MINIMIZED_CLASS), saved: localStorage.getItem(MINIMIZED_KEY) }).toEqual({ minimized: true, saved: "1" });
  });

  it("ignores scrolling inside the dock itself", () => {
    const { dock, apps } = setup();
    scroll(apps);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("ignores an owned chat panel moved outside the dock", () => {
    const { dock } = setup();
    const panel = document.createElement("section");
    panel.dataset.dockChatPanel = "";
    document.body.append(panel);
    scroll(panel);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("restores with a real grip tap and collapses again on the next content scroll", () => {
    const { dock, grip, content } = setup();
    const before = JSON.stringify(localStorage);
    scroll(content);
    tap(grip);
    const restored = !dock.classList.contains(MINIMIZED_CLASS);
    scroll(content);
    expect({ restored, recollapsed: dock.classList.contains(MINIMIZED_CLASS), storage: JSON.stringify(localStorage) }).toEqual({ restored: true, recollapsed: true, storage: before });
  });

  it.each(["Enter", " "])("restores transient collapse with %j without a preference write", (key) => {
    const { dock, grip, content } = setup();
    const before = JSON.stringify(localStorage);
    scroll(content);
    grip.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true }));
    expect({ minimized: dock.classList.contains(MINIMIZED_CLASS), storage: JSON.stringify(localStorage) }).toEqual({ minimized: false, storage: before });
  });

  it("does not reuse the old scroll gesture after grip restoration", () => {
    const { dock, grip, content } = setup();
    scroll(content);
    tap(grip);
    scroll(content, content, false);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("restores when widening to desktop without changing the preference", () => {
    const { dock, content } = setup();
    const before = JSON.stringify(localStorage);
    scroll(content);
    viewport(1440);
    window.dispatchEvent(new Event("resize"));
    expect({ minimized: dock.classList.contains(MINIMIZED_CLASS), storage: JSON.stringify(localStorage) }).toEqual({ minimized: false, storage: before });
  });
});
