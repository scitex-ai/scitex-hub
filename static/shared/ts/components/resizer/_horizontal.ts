/**
 * HorizontalResizer — X-axis panel resizing.
 *
 * Extends BaseResizer with horizontal drag logic, width-based sizing,
 * and domino cascade for frame-level resizers.
 *
 * Usage:
 *   new HorizontalResizer(resizerEl, config)
 *
 * Or via data attributes:
 *   <div class="h-resizer" data-h-resizer
 *        data-left=".left-panel" data-right=".right-panel"
 *        data-icon="fa-chevron-left" data-title="Files"
 *        data-most-left data-threshold="40">
 *   </div>
 */

import { BaseResizer } from "./_base";
import type { HorizontalConfig, PropagationTarget } from "./types";
import { makeStorageKey } from "./_state";

export class HorizontalResizer extends BaseResizer {
  constructor(resizerEl: HTMLElement, config: HorizontalConfig) {
    const leftPanel = document.querySelector(config.left) as HTMLElement;
    const rightPanel = document.querySelector(config.right) as HTMLElement;

    if (!leftPanel || !rightPanel) {
      throw new Error(
        `[Resizer] Missing panels: left=${config.left} right=${config.right}`,
      );
    }

    super(resizerEl, leftPanel, rightPanel, {
      icon: config.icon,
      title: config.title,
      firstCanCollapse: config.isMostLeft,
      secondCanCollapse: config.isMostRight,
      thresholdPx: config.thresholdPx,
      isInApp: config.isInApp,
      storageKey:
        config.storageKey || makeStorageKey(config.left, config.right),
      onDragStart: config.onDragStart,
      onDragEnd: config.onDragEnd,
      externalToggleBtnId: config.externalToggleBtnId,
      accordion: config.accordion,
      snapPoints: config.snapPoints,
    });
  }

  protected getMousePos(e: MouseEvent): number {
    return e.clientX;
  }

  protected getSize(el: HTMLElement): number {
    return el.offsetWidth;
  }

  protected setSize(el: HTMLElement, px: number): void {
    el.style.flexBasis = `${px}px`;
    el.style.width = `${px}px`;
  }

  protected clearSize(el: HTMLElement): void {
    el.style.flexBasis = "";
    el.style.width = "";
  }

  protected getCursor(): string {
    return "col-resize";
  }

  /**
   * Find the next non-collapsed resizable panel for cascade.
   * Walks siblings of workspace-three-col, skipping collapsed or
   * non-resizable panes. Frame-level only (isInApp=false).
   */
  protected findCascadeTarget(
    collapsingPanel: HTMLElement,
    mousePos: number,
  ): PropagationTarget | null {
    if (this.isInApp) return null;

    // Find the pane wrapper of the collapsing panel
    const paneContainer = collapsingPanel.closest(
      ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-apps-pane, .ws-module-pane",
    );
    if (!paneContainer) return null;

    // Determine cascade direction: walk left or right through siblings
    const isFirst = collapsingPanel === this.firstPanel;
    const direction = isFirst ? "previous" : "next";

    let current: Element | null = paneContainer;
    while (current) {
      const sibling =
        direction === "previous"
          ? current.previousElementSibling
          : current.nextElementSibling;
      if (!sibling) return null;

      // Look for resizer inside this sibling pane
      const sibResizer = sibling.querySelector(
        "[data-h-resizer], [data-panel-resizer]",
      ) as HTMLElement;
      const sibPanel = sibling.querySelector(
        ".stx-shell-sidebar",
      ) as HTMLElement;

      if (!sibResizer || !sibPanel) {
        current = sibling;
        continue;
      }

      if (sibPanel.classList.contains("collapsed")) {
        current = sibling;
        continue;
      }

      // Get toggle button info for icon sync
      const toggleId =
        sibResizer.dataset.toggleBtn || sibResizer.dataset.externalToggle || "";
      const toggleBtn = toggleId ? document.getElementById(toggleId) : null;
      const toggleIcon = sibResizer.dataset.icon || "";

      return {
        panel: sibPanel,
        storageKey:
          sibResizer.dataset.storageKey || sibResizer.dataset.collapseKey || "",
        startSize: sibPanel.offsetWidth,
        startPos: mousePos,
        thresholdPx: parseInt(sibResizer.dataset.threshold || "48", 10),
        toggleBtn,
        toggleIcon,
      };
    }

    return null;
  }

  /** Build config from a data-h-resizer element's attributes */
  static configFromElement(el: HTMLElement): HorizontalConfig | null {
    const left = el.dataset.left;
    const right = el.dataset.right;

    if (!left || !right) {
      console.warn("[Resizer] Missing data-left or data-right on", el);
      return null;
    }

    return {
      left,
      right,
      icon: el.dataset.icon || "",
      title: el.dataset.title || "",
      isMostLeft: el.hasAttribute("data-most-left"),
      isMostRight: el.hasAttribute("data-most-right"),
      thresholdPx: parseInt(el.dataset.threshold || "48", 10),
      isInApp: el.hasAttribute("data-in-app"),
      storageKey: el.dataset.storageKey,
      externalToggleBtnId: el.dataset.externalToggle,
      accordion: el.hasAttribute("data-accordion"),
      snapPoints: el.dataset.snap
        ? el.dataset.snap.split(",").map((s) => parseInt(s.trim(), 10))
        : undefined,
    };
  }
}
