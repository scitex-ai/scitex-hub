/**
 * TableRendering - Handles table rendering and virtual scrolling
 *
 * Responsibilities:
 * - Generate HTML for data tables
 * - Render editable and non-editable tables
 * - Virtual scrolling for large datasets (true virtualization)
 * - Dynamic column width management
 *
 * Virtual scrolling approach:
 * - Uses a scrollable container with a tall "spacer" element
 * - Only renders rows visible in viewport + buffer
 * - Positions rendered rows absolutely within the spacer
 * - Updates visible rows on scroll via requestAnimationFrame
 *
 * Helpers:
 * - TableVirtualScroll.ts  - scroll event handling + row body updates
 * - TableColumnTruncation.ts - smart column width adjustment
 */

import { Dataset, DataRow, TABLE_CONSTANTS } from "./types";
import {
  setupVirtualScrolling as doSetupVirtualScrolling,
  updateVisibleRange as doUpdateVisibleRange,
  updateTableBody as doUpdateTableBody,
  VirtualScrollCallbacks,
} from "./_TableVirtualScroll";
import { setupSmartColumnTruncation as doSetupSmartColumnTruncation } from "./_TableColumnTruncation";

export class TableRendering {
  // Table dimensions
  private readonly ROW_HEIGHT: number = TABLE_CONSTANTS.ROW_HEIGHT;
  private readonly COL_WIDTH: number = TABLE_CONSTANTS.COL_WIDTH;

  // Virtual scrolling state
  private virtualScrollEnabled: boolean = true;
  private visibleRowStart: number = 0;
  private visibleRowEnd: number = 50; // Initial visible rows
  private visibleColStart: number = 0;
  private visibleColEnd: number = 32; // Show all 32 columns initially
  private readonly BUFFER_ROWS: number = 10; // Extra rows to render above/below viewport
  private scrollRAFId: number | null = null; // For requestAnimationFrame debouncing
  private lastScrollTop: number = 0;

  // Column width management
  private columnWidths: Map<number, number> = new Map();

  // Display options
  private firstColIsIndex: boolean = false;

  // Container element
  private containerSelector: string = ".data-table-container";

  // Scroll handler reference for cleanup
  private boundScrollHandler: (() => void) | null = null;

  // Resize observer for smart column truncation
  private resizeObserver: ResizeObserver | null = null;

  constructor(
    private getCurrentData: () => Dataset | null,
    private statusBarCallback?: (message: string) => void,
    private updateRulersAreaTransformCallback?: () => void,
  ) {}

  /**
   * Set container selector
   */
  public setContainerSelector(selector: string): void {
    this.containerSelector = selector;
  }

  /**
   * Get virtual scrolling state
   */
  public getVirtualScrollState(): {
    enabled: boolean;
    visibleRowStart: number;
    visibleRowEnd: number;
  } {
    return {
      enabled: this.virtualScrollEnabled,
      visibleRowStart: this.visibleRowStart,
      visibleRowEnd: this.visibleRowEnd,
    };
  }

  /**
   * Set virtual scrolling state
   */
  public setVirtualScrollState(
    enabled: boolean,
    rowStart: number,
    rowEnd: number,
  ): void {
    this.virtualScrollEnabled = enabled;
    this.visibleRowStart = rowStart;
    this.visibleRowEnd = rowEnd;
  }

  /**
   * Get column width
   */
  public getColumnWidth(colIndex: number): number {
    return this.columnWidths.get(colIndex) || this.COL_WIDTH;
  }

  /**
   * Set column width
   */
  public setColumnWidth(colIndex: number, width: number): void {
    this.columnWidths.set(colIndex, width);
  }

  /**
   * Get column widths map
   */
  public getColumnWidths(): Map<number, number> {
    return this.columnWidths;
  }

  /**
   * Render data table (non-editable view)
   */
  public renderDataTable(): void {
    const currentData = this.getCurrentData();
    if (!currentData) return;

    const dataContainer = document.querySelector(this.containerSelector);
    if (dataContainer) {
      dataContainer.innerHTML = this.generateTableHTML(currentData, "main");
    }
  }

