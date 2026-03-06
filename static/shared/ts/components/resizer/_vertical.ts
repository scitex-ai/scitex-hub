/**
 * VerticalResizer — Y-axis panel resizing.
 *
 * Extends BaseResizer with vertical drag logic, height-based sizing
 * using flexBasis for consistent flex container behavior.
 *
 * Usage:
 *   new VerticalResizer(resizerEl, config)
 *
 * Or via data attributes:
 *   <div class="v-resizer" data-v-resizer
 *        data-top=".top-panel" data-bottom=".bottom-panel"
 *        data-icon="fa-chevron-up" data-title="Header"
 *        data-most-top data-threshold="40">
 *   </div>
 */

import { BaseResizer } from "./_base";
import type { VerticalConfig } from "./types";
import { makeStorageKey } from "./_state";

export class VerticalResizer extends BaseResizer {
  constructor(resizerEl: HTMLElement, config: VerticalConfig) {
    const topPanel = document.querySelector(config.top) as HTMLElement;
    const bottomPanel = document.querySelector(config.bottom) as HTMLElement;

    if (!topPanel || !bottomPanel) {
      throw new Error(
        `[Resizer] Missing panels: top=${config.top} bottom=${config.bottom}`,
      );
    }

    super(resizerEl, topPanel, bottomPanel, {
      icon: config.icon,
      title: config.title,
      firstCanCollapse: config.isMostTop,
      secondCanCollapse: config.isMostBottom,
      thresholdPx: config.thresholdPx,
      isInApp: config.isInApp,
      storageKey:
        config.storageKey || makeStorageKey(config.top, config.bottom),
      onDragStart: config.onDragStart,
      onDragEnd: config.onDragEnd,
      accordion: config.accordion,
      snapPoints: config.snapPoints,
    });
  }

  protected getMousePos(e: MouseEvent): number {
    return e.clientY;
  }

  protected getSize(el: HTMLElement): number {
    return el.offsetHeight;
  }

  protected setSize(el: HTMLElement, px: number): void {
    el.style.flexBasis = `${px}px`;
  }

  protected clearSize(el: HTMLElement): void {
    el.style.flexBasis = "";
  }

  protected getCursor(): string {
    return "row-resize";
  }

  /** Build config from a data-v-resizer element's attributes */
  static configFromElement(el: HTMLElement): VerticalConfig | null {
    const top = el.dataset.top;
    const bottom = el.dataset.bottom;

    if (!top || !bottom) {
      console.warn("[Resizer] Missing data-top or data-bottom on", el);
      return null;
    }

    return {
      top,
      bottom,
      icon: el.dataset.icon || "",
      title: el.dataset.title || "",
      isMostTop: el.hasAttribute("data-most-top"),
      isMostBottom: el.hasAttribute("data-most-bottom"),
      thresholdPx: parseInt(el.dataset.threshold || "48", 10),
      isInApp: el.hasAttribute("data-in-app"),
      storageKey: el.dataset.storageKey,
      accordion: el.hasAttribute("data-accordion"),
      snapPoints: el.dataset.snap
        ? el.dataset.snap.split(",").map((s) => parseInt(s.trim(), 10))
        : undefined,
    };
  }
}
