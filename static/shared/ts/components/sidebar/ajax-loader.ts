/**
 * AJAX Page Loader — loads pages into a container without full reload.
 * Uses X-Workspace-Shell: 1 header so Django views return partials.
 *
 * NOTE: Core logic extracted to scitex-ui AjaxLoader class.
 * This file provides scitex-hub-specific initialization.
 */

/** Init collapsible category headers in loaded content */
function initCategoryToggles(container: HTMLElement): void {
  container
    .querySelectorAll<HTMLElement>(".ai-setup-category__header")
    .forEach((header) => {
      header.addEventListener("click", () => {
        header.parentElement?.classList.toggle("open");
      });
    });
  // Auto-open first category
  const first = container.querySelector(".ai-setup-category");
  first?.classList.add("open");
}

/** Initialize delegated click handler for [data-ajax-load] links */
export function initAjaxLinks(): void {
  // Init any categories already in the DOM
  const existing = document.getElementById("ai-setup-content");
  if (existing) initCategoryToggles(existing);
  document.addEventListener("click", (e) => {
    const link = (e.target as HTMLElement).closest<HTMLElement>(
      "[data-ajax-load]",
    );
    if (!link) return;

    e.preventDefault();
    const url = link.getAttribute("data-ajax-load");
    if (!url) return;

    // Highlight active nav item in Miller columns col 1
    const col = link.closest(".stx-app-miller__col");
    if (col) {
      col
        .querySelectorAll(".stx-app-miller__item")
        .forEach((el) => el.classList.remove("stx-app-miller__item--active"));
      link.classList.add("stx-app-miller__item--active");
    }

    void loadPageContent(url);
  });
}

/** Fetch a page via AJAX and inject its content */
export async function loadPageContent(url: string): Promise<void> {
  const pane =
    document.getElementById("ai-setup-content") ||
    document.getElementById("main-content");
  if (!pane) return;

  // Clear detail column (col 3) when loading new section content
  const detailCol = document.getElementById("ai-setup-detail-col");
  if (detailCol) {
    detailCol.innerHTML =
      '<div class="stx-app-miller__detail-empty">Select an item to view details</div>';
  }

  // Show loading spinner
  pane.innerHTML =
    '<div class="ai-setup-loading"><i class="fas fa-spinner fa-spin"></i> Loading...</div>';

  try {
    const resp = await fetch(url, {
      headers: { "X-Workspace-Shell": "1" },
      credentials: "same-origin",
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const html = await resp.text();

    // Partial response (no <html>) — inject directly
    if (!html.includes("<!DOCTYPE") && !html.includes("<html")) {
      pane.innerHTML = html;
    } else {
      // Extract content from full page
      const doc = new DOMParser().parseFromString(html, "text/html");
      const content =
        doc.getElementById("main-content") ||
        doc.querySelector("main") ||
        doc.body;
      pane.innerHTML = content?.innerHTML || html;
    }

    // Re-execute inline scripts
    pane.querySelectorAll("script").forEach((old) => {
      if (old.type === "importmap") {
        old.remove();
        return;
      }
      const replacement = document.createElement("script");
      Array.from(old.attributes).forEach((attr) =>
        replacement.setAttribute(attr.name, attr.value),
      );
      replacement.textContent = old.textContent;
      old.replaceWith(replacement);
    });

    history.pushState({ page: url }, "", url);

    // Init collapsible categories (click header to toggle)
    initCategoryToggles(pane);
  } catch (err) {
    console.error("[ajax-loader] Failed to load:", url, err);
    location.href = url;
  }
}
