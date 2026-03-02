/**
 * CsvStatsPanel - Descriptive statistics panel for CSV data
 *
 * Calculates and displays statistics (mean, std, min, max, median) for numeric columns.
 * Extracted from CsvEditor.ts for single responsibility.
 */

import type { Dataset, DataRow } from '../../data-table/types';

/** Statistics result for a column */
export interface ColumnStats {
  column: string;
  count: number;
  mean: number | null;
  std: number | null;
  min: number | null;
  max: number | null;
  median: number | null;
  sum: number | null;
}

export class CsvStatsPanel {
  /**
   * Render the statistics panel
   */
  public render(panel: HTMLElement, data: Dataset | null): void {
    if (!data || data.rows.length === 0) {
      panel.innerHTML = `
        <div class="csv-stats-empty">
          <i class="fas fa-chart-bar"></i>
          <p>No data available for statistics</p>
        </div>
      `;
      return;
    }

    // Calculate statistics for each numeric column
    const stats = this.calculateAllStats(data);

    panel.innerHTML = `
      <div class="csv-stats-panel">
        <h4><i class="fas fa-calculator"></i> Descriptive Statistics</h4>
        <div class="stats-summary">
          <span class="stats-badge">${data.rows.length} rows</span>
          <span class="stats-badge">${data.columns.length} columns</span>
          <span class="stats-badge">${stats.length} numeric columns</span>
        </div>
        <div class="stats-table-wrapper">
          <table class="stats-table">
            <thead>
              <tr>
                <th>Column</th>
                <th>Count</th>
                <th>Mean</th>
                <th>Std</th>
                <th>Min</th>
                <th>Median</th>
                <th>Max</th>
                <th>Sum</th>
              </tr>
            </thead>
            <tbody>
              ${stats.map(s => `
                <tr>
                  <td class="stats-col-name">${this.escapeHtml(s.column)}</td>
                  <td>${s.count}</td>
                  <td>${s.mean !== null ? s.mean.toFixed(4) : '-'}</td>
                  <td>${s.std !== null ? s.std.toFixed(4) : '-'}</td>
                  <td>${s.min !== null ? s.min.toFixed(4) : '-'}</td>
                  <td>${s.median !== null ? s.median.toFixed(4) : '-'}</td>
                  <td>${s.max !== null ? s.max.toFixed(4) : '-'}</td>
                  <td>${s.sum !== null ? s.sum.toFixed(4) : '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        <div class="stats-actions">
          <button class="csv-control-btn stats-copy-btn" title="Copy to clipboard">
            <i class="fas fa-copy"></i> Copy Stats
          </button>
        </div>
      </div>
    `;

    // Setup copy button
    const copyBtn = panel.querySelector(".stats-copy-btn");
    copyBtn?.addEventListener("click", () => {
      this.copyToClipboard(stats);
    });
  }

  /**
   * Calculate statistics for all numeric columns
   */
  public calculateAllStats(data: Dataset): ColumnStats[] {
    const stats: ColumnStats[] = [];

    for (const colName of data.columns) {
      const values: number[] = [];

      for (const row of data.rows) {
        const val = parseFloat(String(row[colName]));
        if (!isNaN(val)) {
          values.push(val);
        }
      }

      if (values.length > 0) {
        stats.push(this.calculateColumnStats(colName, values));
      }
    }

    return stats;
  }

  /**
   * Calculate statistics for a single column
   */
  public calculateColumnStats(column: string, values: number[]): ColumnStats {
    const count = values.length;
    const sum = values.reduce((a, b) => a + b, 0);
    const mean = sum / count;
    const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / count;
    const std = Math.sqrt(variance);
    const sorted = [...values].sort((a, b) => a - b);
    const min = sorted[0];
    const max = sorted[sorted.length - 1];
    const median = count % 2 === 0
      ? (sorted[count / 2 - 1] + sorted[count / 2]) / 2
      : sorted[Math.floor(count / 2)];

    return { column, count, mean, std, min, max, median, sum };
  }

  /**
   * Copy statistics to clipboard
   */
  private copyToClipboard(stats: ColumnStats[]): void {
    const header = 'Column\tCount\tMean\tStd\tMin\tMedian\tMax\tSum';
    const rows = stats.map(s =>
      `${s.column}\t${s.count}\t${s.mean?.toFixed(4) || '-'}\t${s.std?.toFixed(4) || '-'}\t${s.min?.toFixed(4) || '-'}\t${s.median?.toFixed(4) || '-'}\t${s.max?.toFixed(4) || '-'}\t${s.sum?.toFixed(4) || '-'}`
    ).join('\n');
    navigator.clipboard.writeText(`${header}\n${rows}`);
    alert('Statistics copied to clipboard');
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
