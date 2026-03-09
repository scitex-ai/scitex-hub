/**
 * PltzStatisticsManager - Handles pltz bundle statistics loading and rendering
 *
 * Extracted from PropertiesManager to reduce file size and improve modularity.
 */

export class PltzStatisticsManager {
  /**
   * Load statistics for pltz bundle
   */
  public async loadStatistics(pltzPath: string): Promise<void> {
    const container = document.getElementById("pltz-stats-container");
    if (!container) return;

    try {
      const response = await fetch(
        `/apps/vis/api/bundles/pltz/stats/?path=${encodeURIComponent(pltzPath)}`,
      );

      if (!response.ok) {
        this.renderPlaceholder(container);
        return;
      }

      const stats = await response.json();
      this.renderStatistics(container, stats);
    } catch (error) {
      console.warn("[PltzStatisticsManager] Failed to load statistics:", error);
      container.innerHTML = `
                <div class="pltz-stats-error">
                    Unable to load statistics
                </div>`;
    }
  }

  /**
   * Render statistics placeholder when API not available
   */
  private renderPlaceholder(container: HTMLElement): void {
    container.innerHTML = `
            <div class="pltz-stats-grid">
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">N points</div>
                    <div class="pltz-stat-value">-</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Mean</div>
                    <div class="pltz-stat-value">-</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Std</div>
                    <div class="pltz-stat-value">-</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Range</div>
                    <div class="pltz-stat-value">-</div>
                </div>
            </div>
            <div class="pltz-stats-unavailable">
                Statistics API not available
            </div>`;
  }

  /**
   * Render statistics in container
   */
  private renderStatistics(container: HTMLElement, stats: any): void {
    const formatNum = (n: number | undefined) =>
      n !== undefined ? n.toFixed(3) : "-";

    container.innerHTML = `
            <div class="pltz-stats-grid pltz-stats-grid-6">
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">N points</div>
                    <div class="pltz-stat-value">${stats.n || "-"}</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Mean</div>
                    <div class="pltz-stat-value">${formatNum(stats.mean)}</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Std</div>
                    <div class="pltz-stat-value">${formatNum(stats.std)}</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Min</div>
                    <div class="pltz-stat-value">${formatNum(stats.min)}</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Max</div>
                    <div class="pltz-stat-value">${formatNum(stats.max)}</div>
                </div>
                <div class="pltz-stat-item">
                    <div class="pltz-stat-label">Range</div>
                    <div class="pltz-stat-value">${formatNum(stats.range)}</div>
                </div>
            </div>`;
  }

  /**
   * Setup refresh stats button handler
   */
  public setupRefreshButton(pltzPath: string): void {
    const refreshBtn = document.getElementById("pltz-refresh-stats-btn");
    if (refreshBtn) {
      refreshBtn.addEventListener("click", () => {
        this.loadStatistics(pltzPath);
      });
    }
  }
}
