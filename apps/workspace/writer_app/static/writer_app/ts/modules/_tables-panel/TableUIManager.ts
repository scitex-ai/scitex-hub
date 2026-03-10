/**
 * Table UI Manager
 * Manages UI states (loading, empty, no results) and displays
 */

export class TableUIManager {
  /**
   * Update count display
   */
  updateCountDisplay(selectedCount: number, totalCount: number): void {
    const selectedCountEl = document.getElementById(
      "tables-selected-count-toolbar",
    );
    const totalCountEl = document.getElementById(
      "tables-total-for-selection-toolbar",
    );

    if (selectedCountEl) {
      selectedCountEl.textContent = String(selectedCount);
    }

    if (totalCountEl) {
      totalCountEl.textContent = String(totalCount);
    }
  }

  /**
   * Show loading state
   */
  showLoading(): void {
    this.hideAllStates();
    const loading = document.getElementById("tables-loading");
    if (loading) loading.style.display = "flex";
  }

  /**
   * Show empty state
   */
  showEmptyState(): void {
    this.hideAllStates();
    const empty = document.getElementById("tables-empty");
    if (empty) empty.style.display = "flex";
  }

  /**
   * Show no results state
   */
  showNoResults(): void {
    this.hideAllStates();
    const noResults = document.getElementById("tables-no-results");
    if (noResults) noResults.style.display = "flex";
  }

  /**
   * Hide all states
   */
  hideAllStates(): void {
    const states = ["tables-loading", "tables-empty", "tables-no-results"];
    states.forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.style.display = "none";
    });
  }
}
