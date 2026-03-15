/**
 * Workspace Panel Resizer
 * Unified resizable panel management for Code, Vis, Writer, and Scholar workspaces.
 *
 * Usage (HTML data attributes - recommended):
 * ```html
 * <div class="panel-resizer"
 *      data-panel-resizer
 *      data-target=".sidebar"
 *      data-direction="left"
 *      data-min-width="40"
 *      data-default-width="250"
 *      data-storage-key="sidebar-width"
 *      data-collapse-key="sidebar-collapsed"
 *      data-toggle-btn="stx-shell-sidebar__toggle">
 * </div>
 * ```
 */

export type { PanelConfig } from "./types";
import type { PanelConfig } from "./types";
import { restoreCollapseState } from "./state";
import { updateToggleIcon, initToggleClickHandler } from "./toggle";
import { initResizer } from "./resizer";

export class WorkspacePanelResizer {
  storagePrefix: string;
  private panels: Map<string, PanelConfig> = new Map();

  constructor(storagePrefix: string = "scitex-panel-") {
    this.storagePrefix = storagePrefix;
  }

  public initResizer(config: PanelConfig): void {
    this.panels.set(config.resizerId, config);
    initResizer(this.storagePrefix, config);
  }

  public initToggle(config: PanelConfig): void {
    if (!config.toggleButtonId) return;
    const toggleBtn = document.getElementById(config.toggleButtonId);
    const targetPanel = document.querySelector(
      config.targetPanel,
    ) as HTMLElement;
    if (!toggleBtn || !targetPanel) {
      console.warn(
        `[WorkspacePanelResizer] Missing toggle elements for ${config.toggleButtonId}`,
      );
      return;
    }
    restoreCollapseState(config, targetPanel, toggleBtn, updateToggleIcon);
    initToggleClickHandler(this.storagePrefix, config);
  }

  public updateToggleIcon(
    toggleBtn: HTMLElement,
    direction: "left" | "right",
    isCollapsed: boolean,
  ): void {
    updateToggleIcon(toggleBtn, direction, isCollapsed);
  }

  public initPanel(config: PanelConfig): void {
    const targetPanel = document.querySelector(
      config.targetPanel,
    ) as HTMLElement;
    const toggleBtn = config.toggleButtonId
      ? document.getElementById(config.toggleButtonId)
      : null;

    if (targetPanel) {
      targetPanel.style.transition = "none";
      void targetPanel.offsetWidth;
    }

    if (targetPanel && config.collapseStorageKey) {
      restoreCollapseState(config, targetPanel, toggleBtn, updateToggleIcon);
    }

    this.initResizer(config);
    initToggleClickHandler(this.storagePrefix, config);

    if (targetPanel) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          targetPanel.style.transition = "";
        });
      });
    }
  }
}

export const workspacePanelResizer = new WorkspacePanelResizer();

let _autoInitDone = false;
const _initializedIds = new Set<string>();

/** Build a PanelConfig from a resizer element's data attributes */
function configFromElement(resizer: HTMLElement): PanelConfig | null {
  const config: PanelConfig = {
    resizerId: resizer.id,
    targetPanel: resizer.dataset.target || "",
    minWidth: parseInt(resizer.dataset.minWidth || "40", 10),
    storageKey: resizer.dataset.storageKey || "panel-width",
    resizeDirection: (resizer.dataset.direction || "left") as "left" | "right",
    toggleButtonId: resizer.dataset.toggleBtn,
    collapseStorageKey: resizer.dataset.collapseKey,
    defaultWidth: resizer.dataset.defaultWidth
      ? parseInt(resizer.dataset.defaultWidth, 10)
      : undefined,
    fixedWidth: resizer.hasAttribute("data-fixed-width"),
  };

  if (!config.targetPanel) {
    console.warn("[WorkspacePanelResizer] Missing data-target on", resizer);
    return null;
  }
  return config;
}

export function autoInitPanels(): void {
  if (_autoInitDone) {
    console.log(
      "[WorkspacePanelResizer] autoInitPanels already done, skipping duplicate call.",
    );
    return;
  }
  _autoInitDone = true;
  const resizers = document.querySelectorAll("[data-panel-resizer]");

  document.body.classList.add("no-transition");

  resizers.forEach((el) => {
    const resizer = el as HTMLElement;
    const storagePrefix = resizer.dataset.storagePrefix || "scitex-";
    const instance = new WorkspacePanelResizer(storagePrefix);

    const config = configFromElement(resizer);
    if (!config) return;

    instance.initPanel(config);
    _initializedIds.add(resizer.id);
  });

  console.log(
    `[WorkspacePanelResizer] Auto-initialized ${resizers.length} panel(s)`,
  );

  // Smart collapse for the module pane (no resizer of its own — flex:1 fills remaining space).
  // When other panels expand and squeeze the module pane below threshold, collapse it.
  const modulePane = document.querySelector<HTMLElement>(".ws-module-pane");
  if (modulePane) {
    const MODULE_COLLAPSE_THRESHOLD = 80;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width;
        if (w < MODULE_COLLAPSE_THRESHOLD) {
          modulePane.classList.add("collapsed");
        } else {
          modulePane.classList.remove("collapsed");
        }
      }
    });
    ro.observe(modulePane);
  }

  // Mark panels as ready (makes them visible via CSS) and remove no-transition guard.
  // Double-rAF ensures all width changes have been painted before transitions re-enable.
  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      document
        .querySelectorAll(".workspace-three-col, .workspace-shell")
        .forEach((el) => el.classList.add("panels-ready"));
      document.body.classList.remove("no-transition");
    });
  });
}

/**
 * Initialize any [data-panel-resizer] elements that were added after autoInitPanels.
 * Called automatically on htmx:afterSettle for HTMX-injected content.
 */
export function initNewPanels(): void {
  const resizers = document.querySelectorAll("[data-panel-resizer]");
  let count = 0;

  document.body.classList.add("no-transition");

  resizers.forEach((el) => {
    const resizer = el as HTMLElement;
    if (!resizer.id || _initializedIds.has(resizer.id)) return;

    const storagePrefix = resizer.dataset.storagePrefix || "scitex-";
    const instance = new WorkspacePanelResizer(storagePrefix);

    const config = configFromElement(resizer);
    if (!config) return;

    instance.initPanel(config);
    _initializedIds.add(resizer.id);
    count++;
  });

  if (count > 0) {
    console.log(
      `[WorkspacePanelResizer] Late-initialized ${count} new panel(s)`,
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

if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", autoInitPanels);
  } else {
    autoInitPanels();
  }

  // Re-initialize panels after HTMX content swaps (e.g., writer loaded as partial)
  document.addEventListener("htmx:afterSettle", () => {
    initNewPanels();
  });
}
