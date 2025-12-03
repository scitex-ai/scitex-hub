/**
 * TableSelection - Handles cell, column, and row selection in data tables
 *
 * Responsibilities:
 * - Single cell selection
 * - Range selection (drag to select)
 * - Column selection (click column header, drag to select multiple)
 * - Row selection (click row number, drag to select multiple)
 * - Visual selection updates (highlighting, borders)
 * - Selection state management
 */

import { DataRow, TABLE_CONSTANTS } from './types.js';

export class TableSelection {
    // Selection state
    private selectedCell: HTMLElement | null = null;
    private selectionStart: { row: number, col: number } | null = null;
    private selectionEnd: { row: number, col: number } | null = null;
    private isSelecting: boolean = false;
    private selectedColumns: Set<number> = new Set();
    private selectedRows: Set<number> = new Set();
    private isSelectingColumns: boolean = false;
    private isSelectingRows: boolean = false;
    private columnSelectionStart: number = -1;
    private rowSelectionStart: number = -1;

    // Container selector
    private containerSelector: string = '.data-table-container';

    constructor(
        private getCellAt: (row: number, col: number) => HTMLElement | null,
        private statusBarCallback?: (message: string) => void
    ) {}

    /**
     * Set container selector
     */
    public setContainerSelector(selector: string): void {
        this.containerSelector = selector;
    }

    /**
     * Handle mouse down on cell
     */
    public handleCellMouseDown(e: MouseEvent, cell: HTMLElement): void {
        e.preventDefault();
        e.stopPropagation();  // Prevent event from bubbling to panel resizers

        const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
        const colIndex = parseInt(cell.getAttribute('data-col') || '-1');

        // Clear column/row selections when clicking on regular cells
        this.selectedColumns.clear();
        this.selectedRows.clear();

        // Start selection
        this.isSelecting = true;
        this.selectionStart = { row: rowIndex, col: colIndex };
        this.selectionEnd = { row: rowIndex, col: colIndex };
        this.selectedCell = cell;

        // Update visual selection
        this.updateSelection();

        // Focus the cell for keyboard events
        cell.focus();

        console.log(`[TableSelection] Cell selected: [${rowIndex}, ${colIndex}]`);
    }

    /**
     * Handle mouse over on cell (for drag selection)
     */
    public handleCellMouseOver(cell: HTMLElement): void {
        if (!this.isSelecting || !this.selectionStart) return;

        const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
        const colIndex = parseInt(cell.getAttribute('data-col') || '-1');

        if (rowIndex === -1 || colIndex === -1) return;

        this.selectionEnd = { row: rowIndex, col: colIndex };
        this.updateSelection();

        console.log(`[TableSelection] Selection extended to: [${rowIndex}, ${colIndex}]`);
    }

    /**
     * Handle column header mouse down (start column selection)
     */
    public handleColumnHeaderMouseDown(e: MouseEvent, header: HTMLElement): void {
        e.preventDefault();
        e.stopPropagation();  // Prevent event from bubbling to panel resizers

        const colIndex = parseInt(header.getAttribute('data-col') || '-1');
        if (colIndex === -1) return;

        // Clear previous selections
        this.selectedColumns.clear();
        this.selectedRows.clear();

        // Start column drag selection
        this.isSelectingColumns = true;
        this.columnSelectionStart = colIndex;
        this.selectedColumns.add(colIndex);

        this.updateColumnRowSelection();
        console.log('[TableSelection] Column selection started:', colIndex);
    }

    /**
     * Handle column header mouse over (during drag)
     */
    public handleColumnHeaderMouseOver(header: HTMLElement): void {
        if (!this.isSelectingColumns) return;

        const colIndex = parseInt(header.getAttribute('data-col') || '-1');
        if (colIndex === -1) return;

        // Select range from start to current
        this.selectedColumns.clear();
        const start = Math.min(this.columnSelectionStart, colIndex);
        const end = Math.max(this.columnSelectionStart, colIndex);

        for (let i = start; i <= end; i++) {
            this.selectedColumns.add(i);
        }

        this.updateColumnRowSelection();
    }

