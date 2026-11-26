/**
 * Minimized dock — collapses the dock to a small grip pill (operator 2026-09-15:
 * the two-row phone dock took too much of apps like FigRecipe).
 *
 * Collapsed is the default (live-paper QA 2026-11-26: the open dock sat over
 * the middle of every Hub page and covered content). The state is per device
 * (localStorage): "0" keeps the dock open once the user restores it, "1" or
 * no entry shows the pill. The dock's real height is published
 * as --site-dock-live-height on <html> for scroll alignment only; neither the
 * expanded dock nor the pill reserves page layout space.
 */

export const MINIMIZED_KEY = "stx-site-dock-minimized";
export const MINIMIZED_CLASS = "site-dock--minimized";
export const LIVE_HEIGHT_VAR = "--site-dock-live-height";

/** The saved preference; minimized unless the user chose the open dock. */
export function readMinimized(): boolean {
  try {
    return window.localStorage.getItem(MINIMIZED_KEY) !== "0";
  } catch {
    return true;
  }
}

export function syncDockHeight(
  dock: HTMLElement,
  root: HTMLElement = document.documentElement,
): void {
  const h = Math.round(dock.getBoundingClientRect().height);
  if (h > 0) root.style.setProperty(LIVE_HEIGHT_VAR, `${h}px`);
  else root.style.removeProperty(LIVE_HEIGHT_VAR);
}

export function setMinimized(
  dock: HTMLElement,
  on: boolean,
  persist = true,
): void {
  dock.classList.toggle(MINIMIZED_CLASS, on);
  const grabber = dock.querySelector<HTMLElement>("[data-dock-grabber]");
  const { labelShow, labelMove, titleMove } = grabber?.dataset ?? {};
  if (grabber && labelShow && labelMove) {
    grabber.setAttribute("aria-label", on ? labelShow : labelMove);
    grabber.setAttribute("title", on ? labelShow : (titleMove ?? labelMove));
  }
  try {
    if (persist) {
      window.localStorage.setItem(MINIMIZED_KEY, on ? "1" : "0");
    }
  } catch {
    /* storage unavailable: the state lasts for this page only */
  }
  syncDockHeight(dock);
}

/** Pointer travel below this is a tap; at or beyond it the press is a drag. */
export const TAP_SLOP_PX = 7;

export function isDrag(dx: number, dy: number): boolean {
  return Math.hypot(dx, dy) >= TAP_SLOP_PX;
}

export type GripTap = "restore" | "minimize";

/** One tap on the grip toggles the pill (operator 2026-09-15). */
export function gripTap(minimized: boolean): GripTap {
  return minimized ? "restore" : "minimize";
}

export function isMinimized(dock: HTMLElement): boolean {
  return dock.classList.contains(MINIMIZED_CLASS);
}
