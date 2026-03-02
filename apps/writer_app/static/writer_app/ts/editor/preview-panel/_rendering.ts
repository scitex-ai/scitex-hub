/**
 * Preview Rendering Module
 * Handles PDF preview rendering and display
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/rendering.ts loaded",
);

import type { CompilationStatus } from "./types";

export class PreviewRenderer {
  private previewContent: HTMLElement;
  private compileStatus: HTMLElement;
  private statusIndicator: HTMLElement;

  constructor(
    previewContent: HTMLElement,
    compileStatus: HTMLElement,
    statusIndicator: HTMLElement,
  ) {
    this.previewContent = previewContent;
    this.compileStatus = compileStatus;
    this.statusIndicator = statusIndicator;
  }

  /**
   * Show PDF preview in iframe
   */
  showPDFPreview(pdfUrl: string): void {
    this.previewContent.innerHTML = `
            <iframe src="${pdfUrl}" width="100%" height="100%" class="iframe-borderless"></iframe>
        `;
  }

  /**
   * Update job status display
   */
  updateJobStatus(data: CompilationStatus): void {
    const message = `${data.status} (${data.progress}%)`;
    this.updateCompileStatus(message, data.status);
  }

  /**
   * Update status indicator
   */
  updateStatus(text: string, className: string): void {
    if (this.statusIndicator) {
      this.statusIndicator.innerHTML = `<i class="fas fa-circle ${className} me-1"></i>${text}`;
    }
  }

  /**
   * Update compilation status message
   */
  updateCompileStatus(text: string, type: string): void {
    if (this.compileStatus) {
      this.compileStatus.textContent = text;
      this.compileStatus.className = `compile-status ${type}`;
    }
  }

  /**
   * Handle compilation error
   */
  handleError(message: string): void {
    this.updateStatus("Error", "text-danger");
    this.updateCompileStatus("✗ " + message, "error");
  }

  /**
   * Show success message
   */
  showSuccess(): void {
    this.updateCompileStatus("✓ Compilation successful!", "success");
    this.updateStatus("Compiled", "text-success");
  }
}
