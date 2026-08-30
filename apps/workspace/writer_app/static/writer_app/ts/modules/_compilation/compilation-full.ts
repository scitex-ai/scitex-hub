/**
 * Compilation Full
 * Handles full manuscript compilation from workspace
 */

import { CompilationAPI } from "./compilation-api";
import { CompilationHttpError } from "./compilation-http-error";
import { CompilationState } from "./compilation-state";
import { CompilationUI } from "./compilation-ui";
import { CompilationQueue } from "./compilation-queue";
import { CompilationOptions, CompilationJob } from "./types";
import { statusLamp } from "../status-lamp";

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

    // Initialize details panel log
    const detailsLog = document.getElementById("details-full-log");
    if (detailsLog) {
      detailsLog.innerHTML = `<div>Starting full compilation...</div>`;
    }

    this.state.notifyProgress(0, "Preparing full compilation...");

    let handedOffToPolling = false;

    try {
      const result = await this.api.compileFull(options, 300000);

      console.log("[CompilationFull] API Response:", result);

      if (result?.job_id) {
        // Job started, begin polling for status
        // Polling queue will call setCompiling(false) on completion/failure
        console.log(
          "[CompilationFull] Job started, polling status:",
          result.job_id,
        );
        handedOffToPolling = true;
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

      // Show error modal. A rejected request (403 read-only visitor, 404
      // missing project, 409 busy) carries the backend's own explanation;
      // a JS stack does not. Prefer the explanation — the stack of a
      // `throw new Error("HTTP 403")` told the user nothing.
      this.ui.showError(message, this.detailFor(error));

      this.ui.updateLogLine(
        "compilation-start-line",
        `[${new Date().toLocaleTimeString()}] ✗ Error: ${message}`,
        "error",
      );

      this.state.notifyError(message);
      this.state.setCurrentJob(null);
      return null;
    } finally {
      // Only reset compiling if not handed off to polling queue
      // Polling queue handles setCompiling(false) on completion/failure
      if (!handedOffToPolling) {
        this.state.setCompiling(false);
      }
    }
  }

  /**
   * The body text to show under the headline.
   *
   * For a structured rejection that is the backend's `detail` (plus the
   * conversion urls when it is the read-only visitor role); for anything
   * else it is the stack, which is all we have.
   */
  private detailFor(error: unknown): string {
    if (error instanceof CompilationHttpError) {
      const lines: string[] = [];
      if (error.detail && error.detail !== error.message) {
        lines.push(error.detail);
      }
      if (error.isReadonlyVisitor) {
        const signup = error.signupUrl || "/auth/signup/";
        const login = error.loginUrl || "/auth/login/";
        lines.push(`Sign up: ${signup}`);
        lines.push(`Log in: ${login}`);
      }
      return lines.join("\n");
    }
    return error instanceof Error ? error.stack || "" : "";
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
