/**
 * PDF Viewer Observer Module
 * Handles mutation observer and PDF viewer lifecycle management
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-viewer-observer.ts loaded",
);

import type { PDFZoomControl } from "./pdf-zoom-control.js";
import type { PDFColorThemeManager } from "./pdf-color-theme.js";
import type { PDFScrollManager } from "./pdf-scroll-manager.js";

export class PDFViewerObserver {
  private container: HTMLElement | null;
  private pdfViewer: HTMLElement | null = null;
  private zoomControl: PDFZoomControl;
  private colorTheme: PDFColorThemeManager;
  private scrollManager: PDFScrollManager;
  private onViewerChangeCallback?: (viewer: HTMLElement) => void;

  constructor(
    container: HTMLElement | null,
    zoomControl: PDFZoomControl,
    colorTheme: PDFColorThemeManager,
    scrollManager: PDFScrollManager
  ) {
    this.container = container;
    this.zoomControl = zoomControl;
    this.colorTheme = colorTheme;
    this.scrollManager = scrollManager;
  }

  /**
   * Get PDF viewer element
   */
  getPdfViewer(): HTMLElement | null {
    return this.pdfViewer;
  }

  /**
   * Setup mutation observer to track PDF viewer changes
   */
  setupMutationObserver(): void {
    if (!this.container) return;

    let observerCallCount = 0;

    const observer = new MutationObserver(() => {
      observerCallCount++;
      const currentViewer = this.container?.querySelector(
        ".pdf-preview-viewer",
      );

      // Log every mutation to debug
      if (observerCallCount % 10 === 0) {
        console.log(
          "[PDFViewerObserver] Observer called",
          observerCallCount,
          "times",
        );
      }

      // If viewer changed, update reference
      if (currentViewer && currentViewer !== this.pdfViewer) {
        console.log("[PDFViewerObserver] ========================================");
        console.log("[PDFViewerObserver] 🔄 MUTATION OBSERVER DETECTED CHANGE!");
        console.log("[PDFViewerObserver] Old pdfViewer:", this.pdfViewer);
        console.log("[PDFViewerObserver] New pdfViewer:", currentViewer);

        this.pdfViewer = currentViewer as HTMLElement;
        console.log("[PDFViewerObserver] ✓ pdfViewer reference updated");

        // Update references in all managers
        this.zoomControl.setPdfViewer(this.pdfViewer);
        this.colorTheme.setPdfViewer(this.pdfViewer);
        this.scrollManager.setPdfViewer(this.pdfViewer);

        // Restore saved zoom level instead of resetting to 100
        console.log("[PDFViewerObserver] Step 1: Loading saved zoom...");
        this.zoomControl.loadSavedZoom();

        // Restore saved scroll position and setup tracking
        console.log("[PDFViewerObserver] Step 2: Restoring scroll position...");
        this.scrollManager.restoreSavedScrollPosition();

        console.log("[PDFViewerObserver] Step 3: Setting up scroll tracking...");
        this.scrollManager.setupScrollTracking();

        console.log("[PDFViewerObserver] Step 4: Loading color mode...");
        this.colorTheme.loadColorModePreference();
        this.colorTheme.applyColorMode();
        this.colorTheme.updateColorModeButton();

        console.log("[PDFViewerObserver] PDF viewer dimensions:");
        console.log("[PDFViewerObserver]   scrollHeight:", this.pdfViewer?.scrollHeight);
        console.log("[PDFViewerObserver]   clientHeight:", this.pdfViewer?.clientHeight);
        console.log("[PDFViewerObserver] ✓ All restoration steps completed");
        console.log("[PDFViewerObserver] ========================================");

        // Notify callback
        if (this.onViewerChangeCallback) {
          this.onViewerChangeCallback(this.pdfViewer);
        }
      }
    });

    observer.observe(this.container, {
      childList: true,
      subtree: true,
      attributes: false,
      characterData: false,
    });

    console.log(
      "[PDFViewerObserver] Mutation observer setup on container:",
      this.container,
    );
  }

  /**
   * Check for existing PDF viewer on initialization
   */
  checkForExistingViewer(): void {
    if (!this.container) {
      console.warn("[PDFViewerObserver] No container found for observing");
      return;
    }

    // First, check if PDF viewer already exists
    const existingViewer = this.container.querySelector(".pdf-preview-viewer");
    if (existingViewer) {
      this.pdfViewer = existingViewer as HTMLElement;

      // Update references in all managers
      this.zoomControl.setPdfViewer(this.pdfViewer);
      this.colorTheme.setPdfViewer(this.pdfViewer);
      this.scrollManager.setPdfViewer(this.pdfViewer);

      // Restore saved zoom level instead of resetting to 100
      this.zoomControl.loadSavedZoom();

      this.colorTheme.loadColorModePreference();
      this.colorTheme.applyColorMode();
      this.colorTheme.updateColorModeButton();
      console.log("[PDFViewerObserver] Found existing PDF viewer");
    }

    // Load preference on first initialization
    // Note: Will default to global theme if no PDF-specific preference saved
    this.colorTheme.loadColorModePreference();

    // Apply the theme and update button icon immediately on page load
    this.colorTheme.applyColorMode();
    this.colorTheme.updateColorModeButton();
  }

  /**
   * Register callback for viewer changes
   */
  onViewerChange(callback: (viewer: HTMLElement) => void): void {
    this.onViewerChangeCallback = callback;
  }
}
