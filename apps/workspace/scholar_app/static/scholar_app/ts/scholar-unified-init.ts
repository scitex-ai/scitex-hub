/**
 * Scholar Unified Page Initializer
 *
 * Handles tab switching and inline panel toggle/restore logic
 * for the scholar_unified.html template.
 *
 * Listens for workspace:module-injected for AJAX injection contexts.
 *
 * @module scholar-unified-init
 */

const TAB_ORDER = ["library", "search", "bibtex", "graph"];
const DEFAULT_TAB = "library";
const PANEL_STORAGE_KEY = "scholar-panel-states";

function getActiveTab(): string {
  const hash = window.location.hash.slice(1);
  return TAB_ORDER.includes(hash) ? hash : DEFAULT_TAB;
}

function switchTab(tabName: string): void {
  console.log("[Scholar] Switching to tab:", tabName);

  // Update tab navigation
  document.querySelectorAll(".scholar-tab").forEach((tab) => {
    const el = tab as HTMLElement;
    el.classList.toggle("active", el.dataset.tab === tabName);
  });

  // Update main content
  let foundContent = false;
  document.querySelectorAll(".scholar-tab-content").forEach((content) => {
    const el = content as HTMLElement;
    const isActive = el.dataset.tab === tabName;
    el.classList.toggle("active", isActive);
    if (isActive) {
      foundContent = true;
      console.log("[Scholar] Activated content for:", tabName, el);
    }
  });

  if (!foundContent) {
    console.warn("[Scholar] No content found for tab:", tabName);
  }

  // Update details panel
  document.querySelectorAll(".scholar-details-content").forEach((content) => {
    const el = content as HTMLElement;
    el.classList.toggle("active", el.dataset.tab === tabName);
  });

  // Trigger resize after layout is applied (rAF ensures CSS computed)
  requestAnimationFrame(function () {
    window.dispatchEvent(new Event("resize"));
    if (typeof (window as any).initNewResizers === "function") {
      (window as any).initNewResizers();
    }
  });
}

function initTabSwitching(): void {
  document.querySelectorAll(".scholar-tab").forEach((tab) => {
    tab.addEventListener("click", function (this: HTMLElement, e: Event) {
      e.preventDefault();
      const tabName = this.dataset.tab;
      if (!tabName) return;
      window.location.hash = tabName;
      switchTab(tabName);
    });
  });

  window.addEventListener("hashchange", function () {
    switchTab(getActiveTab());
  });

  if (!window.location.hash) {
    window.location.hash = DEFAULT_TAB;
  }
  switchTab(getActiveTab());
}

function initInlinePanelToggle(): void {
  (window as any)._toggleInlinePanel = function (headerEl: HTMLElement): void {
    const panel = headerEl.closest(
      ".sidebar-section, .bibtex-tile, .mig-card",
    ) as HTMLElement | null;
    if (!panel) return;
    const panelId = panel.dataset.panelId;

    if (panel.classList.contains("sidebar-section")) {
      panel.classList.toggle("collapsed");
    } else if (panel.classList.contains("bibtex-tile")) {
      panel.classList.toggle("bibtex-tile--expanded");
    } else if (panel.classList.contains("mig-card")) {
      panel.classList.toggle("collapsed");
    }

    if (panelId) {
      const isOpen =
        !panel.classList.contains("collapsed") &&
        (panel.classList.contains("bibtex-tile--expanded") ||
          !panel.classList.contains("bibtex-tile"));
      try {
        const stored = JSON.parse(
          localStorage.getItem(PANEL_STORAGE_KEY) || "{}",
        );
        stored[panelId] = isOpen;
        localStorage.setItem(PANEL_STORAGE_KEY, JSON.stringify(stored));
      } catch (_e) {
        // ignore localStorage errors
      }
    }
  };
}

function restorePanelStates(): void {
  try {
    const stored = JSON.parse(localStorage.getItem(PANEL_STORAGE_KEY) || "{}");
    Object.keys(stored).forEach(function (id) {
      const panel = document.querySelector(
        `[data-panel-id="${id}"]`,
      ) as HTMLElement | null;
      if (!panel) return;
      const isOpen = stored[id];

      if (panel.classList.contains("sidebar-section")) {
        panel.classList.toggle("collapsed", !isOpen);
      } else if (panel.classList.contains("bibtex-tile")) {
        panel.classList.toggle("bibtex-tile--expanded", isOpen);
      } else if (panel.classList.contains("mig-card")) {
        panel.classList.toggle("collapsed", !isOpen);
      }
    });
  } catch (_e) {
    // ignore localStorage errors
  }
}

function initScholarUnified(): void {
  initTabSwitching();
  initInlinePanelToggle();
  restorePanelStates();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initScholarUnified);
} else {
  initScholarUnified();
}

// Re-initialize when module is injected via AJAX
window.addEventListener("workspace:module-injected", initScholarUnified);

export { switchTab, getActiveTab, TAB_ORDER, DEFAULT_TAB };
