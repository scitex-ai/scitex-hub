/**
 * PDF Color Mode Module
 * Handles color mode initialization and switching
 */

import { PDFViewer } from "./viewer.js";
import { CompilationHandler } from "./compilation.js";

export class ColorModeManager {
  private viewer: PDFViewer;
  private compilationHandler: CompilationHandler;

  constructor(viewer: PDFViewer, compilationHandler: CompilationHandler) {
    this.viewer = viewer;
    this.compilationHandler = compilationHandler;
  }

  /**
   * Initialize color mode from localStorage or global theme
   */
  static initializeColorMode(): "light" | "dark" {
    const savedMode = localStorage.getItem("pdf-color-mode") as
      | ("light" | "dark")
      | null;
    if (savedMode === "dark" || savedMode === "light") {
      return savedMode;
    }

    // Default to global theme
    const globalTheme =
      document.documentElement.getAttribute("data-theme") ||
      localStorage.getItem("theme") ||
      "light";
    return globalTheme === "dark" ? "dark" : "light";
  }

  /**
   * Set PDF color mode and switch to themed PDF
   */
  async setColorMode(
    colorMode: "light" | "dark",
    content?: string,
    sectionId?: string,
  ): Promise<void> {
    const oldMode = this.viewer.getColorMode();
    console.log(
      "[ColorModeManager] Color mode changed from",
      oldMode,
      "to",
      colorMode,
    );

    // Update viewer color mode
    this.viewer.setColorMode(colorMode);

    // Force reload with new theme if we have a PDF displayed
    const currentPdfUrl = this.viewer.getCurrentPdfUrl();
    if (currentPdfUrl) {
      await this.handleColorModeSwitch(colorMode, currentPdfUrl, content, sectionId);
    }
  }

  /**
   * Handle color mode switch logic
   */
  private async handleColorModeSwitch(
    colorMode: "light" | "dark",
    currentPdfUrl: string,
    content?: string,
    sectionId?: string,
  ): Promise<void> {
    const match = currentPdfUrl.match(/preview-([^-]+)-(?:light|dark)\.pdf/);
    if (!match) return;

    const sectionName = match[1];
    const themedPdfUrl = this.compilationHandler.getThemedPdfUrl(
      sectionName,
      colorMode,
    );

    try {
      const response = await fetch(themedPdfUrl, { method: "HEAD" });
      if (response.ok) {
        console.log("[ColorModeManager] Themed PDF exists, displaying");
        this.viewer.displayPdf(themedPdfUrl + `?t=${Date.now()}`);
      } else if (content) {
        console.log("[ColorModeManager] Themed PDF not found, compiling");
        await this.compilationHandler.compileQuick(
          content,
          sectionId || `manuscript/${sectionName}`,
          colorMode,
        );
      } else {
        console.log(
          "[ColorModeManager] No themed PDF and no content, showing placeholder",
        );
        this.viewer.displayPlaceholder();
      }
    } catch {
      if (content) {
        console.log("[ColorModeManager] Compiling themed PDF");
        await this.compilationHandler.compileQuick(
          content,
          sectionId || `manuscript/${sectionName}`,
          colorMode,
        );
      } else {
        this.viewer.displayPlaceholder();
      }
    }
  }
}