  /**
   * Render editable data table with true virtual scrolling
   * Only renders rows visible in viewport + buffer for performance
   */
  public renderEditableDataTable(): string {
    const renderStart = performance.now();

    const currentData = this.getCurrentData();
    if (!currentData) return "";

    const totalRows = currentData.rows.length;
    const totalHeight = totalRows * this.ROW_HEIGHT;

    // Calculate initial visible range
    const dataContainer = document.querySelector(
      this.containerSelector,
    ) as HTMLElement;
    if (dataContainer && this.virtualScrollEnabled) {
      const containerHeight = Math.max(dataContainer.clientHeight || 400, 300);
      const visibleRowCount = Math.ceil(containerHeight / this.ROW_HEIGHT);
      this.visibleRowEnd = Math.min(
        visibleRowCount + this.BUFFER_ROWS,
        totalRows,
      );
    }

    // Determine which rows to render
    const startRow = this.virtualScrollEnabled ? this.visibleRowStart : 0;
    const endRow = this.virtualScrollEnabled
      ? Math.min(this.visibleRowEnd, totalRows)
      : totalRows;

    // Generate dynamic CSS for column widths
    let dynamicCSS = '<style id="data-table-dynamic-widths">';
    currentData.columns.forEach((col, colIndex) => {
      const columnWidth = this.columnWidths.get(colIndex) || this.COL_WIDTH;
      dynamicCSS += `
                .data-table th[data-col="${colIndex}"],
                .data-table td[data-col="${colIndex}"] {
                    width: ${columnWidth}px;
                    min-width: ${columnWidth}px;
                }
            `;
    });
    // Add virtual scroll row positioning
    if (this.virtualScrollEnabled) {
      dynamicCSS += `
                .virtual-scroll-wrapper {
                    position: relative;
                    height: ${totalHeight}px;
                    overflow: visible;
                }
                .data-table.editable-table tbody {
                    position: relative;
                }
                .data-table.editable-table tbody tr {
                    height: ${this.ROW_HEIGHT}px;
                }
            `;
    }
    dynamicCSS += "</style>";

    // Build table HTML
    let html = '<table class="data-table editable-table">';

    // Header row
    html += "<thead><tr>";
    html += `<th class="row-number-header"></th>`;
    currentData.columns.forEach((col, colIndex) => {
      const isIndexCol = this.firstColIsIndex && colIndex === 0;
      const colName = isIndexCol ? "None" : col;
      html += `<th data-col="${colIndex}" tabindex="0" title="${colName}"><span class="col-header-text">${colName}</span><div class="column-resize-handle" data-col="${colIndex}"></div></th>`;
    });
    html += "</tr></thead>";

    // Data rows - only render visible range
    html += "<tbody>";
    for (let rowIndex = startRow; rowIndex < endRow; rowIndex++) {
      const row = currentData.rows[rowIndex];
      const rowClass = rowIndex % 2 === 0 ? "row-even" : "row-odd";
      html += `<tr class="${rowClass}" data-row-index="${rowIndex}">`;
      html += `<td class="row-number">${rowIndex + 1}</td>`;
      currentData.columns.forEach((col, colIndex) => {
        const value = row[col] ?? "";
        const isIndexCol = this.firstColIsIndex && colIndex === 0;
        const cellClass = isIndexCol ? "index-col" : "data-cell";
        const escapedValue = String(value).replace(/"/g, "&quot;");
        html += `<td data-row="${rowIndex}" data-col="${colIndex}" tabindex="0" class="${cellClass}" title="${escapedValue}"><span class="cell-text">${value}</span></td>`;
      });
      html += "</tr>";
    }
    html += "</tbody></table>";

    // Wrap in virtual scroll container if enabled
    let finalHTML: string;
    if (this.virtualScrollEnabled && totalRows > 100) {
      const topSpacerHeight = startRow * this.ROW_HEIGHT;
      const bottomSpacerHeight = Math.max(
        0,
        (totalRows - endRow) * this.ROW_HEIGHT,
      );
      // Spacer heights are dynamic - add to CSS block (approved pattern)
      dynamicCSS = dynamicCSS.replace(
        "</style>",
        `.virtual-scroll-top-spacer { height: ${topSpacerHeight}px; }
        .virtual-scroll-bottom-spacer { height: ${bottomSpacerHeight}px; }
        </style>`,
      );
      finalHTML =
        dynamicCSS +
        `<div class="virtual-scroll-container">
          <div class="virtual-scroll-top-spacer"></div>
          ${html}
          <div class="virtual-scroll-bottom-spacer"></div>
        </div>`;
    } else {
      finalHTML = dynamicCSS + html;
    }

    const totalTime = performance.now();
    console.log(
      `[TableRendering] Rendered ${endRow - startRow} of ${totalRows} rows in ${(totalTime - renderStart).toFixed(2)}ms`,
    );

    // Insert HTML into DOM
    if (dataContainer) {
      dataContainer.innerHTML = finalHTML;
      const emptyState = document.getElementById("data-empty-state");
      if (emptyState) {
        emptyState.style.display = "none";
      }

      // Apply smart column truncation after DOM update
      requestAnimationFrame(() => {
        this.setupSmartColumnTruncation();
      });
    }

    return finalHTML;
  }

  /**
   * Generate HTML table (for non-editable views).
   * Uses CSS classes (no inline styles) to satisfy linting rules.
   * The tableType class ("mini-table" or "data-table") controls font-size via CSS.
   * Row alternation uses "row-even" / "row-odd" classes (same as editable table).
   */
  public generateTableHTML(data: Dataset, tableType: string): string {
    const tableClass = tableType === "mini" ? "mini-table" : "data-table";
    let html = `<table class="${tableClass}">`;

    // Headers - styled via .data-table thead / .mini-table thead in CSS
    html += "<thead><tr>";
    data.columns.forEach((col) => {
      html += `<th class="preview-th" title="${col}">${col}</th>`;
    });
    html += "</tr></thead>";

    // Rows - styled via .data-table td / .mini-table td in CSS
    html += "<tbody>";
    data.rows.forEach((row, index) => {
      const rowClass = index % 2 === 0 ? "row-even" : "row-odd";
      html += `<tr class="${rowClass}">`;
      data.columns.forEach((col) => {
        const value = row[col];
        const displayValue =
          typeof value === "number" ? value.toFixed(4) : value;
        html += `<td class="preview-td">${displayValue}</td>`;
      });
      html += "</tr>";
    });
    html += "</tbody></table>";

    return html;
  }

  /**
   * Build callbacks object for virtual scroll helpers
   */
  private buildVirtualScrollCallbacks(): VirtualScrollCallbacks {
    return {
      getCurrentData: () => this.getCurrentData(),
      getContainerSelector: () => this.containerSelector,
      getVisibleRowStart: () => this.visibleRowStart,
      getVisibleRowEnd: () => this.visibleRowEnd,
      setVisibleRowStart: (v) => {
        this.visibleRowStart = v;
      },
      setVisibleRowEnd: (v) => {
        this.visibleRowEnd = v;
      },
      getRowHeight: () => this.ROW_HEIGHT,
      getBufferRows: () => this.BUFFER_ROWS,
      getFirstColIsIndex: () => this.firstColIsIndex,
    };
  }

  /**
   * Setup virtual scrolling for incremental rendering
   */
  public setupVirtualScrolling(): void {
    if (!this.virtualScrollEnabled) return;
    this.boundScrollHandler = doSetupVirtualScrolling(
      this.buildVirtualScrollCallbacks(),
      this.boundScrollHandler,
    );
  }

  /**
   * Update visible row range based on scroll position
   */
  public updateVisibleRange(): void {
    if (!this.virtualScrollEnabled) return;
    doUpdateVisibleRange(
      this.buildVirtualScrollCallbacks(),
      this.lastScrollTop,
      (v) => {
        this.lastScrollTop = v;
      },
    );
  }

  /**
   * Enable/disable virtual scrolling
   */
  public setVirtualScrollEnabled(enabled: boolean): void {
    this.virtualScrollEnabled = enabled;
    console.log(
      `[TableRendering] Virtual scrolling ${enabled ? "enabled" : "disabled"}`,
    );
  }

  /**
   * Setup smart truncation for column headers
   */
  public setupSmartColumnTruncation(): void {
    this.resizeObserver = doSetupSmartColumnTruncation(
      { getContainerSelector: () => this.containerSelector },
      this.resizeObserver,
    );
  }

  /**
   * Get visible row range
   */
  public getVisibleRowRange(): { start: number; end: number } {
    return {
      start: this.visibleRowStart,
      end: this.visibleRowEnd,
    };
  }

  /**
   * Set visible row range
   */
  public setVisibleRowRange(start: number, end: number): void {
    this.visibleRowStart = start;
    this.visibleRowEnd = end;
  }

  /**
   * Get table constants
   */
  public getTableConstants(): {
    ROW_HEIGHT: number;
    COL_WIDTH: number;
    BUFFER_ROWS: number;
  } {
    return {
      ROW_HEIGHT: this.ROW_HEIGHT,
      COL_WIDTH: this.COL_WIDTH,
      BUFFER_ROWS: this.BUFFER_ROWS,
    };
  }

  /**
   * Clear column widths (reset to default)
   */
  public clearColumnWidths(): void {
    this.columnWidths.clear();
  }

  /**
   * Set first column as index
   */
  public setFirstColIsIndex(value: boolean): void {
    this.firstColIsIndex = value;
  }

  /**
   * Get first column is index state
   */
  public getFirstColIsIndex(): boolean {
    return this.firstColIsIndex;
  }

  /**
   * Set first row as header (placeholder - data interpretation handled by TableData)
   */
  public setFirstRowIsHeader(value: boolean): void {
    console.log("[TableRendering] First row is header:", value);
  }
}
