/**
 * CSV Viewer
 * Handles CSV/TSV file display and editing using DataTableManager
 */

import { DataTableManager, Dataset } from "@/components/data-table/index.js";
import { LatexExporter } from "./LatexExporter.js";

export class CsvViewer {
  private dataTableManager: DataTableManager | null = null;
  private latexExporter: LatexExporter;
  private rawContent: string = "";
  private currentFilePath: string = "";

  constructor() {
    this.latexExporter = new LatexExporter();
  }

  /**
   * Display a CSV/TSV file
   */
  async display(
    wrapper: HTMLElement,
    filePath: string,
    createToolbar?: (filePath: string, fileType: string) => HTMLElement,
  ): Promise<void> {
    this.currentFilePath = filePath;
    wrapper.className = "media-viewer-csv-wrapper";

    // Toolbar
    if (createToolbar) {
      const toolbar = createToolbar(filePath, "csv");
      this.addCsvControls(toolbar);
      wrapper.appendChild(toolbar);
    }

    // Table container for DataTableManager
    const tableContainer = document.createElement("div");
    tableContainer.className =
      "media-viewer-csv-container data-table-container";
    tableContainer.id = "csv-table-container";
    tableContainer.innerHTML = `
      <div class="csv-loading">
        <i class="fas fa-spinner fa-spin"></i> Loading...
      </div>
    `;
    wrapper.appendChild(tableContainer);

    // Load and parse CSV using DataTableManager
    await this.loadCsvWithDataTable(filePath, tableContainer);
  }

  /**
   * Add CSV-specific controls to toolbar
   */
  private addCsvControls(toolbar: HTMLElement): void {
    const csvControls = document.createElement("div");
    csvControls.className = "media-viewer-csv-controls";
    csvControls.innerHTML = `
      <button class="csv-control-btn" id="csv-toggle-raw" title="Toggle raw view">
        <i class="fas fa-code"></i> Raw
      </button>
      <button class="csv-control-btn" id="csv-save-btn" title="Save changes">
        <i class="fas fa-save"></i> Save
      </button>
      <span class="toolbar-separator"></span>
      <button class="csv-control-btn" id="csv-plot-btn" title="Generate plot from data">
        <i class="fas fa-chart-line"></i> Plot
      </button>
      <button class="csv-control-btn" id="csv-stats-btn" title="Calculate statistics">
        <i class="fas fa-calculator"></i> Stats
      </button>
      <button class="csv-control-btn" id="csv-latex-btn" title="Export as LaTeX table">
        <i class="fas fa-file-code"></i> LaTeX
      </button>
    `;
    toolbar.appendChild(csvControls);
  }

  /**
   * Load and render CSV file using the shared DataTableManager
   */
  private async loadCsvWithDataTable(
    filePath: string,
    container: HTMLElement,
  ): Promise<void> {
    try {
      const projectData = document.getElementById("project-data");
      const projectId = projectData?.dataset.projectId || "";
      const url = `/code/api/file-content/${filePath}?project_id=${projectId}`;

      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch CSV");

      const data = await response.json();
      const content = data.content || "";
      this.rawContent = content;

      // Initialize DataTableManager with the container
      this.dataTableManager = new DataTableManager({
        container: container,
        readOnly: false,
        onDataChange: (data) => {
          console.log("[CsvViewer] CSV data changed");
        },
      });

      // First initialize a large blank table
      this.dataTableManager.initializeBlankTable();

      // Then load the CSV data
      this.loadCsvIntoBlankTable(content, filePath);

      this.dataTableManager.renderEditableDataTable();
      this.dataTableManager.setupColumnResizing();
      this.dataTableManager.setupVirtualScrolling();

      // Setup feature buttons
      this.setupFeatureButtons(content, filePath, container);
    } catch (error) {
      console.error("[CsvViewer] Error loading CSV:", error);
      container.innerHTML = `
        <div class="media-viewer-error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to load CSV</p>
          <small>${filePath}</small>
        </div>
      `;
    }
  }

  /**
   * Load CSV content into an already-initialized blank table
   */
  private loadCsvIntoBlankTable(content: string, filename: string): void {
    if (!this.dataTableManager) return;

    const currentData = this.dataTableManager.getCurrentData();
    if (!currentData) return;

    const delimiter = filename.toLowerCase().endsWith(".tsv") ? "\t" : ",";
    const lines = content.trim().split("\n");
    if (lines.length === 0) return;

    const firstRow = this.parseCSVLine(lines[0], delimiter);
    const colCount = firstRow.length;

    // Parse and place ALL rows as data (no header row detection)
    for (
      let rowIndex = 0;
      rowIndex < lines.length && rowIndex < currentData.rows.length;
      rowIndex++
    ) {
      const csvRow = this.parseCSVLine(lines[rowIndex], delimiter);
      const dataRow = currentData.rows[rowIndex];

      csvRow.forEach((value, colIndex) => {
        const colName = currentData.columns[colIndex];
        if (colName) {
          const trimmedValue = value.trim();
          const numValue = parseFloat(trimmedValue);
          dataRow[colName] =
            isNaN(numValue) || trimmedValue === "" ? trimmedValue : numValue;
        }
      });
    }

    this.dataTableManager.setCurrentData(currentData);
    console.log(
      `[CsvViewer] CSV loaded: ${lines.length} rows × ${colCount} columns`,
    );
  }

