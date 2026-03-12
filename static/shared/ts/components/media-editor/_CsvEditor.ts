/**
 * CsvEditor - Handles CSV/TSV file editing with full table functionality
 *
 * Features:
 * - Full CSV/TSV editing with DataTableManager
 * - Plot integration via figrecipe_app API (delegated to CsvPlotPanel)
 * - Basic statistics panel (delegated to CsvStatsPanel)
 * - LaTeX table export (delegated to CsvLatexPanel)
 *
 * Refactored: Extracted panel logic to separate modules for maintainability.
 */

import type { MediaEditorConfig } from './types';
import { DataTableManager } from '../data-table/index';
import type { Dataset, DataRow } from '../data-table/types';
import { CsvPlotPanel, CsvStatsPanel, CsvLatexPanel } from './_panels/index';

export class CsvEditor {
  private config: MediaEditorConfig;
  private dataTableManager: DataTableManager | null = null;
  private currentFilePath: string | null = null;
  private currentCsvContent: string | null = null;
  private wrapper: HTMLElement | null = null;
  private activePanel: 'table' | 'plot' | 'stats' | 'latex' = 'table';

  // Extracted panel managers
  private plotPanel: CsvPlotPanel;
  private statsPanel: CsvStatsPanel;
  private latexPanel: CsvLatexPanel;

  constructor(config: MediaEditorConfig) {
    this.config = config;
    this.plotPanel = new CsvPlotPanel(() => this.getCsrfToken());
    this.statsPanel = new CsvStatsPanel();
    this.latexPanel = new CsvLatexPanel();
  }

  /**
   * Render a CSV/TSV file with editing capabilities
   */
  async render(container: HTMLElement, filePath: string): Promise<void> {
    this.currentFilePath = filePath;
    this.latexPanel.setFilePath(filePath);

    const wrapper = document.createElement("div");
    wrapper.className = "media-viewer-csv-wrapper";
    this.wrapper = wrapper;

    // Toolbar
    const toolbar = this.createToolbar(filePath);
    wrapper.appendChild(toolbar);

    // Content area for panels
    const contentArea = document.createElement("div");
    contentArea.className = "csv-content-area";

    // Table panel (default, visible)
    const tablePanel = document.createElement("div");
    tablePanel.className = "csv-panel csv-panel-table";

    // Table container for DataTableManager
    const tableContainer = document.createElement("div");
    tableContainer.id = `csv-table-container-${Date.now()}`;
    tableContainer.className = "media-viewer-csv-container data-table-container";
    tableContainer.innerHTML = `
      <div class="csv-loading">
        <i class="fas fa-spinner fa-spin"></i> Loading...
      </div>
    `;
    tablePanel.appendChild(tableContainer);
    contentArea.appendChild(tablePanel);

    wrapper.appendChild(contentArea);
    container.appendChild(wrapper);

    // Load and initialize DataTableManager
    await this.loadCsv(filePath, tableContainer, wrapper);
  }

  /**
   * Create toolbar for CSV editor
   */
  private createToolbar(filePath: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.className = "media-viewer-toolbar csv-editor-toolbar";

    const fileName = filePath.split("/").pop() || filePath;

    toolbar.innerHTML = `
      <div class="media-viewer-toolbar-left">
        <i class="fas fa-table media-viewer-icon"></i>
        <span class="media-viewer-filename" title="${filePath}">${fileName}</span>
      </div>
      <div class="media-viewer-toolbar-center">
        <span class="csv-info">Loading...</span>
        <div class="csv-panel-tabs">
          <button class="csv-panel-tab active" data-panel="table" title="Table View">
            <i class="fas fa-table"></i> Table
          </button>
          <button class="csv-panel-tab" data-panel="plot" title="Plot Data">
            <i class="fas fa-chart-line"></i> Plot
          </button>
          <button class="csv-panel-tab" data-panel="stats" title="Statistics">
            <i class="fas fa-calculator"></i> Stats
          </button>
          <button class="csv-panel-tab" data-panel="latex" title="LaTeX Export">
            <i class="fas fa-file-code"></i> LaTeX
          </button>
        </div>
      </div>
      <div class="media-viewer-toolbar-right">
        <button class="csv-control-btn csv-toggle-raw" title="Toggle raw view">
          <i class="fas fa-code"></i>
        </button>
        <button class="csv-control-btn csv-save-btn" title="Save changes">
          <i class="fas fa-save"></i>
        </button>
        <button class="media-viewer-btn media-download-btn" title="Download">
          <i class="fas fa-download"></i>
        </button>
        <button class="media-viewer-btn media-open-new-tab" title="Open in new tab">
          <i class="fas fa-external-link-alt"></i>
        </button>
      </div>
    `;

    this.setupToolbarHandlers(toolbar, filePath);
    return toolbar;
  }

