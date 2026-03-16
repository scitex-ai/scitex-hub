/**
 * Unified Resizer System
 *
 * Auto-initializes all resizer instances from data attributes:
 *   [data-h-resizer] → HorizontalResizer
 *   [data-v-resizer] → VerticalResizer
 *
 * All templates now use [data-h-resizer] / [data-v-resizer].
 * The legacy [data-panel-resizer] system in _workspace-panel-resizer/ is retired.
 *
 * Re-initializes on htmx:afterSettle for dynamically loaded content.
 */

// Core classes re-exported from scitex-ui (canonical implementation)
export type {
  HorizontalConfig,
  VerticalConfig,
  BaseOpts,
  PropagationTarget,
} from "scitex-ui/ts/app/resizer";
export {
  HorizontalResizer,
  VerticalResizer,
  BaseResizer,
} from "scitex-ui/ts/app/resizer";

import { HorizontalResizer } from "scitex-ui/ts/app/resizer";
import { VerticalResizer } from "scitex-ui/ts/app/resizer";

let _autoInitDone = false;
const _initializedIds = new Set<string>();

/** Auto-initialize all horizontal resizers on the page */
function initHorizontalResizers(): number {
  let count = 0;
  const elements = document.querySelectorAll("[data-h-resizer]");
  console.log(`[Resizer] Found ${elements.length} [data-h-resizer] elements`);
  elements.forEach((el) => {
    const resizerEl = el as HTMLElement;
    if (!resizerEl.id) {
      resizerEl.id = `h-resizer-${count}`;
    }
    console.log(
      `[Resizer] Processing #${resizerEl.id} (already init: ${_initializedIds.has(resizerEl.id)})`,
    );
    if (_initializedIds.has(resizerEl.id)) return;

    const config = HorizontalResizer.configFromElement(resizerEl);
    if (!config) {
      console.warn(
        `[Resizer] #${resizerEl.id}: configFromElement returned null`,
      );
      return;
    }
    console.log(`[Resizer] #${resizerEl.id}: config=`, {
      left: config.left,
      right: config.right,
      isMostLeft: config.isMostLeft,
      isMostRight: config.isMostRight,
      thresholdPx: config.thresholdPx,
      isInApp: config.isInApp,
      storageKey: config.storageKey,
    });

    const leftEl = document.querySelector(config.left);
    const rightEl = document.querySelector(config.right);
    console.log(
      `[Resizer] #${resizerEl.id}: leftEl=${!!leftEl} (${config.left}), rightEl=${!!rightEl} (${config.right})`,
    );

    try {
      new HorizontalResizer(resizerEl, config);
      _initializedIds.add(resizerEl.id);
      count++;
      console.log(`[Resizer] #${resizerEl.id}: OK`);
    } catch (e) {
      console.warn(`[Resizer] #${resizerEl.id}: Failed to init horizontal:`, e);
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

  // Expose for inline scripts that need to re-init after tab switches
  (window as any).initNewResizers = initNewResizers;
}
