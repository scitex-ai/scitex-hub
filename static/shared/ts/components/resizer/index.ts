/**
 * Unified Resizer System
 *
 * Auto-initializes all resizer instances from data attributes:
 *   [data-h-resizer] → HorizontalResizer
 *   [data-v-resizer] → VerticalResizer
 *
 * The old [data-panel-resizer] system remains active in workspace-panel-resizer/
 * for backward compat during migration. This module only handles new attributes.
 *
 * Re-initializes on htmx:afterSettle for dynamically loaded content.
 */

export type {
  HorizontalConfig,
  VerticalConfig,
  BaseOpts,
  PropagationTarget,
} from "./types";
export { HorizontalResizer } from "./_horizontal";
export { VerticalResizer } from "./_vertical";
export { BaseResizer } from "./_base";

import { HorizontalResizer } from "./_horizontal";
import { VerticalResizer } from "./_vertical";

let _autoInitDone = false;
const _initializedIds = new Set<string>();

/** Auto-initialize all horizontal resizers on the page */
function initHorizontalResizers(): number {
  let count = 0;
  document.querySelectorAll("[data-h-resizer]").forEach((el) => {
    const resizerEl = el as HTMLElement;
    if (!resizerEl.id) {
      resizerEl.id = `h-resizer-${count}`;
    }
    if (_initializedIds.has(resizerEl.id)) return;

    const config = HorizontalResizer.configFromElement(resizerEl);
    if (!config) return;

    try {
      new HorizontalResizer(resizerEl, config);
      _initializedIds.add(resizerEl.id);
      count++;
    } catch (e) {
      console.warn("[Resizer] Failed to init horizontal:", e);
    }
  });
  return count;
}

/** Auto-initialize all vertical resizers on the page */
function initVerticalResizers(): number {
  let count = 0;
  document.querySelectorAll("[data-v-resizer]").forEach((el) => {
    const resizerEl = el as HTMLElement;
    if (!resizerEl.id) {
      resizerEl.id = `v-resizer-${count}`;
    }
    if (_initializedIds.has(resizerEl.id)) return;

    const config = VerticalResizer.configFromElement(resizerEl);
    if (!config) return;

    try {
      new VerticalResizer(resizerEl, config);
      _initializedIds.add(resizerEl.id);
      count++;
    } catch (e) {
      console.warn("[Resizer] Failed to init vertical:", e);
    }
  });
  return count;
}

/** Initialize all resizers. Called once on DOMContentLoaded. */
export function autoInit(): void {
  if (_autoInitDone) {
    console.log("[Resizer] autoInit already done, skipping.");
    return;
  }
  _autoInitDone = true;

  document.body.classList.add("no-transition");

  const hCount = initHorizontalResizers();
  const vCount = initVerticalResizers();

  console.log(
    `[Resizer] Auto-initialized ${hCount} horizontal + ${vCount} vertical`,
  );

  // Smart collapse for module pane (no resizer, flex:1 fills remaining space)
  const modulePane = document.querySelector<HTMLElement>(".ws-module-pane");
  if (modulePane) {
    const MODULE_COLLAPSE_THRESHOLD = 80;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width < MODULE_COLLAPSE_THRESHOLD) {
          modulePane.classList.add("collapsed");
        } else {
          modulePane.classList.remove("collapsed");
        }
      }
    });
    ro.observe(modulePane);
  }

  // Mark panels ready + remove transition guard (double-rAF)
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document
        .querySelectorAll(".workspace-three-col, .workspace-shell")
        .forEach((el) => el.classList.add("panels-ready"));
      document.body.classList.remove("no-transition");
    });
  });
}

/** Initialize resizers added after initial load (e.g., HTMX content). */
export function initNewResizers(): void {
  document.body.classList.add("no-transition");

  const hCount = initHorizontalResizers();
  const vCount = initVerticalResizers();

  if (hCount + vCount > 0) {
    console.log(
      `[Resizer] Late-initialized ${hCount} horizontal + ${vCount} vertical`,
    );
  }

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document
        .querySelectorAll(".workspace-three-col, .workspace-shell")
        .forEach((el) => el.classList.add("panels-ready"));
      document.body.classList.remove("no-transition");
    });
  });
}

// Auto-init on page load
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoInit);
  } else {
    autoInit();
  }

  // Re-init on HTMX content swaps
  document.addEventListener("htmx:afterSettle", () => {
    initNewResizers();
  });
}
