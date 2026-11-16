import createDOMPurify from "dompurify";

// Keep print sanitization independent of other app hooks.
const printSanitizer = createDOMPurify(window);

const PRINT_CSS =
  "body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;color:#222}" +
  "pre{background:#f5f5f5;padding:1rem;overflow-x:auto;border-radius:4px}" +
  "code{font-family:monospace}h1,h2,h3{margin-top:1.5rem}" +
  "table{border-collapse:collapse;width:100%}" +
  "th,td{border:1px solid #ddd;padding:8px;text-align:left}";

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
  doc.body.innerHTML = printSanitizer.sanitize(html, { USE_PROFILES: { html: true } });
  win.print();
}

