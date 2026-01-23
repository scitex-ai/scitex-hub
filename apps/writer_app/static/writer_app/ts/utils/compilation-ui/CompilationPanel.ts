/**
 * Compilation Panel Management
 * Handles panel visibility, minimize/restore, and minimized status
 */

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
    minimizeBtn.title = "Minimize to background";
  }
}

/**
 * Update minimized compilation status
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
