/**
 * Compilation State
 * Manages compilation state and current job tracking
 */

import { CompilationJob, CompilationCallbacks } from "./types.js";

export class CompilationState {
  private currentJob: CompilationJob | null = null;
  private isCompiling: boolean = false;
  private callbacks: CompilationCallbacks = {};
  private lastLogLength: number = 0;

  /**
   * Set current job
   */
  setCurrentJob(job: CompilationJob | null): void {
    this.currentJob = job;
  }

  /**
   * Get current job
   */
  getCurrentJob(): CompilationJob | null {
    return this.currentJob;
  }

  /**
   * Set compilation status
   */
  setCompiling(status: boolean): void {
    this.isCompiling = status;
  }

  /**
   * Check if currently compiling
   */
  getIsCompiling(): boolean {
    return this.isCompiling;
  }

  /**
   * Set callbacks
   */
  setCallbacks(callbacks: CompilationCallbacks): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  /**
   * Get callbacks
   */
  getCallbacks(): CompilationCallbacks {
    return this.callbacks;
  }

  /**
   * Set last log length (for incremental log updates)
   */
  setLastLogLength(length: number): void {
    this.lastLogLength = length;
  }

  /**
   * Get last log length
   */
  getLastLogLength(): number {
    return this.lastLogLength;
  }

  /**
   * Reset state
   */
  reset(): void {
    this.currentJob = null;
    this.isCompiling = false;
    this.lastLogLength = 0;
  }

  /**
   * Notify progress callback
   */
  notifyProgress(progress: number, status: string): void {
    console.log(`[Compilation] ${progress}% - ${status}`);
    if (this.callbacks.onProgress) {
      this.callbacks.onProgress(progress, status);
    }
  }

  /**
   * Notify completion callback
   */
  notifyComplete(jobId: string, pdfUrl: string): void {
    if (this.callbacks.onComplete) {
      this.callbacks.onComplete(jobId, pdfUrl);
    }
  }

  /**
   * Notify error callback
   */
  notifyError(error: string): void {
    console.error("[Compilation] Error:", error);
    if (this.callbacks.onError) {
      this.callbacks.onError(error);
    }
  }
}
