/**
 * TableColumnRow - Handles column and row operations for data tables
 *
 * Responsibilities:
 * - Column resizing (Excel-like border dragging)
 * - Add columns and rows
 * - Generate column labels
 * - Cell access utilities
 * - Table dimension management
 */

import { Dataset, DataRow, TABLE_CONSTANTS } from './types';

export class TableColumnRow {
    // Table dimensions
    private readonly ROW_HEIGHT: number = TABLE_CONSTANTS.ROW_HEIGHT;
    private readonly COL_WIDTH: number = TABLE_CONSTANTS.COL_WIDTH;
    private maxRows: number = TABLE_CONSTANTS.MAX_ROWS;
    private maxCols: number = TABLE_CONSTANTS.MAX_COLS;

    // Column resizing state
    private columnWidths: Map<number, number> = new Map();
    private isResizingColumn: boolean = false;
    private resizingColumnIndex: number = -1;
    private resizeStartX: number = 0;
    private resizeStartWidth: number = 0;

    // Container selector
    private containerSelector: string = '.data-table-container';

    constructor(
        private getCurrentData?: () => Dataset | null,
        private setCurrentData?: (data: Dataset | null) => void,
        private renderCallback?: () => void,
        private statusBarCallback?: (message: string) => void
    ) {}

    /**
     * Set container selector
     */
    public setContainerSelector(selector: string): void {
        this.containerSelector = selector;
    }

    /**
     * Get column widths map
     */
    public getColumnWidths(): Map<number, number> {
        return this.columnWidths;
    }

    /**
     * Get column width
     */
    public getColumnWidth(colIndex: number): number {
        return this.columnWidths.get(colIndex) || this.COL_WIDTH;
    }

