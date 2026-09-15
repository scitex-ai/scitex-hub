/**
 * Minimized dock — collapses the dock to a small grip pill (operator 2026-09-15:
 * the two-row phone dock took too much of apps like FigRecipe).
 *
 * The state is per device (localStorage). The dock's real height is published
 * as --site-dock-live-height on <html>, which the page's bottom reservation
 * (site-dock.css) reads, so a minimized dock gives the space back.
 */

export const MINIMIZED_KEY = "stx-site-dock-minimized";
export const MINIMIZED_CLASS = "site-dock--minimized";
export const LIVE_HEIGHT_VAR = "--site-dock-live-height";

export function readMinimized(): boolean {
  try {
    return window.localStorage.getItem(MINIMIZED_KEY) === "1";
  } catch {
    return false;
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

export function setMinimized(dock: HTMLElement, on: boolean): void {
  dock.classList.toggle(MINIMIZED_CLASS, on);
  const grabber = dock.querySelector<HTMLElement>("[data-dock-grabber]");
  const { labelShow, labelMove, titleMove } = grabber?.dataset ?? {};
  if (grabber && labelShow && labelMove) {
    grabber.setAttribute("aria-label", on ? labelShow : labelMove);
    grabber.setAttribute("title", on ? labelShow : (titleMove ?? labelMove));
  }
  try {
    if (on) window.localStorage.setItem(MINIMIZED_KEY, "1");
    else window.localStorage.removeItem(MINIMIZED_KEY);
  } catch {
    /* storage unavailable: the state lasts for this page only */
  }
  syncDockHeight(dock);
}

export const DOUBLE_TAP_MS = 320;

export type GripTap = "restore" | "minimize" | "ignore" | "arm";

/** What a tap (not a drag) on the grip does. A double-tap toggles the pill;
 *  the second tap of a double-tap that restored the pill is swallowed. */
export function gripTap(
  now: number,
  state: { minimized: boolean; lastTap: number; lastRestore: number },
): GripTap {
  if (state.minimized) return "restore";
  if (now - state.lastRestore < DOUBLE_TAP_MS) return "ignore";
  return now - state.lastTap < DOUBLE_TAP_MS ? "minimize" : "arm";
}

export function isMinimized(dock: HTMLElement): boolean {
  return dock.classList.contains(MINIMIZED_CLASS);
}