    /**
     * Handle row number mouse down (start row selection)
     */
    public handleRowNumberMouseDown(e: MouseEvent, rowElement: HTMLElement): void {
        e.preventDefault();
        e.stopPropagation();  // Prevent event from bubbling to panel resizers

        // Get row index from the parent tr
        const tr = rowElement.closest('tr');
        if (!tr) return;

        const firstCell = tr.querySelector('td[data-row]') as HTMLElement;
        if (!firstCell) return;

        const rowIndex = parseInt(firstCell.getAttribute('data-row') || '-1');
        if (rowIndex === -1) return;

        // Clear previous selections
        this.selectedColumns.clear();
        this.selectedRows.clear();

        // Start row drag selection
        this.isSelectingRows = true;
        this.rowSelectionStart = rowIndex;
        this.selectedRows.add(rowIndex);

        this.updateColumnRowSelection();
        console.log('[TableSelection] Row selection started:', rowIndex);
    }

    /**
     * Handle row number mouse over (during drag)
     */
    public handleRowNumberMouseOver(rowElement: HTMLElement): void {
        if (!this.isSelectingRows) return;

        // Get row index from the parent tr
        const tr = rowElement.closest('tr');
        if (!tr) return;

        const firstCell = tr.querySelector('td[data-row]') as HTMLElement;
        if (!firstCell) return;

        const rowIndex = parseInt(firstCell.getAttribute('data-row') || '-1');
        if (rowIndex === -1) return;

        // Select range from start to current
        this.selectedRows.clear();
        const start = Math.min(this.rowSelectionStart, rowIndex);
        const end = Math.max(this.rowSelectionStart, rowIndex);

        for (let i = start; i <= end; i++) {
            this.selectedRows.add(i);
        }

        this.updateColumnRowSelection();
    }

    /**
     * Update visual selection
     */
    public updateSelection(): void {
        if (!this.selectionStart || !this.selectionEnd) return;

        const container = document.querySelector(this.containerSelector) as HTMLElement;
        if (!container) return;

        // Clear previous selection
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('selected', 'header-highlighted'));

        // Remove previous border and fill handle
        container.querySelectorAll('.selection-border-overlay, .fill-handle').forEach(el => el.remove());

        // Calculate selection bounds
        const startRow = Math.min(this.selectionStart.row, this.selectionEnd.row);
        const endRow = Math.max(this.selectionStart.row, this.selectionEnd.row);
        const startCol = Math.min(this.selectionStart.col, this.selectionEnd.col);
        const endCol = Math.max(this.selectionStart.col, this.selectionEnd.col);

        // Apply selection
        let firstCell: HTMLElement | null = null;
        let lastCell: HTMLElement | null = null;

        for (let r = startRow; r <= endRow; r++) {
            for (let c = startCol; c <= endCol; c++) {
                const cell = this.getCellAt(r, c);
                if (cell) {
                    cell.classList.add('selected');
                    if (!firstCell) firstCell = cell;
                    lastCell = cell;
                }
            }
        }

        // Highlight corresponding row numbers and column headers (Excel-like)
        const allRowNumbers = container.querySelectorAll('.row-number');
        for (let r = startRow; r <= endRow; r++) {
            if (allRowNumbers[r]) {
                allRowNumbers[r].classList.add('header-highlighted');
            }
        }

        for (let c = startCol; c <= endCol; c++) {
            const columnHeader = container.querySelector(`th[data-col="${c}"]`);
            if (columnHeader) {
                columnHeader.classList.add('header-highlighted');
            }
        }

