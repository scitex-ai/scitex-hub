/**
 * Vis Panel Toggle - Binary toggle for data/canvas panes
 *
 * Ensures only one of data/canvas panes can be collapsed at a time.
 * When one is collapsed and the other gets collapsed, the first one opens.
 * Uses capture-phase event listeners to intercept before HorizontalResizer.
 */

/**
 * Clear inline width/flex styles so CSS classes take effect.
 * HorizontalResizer sets inline styles that override CSS rules.
 */
function clearInlineStyles(panel: HTMLElement): void {
  panel.style.width = "";
  panel.style.flex = "";
  panel.style.flexShrink = "";
  panel.style.flexGrow = "";
}

/**
 * Toggle a vis pane with binary constraint.
 * When collapsing one, the other must be open.
 */
function toggleVisPane(panelType: "data" | "canvas"): void {
  const dataPane = document.getElementById("data-pane");
  const canvasPane = document.getElementById("canvas-pane");
  const splitResizer = document.getElementById("split-resizer");

  if (!dataPane || !canvasPane) return;

  const targetPanel = panelType === "data" ? dataPane : canvasPane;
  const otherPanel = panelType === "data" ? canvasPane : dataPane;
  const wasCollapsed = targetPanel.classList.contains("collapsed");

  if (wasCollapsed) {
    // Expanding: return both panels to normal
    targetPanel.classList.remove("collapsed");
    clearInlineStyles(targetPanel);
    clearInlineStyles(otherPanel);
  } else {
    // Collapsing this panel: ensure the other is open
    targetPanel.classList.add("collapsed");
    otherPanel.classList.remove("collapsed");
    clearInlineStyles(targetPanel);
    clearInlineStyles(otherPanel);
  }

  // Update resizer visibility
  if (splitResizer) {
    const anyCollapsed =
      dataPane.classList.contains("collapsed") ||
      canvasPane.classList.contains("collapsed");
    splitResizer.style.display = anyCollapsed ? "none" : "";
  }

  updateToggleIcons();
  saveState();

  // Trigger resize for canvas redraw after CSS transition
  setTimeout(() => window.dispatchEvent(new Event("resize")), 350);

  console.log(
    `[VisPanelToggle] ${panelType}: ${wasCollapsed ? "expanded" : "collapsed"}`,
  );
}

function updateToggleIcons(): void {
  const dataPane = document.getElementById("data-pane");
  const canvasPane = document.getElementById("canvas-pane");
  const dataToggle = document.getElementById("data-pane-toggle");
  const canvasToggle = document.getElementById("canvas-pane-toggle");

  if (dataToggle && dataPane) {
    const icon = dataToggle.querySelector("i");
    if (icon) {
      const collapsed = dataPane.classList.contains("collapsed");
      icon.className = collapsed
        ? "fas fa-chevron-right"
        : "fas fa-chevron-left";
    }
  }

  if (canvasToggle && canvasPane) {
    const icon = canvasToggle.querySelector("i");
    if (icon) {
      const collapsed = canvasPane.classList.contains("collapsed");
      icon.className = collapsed
        ? "fas fa-chevron-left"
        : "fas fa-chevron-right";
    }
  }
}

function saveState(): void {
  const dataPane = document.getElementById("data-pane");
  const canvasPane = document.getElementById("canvas-pane");
  if (!dataPane || !canvasPane) return;

  localStorage.setItem(
    "data-pane-collapsed",
    dataPane.classList.contains("collapsed").toString(),
  );
  localStorage.setItem(
    "canvas-pane-collapsed",
    canvasPane.classList.contains("collapsed").toString(),
  );
}

/**
 * Restore state with binary constraint enforcement.
 * If both were somehow saved as collapsed, only keep the latest.
 */
function restoreState(): void {
  const dataPane = document.getElementById("data-pane");
  const canvasPane = document.getElementById("canvas-pane");
  const splitResizer = document.getElementById("split-resizer");

  if (!dataPane || !canvasPane) return;

  const dataCollapsed = localStorage.getItem("data-pane-collapsed") === "true";
  const canvasCollapsed =
    localStorage.getItem("canvas-pane-collapsed") === "true";

  // Enforce binary constraint
  if (dataCollapsed && canvasCollapsed) {
    // Both collapsed - open data, keep canvas collapsed
    canvasPane.classList.add("collapsed");
    dataPane.classList.remove("collapsed");
    clearInlineStyles(dataPane);
    clearInlineStyles(canvasPane);
    localStorage.setItem("data-pane-collapsed", "false");
  } else if (dataCollapsed) {
    dataPane.classList.add("collapsed");
    clearInlineStyles(dataPane);
    clearInlineStyles(canvasPane);
  } else if (canvasCollapsed) {
    canvasPane.classList.add("collapsed");
    clearInlineStyles(dataPane);
    clearInlineStyles(canvasPane);
  }

  // Update resizer visibility
  if (splitResizer) {
    const anyCollapsed =
      dataPane.classList.contains("collapsed") ||
      canvasPane.classList.contains("collapsed");
    splitResizer.style.display = anyCollapsed ? "none" : "";
  }

  updateToggleIcons();
}

function init(): void {
  const dataToggle = document.getElementById("data-pane-toggle");
  const canvasToggle = document.getElementById("canvas-pane-toggle");

  // Use capture phase to intercept before HorizontalResizer's bubble handler
  dataToggle?.addEventListener(
    "click",
    (e) => {
      e.stopImmediatePropagation();
      e.preventDefault();
      toggleVisPane("data");
    },
    true,
  );

  canvasToggle?.addEventListener(
    "click",
    (e) => {
      e.stopImmediatePropagation();
      e.preventDefault();
      toggleVisPane("canvas");
    },
    true,
  );

  // Restore state (may override HorizontalResizer's independent restore)
  restoreState();

  console.log(
    "[VisPanelToggle] Initialized binary toggle for data/canvas panes",
  );
}

// Auto-initialize
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}

export { toggleVisPane, init as initVisPanelToggle };
