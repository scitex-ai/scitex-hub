/**
 * PDF Viewer Module
 * Handles PDF viewing and rendering logic
 */

import { PDFJSViewer } from "../pdf-viewer-pdfjs.js";

export interface ViewerState {
  currentPdfUrl: string | null;
  colorMode: "light" | "dark";
  renderQuality: number;
}

export class PDFViewer {
  private pdfViewer: PDFJSViewer | null = null;
  private container: HTMLElement | null;
  private state: ViewerState;

  constructor(
    containerId: string,
    colorMode: "light" | "dark",
    renderQuality: number,
  ) {
    this.container = document.getElementById(containerId);
    this.state = {
      currentPdfUrl: null,
      colorMode,
      renderQuality,
    };
  }

  /**
   * Initialize PDF.js viewer
   */
  initialize(): void {
    if (!this.container) {
      console.error("[PDFViewer] No container found for PDF viewer");
      return;
    }

    console.log("[PDFViewer] Initializing PDF.js viewer...");
    this.pdfViewer = new PDFJSViewer({
      containerId: this.container.id,
      colorMode: this.state.colorMode,
      fitToWidth: true,
      renderQuality: this.state.renderQuality,
    });

    // Expose PDFJSViewer instance globally for mode synchronization
    (window as any).pdfViewerInstance = this.pdfViewer;

    console.log("[PDFViewer] ✓ PDF.js viewer initialized");
  }

  /**
   * Display PDF using PDF.js canvas viewer
   */
  displayPdf(pdfUrl: string): void {
    if (!this.container || !this.pdfViewer) {
      console.error("[PDFViewer] No container or PDFJSViewer available");
      return;
    }

    console.log("[PDFViewer] ========================================");
    console.log("[PDFViewer] displayPdf() called with PDF.js viewer");
    console.log("[PDFViewer] PDF URL:", pdfUrl);

    // Extract theme from URL
    const pdfTheme = pdfUrl.includes("-dark.pdf") ? "dark" : "light";
    console.log("[PDFViewer] PDF theme:", pdfTheme);

    // Update color mode if needed
    if (pdfTheme !== this.state.colorMode) {
      console.log("[PDFViewer] Updating color mode to match PDF:", pdfTheme);
      this.state.colorMode = pdfTheme;
      this.pdfViewer.setColorMode(pdfTheme);

      // Update button icon to match
      const pdfScrollZoomHandler = (window as any).pdfScrollZoomHandler;
      if (
        pdfScrollZoomHandler &&
        typeof pdfScrollZoomHandler.setColorMode === "function"
      ) {
        pdfScrollZoomHandler.setColorMode(pdfTheme);
      }
    }

    // Add timestamp to URL for cache-busting
    const cacheBustUrl = pdfUrl.includes("?")
      ? pdfUrl
      : `${pdfUrl}?t=${Date.now()}`;

    console.log("[PDFViewer] Cache-bust URL:", cacheBustUrl);
    console.log(
      "[PDFViewer] Loading PDF via PDF.js with",
      this.state.renderQuality + "x quality",
    );

    // Load PDF via PDF.js canvas viewer
    this.pdfViewer.loadPDF(cacheBustUrl);

    // Update current PDF URL
    this.state.currentPdfUrl = pdfUrl;

    // Update download button
    const downloadBtn = document.getElementById(
      "download-pdf-toolbar",
    ) as HTMLAnchorElement;
    if (downloadBtn) {
      downloadBtn.href = pdfUrl;
      downloadBtn.style.display = "inline-block";
    }

    console.log("[PDFViewer] ✓ PDF loaded via PDF.js canvas viewer");
    console.log("[PDFViewer] ✓ Current PDF URL set to:", pdfUrl);
    console.log("[PDFViewer] ✓ Theme:", this.state.colorMode);
    console.log("[PDFViewer] ✓ Render quality:", this.state.renderQuality + "x");
    console.log("[PDFViewer] ========================================");
  }

  /**
   * Display placeholder
   */
  displayPlaceholder(): void {
    if (!this.container) return;

    this.container.innerHTML = `
            <div style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100%;
                text-align: center;
                color: var(--color-fg-muted);
                gap: 1rem;
            ">
                <i class="fas fa-file-pdf fa-3x" style="opacity: 0.3;"></i>
                <h5 style="margin: 0;">PDF Preview</h5>
                <p style="font-size: 0.9rem; margin: 0;">Loading PDF preview...</p>
                <p style="font-size: 0.75rem; opacity: 0.7; margin: 0;">Click Compile to generate PDF</p>
            </div>
        `;
  }

  /**
   * Display error message
   */
  displayError(error: string): void {
    if (!this.container) return;

    this.container.innerHTML = `
            <div style="padding: 2rem; text-align: center; color: var(--color-danger-fg);">
                <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
                <h5>Compilation Error</h5>
                <p style="font-size: 0.9rem;">${error}</p>
                <small style="color: var(--color-fg-muted);">Check the error output for details</small>
            </div>
        `;

    console.error("[PDFViewer] Compilation error:", error);
  }

  /**
   * Update progress display
   */
  updateProgress(progress: number, status: string): void {
    if (!this.container) return;

    // Check if PDF is already displayed
    const hasPDF =
      this.container.querySelector("iframe, .pdfjs-pages-container") !== null;

    if (hasPDF) {
      console.log(
        "[PDFViewer] Background compile progress:",
        progress,
        "%",
        status,
      );
      return;
    }

    // Only show progress UI if no PDF is displayed yet
    this.container.innerHTML = `
            <div style="padding: 2rem; text-align: center;">
                <div class="progress" style="height: 4px; margin-bottom: 1rem;">
                    <div class="progress-bar" role="progressbar" style="width: ${progress}%; background: var(--color-accent-emphasis);" aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
                <p style="color: var(--color-fg-muted);">${status}</p>
                <small>${progress}%</small>
            </div>
        `;
  }

  /**
   * Set color mode
   */
  setColorMode(colorMode: "light" | "dark"): void {
    this.state.colorMode = colorMode;
    if (this.pdfViewer) {
      this.pdfViewer.setColorMode(colorMode);
      console.log("[PDFViewer] ✓ PDF.js viewer color mode updated to:", colorMode);
    }
  }

  /**
   * Get PDFJSViewer instance
   */
  getPdfViewer(): PDFJSViewer | null {
    return this.pdfViewer;
  }

  /**
   * Get current PDF URL
   */
  getCurrentPdfUrl(): string | null {
    return this.state.currentPdfUrl;
  }

  /**
   * Get color mode
   */
  getColorMode(): "light" | "dark" {
    return this.state.colorMode;
  }
}
