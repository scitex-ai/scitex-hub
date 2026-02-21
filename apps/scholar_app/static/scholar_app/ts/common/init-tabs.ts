/**

 * Tab Initialization and Management for Scholar App
 * Handles vertical tab switching between BibTeX and Search tabs
 */

console.log(
  "[DEBUG] apps/scholar_app/static/scholar_app/ts/common/init-tabs.ts loaded",
);
function initTabs(): void {
  const tabLinks: NodeListOf<Element> = document.querySelectorAll(".tab-link");
  const tabContents: NodeListOf<Element> = document.querySelectorAll(
    ".vertical-tab-content",
  );

  // Function to switch tabs smoothly
  function switchTab(targetTab: string): void {
    // Remove active class from all tabs and contents
    tabLinks.forEach((link: Element): void => {
      link.classList.remove("active");
      link.classList.remove("scitex-tab-active");
    });
    tabContents.forEach((content: Element): void =>
      content.classList.remove("active"),
    );

    // Add active class to target tab and content
    const targetLink: Element | null = document.querySelector(
      `.tab-link[data-tab="${targetTab}"]`,
    );
    const targetContent: HTMLElement | null = document.getElementById(
      `${targetTab}-tab`,
    );

    if (targetLink) {
      targetLink.classList.add("active");
      targetLink.classList.add("scitex-tab-active");
    }
    if (targetContent) {
      targetContent.classList.add("active");
    }

    // Focus search input when switching to search tab
    if (targetTab === "search") {
      setTimeout((): void => {
        const searchInput = document.querySelector<HTMLInputElement>(
          '#search-tab input[name="q"]',
        );
        if (searchInput) {
          searchInput.focus();
          console.log("[Tab Switcher] Focused search input");
        }
      }, 100); // Small delay to ensure tab is visible
    }

    console.log("[Tab Switcher] Switched to:", targetTab);
  }

  // Handle hash changes (browser back/forward, direct hash navigation)
  window.addEventListener("hashchange", (): void => {
    const hash: string = window.location.hash.substring(1); // Remove the '#'
    if (hash === "bibtex" || hash === "search") {
      switchTab(hash);
    }
  });

  // Initialize correct tab based on hash, query params, or default
  function initializeTab(): void {
    const hash: string = window.location.hash.substring(1);
    const urlParams: URLSearchParams = new URLSearchParams(
      window.location.search,
    );
    const hasSearchQuery: boolean =
      urlParams.get("q") !== null && urlParams.get("q")!.trim() !== "";

    let initialTab: string = "search"; // Default tab

    // Priority 1: If there's a search query, always show search tab
    if (hasSearchQuery) {
      initialTab = "search";
    }
    // Priority 2: Use hash if valid
    else if (hash === "search" || hash === "bibtex") {
      initialTab = hash;
    }
    // Priority 3: Use Django template context (will be replaced by template engine)
    // Note: This is a Django template variable that will be replaced at runtime
    // @ts-ignore - Django template variable
    else if (typeof active_tab !== "undefined" && active_tab !== "") {
      // @ts-ignore - Django template variable
      initialTab = active_tab;
    }

    // Update hash to match the tab
    window.location.hash = initialTab;

    switchTab(initialTab);
  }

  initializeTab();

  // Enable Enter key to submit search form
  const searchInput: HTMLInputElement | null = document.querySelector(
    '#search-tab input[name="q"]',
  );
  const searchForm: HTMLFormElement | null = document.getElementById(
    "literatureSearchForm",
  ) as HTMLFormElement | null;

  if (searchInput && searchForm) {
    searchInput.addEventListener("keypress", (e: KeyboardEvent): void => {
      if (e.key === "Enter") {
        e.preventDefault();
        searchForm.submit();
        console.log("[Search] Form submitted via Enter key");
      }
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", function () {
    initTabs();
  });
} else {
  initTabs();
}
