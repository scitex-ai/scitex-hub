/**
 * PDF Preview Events Module
 * Handles event listeners and callbacks
 */

import { CompilationManager } from "../compilation.js";
import { PDFViewer } from "./viewer.js";

export class EventHandler {
  private compilationManager: CompilationManager;
  private viewer: PDFViewer;

  constructor(compilationManager: CompilationManager, viewer: PDFViewer) {
    this.compilationManager = compilationManager;
    this.viewer = viewer;
  }

  /**
   * Setup event listeners for compilation
   */
  setupEventListeners(): void {
    this.setupProgressListener();
    this.setupCompleteListener();
    this.setupErrorListener();
  }

  /**
   * Setup progress event listener
   */
  private setupProgressListener(): void {
    this.compilationManager.onProgress((progress, status) => {
      this.viewer.updateProgress(progress, status);
    });
  }

  /**
   * Setup completion event listener
   */
  private setupCompleteListener(): void {
    this.compilationManager.onComplete((_jobId, pdfUrl) => {
      this.viewer.displayPdf(pdfUrl);
    });
  }

  /**
   * Setup error event listener
   */
  private setupErrorListener(): void {
    this.compilationManager.onError((error) => {
      this.viewer.displayError(error);
    });
  }
}
