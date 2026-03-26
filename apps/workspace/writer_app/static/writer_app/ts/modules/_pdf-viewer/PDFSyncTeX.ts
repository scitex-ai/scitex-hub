/**
 * PDF SyncTeX Reverse Lookup Handler
 * Handles double-click on PDF pages to perform SyncTeX reverse lookup,
 * mapping PDF coordinates back to .tex source file and line number.
 */

import { getWriterConfig } from "../../_helpers";

/**
 * Convert a mouse click on a PDF page container to PDF-space coordinates.
 *
 * PDF coordinate system: origin at bottom-left, 72 points per inch.
 * The canvas CSS dimensions match the display viewport (in PDF points * scale).
 * We reverse the scale to get raw PDF points, then flip Y for PDF convention.
 */
function getPageCoordinates(
  pageContainer: HTMLElement,
  event: MouseEvent,
  scale: number,
): { page: number; x: number; y: number } | null {
  const pageNum = parseInt(pageContainer.dataset.pageNum || "0", 10);
  if (!pageNum) return null;

  const rect = pageContainer.getBoundingClientRect();

  // Position relative to page container, in CSS pixels
  const cssX = event.clientX - rect.left;
  const cssY = event.clientY - rect.top;

  // Convert CSS pixels to PDF points (undo the viewport scale)
  const pdfX = cssX / scale;
  // PDF Y-axis is bottom-up; page height in PDF points = container CSS height / scale
  const pageHeightPt = rect.height / scale;
  const pdfY = pageHeightPt - cssY / scale;

  return { page: pageNum, x: pdfX, y: pdfY };
}

/**
 * Call the SyncTeX reverse lookup backend API.
 */
async function callSyncTeXAPI(
  projectId: number,
  page: number,
  x: number,
  y: number,
  pdfFilename: string,
): Promise<{
  success: boolean;
  file?: string;
  line?: number;
  column?: number;
  error?: string;
}> {
  const response = await fetch(
    `/apps/writer/api/project/${projectId}/synctex/`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": getCSRFToken(),
      },
      body: JSON.stringify({
        page,
        x,
        y,
        pdf_filename: pdfFilename,
      }),
    },
  );

  return response.json();
}

/**
 * Get CSRF token from cookie or meta tag.
 */
function getCSRFToken(): string {
  // Try meta tag first
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta) return meta.getAttribute("content") || "";

  // Try cookie
  const cookies = document.cookie.split(";");
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split("=");
    if (name === "csrftoken") return decodeURIComponent(value);
  }

  // Try WRITER_CONFIG
  if ((window as any).WRITER_CONFIG?.csrfToken) {
    return (window as any).WRITER_CONFIG.csrfToken;
  }

  return "";
}

/**
 * Navigate the Monaco editor to a specific file and line.
 * Loads the file if not already open, then moves the cursor.
 */
function navigateEditorToLine(
  filePath: string,
  line: number,
  column: number,
): void {
  const editor = (window as any).writerMonacoEditor;

  if (editor && typeof editor.revealLineInCenter === "function") {
    // Monaco editor is available directly
    jumpToLine(editor, line, column);
    return;
  }

  // Monaco editor not directly on window; dispatch an event for the
  // writer app to handle file loading + line navigation.
  console.log("[SyncTeX] Dispatching synctex:navigateToSource event");
  window.dispatchEvent(
    new CustomEvent("synctex:navigateToSource", {
      detail: { file: filePath, line, column },
    }),
  );
}

/**
 * Jump to a specific line in a Monaco editor instance.
 */
function jumpToLine(editor: any, line: number, column: number): void {
  try {
    editor.revealLineInCenter(line);
    editor.setPosition({ lineNumber: line, column: Math.max(1, column) });
    editor.focus();
    console.log(`[SyncTeX] Editor jumped to line ${line}, column ${column}`);
  } catch (err) {
    console.error("[SyncTeX] Failed to navigate editor:", err);
  }
}

/**
 * Determine the current PDF filename from the viewer state.
 * Looks at the current PDF URL to extract the filename.
 */
