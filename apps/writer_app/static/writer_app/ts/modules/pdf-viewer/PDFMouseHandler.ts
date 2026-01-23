/**
 * PDF Mouse Interaction Handler
 * Handles mouse dragging, panning, and mode switching (text/hand/zoom)
 */

console.log("[DEBUG] PDFMouseHandler.ts loaded");

export class PDFMouseHandler {
  private isDragging: boolean = false;
  private startX: number = 0;
  private startY: number = 0;
  private scrollLeft: number = 0;
  private scrollTop: number = 0;
  public currentMode: "text" | "hand" | "zoom" = "text";

  constructor(mode?: "text" | "hand" | "zoom") {
    this.currentMode = mode ?? "text";
  }

  /**
   * Setup mouse panning (click and drag)
   */
  setupMousePanListener(viewer: HTMLElement): void {
    // Default cursor based on mode
    this.updateCursor(viewer);

    // Mouse down - start dragging
    viewer.addEventListener("mousedown", (e: MouseEvent) => {
      const canPan = (e.button === 0 && this.currentMode === "hand") || e.button === 1;
      if (!canPan) return;

      e.preventDefault();
      this.isDragging = true;
      this.startX = e.pageX - viewer.offsetLeft;
      this.startY = e.pageY - viewer.offsetTop;
      this.scrollLeft = viewer.scrollLeft;
      this.scrollTop = viewer.scrollTop;

      viewer.style.cursor = "grabbing";
      viewer.style.userSelect = "none";

      console.log("[PDFMouseHandler] Panning started (mode:", this.currentMode, ")");
    });

    // Mouse move - pan if dragging
    viewer.addEventListener("mousemove", (e: MouseEvent) => {
      if (!this.isDragging) return;

      e.preventDefault();

      const x = e.pageX - viewer.offsetLeft;
      const y = e.pageY - viewer.offsetTop;
      const walkX = (x - this.startX) * 1.5;
      const walkY = (y - this.startY) * 1.5;

      viewer.scrollLeft = this.scrollLeft - walkX;
      viewer.scrollTop = this.scrollTop - walkY;
    });

    // Mouse up - stop dragging
    const stopDragging = () => {
      if (this.isDragging) {
        console.log("[PDFMouseHandler] Panning stopped");
      }
      this.isDragging = false;
      this.updateCursor(viewer);
      viewer.style.userSelect = "";
    };

    viewer.addEventListener("mouseup", stopDragging);
    viewer.addEventListener("mouseleave", stopDragging);

    console.log("[PDFMouseHandler] Mouse panning enabled (click and drag)");
  }

  /**
   * Update cursor based on current mode
   */
  private updateCursor(viewer: HTMLElement): void {
    if (this.currentMode === "hand") {
      viewer.style.cursor = "grab";
    } else if (this.currentMode === "zoom") {
      viewer.style.cursor = "crosshair";
    } else {
      viewer.style.cursor = "auto";
    }
  }

  /**
   * Set interaction mode
   */
  setMode(mode: "text" | "hand" | "zoom", viewer?: HTMLElement): void {
    this.currentMode = mode;
    console.log("[PDFMouseHandler] Mode changed to:", mode);

    if (viewer) {
      this.updateCursor(viewer);
    }
  }

  /**
   * Get current mode
   */
  getMode(): "text" | "hand" | "zoom" {
    return this.currentMode;
  }

  /**
   * Check if currently dragging
   */
  isDraggingActive(): boolean {
    return this.isDragging;
  }
}

// EOF
