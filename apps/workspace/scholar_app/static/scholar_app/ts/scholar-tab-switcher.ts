/**
 * Scholar Tab Switcher
 * Handles tab navigation and content switching for the Scholar unified page.
 * Works in both standalone mode and AJAX-injected unified workspace.
 */

const TAB_ORDER = ["library", "search", "bibtex", "graph"];
const DEFAULT_TAB = "library";

function isInUnifiedWorkspace(): boolean {
  return !!document.getElementById("unified-center");
}

function getActiveTab(): string {
  if (isInUnifiedWorkspace()) return DEFAULT_TAB;
  const hash = window.location.hash.slice(1);
  return TAB_ORDER.includes(hash) ? hash : DEFAULT_TAB;
}

function switchTab(tabName: string): void {
  document.querySelectorAll(".scholar-tab").forEach((tab) => {
    (tab as HTMLElement).classList.toggle(
      "active",
      (tab as HTMLElement).dataset.tab === tabName,
    );
  });
  document.querySelectorAll(".scholar-tab-content").forEach((content) => {
    (content as HTMLElement).classList.toggle(
      "active",
      (content as HTMLElement).dataset.tab === tabName,
    );
  });
  document.querySelectorAll(".scholar-details-content").forEach((content) => {
    (content as HTMLElement).classList.toggle(
      "active",
      (content as HTMLElement).dataset.tab === tabName,
    );
  });
  window.dispatchEvent(new Event("resize"));
}

function initTabSwitcher(): void {
  document.querySelectorAll(".scholar-tab").forEach((tab) => {
    tab.addEventListener("click", function (this: HTMLElement, e: Event) {
      e.preventDefault();
      const tabName = this.dataset.tab;
      if (!tabName) return;
      if (!isInUnifiedWorkspace()) window.location.hash = tabName;
      switchTab(tabName);
    });
  });

  if (!isInUnifiedWorkspace()) {
    window.addEventListener("hashchange", () => switchTab(getActiveTab()));
  }

  switchTab(getActiveTab());
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTabSwitcher);
} else {
  initTabSwitcher();
}

// Re-initialize after AJAX partial injection into unified workspace
document.addEventListener("workspace:module-injected", (e) => {
  if ((e as CustomEvent).detail?.module === "scholar") {
    initTabSwitcher();
  }
});

export { switchTab, getActiveTab, TAB_ORDER, DEFAULT_TAB };
