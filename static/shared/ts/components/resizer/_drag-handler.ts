/**
 * Drag state machine for BaseResizer.
 *
 * Handles mousedown → mousemove → mouseup with:
 * - Smart collapse: panel collapses instantly during drag (not on mouseUp)
 * - Cascade propagation: remaining delta transfers to adjacent panel
 * - Magnetic snap: resizer is physically pulled toward snap points
 * - Four resize modes: only-second, only-first, both, neither
 */

import type { BaseResizer } from "./_base";
import type { PropagationTarget } from "./types";
import { saveCollapsed, saveSize } from "./_state";
import { updateToggleIcon } from "./_toggle";
import { magneticSnap, percentSnapPoints } from "./_snap";

/** Attach drag handling to a BaseResizer instance */
export function attachDragHandler(resizer: BaseResizer): void {
  const el = resizer.getResizerEl();
  el.addEventListener("mousedown", (e) => onMouseDown(resizer, e));
}

function onMouseDown(r: BaseResizer, e: MouseEvent): void {
  if (r.isClickOnToggle(e)) return;

  e.preventDefault();
  r.startDrag(e);
  const [sf, ss] = r.getStartSizes();
  console.log(
    `[Resizer:drag] mousedown on ${r.getStorageKey()} — firstSize=${sf}, secondSize=${ss}, firstCan=${r.getFirstCanCollapse()}, secondCan=${r.getSecondCanCollapse()}, threshold=${r.getThresholdPx()}, isInApp=${r.getIsInApp()}`,
  );

  document.body.style.cursor = r.getCursorPublic();
  document.body.style.userSelect = "none";
  r.getResizerEl().classList.add("active");

  // Disable transitions during drag
  r.getFirstPanel().style.transition = "none";
  r.getSecondPanel().style.transition = "none";
  if (!r.getIsInApp()) {
    document
      .querySelectorAll<HTMLElement>(".stx-shell-sidebar")
      .forEach((el) => (el.style.transition = "none"));
  }

  r.fireOnDragStart();

  const onMove = (e: MouseEvent) => handleMouseMove(r, e);
  const onUp = () => handleMouseUp(r, onMove, onUp);

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
}

function handleMouseMove(r: BaseResizer, e: MouseEvent): void {
  if (!r.isDraggingNow()) return;

  // If primary collapsed and propagation target exists, resize that instead
  if (r.isPrimaryCollapsed() && r.getPropagate()) {
    applyPropagation(r, e);
    return;
  }
  if (r.isPrimaryCollapsed()) return;

  const delta = r.getMousePosPublic(e) - r.getStartPos();
  applyResize(r, delta, e);
}

function handleMouseUp(
  r: BaseResizer,
  onMove: (e: MouseEvent) => void,
  onUp: () => void,
): void {
  if (!r.isDraggingNow()) return;
  r.endDrag();

  document.body.style.cursor = "";
  document.body.style.userSelect = "";
  r.getResizerEl().classList.remove("active");
  r.getResizerEl().classList.remove("snapped");
  r.getFirstPanel().style.transition = "";
  r.getSecondPanel().style.transition = "";
  if (!r.getIsInApp()) {
    document
      .querySelectorAll<HTMLElement>(".stx-shell-sidebar")
      .forEach((el) => (el.style.transition = ""));
  }

  document.removeEventListener("mousemove", onMove);
  document.removeEventListener("mouseup", onUp);
  console.log(
    `[Resizer:drag] mouseup on ${r.getStorageKey()} — first.collapsed=${r.getFirstPanel().classList.contains("collapsed")}, second.collapsed=${r.getSecondPanel().classList.contains("collapsed")}, firstSize=${r.getSizePublic(r.getFirstPanel())}, secondSize=${r.getSizePublic(r.getSecondPanel())}`,
  );

  // Save propagation target state
  const prop = r.getPropagate();
  if (prop) {
    const propSize = r.getSizePublic(prop.panel);
    if (propSize > prop.thresholdPx + 10) {
      saveSize(prop.storageKey, propSize);
    }
    r.clearPropagate();
  }

  r.fireOnDragEnd();
  r.saveStatePublic();
}

/** Compute snap points for the current drag context */
function getSnapPoints(r: BaseResizer): number[] {
  const container = r.getFirstPanel().parentElement;
  if (!container) return r.getSnapPoints();
  const containerSize = r.getSizePublic(container);
  const pctSnaps = percentSnapPoints(containerSize);
  const explicit = r.getSnapPoints();
  return explicit.length > 0 ? [...pctSnaps, ...explicit] : pctSnaps;
}

/** Apply magnetic snap to a raw size value and update visual feedback */
function snap(r: BaseResizer, raw: number, snaps: number[]): number {
  const result = magneticSnap(raw, snaps);
  const el = r.getResizerEl();
  if (result.snapped) {
    el.classList.add("snapped");
  } else {
    el.classList.remove("snapped");
  }
  return result.value;
}

/**
 * Apply resize delta to primary panels.
 * Four cases via if/else if/else:
 *   1. Only second can collapse → size set on second
 *   2. Only first can collapse → size set on first
 *   3. Both/neither → proportional (snap first panel only to avoid conflicts)
 */
