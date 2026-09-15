/**
 * Site dock grip gesture — one tap toggles the pill, a drag moves without toggling.
 */

import { beforeEach, describe, expect, it } from "vitest";

import { SiteDock } from "@/components/site-dock";
import { MINIMIZED_CLASS } from "@/components/_site-dock/minimize";

function pointer(
  target: HTMLElement,
  type: string,
  x: number,
  y: number,
): void {
  const e = new MouseEvent(type, {
    bubbles: true,
    cancelable: true,
    clientX: x,
    clientY: y,
    button: 0,
  });
  Object.defineProperty(e, "pointerId", { value: 1 });
  Object.defineProperty(e, "pointerType", { value: "touch" });
  target.dispatchEvent(e);
}

function makeDock(): { dock: HTMLElement; grip: HTMLElement } {
  document.body.innerHTML =
    "<nav data-site-dock><button data-dock-grabber></button></nav>";
  const dock = document.querySelector<HTMLElement>("[data-site-dock]")!;
  dock.getBoundingClientRect = () =>
    ({ left: 100, top: 700, width: 200, height: 100 }) as DOMRect;
  new SiteDock(dock).init();
  return {
    dock,
    grip: dock.querySelector<HTMLElement>("[data-dock-grabber]")!,
  };
}

function tap(grip: HTMLElement, dx = 0, dy = 0): void {
  pointer(grip, "pointerdown", 150, 750);
  if (dx || dy) pointer(grip, "pointermove", 150 + dx, 750 + dy);
  pointer(grip, "pointerup", 150 + dx, 750 + dy);
}

describe("site dock grip gesture", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("a single tap minimizes the dock", () => {
    const { dock, grip } = makeDock();
    tap(grip);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(true);
  });

  it("a single tap on the pill restores the dock", () => {
    const { dock, grip } = makeDock();
    tap(grip);
    tap(grip);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("a small wobble still counts as a tap", () => {
    const { dock, grip } = makeDock();
    tap(grip, 3);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(true);
  });

  it("a drag does not toggle", () => {
    const { dock, grip } = makeDock();
    tap(grip, 40);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("a drag moves the dock", () => {
    const { grip } = makeDock();
    tap(grip, 0, -400);
    expect(
      window.localStorage.getItem("stx-site-dock-position"),
    ).not.toBeNull();
  });

  it("a cancelled press does not toggle", () => {
    const { dock, grip } = makeDock();
    pointer(grip, "pointerdown", 150, 750);
    pointer(grip, "pointercancel", 150, 750);
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });

  it("Enter on the grip toggles the pill", () => {
    const { dock, grip } = makeDock();
    grip.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    );
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(true);
  });

  it("Space on the pill restores the dock", () => {
    const { dock, grip } = makeDock();
    tap(grip);
    grip.dispatchEvent(
      new KeyboardEvent("keydown", { key: " ", bubbles: true }),
    );
    expect(dock.classList.contains(MINIMIZED_CLASS)).toBe(false);
  });
});
