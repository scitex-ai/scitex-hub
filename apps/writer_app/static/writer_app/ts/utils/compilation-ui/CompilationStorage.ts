/**
 * Compilation Storage Management
 * Handles localStorage persistence and status restoration
 */

import { updateStatusLamp } from "./CompilationStatus.js";

/**
 * Restore last compilation status from localStorage
 */
export function restoreCompilationStatus(): void {
  const saved = localStorage.getItem("scitex-compilation-status");
  if (!saved) {
    updateStatusLamp("idle", "Ready");
    return;
  }

  try {
    const { status, text, timestamp } = JSON.parse(saved);
    const ageMs = Date.now() - timestamp;
    const ageMinutes = Math.floor(ageMs / 60000);

    // If status is recent (< 5 minutes), show it
    if (ageMinutes < 5) {
      updateStatusLamp(status, text);
    } else if (status === "success") {
      // Show successful compilation even if old
      updateStatusLamp("success", `Done (${ageMinutes}m ago)`);
    } else {
      // Reset to idle
      updateStatusLamp("idle", "Ready");
    }
  } catch (e) {
    console.warn("[Compilation] Failed to restore status:", e);
    updateStatusLamp("idle", "Ready");
  }
}
