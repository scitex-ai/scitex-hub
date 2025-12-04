/**
 * Compilation Queue
 * Manages polling and status updates for async compilation jobs
 */

import { CompilationAPI } from "./compilation-api.js";
import { CompilationState } from "./compilation-state.js";
import { CompilationUI } from "./compilation-ui.js";
import { CompilationStatusData } from "./types.js";
import { statusLamp } from "../status-lamp.js";

export class CompilationQueue {
  private api: CompilationAPI;
  private state: CompilationState;
  private ui: CompilationUI;

  constructor(api: CompilationAPI, state: CompilationState, ui: CompilationUI) {
    this.api = api;
    this.state = state;
    this.ui = ui;
  }

  /**
   * Poll compilation status for real-time updates
   */
  async pollStatus(
    jobId: string,
    projectId: number,
    attempts: number = 0,
  ): Promise<void> {
    const maxAttempts = 300; // 5 minutes max (1 poll per second)

    if (attempts > maxAttempts) {
      console.error(
        "[CompilationQueue] Polling timeout after",
        attempts,
        "attempts",
      );
      this.ui.showError(
        "Compilation timeout",
        "Compilation took longer than expected",
      );
      return;
    }

    try {
      const data = (await this.api.getStatus(
        projectId,
        jobId,
      )) as CompilationStatusData;

      console.log(
        `[CompilationQueue] Poll #${attempts + 1}:`,
        data.status,
        data.progress + "%",
      );

      // Update progress
      if (data.progress !== undefined) {
        this.ui.updateProgress(data.progress, data.step || "Processing...");
      }

      // Append new logs
      this.appendNewLogs(data);

      // Check status
      if (data.status === "completed") {
        this.handleCompleted(data);
      } else if (data.status === "failed") {
        this.handleFailed(data);
      } else if (data.status === "processing" || data.status === "pending") {
        // Continue polling
        setTimeout(() => this.pollStatus(jobId, projectId, attempts + 1), 1000);
      }
    } catch (error) {
      console.error("[CompilationQueue] Polling error:", error);
      // Retry on error
      setTimeout(() => this.pollStatus(jobId, projectId, attempts + 1), 2000);
    }
  }

  /**
   * Append new logs from status update
   */
  private appendNewLogs(data: CompilationStatusData): void {
    const logDiv = document.getElementById("compilation-log-inline");
    if (!logDiv) return;

    if (data.log_html) {
      // Use HTML version for ANSI color support
      const existingLogLength = this.state.getLastLogLength();
      const newLogsHtml = data.log_html.substring(existingLogLength);

      if (newLogsHtml.trim()) {
        this.ui.appendIncrementalLog(newLogsHtml, true);
      }

      this.state.setLastLogLength(data.log_html.length);
    } else if (data.log) {
      // Fallback to plain text
      const existingLogLength = this.state.getLastLogLength();
      const newLogs = data.log.substring(existingLogLength);

      if (newLogs.trim()) {
        this.ui.appendIncrementalLog(newLogs, false);
      }

      this.state.setLastLogLength(data.log.length);
    }
  }

  /**
   * Handle completed compilation
   */
  private handleCompleted(data: CompilationStatusData): void {
    this.state.setCompiling(false);
    console.log("[CompilationQueue] Completed!");
    statusLamp.fullCompilationSuccess();

    const result = data.result || {};
    const pdfPath = result.output_pdf || result.pdf_path;

    // Update log
    this.ui.updateLogLine(
      "compilation-start-line",
      `[${new Date().toLocaleTimeString()}] ✓ Compilation completed successfully!`,
      "success",
    );

    if (pdfPath) {
      this.ui.showSuccess(pdfPath);
      this.state.notifyComplete("full", pdfPath);
    }
  }

  /**
   * Handle failed compilation
   */
  private handleFailed(data: CompilationStatusData): void {
    this.state.setCompiling(false);
    console.error("[CompilationQueue] Failed");
    statusLamp.fullCompilationError();

    // Update log
    this.ui.updateLogLine(
      "compilation-start-line",
      `[${new Date().toLocaleTimeString()}] ✗ Compilation failed`,
      "error",
    );

    const errorMsg = data.result?.error || "Compilation failed";
    const errorLog = data.log || "";
    this.ui.showError(errorMsg, errorLog);
  }
}
