/**
 * AJAX Page Loader — loads pages into the module pane without full reload.
 *
 * Used by:
 * - Customize hub cards ([data-ajax-load] attribute)
 * - Settings pages navigated from within the workspace
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

    loadPageContent(url);
  });
}

/** Fetch a page via AJAX and inject its content into #main-content */
export async function loadPageContent(url: string): Promise<void> {
  const pane = document.getElementById("main-content");
  if (!pane) return;

  try {
    const resp = await fetch(url, {
      headers: { "X-Workspace-Shell": "1" },
      credentials: "same-origin",
    });

    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

    const html = await resp.text();

    // If response is a partial (no <html> tag), use directly
    if (!html.includes("<!DOCTYPE") && !html.includes("<html")) {
      pane.innerHTML = html;
    } else {
      // Extract content from full page
      const doc = new DOMParser().parseFromString(html, "text/html");
      const content =
        doc.getElementById("main-content") ||
        doc.querySelector(".settings-content") ||
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
    console.error("[ajax-loader] Failed to load page:", url, err);
    location.href = url;
  }
}