function getCurrentPdfFilename(): string {
  const pdfViewer = (window as any).pdfViewerInstance;
  if (!pdfViewer) return "manuscript.pdf";

  // Try to get current PDF URL from the viewer's state
  const currentUrl: string | null =
    pdfViewer.getCurrentPdfUrl?.() ?? pdfViewer.state?.currentPdfUrl ?? null;

  if (currentUrl) {
    // Extract filename from URL, e.g. "/apps/writer/api/project/1/pdf/manuscript.pdf?t=123"
    const urlPath = currentUrl.split("?")[0];
    const filename = urlPath.split("/").pop();
    if (filename && filename.endsWith(".pdf")) {
      return filename;
    }
  }

  return "manuscript.pdf";
}

/**
 * Setup SyncTeX double-click handler on the PDF viewer element.
 * Double-clicking a PDF page will perform a reverse lookup and
 * navigate the editor to the corresponding source location.
 *
 * Uses double-click to avoid conflicting with text selection (single click)
 * and hand-mode panning.
 */
export function setupSyncTeXHandler(
  viewerElement: HTMLElement,
  getCurrentScale: () => number,
): void {
  // Guard against duplicate listeners when setupInteractions is called
  // repeatedly (e.g. on zoom change, theme change, re-render).
  if ((viewerElement as any).__synctexHandlerInstalled) return;
  (viewerElement as any).__synctexHandlerInstalled = true;
  viewerElement.addEventListener("dblclick", async (event: MouseEvent) => {
    // Only handle in text mode (not hand or zoom)
    const pdfViewer = (window as any).pdfViewerInstance;
    if (pdfViewer?.currentMode && pdfViewer.currentMode !== "text") {
      return;
    }

    // Find the page container that was clicked
    const target = event.target as HTMLElement;
    const pageContainer = target.closest(
      ".pdfjs-page-container",
    ) as HTMLElement | null;
    if (!pageContainer) return;

    const scale = getCurrentScale();
    const coords = getPageCoordinates(pageContainer, event, scale);
    if (!coords) return;

    const config = getWriterConfig();
    if (!config.projectId) {
      console.warn("[SyncTeX] No project ID available");
      return;
    }

    const pdfFilename = getCurrentPdfFilename();

    console.log(
      `[SyncTeX] Double-click on page ${coords.page} at (${coords.x.toFixed(1)}, ${coords.y.toFixed(1)}) ` +
        `in ${pdfFilename} (scale=${scale.toFixed(2)})`,
    );

    // Show visual feedback
    showClickFeedback(event.clientX, event.clientY);

    try {
      const result = await callSyncTeXAPI(
        config.projectId,
        coords.page,
        coords.x,
        coords.y,
        pdfFilename,
      );

      if (result.success && result.file && result.line) {
        console.log(
          `[SyncTeX] Found source: ${result.file}:${result.line}:${result.column ?? 0}`,
        );
        navigateEditorToLine(result.file, result.line, result.column ?? 0);
      } else {
        console.warn(
          "[SyncTeX] No match found:",
          result.error || "unknown reason",
        );
      }
    } catch (err) {
      console.error("[SyncTeX] API call failed:", err);
    }
  });

  console.log("[SyncTeX] Double-click handler installed on PDF viewer");
}

/**
 * Show a brief visual indicator at the click location.
 */
function showClickFeedback(clientX: number, clientY: number): void {
  const dot = document.createElement("div");
  dot.style.cssText = `
    position: fixed;
    left: ${clientX - 6}px;
    top: ${clientY - 6}px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: rgba(59, 130, 246, 0.7);
    pointer-events: none;
    z-index: 10000;
    transition: opacity 0.5s ease-out, transform 0.5s ease-out;
  `;
  document.body.appendChild(dot);

  requestAnimationFrame(() => {
    dot.style.opacity = "0";
    dot.style.transform = "scale(3)";
  });

  setTimeout(() => dot.remove(), 600);
}

// EOF
