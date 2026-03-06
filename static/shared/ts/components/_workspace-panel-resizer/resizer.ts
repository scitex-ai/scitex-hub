/** Drag-resize mouse event logic for WorkspacePanelResizer
 *
 * Features:
 * - Smart collapse: when panel is dragged below minWidth, it collapses instantly
 *   (not just on mouseUp)
 * - Curtain propagation: remaining drag delta transfers to the next adjacent panel
 *   in the same direction, so dragging one panel past collapse continues resizing
 *   the panel behind it
 * - Bidirectional: works in both left-to-right and right-to-left drag directions
 */

import type { PanelConfig } from "./types";
import { saveWidth, restoreWidth } from "./state";
import { updateToggleIcon } from "./toggle";
import { snapToNearest, percentSnapPoints } from "../resizer/_snap";

/** Shared collapse threshold — panel collapses when width drops to this */
const COLLAPSE_WIDTH = 40;

/** Minimum width the module pane (flex:1, no resizer) must retain.
 *  Matches COLLAPSE_WIDTH so the module pane can shrink to collapse threshold. */
const MIN_MODULE_WIDTH = 40;

/** Calculate the maximum width a panel can grow to without pushing siblings
 *  off-screen. Uses each sibling's ACTUAL current width (or MIN_MODULE_WIDTH
 *  for the module pane) so the cap reflects reality, not just minimums.
 */
function getMaxAllowedWidth(panel: HTMLElement): number {
  const paneEl =
    panel.closest(
      ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-apps-pane",
    ) || panel.parentElement;
  if (!paneEl) return Infinity;

  const flexContainer = paneEl.closest(".workspace-three-col") as HTMLElement;
  if (!flexContainer) return Infinity;

  const containerWidth = flexContainer.clientWidth;
  let reserved = 0;

  for (const child of Array.from(flexContainer.children) as HTMLElement[]) {
    if (child === paneEl) continue;
    if (child.classList.contains("ws-module-pane")) {
      reserved += MIN_MODULE_WIDTH;
    } else {
      // Use actual width — if collapsed, that's already COLLAPSE_WIDTH via CSS
      reserved += child.offsetWidth;
    }
  }

  return containerWidth - reserved;
}

/** Find the next non-collapsed resizable panel in the drag direction.
 *  Walks through siblings, skipping panes that are already collapsed or
 *  have no resizer (e.g., the module pane). This enables domino-style
 *  cascading through multiple panels.
 */
function findAdjacentPanel(
  config: PanelConfig,
  dragDirection: "shrink-left" | "shrink-right",
): { panel: HTMLElement; config: PanelConfig } | null {
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;
  if (!targetPanel) return null;

  const paneContainer = targetPanel.closest(
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-apps-pane, .ws-module-pane",
  );
  if (!paneContainer) return null;

  // Walk siblings until we find a non-collapsed resizable panel
  let current: Element | null = paneContainer;
  while (current) {
    const sibling =
      dragDirection === "shrink-left"
        ? current.previousElementSibling
        : current.nextElementSibling;
    if (!sibling) return null;

    const siblingResizer = sibling.querySelector(
      "[data-panel-resizer]",
    ) as HTMLElement;
    const siblingPanel = sibling.querySelector(
      ".workspace-sidebar",
    ) as HTMLElement;

    // Skip panes without resizer or panel (e.g., module pane)
    if (!siblingResizer || !siblingPanel) {
      current = sibling;
      continue;
    }

    // Skip already-collapsed panels (force passes through them)
    if (siblingPanel.classList.contains("collapsed")) {
      current = sibling;
      continue;
    }

    // Found a non-collapsed, resizable panel
    const sibConfig: PanelConfig = {
      resizerId: siblingResizer.id,
      targetPanel: `#${siblingPanel.id}`,
      minWidth: parseInt(siblingResizer.dataset.minWidth || "40", 10),
      storageKey: siblingResizer.dataset.storageKey || "",
      resizeDirection: (siblingResizer.dataset.direction || "left") as
        | "left"
        | "right",
      toggleButtonId: siblingResizer.dataset.toggleBtn,
      collapseStorageKey: siblingResizer.dataset.collapseKey,
      defaultWidth: siblingResizer.dataset.defaultWidth
        ? parseInt(siblingResizer.dataset.defaultWidth, 10)
        : undefined,
    };

    return { panel: siblingPanel, config: sibConfig };
  }

  return null;
}

