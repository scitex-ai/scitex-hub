/**
 * PDF Mode Manager Module
 * Handles interaction modes (text/hand/zoom) and mode switching UI
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/pdf-scroll-zoom/pdf-mode-manager.ts loaded",
);

export type PDFInteractionMode = "text" | "hand" | "zoom";

export class PDFModeManager {
  private currentMode: PDFInteractionMode = "text"; // Default to text selection mode
  private isSpacePressed: boolean = false;
  private isWaitingForCommand: boolean = false;
  private commandTimeout: number | null = null;
  private pdfViewer: HTMLElement | null = null;

  /**
   * Set PDF viewer reference
   */
  setPdfViewer(viewer: HTMLElement | null): void {
    this.pdfViewer = viewer;
  }

  /**
   * Get current mode
   */
  getCurrentMode(): PDFInteractionMode {
    return this.currentMode;
  }

  /**
   * Get spacebar pressed state
   */
  isSpacePressedState(): boolean {
    return this.isSpacePressed;
  }

  /**
   * Set spacebar pressed state
   */
  setSpacePressed(pressed: boolean): void {
    this.isSpacePressed = pressed;
  }

  /**
   * Get command mode waiting state
   */
  isWaitingForCommandState(): boolean {
    return this.isWaitingForCommand;
  }

  /**
   * Toggle hand/pan mode (public method for toolbar button)
   */
  toggleHandMode(): void {
    if (this.currentMode === "hand") {
      this.setMode("text");
      this.showModeMessage("Text Selection Mode");
    } else {
      this.setMode("hand");
      this.showModeMessage("Hand/Pan Mode (press ESC to exit)");
    }
  }

  /**
   * Set interaction mode and sync with PDFJSViewer
   */
  setMode(mode: PDFInteractionMode): void {
    this.currentMode = mode;

    // Update local state
    if (mode === "hand") {
      this.isSpacePressed = true;
    } else {
      this.isSpacePressed = false;
    }

    // Update cursor
    if (this.pdfViewer) {
      this.pdfViewer.style.cursor = mode === "hand" ? "grab" :
                                    mode === "zoom" ? "crosshair" : "auto";
    }

    // Sync mode with PDFJSViewer if it exists
    const pdfjsViewer = document.getElementById("pdfjs-viewer");
    if (pdfjsViewer) {
      // Find PDFJSViewer instance via window object
      const pdfViewerInstance = (window as any).pdfViewerInstance;
      if (pdfViewerInstance && pdfViewerInstance.currentMode !== undefined) {
        pdfViewerInstance.currentMode = mode;
        console.log("[PDFModeManager] Synced mode to PDFJSViewer:", mode);
      }
      // Always update cursor on the viewer element
      pdfjsViewer.style.cursor = mode === "hand" ? "grab" :
                                 mode === "zoom" ? "crosshair" : "auto";
    }

    // Update toolbar button appearance
    const panBtn = document.getElementById("pdf-pan-mode-btn");
    if (panBtn) {
      if (mode === "hand") {
        panBtn.classList.add("active", "btn-primary");
        panBtn.classList.remove("btn-outline-secondary");
      } else {
        panBtn.classList.remove("active", "btn-primary");
        panBtn.classList.add("btn-outline-secondary");
      }
    }
  }

  /**
   * Enter command mode (Ctrl+Space)
   */
  enterCommandMode(): void {
    this.isWaitingForCommand = true;
    console.log("[PDFModeManager] 🎯 Command mode activated - Press T (text), H (hand), or Z (zoom)");

    // Show visual indicator
    this.showCommandModeIndicator();

    // Auto-exit command mode after 2 seconds if no command pressed
    if (this.commandTimeout) clearTimeout(this.commandTimeout);
    this.commandTimeout = window.setTimeout(() => {
      this.exitCommandMode();
      console.log("[PDFModeManager] Command mode timeout - exited");
    }, 2000);
  }

  /**
   * Exit command mode
   */
  exitCommandMode(): void {
    this.isWaitingForCommand = false;
    if (this.commandTimeout) clearTimeout(this.commandTimeout);
    this.hideCommandModeIndicator();
  }

  /**
   * Handle command key press
   */
  handleCommandKey(key: string): boolean {
    if (!this.isWaitingForCommand) return false;

    this.exitCommandMode();

    switch (key.toLowerCase()) {
      case "t":
        console.log("[PDFModeManager] 📝 Text selection mode activated");
        this.setMode("text");
        this.showModeMessage("Text Selection Mode");
        return true;
      case "h":
        console.log("[PDFModeManager] ✋ Hand/Pan mode activated");
        this.setMode("hand");
        this.showModeMessage("Hand/Pan Mode (press ESC to exit)");
        return true;
      case "z":
        console.log("[PDFModeManager] 🔍 Zoom mode activated - Use Ctrl+drag or Ctrl+wheel");
        this.setMode("zoom");
        this.showModeMessage("Zoom Mode - Use Ctrl+drag or Ctrl+wheel");
        return true;
      default:
        console.log("[PDFModeManager] Unknown command:", key);
        this.showModeMessage("Unknown command: " + key);
        return false;
    }
  }

  /**
   * Handle escape key - exit modes
   */
  handleEscapeKey(): boolean {
    if (this.isWaitingForCommand) {
      this.exitCommandMode();
      console.log("[PDFModeManager] Command mode cancelled");
      return true;
    } else if (this.currentMode !== "text") {
      // Reset to text selection mode
      this.setMode("text");
      this.showModeMessage("Text Selection Mode (default)");
      console.log("[PDFModeManager] Returned to text selection mode via Escape");
      return true;
    }
    return false;
  }

  /**
   * Show command mode indicator
   */
  private showCommandModeIndicator(): void {
    // Remove any existing indicator
    this.hideCommandModeIndicator();

    const indicator = document.createElement("div");
    indicator.id = "pdf-command-mode-indicator";
    indicator.innerHTML = `
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                  background: rgba(0, 0, 0, 0.8); color: white; padding: 1rem 2rem;
                  border-radius: 8px; z-index: 10000; font-size: 1.2rem;
                  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);">
        🎯 Command Mode: <kbd>T</kbd> Text | <kbd>H</kbd> Hand | <kbd>Z</kbd> Zoom
      </div>
    `;
    document.body.appendChild(indicator);
  }

  /**
   * Hide command mode indicator
   */
  private hideCommandModeIndicator(): void {
    const indicator = document.getElementById("pdf-command-mode-indicator");
    if (indicator) indicator.remove();
  }

  /**
   * Show temporary mode message
   */
  private showModeMessage(message: string): void {
    // Remove any existing message
    const existingMsg = document.getElementById("pdf-mode-message");
    if (existingMsg) existingMsg.remove();

    const msgDiv = document.createElement("div");
    msgDiv.id = "pdf-mode-message";
    msgDiv.innerHTML = `
      <div style="position: fixed; top: 20px; right: 20px;
                  background: rgba(59, 130, 246, 0.95); color: white;
                  padding: 0.75rem 1.5rem; border-radius: 6px; z-index: 10000;
                  font-size: 0.9rem; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
                  animation: slideInRight 0.3s ease;">
        ${message}
      </div>
      <style>
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      </style>
    `;
    document.body.appendChild(msgDiv);

    // Auto-remove after 3 seconds
    setTimeout(() => {
      if (msgDiv.parentNode) msgDiv.remove();
    }, 3000);
  }
}
