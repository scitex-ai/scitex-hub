/**
 * Compilation Preview
 * Handles preview compilation (live editing with content)
 */

import { CompilationAPI } from "./compilation-api.js";
import { CompilationState } from "./compilation-state.js";
import { CompilationUI } from "./compilation-ui.js";
import { CompilationOptions, CompilationJob } from "./types.js";
import { statusLamp } from "../status-lamp.js";

export class CompilationPreview {
  private api: CompilationAPI;
  private state: CompilationState;
  private ui: CompilationUI;

  constructor(api: CompilationAPI, state: CompilationState, ui: CompilationUI) {
    this.api = api;
    this.state = state;
    this.ui = ui;
  }

  /**
   * Compile preview (live editing with content)
   */
  async compile(options: CompilationOptions): Promise<CompilationJob | null> {
    if (!options.content) {
      console.error("[CompilationPreview] Content is required for preview compilation");
      return null;
    }

    if (this.state.getIsCompiling()) {
      console.warn("[CompilationPreview] Compilation already in progress");
      return null;
    }

    this.state.setCompiling(true);
    statusLamp.startPreviewCompilation();
    this.state.notifyProgress(0, "Preparing preview...");

    // Initialize preview log
    this.ui.initializePreviewLog();

    try {
      const result = await this.api.compilePreview(options, 60000);

      console.log("[CompilationPreview] Result:", result.success);
      console.log(
        "[CompilationPreview] PDF URL from server:",
        result.output_pdf || result.pdf_path,
      );
      this.state.notifyProgress(50, "Compiling preview...");

      // Build log HTML
      let logHtml = this.ui.buildLogHtml(result);

      if (result?.success === true) {
        this.state.notifyProgress(100, "Preview ready");
        const job: CompilationJob = {
          id: "preview",
          status: "completed",
          progress: 100,
        };
        this.state.setCurrentJob(job);
        statusLamp.previewCompilationSuccess();

        const pdfPath = result.output_pdf || result.pdf_path;
        console.log("[CompilationPreview] Using PDF path:", pdfPath);

        // Append success message to log
        logHtml += this.ui.appendSuccessMessage();

        // Save preview log to global storage
        this.ui.savePreviewLog(logHtml);

        // Update log div if currently showing preview logs
        this.ui.updateLogDiv(logHtml, "preview");

        if (pdfPath) {
          this.state.notifyComplete("preview", pdfPath);
        }

        return job;
      } else {
        throw new Error(result?.error || "Preview compilation failed");
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Preview compilation failed";
      this.state.notifyError(message);
      statusLamp.previewCompilationError();

      // Build error log HTML
      const errorLogHtml = this.ui.appendErrorMessage(
        `Preview compilation failed: ${message}`,
      );

      // Save error to global storage
      const compilationLogs = (window as any).compilationLogs;
      if (compilationLogs) {
        const currentLog = compilationLogs.preview || "";
        compilationLogs.preview = currentLog + errorLogHtml;
      }

      // Update log div if currently showing preview logs
      this.ui.appendToLogDiv(errorLogHtml, "preview");

      this.state.setCurrentJob(null);
      return null;
    } finally {
      this.state.setCompiling(false);
    }
  }
}
