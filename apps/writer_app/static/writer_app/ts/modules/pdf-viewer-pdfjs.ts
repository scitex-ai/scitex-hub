/**
 * PDF.js Viewer for Writer App - Orchestrator
 * Coordinates PDF viewing modules for canvas-based rendering
 * Provides full control over scrollbars, themes, and rendering
 */

import { PDFLoader } from "./pdf-viewer/PDFLoader.js";
import { PDFRenderer } from "./pdf-viewer/PDFRenderer.js";
import { PDFNavigation } from "./pdf-viewer/PDFNavigation.js";
import { PDFZoom } from "./pdf-viewer/PDFZoom.js";
import { PDFScrollState } from "./pdf-viewer/PDFScrollState.js";
import { PDFMouseHandler } from "./pdf-viewer/PDFMouseHandler.js";
import { PDFTheme } from "./pdf-viewer/PDFTheme.js";

console.log("[DEBUG] pdf-viewer-pdfjs.ts loaded");

export interface PDFViewerOptions {
  containerId: string;
  colorMode?: "light" | "dark";
  fitToWidth?: boolean;
  onPageChange?: (pageNum: number) => void;
  renderQuality?: number;
}

export class PDFJSViewer {
  private container: HTMLElement | null;
  private loader: PDFLoader;
  private renderer: PDFRenderer;
  private navigation: PDFNavigation;
  private zoom: PDFZoom;
  private scrollState: PDFScrollState;
  private mouseHandler: PDFMouseHandler;
  private theme: PDFTheme;

  // Public mode property for external access
  public get currentMode(): "text" | "hand" | "zoom" {
    return this.mouseHandler.getMode();
  }

  public set currentMode(mode: "text" | "hand" | "zoom") {
    const viewer = this.renderer.getViewerElement();
    this.mouseHandler.setMode(mode, viewer || undefined);
  }

  constructor(options: PDFViewerOptions) {
    this.container = document.getElementById(options.containerId);

    // Initialize modules
    this.loader = new PDFLoader();
    this.renderer = new PDFRenderer(options.renderQuality, options.colorMode);
    this.navigation = new PDFNavigation(options.onPageChange);
    this.zoom = new PDFZoom(options.fitToWidth);
    this.scrollState = new PDFScrollState();
    this.mouseHandler = new PDFMouseHandler("text");
    this.theme = new PDFTheme(options.colorMode);

    console.log(
      "[PDFJSViewer] Initialized with container:",
      options.containerId,
      "theme:",
      options.colorMode,
      "quality:",
      (options.renderQuality ?? 4.0) + "x",
    );
  }

  /**
   * Load and render a PDF
   */
  async loadPDF(pdfUrl: string): Promise<void> {
    if (!this.container) {
      console.error("[PDFJSViewer] No container found");
      return;
    }

    try {
      console.log("[PDFJSViewer] Loading PDF:", pdfUrl, "theme:", this.theme.getColorMode());

      // Load document
      const pdfDoc = await this.loader.loadDocument(pdfUrl, this.container);

      // Calculate scale
      let scale = this.zoom.getCurrentScale();
      if (this.zoom.shouldFitToWidth()) {
        const viewer = this.renderer.getViewerElement();
        if (viewer) {
          scale = this.zoom.calculateFitToWidth(viewer.clientWidth);
          this.zoom.setScale(scale);

          // Update dropdown
          const zoomSelect = document.getElementById("pdf-zoom-select") as HTMLSelectElement;
          if (zoomSelect) {
            zoomSelect.value = "fit-width";
            console.log("[PDFJSViewer] Dropdown set to 'Fit to Width'");
          }
        }
      }

      // Render all pages
      await this.renderer.renderAllPages(
        pdfDoc,
        this.container,
        scale,
        this.theme.getColorMode()
      );

      // Setup interactions
      const viewer = this.renderer.getViewerElement();
      if (viewer) {
        this.setupInteractions(viewer);
        this.scrollState.restoreScrollPosition(viewer);
      }
    } catch (error) {
      console.error("[PDFJSViewer] Error loading PDF:", error);
      if (this.container) {
        this.container.innerHTML = `
          <div style="display: flex; align-items: center; justify-content: center; height: 100%; padding: 2rem; text-align: center; color: var(--color-danger-fg);">
            <div>
              <i class="fas fa-exclamation-triangle fa-2x mb-3"></i>
              <h5>Error Loading PDF</h5>
              <p>${error instanceof Error ? error.message : "Unknown error"}</p>
            </div>
          </div>
        `;
      }
    }
  }

