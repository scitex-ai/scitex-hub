/**
 * Writer Compilation Module - Orchestrator
 * Handles LaTeX compilation and PDF generation
 * Coordinates between API, State, UI, Queue, Preview, and Full compilation modules
 */

import { ApiClient } from "@/utils/api";
import { CompilationAPI } from "./_compilation/compilation-api";
import { CompilationState } from "./_compilation/compilation-state";
import { CompilationUI } from "./_compilation/compilation-ui";
import { CompilationQueue } from "./_compilation/compilation-queue";
import { CompilationPreview } from "./_compilation/compilation-preview";
import { CompilationFull } from "./_compilation/compilation-full";
import type {
  CompilationOptions,
  CompilationJob,
  CompilationCallbacks,
} from "./_compilation/types";

// Re-export types for backward compatibility
export type { CompilationOptions };

/**
 * CompilationManager - Orchestrator
 * Coordinates all compilation operations through specialized modules
 */
export class CompilationManager {
  private apiClient: ApiClient;
  private api: CompilationAPI;
  private state: CompilationState;
  private ui: CompilationUI;
  private queue: CompilationQueue;
  private preview: CompilationPreview;
  private full: CompilationFull;

  constructor(apiBaseUrl: string = "") {
    this.apiClient = new ApiClient(apiBaseUrl);

    // Initialize modules
    this.api = new CompilationAPI();
    this.state = new CompilationState();
    this.ui = new CompilationUI();
    this.queue = new CompilationQueue(this.api, this.state, this.ui);
    this.preview = new CompilationPreview(this.api, this.state, this.ui);
    this.full = new CompilationFull(this.api, this.state, this.ui, this.queue);
  }

  /**
   * Compile preview (live editing with content)
   */
  async compilePreview(
    options: CompilationOptions,
  ): Promise<CompilationJob | null> {
    return this.preview.compile(options);
  }

  /**
   * Compile full manuscript from workspace (no content)
   */
  async compileFull(
    options: CompilationOptions,
  ): Promise<CompilationJob | null> {
    return this.full.compile(options);
  }

  /**
   * @deprecated Use compilePreview() or compileFull() instead
   */
  async compile(options: CompilationOptions): Promise<CompilationJob | null> {
    console.warn(
      "[Compilation] DEPRECATED: Use compilePreview() or compileFull() instead",
    );
    if (options.content) {
      return this.compilePreview(options);
    } else {
      return this.compileFull(options);
    }
  }

  /**
   * Get current job status
   */
  async getStatus(jobId: string): Promise<CompilationJob | null> {
    try {
      if (jobId === "local") {
        // Local synchronous job
        return this.state.getCurrentJob();
      }

      // This would be for async job polling (not currently used)
      return null;
    } catch (error) {
      console.error("[Compilation] Failed to get status:", error);
      return null;
    }
  }

  /**
   * Cancel compilation
   */
  async cancel(jobId: string): Promise<boolean> {
    return this.api.cancel(jobId);
  }

  /**
   * Check if currently compiling
   */
  getIsCompiling(): boolean {
    return this.state.getIsCompiling();
  }

  /**
   * Set progress callback
   */
  onProgress(callback: (progress: number, status: string) => void): void {
    this.state.setCallbacks({ onProgress: callback });
  }

  /**
   * Set completion callback
   */
  onComplete(callback: (jobId: string, pdfUrl: string) => void): void {
    this.state.setCallbacks({ onComplete: callback });
  }

  /**
   * Set error callback
   */
  onError(callback: (error: string) => void): void {
    this.state.setCallbacks({ onError: callback });
  }

  /**
   * Check for existing PDF
   */
  async checkExistingPDF(
    projectSlug: string,
    docType: string = "manuscript",
  ): Promise<string | null> {
    return this.api.checkExistingPDF(projectSlug, docType);
  }
}
