import createDOMPurify from "dompurify";
import { PRINT_CSS } from "./docs-export-style";
import { removeExportControls } from "./docs-export-controls";

// Keep print sanitization independent of other app hooks.
const printSanitizer = createDOMPurify(window);

/** Prepare static document content, keeping SVG figures and excluding controls. */
export function preparePrintContent(html: string): DocumentFragment {
  const fragment = printSanitizer.sanitize(html, {
    USE_PROFILES: { html: true, svg: true },
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "canvas", "form"],
    RETURN_DOM_FRAGMENT: true,
  });
  removeExportControls(fragment);
  return fragment;
}

export function openPrintWindow(html: string): void {
  const win = window.open("", "_blank");
  if (!win) return;
  const doc = win.document;
  doc.open();
  doc.write(
    "<!DOCTYPE html><html><head><title>SciTeX Docs</title></head><body></body></html>",
  );
  doc.close();
  const s = doc.createElement("style");
  s.textContent = PRINT_CSS;
  doc.head.appendChild(s);
  doc.body.replaceChildren(doc.importNode(preparePrintContent(html), true));
  win.print();
}

