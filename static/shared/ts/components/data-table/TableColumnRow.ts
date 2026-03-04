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
import { TABLE_CONSTANTS } from './types.ts';
export class TableColumnRow {
    constructor(getCurrentData, setCurrentData, renderCallback, statusBarCallback) {
        this.getCurrentData = getCurrentData;
        this.setCurrentData = setCurrentData;
        this.renderCallback = renderCallback;
        this.statusBarCallback = statusBarCallback;
        // Table dimensions
        this.ROW_HEIGHT = TABLE_CONSTANTS.ROW_HEIGHT;
        this.COL_WIDTH = TABLE_CONSTANTS.COL_WIDTH;
        this.maxRows = TABLE_CONSTANTS.MAX_ROWS;
        this.maxCols = TABLE_CONSTANTS.MAX_COLS;
        // Column resizing state
        this.columnWidths = new Map();
        this.isResizingColumn = false;
        this.resizingColumnIndex = -1;
        this.resizeStartX = 0;
        this.resizeStartWidth = 0;
        // Container selector
        this.containerSelector = '.data-table-container';
    }
    /**
     * Set container selector
     */
    setContainerSelector(selector) {
        this.containerSelector = selector;
    }
    /**
     * Get column widths map
     */
    getColumnWidths() {
        return this.columnWidths;
    }
    /**
     * Get column width
     */
    getColumnWidth(colIndex) {
        return this.columnWidths.get(colIndex) || this.COL_WIDTH;
    }
    /**
     * Setup column resizing functionality (Excel-like column border dragging)
     */
    setupColumnResizing() {
        const dataContainer = document.querySelector(this.containerSelector);
        if (!dataContainer)
            return;
        // Use event delegation for resize handles (since table is re-rendered)
        dataContainer.addEventListener('mousedown', (e) => {
            const target = e.target;
            if (!target.classList.contains('column-resize-handle'))
                return;
            const colIndex = parseInt(target.getAttribute('data-col') || '-1');
            if (colIndex === -1)
                return;
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
        document.addEventListener('mousemove', (e) => {
            if (!this.isResizingColumn)
                return;
            e.preventDefault();
            e.stopPropagation();
            const deltaX = e.clientX - this.resizeStartX;
            const newWidth = Math.max(30, this.resizeStartWidth + deltaX); // Minimum 30px
            // Update the stored width
            this.columnWidths.set(this.resizingColumnIndex, newWidth);
            // Apply width to all cells in this column
            const table = dataContainer.querySelector('.data-table');
            if (table) {
                // Update header
                const header = table.querySelector(`th[data-col="${this.resizingColumnIndex}"]`);
                if (header) {
                    header.style.minWidth = `${newWidth}px`;
                    header.style.width = `${newWidth}px`;
                }
                // Update all data cells in this column
                const cells = table.querySelectorAll(`td[data-col="${this.resizingColumnIndex}"]`);
                cells.forEach((cell) => {
                    const td = cell;
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
    addColumns(count) {
        const currentData = this.getCurrentData?.();
        if (!currentData)
            return;
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
    addRows(count) {
        const currentData = this.getCurrentData?.();
        if (!currentData)
            return;
        const currentRowCount = currentData.rows.length;
        const newRowCount = Math.min(currentRowCount + count, this.maxRows);
        for (let i = currentRowCount; i < newRowCount; i++) {
            const newRow = {};
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
    getColumnLabel(index) {
        return `${index + 1}`;
    }
    /**
     * Get cell element at specific position
     */
    getCellAt(row, col) {
        const container = document.querySelector(this.containerSelector);
        if (!container)
            return null;
        // Try td first (data cells)
        let cell = container.querySelector(`td[data-row="${row}"][data-col="${col}"]`);
        // If not found and row is -1, try th (header cells)
        if (!cell && row === -1) {
            cell = container.querySelector(`th[data-col="${col}"]`);
        }
        return cell;
    }
    /**
     * Resize table to match current selection (Ctrl+drag)
     */
    resizeTableToSelection(selectionStart, selectionEnd, updateSelectionCallback, updateRulersAreaTransformCallback) {
        const currentData = this.getCurrentData?.();
        if (!selectionStart || !selectionEnd || !currentData)
            return;
        const endRow = Math.max(selectionStart.row, selectionEnd.row);
        const endCol = Math.max(selectionStart.col, selectionEnd.col);
        const currentRowCount = currentData.rows.length;
        const currentColCount = currentData.columns.length;
        const needRows = endRow + 1; // +1 because rows are 0-indexed
        const needCols = endCol + 1; // +1 because cols are 0-indexed
        let changed = false;
        // Add rows if needed
        if (needRows > currentRowCount) {
            const rowsToAdd = needRows - currentRowCount;
            for (let i = 0; i < rowsToAdd; i++) {
                const row = {};
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
//# sourceMappingURL=TableColumnRow.ts.map
