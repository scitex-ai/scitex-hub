/**
 * Compilation UI
 * Handles UI updates for compilation operations
 */

import { CompilationResult } from "./types.js";

export class CompilationUI {
  /**
   * Initialize preview log
   */
  initializePreviewLog(): string {
    const logHtml = "<div>Starting preview compilation...</div>";

    // Save to global storage
    const compilationLogs = (window as any).compilationLogs;
    if (compilationLogs) {
      compilationLogs.preview = logHtml;
    }

    // Update log div if currently showing preview
    this.updateLogDiv(logHtml, "preview");

    return logHtml;
  }

  /**
   * Update log div
   */
  updateLogDiv(content: string, logType: string): void {
    const logDiv = document.getElementById("compilation-log-inline");
    const output = document.getElementById("compilation-output");

    if (logDiv && output?.getAttribute("data-log-type") === logType) {
      logDiv.innerHTML = content;
      logDiv.scrollTop = logDiv.scrollHeight;
    }
  }

  /**
   * Append to log div
   */
  appendToLogDiv(content: string, logType: string): void {
    const logDiv = document.getElementById("compilation-log-inline");
    const output = document.getElementById("compilation-output");

    if (logDiv && output?.getAttribute("data-log-type") === logType) {
      logDiv.innerHTML += content;
      logDiv.scrollTop = logDiv.scrollHeight;
    }
  }

  /**
   * Build log HTML from result
   */
  buildLogHtml(result: CompilationResult): string {
    let logHtml = "";

    if (result.log) {
      if (result.log_html) {
        // Server provides HTML-formatted log (ANSI colors converted)
        logHtml = result.log_html;
      } else {
        // Plain text log - convert to HTML
        const logLines = result.log.split("\n");
        logLines.forEach((line: string) => {
          logHtml += `<div>${line || " "}</div>`;
        });
      }
    }

    return logHtml;
  }

  /**
   * Save preview log
   */
  savePreviewLog(logHtml: string): void {
    const compilationLogs = (window as any).compilationLogs;
    if (compilationLogs) {
      compilationLogs.preview = logHtml;
    }
  }

  /**
   * Append success message to log
   */
  appendSuccessMessage(message: string = "Preview compilation completed successfully"): string {
    return `<div style="color: var(--color-success-fg); margin-top: 0.5rem;">✓ ${message}</div>`;
  }

  /**
   * Append error message to log
   */
  appendErrorMessage(message: string): string {
    return `<div style="color: var(--color-danger-fg); margin-top: 0.5rem; font-weight: bold;">✗ ${message}</div>`;
  }

  /**
   * Show compilation progress modal
   */
  showProgressModal(title: string, message: string): void {
    const showProgress = (window as any).showCompilationProgress;
    if (showProgress) {
      showProgress(title, message);
    }
  }

  /**
   * Update compilation progress
   */
  updateProgress(progress: number, step: string): void {
    const updateProgress = (window as any).updateCompilationProgress;
    if (updateProgress) {
      updateProgress(progress, step);
    }
  }

  /**
   * Show compilation success
   */
  showSuccess(pdfPath: string): void {
    const showSuccess = (window as any).showCompilationSuccess;
    if (showSuccess) {
      showSuccess(pdfPath);
    }
  }

  /**
   * Show compilation error
   */
  showError(message: string, log: string = ""): void {
    const showError = (window as any).showCompilationError;
    if (showError) {
      showError(message, log);
    }
  }

  /**
   * Append to compilation log
   */
  appendLog(message: string, type: string = "info", options?: any): void {
    const appendLog = (window as any).appendCompilationLog;
    if (appendLog) {
      appendLog(message, type, options);
    }
  }

  /**
   * Update specific log line
   */
  updateLogLine(lineId: string, message: string, type: string): void {
    const updateLog = (window as any).updateCompilationLog;
    if (updateLog) {
      updateLog(lineId, message, type);
    }
  }

  /**
   * Append incremental log updates
   */
  appendIncrementalLog(
    newLogsHtml: string,
    isHtml: boolean = true,
  ): void {
    const logDiv = document.getElementById("compilation-log-inline");
    if (!logDiv) return;

    if (isHtml && newLogsHtml.trim()) {
      // Append HTML directly (ANSI codes converted to colored spans)
      const newContent = document.createElement("span");
      newContent.innerHTML = newLogsHtml;
      logDiv.appendChild(newContent);
      logDiv.appendChild(document.createTextNode("\n"));

      // Auto-scroll
      logDiv.scrollTop = logDiv.scrollHeight;
    } else if (!isHtml && newLogsHtml.trim()) {
      // Fallback to plain text
      const appendLog = (window as any).appendCompilationLog;
      if (appendLog) {
        newLogsHtml
          .trim()
          .split("\n")
          .forEach((line) => {
            appendLog(line);
          });
      }
    }
  }
}
