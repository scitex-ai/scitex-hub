/**
 * PDF Scroll Manager Module
 * Handles scroll position save/restore and scroll tracking
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-scroll-manager.ts loaded",
);

import { statePersistence } from "../state-persistence.js";

export class PDFScrollManager {
  private pdfViewer: HTMLElement | null = null;
  private scrollSaveTimeout: number | null = null;

  /**
   * Set PDF viewer reference
   */
  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  /**
   * Restore saved PDF scroll position
   * Waits for iframe to load before restoring
   */
  restoreSavedScrollPosition(): void {
    console.log("[PDFScrollManager] ----------------------------------------");
    console.log("[PDFScrollManager] restoreSavedScrollPosition() called");

    if (!this.pdfViewer) {
      console.log("[PDFScrollManager] ✗ No pdfViewer reference, cannot restore");
      return;
    }

    const savedPosition = statePersistence.getSavedPdfScrollPosition();
    if (!savedPosition) {
      console.log("[PDFScrollManager] No saved scroll position found");
      return;
    }

    console.log("[PDFScrollManager] Found saved position:", savedPosition);

    const iframe = this.pdfViewer.querySelector("iframe");
    if (!iframe) {
      console.log("[PDFScrollManager] ✗ No iframe found in pdfViewer");
      return;
    }

    console.log("[PDFScrollManager] Found iframe, setting up restoration...");

    // Wait for iframe to fully load before restoring scroll position
    const restoreScroll = () => {
      console.log("[PDFScrollManager] restoreScroll() function executing...");
      // Use multiple RAF calls to ensure PDF is fully rendered
      requestAnimationFrame(() => {
        console.log("[PDFScrollManager] First RAF");
        requestAnimationFrame(() => {
          console.log("[PDFScrollManager] Second RAF, applying scroll position...");
          if (this.pdfViewer) {
            this.pdfViewer.scrollTop = savedPosition.scrollTop;
            this.pdfViewer.scrollLeft = savedPosition.scrollLeft;
            console.log("[PDFScrollManager] ✓ Scroll position SET to:", {
              scrollTop: this.pdfViewer.scrollTop,
              scrollLeft: this.pdfViewer.scrollLeft
            });
            console.log("[PDFScrollManager] ✓ Successfully restored scroll position!");
          }
        });
      });
    };

    // If iframe already loaded, restore immediately
    if (iframe.contentDocument?.readyState === "complete") {
      console.log("[PDFScrollManager] Iframe contentDocument.readyState = 'complete', restoring immediately");
      restoreScroll();
    } else {
      console.log("[PDFScrollManager] Iframe not yet loaded, adding load event listener...");
      console.log("[PDFScrollManager] Current readyState:", iframe.contentDocument?.readyState);
      // Wait for iframe to load
      iframe.addEventListener("load", () => {
        console.log("[PDFScrollManager] ✓ Iframe 'load' event fired!");
        restoreScroll();
      }, { once: true });
    }
    console.log("[PDFScrollManager] ----------------------------------------");
  }

  /**
   * Save current PDF scroll position (debounced)
   */
  private saveScrollPosition(): void {
    if (!this.pdfViewer) return;

    // Debounce to avoid excessive saves
    if (this.scrollSaveTimeout) {
      clearTimeout(this.scrollSaveTimeout);
    }

    this.scrollSaveTimeout = window.setTimeout(() => {
      if (this.pdfViewer) {
        const scrollTop = this.pdfViewer.scrollTop;
        const scrollLeft = this.pdfViewer.scrollLeft;
        statePersistence.savePdfScrollPosition(scrollTop, scrollLeft);
        console.log("[PDFScrollManager] 💾 Saved scroll position to localStorage:", { scrollTop, scrollLeft });
      }
    }, 500); // Save after 500ms of no scrolling
  }

  /**
   * Setup scroll position tracking for PDF viewer
   */
  setupScrollTracking(): void {
    console.log("[PDFScrollManager] setupScrollTracking() called");

    if (!this.pdfViewer) {
      console.log("[PDFScrollManager] ✗ No pdfViewer, cannot setup tracking");
      return;
    }

    this.pdfViewer.addEventListener("scroll", () => {
      this.saveScrollPosition();
    });

    console.log("[PDFScrollManager] ✓ Scroll event listener attached to pdfViewer");
  }
}
