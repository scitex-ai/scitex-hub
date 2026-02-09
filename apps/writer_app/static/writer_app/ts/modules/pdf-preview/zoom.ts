/**
 * PDF Zoom Module
 * Handles zoom controls and zoom level management
 */

import { PDFJSViewer } from "../pdf-viewer-pdfjs";

export class ZoomController {
  private pdfZoom: number = 100;
  private pdfViewer: PDFJSViewer | null = null;
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
    this.setupDpiSelector();
  }

  /**
   * Setup zoom selector dropdown using event delegation
   * (The dropdown is inside a template that gets innerHTML-copied into the shared header,
   *  so direct event listeners are lost. Use document-level delegation instead.)
   */
  private setupZoomSelector(): void {
    // Set initial value on the template element
    const zoomSelector = document.getElementById(
      "pdf-zoom-select",
    ) as HTMLSelectElement;
    if (zoomSelector) {
      zoomSelector.value = this.pdfZoom.toString();
    }

    // Use event delegation on document to catch changes on dynamically copied elements
    document.addEventListener("change", (e) => {
      const target = e.target as HTMLSelectElement;
      if (target && target.id === "pdf-zoom-select") {
        const value = target.value;
        if (value === "fit-width") {
          this.setFitToWidth();
        } else {
          this.setPdfZoom(parseInt(value, 10));
        }
      }
    });
  }

  /**
   * Setup zoom in button using event delegation
   */
  private setupZoomInButton(): void {
    document.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.id === "pdf-zoom-in" || target.closest("#pdf-zoom-in"))
      ) {
        const currentIndex = this.ZOOM_LEVELS.indexOf(this.pdfZoom);
        if (currentIndex < this.ZOOM_LEVELS.length - 1) {
          this.setPdfZoom(this.ZOOM_LEVELS[currentIndex + 1]);
        }
      }
    });
  }

  /**
   * Setup zoom out button using event delegation
   */
  private setupZoomOutButton(): void {
    document.addEventListener("click", (e) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.id === "pdf-zoom-out" || target.closest("#pdf-zoom-out"))
      ) {
        const currentIndex = this.ZOOM_LEVELS.indexOf(this.pdfZoom);
        if (currentIndex > 0) {
          this.setPdfZoom(this.ZOOM_LEVELS[currentIndex - 1]);
        }
      }
    });
  }

  /**
   * Set PDF zoom level
   */
  setPdfZoom(zoom: number): void {
    this.pdfZoom = zoom;
    localStorage.setItem("pdf-zoom-level", zoom.toString());

    // Update all zoom selectors (template + visible copy)
    const zoomSelectors = document.querySelectorAll("#pdf-zoom-select");
    zoomSelectors.forEach((el) => {
      (el as HTMLSelectElement).value = zoom.toString();
    });

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

    // Update zoom selector in visible header
    const zoomSelectors = document.querySelectorAll("#pdf-zoom-select");
    zoomSelectors.forEach((el) => {
      (el as HTMLSelectElement).value = "fit-width";
    });

    // Trigger PDF.js viewer to recalculate fit-to-width
    if (this.pdfViewer) {
      this.pdfViewer.fitWidth();
      console.log("[ZoomController] Fit-to-width mode enabled");
    }
  }

  /**
   * Setup DPI quality selector dropdown using event delegation
   */
  private setupDpiSelector(): void {
    // Restore saved DPI on the template element
    const dpiSelector = document.getElementById(
      "pdf-dpi-select",
    ) as HTMLSelectElement;
    const savedDpi = localStorage.getItem("pdf-dpi-quality");
    if (savedDpi) {
      if (dpiSelector) dpiSelector.value = savedDpi;
      if (this.pdfViewer) {
        this.pdfViewer.setRenderQuality(parseFloat(savedDpi));
        console.log(
          "[ZoomController] Restored saved DPI quality:",
          savedDpi + "x",
        );
      }
    }

    // Use event delegation for dynamically copied elements
    document.addEventListener("change", (e) => {
      const target = e.target as HTMLSelectElement;
      if (target && target.id === "pdf-dpi-select") {
        const quality = parseFloat(target.value);
        localStorage.setItem("pdf-dpi-quality", target.value);
        if (this.pdfViewer) {
          this.pdfViewer.setRenderQuality(quality);
          console.log(
            "[ZoomController] DPI quality changed to:",
            quality + "x",
          );
        }
      }
    });
  }

  /**
   * Get current zoom level
   */
  getCurrentZoom(): number {
    return this.pdfZoom;
  }
}