function applyResize(r: BaseResizer, delta: number, e: MouseEvent): void {
  const first = r.getFirstPanel();
  const second = r.getSecondPanel();
  const key = r.getStorageKey();
  const threshold = r.getThresholdPx();
  const [startFirst, startSecond] = r.getStartSizes();
  const firstCan = r.getFirstCanCollapse();
  const secondCan = r.getSecondCanCollapse();
  const snaps = getSnapPoints(r);

  if (secondCan && !firstCan) {
    const totalSize = startFirst + startSecond;
    const maxSize = totalSize - threshold; // protect first panel
    const newSize = Math.min(snap(r, startSecond - delta, snaps), maxSize);
    if (Math.abs(delta) % 50 < 2)
      console.log(
        `[Resizer:drag] ${key} mode=onlySecondCan delta=${delta.toFixed(0)} newSecondSize=${newSize.toFixed(0)} threshold=${threshold}`,
      );
    if (newSize < threshold) {
      console.log(
        `[Resizer:drag] ${key} COLLAPSE second (newSize=${newSize.toFixed(0)} < threshold=${threshold})`,
      );
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("second");
      tryStartCascade(r, second, e);
      return;
    }
    if (second.classList.contains("collapsed")) {
      console.log(`[Resizer:drag] ${key} UN-COLLAPSE second`);
      second.classList.remove("collapsed");
      saveCollapsed(key + "-second", false);
    }
    r.setSizePublic(second, newSize);
    second.style.flexShrink = "0";
    second.style.flexGrow = "0";
  } else if (firstCan && !secondCan) {
    const totalSize = startFirst + startSecond;
    const maxSize = totalSize - threshold; // protect second panel
    const newSize = Math.min(snap(r, startFirst + delta, snaps), maxSize);
    if (Math.abs(delta) % 50 < 2)
      console.log(
        `[Resizer:drag] ${key} mode=onlyFirstCan delta=${delta.toFixed(0)} newFirstSize=${newSize.toFixed(0)} threshold=${threshold}`,
      );
    if (newSize < threshold) {
      console.log(
        `[Resizer:drag] ${key} COLLAPSE first (newSize=${newSize.toFixed(0)} < threshold=${threshold})`,
      );
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("first");
      tryStartCascade(r, first, e);
      return;
    }
    if (first.classList.contains("collapsed")) {
      console.log(`[Resizer:drag] ${key} UN-COLLAPSE first`);
      first.classList.remove("collapsed");
      saveCollapsed(key + "-first", false);
    }
    r.setSizePublic(first, newSize);
    first.style.flexShrink = "0";
    first.style.flexGrow = "0";
  } else {
    // Snap first panel only; second adjusts to fill remaining space
    const newFirst = snap(r, startFirst + delta, snaps);
    let newSecond = startSecond - (newFirst - startFirst);

    if (firstCan && newFirst < threshold) {
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("first");
      tryStartCascade(r, first, e);
      return;
    }
    if (secondCan && newSecond < threshold) {
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("second");
      tryStartCascade(r, second, e);
      return;
    }

    if (!firstCan && newFirst < threshold) {
      newSecond = startFirst + startSecond - threshold;
    }
    if (!secondCan && newSecond < threshold) newSecond = threshold;

    const finalFirst = !firstCan && newFirst < threshold ? threshold : newFirst;

    if (first.classList.contains("collapsed")) {
      first.classList.remove("collapsed");
      saveCollapsed(key + "-first", false);
    }
    if (second.classList.contains("collapsed")) {
      second.classList.remove("collapsed");
      saveCollapsed(key + "-second", false);
    }

    r.setSizePublic(first, finalFirst);
    first.style.flexShrink = "0";
    first.style.flexGrow = "0";
    r.setSizePublic(second, newSecond);
    second.style.flexShrink = "0";
    second.style.flexGrow = "0";
  }
}

/** Attempt to start cascade propagation after primary collapse */
function tryStartCascade(
  r: BaseResizer,
  collapsingPanel: HTMLElement,
  e: MouseEvent,
): void {
  if (r.getIsInApp()) return;
  const target = r.findCascadeTargetPublic(
    collapsingPanel,
    r.getMousePosPublic(e),
  );
  if (target) r.setPropagate(target);
}

/** Apply propagation delta to the cascade target */
function applyPropagation(r: BaseResizer, e: MouseEvent): void {
  const prop = r.getPropagate();
  if (!prop) return;

  const propDelta = r.getMousePosPublic(e) - prop.startPos;
  const snaps = getSnapPoints(r);
  const newSize = snap(r, prop.startSize + propDelta, snaps);

  if (newSize < prop.thresholdPx) {
    // Cascade: collapse target, find next
    cascadeCollapseTarget(r, prop);
    const next = r.findCascadeTargetPublic(prop.panel, r.getMousePosPublic(e));
    r.setPropagate(next);
    return;
  }

  r.setSizePublic(prop.panel, newSize);
  prop.panel.style.flexShrink = "0";
  prop.panel.style.flexGrow = "0";
}

/** Collapse the current cascade propagation target */
function cascadeCollapseTarget(r: BaseResizer, prop: PropagationTarget): void {
  prop.panel.classList.add("collapsed");
  r.clearSizePublic(prop.panel);
  prop.panel.style.flexShrink = "";
  prop.panel.style.flexGrow = "";

  saveCollapsed(prop.storageKey, true);

  if (prop.toggleBtn && prop.toggleIcon) {
    updateToggleIcon(prop.toggleBtn, prop.toggleIcon, true);
  }
}
