/**
 * Compilation Status Management
 * Handles status indicators, success/error states, and alert banners
 */

import { updateCompilationProgress } from "./CompilationProgress.js";

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

/**
 * Update status lamp (LED indicator)
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
