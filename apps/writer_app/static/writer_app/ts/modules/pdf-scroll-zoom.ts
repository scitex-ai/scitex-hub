/**
 * PDF Scroll and Zoom Handler (Orchestrator)
 * Provides native PDF viewer-like interaction:
 * - Mouse wheel scrolling within PDF (doesn't scroll page)
 * - Ctrl+drag for zoom with cursor centering
 * - Zoom level indicator and controls
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom.ts loaded",
);

import {
  PDFZoomControl,
  PDFColorThemeManager,
  PDFScrollManager,
  PDFModeManager,
  PDFEventHandlers,
  PDFViewerObserver,
} from "./pdf-scroll-zoom/index.js";

import type {
  ZoomOptions,
  PDFColorMode,
  PDFColorTheme,
  PDFInteractionMode,
} from "./pdf-scroll-zoom/index.js";

export interface PDFScrollZoomOptions {
  containerId: string;
  minZoom?: number;
  maxZoom?: number;
  zoomStep?: number;
}

// Re-export types for backward compatibility
export type { PDFColorMode, PDFColorTheme };

export class PDFScrollZoomHandler {
  private container: HTMLElement | null;
  private zoomControl: PDFZoomControl;
  private colorTheme: PDFColorThemeManager;
  private scrollManager: PDFScrollManager;
  private modeManager: PDFModeManager;
  private eventHandlers: PDFEventHandlers;
  private viewerObserver: PDFViewerObserver;

  constructor(options: PDFScrollZoomOptions) {
    this.container = document.getElementById(options.containerId);

    console.log(
      "[PDFScrollZoom] Constructor called, containerId:",
      options.containerId,
    );
    console.log("[PDFScrollZoom] Container found:", !!this.container);

    // Initialize all managers
    const zoomOptions: ZoomOptions = {
      minZoom: options.minZoom || 50,
      maxZoom: options.maxZoom || 300,
      zoomStep: options.zoomStep || 10,
    };

    this.zoomControl = new PDFZoomControl(zoomOptions);
    this.colorTheme = new PDFColorThemeManager();
    this.scrollManager = new PDFScrollManager();
    this.modeManager = new PDFModeManager();
    this.eventHandlers = new PDFEventHandlers(
      this.container,
      this.zoomControl,
      this.modeManager
    );
    this.viewerObserver = new PDFViewerObserver(
      this.container,
      this.zoomControl,
      this.colorTheme,
      this.scrollManager
    );

    if (this.container) {
      // Try to find existing PDF viewer immediately
      const existingViewer = this.container.querySelector(
        ".pdf-preview-viewer",
      );
      console.log(
        "[PDFScrollZoom] Existing PDF viewer found:",
        !!existingViewer,
      );
      if (existingViewer) {
        const pdfViewer = existingViewer as HTMLElement;
        this.zoomControl.setPdfViewer(pdfViewer);
        this.colorTheme.setPdfViewer(pdfViewer);
        this.scrollManager.setPdfViewer(pdfViewer);
        this.modeManager.setPdfViewer(pdfViewer);
        this.eventHandlers.setPdfViewer(pdfViewer);
        console.log("[PDFScrollZoom] Set pdfViewer reference on construction");
      }

      this.setupEventListeners();
    } else {
      console.warn("[PDFScrollZoom] Container not found!");
    }
  }

  /**
   * Setup all event listeners and observers
   */
  private setupEventListeners(): void {
    if (!this.container) return;

    // Setup event handlers
    this.eventHandlers.setupEventListeners();

    // Setup mutation observer to detect PDF viewer changes
    this.viewerObserver.setupMutationObserver();

    // Setup viewer change callback to update event handlers
    this.viewerObserver.onViewerChange((viewer) => {
      this.eventHandlers.setPdfViewer(viewer);
      this.modeManager.setPdfViewer(viewer);
    });

    // Setup PDF zoom button controls
    this.zoomControl.setupZoomButtons();

    // Load saved zoom level
    this.zoomControl.loadSavedZoom();

    console.log("[PDFScrollZoom] Event listeners initialized");
  }

  /**
   * Toggle hand/pan mode (public method for toolbar button)
   */
  public toggleHandMode(): void {
    this.modeManager.toggleHandMode();
  }

  /**
   * Zoom in
   */
  zoomIn(): void {
    this.zoomControl.zoomIn();
  }

  /**
   * Zoom out
   */
  zoomOut(): void {
    this.zoomControl.zoomOut();
  }

  /**
   * Reset zoom to 125% (default)
   */
  resetZoom(): void {
    this.zoomControl.resetZoom();
  }

  /**
   * Set zoom to fit page width
   */
  fitToWidth(): void {
    this.zoomControl.fitToWidth();
  }

  /**
   * Set zoom to fit page height
   */
  fitToHeight(): void {
    this.zoomControl.fitToHeight();
  }

  /**
   * Get current zoom level
   */
  getCurrentZoom(): number {
    return this.zoomControl.getCurrentZoom();
  }

  /**
   * Cycle through available PDF color modes
   */
  cycleColorMode(): void {
    this.colorTheme.cycleColorMode();
  }

  /**
   * Alias for backward compatibility - toggle between light and dark
   */
  toggleColorMode(): void {
    this.colorTheme.toggleColorMode();
  }

  /**
   * Set PDF color mode explicitly
   */
  setColorMode(mode: PDFColorMode): void {
    this.colorTheme.setColorMode(mode);
  }

  /**
   * Get current color mode
   */
  getColorMode(): PDFColorMode {
    return this.colorTheme.getColorMode();
  }

  /**
   * Get available color modes
   */
  getAvailableColorModes(): { name: PDFColorMode; label: string }[] {
    return this.colorTheme.getAvailableColorModes();
  }

  /**
   * Register callback for color mode changes
   */
  onColorModeChange(callback: (colorMode: PDFColorMode) => void): void {
    this.colorTheme.onColorModeChange(callback);
  }

  /**
   * Observe PDF viewer changes and reinitialize
   * (Already handled by setupMutationObserver in setupEventListeners)
   */
  observePDFViewer(): void {
    this.viewerObserver.checkForExistingViewer();
  }
}
