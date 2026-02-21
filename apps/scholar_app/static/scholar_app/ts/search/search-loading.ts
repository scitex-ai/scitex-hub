/**
 * Search Loading Display Module
 *
 * Shows inspiring quotes during search loading.
 * Delegates to the shared inspiring-spinner component.
 */

import {
  startInspiringSpinner,
  type SpinnerHandle,
} from "../../../../../../static/shared/ts/components/inspiring-spinner";

let spinnerHandle: SpinnerHandle | null = null;

/**
 * Generate the loading HTML (for backward compat with progressive results)
 */
export function getLoadingHtml(): string {
  return '<div class="search-loading"></div>';
}

/**
 * Show loading state in the progressive results container
 */
export function showSearchLoading(): void {
  const progressiveResults = document.getElementById("progressiveResults");
  if (progressiveResults) {
    progressiveResults.style.display = "block";
    progressiveResults.innerHTML = '<div class="search-loading"></div>';
    const loadingEl = progressiveResults.querySelector(
      ".search-loading",
    ) as HTMLElement;
    if (loadingEl) {
      spinnerHandle = startInspiringSpinner(loadingEl);
    }
  }
}

/**
 * Hide loading state
 */
export function hideSearchLoading(): void {
  spinnerHandle?.stop();
  spinnerHandle = null;

  const loadingEl = document.querySelector(".search-loading");
  if (loadingEl) {
    loadingEl.remove();
  }
}