    /**
     * Setup column resizing functionality (Excel-like column border dragging)
     */
    public setupColumnResizing(): void {
        const dataContainer = document.querySelector(this.containerSelector) as HTMLElement;
        if (!dataContainer) return;

        // Use event delegation for resize handles (since table is re-rendered)
        dataContainer.addEventListener('mousedown', (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            if (!target.classList.contains('column-resize-handle')) return;

            const colIndex = parseInt(target.getAttribute('data-col') || '-1');
            if (colIndex === -1) return;

            // CRITICAL: Prevent event propagation to avoid triggering page resizers
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();

            this.isResizingColumn = true;
            this.resizingColumnIndex = colIndex;
            this.resizeStartX = e.clientX;
            this.resizeStartWidth = this.columnWidths.get(colIndex) || this.COL_WIDTH;

            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            console.log(`[TableColumnRow] Started resizing column ${colIndex}, initial width: ${this.resizeStartWidth}px`);
        }, true); // Use capture phase to intercept before other handlers

        document.addEventListener('mousemove', (e: MouseEvent) => {
            if (!this.isResizingColumn) return;

            e.preventDefault();
            e.stopPropagation();

            const deltaX = e.clientX - this.resizeStartX;
            const newWidth = Math.max(30, this.resizeStartWidth + deltaX); // Minimum 30px

            // Update the stored width
            this.columnWidths.set(this.resizingColumnIndex, newWidth);

            // Apply width to all cells in this column
            const table = dataContainer.querySelector('.data-table') as HTMLTableElement;
            if (table) {
                // Update header
                const header = table.querySelector(`th[data-col="${this.resizingColumnIndex}"]`) as HTMLElement;
                if (header) {
                    header.style.minWidth = `${newWidth}px`;
                    header.style.width = `${newWidth}px`;
                }

                // Update all data cells in this column
                const cells = table.querySelectorAll(`td[data-col="${this.resizingColumnIndex}"]`);
                cells.forEach((cell: Element) => {
                    const td = cell as HTMLElement;
                    td.style.minWidth = `${newWidth}px`;
                    td.style.width = `${newWidth}px`;
                });
            }
        }, true); // Use capture phase

        document.addEventListener('mouseup', () => {
            if (this.isResizingColumn) {
                console.log(`[TableColumnRow] Finished resizing column ${this.resizingColumnIndex}, final width: ${this.columnWidths.get(this.resizingColumnIndex)}px`);

                this.isResizingColumn = false;
                this.resizingColumnIndex = -1;

                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        }, true); // Use capture phase

        console.log('[TableColumnRow] Column resizing initialized');
    }

    /**
     * Add columns to the table
     */
    public addColumns(count: number): void {
        const currentData = this.getCurrentData?.();
        if (!currentData) return;

        const currentColCount = currentData.columns.length;
        const newColCount = Math.min(currentColCount + count, this.maxCols);

        for (let i = currentColCount; i < newColCount; i++) {
            const newColName = this.getColumnLabel(i);
            currentData.columns.push(newColName);
            // Add empty cells to existing rows
            currentData.rows.forEach(row => {
                row[newColName] = '';
            });
        }

        if (this.setCurrentData) {
            this.setCurrentData(currentData);
        }

        if (this.renderCallback) {
            this.renderCallback();
        }

        if (this.statusBarCallback) {
            this.statusBarCallback(`Added ${newColCount - currentColCount} columns (Total: ${currentData.rows.length} rows × ${currentData.columns.length} columns)`);
        }

        console.log(`[TableColumnRow] Columns added. Total: ${currentData.columns.length}`);
    }

    /**
     * Add rows to the table
     */
    public addRows(count: number): void {
        const currentData = this.getCurrentData?.();
        if (!currentData) return;

        const currentRowCount = currentData.rows.length;
        const newRowCount = Math.min(currentRowCount + count, this.maxRows);

        for (let i = currentRowCount; i < newRowCount; i++) {
            const newRow: DataRow = {};
            currentData.columns.forEach(col => {
                newRow[col] = '';
            });
            currentData.rows.push(newRow);
        }

        if (this.setCurrentData) {
            this.setCurrentData(currentData);
        }

        if (this.renderCallback) {
            this.renderCallback();
        }

        if (this.statusBarCallback) {
            this.statusBarCallback(`Added ${newRowCount - currentRowCount} rows (Total: ${currentData.rows.length} rows × ${currentData.columns.length} columns)`);
        }

        console.log(`[TableColumnRow] Rows added. Total: ${currentData.rows.length}`);
    }

    /**
     * Get column label (1, 2, 3, ...)
     */
    public getColumnLabel(index: number): string {
        return `${index + 1}`;
    }

    /**
     * Get cell element at specific position
     */
    public getCellAt(row: number, col: number): HTMLElement | null {
        const container = document.querySelector(this.containerSelector);
        if (!container) return null;

        // Try td first (data cells)
        let cell = container.querySelector(`td[data-row="${row}"][data-col="${col}"]`);
        // If not found and row is -1, try th (header cells)
        if (!cell && row === -1) {
            cell = container.querySelector(`th[data-col="${col}"]`);
        }
        return cell as HTMLElement | null;
    }

    /**
     * Resize table to match current selection (Ctrl+drag)
     */
    public resizeTableToSelection(
        selectionStart: { row: number, col: number } | null,
        selectionEnd: { row: number, col: number } | null,
        updateSelectionCallback?: () => void,
        updateRulersAreaTransformCallback?: () => void
    ): void {
        const currentData = this.getCurrentData?.();
        if (!selectionStart || !selectionEnd || !currentData) return;

        const endRow = Math.max(selectionStart.row, selectionEnd.row);
        const endCol = Math.max(selectionStart.col, selectionEnd.col);

        const currentRowCount = currentData.rows.length;
        const currentColCount = currentData.columns.length;

        const needRows = endRow + 1;  // +1 because rows are 0-indexed
        const needCols = endCol + 1;  // +1 because cols are 0-indexed

        let changed = false;

        // Add rows if needed
        if (needRows > currentRowCount) {
            const rowsToAdd = needRows - currentRowCount;
            for (let i = 0; i < rowsToAdd; i++) {
                const row: DataRow = {};
                currentData.columns.forEach(col => {
                    row[col] = '';
                });
                currentData.rows.push(row);
            }
            changed = true;
        }

        // Add columns if needed
        if (needCols > currentColCount) {
            const colsToAdd = needCols - currentColCount;
            for (let i = 0; i < colsToAdd; i++) {
                const newColLabel = this.getColumnLabel(currentColCount + i);
                currentData.columns.push(newColLabel);
                // Add empty value to all rows for new column
                currentData.rows.forEach(row => {
                    row[newColLabel] = '';
                });
            }
            changed = true;
        }

        // Re-render table if changed
        if (changed) {
            if (this.setCurrentData) {
                this.setCurrentData(currentData);
            }

            if (this.renderCallback) {
                this.renderCallback();
            }

            // Restore selection state after re-render
            if (updateSelectionCallback) {
                updateSelectionCallback();
            }

            // Reapply rulers area transform after table re-render
            if (updateRulersAreaTransformCallback) {
                updateRulersAreaTransformCallback();
            }

            const rowCount = currentData.rows.length;
            const colCount = currentData.columns.length;

            if (this.statusBarCallback) {
                this.statusBarCallback(`Resized - ${rowCount} rows × ${colCount} columns`);
            }
        }
    }
}
