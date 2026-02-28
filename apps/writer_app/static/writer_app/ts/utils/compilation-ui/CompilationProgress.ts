/**
 * Compilation Progress Management
 * Targets the Details panel for all compilation UI.
 */

import { updateStatusLamp } from "./CompilationStatus";
import { setActiveLogType, getActiveLogType } from "./CompilationLogs";

/**
 * Show compilation progress — clears the Details panel log and expands
 * the relevant section.
 */
export function showCompilationProgress(
  title: string = "Compiling Manuscript",
): void {
  const logType = getActiveLogType();
  const sectionKey = logType === "preview" ? "preview-log" : "full-log";
  const detailsLogId =
    logType === "preview" ? "details-preview-log" : "details-full-log";
  const detailsLog = document.getElementById(detailsLogId);

  if (detailsLog) {
    detailsLog.textContent = "Starting compilation...\n";

    // Auto-expand the section
    const section = detailsLog.closest("[data-section]") as HTMLElement;
    if (section) {
      section.classList.remove("collapsed");
      try {
        const states = JSON.parse(
          localStorage.getItem("writer-details-sections") || "{}",
        );
        states[sectionKey] = false;
        localStorage.setItem("writer-details-sections", JSON.stringify(states));
      } catch {
        /* ignore */
      }
    }
  }

  // Update status lamp and slim progress
  updateStatusLamp("compiling", "Compiling...");
  updateSlimProgress(0, "Initializing...");
}

/**
 * Hide compilation progress — no-op since Details panel is persistent.
 */
export function hideCompilationProgress(): void {
  // Details panel is always visible; nothing to hide.
}

/**
 * Update compilation progress percentage.
 * Updates the slim progress bar and status lamp.
 */
export function updateCompilationProgress(
  percent: number,
  status: string,
): void {
  updateSlimProgress(percent, status);

  // Update details panel lamp text for active log type
  const logType = getActiveLogType();
  const lampId =
    logType === "preview" ? "details-preview-lamp" : "details-full-lamp";
  const lamp = document.getElementById(lampId);
  if (lamp && percent > 0 && percent < 100) {
    lamp.setAttribute("data-status", "compiling");
    lamp.title = `${percent}% — ${status}`;
  }
}

/**
 * Update slim progress bar (tqdm-style)
 */
export function updateSlimProgress(
  progress: number,
  status: string,
  eta?: string,
): void {
  const slimProgress = document.getElementById("compilation-slim-progress");
  const slimFill = document.getElementById("slim-progress-fill");
  const slimPercent = document.getElementById("slim-progress-percent");
  const slimStatus = document.getElementById("slim-progress-status");
  const slimEta = document.getElementById("slim-progress-eta");

  if (!slimProgress) return;

  if (slimFill) {
    slimFill.style.width = `${progress}%`;
  }
  if (slimPercent) {
    slimPercent.textContent = `${progress}%`;
  }
  if (slimStatus) {
    slimStatus.textContent = status;
  }
  if (slimEta && eta) {
    slimEta.textContent = eta;
  }

  // Hide after completion (with delay)
  if (progress === 100) {
    setTimeout(() => {
      if (slimProgress) {
        slimProgress.style.display = "none";
      }
    }, 2000);
  }
}
