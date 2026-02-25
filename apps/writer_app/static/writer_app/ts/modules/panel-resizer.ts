/**
 * Panel Resizer Module
 * Handles draggable divider between editor and preview panels
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/panel-resizer.ts loaded",
);

import { statePersistence } from "./state-persistence";

/** Shared collapse threshold — panel collapses when width drops to this (px) */
const COLLAPSE_WIDTH = 40;

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
    console.log(
      "[PanelResizer] Forced resizer dimensions via JS (4px, transparent)",
    );

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
   * Smart-collapse a panel during drag
   */
  private smartCollapse(target: "editor" | "preview"): void {
    if (!this.leftPanel || !this.rightPanel || !this.resizer) return;

    const collapseTarget =
      target === "editor" ? this.leftPanel : this.rightPanel;
    const expandTarget = target === "editor" ? this.rightPanel : this.leftPanel;

    collapseTarget.classList.add("collapsed");
    collapseTarget.classList.remove("expanded");
    expandTarget.classList.add("expanded");
    expandTarget.classList.remove("collapsed");

    // Clear inline flex so CSS classes take effect
    collapseTarget.style.flex = "";
    collapseTarget.style.width = "";
    collapseTarget.style.flexShrink = "";
    collapseTarget.style.flexGrow = "";
    expandTarget.style.flex = "";
    expandTarget.style.width = "";
    expandTarget.style.flexShrink = "";
    expandTarget.style.flexGrow = "";

    // Hide resizer when collapsed
    this.resizer.style.display = "none";

    // Persist state
    const STORAGE_KEY_EDITOR = "scitex-writer-editor-expanded";
    const STORAGE_KEY_PREVIEW = "scitex-writer-preview-expanded";
    localStorage.setItem(STORAGE_KEY_EDITOR, String(target === "preview"));
    localStorage.setItem(STORAGE_KEY_PREVIEW, String(target === "editor"));

    // Update toggle button icons
    const editorToggle = document.getElementById("editor-toggle-btn");
    const previewToggle = document.getElementById("preview-toggle-btn");
    if (editorToggle) {
      editorToggle.title =
        target === "editor"
          ? "Expand editor"
          : "Collapse editor (Ctrl+Shift+E)";
    }
    if (previewToggle) {
      previewToggle.title =
        target === "preview"
          ? "Expand preview"
          : "Collapse preview (Ctrl+Shift+P)";
    }

    // Stop resizing
    this.isResizing = false;
    document.body.style.cursor = "";
    this.resizer.classList.remove("active");

    // Re-fit PDF after collapse
    setTimeout(() => {
      const pdfViewer = (window as any).pdfViewerInstance;
      if (pdfViewer && typeof pdfViewer.fitWidth === "function") {
        pdfViewer.fitWidth();
      }
      window.dispatchEvent(new Event("resize"));
    }, 350);

    console.log(`[PanelResizer] Smart-collapsed ${target} panel`);
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
    const newRightWidth = containerWidth - newLeftWidth;

    // Smart collapse: auto-collapse when dragged below threshold
    if (newLeftWidth < COLLAPSE_WIDTH) {
      this.smartCollapse("editor");
      return;
    }
    if (newRightWidth < COLLAPSE_WIDTH) {
      this.smartCollapse("preview");
      return;
    }

    const leftPercent = (newLeftWidth / containerWidth) * 100;
    const rightPercent = 100 - leftPercent;

    this.leftPanel.style.flex = `0 0 ${leftPercent}%`;
    this.rightPanel.style.flex = `0 0 ${rightPercent}%`;

    // Save preference to unified state persistence
    statePersistence.savePanelWidth(leftPercent);
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
    if (!this.leftPanel || !this.rightPanel) return;

    // Don't restore inline flex when panels are in collapsed/expanded state
    // panel-toggle.ts manages these states via CSS classes
    const hasCollapseState =
      this.leftPanel.classList.contains("collapsed") ||
      this.leftPanel.classList.contains("expanded") ||
      this.rightPanel.classList.contains("collapsed") ||
      this.rightPanel.classList.contains("expanded");

    if (hasCollapseState) {
      console.log(
        "[PanelResizer] Panel has collapsed/expanded state, skipping inline flex restore",
      );
      return;
    }

    const savedWidth = statePersistence.getSavedPanelWidth();
    if (savedWidth) {
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

      // Suppress transitions during restore to prevent load-time animation flash
      document.body.classList.add("no-transition");
      this.leftPanel.style.flex = `0 0 ${leftPercent}%`;
      this.rightPanel.style.flex = `0 0 ${rightPercent}%`;
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          document.body.classList.remove("no-transition");
        });
      });

      console.log("[PanelResizer] Restored panel width:", leftPercent + "%");
    } else {
      console.log(
        "[PanelResizer] No saved width, using default 50:50 (editor:preview)",
      );
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

    // Suppress transitions to avoid animation when resetting on init
    document.body.classList.add("no-transition");
    this.leftPanel.style.flex = `0 0 ${defaultLeftPercent}%`;
    this.rightPanel.style.flex = `0 0 ${defaultRightPercent}%`;
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.body.classList.remove("no-transition");
      });
    });
    statePersistence.savePanelWidth(defaultLeftPercent);

    console.log(
      `[PanelResizer] Reset to ${defaultLeftPercent}:${defaultRightPercent} split (editor:preview)`,
    );
  }

  /**
   * Check if the resizer is properly initialized
   */
  isInitialized(): boolean {
    return this._initialized;
  }
}
