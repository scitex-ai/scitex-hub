/**
 * Compilation Full
 * Handles full manuscript compilation from workspace
 */

import { CompilationAPI } from "./compilation-api.js";
import { CompilationState } from "./compilation-state.js";
import { CompilationUI } from "./compilation-ui.js";
import { CompilationQueue } from "./compilation-queue.js";
import { CompilationOptions, CompilationJob } from "./types.js";
import { statusLamp } from "../status-lamp.js";

export class CompilationFull {
  private api: CompilationAPI;
  private state: CompilationState;
  private ui: CompilationUI;
  private queue: CompilationQueue;

  constructor(
    api: CompilationAPI,
    state: CompilationState,
    ui: CompilationUI,
    queue: CompilationQueue,
  ) {
    this.api = api;
    this.state = state;
    this.ui = ui;
    this.queue = queue;
  }

  /**
   * Compile full manuscript from workspace
   */
  async compile(options: CompilationOptions): Promise<CompilationJob | null> {
    if (this.state.getIsCompiling()) {
      console.warn("[CompilationFull] Compilation already in progress");
      return null;
    }

    this.state.setCompiling(true);
    statusLamp.startFullCompilation();

    this.state.notifyProgress(0, "Preparing full compilation...");

    try {
      const result = await this.api.compileFull(options, 300000);

      console.log("[CompilationFull] API Response:", result);

      if (result?.job_id) {
        // Job started, begin polling for status
        console.log(
          "[CompilationFull] Job started, polling status:",
          result.job_id,
        );
        this.queue.pollStatus(result.job_id, options.projectId);
        return { id: result.job_id, status: "processing", progress: 0 };
      } else if (result?.success === true) {
        // Old-style immediate response (backward compat)
        return this.handleImmediateSuccess(result);
      } else {
        const errorMsg =
          result?.error || result?.log || "Full compilation failed";
        console.error("[CompilationFull] Error:", errorMsg);
        statusLamp.fullCompilationError();

        // Show error
        this.ui.showError("Compilation failed", result?.log || errorMsg);

        this.ui.updateLogLine(
          "compilation-start-line",
          `[${new Date().toLocaleTimeString()}] ✗ Compilation failed`,
          "error",
        );
        this.ui.appendLog(`Error: ${errorMsg}`, "error");

        throw new Error(errorMsg);
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Full compilation failed";
      statusLamp.fullCompilationError();

      // Show error modal
      this.ui.showError(
        message,
        error instanceof Error ? error.stack || "" : "",
      );

      this.ui.updateLogLine(
        "compilation-start-line",
        `[${new Date().toLocaleTimeString()}] ✗ Error: ${message}`,
        "error",
      );

      this.state.notifyError(message);
      this.state.setCurrentJob(null);
      return null;
    } finally {
      this.state.setCompiling(false);
    }
  }

  /**
   * Handle immediate success response (backward compatibility)
   */
  private handleImmediateSuccess(result: any): CompilationJob {
    const job: CompilationJob = {
      id: "full",
      status: "completed",
      progress: 100,
    };
    this.state.setCurrentJob(job);
    statusLamp.fullCompilationSuccess();

    const pdfPath = result.output_pdf || result.pdf_path;
    console.log("[CompilationFull] PDF path:", pdfPath);

    // Show success
    if (pdfPath) {
      this.ui.showSuccess(pdfPath);
    }

    this.ui.updateLogLine(
      "compilation-start-line",
      `[${new Date().toLocaleTimeString()}] ✓ Compilation successful!`,
      "success",
    );
    this.ui.appendLog(`PDF generated: ${pdfPath}`, "info");

    if (pdfPath) {
      this.state.notifyComplete("full", pdfPath);
    }

    return job;
  }
}
