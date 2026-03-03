/**
 * TableClipboard - Handles copy/paste operations for data table
 *
 * Responsibilities:
 * - Copy selected cells to clipboard (Excel-compatible format)
 * - Paste from clipboard (Excel/CSV-compatible)
 * - Handle cell expansion during paste
 * - Tab-separated value formatting
 */
import { TABLE_CONSTANTS } from './types.ts';
export class TableClipboard {
    constructor(getCurrentData, setCurrentData, getSelection, renderCallback, statusBarCallback) {
        this.getCurrentData = getCurrentData;
        this.setCurrentData = setCurrentData;
        this.getSelection = getSelection;
        this.renderCallback = renderCallback;
        this.statusBarCallback = statusBarCallback;
        this.maxRows = TABLE_CONSTANTS.MAX_ROWS;
        this.maxCols = TABLE_CONSTANTS.MAX_COLS;
    }
    /**
     * Handle table copy event (native browser copy)
     */
    handleTableCopy(e) {
        e.preventDefault();
        this.copySelectionToClipboard();
    }
    /**
     * Copy selected cells to clipboard (Excel-compatible format)
     */
    async copySelectionToClipboard() {
        console.log('[TableClipboard] Copy called');
        const currentData = this.getCurrentData();
        const selection = this.getSelection();
        if (!currentData || !selection.start || !selection.end) {
            console.warn('[TableClipboard] No selection to copy');
            return;
        }
        const startRow = Math.min(selection.start.row, selection.end.row);
        const endRow = Math.max(selection.start.row, selection.end.row);
        const startCol = Math.min(selection.start.col, selection.end.col);
        const endCol = Math.max(selection.start.col, selection.end.col);
        // Build tab-separated text (Excel format)
        const lines = [];
        for (let r = startRow; r <= endRow; r++) {
            const rowValues = [];
            for (let c = startCol; c <= endCol; c++) {
                if (r < currentData.rows.length && c < currentData.columns.length) {
                    const colName = currentData.columns[c];
                    const value = currentData.rows[r][colName];
                    rowValues.push(value !== undefined && value !== null ? String(value) : '');
                }
                else {
                    rowValues.push('');
                }
            }
            lines.push(rowValues.join('\t'));
        }
        const textToCopy = lines.join('\n');
        try {
            await navigator.clipboard.writeText(textToCopy);
            const rowCount = endRow - startRow + 1;
            const colCount = endCol - startCol + 1;
            if (this.statusBarCallback) {
                this.statusBarCallback(`Copied ${rowCount} row${rowCount > 1 ? 's' : ''} × ${colCount} column${colCount > 1 ? 's' : ''}`);
            }
            console.log('[TableClipboard] Successfully copied to clipboard');
        }
        catch (error) {
            console.error('[TableClipboard] Failed to copy to clipboard:', error);
            if (this.statusBarCallback) {
                this.statusBarCallback('Copy failed - clipboard access denied');
            }
        }
    }
    /**
     * Handle paste from Excel/clipboard
     */
    handleTablePaste(e) {
        e.preventDefault();
        const pasteData = e.clipboardData?.getData('text');
        if (!pasteData)
            return;
        console.log('[TableClipboard] Paste detected');
        // Parse tab-separated or newline-separated values
        const lines = pasteData.trim().split('\n');
        const rows = lines.map(line => {
            if (line.includes('\t')) {
                return line.split('\t');
            }
            else if (line.split(',').length > 1) {
                return line.split(',');
            }
            else {
                return [line];
            }
        });
        if (rows.length === 0)
            return;
        const selection = this.getSelection();
        // If we have a selected cell, paste starting from that cell
        if (selection.selectedCell) {
            this.pasteToCells(rows);
            return;
        }
        // Otherwise, paste to first data cell (row 0, col 0)
        const firstCell = document.querySelector('td[data-row="0"][data-col="0"]');
        if (firstCell) {
            // Note: This will be handled by the main manager's selection state
            this.pasteToCells(rows);
            return;
        }
        // Otherwise, replace entire table
        this.pasteAsNewTable(rows);
    }
    /**
     * Paste data to cells starting from selected cell
     */
    pasteToCells(rows) {
        const selection = this.getSelection();
        const currentData = this.getCurrentData();
        if (!selection.selectedCell || !currentData)
            return;
        const startRow = parseInt(selection.selectedCell.getAttribute('data-row') || '0');
        const startCol = parseInt(selection.selectedCell.getAttribute('data-col') || '0');
        const neededRows = startRow + rows.length;
        const neededCols = startCol + (rows[0]?.length || 0);
        // Expand columns if needed (up to max)
        while (currentData.columns.length < neededCols && currentData.columns.length < this.maxCols) {
            const newColIndex = currentData.columns.length;
            const newColName = this.getColumnLabel(newColIndex);
            currentData.columns.push(newColName);
            // Add empty cells to existing rows
            currentData.rows.forEach(row => {
                row[newColName] = '';
            });
        }
        // Expand rows if needed (up to max)
        while (currentData.rows.length < neededRows && currentData.rows.length < this.maxRows) {
            const newRow = {};
            currentData.columns.forEach(col => {
                newRow[col] = '';
            });
            currentData.rows.push(newRow);
        }
        // Paste data cell by cell
        for (let r = 0; r < rows.length; r++) {
            const targetRow = startRow + r;
            if (targetRow >= currentData.rows.length)
                break;
            for (let c = 0; c < rows[r].length; c++) {
                const targetCol = startCol + c;
                if (targetCol >= currentData.columns.length)
                    break;
                const colName = currentData.columns[targetCol];
                const value = rows[r][c]?.trim() || '';
                const numValue = parseFloat(value);
                currentData.rows[targetRow][colName] = isNaN(numValue) || value === '' ? value : numValue;
            }
        }
        this.setCurrentData(currentData);
        this.renderCallback();
        if (this.statusBarCallback) {
            this.statusBarCallback(`Pasted ${rows.length} rows × ${rows[0].length} columns (Table expanded to ${currentData.rows.length} × ${currentData.columns.length})`);
        }
        console.log('[TableClipboard] Cell paste completed with expansion');
    }
    /**
     * Paste as new table (replace entire table)
     */
    pasteAsNewTable(rows) {
        const hasHeaders = false;
        const startRow = hasHeaders ? 1 : 0;
        const columns = hasHeaders
            ? rows[0].slice(0, this.maxCols)
            : rows[0].slice(0, this.maxCols).map((_, i) => this.getColumnLabel(i));
        const maxDataRows = Math.min(rows.length - startRow, this.maxRows);
        const dataRows = [];
        for (let i = startRow; i < startRow + maxDataRows; i++) {
            if (i >= rows.length)
                break;
            const row = {};
            columns.forEach((col, colIndex) => {
                const value = rows[i][colIndex]?.trim() || '';
                const numValue = parseFloat(value);
                row[col] = isNaN(numValue) || value === '' ? value : numValue;
            });
            dataRows.push(row);
        }
        this.setCurrentData({ columns, rows: dataRows });
        this.renderCallback();
        const truncatedMsg = (rows.length - startRow > this.maxRows || rows[0].length > this.maxCols)
            ? ' (truncated to fit limits)'
            : '';
        if (this.statusBarCallback) {
            this.statusBarCallback(`Pasted ${dataRows.length} rows × ${columns.length} columns${truncatedMsg}`);
        }
        console.log('[TableClipboard] Data pasted as new table');
    }
    /**
     * Get column label (1, 2, 3, ...)
     */
    getColumnLabel(index) {
        return `${index + 1}`;
    }
}
//# sourceMappingURL=TableClipboard.ts.map
