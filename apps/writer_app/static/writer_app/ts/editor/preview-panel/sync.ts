/**
 * Preview Sync Module
 * Handles synchronization between editor and preview
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/sync.ts loaded",
);

import type {
  CompilationData,
  CompilationResponse,
  CompilationStatus,
  PreviewPanelConfig,
} from "./types";
import { PreviewRenderer } from "./rendering";

export class PreviewSync {
  private config: PreviewPanelConfig;
  private renderer: PreviewRenderer;
  private compileBtn: HTMLButtonElement;
  private currentJobId: string | null = null;
  private statusCheckInterval: ReturnType<typeof setInterval> | null = null;

  constructor(
    config: PreviewPanelConfig,
    renderer: PreviewRenderer,
    compileBtn: HTMLButtonElement,
  ) {
    this.config = config;
    this.renderer = renderer;
    this.compileBtn = compileBtn;
  }

  /**
   * Compile LaTeX document to PDF
   */
  async compileDocument(content: string, title: string): Promise<void> {
    if (!content) {
      alert("Please enter some LaTeX content to compile.");
      return;
    }

    // Update UI
    this.compileBtn.disabled = true;
    this.compileBtn.innerHTML =
      '<i class="fas fa-spinner fa-spin me-2"></i>Compiling...';
    this.renderer.updateStatus("Compiling...", "text-warning");
    this.renderer.updateCompileStatus("Compilation started...", "running");

    // Send compile request
    try {
      const response = await fetch(this.config.quickCompileUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.config.csrfToken,
        },
        body: JSON.stringify({
          content: content,
          title: title,
        } as CompilationData),
      });

      const data: CompilationResponse = await response.json();

      if (data.success && data.job_id) {
        this.currentJobId = data.job_id;
        this.startStatusChecking();
      } else {
        this.handleError(data.error || "Compilation failed");
      }
    } catch (error) {
      this.handleError(
        "Network error: " +
          (error instanceof Error ? error.message : "Unknown error"),
      );
    }
  }

  /**
   * Start polling compilation status
   */
  private startStatusChecking(): void {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
    }

    this.statusCheckInterval = setInterval(async () => {
      if (!this.currentJobId) return;

      try {
        const url = this.config.compilationStatusUrl.replace(
          "__JOB_ID__",
          this.currentJobId,
        );
        const response = await fetch(url);
        const data: CompilationStatus = await response.json();

        this.renderer.updateJobStatus(data);

        if (data.status === "completed" || data.status === "failed") {
          if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
          }
          this.resetCompileUI();

          if (data.status === "completed" && data.pdf_url) {
            this.renderer.showPDFPreview(data.pdf_url);
            this.renderer.showSuccess();
          } else if (data.status === "failed") {
            this.handleError(data.error || "Compilation failed");
          }
        }
      } catch (error) {
        console.error("[PreviewSync] Status check error:", error);
      }
    }, 1000);
  }

  /**
   * Reset compile button UI
   */
  private resetCompileUI(): void {
    this.compileBtn.disabled = false;
    this.compileBtn.innerHTML = '<i class="fas fa-play me-2"></i>Compile PDF';
    this.currentJobId = null;
  }

  /**
   * Handle compilation error
   */
  private handleError(message: string): void {
    this.renderer.handleError(message);
    this.resetCompileUI();
  }

  /**
   * Cleanup and stop status checking
   */
  destroy(): void {
    if (this.statusCheckInterval) {
      clearInterval(this.statusCheckInterval);
    }
  }
}
