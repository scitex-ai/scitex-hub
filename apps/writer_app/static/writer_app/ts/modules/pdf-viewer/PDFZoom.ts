/**
 * PDF Zoom Controller
 * Handles zoom controls, scale management, and persistence
 */

import { statePersistence } from "../state-persistence.js";

console.log("[DEBUG] PDFZoom.ts loaded");

export class PDFZoom {
  private currentScale: number = 1.5;
  private fitToWidth: boolean = true;

  constructor(fitToWidth?: boolean) {
    this.fitToWidth = fitToWidth ?? true;
    this.restoreSavedZoom();
  }

  /**
   * Restore zoom level from localStorage
   */
  private restoreSavedZoom(): void {
    const savedZoom = statePersistence.getSavedPdfZoom();
    if (savedZoom) {
      this.currentScale = savedZoom / 100;
      console.log("[PDFZoom] Restored saved zoom:", savedZoom + "%", "scale:", this.currentScale);
    }
  }

  /**
   * Calculate scale for fit-to-width
   */
  calculateFitToWidth(viewerWidth: number): number {
    const availableWidth = viewerWidth;
    const pdfPageWidth = 612; // Standard PDF page width in points
    const scale = availableWidth / pdfPageWidth;
    console.log(
      "[PDFZoom] Fit to width:",
      "viewer width:", viewerWidth,
      "available width:", availableWidth,
      "scale:", scale.toFixed(2)
    );
    return scale;
  }

  /**
   * Set zoom level
   */
  setScale(scale: number): number {
    if (scale < 0.5 || scale > 3.0) {
      console.warn("[PDFZoom] Scale must be between 0.5 and 3.0");
      return this.currentScale;
    }

    this.currentScale = scale;
    console.log("[PDFZoom] Scale changed to:", scale);

    // Save zoom level to localStorage
    const zoomPercent = Math.round(scale * 100);
    statePersistence.savePdfZoom(zoomPercent);
    console.log("[PDFZoom] Saved zoom to localStorage:", zoomPercent + "%");

    return scale;
  }

  /**
   * Zoom in
   */
  zoomIn(): number {
    return this.setScale(this.currentScale + 0.25);
  }

  /**
   * Zoom out
   */
  zoomOut(): number {
    return this.setScale(this.currentScale - 0.25);
  }

  /**
   * Fit to width
   */
  fitWidth(containerWidth: number): number {
    const newScale = (containerWidth - 40) / 612; // Standard PDF width
    return this.setScale(newScale);
  }

  /**
   * Fit to height
   */
  fitHeight(containerHeight: number): number {
    const newScale = (containerHeight - 40) / 792; // Standard PDF height
    return this.setScale(newScale);
  }

  /**
   * Update zoom dropdown in toolbar
   */
  updateZoomDropdown(zoomPercent: number): void {
    const zoomSelect = document.getElementById("pdf-zoom-select") as HTMLSelectElement;
    if (!zoomSelect) return;

    const predefinedZooms = [50, 75, 100, 125, 150, 200];

    // If exact match exists, select it
    const exactOption = Array.from(zoomSelect.options).find(
      opt => parseInt(opt.value) === zoomPercent
    );

    if (exactOption) {
      zoomSelect.value = zoomPercent.toString();
      console.log("[PDFZoom] Toolbar updated to exact zoom:", zoomPercent + "%");
    } else {
      // Add custom zoom value
      const customOption = document.createElement("option");
      customOption.value = zoomPercent.toString();
      customOption.text = zoomPercent + "%";
      customOption.selected = true;

      // Insert in sorted order
      let inserted = false;
      for (let i = 0; i < zoomSelect.options.length; i++) {
        const optValue = zoomSelect.options[i].value;
        if (optValue === "fit-width") continue;

        const numericValue = parseInt(optValue);
        if (zoomPercent < numericValue) {
          zoomSelect.add(customOption, i);
          inserted = true;
          break;
        }
      }
      if (!inserted) {
        zoomSelect.add(customOption);
      }

      // Remove old custom values
      for (let i = zoomSelect.options.length - 1; i >= 0; i--) {
        const optValue = zoomSelect.options[i].value;
        if (optValue === "fit-width") continue;

        const numericValue = parseInt(optValue);
        if (isNaN(numericValue)) continue;

        if (!predefinedZooms.includes(numericValue) && numericValue !== zoomPercent) {
          zoomSelect.remove(i);
        }
      }

      console.log("[PDFZoom] Toolbar updated with custom zoom:", zoomPercent + "%");
    }
  }

  /**
   * Setup mouse wheel zoom listener
   */
  setupMouseZoomListener(
    viewer: HTMLElement,
    onZoomChange: (scale: number) => void
  ): void {
    viewer.addEventListener("wheel", (e: WheelEvent) => {
      if (!e.ctrlKey && !e.metaKey) return;

      e.preventDefault();

      const delta = -e.deltaY / 100;
      const zoomFactor = 1 + delta * 0.1;

      let newScale = this.currentScale * zoomFactor;
      newScale = Math.max(0.5, Math.min(3.0, newScale));

      if (newScale !== this.currentScale) {
        console.log("[PDFZoom] Mouse wheel zoom:", (newScale * 100).toFixed(0) + "%");
        const finalScale = this.setScale(newScale);
        onZoomChange(finalScale);
      }
    }, { passive: false });

    console.log("[PDFZoom] Mouse wheel zoom enabled (Ctrl+Wheel)");
  }

  /**
   * Get current scale
   */
  getCurrentScale(): number {
    return this.currentScale;
  }

  /**
   * Should fit to width on initial load
   */
  shouldFitToWidth(): boolean {
    return this.fitToWidth && !statePersistence.getSavedPdfZoom();
  }
}

// EOF