  /**
   * Setup all interactions (scroll, zoom, mouse)
   */
  private setupInteractions(viewer: HTMLElement): void {
    // Navigation scroll tracking
    this.navigation.setupScrollListener(viewer);

    // Scroll position saving
    this.scrollState.setupScrollListener(viewer, () => {
      this.navigation.updateCurrentPageFromScroll(viewer);
    });

    // Mouse wheel zoom
    this.zoom.setupMouseZoomListener(viewer, (scale) => {
      this.setScale(scale);
    });

    // Mouse panning
    this.mouseHandler.setupMousePanListener(viewer);
  }

  /**
   * Set color mode and re-render
   */
  setColorMode(colorMode: "light" | "dark"): void {
    if (this.theme.getColorMode() === colorMode) return;

    const viewer = this.renderer.getViewerElement();
    if (viewer) {
      this.scrollState.saveScrollPositionTemporary(viewer);
    }

    this.theme.setColorMode(colorMode);
    this.renderer.setColorMode(colorMode);

    const pdfDoc = this.loader.getDocument();
    if (pdfDoc && this.container) {
      this.renderer.renderAllPages(
        pdfDoc,
        this.container,
        this.zoom.getCurrentScale(),
        colorMode
      ).then(() => {
        const newViewer = this.renderer.getViewerElement();
        if (newViewer) {
          this.setupInteractions(newViewer);
          this.scrollState.restoreScrollPosition(newViewer);
        }
      });
    }
  }

  /**
   * Set zoom level and re-render
   */
  setScale(scale: number): void {
    if (scale < 0.5 || scale > 3.0) return;

    const viewer = this.renderer.getViewerElement();
    if (viewer) {
      this.scrollState.saveScrollPositionTemporary(viewer);
    }

    const finalScale = this.zoom.setScale(scale);
    const zoomPercent = Math.round(finalScale * 100);
    this.zoom.updateZoomDropdown(zoomPercent);

    const pdfDoc = this.loader.getDocument();
    if (pdfDoc && this.container) {
      this.renderer.renderAllPages(
        pdfDoc,
        this.container,
        finalScale,
        this.theme.getColorMode()
      ).then(() => {
        const newViewer = this.renderer.getViewerElement();
        if (newViewer) {
          this.setupInteractions(newViewer);
          this.scrollState.restoreScrollPosition(newViewer);
        }
      });
    }
  }

  /**
   * Set render quality
   */
  setRenderQuality(quality: number): void {
    if (quality < 0.5 || quality > 5.0) {
      console.warn("[PDFJSViewer] Quality must be between 0.5 and 5.0");
      return;
    }

    const viewer = this.renderer.getViewerElement();
    if (viewer) {
      this.scrollState.saveScrollPositionTemporary(viewer);
    }

    this.renderer.setQuality(quality);

    const pdfDoc = this.loader.getDocument();
    if (pdfDoc && this.container) {
      this.renderer.renderAllPages(
        pdfDoc,
        this.container,
        this.zoom.getCurrentScale(),
        this.theme.getColorMode()
      ).then(() => {
        const newViewer = this.renderer.getViewerElement();
        if (newViewer) {
          this.setupInteractions(newViewer);
          this.scrollState.restoreScrollPosition(newViewer);
        }
      });
    }
  }

  // Zoom methods
  zoomIn(): void {
    const newScale = this.zoom.zoomIn();
    this.setScale(newScale);
  }

  zoomOut(): void {
    const newScale = this.zoom.zoomOut();
    this.setScale(newScale);
  }

  fitWidth(): void {
    if (!this.container) return;
    const newScale = this.zoom.fitWidth(this.container.clientWidth);
    this.setScale(newScale);
  }

  // Navigation methods
  gotoPage(pageNum: number): void {
    const totalPages = this.getPageCount();
    this.navigation.gotoPage(pageNum, totalPages);
  }

  // Getters
  getPageCount(): number {
    const pdfDoc = this.loader.getDocument();
    return pdfDoc ? pdfDoc.numPages : 0;
  }

  getCurrentPage(): number {
    return this.navigation.getCurrentPage();
  }

  getCurrentScale(): number {
    return this.zoom.getCurrentScale();
  }

  getCurrentScrollPosition(): { scrollTop: number; scrollLeft: number } | null {
    const viewer = this.renderer.getViewerElement();
    if (viewer) {
      return this.scrollState.getCurrentScrollPosition(viewer);
    }
    return null;
  }

  getColorMode(): "light" | "dark" {
    return this.theme.getColorMode();
  }

  getRenderQuality(): number {
    return this.renderer.getQuality();
  }
}

// EOF
