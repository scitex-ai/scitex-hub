import createDOMPurify from "dompurify";
import { PRINT_CSS } from "./docs-export-style";
import { removeExportControls } from "./docs-export-controls";

// Keep print sanitization independent of other app hooks.
const printSanitizer = createDOMPurify(window);

/** Prepare static document content, keeping SVG figures and excluding controls. */
export function preparePrintContent(html: string): string {
  const fragment = document.createElement("template");
  fragment.innerHTML = html;
  removeExportControls(fragment.content);
  return printSanitizer.sanitize(fragment.innerHTML, {
    USE_PROFILES: { html: true, svg: true },
    ALLOW_DATA_ATTR: false,
    FORBID_TAGS: ["script", "style", "iframe", "object", "embed", "canvas", "form"],
  });
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
  doc.body.innerHTML = preparePrintContent(html);
  win.print();
}