  /**
   * Setup toolbar button handlers
   */
  private setupToolbarHandlers(toolbar: HTMLElement, filePath: string): void {
    const downloadBtn = toolbar.querySelector(".media-download-btn");
    downloadBtn?.addEventListener("click", () => this.downloadFile(filePath));

    const openNewTabBtn = toolbar.querySelector(".media-open-new-tab");
    openNewTabBtn?.addEventListener("click", () => this.openInNewTab(filePath));

    const panelTabs = toolbar.querySelectorAll(".csv-panel-tab");
    panelTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        const panel = (tab as HTMLElement).dataset.panel as 'table' | 'plot' | 'stats' | 'latex';
        this.switchPanel(panel);
        panelTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
      });
    });
  }

  /**
   * Switch between panels
   */
  private switchPanel(panel: 'table' | 'plot' | 'stats' | 'latex'): void {
    if (!this.wrapper) return;

    this.activePanel = panel;
    const contentArea = this.wrapper.querySelector(".csv-content-area") as HTMLElement;
    if (!contentArea) return;

    // Hide all panels
    const panels = contentArea.querySelectorAll(".csv-panel");
    panels.forEach(p => (p as HTMLElement).style.display = "none");

    // Show the selected panel
    const selectedPanel = contentArea.querySelector(`.csv-panel-${panel}`) as HTMLElement;
    if (selectedPanel) {
      selectedPanel.style.display = "block";
    } else {
      this.createPanel(panel, contentArea);
    }
  }

  /**
   * Create a panel on first access
   */
  private createPanel(panel: 'table' | 'plot' | 'stats' | 'latex', contentArea: HTMLElement): void {
    const panelEl = document.createElement("div");
    panelEl.className = `csv-panel csv-panel-${panel}`;

    const data = this.dataTableManager?.getCurrentData() || null;

    switch (panel) {
      case 'plot':
        (panelEl as any).__currentData = data;
        this.plotPanel.render(panelEl, data?.columns || []);
        break;
      case 'stats':
        this.statsPanel.render(panelEl, data);
        break;
      case 'latex':
        this.latexPanel.render(panelEl, data);
        break;
      default:
        return;
    }

    contentArea.appendChild(panelEl);
  }

  /**
   * Load and initialize DataTableManager with CSV content
   */
  private async loadCsv(filePath: string, tableContainer: HTMLElement, wrapper: HTMLElement): Promise<void> {
    try {
      const url = this.config.getFileUrl(filePath, false, false);
      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch CSV");

      const data = await response.json();
      const content = data.content || "";

      this.currentCsvContent = content;
      (tableContainer as any).__rawContent = content;

      const statusCallback = (msg: string) => {
        const infoEl = wrapper.querySelector(".csv-info");
        if (infoEl) infoEl.textContent = msg;
      };

      this.dataTableManager = new DataTableManager(statusCallback);
      this.dataTableManager.loadFromCSVContent(content, filePath);
      this.dataTableManager.renderEditableDataTable();
      this.dataTableManager.setupColumnResizing();
      this.dataTableManager.setupVirtualScrolling();

      const currentData = this.dataTableManager.getCurrentData();
      const infoEl = wrapper.querySelector(".csv-info");
      if (infoEl && currentData) {
        infoEl.textContent = `${currentData.rows.length} rows × ${currentData.columns.length} columns`;
      }

      this.setupContextMenu(tableContainer);
      this.setupToggleRawView(wrapper, tableContainer, content);
      this.setupSaveButton(wrapper);

    } catch (error) {
      console.error("[CsvEditor] Error loading CSV:", error);
      tableContainer.innerHTML = `
        <div class="media-viewer-error">
          <i class="fas fa-exclamation-triangle"></i>
          <p>Failed to load CSV</p>
          <small>${filePath}</small>
        </div>
      `;
    }
  }

  /**
   * Setup toggle raw view button
   */
  private setupToggleRawView(wrapper: HTMLElement, tableContainer: HTMLElement, content: string): void {
    const toggleRawBtn = wrapper.querySelector(".csv-toggle-raw");
    let showingRaw = false;

    toggleRawBtn?.addEventListener("click", () => {
      showingRaw = !showingRaw;
      if (showingRaw) {
        tableContainer.innerHTML = `<pre class="csv-raw-content">${this.escapeHtml(content)}</pre>`;
        toggleRawBtn.innerHTML = '<i class="fas fa-table"></i>';
      } else {
        if (this.dataTableManager) {
          this.dataTableManager.renderEditableDataTable();
          this.dataTableManager.setupColumnResizing();
        }
        toggleRawBtn.innerHTML = '<i class="fas fa-code"></i>';
      }
    });
  }

  /**
   * Setup save button
   */
  private setupSaveButton(wrapper: HTMLElement): void {
    const saveBtn = wrapper.querySelector(".csv-save-btn");
    saveBtn?.addEventListener("click", async () => {
      await this.saveFile();
    });
  }

  /**
   * Setup right-click context menu
   */
  private setupContextMenu(tableContainer: HTMLElement): void {
    const contextMenu = document.createElement('div');
    contextMenu.className = 'csv-context-menu';
    contextMenu.style.display = 'none';
    contextMenu.innerHTML = `
      <div class="csv-context-menu-item" data-action="use-header">
        <i class="fas fa-heading"></i> Use first row as header
      </div>
      <div class="csv-context-menu-item" data-action="insert-header">
        <i class="fas fa-arrow-down"></i> Insert header as first row
      </div>
      <div class="csv-context-menu-divider"></div>
      <div class="csv-context-menu-item" data-action="use-index">
        <i class="fas fa-hashtag"></i> Use first column as index
      </div>
      <div class="csv-context-menu-item" data-action="insert-index">
        <i class="fas fa-arrow-right"></i> Insert index column
      </div>
    `;
    document.body.appendChild(contextMenu);

    tableContainer.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      let x = e.clientX;
      let y = e.clientY;

      contextMenu.style.display = 'block';
      const menuRect = contextMenu.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      if (x + menuRect.width > viewportWidth) {
        x = viewportWidth - menuRect.width - 10;
      }
      if (y + menuRect.height > viewportHeight) {
        y = viewportHeight - menuRect.height - 10;
      }

      contextMenu.style.left = `${x}px`;
      contextMenu.style.top = `${y}px`;
    });

    document.addEventListener('click', () => {
      contextMenu.style.display = 'none';
    });

    contextMenu.addEventListener('click', (e) => {
      const item = (e.target as HTMLElement).closest('.csv-context-menu-item');
      if (!item || !this.dataTableManager) return;

      const action = item.getAttribute('data-action');
      switch (action) {
        case 'use-header':
          this.dataTableManager.useFirstRowAsHeader();
          this.dataTableManager.setupVirtualScrolling();
          break;
        case 'insert-header':
          this.dataTableManager.insertHeaderAsFirstRow();
          this.dataTableManager.setupVirtualScrolling();
          break;
        case 'use-index':
          this.dataTableManager.useFirstColumnAsIndex();
          this.dataTableManager.setupVirtualScrolling();
          break;
        case 'insert-index':
          this.dataTableManager.insertIndexColumn();
          this.dataTableManager.setupVirtualScrolling();
          break;
      }
      contextMenu.style.display = 'none';
    });
  }

  /**
   * Save the current CSV content
   */
  async saveFile(): Promise<boolean> {
    if (!this.dataTableManager || !this.currentFilePath) return false;

    try {
      const csvContent = this.dataTableManager.exportToCSV();
      const url = this.config.getFileUrl(this.currentFilePath, false, false);

      const response = await fetch(url, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": this.getCsrfToken(),
        },
        body: JSON.stringify({ content: csvContent }),
      });

      if (!response.ok) throw new Error("Failed to save CSV");

      console.log("[CsvEditor] CSV saved successfully");
      return true;
    } catch (error) {
      console.error("[CsvEditor] Error saving CSV:", error);
      alert("Failed to save CSV file");
      return false;
    }
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
   * Download the file
   */
  private downloadFile(filePath: string): void {
    const url = this.config.getFileUrl(filePath, true, true);
    const a = document.createElement("a");
    a.href = url;
    a.download = filePath.split("/").pop() || "download";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    this.config.onDownload?.(filePath);
  }

  /**
   * Open file in new tab
   */
  private openInNewTab(filePath: string): void {
    const url = this.config.getFileUrl(filePath, false, false);
    window.open(url, "_blank");
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
    this.currentFilePath = null;
    this.wrapper = null;
  }
}
