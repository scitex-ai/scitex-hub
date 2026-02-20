/**
 * PDF Mode Manager Module
 * Handles interaction modes (text/hand/zoom) and mode switching UI.
 * Ctrl+Space command mode has been removed — use the toolbar button to toggle hand mode.
 */

export type PDFInteractionMode = "text" | "hand" | "zoom";

export class PDFModeManager {
  private currentMode: PDFInteractionMode = "text";
  private isSpacePressed: boolean = false;
  private pdfViewer: HTMLElement | null = null;

  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  getCurrentMode(): PDFInteractionMode {
    return this.currentMode;
  }

  isSpacePressedState(): boolean {
    return this.isSpacePressed;
  }

  setSpacePressed(pressed: boolean): void {
    this.isSpacePressed = pressed;
  }

  /** Toggle hand/pan mode — called by the toolbar button. */
  toggleHandMode(): void {
    if (this.currentMode === "hand") {
      this.setMode("text");
    } else {
      this.setMode("hand");
    }
  }

  /** Set interaction mode and sync cursor + toolbar button state. */
  setMode(mode: PDFInteractionMode): void {
    this.currentMode = mode;
    this.isSpacePressed = mode === "hand";

    const cursor =
      mode === "hand" ? "grab" : mode === "zoom" ? "crosshair" : "auto";

    if (this.pdfViewer) {
      this.pdfViewer.style.cursor = cursor;
    }

    const pdfjsViewer = document.getElementById("pdfjs-viewer");
    if (pdfjsViewer) {
      const instance = (window as any).pdfViewerInstance;
      if (instance?.currentMode !== undefined) {
        instance.currentMode = mode;
      }
      pdfjsViewer.style.cursor = cursor;
    }

    const panBtn = document.getElementById("pdf-pan-mode-btn");
    if (panBtn) {
      panBtn.classList.toggle("active", mode === "hand");
      panBtn.classList.toggle("btn-primary", mode === "hand");
      panBtn.classList.toggle("btn-outline-secondary", mode !== "hand");
    }
  }

  /** Handle Escape — return to text mode if in another mode. */
  handleEscapeKey(): boolean {
    if (this.currentMode !== "text") {
      this.setMode("text");
      return true;
    }
    return false;
  }
}
