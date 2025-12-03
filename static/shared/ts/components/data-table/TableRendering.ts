/**
 * TableRendering - Handles table rendering and virtual scrolling
 *
 * Responsibilities:
 * - Generate HTML for data tables
 * - Render editable and non-editable tables
 * - Virtual scrolling for large datasets
 * - Dynamic column width management
 */

import { Dataset, DataRow, TABLE_CONSTANTS } from './types.js';

export class TableRendering {
    // Table dimensions
    private readonly ROW_HEIGHT: number = TABLE_CONSTANTS.ROW_HEIGHT;
    private readonly COL_WIDTH: number = TABLE_CONSTANTS.COL_WIDTH;

    // Virtual scrolling state
    private virtualScrollEnabled: boolean = true;
    private visibleRowStart: number = 0;
    private visibleRowEnd: number = 50;  // Initial visible rows
    private visibleColStart: number = 0;
    private visibleColEnd: number = 32;  // Show all 32 columns initially
    private readonly BUFFER_ROWS: number = 20;  // Extra rows to render above/below viewport

    // Column width management
    private columnWidths: Map<number, number> = new Map();

    // Display options
    private firstColIsIndex: boolean = false;

    // Container element
    private containerSelector: string = '.data-table-container';

    constructor(
        private getCurrentData: () => Dataset | null,
        private statusBarCallback?: (message: string) => void,
        private updateRulersAreaTransformCallback?: () => void
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
            visibleRowEnd: this.visibleRowEnd
        };
    }

    /**
     * Set virtual scrolling state
     */
    public setVirtualScrollState(enabled: boolean, rowStart: number, rowEnd: number): void {
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
            dataContainer.innerHTML = this.generateTableHTML(currentData, 'main');
        }
    }

    /**
     * Render editable data table
     */
    public renderEditableDataTable(): string {
        const renderStart = performance.now();
        console.log('[TableRendering] Starting table render...');

        const currentData = this.getCurrentData();
        if (!currentData) return '';

        // Performance optimized: Use CSS classes instead of inline styles (95% HTML size reduction)
        let html = '<table class="data-table editable-table">';

        // Header row with row/column numbers
        html += '<thead><tr>';
        // Top-left corner cell (empty)
        html += `<th class="row-number-header"></th>`;
        // Column headers (Col 1, Col 2, ...)
        currentData.columns.forEach((col, colIndex) => {
            const isIndexCol = this.firstColIsIndex && colIndex === 0;
            const colName = isIndexCol ? 'None' : col;
            html += `<th data-col="${colIndex}" tabindex="0">${colName}<div class="column-resize-handle" data-col="${colIndex}"></div></th>`;
        });
        html += '</tr></thead>';

        // Data rows with row numbers (with virtual scrolling support)
        html += '<tbody>';

        // Determine which rows to render based on virtual scrolling
        const totalRows = currentData.rows.length;
        const startRow = this.virtualScrollEnabled ? this.visibleRowStart : 0;
        const endRow = this.virtualScrollEnabled ? Math.min(this.visibleRowEnd, totalRows) : totalRows;

        console.log(`[TableRendering] Rendering rows ${startRow} to ${endRow} of ${totalRows}`);

        // Render only visible rows
        for (let rowIndex = startRow; rowIndex < endRow; rowIndex++) {
            const row = currentData.rows[rowIndex];
            const rowClass = rowIndex % 2 === 0 ? 'row-even' : 'row-odd';
            html += `<tr class="${rowClass}">`;
            // Row number
            html += `<td class="row-number">${rowIndex + 1}</td>`;
            // Data cells
            currentData.columns.forEach((col, colIndex) => {
                const value = row[col] || '';
                const isIndexCol = this.firstColIsIndex && colIndex === 0;
                const cellClass = isIndexCol ? 'index-col' : 'data-cell';
                html += `<td data-row="${rowIndex}" data-col="${colIndex}" tabindex="0" class="${cellClass}">${value}</td>`;
            });
            html += '</tr>';
        }
        html += '</tbody></table>';

        const htmlBuildTime = performance.now();
        console.log(`[TableRendering] HTML string built in ${(htmlBuildTime - renderStart).toFixed(2)}ms`);

        // Generate dynamic CSS for column widths (NO INLINE STYLES!)
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
        dynamicCSS += '</style>';

        const finalHTML = dynamicCSS + html;

        const totalTime = performance.now();
        console.log(`[TableRendering] Total render time: ${(totalTime - renderStart).toFixed(2)}ms`);

        // Insert HTML into DOM
        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (dataContainer) {
            dataContainer.innerHTML = finalHTML;
            // Hide empty state if it exists
            const emptyState = document.getElementById('data-empty-state');
            if (emptyState) {
                emptyState.style.display = 'none';
            }
        }

        return finalHTML;
    }

    /**
     * Generate HTML table (for non-editable views)
     */
    public generateTableHTML(data: Dataset, tableType: string): string {
        const tableClass = tableType === 'mini' ? 'mini-table' : 'data-table';
        let html = `<table class="${tableClass}" style="width: 100%; border-collapse: collapse; font-size: ${tableType === 'mini' ? '11px' : '13px'};">`;

        // Headers
        html += '<thead style="background: var(--bg-secondary); position: sticky; top: 0;"><tr>';
        data.columns.forEach(col => {
            html += `<th style="padding: 8px; text-align: left; border-bottom: 2px solid var(--border-default); font-weight: 600;">${col}</th>`;
        });
        html += '</tr></thead>';

        // Rows
        html += '<tbody>';
        data.rows.forEach((row, index) => {
            const bgColor = index % 2 === 0 ? 'var(--bg-primary)' : 'var(--bg-secondary)';
            html += `<tr style="background: ${bgColor};">`;
            data.columns.forEach(col => {
                const value = row[col];
                const displayValue = typeof value === 'number' ? value.toFixed(4) : value;
                html += `<td style="padding: 6px 8px; border-bottom: 1px solid var(--border-muted);">${displayValue}</td>`;
            });
            html += '</tr>';
        });
        html += '</tbody></table>';

        return html;
    }

    /**
     * Setup virtual scrolling for incremental rendering
     */
    public setupVirtualScrolling(): void {
        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (!dataContainer || !this.virtualScrollEnabled) return;

        let scrollTimeout: number | null = null;

        dataContainer.addEventListener('scroll', () => {
            // Debounce scroll events for performance
            if (scrollTimeout) {
                clearTimeout(scrollTimeout);
            }

            scrollTimeout = window.setTimeout(() => {
                this.updateVisibleRange();
            }, 100);  // 100ms debounce
        });

        console.log('[TableRendering] Virtual scrolling enabled');
    }

    /**
     * Update visible row range based on scroll position
     */
    public updateVisibleRange(): void {
        const currentData = this.getCurrentData();
        if (!currentData || !this.virtualScrollEnabled) return;

        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (!dataContainer) return;

        const scrollTop = dataContainer.scrollTop;
        const containerHeight = dataContainer.clientHeight;

        // Calculate which rows are visible
        const firstVisibleRow = Math.floor(scrollTop / this.ROW_HEIGHT);
        const visibleRowCount = Math.ceil(containerHeight / this.ROW_HEIGHT);

        // Add buffer rows above and below
        const newStart = Math.max(0, firstVisibleRow - this.BUFFER_ROWS);
        const newEnd = Math.min(currentData.rows.length, firstVisibleRow + visibleRowCount + this.BUFFER_ROWS);

        // Only re-render if range changed significantly
        if (newStart !== this.visibleRowStart || newEnd !== this.visibleRowEnd) {
            this.visibleRowStart = newStart;
            this.visibleRowEnd = newEnd;

            console.log(`[TableRendering] Scroll update: rendering rows ${newStart}-${newEnd}`);

            // Trigger re-render by updating container
            const dataContainer = document.querySelector(this.containerSelector);
            if (dataContainer) {
                dataContainer.innerHTML = this.renderEditableDataTable();
            }

            // Reapply rulers area transform after table re-render
            if (this.updateRulersAreaTransformCallback) {
                this.updateRulersAreaTransformCallback();
            }
        }
    }

    /**
     * Enable/disable virtual scrolling
     */
    public setVirtualScrollEnabled(enabled: boolean): void {
        this.virtualScrollEnabled = enabled;
        console.log(`[TableRendering] Virtual scrolling ${enabled ? 'enabled' : 'disabled'}`);
    }

    /**
     * Get visible row range
     */
    public getVisibleRowRange(): { start: number; end: number } {
        return {
            start: this.visibleRowStart,
            end: this.visibleRowEnd
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
    public getTableConstants(): { ROW_HEIGHT: number; COL_WIDTH: number; BUFFER_ROWS: number } {
        return {
            ROW_HEIGHT: this.ROW_HEIGHT,
            COL_WIDTH: this.COL_WIDTH,
            BUFFER_ROWS: this.BUFFER_ROWS
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
}