  /**
   * Setup Plot, Stats, LaTeX, Raw toggle, and Save buttons
   */
  private setupFeatureButtons(
    content: string,
    filePath: string,
    container: HTMLElement,
  ): void {
    // Plot button
    const plotBtn = document.getElementById("csv-plot-btn");
    plotBtn?.addEventListener("click", () => {
      console.log("[CsvViewer] Plot panel - coming soon");
      alert("Plot feature coming soon! Will integrate with /apps/vis/ app.");
    });

    // Stats button
    const statsBtn = document.getElementById("csv-stats-btn");
    statsBtn?.addEventListener("click", () => {
      console.log("[CsvViewer] Stats panel - coming soon");
      alert("Stats feature coming soon! Will integrate with scitex.stats.");
    });

    // LaTeX button
    const latexBtn = document.getElementById("csv-latex-btn");
    latexBtn?.addEventListener("click", () => {
      this.latexExporter.show(this.rawContent, filePath);
    });

    // Toggle raw view button
    const toggleRawBtn = document.getElementById("csv-toggle-raw");
    let showingRaw = false;
    toggleRawBtn?.addEventListener("click", () => {
      showingRaw = !showingRaw;
      if (showingRaw) {
        container.innerHTML = `<pre class="csv-raw-content">${this.escapeHtml(content)}</pre>`;
        toggleRawBtn.innerHTML = '<i class="fas fa-table"></i> Table';
      } else {
        if (this.dataTableManager) {
          this.dataTableManager.renderEditableDataTable();
          this.dataTableManager.setupColumnResizing();
        }
        toggleRawBtn.innerHTML = '<i class="fas fa-code"></i> Raw';
      }
    });

    // Save button
    const saveBtn = document.getElementById("csv-save-btn");
    saveBtn?.addEventListener("click", async () => {
      if (!this.dataTableManager) return;
      const csvContent = this.dataTableManager.exportToCSV();
      await this.saveCsvFile(filePath, csvContent);
    });
  }

  /**
   * Save CSV file to server
   */
  private async saveCsvFile(filePath: string, content: string): Promise<void> {
    try {
      const projectData = document.getElementById("project-data");
      const projectId = projectData?.dataset.projectId || "";

      const response = await fetch(
        `/code/api/file-content/${filePath}?project_id=${projectId}`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": this.getCsrfToken(),
          },
          body: JSON.stringify({ content }),
        },
      );

      if (!response.ok) throw new Error("Failed to save CSV");

      const infoEl = document.getElementById("csv-info");
      if (infoEl) {
        const originalText = infoEl.textContent;
        infoEl.textContent = "Saved!";
        setTimeout(() => {
          if (infoEl) infoEl.textContent = originalText || "";
        }, 2000);
      }

      console.log("[CsvViewer] CSV saved successfully");
    } catch (error) {
      console.error("[CsvViewer] Error saving CSV:", error);
      alert("Failed to save CSV file");
    }
  }

  /**
   * Parse a single CSV line handling quoted fields
   */
  private parseCSVLine(line: string, delimiter: string): string[] {
    const result: string[] = [];
    let currentValue = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const nextChar = line[i + 1];

      if (inQuotes) {
        if (char === '"' && nextChar === '"') {
          currentValue += '"';
          i++;
        } else if (char === '"') {
          inQuotes = false;
        } else {
          currentValue += char;
        }
      } else {
        if (char === '"') {
          inQuotes = true;
        } else if (char === delimiter) {
          result.push(currentValue);
          currentValue = "";
        } else {
          currentValue += char;
        }
      }
    }
    result.push(currentValue);

    return result;
  }

  /**
   * Get CSRF token from cookies
   */
  private getCsrfToken(): string {
    const name = "csrftoken";
    const cookies = document.cookie.split(";");
    for (const cookie of cookies) {
      const [key, value] = cookie.trim().split("=");
      if (key === name) return value;
    }
    return "";
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Get the DataTableManager instance
   */
  getDataTableManager(): DataTableManager | null {
    return this.dataTableManager;
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    this.dataTableManager = null;
    this.rawContent = "";
    this.currentFilePath = "";
  }
}
