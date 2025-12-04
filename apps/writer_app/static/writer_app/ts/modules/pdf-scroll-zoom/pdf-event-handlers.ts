/**
 * PDF Event Handlers Module
 * Handles mouse, keyboard, and touch events for PDF interaction
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-event-handlers.ts loaded",
);

import type { PDFZoomControl } from "./pdf-zoom-control.js";
import type { PDFModeManager } from "./pdf-mode-manager.js";

export class PDFEventHandlers {
  private container: HTMLElement | null;
  private pdfViewer: HTMLElement | null = null;
  private isCtrlPressed: boolean = false;
  private isDraggingZoom: boolean = false;
  private isPanning: boolean = false;
  private dragStartX: number = 0;
  private dragStartY: number = 0;
  private dragStartZoom: number = 125;
  private panStartScrollTop: number = 0;
  private panStartScrollLeft: number = 0;
  private originalCursor: string = "";
  private zoomControl: PDFZoomControl;
  private modeManager: PDFModeManager;

  constructor(
    container: HTMLElement | null,
    zoomControl: PDFZoomControl,
    modeManager: PDFModeManager
  ) {
    this.container = container;
    this.zoomControl = zoomControl;
    this.modeManager = modeManager;
  }

  /**
   * Set PDF viewer reference
   */
  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  /**
   * Setup all event listeners for scroll and zoom
   */
  setupEventListeners(): void {
    if (!this.container) return;

    // Track Ctrl key state
    document.addEventListener("keydown", (e) => this.handleKeyDown(e));
    document.addEventListener("keyup", (e) => this.handleKeyUp(e));

    // Mouse wheel scrolling within PDF (use capture phase)
    this.container.addEventListener("wheel", (e) => this.handleWheel(e), true);

    // Also handle editor scrolling - find editor container and prioritize it
    const editorContainer = document.querySelector(".latex-panel");
    if (editorContainer) {
      editorContainer.addEventListener(
        "wheel",
        (e: any) => this.handleEditorWheel(e as WheelEvent),
        true,
      );
    }

    // Ctrl+drag for zoom
    document.addEventListener("mousedown", (e: any) =>
      this.handleMouseDown(e as MouseEvent),
    );
    document.addEventListener("mousemove", (e: any) =>
      this.handleMouseMove(e as MouseEvent),
    );
    document.addEventListener("mouseup", () => this.handleMouseUp());

    // Touch gestures for zoom (pinch)
    this.container.addEventListener(
      "touchstart",
      (e) => this.handleTouchStart(e),
      true,
    );
    this.container.addEventListener(
      "touchmove",
      (e) => this.handleTouchMove(e),
      true,
    );
    this.container.addEventListener(
      "touchend",
      (e) => this.handleTouchEnd(e),
      true,
    );

    console.log("[PDFEventHandlers] Event listeners initialized");
  }

  /**
   * Handle keyboard - track Ctrl key
   */
  private handleKeyDown(e: KeyboardEvent): void {
    if (e.key === "Control" || e.key === "Meta") {
      this.isCtrlPressed = true;
    }

    // Ctrl+Space: Enter command mode (prefix key)
    if (this.isCtrlPressed && e.key === " " && !this.modeManager.isWaitingForCommandState()) {
      e.preventDefault();
      this.modeManager.enterCommandMode();
      return;
    }

    // Handle commands when in command mode
    if (this.modeManager.isWaitingForCommandState()) {
      e.preventDefault();
      this.modeManager.handleCommandKey(e.key);
      return;
    }

    // Escape: Exit hand/zoom mode to text mode, or cancel command mode
    if (e.key === "Escape") {
      this.modeManager.handleEscapeKey();
      return;
    }

    // Spacebar: activate hand/pan tool (like PDF Studio)
    if (e.key === " " && !this.modeManager.isSpacePressedState() && !this.isCtrlPressed) {
      this.modeManager.setSpacePressed(true);
      // Change cursor to grab/hand when spacebar is held
      if (this.pdfViewer) {
        this.originalCursor = this.pdfViewer.style.cursor;
        this.pdfViewer.style.cursor = "grab";
      }
      console.log("[PDFEventHandlers] Spacebar pressed - Hand tool activated");
    }

    // Only handle zoom shortcuts when focus is on PDF viewer or preview panel
    const activeElement = document.activeElement;
    const previewPanel = document.querySelector('.preview-panel');
    const isOverPDF = this.pdfViewer && (
      activeElement === this.pdfViewer ||
      activeElement?.closest('.preview-panel') !== null ||
      this.pdfViewer.contains(activeElement) ||
      (previewPanel && previewPanel.contains(activeElement))
    );

    // Ctrl + Plus: zoom in (only when over PDF)
    if (this.isCtrlPressed && (e.key === "+" || e.key === "=") && isOverPDF) {
      e.preventDefault();
      this.zoomControl.zoomIn();
    }

    // Ctrl + Minus: zoom out (only when over PDF)
    if (this.isCtrlPressed && e.key === "-" && isOverPDF) {
      e.preventDefault();
      this.zoomControl.zoomOut();
    }

    // Ctrl + 0: reset zoom (only when over PDF)
    if (this.isCtrlPressed && e.key === "0" && isOverPDF) {
      e.preventDefault();
      this.zoomControl.resetZoom();
    }
  }

  /**
   * Handle keyboard - untrack Ctrl key
   */
  private handleKeyUp(e: KeyboardEvent): void {
    if (e.key === "Control" || e.key === "Meta") {
      this.isCtrlPressed = false;
    }

    // Spacebar released: deactivate hand/pan tool
    if (e.key === " " && this.modeManager.isSpacePressedState()) {
      this.modeManager.setSpacePressed(false);
      // Restore original cursor
      if (this.pdfViewer && !this.isPanning) {
        this.pdfViewer.style.cursor = this.originalCursor || "auto";
      }
      console.log("[PDFEventHandlers] Spacebar released - Hand tool deactivated");
    }
  }

  /**
   * Handle mouse wheel - ALWAYS prioritize PDF scroll
   * Don't prevent default - let CSS handle scrolling, just check if we're over PDF
   */
  private handleWheel(e: WheelEvent): void {
    if (!this.container) return;
    if (!this.pdfViewer) return;

    const isOverPDF = this.container.contains(e.target as Node);
    if (!isOverPDF) return;

    // DON'T prevent default - let browser handle native scrolling
    // The CSS will make the PDF viewer scrollable with overflow-y: scroll
    // This allows native smooth scrolling
  }

  /**
   * Handle mouse wheel for editor - just tracking, let CSS handle scrolling
   */
  private handleEditorWheel(e: WheelEvent): void {
    const editorContainer = e.currentTarget as HTMLElement;
    if (!editorContainer) return;

    // Check if target is actually inside the editor
    if (!editorContainer.contains(e.target as Node)) return;

    // DON'T prevent default - let browser handle native scrolling
    // The CSS will make the editor scrollable
  }

  /**
   * Handle mouse down - start zoom drag or panning
   */
  private handleMouseDown(e: MouseEvent): void {
    if (!this.container) return;

    const isOverPDF = this.container.contains(e.target as Node);
    if (!isOverPDF) return;

    const currentMode = this.modeManager.getCurrentMode();

    // Spacebar + left click OR middle mouse button OR hand mode for panning
    // But NOT in text selection mode
    const canPan = (e.button === 0 && this.modeManager.isSpacePressedState()) ||
                   (e.button === 1) ||
                   (e.button === 0 && currentMode === "hand");

    if (canPan && currentMode !== "text") {
      e.preventDefault();
      this.isPanning = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;

      // Save current scroll position
      const textPreview = this.container.querySelector(".text-preview");
      if (textPreview) {
        this.panStartScrollTop = textPreview.scrollTop;
        this.panStartScrollLeft = textPreview.scrollLeft;
      }

      // Change cursor to indicate pan mode
      if (this.pdfViewer) {
        this.originalCursor = this.pdfViewer.style.cursor;
        this.pdfViewer.style.cursor = "grabbing";
      }

      console.log("[PDFEventHandlers] Starting pan mode");
      return;
    }

    // Ctrl + left mouse button for zoom drag
    if (e.button === 0 && this.isCtrlPressed) {
      e.preventDefault();
      this.isDraggingZoom = true;
      this.dragStartX = e.clientX;
      this.dragStartY = e.clientY;
      this.dragStartZoom = this.zoomControl.getCurrentZoom();

      console.log("[PDFEventHandlers] Starting zoom drag from:", this.dragStartZoom);

      // Change cursor to indicate zoom mode
      if (this.pdfViewer) {
        this.originalCursor = this.pdfViewer.style.cursor;
        this.pdfViewer.style.cursor = "grabbing";
      }
    }
  }

  /**
   * Handle mouse move - drag zoom or panning
   */
  private handleMouseMove(e: MouseEvent): void {
    // Handle panning
    if (this.isPanning && this.container) {
      const textPreview = this.container.querySelector(".text-preview");
      if (textPreview) {
        const deltaX = e.clientX - this.dragStartX;
        const deltaY = e.clientY - this.dragStartY;

        // Pan by adjusting scroll position (inverted for natural feel)
        textPreview.scrollTop = this.panStartScrollTop - deltaY;
        textPreview.scrollLeft = this.panStartScrollLeft - deltaX;
      }
      return;
    }

    // Handle zoom drag
    if (!this.isDraggingZoom || !this.pdfViewer) return;

    // Use both X and Y delta for better zoom control (diagonal drag for better UX)
    const deltaY = this.dragStartY - e.clientY;
    const deltaX = e.clientX - this.dragStartX;
    const delta = deltaY + deltaX * 0.5; // Y movement is primary, X is secondary
    const zoomStep = 10;
    const zoomDelta = (delta / 100) * zoomStep;
    const minZoom = 50;
    const maxZoom = 300;
    const newZoom = Math.max(
      minZoom,
      Math.min(maxZoom, this.dragStartZoom + zoomDelta),
    );

    this.zoomControl.setZoom(newZoom, e.clientX, e.clientY);
  }

  /**
   * Handle mouse up - end zoom drag or panning
   */
  private handleMouseUp(): void {
    // End panning
    if (this.isPanning) {
      this.isPanning = false;
      if (this.pdfViewer) {
        this.pdfViewer.style.cursor = this.originalCursor || "auto";
      }
      console.log("[PDFEventHandlers] Ended pan mode");
    }

    // End zoom drag
    if (this.isDraggingZoom) {
      this.isDraggingZoom = false;
      if (this.pdfViewer) {
        this.pdfViewer.style.cursor = this.originalCursor || "auto";
      }
    }
  }

  /**
   * Handle touch start - start pinch zoom
   */
  private handleTouchStart(e: TouchEvent): void {
    if (e.touches.length !== 2) return;
    e.preventDefault();

    const touch1 = e.touches[0];
    const touch2 = e.touches[1];
    const distance = Math.hypot(
      touch2.clientX - touch1.clientX,
      touch2.clientY - touch1.clientY,
    );

    (e as any).pinchStartDistance = distance;
    (e as any).pinchStartZoom = this.zoomControl.getCurrentZoom();
  }

  /**
   * Handle touch move - pinch zoom
   */
  private handleTouchMove(e: TouchEvent): void {
    if (e.touches.length !== 2 || !(e as any).pinchStartDistance) return;
    e.preventDefault();

    const touch1 = e.touches[0];
    const touch2 = e.touches[1];
    const distance = Math.hypot(
      touch2.clientX - touch1.clientX,
      touch2.clientY - touch1.clientY,
    );

    const zoomRatio = distance / (e as any).pinchStartDistance;
    const centerX = (touch1.clientX + touch2.clientX) / 2;
    const centerY = (touch1.clientY + touch2.clientY) / 2;

    const minZoom = 50;
    const maxZoom = 300;
    const newZoom = Math.max(
      minZoom,
      Math.min(maxZoom, (e as any).pinchStartZoom * zoomRatio),
    );
    this.zoomControl.setZoom(newZoom, centerX, centerY);
  }

  /**
   * Handle touch end
   */
  private handleTouchEnd(e: TouchEvent): void {
    (e as any).pinchStartDistance = null;
    (e as any).pinchStartZoom = null;
  }
}
