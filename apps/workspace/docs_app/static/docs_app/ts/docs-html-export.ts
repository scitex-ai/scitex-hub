/** A static HTML copy of the loaded document; no navigation chrome or embeds. */
import createDOMPurify from "dompurify";

const htmlSanitizer = createDOMPurify(window);
const mounted = new WeakMap<Document, () => void>();
class HtmlExportUnavailable extends Error {}

export function buildHtmlExport(html: string, title: string, styles: string, source: string): string {
  const sourceUrl = new URL(source);
  if (!["http:", "https:"].includes(sourceUrl.protocol)) throw new HtmlExportUnavailable("Open this page online before exporting HTML.");
  sourceUrl.username = sourceUrl.password = sourceUrl.search = sourceUrl.hash = "";
  const fragment = document.createElement("template");
  fragment.innerHTML = html;
  if (fragment.content.querySelector("iframe,object,embed,canvas")) throw new HtmlExportUnavailable("HTML download is unavailable for embedded documentation.");
  fragment.content.querySelectorAll("button,input,textarea,select,.docs-section-export,.docs-toolbar,.docs-context-menu,[data-docs-html-status]").forEach(node => node.remove());
  const doc = document.implementation.createHTMLDocument(title);
  doc.documentElement.lang = document.documentElement.lang || "en";
  const charset = doc.createElement("meta");
  charset.setAttribute("charset", "utf-8");
  const viewport = doc.createElement("meta");
  viewport.name = "viewport"; viewport.content = "width=device-width, initial-scale=1";
  const policy = doc.createElement("meta");
  policy.httpEquiv = "Content-Security-Policy";
  policy.content = "default-src 'none'; style-src 'unsafe-inline'; img-src https: http: data:; base-uri 'none'; form-action 'none'";
  const style = doc.createElement("style"); style.textContent = styles;
  doc.head.prepend(charset, viewport, policy);
  doc.head.append(style);
  doc.body.innerHTML = htmlSanitizer.sanitize(fragment.innerHTML, {
    USE_PROFILES: { html: true, svg: true },
    ALLOW_DATA_ATTR: false, FORBID_ATTR: ["srcset"],
    FORBID_TAGS: ["script", "style", "link", "meta", "base", "form", "input", "button", "textarea", "select"],
  });
  if (!doc.body.textContent?.trim() && !doc.body.querySelector("img[src],svg,table,pre")) throw new HtmlExportUnavailable("Wait for the document to finish loading.");
  doc.body.querySelectorAll("[href],[src],[poster]").forEach(element => {
    for (const attr of ["href", "src", "poster"]) {
      const value = element.getAttribute(attr);
      if (value && !value.startsWith("#")) element.setAttribute(attr, new URL(value, sourceUrl).href);
    }
  });
  return "<!DOCTYPE html>\n" + doc.documentElement.outerHTML;
}

export function initDocsHtmlExport(styles: string, root: Document = document): () => void {
  const existing = mounted.get(root);
  if (existing) return existing;
  const onClick = (event: MouseEvent) => {
    const button = event.target instanceof Element ? event.target.closest<HTMLButtonElement>("[data-docs-html-export]") : null;
    const workspace = button?.closest<HTMLElement>(".docs-workspace");
    const area = workspace?.querySelector<HTMLElement>("#docs-content-area");
    if (!button || !workspace || !area) return;
    event.preventDefault();
    let status = workspace.querySelector<HTMLElement>("[data-docs-html-status]");
    if (!status) {
      status = root.createElement("span"); status.className = "visually-hidden";
      status.dataset.docsHtmlStatus = ""; status.setAttribute("role", "status"); workspace.append(status);
    }
    try {
      if (area.querySelector(".docs-loading,.docs-error") || area.style.opacity === "0.5") throw new HtmlExportUnavailable("Wait for the document to finish loading.");
      const page = workspace.querySelector<HTMLElement>(".docs-nav-item.active");
      const slug = (page?.dataset.docSlug || "page").replace(/[^a-z0-9._-]/gi, "-");
      const title = page?.querySelector("span")?.textContent?.trim() || "SciTeX Documentation";
      const html = buildHtmlExport(area.innerHTML, title, styles, root.location.href);
      const url = URL.createObjectURL(new Blob([html], { type: "text/html;charset=utf-8" }));
      const anchor = root.createElement("a"); anchor.href = url; anchor.download = `scitex-docs-${slug}.html`;
      root.body.append(anchor);
      try { anchor.click(); } finally {
        anchor.remove(); setTimeout(() => URL.revokeObjectURL(url), 0);
      }
      button.title = "Download the loaded page as HTML"; status.textContent = "HTML download ready.";
    } catch (error) {
      const message = error instanceof HtmlExportUnavailable ? error.message : "HTML download unavailable.";
      button.title = message; status.textContent = message;
    }
  };
  root.addEventListener("click", onClick);
  const cleanup = () => { root.removeEventListener("click", onClick); mounted.delete(root); };
  mounted.set(root, cleanup);
  return cleanup;
}
