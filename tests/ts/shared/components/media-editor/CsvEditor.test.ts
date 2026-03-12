/**
 * Tests for static/shared/ts/components/media-editor/CsvEditor.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/static/shared/ts/components/media-editor/CsvEditor';

describe('CsvEditor', () => {
    beforeEach(() => {
        // Setup before each test
    });

    afterEach(() => {
        // Cleanup after each test
    });

    it.todo('should be implemented');
});

// =============================================================================
// Source Code Reference (auto-generated, do not edit below this line)
// =============================================================================
// Source: static/shared/ts/components/media-editor/CsvEditor.ts
// =============================================================================

// /**
//  * CsvEditor - Handles CSV/TSV file editing with full table functionality
//  * Uses the shared DataTableManager for editing capabilities
//  *
//  * Features:
//  * - Full CSV/TSV editing with DataTableManager
//  * - Plot integration via figrecipe_app API
//  * - Basic statistics panel
//  * - LaTeX table export
//  */
//
// import type { MediaEditorConfig } from './types';
// import { DataTableManager } from '../data-table/index';
// import type { Dataset, DataRow } from '../data-table/types';
//
// /** Plot configuration for figrecipe_app integration */
// interface PlotSpec {
//   figure: {
//     width_mm: number;
//     height_mm: number;
//     dpi: number;
//   };
//   plot: {
//     kind: string;
//     x_col?: string;
//     y_col?: string;
//     hue_col?: string;
//     data?: number[][];
//     columns?: string[];
//   };
// }
//
// /** Statistics result for a column */
// interface ColumnStats {
//   column: string;
//   count: number;
//   mean: number | null;
//   std: number | null;
//   min: number | null;
//   max: number | null;
//   median: number | null;
//   sum: number | null;
// }
//
// export class CsvEditor {
//   private config: MediaEditorConfig;
//   private dataTableManager: DataTableManager | null = null;
//   private currentFilePath: string | null = null;
//   private currentCsvContent: string | null = null;
//   private wrapper: HTMLElement | null = null;
//   private activePanel: 'table' | 'plot' | 'stats' | 'latex' = 'table';
//
//   constructor(config: MediaEditorConfig) {
//     this.config = config;
//   }
//
//   /**
//    * Convert DataRow to an array of values in column order
//    */
//   private rowToArray(row: DataRow, columns: string[]): string[] {
//     return columns.map(col => String(row[col] ?? ''));
//   }
//
//   /**
//    * Get cell value from DataRow as string
//    */
//   private getCellValue(row: DataRow, colIdx: number, columns: string[]): string {
//     const colName = columns[colIdx];
//     return colName ? String(row[colName] ?? '') : '';
//   }
//
//   /**
//    * Render a CSV/TSV file with editing capabilities
//    */
//   async render(container: HTMLElement, filePath: string): Promise<void> {
//     this.currentFilePath = filePath;
//
//     const wrapper = document.createElement("div");
//     wrapper.className = "media-viewer-csv-wrapper";
//     this.wrapper = wrapper;
//
//     // Toolbar
//     const toolbar = this.createToolbar(filePath);
//     wrapper.appendChild(toolbar);
//
//     // Content area for panels
//     const contentArea = document.createElement("div");
//     contentArea.className = "csv-content-area";
//
//     // Table panel (default, visible)
//     const tablePanel = document.createElement("div");
//     tablePanel.className = "csv-panel csv-panel-table";
//
//     // Table container for DataTableManager
//     const tableContainer = document.createElement("div");
//     tableContainer.id = `csv-table-container-${Date.now()}`;
//     tableContainer.className = "media-viewer-csv-container data-table-container";
//     tableContainer.innerHTML = `
//       <div class="csv-loading">
//         <i class="fas fa-spinner fa-spin"></i> Loading...
//       </div>
//     `;
//     tablePanel.appendChild(tableContainer);
//     contentArea.appendChild(tablePanel);
//
//     wrapper.appendChild(contentArea);
//     container.appendChild(wrapper);
//
//     // Load and initialize DataTableManager
//     await this.loadCsv(filePath, tableContainer, wrapper);
//   }
//
//   /**
//    * Create toolbar for CSV editor with Plot, Stats, and LaTeX export
//    */
//   private createToolbar(filePath: string): HTMLElement {
//     const toolbar = document.createElement("div");
//     toolbar.className = "media-viewer-toolbar csv-editor-toolbar";
//
//     const fileName = filePath.split("/").pop() || filePath;
//
//     toolbar.innerHTML = `
//       <div class="media-viewer-toolbar-left">
//         <i class="fas fa-table media-viewer-icon"></i>
//         <span class="media-viewer-filename" title="${filePath}">${fileName}</span>
//       </div>
//       <div class="media-viewer-toolbar-center">
//         <span class="csv-info">Loading...</span>
//         <div class="csv-panel-tabs">
//           <button class="csv-panel-tab active" data-panel="table" title="Table View">
//             <i class="fas fa-table"></i> Table
//           </button>
//           <button class="csv-panel-tab" data-panel="plot" title="Plot Data">
//             <i class="fas fa-chart-line"></i> Plot
//           </button>
//           <button class="csv-panel-tab" data-panel="stats" title="Statistics">
//             <i class="fas fa-calculator"></i> Stats
//           </button>
//           <button class="csv-panel-tab" data-panel="latex" title="LaTeX Export">
//             <i class="fas fa-file-code"></i> LaTeX
//           </button>
//         </div>
//       </div>
//       <div class="media-viewer-toolbar-right">
//         <button class="csv-control-btn csv-toggle-raw" title="Toggle raw view">
//           <i class="fas fa-code"></i>
//         </button>
//         <button class="csv-control-btn csv-save-btn" title="Save changes">
//           <i class="fas fa-save"></i>
//         </button>
//         <button class="media-viewer-btn media-download-btn" title="Download">
//           <i class="fas fa-download"></i>
//         </button>
//         <button class="media-viewer-btn media-open-new-tab" title="Open in new tab">
//           <i class="fas fa-external-link-alt"></i>
//         </button>
//       </div>
//     `;
//
//     // Setup button handlers
//     const downloadBtn = toolbar.querySelector(".media-download-btn");
//     downloadBtn?.addEventListener("click", () => this.downloadFile(filePath));
//
//     const openNewTabBtn = toolbar.querySelector(".media-open-new-tab");
//     openNewTabBtn?.addEventListener("click", () => this.openInNewTab(filePath));
//
//     // Setup panel tab handlers
//     const panelTabs = toolbar.querySelectorAll(".csv-panel-tab");
//     panelTabs.forEach(tab => {
//       tab.addEventListener("click", () => {
//         const panel = (tab as HTMLElement).dataset.panel as 'table' | 'plot' | 'stats' | 'latex';
//         this.switchPanel(panel);
//         // Update active state
//         panelTabs.forEach(t => t.classList.remove("active"));
//         tab.classList.add("active");
//       });
//     });
//
//     return toolbar;
//   }
//
//   /**
//    * Switch between panels (table, plot, stats, latex)
//    */
//   private switchPanel(panel: 'table' | 'plot' | 'stats' | 'latex'): void {
//     if (!this.wrapper) return;
//
//     this.activePanel = panel;
//     const contentArea = this.wrapper.querySelector(".csv-content-area") as HTMLElement;
//     if (!contentArea) return;
//
//     // Hide all panels
//     const panels = contentArea.querySelectorAll(".csv-panel");
//     panels.forEach(p => (p as HTMLElement).style.display = "none");
//
//     // Show the selected panel
//     const selectedPanel = contentArea.querySelector(`.csv-panel-${panel}`) as HTMLElement;
//     if (selectedPanel) {
//       selectedPanel.style.display = "block";
//     } else {
//       // Create panel if it doesn't exist
//       this.createPanel(panel, contentArea);
//     }
//   }
//
//   /**
//    * Create a panel on first access
//    */
//   private createPanel(panel: 'table' | 'plot' | 'stats' | 'latex', contentArea: HTMLElement): void {
//     const panelEl = document.createElement("div");
//     panelEl.className = `csv-panel csv-panel-${panel}`;
//
//     switch (panel) {
//       case 'plot':
//         this.renderPlotPanel(panelEl);
//         break;
//       case 'stats':
//         this.renderStatsPanel(panelEl);
//         break;
//       case 'latex':
//         this.renderLatexPanel(panelEl);
//         break;
//       default:
//         return; // Table panel is already created
//     }
//
//     contentArea.appendChild(panelEl);
//   }
//
//   /**
//    * Load and initialize DataTableManager with CSV content
//    */
//   private async loadCsv(filePath: string, tableContainer: HTMLElement, wrapper: HTMLElement): Promise<void> {
//     try {
//       const url = this.config.getFileUrl(filePath, false, false);
//       const response = await fetch(url);
//       if (!response.ok) throw new Error("Failed to fetch CSV");
//
//       const data = await response.json();
//       const content = data.content || "";
//
//       // Store raw content for reload
//       this.currentCsvContent = content;
//       (tableContainer as any).__rawContent = content;
//
//       // Initialize DataTableManager with status bar callback
//       const statusCallback = (msg: string) => {
//         const infoEl = wrapper.querySelector(".csv-info");
//         if (infoEl) infoEl.textContent = msg;
//       };
//
//       this.dataTableManager = new DataTableManager(statusCallback);
//
//       // Load CSV content into blank table (Excel-like behavior)
//       this.dataTableManager.loadFromCSVContent(content, filePath);
//       this.dataTableManager.renderEditableDataTable();
//       this.dataTableManager.setupColumnResizing();
//       this.dataTableManager.setupVirtualScrolling();
//
//       // Update info
//       const currentData = this.dataTableManager.getCurrentData();
//       const infoEl = wrapper.querySelector(".csv-info");
//       if (infoEl && currentData) {
//         infoEl.textContent = `${currentData.rows.length} rows × ${currentData.columns.length} columns`;
//       }
//
//       // Setup right-click context menu for header/index operations
//       this.setupContextMenu(tableContainer);
//
//       // Setup toggle raw view button
//       const toggleRawBtn = wrapper.querySelector(".csv-toggle-raw");
//       let showingRaw = false;
//       toggleRawBtn?.addEventListener("click", () => {
//         showingRaw = !showingRaw;
//         if (showingRaw) {
//           tableContainer.innerHTML = `<pre class="csv-raw-content">${this.escapeHtml(content)}</pre>`;
//           toggleRawBtn.innerHTML = '<i class="fas fa-table"></i>';
//         } else {
//           // Re-render the DataTableManager
//           if (this.dataTableManager) {
//             this.dataTableManager.renderEditableDataTable();
//             this.dataTableManager.setupColumnResizing();
//           }
//           toggleRawBtn.innerHTML = '<i class="fas fa-code"></i>';
//         }
//       });
//
//       // Setup save button
//       const saveBtn = wrapper.querySelector(".csv-save-btn");
//       saveBtn?.addEventListener("click", async () => {
//         await this.saveFile();
//       });
//
//     } catch (error) {
//       console.error("[CsvEditor] Error loading CSV:", error);
//       tableContainer.innerHTML = `
//         <div class="media-viewer-error">
//           <i class="fas fa-exclamation-triangle"></i>
//           <p>Failed to load CSV</p>
//           <small>${filePath}</small>
//         </div>
//       `;
//     }
//   }
//
//   /**
//    * Setup right-click context menu for header/index operations
//    */
//   private setupContextMenu(tableContainer: HTMLElement): void {
//     // Create context menu element
//     const contextMenu = document.createElement('div');
//     contextMenu.className = 'csv-context-menu';
//     contextMenu.style.display = 'none';
//     contextMenu.innerHTML = `
//       <div class="csv-context-menu-item" data-action="use-header">
//         <i class="fas fa-heading"></i> Use first row as header
//       </div>
//       <div class="csv-context-menu-item" data-action="insert-header">
//         <i class="fas fa-arrow-down"></i> Insert header as first row
//       </div>
//       <div class="csv-context-menu-divider"></div>
//       <div class="csv-context-menu-item" data-action="use-index">
//         <i class="fas fa-hashtag"></i> Use first column as index
//       </div>
//       <div class="csv-context-menu-item" data-action="insert-index">
//         <i class="fas fa-arrow-right"></i> Insert index column
//       </div>
//     `;
//     document.body.appendChild(contextMenu);
//
//     // Show context menu on right-click
//     tableContainer.addEventListener('contextmenu', (e) => {
//       e.preventDefault();
//
//       // Use clientX/clientY for fixed positioning
//       let x = e.clientX;
//       let y = e.clientY;
//
//       // Show menu first to get its dimensions
//       contextMenu.style.display = 'block';
//
//       // Adjust position if menu would go off-screen
//       const menuRect = contextMenu.getBoundingClientRect();
//       const viewportWidth = window.innerWidth;
//       const viewportHeight = window.innerHeight;
//
//       if (x + menuRect.width > viewportWidth) {
//         x = viewportWidth - menuRect.width - 10;
//       }
//       if (y + menuRect.height > viewportHeight) {
//         y = viewportHeight - menuRect.height - 10;
//       }
//
//       contextMenu.style.left = `${x}px`;
//       contextMenu.style.top = `${y}px`;
//     });
//
//     // Hide context menu on click elsewhere
//     document.addEventListener('click', () => {
//       contextMenu.style.display = 'none';
//     });
//
//     // Handle menu item clicks
//     contextMenu.addEventListener('click', (e) => {
//       const item = (e.target as HTMLElement).closest('.csv-context-menu-item');
//       if (!item || !this.dataTableManager) return;
//
//       const action = item.getAttribute('data-action');
//       switch (action) {
//         case 'use-header':
//           this.dataTableManager.useFirstRowAsHeader();
//           this.dataTableManager.setupVirtualScrolling();
//           break;
//         case 'insert-header':
//           this.dataTableManager.insertHeaderAsFirstRow();
//           this.dataTableManager.setupVirtualScrolling();
//           break;
//         case 'use-index':
//           this.dataTableManager.useFirstColumnAsIndex();
//           this.dataTableManager.setupVirtualScrolling();
//           break;
//         case 'insert-index':
//           this.dataTableManager.insertIndexColumn();
//           this.dataTableManager.setupVirtualScrolling();
//           break;
//       }
//       contextMenu.style.display = 'none';
//     });
//   }
//
//   /**
//    * Save the current CSV content
//    */
//   async saveFile(): Promise<boolean> {
//     if (!this.dataTableManager || !this.currentFilePath) return false;
//
//     try {
//       const csvContent = this.dataTableManager.exportToCSV();
//       const url = this.config.getFileUrl(this.currentFilePath, false, false);
//
//       const response = await fetch(url, {
//         method: "PUT",
//         headers: {
//           "Content-Type": "application/json",
//           "X-CSRFToken": this.getCsrfToken(),
//         },
//         body: JSON.stringify({ content: csvContent }),
//       });
//
//       if (!response.ok) throw new Error("Failed to save CSV");
//
//       console.log("[CsvEditor] CSV saved successfully");
//       return true;
//     } catch (error) {
//       console.error("[CsvEditor] Error saving CSV:", error);
//       alert("Failed to save CSV file");
//       return false;
//     }
//   }
//
//   /**
//    * Get CSRF token from cookies
//    */
//   private getCsrfToken(): string {
//     const name = "csrftoken";
//     const cookies = document.cookie.split(";");
//     for (const cookie of cookies) {
//       const [key, value] = cookie.trim().split("=");
//       if (key === name) return value;
//     }
//     return "";
//   }
//
//   /**
//    * Escape HTML special characters
//    */
//   private escapeHtml(text: string): string {
//     const div = document.createElement("div");
//     div.textContent = text;
//     return div.innerHTML;
//   }
//
//   /**
//    * Download the file
//    */
//   private downloadFile(filePath: string): void {
//     const url = this.config.getFileUrl(filePath, true, true);
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = filePath.split("/").pop() || "download";
//     document.body.appendChild(a);
//     a.click();
//     document.body.removeChild(a);
//     this.config.onDownload?.(filePath);
//   }
//
//   /**
//    * Open file in new tab
//    */
//   private openInNewTab(filePath: string): void {
//     const url = this.config.getFileUrl(filePath, false, false);
//     window.open(url, "_blank");
//   }
//
//   /**
//    * Get the DataTableManager instance
//    */
//   getDataTableManager(): DataTableManager | null {
//     return this.dataTableManager;
//   }
//
//   /**
//    * Cleanup resources
//    */
//   cleanup(): void {
//     this.dataTableManager = null;
//     this.currentFilePath = null;
//     this.wrapper = null;
//   }
//
//   // ========================================
//   // Plot Panel
//   // ========================================
//
//   /**
//    * Render the plot configuration panel
//    */
//   private renderPlotPanel(panel: HTMLElement): void {
//     const data = this.dataTableManager?.getCurrentData();
//     const columns = data?.columns || [];
//
//     panel.innerHTML = `
//       <div class="csv-plot-panel">
//         <div class="csv-plot-config">
//           <h4><i class="fas fa-chart-line"></i> Quick Plot</h4>
//           <div class="plot-config-row">
//             <label>Plot Type:</label>
//             <select class="plot-type-select">
//               <option value="line">Line Chart</option>
//               <option value="scatter">Scatter Plot</option>
//               <option value="bar">Bar Chart</option>
//               <option value="hist">Histogram</option>
//               <option value="box">Box Plot</option>
//             </select>
//           </div>
//           <div class="plot-config-row">
//             <label>X Column:</label>
//             <select class="plot-x-select">
//               <option value="">-- Auto (row index) --</option>
//               ${columns.map(c => `<option value="${c}">${c}</option>`).join('')}
//             </select>
//           </div>
//           <div class="plot-config-row">
//             <label>Y Column:</label>
//             <select class="plot-y-select">
//               ${columns.map((c, i) => `<option value="${c}" ${i === 1 ? 'selected' : ''}>${c}</option>`).join('')}
//             </select>
//           </div>
//           <div class="plot-config-row">
//             <label>Color By:</label>
//             <select class="plot-hue-select">
//               <option value="">-- None --</option>
//               ${columns.map(c => `<option value="${c}">${c}</option>`).join('')}
//             </select>
//           </div>
//           <button class="csv-control-btn plot-generate-btn">
//             <i class="fas fa-play"></i> Generate Plot
//           </button>
//         </div>
//         <div class="csv-plot-preview">
//           <div class="plot-placeholder">
//             <i class="fas fa-chart-area"></i>
//             <p>Configure and generate a plot</p>
//           </div>
//         </div>
//       </div>
//     `;
//
//     // Setup generate button
//     const generateBtn = panel.querySelector(".plot-generate-btn");
//     generateBtn?.addEventListener("click", () => this.generatePlot(panel));
//   }
//
//   /**
//    * Generate plot using figrecipe_app API
//    */
//   private async generatePlot(panel: HTMLElement): Promise<void> {
//     const data = this.dataTableManager?.getCurrentData();
//     if (!data) return;
//
//     const plotType = (panel.querySelector(".plot-type-select") as HTMLSelectElement)?.value || 'line';
//     const xCol = (panel.querySelector(".plot-x-select") as HTMLSelectElement)?.value;
//     const yCol = (panel.querySelector(".plot-y-select") as HTMLSelectElement)?.value;
//     const hueCol = (panel.querySelector(".plot-hue-select") as HTMLSelectElement)?.value;
//
//     const previewArea = panel.querySelector(".csv-plot-preview");
//     if (!previewArea) return;
//
//     previewArea.innerHTML = `
//       <div class="plot-loading">
//         <i class="fas fa-spinner fa-spin"></i> Generating plot...
//       </div>
//     `;
//
//     try {
//       // Prepare plot specification
//       // Convert DataRow objects to 2D numeric array
//       const numericData = data.rows.map(row =>
//         data.columns.map(col => parseFloat(String(row[col])) || 0)
//       );
//
//       const plotSpec: PlotSpec = {
//         figure: {
//           width_mm: 120,
//           height_mm: 80,
//           dpi: 150
//         },
//         plot: {
//           kind: plotType,
//           x_col: xCol || undefined,
//           y_col: yCol || undefined,
//           hue_col: hueCol || undefined,
//           data: numericData,
//           columns: data.columns
//         }
//       };
//
//       // Call figrecipe_app API
//       const response = await fetch('/api/vis/plot/', {
//         method: 'POST',
//         headers: {
//           'Content-Type': 'application/json',
//           'X-CSRFToken': this.getCsrfToken()
//         },
//         body: JSON.stringify(plotSpec)
//       });
//
//       if (!response.ok) {
//         const error = await response.json();
//         throw new Error(error.error || 'Plot generation failed');
//       }
//
//       // Display SVG
//       const svgContent = await response.text();
//       previewArea.innerHTML = `
//         <div class="plot-result">
//           ${svgContent}
//           <div class="plot-actions">
//             <button class="csv-control-btn plot-download-svg" title="Download SVG">
//               <i class="fas fa-download"></i> SVG
//             </button>
//             <button class="csv-control-btn plot-open-vis" title="Open in Vis Editor">
//               <i class="fas fa-external-link-alt"></i> Edit in Vis
//             </button>
//           </div>
//         </div>
//       `;
//
//       // Setup download button
//       const downloadBtn = previewArea.querySelector(".plot-download-svg");
//       downloadBtn?.addEventListener("click", () => {
//         const blob = new Blob([svgContent], { type: 'image/svg+xml' });
//         const url = URL.createObjectURL(blob);
//         const a = document.createElement('a');
//         a.href = url;
//         a.download = 'plot.svg';
//         a.click();
//         URL.revokeObjectURL(url);
//       });
//
//     } catch (error) {
//       console.error("[CsvEditor] Plot generation error:", error);
//       previewArea.innerHTML = `
//         <div class="plot-error">
//           <i class="fas fa-exclamation-triangle"></i>
//           <p>Failed to generate plot</p>
//           <small>${error instanceof Error ? error.message : 'Unknown error'}</small>
//         </div>
//       `;
//     }
//   }
//
//   // ========================================
//   // Statistics Panel
//   // ========================================
//
//   /**
//    * Render the statistics panel
//    */
//   private renderStatsPanel(panel: HTMLElement): void {
//     const data = this.dataTableManager?.getCurrentData();
//     if (!data || data.rows.length === 0) {
//       panel.innerHTML = `
//         <div class="csv-stats-empty">
//           <i class="fas fa-chart-bar"></i>
//           <p>No data available for statistics</p>
//         </div>
//       `;
//       return;
//     }
//
//     // Calculate statistics for each numeric column
//     const stats: ColumnStats[] = [];
//     for (let colIdx = 0; colIdx < data.columns.length; colIdx++) {
//       const colName = data.columns[colIdx];
//       const values: number[] = [];
//
//       for (const row of data.rows) {
//         const val = parseFloat(String(row[colName]));
//         if (!isNaN(val)) {
//           values.push(val);
//         }
//       }
//
//       if (values.length > 0) {
//         stats.push(this.calculateColumnStats(colName, values));
//       }
//     }
//
//     panel.innerHTML = `
//       <div class="csv-stats-panel">
//         <h4><i class="fas fa-calculator"></i> Descriptive Statistics</h4>
//         <div class="stats-summary">
//           <span class="stats-badge">${data.rows.length} rows</span>
//           <span class="stats-badge">${data.columns.length} columns</span>
//           <span class="stats-badge">${stats.length} numeric columns</span>
//         </div>
//         <div class="stats-table-wrapper">
//           <table class="stats-table">
//             <thead>
//               <tr>
//                 <th>Column</th>
//                 <th>Count</th>
//                 <th>Mean</th>
//                 <th>Std</th>
//                 <th>Min</th>
//                 <th>Median</th>
//                 <th>Max</th>
//                 <th>Sum</th>
//               </tr>
//             </thead>
//             <tbody>
//               ${stats.map(s => `
//                 <tr>
//                   <td class="stats-col-name">${this.escapeHtml(s.column)}</td>
//                   <td>${s.count}</td>
//                   <td>${s.mean !== null ? s.mean.toFixed(4) : '-'}</td>
//                   <td>${s.std !== null ? s.std.toFixed(4) : '-'}</td>
//                   <td>${s.min !== null ? s.min.toFixed(4) : '-'}</td>
//                   <td>${s.median !== null ? s.median.toFixed(4) : '-'}</td>
//                   <td>${s.max !== null ? s.max.toFixed(4) : '-'}</td>
//                   <td>${s.sum !== null ? s.sum.toFixed(4) : '-'}</td>
//                 </tr>
//               `).join('')}
//             </tbody>
//           </table>
//         </div>
//         <div class="stats-actions">
//           <button class="csv-control-btn stats-copy-btn" title="Copy to clipboard">
//             <i class="fas fa-copy"></i> Copy Stats
//           </button>
//         </div>
//       </div>
//     `;
//
//     // Setup copy button
//     const copyBtn = panel.querySelector(".stats-copy-btn");
//     copyBtn?.addEventListener("click", () => {
//       const text = stats.map(s =>
//         `${s.column}\t${s.count}\t${s.mean?.toFixed(4) || '-'}\t${s.std?.toFixed(4) || '-'}\t${s.min?.toFixed(4) || '-'}\t${s.median?.toFixed(4) || '-'}\t${s.max?.toFixed(4) || '-'}\t${s.sum?.toFixed(4) || '-'}`
//       ).join('\n');
//       navigator.clipboard.writeText(`Column\tCount\tMean\tStd\tMin\tMedian\tMax\tSum\n${text}`);
//       alert('Statistics copied to clipboard');
//     });
//   }
//
//   /**
//    * Calculate statistics for a column of numeric values
//    */
//   private calculateColumnStats(column: string, values: number[]): ColumnStats {
//     const count = values.length;
//     const sum = values.reduce((a, b) => a + b, 0);
//     const mean = sum / count;
//     const variance = values.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / count;
//     const std = Math.sqrt(variance);
//     const sorted = [...values].sort((a, b) => a - b);
//     const min = sorted[0];
//     const max = sorted[sorted.length - 1];
//     const median = count % 2 === 0
//       ? (sorted[count / 2 - 1] + sorted[count / 2]) / 2
//       : sorted[Math.floor(count / 2)];
//
//     return { column, count, mean, std, min, max, median, sum };
//   }
//
//   // ========================================
//   // LaTeX Export Panel
//   // ========================================
//
//   /**
//    * Render the LaTeX export panel
//    */
//   private renderLatexPanel(panel: HTMLElement): void {
//     const data = this.dataTableManager?.getCurrentData();
//     if (!data || data.rows.length === 0) {
//       panel.innerHTML = `
//         <div class="csv-latex-empty">
//           <i class="fas fa-file-code"></i>
//           <p>No data available for LaTeX export</p>
//         </div>
//       `;
//       return;
//     }
//
//     const latex = this.generateLatexTable(data.columns, data.rows);
//
//     panel.innerHTML = `
//       <div class="csv-latex-panel">
//         <h4><i class="fas fa-file-code"></i> LaTeX Table Export</h4>
//         <div class="latex-options">
//           <label>
//             <input type="checkbox" class="latex-opt-booktabs" checked>
//             Use booktabs (\\toprule, \\midrule, \\bottomrule)
//           </label>
//           <label>
//             <input type="checkbox" class="latex-opt-caption">
//             Include caption
//           </label>
//           <label>
//             <input type="checkbox" class="latex-opt-label">
//             Include label
//           </label>
//         </div>
//         <div class="latex-preview-wrapper">
//           <textarea class="latex-preview" readonly>${latex}</textarea>
//         </div>
//         <div class="latex-actions">
//           <button class="csv-control-btn latex-copy-btn" title="Copy to clipboard">
//             <i class="fas fa-copy"></i> Copy LaTeX
//           </button>
//           <button class="csv-control-btn latex-download-btn" title="Download as .tex file">
//             <i class="fas fa-download"></i> Download .tex
//           </button>
//         </div>
//       </div>
//     `;
//
//     const updatePreview = () => {
//       const booktabs = (panel.querySelector(".latex-opt-booktabs") as HTMLInputElement)?.checked;
//       const caption = (panel.querySelector(".latex-opt-caption") as HTMLInputElement)?.checked;
//       const label = (panel.querySelector(".latex-opt-label") as HTMLInputElement)?.checked;
//       const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
//       if (preview) {
//         preview.value = this.generateLatexTable(data.columns, data.rows, { booktabs, caption, label });
//       }
//     };
//
//     // Update preview on option change
//     panel.querySelectorAll("input[type=checkbox]").forEach(cb => {
//       cb.addEventListener("change", updatePreview);
//     });
//
//     // Setup copy button
//     const copyBtn = panel.querySelector(".latex-copy-btn");
//     copyBtn?.addEventListener("click", () => {
//       const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
//       if (preview) {
//         navigator.clipboard.writeText(preview.value);
//         alert('LaTeX table copied to clipboard');
//       }
//     });
//
//     // Setup download button
//     const downloadBtn = panel.querySelector(".latex-download-btn");
//     downloadBtn?.addEventListener("click", () => {
//       const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
//       if (preview) {
//         const blob = new Blob([preview.value], { type: 'text/x-latex' });
//         const url = URL.createObjectURL(blob);
//         const a = document.createElement('a');
//         a.href = url;
//         const baseName = this.currentFilePath?.split('/').pop()?.replace(/\.[^.]+$/, '') || 'table';
//         a.download = `${baseName}.tex`;
//         a.click();
//         URL.revokeObjectURL(url);
//       }
//     });
//   }
//
//   /**
//    * Generate LaTeX table code from data
//    */
//   private generateLatexTable(
//     columns: string[],
//     rows: DataRow[],
//     options: { booktabs?: boolean; caption?: boolean; label?: boolean } = {}
//   ): string {
//     const { booktabs = true, caption = false, label = false } = options;
//
//     const colSpec = columns.map(() => 'c').join(' ');
//     const headerRow = columns.map(c => this.escapeLatex(c)).join(' & ');
//     const dataRows = rows.slice(0, 100).map(row =>
//       columns.map(col => this.escapeLatex(String(row[col] ?? ''))).join(' & ')
//     );
//
//     let latex = '';
//     latex += '\\begin{table}[htbp]\n';
//     latex += '  \\centering\n';
//
//     if (caption) {
//       latex += '  \\caption{Table Caption Here}\n';
//     }
//     if (label) {
//       const baseName = this.currentFilePath?.split('/').pop()?.replace(/\.[^.]+$/, '') || 'table';
//       latex += `  \\label{tab:${baseName}}\n`;
//     }
//
//     latex += `  \\begin{tabular}{${colSpec}}\n`;
//
//     if (booktabs) {
//       latex += '    \\toprule\n';
//       latex += `    ${headerRow} \\\\\n`;
//       latex += '    \\midrule\n';
//     } else {
//       latex += '    \\hline\n';
//       latex += `    ${headerRow} \\\\\n`;
//       latex += '    \\hline\n';
//     }
//
//     for (const row of dataRows) {
//       latex += `    ${row} \\\\\n`;
//     }
//
//     if (booktabs) {
//       latex += '    \\bottomrule\n';
//     } else {
//       latex += '    \\hline\n';
//     }
//
//     latex += '  \\end{tabular}\n';
//     latex += '\\end{table}\n';
//
//     if (rows.length > 100) {
//       latex += `\n% Note: Table truncated to first 100 rows (original: ${rows.length} rows)\n`;
//     }
//
//     return latex;
//   }
//
//   /**
//    * Escape special LaTeX characters
//    */
//   private escapeLatex(text: string): string {
//     return text
//       .replace(/\\/g, '\\textbackslash{}')
//       .replace(/&/g, '\\&')
//       .replace(/%/g, '\\%')
//       .replace(/\$/g, '\\$')
//       .replace(/#/g, '\\#')
//       .replace(/_/g, '\\_')
//       .replace(/\{/g, '\\{')
//       .replace(/\}/g, '\\}')
//       .replace(/~/g, '\\textasciitilde{}')
//       .replace(/\^/g, '\\textasciicircum{}');
//   }
// }

// =============================================================================
// End of Source Code
// =============================================================================
