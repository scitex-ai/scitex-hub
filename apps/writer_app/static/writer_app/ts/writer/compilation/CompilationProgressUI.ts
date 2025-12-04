/**
 * CompilationProgressUI.ts
 * Manages the compilation progress UI display, including progress bars,
 * modals, and success/error messages.
 */

import {
  updateMinimizedStatus,
  updateStatusLamp,
  updateSlimProgress,
} from "./CompilationStatusDisplay.js";

/**
 * Show compilation progress modal
 */
export function showCompilationProgress(
  title: string = "Compiling Manuscript",
): void {
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
  const logDetails = document.getElementById(
    "compilation-log-details",
  ) as HTMLDetailsElement;
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
export function updateCompilationProgress(
  percent: number,
  status: string,
): void {
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
 * Show compilation success
 */
export function showCompilationSuccess(pdfUrl: string): void {
  const icon = document.getElementById("compilation-icon");
  const progressContainer = document.getElementById(
    "compilation-progress-container",
  );
  const alertBanner = document.getElementById("compilation-alert-banner");
  const resultDiv = document.getElementById("compilation-result-inline");
  const minimizedStatus = document.getElementById(
    "minimized-compilation-status",
  );

  // Update icon to success
  if (icon) {
    icon.className = "fas fa-check-circle text-success";
  }

  // Hide progress bar
  if (progressContainer) {
    progressContainer.style.display = "none";
  }

  // Show success alert banner
  if (alertBanner) {
    alertBanner.style.display = "block";
    alertBanner.className = "alert-banner alert-banner-success";
    alertBanner.innerHTML = `
            <div class="warning-banner-content">
                <i class="fas fa-check-circle warning-banner-icon"></i>
                <div class="warning-banner-text">
                    <div class="warning-banner-title">Compilation Successful!</div>
                    <div class="warning-banner-description">
                        Your manuscript PDF has been generated.
                        <a href="${pdfUrl}" target="_blank" style="color: white; text-decoration: underline; margin-left: 0.5rem;">
                            <i class="fas fa-file-pdf me-1"></i>View PDF
                        </a>
                    </div>
                </div>
            </div>
        `;
  }

  // Keep old result div for backward compatibility (hide it)
  if (resultDiv) {
    resultDiv.style.display = "none";
  }

  updateCompilationProgress(100, "Complete!");

  // Update status lamp to success
  updateStatusLamp("success", "Success");

  // Update toolbar buttons: show Start, hide Stop
  const startBtn = document.getElementById("compilation-log-start-btn");
  const stopBtn = document.getElementById("compilation-log-stop-btn");
  if (startBtn) startBtn.style.display = "inline-block";
  if (stopBtn) stopBtn.style.display = "none";

  // Update minimized status icon to success
  if (minimizedStatus) {
    const icon = minimizedStatus.querySelector("i");
    if (icon) {
      icon.className = "fas fa-check-circle";
      icon.style.color = "var(--color-success-emphasis)";
    }
  }

  // Auto-hide minimized status after 3 seconds if compilation was successful
  setTimeout(() => {
    if (minimizedStatus && minimizedStatus.style.display !== "none") {
      minimizedStatus.style.display = "none";
    }
  }, 3000);
}

/**
 * Show compilation error
 */
export function showCompilationError(
  errorMessage: string,
  errorDetails: string = "",
): void {
  const icon = document.getElementById("compilation-icon");
  const progressContainer = document.getElementById(
    "compilation-progress-container",
  );
  const alertBanner = document.getElementById("compilation-alert-banner");
  const resultDiv = document.getElementById("compilation-result-inline");
  const minimizedStatus = document.getElementById(
    "minimized-compilation-status",
  );

  // Update icon to error
  if (icon) {
    icon.className = "fas fa-exclamation-circle text-danger";
  }

  // Hide progress bar
  if (progressContainer) {
    progressContainer.style.display = "none";
  }

  // Show error alert banner
  if (alertBanner) {
    alertBanner.style.display = "block";
    alertBanner.className = "alert-banner alert-banner-danger";
    alertBanner.innerHTML = `
            <div class="warning-banner-content">
                <i class="fas fa-exclamation-circle warning-banner-icon"></i>
                <div class="warning-banner-text">
                    <div class="warning-banner-title">Compilation Failed</div>
                    <div class="warning-banner-description">
                        ${errorMessage}
                        ${errorDetails ? "<br><small>Check the compilation log below for details.</small>" : ""}
                    </div>
                </div>
            </div>
        `;
  }

  // Keep old result div for backward compatibility (hide it)
  if (resultDiv) {
    resultDiv.style.display = "none";
  }

  // Update status lamp to error
  updateStatusLamp("error", "Failed");

  // Update toolbar buttons: show Start, hide Stop
  const startBtn = document.getElementById("compilation-log-start-btn");
  const stopBtn = document.getElementById("compilation-log-stop-btn");
  if (startBtn) startBtn.style.display = "inline-block";
  if (stopBtn) stopBtn.style.display = "none";

  // Update minimized status icon to error and make it clickable to see details
  if (minimizedStatus) {
    const icon = minimizedStatus.querySelector("i");
    const text = minimizedStatus.querySelector("#minimized-compilation-text");
    if (icon) {
      icon.className = "fas fa-exclamation-circle";
      icon.style.color = "var(--color-danger-emphasis)";
    }
    if (text) {
      text.textContent = "Failed";
    }
    // Keep minimized status visible so user can click to see error details
    minimizedStatus.title = "Click to view error details";
  }
}
