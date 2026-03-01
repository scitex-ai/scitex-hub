/**
 * Drag state machine for BaseResizer.
 *
 * Handles mousedown → mousemove → mouseup with:
 * - Smart collapse: panel collapses instantly during drag (not on mouseUp)
 * - Cascade propagation: remaining delta transfers to adjacent panel
 * - Four resize modes: only-second, only-first, both, neither
 */

import type { BaseResizer } from "./base";
import type { PropagationTarget } from "./types";
import { saveCollapsed, saveSize } from "./state";
import { updateToggleIcon } from "./toggle";

/** Attach drag handling to a BaseResizer instance */
export function attachDragHandler(resizer: BaseResizer): void {
  const el = resizer.getResizerEl();
  el.addEventListener("mousedown", (e) => onMouseDown(resizer, e));
}

function onMouseDown(r: BaseResizer, e: MouseEvent): void {
  if (r.isClickOnToggle(e)) return;

  e.preventDefault();
  r.startDrag(e);

  document.body.style.cursor = r.getCursorPublic();
  document.body.style.userSelect = "none";
  r.getResizerEl().classList.add("active");

  // Disable transitions during drag
  r.getFirstPanel().style.transition = "none";
  r.getSecondPanel().style.transition = "none";
  if (!r.getIsInApp()) {
    document
      .querySelectorAll<HTMLElement>(".workspace-sidebar")
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
  r.getFirstPanel().style.transition = "";
  r.getSecondPanel().style.transition = "";
  if (!r.getIsInApp()) {
    document
      .querySelectorAll<HTMLElement>(".workspace-sidebar")
      .forEach((el) => (el.style.transition = ""));
  }

  document.removeEventListener("mousemove", onMove);
  document.removeEventListener("mouseup", onUp);

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

/**
 * Apply resize delta to primary panels.
 * Four cases via if/else if/else:
 *   1. Only second can collapse → size set on second
 *   2. Only first can collapse → size set on first
 *   3. Both/neither → proportional
 */
function applyResize(r: BaseResizer, delta: number, e: MouseEvent): void {
  const first = r.getFirstPanel();
  const second = r.getSecondPanel();
  const key = r.getStorageKey();
  const threshold = r.getThresholdPx();
  const [startFirst, startSecond] = r.getStartSizes();
  const firstCan = r.getFirstCanCollapse();
  const secondCan = r.getSecondCanCollapse();

  if (secondCan && !firstCan) {
    const newSize = startSecond - delta;
    if (newSize < threshold) {
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("second");
      tryStartCascade(r, second, e);
      return;
    }
    if (second.classList.contains("collapsed")) {
      second.classList.remove("collapsed");
      saveCollapsed(key + "-second", false);
    }
    r.setSizePublic(second, newSize);
    second.style.flexShrink = "0";
    second.style.flexGrow = "0";
  } else if (firstCan && !secondCan) {
    const newSize = startFirst + delta;
    if (newSize < threshold) {
      r.markPrimaryCollapsed();
      r.collapsePanelPublic("first");
      tryStartCascade(r, first, e);
      return;
    }
    if (first.classList.contains("collapsed")) {
      first.classList.remove("collapsed");
      saveCollapsed(key + "-first", false);
    }
    r.setSizePublic(first, newSize);
    first.style.flexShrink = "0";
    first.style.flexGrow = "0";
  } else {
    let newFirst = startFirst + delta;
    let newSecond = startSecond - delta;

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

    if (!firstCan && newFirst < threshold) newFirst = threshold;
    if (!secondCan && newSecond < threshold) newSecond = threshold;

    if (first.classList.contains("collapsed")) {
      first.classList.remove("collapsed");
      saveCollapsed(key + "-first", false);
    }
    if (second.classList.contains("collapsed")) {
      second.classList.remove("collapsed");
      saveCollapsed(key + "-second", false);
    }

    r.setSizePublic(first, newFirst);
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
  const newSize = prop.startSize + propDelta;

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
