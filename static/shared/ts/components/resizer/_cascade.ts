/**
 * Domino cascade logic for frame-level horizontal resizers.
 *
 * When a panel collapses, remaining drag delta propagates to the next
 * adjacent panel in the same direction. Only applies to frame-level
 * resizers (isInApp=false).
 */

const COLLAPSE_WIDTH = 40;
const MIN_MODULE_WIDTH = 40;

/** Calculate the maximum width a panel can grow to */
export function getMaxAllowedWidth(panel: HTMLElement): number {
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
      reserved += child.offsetWidth;
    }
  }

  return containerWidth - reserved;
}

/** Cascade state tracked during a drag operation */
export interface CascadeTarget {
  panel: HTMLElement;
  storageKey: string;
  startWidth: number;
  startX: number;
  thresholdPx: number;
}

/**
 * Find the next non-collapsed resizable panel in the drag direction.
 * Walks through siblings, skipping collapsed or non-resizable panes.
 */
export function findAdjacentPanel(
  currentPanel: HTMLElement,
  direction: "left" | "right",
): { panel: HTMLElement; storageKey: string; thresholdPx: number } | null {
  const paneContainer = currentPanel.closest(
    ".ws-ai-pane, .ws-worktree-pane, .ws-viewer-pane, .ws-apps-pane, .ws-module-pane",
  );
  if (!paneContainer) return null;

  let current: Element | null = paneContainer;
  while (current) {
    const sibling =
      direction === "left"
        ? current.previousElementSibling
        : current.nextElementSibling;
    if (!sibling) return null;

    const siblingResizer = sibling.querySelector(
      "[data-h-resizer]",
    ) as HTMLElement;
    const siblingPanel = sibling.querySelector(
      ".stx-shell-sidebar",
    ) as HTMLElement;

    if (!siblingResizer || !siblingPanel) {
      current = sibling;
      continue;
    }

    if (siblingPanel.classList.contains("collapsed")) {
      current = sibling;
      continue;
    }

    return {
      panel: siblingPanel,
      storageKey: siblingResizer.dataset.storageKey || "",
      thresholdPx: parseInt(siblingResizer.dataset.threshold || "48", 10),
    };
  }

  return null;
}

/** Collapse a panel during cascade */
export function cascadeCollapse(panel: HTMLElement, storageKey: string): void {
  panel.classList.add("collapsed");
  panel.style.width = "";
  panel.style.flexShrink = "";
  panel.style.flexGrow = "";

  if (storageKey) {
    localStorage.setItem(storageKey + "-collapsed", "true");
  }
}
