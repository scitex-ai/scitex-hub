/**
 * Site dock minimize — state, persistence, and the live height variable.
 */

import { beforeEach, describe, expect, it } from "vitest";

import {
  gripTap,
  LIVE_HEIGHT_VAR,
  MINIMIZED_CLASS,
  readMinimized,
  setMinimized,
} from "@/components/_site-dock/minimize";
import { panelRect } from "@/components/_site-dock/chat-float";

function makeDock(height: number): HTMLElement {
  const dock = document.createElement("nav");
  dock.innerHTML =
    '<button data-dock-grabber data-label-move="Move dock" data-label-show="Show dock"></button>';
  dock.getBoundingClientRect = () => ({ height }) as DOMRect;
  document.body.appendChild(dock);
  return dock;
}

describe("site dock minimize", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    document.documentElement.style.removeProperty(LIVE_HEIGHT_VAR);
    window.localStorage.clear();
  });

  it("minimize adds the pill class", () => {
    const dock = makeDock(44);
    setMinimized(dock, true);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(true);
  });

  it("minimize is remembered per device", () => {
    setMinimized(makeDock(44), true);
    expect(readMinimized()).toBe(true);
  });

  it("restore forgets the minimized state", () => {
    const dock = makeDock(150);
    setMinimized(dock, true);
    setMinimized(dock, false);
    expect(readMinimized()).toBe(false);
  });

  it("publishes the dock's real height for the page padding", () => {
    setMinimized(makeDock(44), true);
    expect(
      document.documentElement.style.getPropertyValue(LIVE_HEIGHT_VAR),
    ).toBe("44px");
  });

  it("labels the pill as Show dock", () => {
    const dock = makeDock(44);
    setMinimized(dock, true);
    expect(
      dock.querySelector("[data-dock-grabber]")?.getAttribute("aria-label"),
    ).toBe("Show dock");
  });

  it("double-tap on the grip minimizes the dock", () => {
    expect(
      gripTap(1000, { minimized: false, lastTap: 800, lastRestore: 0 }),
    ).toBe("minimize");
  });

  it("the second tap of a pill-restoring double-tap is swallowed", () => {
    expect(
      gripTap(1000, { minimized: false, lastTap: 0, lastRestore: 800 }),
    ).toBe("ignore");
  });

  it("chat panel keeps a phone width above a minimized pill", () => {
    const pill = { left: 153, top: 790, width: 84, height: 44 };
    expect(panelRect(pill, { width: 390, height: 844 }).width).toBe(374);
  });
});