        // Add dashed border overlay and fill handle
        if (firstCell && lastCell) {
            const containerRect = container.getBoundingClientRect();
            const firstRect = firstCell.getBoundingClientRect();
            const lastRect = lastCell.getBoundingClientRect();

            const borderOffset = 1;

            const left = firstRect.left - containerRect.left + container.scrollLeft;
            const top = firstRect.top - containerRect.top + container.scrollTop;
            const width = lastRect.right - firstRect.left;
            const height = lastRect.bottom - firstRect.top;

            // Create dashed border overlay
            const borderOverlay = document.createElement('div');
            borderOverlay.className = 'selection-border-overlay';
            borderOverlay.style.left = (left - borderOffset) + 'px';
            borderOverlay.style.top = (top - borderOffset) + 'px';
            borderOverlay.style.width = (width + borderOffset * 2) + 'px';
            borderOverlay.style.height = (height + borderOffset * 2) + 'px';
            container.appendChild(borderOverlay);

            // Create fill handle (small square at bottom-right)
            const fillHandle = document.createElement('div');
            fillHandle.className = 'fill-handle';
            fillHandle.style.left = (left + width - 4 + borderOffset) + 'px';
            fillHandle.style.top = (top + height - 4 + borderOffset) + 'px';
            container.appendChild(fillHandle);
        }
    }

    /**
     * Update visual selection for columns/rows
     */
    private updateColumnRowSelection(): void {
        const container = document.querySelector(this.containerSelector) as HTMLElement;
        if (!container) return;

        // Clear all selections first
        const allCells = container.querySelectorAll('.data-table td, .data-table th');
        allCells.forEach(cell => cell.classList.remove('selected'));

        // Select columns
        this.selectedColumns.forEach(colIndex => {
            // Select header
            const header = container.querySelector(`th[data-col="${colIndex}"]`);
            header?.classList.add('selected');

            // Select all cells in column
            const cells = container.querySelectorAll(`td[data-col="${colIndex}"]`);
            cells.forEach(cell => cell.classList.add('selected'));
        });

        // Select rows
        this.selectedRows.forEach(rowIndex => {
            // Select row number
            const cells = container.querySelectorAll(`td[data-row="${rowIndex}"]`);
            cells.forEach(cell => cell.classList.add('selected'));
        });
    }

    /**
     * Clear cell selection
     */
    public clearSelection(): void {
        this.selectionStart = null;
        this.selectionEnd = null;
        this.selectedCell = null;
        this.selectedColumns.clear();
        this.selectedRows.clear();
        this.isSelecting = false;
        this.isSelectingColumns = false;
        this.isSelectingRows = false;
    }

    /**
     * Stop selection mode (called on mouse up)
     */
    public stopSelection(): void {
        this.isSelecting = false;
        this.isSelectingColumns = false;
        this.isSelectingRows = false;
    }

    /**
     * Get current selection bounds
     */
    public getSelectionBounds(): { startRow: number, endRow: number, startCol: number, endCol: number } | null {
        if (!this.selectionStart || !this.selectionEnd) return null;

        return {
            startRow: Math.min(this.selectionStart.row, this.selectionEnd.row),
            endRow: Math.max(this.selectionStart.row, this.selectionEnd.row),
            startCol: Math.min(this.selectionStart.col, this.selectionEnd.col),
            endCol: Math.max(this.selectionStart.col, this.selectionEnd.col)
        };
    }

    /**
     * Get selected cell
     */
    public getSelectedCell(): HTMLElement | null {
        return this.selectedCell;
    }

    /**
     * Get selection state (for external use)
     */
    public getSelectionState(): {
        start: { row: number, col: number } | null,
        end: { row: number, col: number } | null,
        selectedCell: HTMLElement | null,
        selectionStart: { row: number, col: number } | null,
        selectionEnd: { row: number, col: number } | null,
        isSelecting: boolean
    } {
        return {
            start: this.selectionStart,
            end: this.selectionEnd,
            selectedCell: this.selectedCell,
            selectionStart: this.selectionStart,
            selectionEnd: this.selectionEnd,
            isSelecting: this.isSelecting
        };
    }

    /**
     * Set selection programmatically
     */
    public setSelection(startRow: number, startCol: number, endRow: number, endCol: number): void {
        this.selectionStart = { row: startRow, col: startCol };
        this.selectionEnd = { row: endRow, col: endCol };
        this.updateSelection();
    }
}
