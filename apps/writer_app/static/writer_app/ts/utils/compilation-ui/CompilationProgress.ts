/**
 * Compilation Progress Management
 * Handles progress bars, percentages, and status updates
 */

import { updateStatusLamp } from "./CompilationStatus.js";
import { updateMinimizedStatus } from "./CompilationPanel.js";

/**
 * Show compilation progress UI
 */
export function showCompilationProgress(title: string = "Compiling Manuscript"): void {
  const output = document.getElementById("compilation-output");
  const icon = document.getElementById("compilation-icon");
  const headerTitle = document.getElementById("compilation-header-title");
  const progressContainer = document.getElementById(
    "compilation-progress-container",
  );
  const resultDiv = document.getElementById("compilation-result-inline");

  if (!output) return;

  // Update header
  if (icon) {
    icon.className = "fas fa-spinner fa-spin";
  }
  if (headerTitle) {
    headerTitle.textContent = title;
  }

  // Show progress bar
  if (progressContainer) {
    progressContainer.style.display = "block";
  }

  // Hide result
  if (resultDiv) {
    resultDiv.style.display = "none";
    resultDiv.innerHTML = "";
  }

  // Reset progress
  updateCompilationProgress(0, "Initializing...");

  // Clear log
  const log = document.getElementById("compilation-log-inline");
  if (log) {
    log.textContent = "Starting compilation...\n";
  }

  // Ensure log details are closed (minimized) by default
  const logDetails = document.getElementById("compilation-log-details") as HTMLDetailsElement;
  if (logDetails) {
    logDetails.open = false;
  }

  // Update toolbar buttons: show Stop, hide Start
  const startBtn = document.getElementById("compilation-log-start-btn");
  const stopBtn = document.getElementById("compilation-log-stop-btn");
  if (startBtn) startBtn.style.display = "none";
  if (stopBtn) stopBtn.style.display = "inline-block";

  // Show compilation output
  output.style.display = "block";

  // Update status lamp and slim progress
  updateStatusLamp("compiling", "Compiling...");
  updateSlimProgress(0, "Initializing...");
}

/**
 * Hide compilation output
 */
export function hideCompilationProgress(): void {
  const output = document.getElementById("compilation-output");
  if (output) {
    output.style.display = "none";
  }
}

/**
 * Update compilation progress
 */
export function updateCompilationProgress(percent: number, status: string): void {
  const progressBar = document.getElementById("compilation-progress-bar");
  const progressPercent = document.getElementById(
    "compilation-progress-percent",
  );
  const progressStatus = document.getElementById("compilation-progress-status");

  if (progressBar) progressBar.style.width = `${percent}%`;
  if (progressPercent) progressPercent.textContent = `${percent}%`;
  if (progressStatus) progressStatus.textContent = status;

  // Also update minimized status if it's visible
  updateMinimizedStatus(percent, status);

  // Update slim progress bar
  updateSlimProgress(percent, status);
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

  // DISABLED: Status lamp provides sufficient feedback, no need for progress bar
  // Show slim progress during compilation
  // if (progress > 0 && progress < 100) {
  //   slimProgress.style.display = "block";
  // }

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

/**
 * Toggle compilation details panel
 */
export function toggleCompilationDetails(): void {
  const output = document.getElementById("compilation-output");
  const slimProgress = document.getElementById("compilation-slim-progress");

  if (!output) return;

  const isVisible = output.style.display === "block";

  if (isVisible) {
    // Hide details (slim progress disabled - status lamp provides feedback)
    output.style.display = "none";
    // DISABLED: Status lamp provides sufficient feedback
    // if (slimProgress) {
    //   slimProgress.style.display = "block";
    // }
  } else {
    // Show full details
    output.style.display = "block";
    if (slimProgress) {
      slimProgress.style.display = "none";
    }
  }
}
