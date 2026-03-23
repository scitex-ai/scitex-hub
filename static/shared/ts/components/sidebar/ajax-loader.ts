/**
 * AJAX Page Loader — loads pages into a container without full reload.
 * Uses X-Workspace-Shell: 1 header so Django views return partials.
 *
 * NOTE: Core logic extracted to scitex-ui AjaxLoader class.
 * This file provides scitex-cloud-specific initialization.
 */

/** Initialize delegated click handler for [data-ajax-load] links */
export function initAjaxLinks(): void {
  document.addEventListener("click", (e) => {
    const link = (e.target as HTMLElement).closest<HTMLElement>(
      "[data-ajax-load]",
    );
    if (!link) return;

    e.preventDefault();
    const url = link.getAttribute("data-ajax-load");
    if (!url) return;

    void loadPageContent(url);
  });
}

/** Fetch a page via AJAX and inject its content */
export async function loadPageContent(url: string): Promise<void> {
  // Prefer customize-content container on /customize/ pages
  const pane =
    document.getElementById("customize-content") ||
    document.getElementById("main-content");
  if (!pane) return;

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
  } catch (err) {
    console.error("[ajax-loader] Failed to load:", url, err);
    location.href = url;
  }
}
