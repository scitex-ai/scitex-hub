/**
 * Tests for apps/code_app/static/code_app/ts/workspace/editor/MediaViewerManager.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// TODO: Update import path based on your tsconfig paths
// import { } from '@/apps/code_app/static/code_app/ts/workspace/editor/MediaViewerManager';

describe('MediaViewerManager', () => {
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
// Source: apps/code_app/static/code_app/ts/workspace/editor/MediaViewerManager.ts
// =============================================================================

// /**
//  * Media Viewer Manager
//  * Handles rendering of non-text files (images, PDFs, CSVs) in the editor area
//  * Uses the shared DataTableManager for full-featured CSV editing
//  */
// 
// import type { FileType } from "../core/types";
// import { DataTableManager, Dataset } from "@/components/data-table/index.js";
// 
// export class MediaViewerManager {
//   private container: HTMLElement | null = null;
//   private currentFilePath: string | null = null;
//   private dataTableManager: DataTableManager | null = null;
// 
//   constructor() {
//     this.initContainer();
//   }
// 
//   /**
//    * Initialize the media viewer container
//    */
//   private initContainer(): void {
//     // Check if container already exists
//     this.container = document.getElementById("media-viewer");
//     if (this.container) return;
// 
//     // Create the container
//     this.container = document.createElement("div");
//     this.container.id = "media-viewer";
//     this.container.className = "media-viewer-container";
//     this.container.style.display = "none";
// 
//     // Insert into editor container (alongside monaco-editor)
//     const editorContainer = document.getElementById("editor-container");
//     if (editorContainer) {
//       editorContainer.appendChild(this.container);
//     }
//   }
// 
//   /**
//    * Show media viewer and hide Monaco editor
//    */
//   show(): void {
//     if (this.container) {
//       this.container.style.display = "flex";
//     }
//     const monacoEditor = document.getElementById("monaco-editor");
//     if (monacoEditor) {
//       monacoEditor.style.display = "none";
//     }
//     // Also hide welcome screen
//     const welcomeScreen = document.getElementById("welcome-screen");
//     if (welcomeScreen) {
//       welcomeScreen.style.display = "none";
//     }
//   }
// 
//   /**
//    * Hide media viewer and show Monaco editor
//    */
//   hide(): void {
//     if (this.container) {
//       this.container.style.display = "none";
//     }
//     const monacoEditor = document.getElementById("monaco-editor");
//     if (monacoEditor) {
//       monacoEditor.style.display = "block";
//     }
//   }
// 
//   /**
//    * Display a file in the media viewer
//    */
//   displayFile(filePath: string, fileType: FileType, blobUrl?: string): void {
//     if (!this.container) {
//       this.initContainer();
//     }
//     if (!this.container) return;
// 
//     this.currentFilePath = filePath;
//     this.container.innerHTML = "";
// 
//     switch (fileType) {
//       case "image":
//         this.displayImage(filePath, blobUrl);
//         break;
//       case "pdf":
//         this.displayPdf(filePath, blobUrl);
//         break;
//       case "csv":
//         this.displayCsv(filePath);
//         break;
//       case "binary":
//         this.displayBinaryPlaceholder(filePath);
//         break;
//       default:
//         // Text files should be handled by Monaco
//         this.hide();
//         return;
//     }
// 
//     this.show();
//   }
// 
//   /**
//    * Display an image file
//    */
//   private displayImage(filePath: string, blobUrl?: string): void {
//     if (!this.container) return;
// 
//     const wrapper = document.createElement("div");
//     wrapper.className = "media-viewer-image-wrapper";
// 
//     // Toolbar
//     const toolbar = this.createToolbar(filePath, "image");
//     wrapper.appendChild(toolbar);
// 
//     // Image container with zoom/pan support
//     const imageContainer = document.createElement("div");
//     imageContainer.className = "media-viewer-image-container";
// 
//     const img = document.createElement("img");
//     img.className = "media-viewer-image";
//     img.alt = filePath.split("/").pop() || "Image";
// 
//     // Use blob URL if available, otherwise construct API URL
//     if (blobUrl) {
//       img.src = blobUrl;
//     } else {
//       // Get project info from page
//       const projectData = document.getElementById("project-data");
//       const projectId = projectData?.dataset.projectId || "";
//       img.src = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
//     }
// 
//     img.onerror = () => {
//       img.style.display = "none";
//       const errorMsg = document.createElement("div");
//       errorMsg.className = "media-viewer-error";
//       errorMsg.innerHTML = `
//         <i class="fas fa-exclamation-triangle"></i>
//         <p>Failed to load image</p>
//         <small>${filePath}</small>
//       `;
//       imageContainer.appendChild(errorMsg);
//     };
// 
//     imageContainer.appendChild(img);
//     wrapper.appendChild(imageContainer);
//     this.container.appendChild(wrapper);
// 
//     // Add zoom controls
//     this.setupImageZoom(img, imageContainer);
//   }
// 
//   /**
//    * Display a PDF file using PDF.js
//    */
//   private displayPdf(filePath: string, blobUrl?: string): void {
//     if (!this.container) return;
// 
//     const wrapper = document.createElement("div");
//     wrapper.className = "media-viewer-pdf-wrapper";
// 
//     // Toolbar
//     const toolbar = this.createToolbar(filePath, "pdf");
// 
//     // Add PDF-specific controls
//     const pdfControls = document.createElement("div");
//     pdfControls.className = "media-viewer-pdf-controls";
//     pdfControls.innerHTML = `
//       <button class="pdf-control-btn" id="pdf-prev" title="Previous page">
//         <i class="fas fa-chevron-left"></i>
//       </button>
//       <span class="pdf-page-info">
//         <input type="number" id="pdf-page-input" min="1" value="1" class="pdf-page-input">
//         <span> / </span>
//         <span id="pdf-total-pages">-</span>
//       </span>
//       <button class="pdf-control-btn" id="pdf-next" title="Next page">
//         <i class="fas fa-chevron-right"></i>
//       </button>
//       <span class="pdf-control-separator"></span>
//       <button class="pdf-control-btn" id="pdf-zoom-out" title="Zoom out">
//         <i class="fas fa-search-minus"></i>
//       </button>
//       <span id="pdf-zoom-level" class="pdf-zoom-level">100%</span>
//       <button class="pdf-control-btn" id="pdf-zoom-in" title="Zoom in">
//         <i class="fas fa-search-plus"></i>
//       </button>
//       <button class="pdf-control-btn" id="pdf-fit-width" title="Fit width">
//         <i class="fas fa-arrows-alt-h"></i>
//       </button>
//     `;
//     toolbar.appendChild(pdfControls);
//     wrapper.appendChild(toolbar);
// 
//     // PDF viewer container
//     const pdfContainer = document.createElement("div");
//     pdfContainer.className = "media-viewer-pdf-container";
//     pdfContainer.id = "pdf-viewer-container";
// 
//     // Canvas for PDF rendering
//     const canvas = document.createElement("canvas");
//     canvas.id = "pdf-canvas";
//     canvas.className = "media-viewer-pdf-canvas";
//     pdfContainer.appendChild(canvas);
// 
//     wrapper.appendChild(pdfContainer);
//     this.container.appendChild(wrapper);
// 
//     // Load PDF
//     this.loadPdf(filePath, blobUrl);
//   }
// 
//   /**
//    * Load and render PDF using PDF.js
//    */
//   private async loadPdf(filePath: string, blobUrl?: string): Promise<void> {
//     // Check if PDF.js is loaded
//     const pdfjsLib = (window as any).pdfjsLib;
//     if (!pdfjsLib) {
//       // Load PDF.js from CDN
//       await this.loadPdfJs();
//     }
// 
//     const lib = (window as any).pdfjsLib;
//     if (!lib) {
//       console.error("[MediaViewerManager] PDF.js not available");
//       return;
//     }
// 
//     // Get PDF URL
//     let pdfUrl: string;
//     if (blobUrl) {
//       pdfUrl = blobUrl;
//     } else {
//       const projectData = document.getElementById("project-data");
//       const projectId = projectData?.dataset.projectId || "";
//       pdfUrl = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
//     }
// 
//     try {
//       const loadingTask = lib.getDocument(pdfUrl);
//       const pdf = await loadingTask.promise;
// 
//       // Store PDF object for navigation
//       (window as any).__currentPdf = pdf;
//       (window as any).__currentPdfPage = 1;
//       (window as any).__currentPdfScale = 1.0;
// 
//       // Update total pages
//       const totalPagesEl = document.getElementById("pdf-total-pages");
//       if (totalPagesEl) {
//         totalPagesEl.textContent = pdf.numPages.toString();
//       }
// 
//       // Render first page
//       await this.renderPdfPage(pdf, 1, 1.0);
// 
//       // Setup navigation controls
//       this.setupPdfControls(pdf);
//     } catch (error) {
//       console.error("[MediaViewerManager] Error loading PDF:", error);
//       const pdfContainer = document.getElementById("pdf-viewer-container");
//       if (pdfContainer) {
//         pdfContainer.innerHTML = `
//           <div class="media-viewer-error">
//             <i class="fas fa-exclamation-triangle"></i>
//             <p>Failed to load PDF</p>
//             <small>${filePath}</small>
//           </div>
//         `;
//       }
//     }
//   }
// 
//   /**
//    * Load PDF.js library from CDN
//    */
//   private loadPdfJs(): Promise<void> {
//     return new Promise((resolve, reject) => {
//       // Check if already loaded
//       if ((window as any).pdfjsLib) {
//         resolve();
//         return;
//       }
// 
//       const script = document.createElement("script");
//       script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
//       script.onload = () => {
//         const lib = (window as any).pdfjsLib;
//         if (lib) {
//           lib.GlobalWorkerOptions.workerSrc =
//             "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
//         }
//         resolve();
//       };
//       script.onerror = reject;
//       document.head.appendChild(script);
//     });
//   }
// 
//   /**
//    * Render a specific PDF page
//    */
//   private async renderPdfPage(pdf: any, pageNum: number, scale: number): Promise<void> {
//     const canvas = document.getElementById("pdf-canvas") as HTMLCanvasElement;
//     if (!canvas) return;
// 
//     const page = await pdf.getPage(pageNum);
//     const viewport = page.getViewport({ scale });
// 
//     canvas.height = viewport.height;
//     canvas.width = viewport.width;
// 
//     const context = canvas.getContext("2d");
//     if (!context) return;
// 
//     await page.render({
//       canvasContext: context,
//       viewport: viewport,
//     }).promise;
// 
//     // Update page input
//     const pageInput = document.getElementById("pdf-page-input") as HTMLInputElement;
//     if (pageInput) {
//       pageInput.value = pageNum.toString();
//     }
// 
//     // Update zoom level display
//     const zoomLevel = document.getElementById("pdf-zoom-level");
//     if (zoomLevel) {
//       zoomLevel.textContent = `${Math.round(scale * 100)}%`;
//     }
//   }
// 
//   /**
//    * Setup PDF navigation controls
//    */
//   private setupPdfControls(pdf: any): void {
//     const prevBtn = document.getElementById("pdf-prev");
//     const nextBtn = document.getElementById("pdf-next");
//     const pageInput = document.getElementById("pdf-page-input") as HTMLInputElement;
//     const zoomInBtn = document.getElementById("pdf-zoom-in");
//     const zoomOutBtn = document.getElementById("pdf-zoom-out");
//     const fitWidthBtn = document.getElementById("pdf-fit-width");
// 
//     const goToPage = async (pageNum: number) => {
//       if (pageNum < 1 || pageNum > pdf.numPages) return;
//       (window as any).__currentPdfPage = pageNum;
//       await this.renderPdfPage(pdf, pageNum, (window as any).__currentPdfScale);
//     };
// 
//     const setZoom = async (scale: number) => {
//       (window as any).__currentPdfScale = scale;
//       await this.renderPdfPage(pdf, (window as any).__currentPdfPage, scale);
//     };
// 
//     prevBtn?.addEventListener("click", () => {
//       goToPage((window as any).__currentPdfPage - 1);
//     });
// 
//     nextBtn?.addEventListener("click", () => {
//       goToPage((window as any).__currentPdfPage + 1);
//     });
// 
//     pageInput?.addEventListener("change", () => {
//       goToPage(parseInt(pageInput.value, 10));
//     });
// 
//     zoomInBtn?.addEventListener("click", () => {
//       setZoom((window as any).__currentPdfScale * 1.25);
//     });
// 
//     zoomOutBtn?.addEventListener("click", () => {
//       setZoom((window as any).__currentPdfScale / 1.25);
//     });
// 
//     fitWidthBtn?.addEventListener("click", async () => {
//       const container = document.getElementById("pdf-viewer-container");
//       if (!container) return;
//       const page = await pdf.getPage((window as any).__currentPdfPage);
//       const viewport = page.getViewport({ scale: 1 });
//       const scale = (container.clientWidth - 40) / viewport.width;
//       setZoom(scale);
//     });
//   }
// 
//   /**
//    * Display a CSV/TSV file as a table using the shared DataTableManager
//    */
//   private async displayCsv(filePath: string): Promise<void> {
//     if (!this.container) return;
// 
//     const wrapper = document.createElement("div");
//     wrapper.className = "media-viewer-csv-wrapper";
// 
//     // Toolbar
//     const toolbar = this.createToolbar(filePath, "csv");
// 
//     // Add CSV-specific controls
//     const csvControls = document.createElement("div");
//     csvControls.className = "media-viewer-csv-controls";
//     csvControls.innerHTML = `
//       <button class="csv-control-btn" id="csv-toggle-raw" title="Toggle raw view">
//         <i class="fas fa-code"></i> Raw
//       </button>
//       <button class="csv-control-btn" id="csv-save-btn" title="Save changes">
//         <i class="fas fa-save"></i> Save
//       </button>
//       <span class="toolbar-separator"></span>
//       <button class="csv-control-btn" id="csv-plot-btn" title="Generate plot from data">
//         <i class="fas fa-chart-line"></i> Plot
//       </button>
//       <button class="csv-control-btn" id="csv-stats-btn" title="Calculate statistics">
//         <i class="fas fa-calculator"></i> Stats
//       </button>
//       <button class="csv-control-btn" id="csv-latex-btn" title="Export as LaTeX table">
//         <i class="fas fa-file-code"></i> LaTeX
//       </button>
//     `;
//     toolbar.appendChild(csvControls);
//     wrapper.appendChild(toolbar);
// 
//     // Table container for DataTableManager
//     const tableContainer = document.createElement("div");
//     tableContainer.className = "media-viewer-csv-container data-table-container";
//     tableContainer.id = "csv-table-container";
//     tableContainer.innerHTML = `
//       <div class="csv-loading">
//         <i class="fas fa-spinner fa-spin"></i> Loading...
//       </div>
//     `;
//     wrapper.appendChild(tableContainer);
// 
//     this.container.appendChild(wrapper);
// 
//     // Load and parse CSV using DataTableManager
//     await this.loadCsvWithDataTable(filePath, tableContainer);
//   }
// 
//   /**
//    * Load and render CSV file using the shared DataTableManager
//    */
//   private async loadCsvWithDataTable(filePath: string, container: HTMLElement): Promise<void> {
//     try {
//       const projectData = document.getElementById("project-data");
//       const projectId = projectData?.dataset.projectId || "";
//       const url = `/code/api/file-content/${filePath}?project_id=${projectId}`;
// 
//       const response = await fetch(url);
//       if (!response.ok) throw new Error("Failed to fetch CSV");
// 
//       const data = await response.json();
//       const content = data.content || "";
// 
//       // Store raw content for toggle
//       (container as any).__rawContent = content;
// 
//       // Initialize DataTableManager with the container
//       this.dataTableManager = new DataTableManager(
//         {
//           container: container,
//           readOnly: false, // Allow editing
//           onDataChange: (data) => {
//             console.log('[MediaViewerManager] CSV data changed');
//           }
//         }
//       );
// 
//       // First initialize a large blank table (like /vis/ does for Excel-like spreadsheet)
//       this.dataTableManager.initializeBlankTable();
// 
//       // Then load the CSV data - this will populate the data into the blank table
//       // Parse CSV and place in upper-left corner while keeping the large table size
//       this.loadCsvIntoBlankTable(content, filePath);
// 
//       this.dataTableManager.renderEditableDataTable();
//       this.dataTableManager.setupColumnResizing();
//       this.dataTableManager.setupVirtualScrolling();
// 
//       // Setup Plot, Stats, LaTeX buttons
//       this.setupCsvFeatureButtons(content, filePath);
// 
//       // Setup toggle raw view button
//       const toggleRawBtn = document.getElementById("csv-toggle-raw");
//       let showingRaw = false;
//       toggleRawBtn?.addEventListener("click", () => {
//         showingRaw = !showingRaw;
//         if (showingRaw) {
//           container.innerHTML = `<pre class="csv-raw-content">${this.escapeHtml(content)}</pre>`;
//           toggleRawBtn.innerHTML = '<i class="fas fa-table"></i> Table';
//         } else {
//           // Re-render the DataTableManager
//           if (this.dataTableManager) {
//             this.dataTableManager.renderEditableDataTable();
//             this.dataTableManager.setupColumnResizing();
//           }
//           toggleRawBtn.innerHTML = '<i class="fas fa-code"></i> Raw';
//         }
//       });
// 
//       // Setup save button
//       const saveBtn = document.getElementById("csv-save-btn");
//       saveBtn?.addEventListener("click", async () => {
//         if (!this.dataTableManager) return;
//         const csvContent = this.dataTableManager.exportToCSV();
//         await this.saveCsvFile(filePath, csvContent);
//       });
// 
//     } catch (error) {
//       console.error("[MediaViewerManager] Error loading CSV:", error);
//       container.innerHTML = `
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
//    * Save CSV file to server
//    */
//   private async saveCsvFile(filePath: string, content: string): Promise<void> {
//     try {
//       const projectData = document.getElementById("project-data");
//       const projectId = projectData?.dataset.projectId || "";
// 
//       const response = await fetch(`/code/api/file-content/${filePath}?project_id=${projectId}`, {
//         method: "PUT",
//         headers: {
//           "Content-Type": "application/json",
//           "X-CSRFToken": this.getCsrfToken(),
//         },
//         body: JSON.stringify({ content }),
//       });
// 
//       if (!response.ok) throw new Error("Failed to save CSV");
// 
//       const infoEl = document.getElementById("csv-info");
//       if (infoEl) {
//         const originalText = infoEl.textContent;
//         infoEl.textContent = "Saved!";
//         setTimeout(() => {
//           if (infoEl) infoEl.textContent = originalText || "";
//         }, 2000);
//       }
// 
//       console.log("[MediaViewerManager] CSV saved successfully");
//     } catch (error) {
//       console.error("[MediaViewerManager] Error saving CSV:", error);
//       alert("Failed to save CSV file");
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
//    * Load and parse CSV file (legacy method - kept for reference)
//    */
//   private async loadCsv(filePath: string, container: HTMLElement): Promise<void> {
//     try {
//       const projectData = document.getElementById("project-data");
//       const projectId = projectData?.dataset.projectId || "";
//       const url = `/code/api/file-content/${filePath}?project_id=${projectId}`;
// 
//       const response = await fetch(url);
//       if (!response.ok) throw new Error("Failed to fetch CSV");
// 
//       const data = await response.json();
//       const content = data.content || "";
// 
//       // Detect delimiter (comma or tab)
//       const isTsv = filePath.toLowerCase().endsWith(".tsv");
//       const delimiter = isTsv ? "\t" : ",";
// 
//       // Parse CSV
//       const rows = this.parseCsv(content, delimiter);
// 
//       if (rows.length === 0) {
//         container.innerHTML = `
//           <div class="media-viewer-error">
//             <i class="fas fa-exclamation-triangle"></i>
//             <p>Empty or invalid CSV file</p>
//           </div>
//         `;
//         return;
//       }
// 
//       // Render table
//       this.renderCsvTable(rows, container, content);
// 
//       // Update info
//       const infoEl = document.getElementById("csv-info");
//       if (infoEl) {
//         infoEl.textContent = `${rows.length} rows × ${rows[0]?.length || 0} columns`;
//       }
// 
//       // Setup toggle raw view
//       const toggleRawBtn = document.getElementById("csv-toggle-raw");
//       let showingRaw = false;
//       toggleRawBtn?.addEventListener("click", () => {
//         showingRaw = !showingRaw;
//         if (showingRaw) {
//           container.innerHTML = `<pre class="csv-raw-content">${this.escapeHtml(content)}</pre>`;
//           toggleRawBtn.innerHTML = '<i class="fas fa-table"></i> Table';
//         } else {
//           this.renderCsvTable(rows, container, content);
//           toggleRawBtn.innerHTML = '<i class="fas fa-code"></i> Raw';
//         }
//       });
//     } catch (error) {
//       console.error("[MediaViewerManager] Error loading CSV:", error);
//       container.innerHTML = `
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
//    * Parse CSV content into rows
//    */
//   private parseCsv(content: string, delimiter: string): string[][] {
//     const rows: string[][] = [];
//     let currentRow: string[] = [];
//     let currentCell = "";
//     let inQuotes = false;
// 
//     for (let i = 0; i < content.length; i++) {
//       const char = content[i];
//       const nextChar = content[i + 1];
// 
//       if (inQuotes) {
//         if (char === '"' && nextChar === '"') {
//           // Escaped quote
//           currentCell += '"';
//           i++;
//         } else if (char === '"') {
//           // End of quoted field
//           inQuotes = false;
//         } else {
//           currentCell += char;
//         }
//       } else {
//         if (char === '"') {
//           // Start of quoted field
//           inQuotes = true;
//         } else if (char === delimiter) {
//           // Field delimiter
//           currentRow.push(currentCell);
//           currentCell = "";
//         } else if (char === "\n" || (char === "\r" && nextChar === "\n")) {
//           // Row delimiter
//           currentRow.push(currentCell);
//           if (currentRow.length > 0 && currentRow.some(c => c.trim())) {
//             rows.push(currentRow);
//           }
//           currentRow = [];
//           currentCell = "";
//           if (char === "\r") i++; // Skip \n in \r\n
//         } else if (char !== "\r") {
//           currentCell += char;
//         }
//       }
//     }
// 
//     // Handle last row
//     if (currentCell || currentRow.length > 0) {
//       currentRow.push(currentCell);
//       if (currentRow.some(c => c.trim())) {
//         rows.push(currentRow);
//       }
//     }
// 
//     return rows;
//   }
// 
//   /**
//    * Render CSV data as HTML table
//    */
//   private renderCsvTable(rows: string[][], container: HTMLElement, rawContent: string): void {
//     if (rows.length === 0) return;
// 
//     const table = document.createElement("table");
//     table.className = "csv-table";
// 
//     // Header row
//     const thead = document.createElement("thead");
//     const headerRow = document.createElement("tr");
// 
//     // Row number column
//     const rowNumHeader = document.createElement("th");
//     rowNumHeader.className = "csv-row-num";
//     rowNumHeader.textContent = "#";
//     headerRow.appendChild(rowNumHeader);
// 
//     rows[0].forEach((cell, idx) => {
//       const th = document.createElement("th");
//       th.textContent = cell || `Column ${idx + 1}`;
//       th.title = cell;
//       headerRow.appendChild(th);
//     });
//     thead.appendChild(headerRow);
//     table.appendChild(thead);
// 
//     // Data rows
//     const tbody = document.createElement("tbody");
//     const maxRows = Math.min(rows.length, 1000); // Limit to 1000 rows for performance
// 
//     for (let i = 1; i < maxRows; i++) {
//       const row = rows[i];
//       const tr = document.createElement("tr");
// 
//       // Row number
//       const rowNumCell = document.createElement("td");
//       rowNumCell.className = "csv-row-num";
//       rowNumCell.textContent = i.toString();
//       tr.appendChild(rowNumCell);
// 
//       row.forEach(cell => {
//         const td = document.createElement("td");
//         td.textContent = cell;
//         td.title = cell;
//         tr.appendChild(td);
//       });
//       tbody.appendChild(tr);
//     }
//     table.appendChild(tbody);
// 
//     container.innerHTML = "";
//     container.appendChild(table);
// 
//     // Show truncation warning if needed
//     if (rows.length > 1000) {
//       const warning = document.createElement("div");
//       warning.className = "csv-truncation-warning";
//       warning.innerHTML = `
//         <i class="fas fa-info-circle"></i>
//         Showing first 1,000 of ${rows.length.toLocaleString()} rows.
//         <button id="csv-show-all">Show all</button>
//       `;
//       container.appendChild(warning);
// 
//       const showAllBtn = document.getElementById("csv-show-all");
//       showAllBtn?.addEventListener("click", () => {
//         this.renderCsvTableAll(rows, container);
//       });
//     }
//   }
// 
//   /**
//    * Render all CSV rows (for large files)
//    */
//   private renderCsvTableAll(rows: string[][], container: HTMLElement): void {
//     // Just render all rows
//     const table = container.querySelector("table");
//     const tbody = table?.querySelector("tbody");
//     if (!tbody) return;
// 
//     tbody.innerHTML = "";
//     for (let i = 1; i < rows.length; i++) {
//       const row = rows[i];
//       const tr = document.createElement("tr");
// 
//       const rowNumCell = document.createElement("td");
//       rowNumCell.className = "csv-row-num";
//       rowNumCell.textContent = i.toString();
//       tr.appendChild(rowNumCell);
// 
//       row.forEach(cell => {
//         const td = document.createElement("td");
//         td.textContent = cell;
//         td.title = cell;
//         tr.appendChild(td);
//       });
//       tbody.appendChild(tr);
//     }
// 
//     // Remove warning
//     container.querySelector(".csv-truncation-warning")?.remove();
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
//    * Display placeholder for binary files
//    */
//   private displayBinaryPlaceholder(filePath: string): void {
//     if (!this.container) return;
// 
//     const wrapper = document.createElement("div");
//     wrapper.className = "media-viewer-binary-wrapper";
// 
//     const fileName = filePath.split("/").pop() || filePath;
//     const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();
// 
//     wrapper.innerHTML = `
//       <div class="media-viewer-binary-content">
//         <i class="fas fa-file-archive media-viewer-binary-icon"></i>
//         <h3>Binary File</h3>
//         <p class="media-viewer-binary-filename">${fileName}</p>
//         <p class="media-viewer-binary-info">
//           This file type (${ext}) cannot be displayed in the editor.
//         </p>
//         <button class="btn-primary media-viewer-download-btn" id="download-binary-btn">
//           <i class="fas fa-download"></i> Download
//         </button>
//       </div>
//     `;
// 
//     this.container.appendChild(wrapper);
// 
//     // Setup download button
//     const downloadBtn = document.getElementById("download-binary-btn");
//     downloadBtn?.addEventListener("click", () => {
//       this.downloadFile(filePath);
//     });
//   }
// 
//   /**
//    * Create toolbar for media viewer
//    */
//   private createToolbar(filePath: string, fileType: string): HTMLElement {
//     const toolbar = document.createElement("div");
//     toolbar.className = "media-viewer-toolbar";
// 
//     const fileName = filePath.split("/").pop() || filePath;
//     const icon = fileType === "image" ? "fa-image" : fileType === "pdf" ? "fa-file-pdf" : "fa-file";
// 
//     toolbar.innerHTML = `
//       <div class="media-viewer-toolbar-left">
//         <i class="fas ${icon} media-viewer-icon"></i>
//         <span class="media-viewer-filename" title="${filePath}">${fileName}</span>
//       </div>
//       <div class="media-viewer-toolbar-right">
//         <button class="media-viewer-btn" id="media-download-btn" title="Download">
//           <i class="fas fa-download"></i>
//         </button>
//         <button class="media-viewer-btn" id="media-open-new-tab" title="Open in new tab">
//           <i class="fas fa-external-link-alt"></i>
//         </button>
//       </div>
//     `;
// 
//     // Setup button handlers after appending to DOM
//     setTimeout(() => {
//       const downloadBtn = document.getElementById("media-download-btn");
//       downloadBtn?.addEventListener("click", () => this.downloadFile(filePath));
// 
//       const openNewTabBtn = document.getElementById("media-open-new-tab");
//       openNewTabBtn?.addEventListener("click", () => this.openInNewTab(filePath));
//     }, 0);
// 
//     return toolbar;
//   }
// 
//   /**
//    * Setup image zoom functionality
//    */
//   private setupImageZoom(img: HTMLImageElement, container: HTMLElement): void {
//     let scale = 1;
//     let isDragging = false;
//     let startX = 0;
//     let startY = 0;
//     let translateX = 0;
//     let translateY = 0;
// 
//     const updateTransform = () => {
//       img.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
//     };
// 
//     // Zoom with mouse wheel
//     container.addEventListener("wheel", (e) => {
//       e.preventDefault();
//       const delta = e.deltaY > 0 ? 0.9 : 1.1;
//       scale = Math.max(0.1, Math.min(10, scale * delta));
//       updateTransform();
//     });
// 
//     // Pan with mouse drag
//     img.addEventListener("mousedown", (e) => {
//       isDragging = true;
//       startX = e.clientX - translateX;
//       startY = e.clientY - translateY;
//       img.style.cursor = "grabbing";
//     });
// 
//     document.addEventListener("mousemove", (e) => {
//       if (!isDragging) return;
//       translateX = e.clientX - startX;
//       translateY = e.clientY - startY;
//       updateTransform();
//     });
// 
//     document.addEventListener("mouseup", () => {
//       isDragging = false;
//       img.style.cursor = "grab";
//     });
// 
//     // Reset on double-click
//     img.addEventListener("dblclick", () => {
//       scale = 1;
//       translateX = 0;
//       translateY = 0;
//       updateTransform();
//     });
// 
//     img.style.cursor = "grab";
//   }
// 
//   /**
//    * Download the current file
//    */
//   private downloadFile(filePath: string): void {
//     const projectData = document.getElementById("project-data");
//     const projectId = projectData?.dataset.projectId || "";
//     const url = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true&download=true`;
// 
//     const a = document.createElement("a");
//     a.href = url;
//     a.download = filePath.split("/").pop() || "download";
//     document.body.appendChild(a);
//     a.click();
//     document.body.removeChild(a);
//   }
// 
//   /**
//    * Open file in new tab
//    */
//   private openInNewTab(filePath: string): void {
//     const projectData = document.getElementById("project-data");
//     const projectId = projectData?.dataset.projectId || "";
//     const url = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
//     window.open(url, "_blank");
//   }
// 
//   /**
//    * Get the currently displayed file path
//    */
//   getCurrentFilePath(): string | null {
//     return this.currentFilePath;
//   }
// 
//   /**
//    * Load CSV content into an already-initialized blank table
//    * Places the CSV data in the upper-left corner while keeping the large table size
//    * All rows are treated as data (no header detection)
//    */
//   private loadCsvIntoBlankTable(content: string, filename: string): void {
//     if (!this.dataTableManager) return;
// 
//     const currentData = this.dataTableManager.getCurrentData();
//     if (!currentData) return;
// 
//     // Parse CSV content
//     const delimiter = filename.toLowerCase().endsWith('.tsv') ? '\t' : ',';
//     const lines = content.trim().split('\n');
//     if (lines.length === 0) return;
// 
//     // Determine column count from first line
//     const firstRow = this.parseCSVLine(lines[0], delimiter);
//     const colCount = firstRow.length;
// 
//     // Parse and place ALL rows as data (no header row detection)
//     for (let rowIndex = 0; rowIndex < lines.length && rowIndex < currentData.rows.length; rowIndex++) {
//       const csvRow = this.parseCSVLine(lines[rowIndex], delimiter);
//       const dataRow = currentData.rows[rowIndex];
// 
//       csvRow.forEach((value, colIndex) => {
//         const colName = currentData.columns[colIndex];
//         if (colName) {
//           const trimmedValue = value.trim();
//           const numValue = parseFloat(trimmedValue);
//           dataRow[colName] = isNaN(numValue) || trimmedValue === '' ? trimmedValue : numValue;
//         }
//       });
//     }
// 
//     // Update the data in the manager
//     this.dataTableManager.setCurrentData(currentData);
//     console.log(`[MediaViewerManager] CSV loaded: ${lines.length} rows × ${colCount} columns`);
//   }
// 
//   /**
//    * Setup Plot, Stats, and LaTeX feature buttons
//    */
//   private setupCsvFeatureButtons(content: string, filePath: string): void {
//     // Plot button
//     const plotBtn = document.getElementById("csv-plot-btn");
//     plotBtn?.addEventListener("click", () => {
//       this.showPlotPanel(content, filePath);
//     });
// 
//     // Stats button
//     const statsBtn = document.getElementById("csv-stats-btn");
//     statsBtn?.addEventListener("click", () => {
//       this.showStatsPanel(content, filePath);
//     });
// 
//     // LaTeX button
//     const latexBtn = document.getElementById("csv-latex-btn");
//     latexBtn?.addEventListener("click", () => {
//       this.showLatexPanel(content, filePath);
//     });
//   }
// 
//   /**
//    * Show plot generation panel
//    */
//   private showPlotPanel(content: string, filePath: string): void {
//     // TODO: Implement plot panel with options (line, scatter, bar, etc.)
//     // Will use the /api/vis/plot/ endpoint
//     console.log("[MediaViewerManager] Plot panel - coming soon");
//     alert("Plot feature coming soon! Will integrate with /vis/ app.");
//   }
// 
//   /**
//    * Show statistics panel
//    */
//   private showStatsPanel(content: string, filePath: string): void {
//     // TODO: Implement stats panel showing mean, std, min, max, etc.
//     // Will use scitex.stats module
//     console.log("[MediaViewerManager] Stats panel - coming soon");
//     alert("Stats feature coming soon! Will integrate with scitex.stats.");
//   }
// 
//   /**
//    * Show LaTeX export panel
//    */
//   private showLatexPanel(content: string, filePath: string): void {
//     // Generate LaTeX table from current data
//     if (!this.dataTableManager) {
//       alert("No data table available");
//       return;
//     }
// 
//     const latexCode = this.generateLatexTable(content, filePath);
// 
//     // Show in a modal or copy to clipboard
//     this.showLatexModal(latexCode);
//   }
// 
//   /**
//    * Generate LaTeX table code from CSV content
//    * All rows are treated as data (no header detection)
//    */
//   private generateLatexTable(content: string, filePath: string): string {
//     const delimiter = filePath.toLowerCase().endsWith('.tsv') ? '\t' : ',';
//     const lines = content.trim().split('\n');
//     if (lines.length === 0) return '';
// 
//     const firstRow = this.parseCSVLine(lines[0], delimiter);
//     const colCount = firstRow.length;
// 
//     // Generate column alignment (right-aligned for numbers)
//     const colAlign = Array(colCount).fill('r').join('');
// 
//     let latex = `\\begin{table}[htbp]\n`;
//     latex += `  \\centering\n`;
//     latex += `  \\caption{${filePath.split('/').pop()?.replace('.csv', '').replace('.tsv', '') || 'Data'}}\n`;
//     latex += `  \\begin{tabular}{${colAlign}}\n`;
//     latex += `    \\toprule\n`;
// 
//     // All rows are data (no header row)
//     for (let i = 0; i < lines.length; i++) {
//       const row = this.parseCSVLine(lines[i], delimiter);
//       latex += `    ${row.map(v => v.trim()).join(' & ')} \\\\\n`;
//     }
// 
//     latex += `    \\bottomrule\n`;
//     latex += `  \\end{tabular}\n`;
//     latex += `\\end{table}`;
// 
//     return latex;
//   }
// 
//   /**
//    * Show LaTeX code in a modal with copy functionality
//    */
//   private showLatexModal(latexCode: string): void {
//     // Create modal overlay
//     const overlay = document.createElement("div");
//     overlay.className = "latex-modal-overlay";
//     overlay.style.cssText = `
//       position: fixed;
//       top: 0;
//       left: 0;
//       right: 0;
//       bottom: 0;
//       background: rgba(0, 0, 0, 0.6);
//       display: flex;
//       align-items: center;
//       justify-content: center;
//       z-index: 10000;
//     `;
// 
//     const modal = document.createElement("div");
//     modal.className = "latex-modal";
//     modal.style.cssText = `
//       background: var(--workspace-bg-secondary, #1e2228);
//       border: 1px solid var(--color-border-default, #30363d);
//       border-radius: 8px;
//       padding: 16px;
//       width: 600px;
//       max-width: 90vw;
//       max-height: 80vh;
//       display: flex;
//       flex-direction: column;
//     `;
// 
//     modal.innerHTML = `
//       <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
//         <h3 style="margin: 0; font-size: 16px; color: var(--color-fg-default, #c9d1d9);">
//           <i class="fas fa-file-code"></i> LaTeX Table
//         </h3>
//         <button id="latex-modal-close" style="background: transparent; border: none; color: var(--color-fg-muted, #8b949e); cursor: pointer; font-size: 18px;">
//           <i class="fas fa-times"></i>
//         </button>
//       </div>
//       <textarea id="latex-code-textarea" style="
//         flex: 1;
//         min-height: 300px;
//         padding: 12px;
//         background: var(--workspace-bg-tertiary, #161b22);
//         border: 1px solid var(--color-border-default, #30363d);
//         border-radius: 4px;
//         color: var(--color-fg-default, #c9d1d9);
//         font-family: var(--font-mono, 'JetBrains Mono', Monaco, monospace);
//         font-size: 12px;
//         resize: none;
//       ">${this.escapeHtml(latexCode)}</textarea>
//       <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end;">
//         <button id="latex-copy-btn" class="csv-control-btn" style="background: var(--color-accent, #238636); border-color: var(--color-accent, #238636); color: #fff;">
//           <i class="fas fa-copy"></i> Copy to Clipboard
//         </button>
//       </div>
//     `;
// 
//     overlay.appendChild(modal);
//     document.body.appendChild(overlay);
// 
//     // Close button
//     document.getElementById("latex-modal-close")?.addEventListener("click", () => {
//       overlay.remove();
//     });
// 
//     // Click outside to close
//     overlay.addEventListener("click", (e) => {
//       if (e.target === overlay) {
//         overlay.remove();
//       }
//     });
// 
//     // Copy button
//     document.getElementById("latex-copy-btn")?.addEventListener("click", async () => {
//       const textarea = document.getElementById("latex-code-textarea") as HTMLTextAreaElement;
//       try {
//         await navigator.clipboard.writeText(textarea.value);
//         const btn = document.getElementById("latex-copy-btn");
//         if (btn) {
//           btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
//           setTimeout(() => {
//             btn.innerHTML = '<i class="fas fa-copy"></i> Copy to Clipboard';
//           }, 2000);
//         }
//       } catch (err) {
//         textarea.select();
//         document.execCommand("copy");
//       }
//     });
// 
//     // Escape to close
//     const handleEscape = (e: KeyboardEvent) => {
//       if (e.key === "Escape") {
//         overlay.remove();
//         document.removeEventListener("keydown", handleEscape);
//       }
//     };
//     document.addEventListener("keydown", handleEscape);
//   }
// 
//   /**
//    * Parse a single CSV line handling quoted fields
//    */
//   private parseCSVLine(line: string, delimiter: string): string[] {
//     const result: string[] = [];
//     let currentValue = '';
//     let inQuotes = false;
// 
//     for (let i = 0; i < line.length; i++) {
//       const char = line[i];
//       const nextChar = line[i + 1];
// 
//       if (inQuotes) {
//         if (char === '"' && nextChar === '"') {
//           currentValue += '"';
//           i++;
//         } else if (char === '"') {
//           inQuotes = false;
//         } else {
//           currentValue += char;
//         }
//       } else {
//         if (char === '"') {
//           inQuotes = true;
//         } else if (char === delimiter) {
//           result.push(currentValue);
//           currentValue = '';
//         } else {
//           currentValue += char;
//         }
//       }
//     }
//     result.push(currentValue);
// 
//     return result;
//   }
// 
//   /**
//    * Clean up resources (revoke blob URLs, etc.)
//    */
//   cleanup(): void {
//     if (this.container) {
//       this.container.innerHTML = "";
//     }
//     this.currentFilePath = null;
//     // Clean up PDF.js objects
//     delete (window as any).__currentPdf;
//     delete (window as any).__currentPdfPage;
//     delete (window as any).__currentPdfScale;
//     // Clean up DataTableManager
//     this.dataTableManager = null;
//   }
// 
//   /**
//    * Get the DataTableManager instance (for external access if needed)
//    */
//   getDataTableManager(): DataTableManager | null {
//     return this.dataTableManager;
//   }
// }

// =============================================================================
// End of Source Code
// =============================================================================