/** Collapse a panel programmatically */
function collapsePanel(
  storagePrefix: string,
  config: PanelConfig,
  panel: HTMLElement,
): void {
  panel.classList.add("collapsed");
  panel.style.width = "";
  panel.style.flexShrink = "";
  panel.style.flexGrow = "";

  if (config.toggleButtonId) {
    const toggleBtn = document.getElementById(config.toggleButtonId);
    if (toggleBtn) updateToggleIcon(toggleBtn, config.resizeDirection, true);
  }

  if (config.collapseStorageKey) {
    localStorage.setItem(config.collapseStorageKey, "true");
  }
}

export function initResizer(storagePrefix: string, config: PanelConfig): void {
  const resizer = document.getElementById(config.resizerId);
  const targetPanel = document.querySelector(config.targetPanel) as HTMLElement;

  if (!resizer || !targetPanel) {
    console.warn(
      `[WorkspacePanelResizer] Missing elements for ${config.resizerId}`,
    );
    return;
  }

  restoreWidth(storagePrefix, config, targetPanel);

  let isResizing = false;
  let startX = 0;
  let startWidth = 0;
  let wasCollapsed = false;
  let primaryCollapsed = false; // true once primary panel collapses during drag
  let snapTimer: ReturnType<typeof setTimeout> | undefined;

  // Track propagation state: when the primary panel collapses during drag,
  // we start resizing the adjacent panel
  let propagationTarget: {
    panel: HTMLElement;
    config: PanelConfig;
    startWidth: number;
    startX: number;
  } | null = null;

  /** Disable CSS transitions on all workspace sidebars during drag */
  const disableTransitions = () => {
    document
      .querySelectorAll<HTMLElement>(".workspace-sidebar")
      .forEach((el) => {
        el.style.transition = "none";
      });
  };

  /** Re-enable CSS transitions after drag ends */
  const enableTransitions = () => {
    document
      .querySelectorAll<HTMLElement>(".workspace-sidebar")
      .forEach((el) => {
        el.style.transition = "";
      });
  };

  const handleMouseDown = (e: MouseEvent) => {
    wasCollapsed = targetPanel.classList.contains("collapsed");
    propagationTarget = null;
    primaryCollapsed = false;

    // Fixed-width panels skip collapse/expand — go straight to propagation
    if (config.fixedWidth) {
      isResizing = true;
      startX = e.clientX;
      startWidth = targetPanel.offsetWidth;
      primaryCollapsed = true; // skip primary resize entirely

      // Find adjacent panel to propagate to based on drag direction
      // We'll determine actual direction in mousemove
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
      resizer.classList.add("active");
      disableTransitions();
      e.preventDefault();
      return;
    }

    if (wasCollapsed) {
      targetPanel.classList.remove("collapsed");
      targetPanel.style.width = `${config.minWidth}px`;
      targetPanel.style.flexShrink = "0";
      targetPanel.style.flexGrow = "0";

      if (config.toggleButtonId) {
        const toggleBtn = document.getElementById(config.toggleButtonId);
        if (toggleBtn)
          updateToggleIcon(toggleBtn, config.resizeDirection, false);
      }

      if (config.collapseStorageKey)
        localStorage.setItem(config.collapseStorageKey, "false");
    }

    isResizing = true;
    startX = e.clientX;
    startWidth = targetPanel.offsetWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    resizer.classList.add("active");
    targetPanel.dataset.wprDragging = "true";
    disableTransitions();
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!isResizing) return;

    // Fixed-width panel: propagate to adjacent panel based on drag direction
    if (config.fixedWidth && !propagationTarget) {
      const delta = e.clientX - startX;
      if (Math.abs(delta) < 3) return; // dead zone
      const dragDir = delta < 0 ? "shrink-left" : "shrink-right";
      const adjacent = findAdjacentPanel(config, dragDir);
      if (adjacent) {
        propagationTarget = {
          panel: adjacent.panel,
          config: adjacent.config,
          startWidth: adjacent.panel.offsetWidth,
          startX: e.clientX,
        };
      }
      return;
    }

    // Once the primary panel has collapsed, only handle propagation
    if (primaryCollapsed && !propagationTarget) return;

    // If we're in propagation mode, resize the adjacent panel instead
    if (propagationTarget) {
      const propDelta = e.clientX - propagationTarget.startX;
      let propNewWidth =
        config.resizeDirection === "left"
          ? propagationTarget.startWidth + propDelta
          : propagationTarget.startWidth - propDelta;

      // Cap propagation target so it doesn't push siblings off-screen
      const propMax = getMaxAllowedWidth(propagationTarget.panel);
      if (propNewWidth > propMax) propNewWidth = propMax;

      // Snap propagation target to percentage points
      const propFlex = propagationTarget.panel.closest(
        ".workspace-three-col",
      ) as HTMLElement;
      if (propFlex) {
        const propSnaps = percentSnapPoints(propFlex.clientWidth);
        propNewWidth = snapToNearest(propNewWidth, propSnaps);
      }

      if (propNewWidth < COLLAPSE_WIDTH) {
        // Collapse propagation target too, then try next panel
        collapsePanel(
          storagePrefix,
          propagationTarget.config,
          propagationTarget.panel,
        );

        // Try to propagate further (domino cascade)
        const dragDir =
          config.resizeDirection === "left" ? "shrink-left" : "shrink-right";
        const next = findAdjacentPanel(propagationTarget.config, dragDir);
        if (next) {
          propagationTarget = {
            panel: next.panel,
            config: next.config,
            startWidth: next.panel.offsetWidth,
            startX: e.clientX,
          };
        } else {
          propagationTarget = null;
        }
        return;
      }

      propagationTarget.panel.style.width = `${propNewWidth}px`;
      propagationTarget.panel.style.flexShrink = "0";
      propagationTarget.panel.style.flexGrow = "0";
      return;
    }

    // Normal resize of the primary panel
    const delta = e.clientX - startX;
    let newWidth =
      config.resizeDirection === "left"
        ? startWidth + delta
        : startWidth - delta;

    // Cap width so siblings always fit on screen
    const maxWidth = getMaxAllowedWidth(targetPanel);
    if (newWidth > maxWidth) newWidth = maxWidth;

    // Snap to percentage-based points
    const rawWidth = newWidth;
    const flexContainer = targetPanel.closest(
      ".workspace-three-col",
    ) as HTMLElement;
    if (flexContainer) {
      const snaps = percentSnapPoints(flexContainer.clientWidth);
      newWidth = snapToNearest(newWidth, snaps);
    }
    // Flash resizer when snap engages
    if (newWidth !== rawWidth) {
      resizer.classList.add("snapped");
      clearTimeout(snapTimer);
      snapTimer = setTimeout(() => resizer.classList.remove("snapped"), 150);
    }

    // Smart collapse: if dragged below threshold, collapse and propagate
    if (newWidth < COLLAPSE_WIDTH) {
      primaryCollapsed = true;
      collapsePanel(storagePrefix, config, targetPanel);

      // Start propagation to adjacent panel (domino cascade)
      const dragDir =
        config.resizeDirection === "left" ? "shrink-left" : "shrink-right";
      const adjacent = findAdjacentPanel(config, dragDir);
      if (adjacent) {
        propagationTarget = {
          panel: adjacent.panel,
          config: adjacent.config,
          startWidth: adjacent.panel.offsetWidth,
          startX: e.clientX,
        };
      }
      return;
    }

    targetPanel.style.width = `${newWidth}px`;
    targetPanel.style.flexShrink = "0";
    targetPanel.style.flexGrow = "0";
  };

  const handleMouseUp = () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    resizer.classList.remove("active");
    enableTransitions();

    // Clear drag flag after click event has been processed (rAF delay)
    requestAnimationFrame(() => {
      delete targetPanel.dataset.wprDragging;
    });

    // Save propagation target width if we were propagating
    if (propagationTarget) {
      const propWidth = propagationTarget.panel.offsetWidth;
      if (propWidth > COLLAPSE_WIDTH + 10) {
        saveWidth(storagePrefix, propagationTarget.config, propWidth);
      }
      propagationTarget = null;
    }

    // If primary panel is already collapsed (from smart collapse during drag), done
    if (targetPanel.classList.contains("collapsed")) {
      wasCollapsed = false;
      return;
    }

    const finalWidth = targetPanel.offsetWidth;

    // Threshold-based collapse on mouseUp (backup for edge cases)
    if (finalWidth <= config.minWidth + 10) {
      collapsePanel(storagePrefix, config, targetPanel);
    } else {
      saveWidth(storagePrefix, config, finalWidth);
    }

    wasCollapsed = false;
  };

  resizer.addEventListener("mousedown", handleMouseDown);
  document.addEventListener("mousemove", handleMouseMove);
  document.addEventListener("mouseup", handleMouseUp);

  console.log(
    `[WorkspacePanelResizer] Initialized ${config.resizerId} (direction: ${config.resizeDirection})`,
  );
}
