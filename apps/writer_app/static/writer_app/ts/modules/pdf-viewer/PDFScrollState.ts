/**
 * PDF Scroll State Manager
 * Handles scroll position saving, restoring, and management
 */

import { statePersistence } from "../state-persistence.js";

console.log("[DEBUG] PDFScrollState.ts loaded");

export class PDFScrollState {
  private scrollSaveTimeout: number | null = null;
  private savedScrollPosition: { scrollTop: number; scrollLeft: number } | null = null;

  /**
   * Save scroll position to localStorage (debounced)
   */
  saveScrollPositionDebounced(viewer: HTMLElement): void {
    if (this.scrollSaveTimeout) {
      clearTimeout(this.scrollSaveTimeout);
    }

    this.scrollSaveTimeout = window.setTimeout(() => {
      const scrollTop = viewer.scrollTop;
      const scrollLeft = viewer.scrollLeft;
      statePersistence.savePdfScrollPosition(scrollTop, scrollLeft);
      console.log("[PDFScrollState] Saved scroll position:", { scrollTop, scrollLeft });
    }, 500);
  }

  /**
   * Setup scroll listener for saving position
   */
  setupScrollListener(viewer: HTMLElement, onScroll?: () => void): void {
    viewer.addEventListener("scroll", () => {
      this.saveScrollPositionDebounced(viewer);
      if (onScroll) {
        onScroll();
      }
    });

    console.log("[PDFScrollState] Scroll listener attached, will save position every 500ms");
  }

  /**
   * Restore scroll position from localStorage or temporary save
   */
  restoreScrollPosition(viewer: HTMLElement): void {
    // First try temporary saved position (during re-render)
    if (this.savedScrollPosition) {
      console.log("[PDFScrollState] Restoring scroll from temporary save:", this.savedScrollPosition);
      requestAnimationFrame(() => {
        viewer.scrollTop = this.savedScrollPosition!.scrollTop;
        viewer.scrollLeft = this.savedScrollPosition!.scrollLeft;
        console.log("[PDFScrollState] Scroll restored from temporary save");
        this.savedScrollPosition = null;
      });
      return;
    }

    // Otherwise restore from localStorage
    const savedPosition = statePersistence.getSavedPdfScrollPosition();
    if (savedPosition) {
      console.log("[PDFScrollState] Restoring scroll from localStorage:", savedPosition);
      requestAnimationFrame(() => {
        viewer.scrollTop = savedPosition.scrollTop;
        viewer.scrollLeft = savedPosition.scrollLeft;
        console.log("[PDFScrollState] Scroll restored from localStorage");
      });
    } else {
      console.log("[PDFScrollState] No saved scroll position found");
    }
  }

  /**
   * Save current scroll position temporarily (before re-render)
   */
  saveScrollPositionTemporary(viewer: HTMLElement): void {
    this.savedScrollPosition = {
      scrollTop: viewer.scrollTop,
      scrollLeft: viewer.scrollLeft,
    };
    console.log("[PDFScrollState] Saved scroll position temporarily:", this.savedScrollPosition);
  }

  /**
   * Get current scroll position
   */
  getCurrentScrollPosition(viewer: HTMLElement): { scrollTop: number; scrollLeft: number } {
    return {
      scrollTop: viewer.scrollTop,
      scrollLeft: viewer.scrollLeft,
    };
  }

  /**
   * Clear temporary saved position
   */
  clearTemporarySave(): void {
    this.savedScrollPosition = null;
  }
}

// EOF
