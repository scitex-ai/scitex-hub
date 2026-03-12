/**
 * CsvPlotPanel - Plot configuration and generation panel for CSV data
 *
 * Handles plot type selection, column mapping, and plot generation via figrecipe_app API.
 * Extracted from CsvEditor.ts for single responsibility.
 */

import type { Dataset, DataRow } from '../../data-table/types';

/** Plot configuration for figrecipe_app integration */
export interface PlotSpec {
  figure: {
    width_mm: number;
    height_mm: number;
    dpi: number;
  };
  plot: {
    kind: string;
    x_col?: string;
    y_col?: string;
    hue_col?: string;
    data?: number[][];
    columns?: string[];
  };
}

export class CsvPlotPanel {
  private getCsrfToken: () => string;

  constructor(getCsrfToken: () => string) {
    this.getCsrfToken = getCsrfToken;
  }

  /**
   * Render the plot configuration panel
   */
  public render(panel: HTMLElement, columns: string[]): void {
    panel.innerHTML = `
      <div class="csv-plot-panel">
        <div class="csv-plot-config">
          <h4><i class="fas fa-chart-line"></i> Quick Plot</h4>
          <div class="plot-config-row">
            <label>Plot Type:</label>
            <select class="plot-type-select">
              <option value="line">Line Chart</option>
              <option value="scatter">Scatter Plot</option>
              <option value="bar">Bar Chart</option>
              <option value="hist">Histogram</option>
              <option value="box">Box Plot</option>
            </select>
          </div>
          <div class="plot-config-row">
            <label>X Column:</label>
            <select class="plot-x-select">
              <option value="">-- Auto (row index) --</option>
              ${columns.map(c => `<option value="${c}">${c}</option>`).join('')}
            </select>
          </div>
          <div class="plot-config-row">
            <label>Y Column:</label>
            <select class="plot-y-select">
              ${columns.map((c, i) => `<option value="${c}" ${i === 1 ? 'selected' : ''}>${c}</option>`).join('')}
            </select>
          </div>
          <div class="plot-config-row">
            <label>Color By:</label>
            <select class="plot-hue-select">
              <option value="">-- None --</option>
              ${columns.map(c => `<option value="${c}">${c}</option>`).join('')}
            </select>
          </div>
          <button class="csv-control-btn plot-generate-btn">
            <i class="fas fa-play"></i> Generate Plot
          </button>
        </div>
        <div class="csv-plot-preview">
          <div class="plot-placeholder">
            <i class="fas fa-chart-area"></i>
            <p>Configure and generate a plot</p>
          </div>
        </div>
      </div>
    `;

    // Setup generate button
    const generateBtn = panel.querySelector(".plot-generate-btn");
    generateBtn?.addEventListener("click", () => {
      const data = (panel as any).__currentData as Dataset | undefined;
      if (data) {
        this.generatePlot(panel, data);
      }
    });
  }

  /**
   * Generate plot using figrecipe_app API
   */
  public async generatePlot(panel: HTMLElement, data: Dataset): Promise<void> {
    const plotType = (panel.querySelector(".plot-type-select") as HTMLSelectElement)?.value || 'line';
    const xCol = (panel.querySelector(".plot-x-select") as HTMLSelectElement)?.value;
    const yCol = (panel.querySelector(".plot-y-select") as HTMLSelectElement)?.value;
    const hueCol = (panel.querySelector(".plot-hue-select") as HTMLSelectElement)?.value;

    const previewArea = panel.querySelector(".csv-plot-preview");
    if (!previewArea) return;

    previewArea.innerHTML = `
      <div class="plot-loading">
        <i class="fas fa-spinner fa-spin"></i> Generating plot...
      </div>
    `;

    try {
      // Prepare plot specification
      const numericData = data.rows.map(row =>
        data.columns.map(col => parseFloat(String(row[col])) || 0)
      );

      const plotSpec: PlotSpec = {
        figure: {
          width_mm: 120,
          height_mm: 80,
          dpi: 150
        },
        plot: {
          kind: plotType,
          x_col: xCol || undefined,
          y_col: yCol || undefined,
          hue_col: hueCol || undefined,
          data: numericData,
          columns: data.columns
        }
      };

      // Call figrecipe_app API
      const response = await fetch('/api/vis/plot/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': this.getCsrfToken()
        },
        body: JSON.stringify(plotSpec)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error || 'Plot generation failed');
      }

      // Display SVG
      const svgContent = await response.text();
      previewArea.innerHTML = `
        <div class="plot-result">
          ${svgContent}
          <div class="plot-actions">
            <button class="csv-control-btn plot-download-svg" title="Download SVG">
              <i class="fas fa-download"></i> SVG
            </button>
            <button class="csv-control-btn plot-open-vis" title="Open in Vis Editor">
              <i class="fas fa-external-link-alt"></i> Edit in Vis
            </button>
          </div>
        </div>
      `;

      // Setup download button
      const downloadBtn = previewArea.querySelector(".plot-download-svg");
      downloadBtn?.addEventListener("click", () => {
        this.downloadSvg(svgContent);
      });

    } catch (error) {
      console.error("[CsvPlotPanel] Plot generation error:", error);
      previewArea.innerHTML = `
        <div class="plot-error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to generate plot</p>
          <small>${error instanceof Error ? error.message : 'Unknown error'}</small>
        </div>
      `;
    }
  }

  /**
   * Download SVG content as file
   */
  private downloadSvg(svgContent: string): void {
    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'plot.svg';
    a.click();
    URL.revokeObjectURL(url);
  }
}
