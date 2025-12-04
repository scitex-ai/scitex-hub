/**
 * PDF Zoom Module
 * Handles zoom controls and zoom level management
 */

import { PDFJSViewer } from "../pdf-viewer-pdfjs.js";

export class ZoomController {
  private pdfZoom: number = 100;
  private pdfViewer: PDFJSViewer | null = null;
  private currentPdfUrl: string | null = null;
  private readonly ZOOM_LEVELS = [100, 125, 150, 175, 200];

  constructor(pdfViewer: PDFJSViewer | null) {
    this.pdfViewer = pdfViewer;
    this.loadSavedZoom();
  }

  /**
   * Load saved zoom level from localStorage
   */
  private loadSavedZoom(): void {
    const savedZoom = localStorage.getItem("pdf-zoom-level");
    if (savedZoom) {
      this.pdfZoom = parseInt(savedZoom, 10);
      if (this.pdfViewer) {
        const scale = this.pdfZoom / 100;
        this.pdfViewer.setScale(scale);
        console.log(
          "[ZoomController] ✓ Restored saved zoom:",
          this.pdfZoom + "% (scale:",
          scale + ")",
        );
      }
    }
  }

  /**
   * Setup zoom controls
   */
  setupControls(): void {
    this.setupZoomSelector();
    this.setupZoomInButton();
    this.setupZoomOutButton();
  }

  /**
   * Setup zoom selector dropdown
   */
  private setupZoomSelector(): void {
    const zoomSelector = document.getElementById(
      "pdf-zoom-select",
    ) as HTMLSelectElement;
    if (zoomSelector) {
      zoomSelector.value = this.pdfZoom.toString();
      zoomSelector.addEventListener("change", () => {
        const value = zoomSelector.value;
        if (value === "fit-width") {
          this.setFitToWidth();
        } else {
          this.setPdfZoom(parseInt(value, 10));
        }
      });
    }
  }

  /**
   * Setup zoom in button
   */
  private setupZoomInButton(): void {
    const zoomInBtn = document.getElementById("pdf-zoom-in");
    if (zoomInBtn) {
      zoomInBtn.addEventListener("click", () => {
        const currentIndex = this.ZOOM_LEVELS.indexOf(this.pdfZoom);
        if (currentIndex < this.ZOOM_LEVELS.length - 1) {
          this.setPdfZoom(this.ZOOM_LEVELS[currentIndex + 1]);
        }
      });
    }
  }

  /**
   * Setup zoom out button
   */
  private setupZoomOutButton(): void {
    const zoomOutBtn = document.getElementById("pdf-zoom-out");
    if (zoomOutBtn) {
      zoomOutBtn.addEventListener("click", () => {
        const currentIndex = this.ZOOM_LEVELS.indexOf(this.pdfZoom);
        if (currentIndex > 0) {
          this.setPdfZoom(this.ZOOM_LEVELS[currentIndex - 1]);
        }
      });
    }
  }

  /**
   * Set PDF zoom level
   */
  setPdfZoom(zoom: number): void {
    this.pdfZoom = zoom;
    localStorage.setItem("pdf-zoom-level", zoom.toString());

    // Update zoom selector
    const zoomSelector = document.getElementById(
      "pdf-zoom-select",
    ) as HTMLSelectElement;
    if (zoomSelector) {
      zoomSelector.value = zoom.toString();
    }

    // Update PDF.js viewer zoom
    if (this.pdfViewer) {
      const scale = zoom / 100;
      this.pdfViewer.setScale(scale);
      console.log(
        "[ZoomController] PDF.js zoom changed to:",
        zoom + "% (scale:",
        scale + ")",
      );
    }
  }

  /**
   * Enable fit-to-width mode
   */
  setFitToWidth(): void {
    // Clear saved zoom to enable fit-to-width calculation
    localStorage.removeItem("pdf-zoom-level");

    // Update zoom selector
    const zoomSelector = document.getElementById(
      "pdf-zoom-select",
    ) as HTMLSelectElement;
    if (zoomSelector) {
      zoomSelector.value = "fit-width";
    }

    // Trigger PDF.js viewer to recalculate fit-to-width
    if (this.pdfViewer && this.currentPdfUrl) {
      this.pdfViewer.fitWidth();
      console.log("[ZoomController] Fit-to-width mode enabled");
    }
  }

  /**
   * Update current PDF URL (needed for fit-to-width)
   */
  setCurrentPdfUrl(url: string | null): void {
    this.currentPdfUrl = url;
  }

  /**
   * Get current zoom level
   */
  getCurrentZoom(): number {
    return this.pdfZoom;
  }
}
