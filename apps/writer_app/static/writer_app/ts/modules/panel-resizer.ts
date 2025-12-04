/**
 * Panel Resizer Module
 * Handles draggable divider between editor and preview panels
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/panel-resizer.ts loaded",
);

import { statePersistence } from "./state-persistence.js";

export class PanelResizer {
  private resizer: HTMLElement | null;
  private leftPanel: HTMLElement | null;
  private rightPanel: HTMLElement | null;
  private container: HTMLElement | null;
  private isResizing: boolean = false;
  private startX: number = 0;
  private startLeftWidth: number = 0;
  private _initialized: boolean = false;

  constructor(containerId: string = "editor-view-split") {
    this.container = document.getElementById(containerId);
    this.resizer = document.getElementById("panel-resizer");
    this.leftPanel = document.querySelector(".latex-panel");
    this.rightPanel = document.querySelector(".preview-panel");

    if (this.resizer && this.container && this.leftPanel && this.rightPanel) {
      this.init();
    } else {
      console.warn("[PanelResizer] Required elements not found");
    }
  }

  /**
   * Initialize resizer event listeners
   */
  private init(): void {
    if (!this.resizer) return;

    // Force resizer to be visible (CSS might be overridden by other stylesheets)
    // Use 4px to match Scholar pattern (transparent by default, visible on hover)
    this.resizer.style.width = "4px";
    this.resizer.style.minWidth = "4px";
    this.resizer.style.maxWidth = "4px";
    this.resizer.style.height = "100%";
    this.resizer.style.flexShrink = "0";
    this.resizer.style.flexGrow = "0";
    this.resizer.style.background = "transparent";
    console.log("[PanelResizer] Forced resizer dimensions via JS (4px, transparent)");

    this.resizer.addEventListener("mousedown", (e) => this.handleMouseDown(e), {
      capture: true,
    });
    document.addEventListener("mousemove", (e) => this.handleMouseMove(e), {
      capture: true,
    });
    document.addEventListener("mouseup", () => this.handleMouseUp(), {
      capture: true,
    });

    this._initialized = true;
    this.restoreSavedWidth();
    console.log("[PanelResizer] Initialized");
  }

  /**
   * Handle mouse down on resizer
   */
  private handleMouseDown(e: MouseEvent): void {
    console.log("[PanelResizer] Mouse down on resizer");
    this.isResizing = true;
    this.startX = e.clientX;

    if (this.leftPanel && this.container) {
      this.startLeftWidth = this.leftPanel.getBoundingClientRect().width;
      console.log("[PanelResizer] Starting left width:", this.startLeftWidth);
    }

    if (this.resizer) {
      this.resizer.classList.add("active");
    }

    // Hide PDF iframe during resize for better performance
    const pdfIframe = document.querySelector(
      ".preview-panel iframe",
    ) as HTMLElement;
    const pdfViewer = document.querySelector(
      ".pdf-preview-viewer",
    ) as HTMLElement;
    if (pdfIframe) {
      pdfIframe.style.visibility = "hidden";
      console.log("[PanelResizer] PDF hidden for resize performance");

      // Set background color based on theme during resize
      if (pdfViewer) {
        const isDarkMode =
          document.documentElement.getAttribute("data-theme") === "dark";
        pdfViewer.style.backgroundColor = isDarkMode ? "#1a1a1a" : "#ffffff";
      }
    }

    // Set cursor for entire document during drag
    document.body.style.cursor = "col-resize";

    e.preventDefault();
    e.stopPropagation();
    console.log("[PanelResizer] Resize started at X:", this.startX);
  }

  /**
   * Handle mouse move during resize
   */
  private handleMouseMove(e: MouseEvent): void {
    if (
      !this.isResizing ||
      !this.leftPanel ||
      !this.rightPanel ||
      !this.container
    ) {
      return;
    }

    const deltaX = e.clientX - this.startX;
    const containerWidth = this.container.getBoundingClientRect().width;
    const newLeftWidth = this.startLeftWidth + deltaX;

    console.log(
      "[PanelResizer] Mouse move - deltaX:",
      deltaX,
      "newLeftWidth:",
      newLeftWidth,
    );

    // Minimum width for each panel (200px)
    const minWidth = 200;
    const maxLeftWidth = containerWidth - minWidth;

    if (newLeftWidth >= minWidth && newLeftWidth <= maxLeftWidth) {
      const leftPercent = (newLeftWidth / containerWidth) * 100;
      const rightPercent = 100 - leftPercent;

      console.log(
        "[PanelResizer] Setting widths - left:",
        leftPercent.toFixed(1) + "%",
        "right:",
        rightPercent.toFixed(1) + "%",
      );

      this.leftPanel.style.flex = `0 0 ${leftPercent}%`;
      this.rightPanel.style.flex = `0 0 ${rightPercent}%`;

      // Save preference to unified state persistence
      statePersistence.savePanelWidth(leftPercent);
    } else {
      console.log(
        "[PanelResizer] Width out of bounds - minWidth:",
        minWidth,
        "maxLeftWidth:",
        maxLeftWidth,
      );
    }
  }

  /**
   * Handle mouse up
   */
  private handleMouseUp(): void {
    if (this.isResizing) {
      console.log("[PanelResizer] Resize ended");
      this.isResizing = false;

      if (this.resizer) {
        this.resizer.classList.remove("active");
      }

      // Show PDF iframe again
      const pdfIframe = document.querySelector(
        ".preview-panel iframe",
      ) as HTMLElement;
      if (pdfIframe) {
        pdfIframe.style.visibility = "visible";
        console.log("[PanelResizer] PDF shown again");
      }

      // Reset cursor
      document.body.style.cursor = "";
    }
  }

  /**
   * Restore saved panel width from state persistence
   */
  restoreSavedWidth(): void {
    const savedWidth = statePersistence.getSavedPanelWidth();
    if (savedWidth && this.leftPanel && this.rightPanel) {
      const leftPercent = savedWidth;

      // Validate saved width (must be between 20% and 80%)
      if (leftPercent < 20 || leftPercent > 80) {
        console.log(
          "[PanelResizer] Saved width invalid:",
          leftPercent,
          "% - resetting to 50%",
        );
        this.resetToDefault();
        return;
      }

      const rightPercent = 100 - leftPercent;

      this.leftPanel.style.flex = `0 0 ${leftPercent}%`;
      this.rightPanel.style.flex = `0 0 ${rightPercent}%`;

      console.log("[PanelResizer] Restored panel width:", leftPercent + "%");
    } else {
      console.log("[PanelResizer] No saved width, using default 50:50 (editor:preview)");
      // Set default to 50:50 for balanced workspace
      this.resetToDefault();
    }
  }

  /**
   * Reset to default 50:50 split (editor:preview for balanced workspace)
   */
  resetToDefault(): void {
    if (!this.leftPanel || !this.rightPanel) return;

    const defaultLeftPercent = 50; // Balanced 50:50 split
    const defaultRightPercent = 50;

    this.leftPanel.style.flex = `0 0 ${defaultLeftPercent}%`;
    this.rightPanel.style.flex = `0 0 ${defaultRightPercent}%`;
    statePersistence.savePanelWidth(defaultLeftPercent);

    console.log(`[PanelResizer] Reset to ${defaultLeftPercent}:${defaultRightPercent} split (editor:preview)`);
  }

  /**
   * Check if the resizer is properly initialized
   */
  isInitialized(): boolean {
    return this._initialized;
  }
}
