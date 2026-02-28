/**
 * Compilation Status Management
 * Handles status lamp indicators and success/error states.
 * All visual feedback goes to the Details panel and status lamps.
 */

import { updateCompilationProgress } from "./CompilationProgress";
import { appendCompilationLog, getActiveLogType } from "./CompilationLogs";

/**
 * Show compilation success — updates status lamp and appends
 * a success entry to the Details panel log.
 */
export function showCompilationSuccess(pdfUrl: string): void {
  updateCompilationProgress(100, "Complete!");
  updateStatusLamp("success", "Success");

  // Update details panel lamp
  const logType = getActiveLogType();
  const lampId =
    logType === "preview" ? "details-preview-lamp" : "details-full-lamp";
  const lamp = document.getElementById(lampId);
  if (lamp) {
    lamp.setAttribute("data-status", "success");
    lamp.title = "Compilation successful";
  }

  // Append success line to the Details panel log
  appendCompilationLog(
    `\u2713 Compilation successful — View PDF: ${pdfUrl}`,
    "success",
  );
}

/**
 * Show compilation error — updates status lamp and appends
 * an error entry to the Details panel log.
 */
export function showCompilationError(
  errorMessage: string,
  errorDetails: string = "",
): void {
  updateStatusLamp("error", "Failed");

  // Update details panel lamp
  const logType = getActiveLogType();
  const lampId =
    logType === "preview" ? "details-preview-lamp" : "details-full-lamp";
  const lamp = document.getElementById(lampId);
  if (lamp) {
    lamp.setAttribute("data-status", "error");
    lamp.title = "Compilation failed";
  }

  // Append error line(s) to the Details panel log
  appendCompilationLog(`\u2717 ${errorMessage}`, "error");
  if (errorDetails) {
    appendCompilationLog(errorDetails, "error");
  }
}

/**
 * Update status lamp (LED indicator in the main editor toolbar)
 */
export function updateStatusLamp(
  status: "idle" | "compiling" | "success" | "error",
  text: string,
): void {
  const lamp = document.querySelector(".status-lamp-indicator") as HTMLElement;
  const lampText = document.querySelector(".status-lamp-text") as HTMLElement;

  if (lamp) {
    lamp.setAttribute("data-status", status);
  }
  if (lampText) {
    lampText.textContent = text;
  }

  // Persist status to localStorage
  localStorage.setItem(
    "scitex-compilation-status",
    JSON.stringify({ status, text, timestamp: Date.now() }),
  );
}
