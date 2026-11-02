/**
 * Focus avoidance keeps a terminal control visible without reserving layout.
 */

import { describe, expect, it } from "vitest";

import {
  focusAvoidanceShift,
  isFocusAvoidanceTarget,
} from "@/components/_site-dock/focus-avoid";
import { SiteDock } from "@/components/site-dock";

const rect = (left: number, top: number, width: number, height: number) =>
  ({ left, top, right: left + width, bottom: top + height }) as DOMRect;

describe("site dock focus avoidance", () => {
  it("ignores body and focusable panels while preserving real controls", () => {
    const panel = document.createElement("div");
    panel.tabIndex = 0;
    panel.setAttribute("role", "tabpanel");
    expect(isFocusAvoidanceTarget(document.body)).toBe(false);
    expect(isFocusAvoidanceTarget(document.documentElement)).toBe(false);
    expect(isFocusAvoidanceTarget(panel)).toBe(false);
    for (const tag of ["button", "input", "textarea", "select", "summary"]) {
      expect(isFocusAvoidanceTarget(document.createElement(tag))).toBe(true);
    }
    const customButton = document.createElement("div");
    customButton.setAttribute("role", "button");
    expect(isFocusAvoidanceTarget(customButton)).toBe(true);
    const keyboardControl = document.createElement("span");
    keyboardControl.tabIndex = 0;
    expect(isFocusAvoidanceTarget(keyboardControl)).toBe(true);
  });

  it("clears a previous focus shift when a hidden tab button yields focus to body", () => {
    document.body.innerHTML = '<nav data-site-dock><button data-dock-grabber></button></nav>';
    const dock = document.querySelector<HTMLElement>("[data-site-dock]")!;
    dock.getBoundingClientRect = () => rect(10, 681, 370, 153);
    const originalBodyRect = document.body.getBoundingClientRect;
    document.body.getBoundingClientRect = () => rect(0, 0, 1000, 2000);
    new SiteDock(dock).init();
    dock.classList.add("site-dock--avoiding-focus");
    dock.style.setProperty("--site-dock-focus-shift", "-621px");

    document.body.dispatchEvent(new FocusEvent("focusin", { bubbles: true }));
    document.body.getBoundingClientRect = originalBodyRect;

    expect(dock.classList.contains("site-dock--avoiding-focus")).toBe(false);
    expect(dock.style.getPropertyValue("--site-dock-focus-shift")).toBe("");
  });
  it("moves the dock just above an overlapping focused control", () => {
    expect(
      focusAvoidanceShift(
        rect(10, 681, 370, 153),
        rect(16, 780, 358, 44),
      ),
    ).toBe(62);
  });

  it("does not move for a control already clear of the dock", () => {
    expect(
      focusAvoidanceShift(
        rect(10, 681, 370, 153),
        rect(16, 600, 358, 44),
      ),
    ).toBe(0);
  });

  it("does not move for a control beside the dock", () => {
    expect(
      focusAvoidanceShift(
        rect(300, 681, 80, 153),
        rect(16, 780, 200, 44),
      ),
    ).toBe(0);
  });

  it("temporarily shifts the bottom dock when focus would be covered", () => {
    document.body.innerHTML = `
      <main><input id="last-control"></main>
      <nav data-site-dock><button data-dock-grabber></button></nav>
    `;
    const dock = document.querySelector<HTMLElement>("[data-site-dock]")!;
    const control = document.querySelector<HTMLElement>("#last-control")!;
    dock.getBoundingClientRect = () => rect(10, 681, 370, 153);
    control.getBoundingClientRect = () => rect(16, 780, 358, 44);
    new SiteDock(dock).init();

    control.focus();

    expect(dock.classList.contains("site-dock--avoiding-focus")).toBe(true);
    expect(dock.style.getPropertyValue("--site-dock-focus-shift")).toBe(
      "-62px",
    );
  });
});
