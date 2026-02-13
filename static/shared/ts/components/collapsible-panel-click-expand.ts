/**
 * Collapsible Panel Interactions
 * - Click anywhere on a collapsed panel to expand
 * - Double-click empty header space to collapse an expanded panel
 * Handles .collapsible-panel, .workspace-sidebar, and right-side panels.
 * Delegates to existing toggle button click handlers.
 */

/* Any panel that can be collapsed and has a toggle button */
const COLLAPSED_SELECTORS = [
  ".collapsible-panel.collapsed",
  ".workspace-sidebar.collapsed",
].join(", ");

const PANEL_SELECTORS = [".collapsible-panel", ".workspace-sidebar"].join(", ");

const TOGGLE_SELECTORS =
  ".panel-toggle-btn, .sidebar-toggle, .sidebar-toggle-btn";

const HEADER_SELECTORS = [
  ".panel-header",
  ".sidebar-header",
  ".tools-nav-header",
  ".details-header",
  ".properties-header",
  ".terminal-panel-top",
  ".pane-header",
].join(", ");

function findToggleBtn(panel: Element): HTMLElement | null {
  return panel.querySelector(TOGGLE_SELECTORS) as HTMLElement;
}

function updateTooltips(panel: Element): void {
  const isCollapsed = panel.matches(".collapsed");
  const header = panel.querySelector(HEADER_SELECTORS);

  if (isCollapsed) {
    panel.setAttribute("data-tooltip", "Click to expand");
    if (header) header.removeAttribute("data-tooltip");
  } else {
    panel.removeAttribute("data-tooltip");
    if (header) header.setAttribute("data-tooltip", "Double-click to collapse");
  }
}

function initPanelInteractions(): void {
  // Track when click-to-expand fires to prevent dblclick race condition:
  // Without this, double-clicking a collapsed panel would expand (click)
  // then immediately collapse (dblclick), creating a flash with no net change.
  let lastExpandTime = 0;

  // Click on collapsed panel → expand
  document.addEventListener("click", (e) => {
    const target = e.target as HTMLElement;
    const panel = target.closest(COLLAPSED_SELECTORS);
    if (!panel) return;

    const toggleBtn = findToggleBtn(panel);
    if (toggleBtn && target !== toggleBtn && !toggleBtn.contains(target)) {
      lastExpandTime = Date.now();
      toggleBtn.click();
    }
  });

  // Set initial tooltips and watch for state changes
  document.querySelectorAll(PANEL_SELECTORS).forEach(updateTooltips);
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.attributeName === "class") updateTooltips(m.target as Element);
    }
  });
  document.querySelectorAll(PANEL_SELECTORS).forEach((panel) => {
    observer.observe(panel, { attributes: true, attributeFilter: ["class"] });
  });

  // Double-click on expanded panel header → collapse
  document.addEventListener("dblclick", (e) => {
    // Skip if a click-to-expand just fired (prevents expand→collapse flash)
    if (Date.now() - lastExpandTime < 500) return;

    const target = e.target as HTMLElement;
    const header = target.closest(HEADER_SELECTORS);
    if (!header) return;

    // Don't trigger on buttons or interactive elements
    if (target.closest("button, a, input, select, textarea")) return;

    const panel = header.closest(PANEL_SELECTORS);
    if (!panel || panel.matches(".collapsed")) return;

    const toggleBtn = findToggleBtn(panel);
    if (toggleBtn) {
      toggleBtn.click();
    }
  });
}

// Auto-initialize
if (typeof document !== "undefined") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPanelInteractions);
  } else {
    initPanelInteractions();
  }
}

export { initPanelInteractions };
