/**
 * PDF Zoom Control Module
 * Handles zoom operations, zoom level management, and zoom UI controls
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-zoom-control.ts loaded",
);

import { statePersistence } from "../state-persistence.js";

export interface ZoomOptions {
  minZoom: number;
  maxZoom: number;
  zoomStep: number;
}

export class PDFZoomControl {
  private currentZoom: number = 125; // Default to 125% for better readability
  private minZoom: number;
  private maxZoom: number;
  private zoomStep: number;
  private pdfViewer: HTMLElement | null = null;

  constructor(options: ZoomOptions) {
    this.minZoom = options.minZoom;
    this.maxZoom = options.maxZoom;
    this.zoomStep = options.zoomStep;
  }

  /**
   * Set PDF viewer reference
   */
  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  /**
   * Get current zoom level
   */
  getCurrentZoom(): number {
    return this.currentZoom;
  }

  /**
   * Setup PDF zoom dropdown control
   */
  setupZoomButtons(): void {
    const zoomSelect = document.getElementById("pdf-zoom-select") as HTMLSelectElement;

    if (zoomSelect) {
      // Set initial value
      zoomSelect.value = this.currentZoom.toString();

      // Handle dropdown change
      zoomSelect.addEventListener("change", () => {
        const newZoom = parseInt(zoomSelect.value, 10);
        this.setZoom(newZoom);
        console.log(`[PDFZoomControl] Zoom changed to ${newZoom}% via dropdown`);
      });

      console.log("[PDFZoomControl] Zoom dropdown control initialized");
    } else {
      console.warn("[PDFZoomControl] Zoom dropdown not found");
    }
  }

  /**
   * Load saved zoom level from state persistence
   * Applies zoom immediately to iframe if present
   */
  loadSavedZoom(): void {
    const savedZoom = statePersistence.getSavedPdfZoom();
    if (savedZoom && savedZoom >= this.minZoom && savedZoom <= this.maxZoom) {
      this.currentZoom = savedZoom;

      // Update dropdown to reflect saved zoom
      const zoomSelect = document.getElementById("pdf-zoom-select") as HTMLSelectElement;
      if (zoomSelect) {
        zoomSelect.value = savedZoom.toString();
      }

      console.log("[PDFZoomControl] Loaded saved zoom level:", savedZoom);
    } else {
      console.log("[PDFZoomControl] No saved zoom or invalid value, using default:", this.currentZoom);
    }

    // Apply zoom immediately
    this.applyZoomToIframe();
  }

  /**
   * Apply current zoom level to iframe
   */
  applyZoomToIframe(): void {
    console.log("[PDFZoomControl] applyZoomToIframe() - checking for iframe...");

    if (!this.pdfViewer) {
      console.log("[PDFZoomControl] ✗ No pdfViewer reference, cannot apply zoom");
      return;
    }

    const iframe = this.pdfViewer.querySelector("iframe, embed");
    if (iframe) {
      const scaleRatio = this.currentZoom / 100;
      console.log("[PDFZoomControl] Found iframe/embed, applying scale:", scaleRatio);
      (iframe as HTMLElement).style.transform = `scale(${scaleRatio})`;
      (iframe as HTMLElement).style.transformOrigin = "top center";
      (iframe as HTMLElement).style.transition = "transform 0.2s ease";
      this.updateZoomIndicator();
      console.log("[PDFZoomControl] ✓ Zoom applied successfully:", this.currentZoom + "%");
    } else {
      console.log("[PDFZoomControl] ✗ No iframe/embed found in pdfViewer");
    }
  }

  /**
   * Set zoom level with cursor/center point preservation
   */
  setZoom(zoomLevel: number, cursorX?: number, cursorY?: number): void {
    if (!this.pdfViewer) return;

    const oldZoom = this.currentZoom;
    this.currentZoom = Math.max(
      this.minZoom,
      Math.min(this.maxZoom, zoomLevel),
    );

    // Apply zoom via transform to iframe/embed
    const embed = this.pdfViewer.querySelector("embed, iframe");
    if (embed) {
      const scaleRatio = this.currentZoom / 100;
      (embed as HTMLElement).style.transform = `scale(${scaleRatio})`;
      (embed as HTMLElement).style.transformOrigin = "top center";
      (embed as HTMLElement).style.transition = "none";

      // If cursor position provided, center zoom on cursor
      if (cursorX !== undefined && cursorY !== undefined) {
        this.centerZoomOnPoint(cursorX, cursorY, oldZoom);
      }
    }

    this.updateZoomIndicator();

    // Save zoom level to state persistence
    statePersistence.savePdfZoom(this.currentZoom);

    console.log(`[PDFZoomControl] Zoom: ${this.currentZoom.toFixed(0)}%`);
  }

  /**
   * Center zoom on a specific point (cursor/touch point)
   */
  private centerZoomOnPoint(
    pointX: number,
    pointY: number,
    oldZoom: number,
  ): void {
    if (!this.pdfViewer) return;

    const rect = this.pdfViewer.getBoundingClientRect();
    const relX = pointX - rect.left;
    const relY = pointY - rect.top;

    // Calculate scroll adjustment to keep point centered
    const zoomRatio = this.currentZoom / oldZoom;
    const scrollLeftAdjust = (relX * (zoomRatio - 1)) / zoomRatio;
    const scrollTopAdjust = (relY * (zoomRatio - 1)) / zoomRatio;

    requestAnimationFrame(() => {
      this.pdfViewer!.scrollLeft += scrollLeftAdjust;
      this.pdfViewer!.scrollTop += scrollTopAdjust;
    });
  }

  /**
   * Zoom in
   */
  zoomIn(): void {
    const newZoom = this.currentZoom + this.zoomStep;
    this.setZoom(newZoom);
  }

  /**
   * Zoom out
   */
  zoomOut(): void {
    const newZoom = this.currentZoom - this.zoomStep;
    this.setZoom(newZoom);
  }

  /**
   * Reset zoom to 125% (default)
   */
  resetZoom(): void {
    this.setZoom(125);
  }

  /**
   * Set zoom to fit page width
   */
  fitToWidth(): void {
    if (!this.pdfViewer || !this.pdfViewer.querySelector("embed")) return;

    const embed = this.pdfViewer.querySelector("embed") as HTMLEmbedElement;
    const embedWidth = embed.scrollWidth;
    const containerWidth = this.pdfViewer.clientWidth;

    const zoomLevel = (containerWidth / embedWidth) * 100;
    this.setZoom(zoomLevel);
  }

  /**
   * Set zoom to fit page height
   */
  fitToHeight(): void {
    if (!this.pdfViewer || !this.pdfViewer.querySelector("embed")) return;

    const embed = this.pdfViewer.querySelector("embed") as HTMLEmbedElement;
    const embedHeight = embed.scrollHeight;
    const containerHeight = this.pdfViewer.clientHeight;

    const zoomLevel = (containerHeight / embedHeight) * 100;
    this.setZoom(zoomLevel);
  }

  /**
   * Update zoom indicator in UI
   */
  private updateZoomIndicator(): void {
    // Update zoom dropdown
    const zoomSelect = document.getElementById("pdf-zoom-select") as HTMLSelectElement;
    if (zoomSelect) {
      // Round to nearest preset value or set custom value
      const roundedZoom = this.currentZoom.toFixed(0);

      // Check if the current zoom matches any preset option
      const hasMatchingOption = Array.from(zoomSelect.options).some(
        option => option.value === roundedZoom
      );

      if (hasMatchingOption) {
        zoomSelect.value = roundedZoom;
      } else {
        // If zoom doesn't match any preset, select the closest one
        const presetValues = Array.from(zoomSelect.options).map(opt => parseInt(opt.value, 10));
        const closest = presetValues.reduce((prev, curr) =>
          Math.abs(curr - this.currentZoom) < Math.abs(prev - this.currentZoom) ? curr : prev
        );
        zoomSelect.value = closest.toString();
      }
    }
  }
}
