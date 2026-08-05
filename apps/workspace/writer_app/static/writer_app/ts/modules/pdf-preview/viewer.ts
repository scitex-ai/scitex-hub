/**
 * PDF Viewer Module
 * Handles PDF viewing and rendering logic
 */

import { PDFJSViewer } from "../pdf-viewer-pdfjs";

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
   * Display PDF using PDF.js canvas viewer.
   * Pass force=true to reload even when the URL hasn't changed (e.g. after fresh compile).
   */
  displayPdf(pdfUrl: string, force = false): void {
    if (!this.container || !this.pdfViewer) {
      console.error("[PDFViewer] No container or PDFJSViewer available");
      return;
    }

    // Skip reload if showing the same URL and not forced (prevents flash on redundant calls)
    if (!force && this.state.currentPdfUrl === pdfUrl) {
      console.log(
        "[PDFViewer] Same PDF URL already displayed, skipping reload",
      );
      return;
    }

    console.log("[PDFViewer] ========================================");
    console.log("[PDFViewer] displayPdf() called with PDF.js viewer");
    console.log("[PDFViewer] PDF URL:", pdfUrl);

    // For preview PDFs (with theme baked in), sync viewer to match the PDF theme.
    // For full compilation PDFs, preserve user's current color mode preference.
    const isPreviewPdf = pdfUrl.includes("preview-");
    if (isPreviewPdf) {
      const pdfTheme = pdfUrl.includes("-dark.pdf") ? "dark" : "light";
      console.log("[PDFViewer] Preview PDF theme:", pdfTheme);

      if (pdfTheme !== this.state.colorMode) {
        console.log(
          "[PDFViewer] Syncing viewer color mode to preview PDF:",
          pdfTheme,
        );
        this.state.colorMode = pdfTheme;
        this.pdfViewer.setColorMode(pdfTheme);

        const pdfScrollZoomHandler = (window as any).pdfScrollZoomHandler;
        if (
          pdfScrollZoomHandler &&
          typeof pdfScrollZoomHandler.setColorMode === "function"
        ) {
          pdfScrollZoomHandler.setColorMode(pdfTheme);
        }
      }
    } else {
      // Full compilation PDF: apply user's preferred color mode
      const savedPdfTheme = localStorage.getItem("pdf-color-mode");
      const preferredMode =
        savedPdfTheme === "dark" || savedPdfTheme === "light"
          ? savedPdfTheme
          : document.documentElement.getAttribute("data-theme") === "dark"
            ? "dark"
            : "light";

      console.log(
        "[PDFViewer] Full PDF — applying user preference:",
        preferredMode,
      );
      if (preferredMode !== this.state.colorMode) {
        this.state.colorMode = preferredMode as "light" | "dark";
        this.pdfViewer.setColorMode(preferredMode as "light" | "dark");

        const pdfScrollZoomHandler = (window as any).pdfScrollZoomHandler;
        if (
          pdfScrollZoomHandler &&
          typeof pdfScrollZoomHandler.setColorMode === "function"
        ) {
          pdfScrollZoomHandler.setColorMode(preferredMode);
        }
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
    console.log(
      "[PDFViewer] ✓ Render quality:",
      this.state.renderQuality + "x",
    );
    console.log("[PDFViewer] ========================================");
  }

  /**
   * Display placeholder.
   *
   * WHY THIS NO LONGER SAYS "Loading PDF preview...": that line was a standing
   * claim that something was in flight, and on a fresh project nothing is.
   * ComponentInitializer.loadInitialPDF() HEAD-checks for an existing preview;
   * if none exists AND the abstract is empty it takes neither branch — it does
   * not compile and it does not update the panel — so this placeholder is the
   * final state, not a transient one. A new user therefore saw "Loading PDF
   * preview..." forever on a document that was never going to load.
   *
   * Measured on live scitex.ai 2026-08-04: HEAD
   * /apps/writer/api/project/19/pdf/preview-abstract-light.pdf -> 404, and the
   * panel still read "Loading PDF preview..". The 404 itself is CORRECT — the
   * preview PDF is produced by compilation into writer_dir/.preview/, so its
   * absence just means "never compiled". Only the wording was wrong.
   *
   * The panel already carried the right instruction on the next line ("Click
   * Compile to generate PDF"); it was contradicted by the line above it. This
   * keeps the instruction and drops the false one.
   *
   * TRADE-OFF, stated: while a preview genuinely IS loading, this now reads "No
   * preview yet" for that moment instead of "Loading...". A brief understatement
   * during a real load is a much smaller lie than a permanent "Loading..." on a
   * document that will never load, and the real load replaces this markup on
   * completion.
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
                <p style="font-size: 0.9rem; margin: 0;">No preview yet</p>
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
      console.log(
        "[PDFViewer] ✓ PDF.js viewer color mode updated to:",
        colorMode,
      );
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
