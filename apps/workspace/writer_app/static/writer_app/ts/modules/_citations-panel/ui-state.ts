/**
 * UI State Module
 * Manages UI states (loading, empty, no results) and count displays
 */

export class UIState {
  /**
   * Show loading state
   */
  public showLoading(): void {
    this.hideAllStates();
    const loading = document.getElementById("citations-loading");
    if (loading) loading.style.display = "flex";
  }

  /**
   * Show empty state
   */
  public showEmptyState(): void {
    this.hideAllStates();
    const empty = document.getElementById("citations-empty");
    if (empty) empty.style.display = "flex";
  }

  /**
   * Show no results state
   */
  public showNoResults(): void {
    this.hideAllStates();
    const noResults = document.getElementById("citations-no-results");
    if (noResults) noResults.style.display = "flex";
  }

  /**
   * Hide all states
   */
  public hideAllStates(): void {
    ["citations-loading", "citations-empty", "citations-no-results"].forEach(
      (id) => {
        const el = document.getElementById(id);
        if (el) el.style.display = "none";
      },
    );
  }

  /**
   * Update count display in toolbar
   */
  public updateCountDisplay(
    selectedCount: number,
    totalCount: number,
  ): void {
    const selectedCountEl = document.getElementById(
      "citations-selected-count-toolbar",
    );
    const totalForSelectionEl = document.getElementById(
      "citations-total-for-selection-toolbar",
    );

    if (selectedCountEl) {
      selectedCountEl.textContent = String(selectedCount);
    }

    if (totalForSelectionEl) {
      totalForSelectionEl.textContent = String(totalCount);
    }
  }
}
