import { openPrintWindow } from "./docs-print";

/** Reserve a print window while the click still has browser user activation. */
export async function printAllDocs(slugs: string[]): Promise<void> {
  const win = window.open("", "_blank");
  if (!win) {
    window.alert("Allow popups for this site to print all documentation.");
    return;
  }
  win.document.title = "Preparing SciTeX Docs";
  win.document.body.textContent = "Preparing all documentation for printing…";
  try {
    const pages = await Promise.all(slugs.map(async (slug) => {
      const response = await fetch("/apps/docs/content/" + encodeURIComponent(slug) + "/", {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) throw new Error(`Could not load ${slug} (HTTP ${response.status}).`);
      return response.text();
    }));
    if (win.closed) return;
    const combined = pages.map((html, i) => {
      const heading = document.createElement("h1");
      heading.textContent = slugs[i];
      return heading.outerHTML + html;
    }).join('<hr class="docs-print-page-break" />');
    openPrintWindow(combined, win);
  } catch (error) {
    if (win.closed) return;
    win.document.title = "Documentation print failed";
    const message = win.document.createElement("p");
    message.setAttribute("role", "alert");
    message.textContent = "Could not prepare all documentation. " +
      (error instanceof Error ? error.message : "Please try again.");
    win.document.body.replaceChildren(message);
  }
}
