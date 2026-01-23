/**
 * CompilationStatusDisplay.ts
 * Manages status indicators including status lamp, slim progress bar,
 * and minimized status display.
 */

/**
 * Update minimized status text and progress
 */
export function updateMinimizedStatus(progress: number, status: string): void {
  const minimizedText = document.getElementById("minimized-compilation-text");
  const minimizedProgress = document.getElementById(
    "minimized-compilation-progress",
  );

  if (minimizedText) {
    minimizedText.textContent = status;
  }
  if (minimizedProgress) {
    minimizedProgress.textContent = `${progress}%`;
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

/**
 * Restore compilation status from previous session
 */
export function restoreCompilationStatus(): void {
  const stored = localStorage.getItem("scitex-compilation-status");
  if (!stored) {
    updateStatusLamp("idle", "Ready");
    return;
  }

  try {
    const { status, text, timestamp } = JSON.parse(stored);
    const ageMinutes = Math.floor((Date.now() - timestamp) / 1000 / 60);

    // Show status if less than 5 minutes old
    if (ageMinutes < 5) {
      updateStatusLamp(status, text);
    } else if (status === "success") {
      updateStatusLamp("success", `Done (${ageMinutes}m ago)`);
    } else {
      updateStatusLamp("idle", "Ready");
    }
  } catch (e) {
    updateStatusLamp("idle", "Ready");
  }
}

/**
 * Minimize compilation output to background status
 */
export function minimizeCompilationOutput(): void {
  const output = document.getElementById("compilation-output");
  const minimizedStatus = document.getElementById(
    "minimized-compilation-status",
  );
  const minimizeBtn = document.getElementById("minimize-compilation-output");

  if (!output) return;

  // Hide the full compilation output
  output.style.display = "none";

  // Show minimized status indicator
  if (minimizedStatus) {
    minimizedStatus.style.display = "flex";
  }

  // Update minimize button icon to restore icon
  if (minimizeBtn) {
    minimizeBtn.innerHTML = '<i class="fas fa-window-restore"></i>';
    minimizeBtn.title = "Restore compilation panel";
  }
}

/**
 * Restore compilation output from minimized state
 */
export function restoreCompilationOutput(): void {
  const output = document.getElementById("compilation-output");
  const minimizedStatus = document.getElementById(
    "minimized-compilation-status",
  );
  const minimizeBtn = document.getElementById("minimize-compilation-output");

  if (!output) return;

  // Show the full compilation output
  output.style.display = "block";

  // Hide minimized status indicator
  if (minimizedStatus) {
    minimizedStatus.style.display = "none";
  }

  // Update minimize button icon back to minimize icon
  if (minimizeBtn) {
    minimizeBtn.innerHTML = '<i class="fas fa-window-minimize"></i>';
    minimizeBtn.title = "Minimize compilation panel";
  }
}

/**
 * Toggle compilation panel visibility
 */
export function toggleCompilationPanel(
  type: "preview" | "full" = "full",
): void {
  const output = document.getElementById("compilation-output");
  if (!output) return;

  if (output.style.display === "none") {
    restoreCompilationOutput();
  } else {
    minimizeCompilationOutput();
  }
}
