/**
 * Move a bottom-docked launcher only when it covers keyboard focus.
 *
 * This is transient geometry, not layout reservation: the page keeps its full
 * height and the dock returns to its anchor when focus leaves the covered
 * control.
 */

export interface RectLike {
  left: number;
  top: number;
  right: number;
  bottom: number;
}

export const FOCUS_AVOID_CLASS = "site-dock--avoiding-focus";
export const FOCUS_SHIFT_VAR = "--site-dock-focus-shift";

/** A tab switch may leave focus on body; its page-sized box is not a control. */
export function isFocusAvoidanceTarget(
  target: EventTarget | null,
): target is HTMLElement {
  if (
    !(target instanceof HTMLElement) ||
    target === document.body ||
    target === document.documentElement ||
    target.matches('[role="tabpanel"], [role="region"]')
  ) return false;
  return target.matches(
    'a[href], button, input:not([type="hidden"]), select, textarea, summary, ' +
    '[role="button"], [role="link"], [role="checkbox"], [role="radio"], ' +
    '[role="switch"], [role="combobox"], [role="textbox"], [role="slider"], ' +
    '[role="spinbutton"], [role="menuitem"], [tabindex]:not([tabindex="-1"]), ' +
    '[contenteditable]:not([contenteditable="false"])',
  );
}

export function focusAvoidanceShift(
  dock: RectLike,
  target: RectLike,
  gap = 8,
): number {
  const overlapsHorizontally = target.right > dock.left && target.left < dock.right;
  const overlapsVertically = target.bottom > dock.top && target.top < dock.bottom;
  if (!overlapsHorizontally || !overlapsVertically) return 0;
  return Math.max(0, Math.ceil(dock.bottom - target.top + gap));
}
