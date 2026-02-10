/**
 * Tools Panel - Three-column layout controller
 * Column 1: File tree (handled by auto-init)
 * Column 2: Tool navigation with search (always visible)
 * Column 3: Tool content via iframe (placeholder until tool selected)
 */

function getElements() {
  return {
    iframe: document.getElementById("tools-iframe") as HTMLIFrameElement | null,
    placeholder: document.getElementById("tools-placeholder"),
    searchInput: document.getElementById(
      "searchInput",
    ) as HTMLInputElement | null,
  };
}

// --- Tool loading ---
function loadTool(toolUrl: string, toolName: string): void {
  const el = getElements();
  if (!el.iframe) return;

  // Show iframe, hide placeholder
  el.placeholder?.setAttribute("hidden", "");
  el.iframe.removeAttribute("hidden");
  el.iframe.src = toolUrl;

  // Update active state in nav
  document.querySelectorAll(".tools-nav-item").forEach((item) => {
    item.classList.toggle(
      "active",
      (item as HTMLElement).dataset.toolUrl === toolUrl,
    );
  });

  // Update URL hash
  const slug = toolUrl.split("/tools/")[1]?.replace("/?embed=1", "") || "";
  if (slug) history.replaceState(null, "", `/tools/#${slug}`);
}

function closeTool(): void {
  const el = getElements();
  if (!el.iframe) return;

  el.iframe.setAttribute("hidden", "");
  el.iframe.src = "";
  el.placeholder?.removeAttribute("hidden");

  document
    .querySelectorAll(".tools-nav-item")
    .forEach((item) => item.classList.remove("active"));
  history.replaceState(null, "", "/tools/");
}

// --- Sidebar domain expand/collapse ---
function initDomainNav(): void {
  document.querySelectorAll(".tools-nav-domain-header").forEach((header) => {
    header.addEventListener("click", () => {
      const items = header.nextElementSibling as HTMLElement | null;
      if (!items) return;
      const isExpanded = header.classList.contains("expanded");
      header.classList.toggle("expanded", !isExpanded);
      items.classList.toggle("expanded", !isExpanded);
    });
  });
}

// --- Tool click handlers ---
function initToolClicks(): void {
  document.querySelectorAll(".tools-nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      e.preventDefault();
      const el = item as HTMLElement;
      const url = el.dataset.toolUrl;
      const name = el.dataset.toolName;
      if (url && name) loadTool(url, name);
    });
  });

  // No close button - tools nav handles switching
}

// --- Search (filters nav items) ---
function initSearch(): void {
  const searchInput = document.getElementById(
    "searchInput",
  ) as HTMLInputElement | null;
  if (!searchInput) return;

  searchInput.addEventListener("input", () => {
    const term = searchInput.value.toLowerCase().trim();

    document
      .querySelectorAll<HTMLElement>(".tools-nav-item")
      .forEach((item) => {
        const name = (item.dataset.toolName || "").toLowerCase();
        item.style.display =
          term === "" || name.includes(term) ? "flex" : "none";
      });

    // Hide domains with no visible items
    document
      .querySelectorAll<HTMLElement>(".tools-nav-domain")
      .forEach((dom) => {
        let hasVisible = false;
        dom.querySelectorAll<HTMLElement>(".tools-nav-item").forEach((item) => {
          if (item.style.display !== "none") hasVisible = true;
        });
        dom.style.display = term === "" || hasVisible ? "block" : "none";
      });
  });

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      searchInput.focus();
    }
    if (e.key === "Escape") {
      if (document.activeElement === searchInput) {
        searchInput.blur();
      } else {
        const el = getElements();
        if (el.iframe && !el.iframe.hasAttribute("hidden")) closeTool();
      }
    }
  });
}

// --- URL hash restore ---
function restoreFromHash(): void {
  const hash = window.location.hash.slice(1);
  if (!hash) return;
  const navItem = document.querySelector(
    `.tools-nav-item[data-tool-slug*="${hash}"]`,
  ) as HTMLElement | null;
  if (navItem) {
    const url = navItem.dataset.toolUrl;
    const name = navItem.dataset.toolName;
    if (url && name) loadTool(url, name);
  }
}

// --- Initialize ---
document.addEventListener("DOMContentLoaded", () => {
  initDomainNav();
  initToolClicks();
  initSearch();
  restoreFromHash();
});
