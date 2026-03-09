/**
 * Figure State Module
 * Handles UI state display (loading, empty, no results)
 */

export class FigureState {
  constructor() {
    console.log("[FigureState] Initialized");
  }

  /**
   * Show loading state
   */
  showLoading(loadingId: string = "figures-loading"): void {
    this.hideAllStates();
    const loading = document.getElementById(loadingId);
    if (loading) {
      loading.style.display = "flex";
      console.log("[FigureState] Showing loading state");
    }
  }

  /**
   * Show empty state
   */
  showEmpty(emptyId: string = "figures-empty"): void {
    this.hideAllStates();
    const empty = document.getElementById(emptyId);
    if (empty) {
      empty.style.display = "flex";
      console.log("[FigureState] Showing empty state");
    }
  }

  /**
   * Show no results state
   */
  showNoResults(noResultsId: string = "figures-no-results"): void {
    this.hideAllStates();
    const noResults = document.getElementById(noResultsId);
    if (noResults) {
      noResults.style.display = "flex";
      console.log("[FigureState] Showing no results state");
    }
  }

  /**
   * Hide all states
   */
  hideAllStates(
    stateIds: string[] = [
      "figures-loading",
      "figures-empty",
      "figures-no-results",
    ],
  ): void {
    stateIds.forEach((id) => {
      const el = document.getElementById(id);
      if (el) {
        el.style.display = "none";
      }
    });
  }

  /**
   * Update count display
   */
  updateCountDisplay(
    selectedCount: number,
    totalCount: number,
    selectedCountId: string = "figures-selected-count-toolbar",
    totalCountId: string = "figures-total-for-selection-toolbar",
  ): void {
    const selectedCountEl = document.getElementById(selectedCountId);
    const totalCountEl = document.getElementById(totalCountId);

    if (selectedCountEl) {
      selectedCountEl.textContent = String(selectedCount);
    }

    if (totalCountEl) {
      totalCountEl.textContent = String(totalCount);
    }

    console.log(`[FigureState] Updated count: ${selectedCount}/${totalCount}`);
  }

  /**
   * Show error message
   */
  showError(
    message: string,
    containerId: string = "figures-cards-container",
  ): void {
    this.hideAllStates();
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `
        <div class="figure-error-state">
          <i class="fas fa-exclamation-circle"></i>
          <p>${message}</p>
        </div>
      `;
      console.error("[FigureState] Error:", message);
    }
  }

  /**
   * Show success message (temporary)
   */
  showSuccess(
    message: string,
    duration: number = 3000,
    containerId: string = "figures-success-message",
  ): void {
    let container = document.getElementById(containerId);

    if (!container) {
      container = document.createElement("div");
      container.id = containerId;
      container.className = "figure-success-message";
      document.body.appendChild(container);
    }

    container.textContent = message;
    container.style.display = "block";

    setTimeout(() => {
      container!.style.display = "none";
    }, duration);

    console.log("[FigureState] Success:", message);
  }

  /**
   * Toggle toolbar visibility
   */
  toggleToolbar(
    visible: boolean,
    toolbarId: string = "figures-toolbar",
  ): void {
    const toolbar = document.getElementById(toolbarId);
    if (toolbar) {
      toolbar.style.display = visible ? "flex" : "none";
    }
  }

  /**
   * Update loading progress
   */
  updateLoadingProgress(
    progress: number,
    progressBarId: string = "figures-loading-progress",
  ): void {
    const progressBar = document.getElementById(progressBarId);
    if (progressBar) {
      progressBar.style.width = `${Math.min(100, Math.max(0, progress))}%`;
    }
  }

  /**
   * Check if any state is visible
   */
  isStateVisible(stateId: string): boolean {
    const state = document.getElementById(stateId);
    return state ? state.style.display !== "none" : false;
  }

  /**
   * Get current visible state
   */
  getCurrentState(
    stateIds: string[] = [
      "figures-loading",
      "figures-empty",
      "figures-no-results",
    ],
  ): string | null {
    for (const id of stateIds) {
      if (this.isStateVisible(id)) {
        return id;
      }
    }
    return null;
  }
}
