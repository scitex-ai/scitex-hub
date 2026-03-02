/**
 * TableFillHandle - Excel-like fill handle for drag-to-fill cells
 *
 * Responsibilities:
 * - Handle fill handle mouse down (start drag)
 * - Show fill preview during drag
 * - Apply fill operation (copy values down/right)
 */

import { Dataset } from './types';

interface FillHandleCallbacks {
    getCurrentData: () => Dataset | null;
    setCurrentData: (data: Dataset | null) => void;
    getCellAt: (row: number, col: number) => HTMLElement | null;
    renderCallback: () => void;
    statusBarCallback?: (message: string) => void;
}

export class TableFillHandle {
    private callbacks: FillHandleCallbacks;

    constructor(callbacks: FillHandleCallbacks) {
        this.callbacks = callbacks;
    }

    /**
     * Handle fill handle mouse down (start drag-to-fill)
     */
    public handleFillHandleMouseDown(
        e: MouseEvent,
        selectionStart: { row: number, col: number },
        selectionEnd: { row: number, col: number }
    ): void {
        e.preventDefault();
        e.stopPropagation();

        const currentData = this.callbacks.getCurrentData();
        if (!currentData) return;

        const startRow = Math.min(selectionStart.row, selectionEnd.row);
        const endRow = Math.max(selectionStart.row, selectionEnd.row);
        const startCol = Math.min(selectionStart.col, selectionEnd.col);
        const endCol = Math.max(selectionStart.col, selectionEnd.col);

        let isFilling = true;
        let fillRow = endRow;
        let fillCol = endCol;

        const handleMouseMove = (e: MouseEvent) => {
            if (!isFilling) return;

            // Get cell under mouse
            const element = document.elementFromPoint(e.clientX, e.clientY) as HTMLElement;
            if (!element || !element.hasAttribute('data-row')) return;

            const newFillRow = parseInt(element.getAttribute('data-row') || '0');
            const newFillCol = parseInt(element.getAttribute('data-col') || '0');

            // Update fill preview
            if (newFillRow !== fillRow || newFillCol !== fillCol) {
                fillRow = newFillRow;
                fillCol = newFillCol;
                this.showFillPreview(startRow, endRow, startCol, endCol, fillRow, fillCol);
            }
        };

        const handleMouseUp = () => {
            if (!isFilling) return;
            isFilling = false;

            // Apply fill
            this.applyFill(startRow, endRow, startCol, endCol, fillRow, fillCol);

            // Clean up
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            document.querySelectorAll('.fill-preview').forEach(el => el.classList.remove('fill-preview'));
        };

        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);

        console.log('[TableFillHandle] Fill handle drag started');
    }

    /**
     * Show fill preview
     */
    private showFillPreview(
        startRow: number,
        endRow: number,
        startCol: number,
        endCol: number,
        fillRow: number,
        fillCol: number
    ): void {
        // Remove previous preview
        document.querySelectorAll('.fill-preview').forEach(el => el.classList.remove('fill-preview'));

        // Add preview class to fill range
        const fillStartRow = Math.min(endRow + 1, fillRow);
        const fillEndRow = Math.max(endRow, fillRow);
        const fillStartCol = Math.min(endCol + 1, fillCol);
        const fillEndCol = Math.max(endCol, fillCol);

        for (let r = fillStartRow; r <= fillEndRow; r++) {
            for (let c = fillStartCol; c <= fillEndCol; c++) {
                const cell = this.callbacks.getCellAt(r, c);
                if (cell) {
                    cell.classList.add('fill-preview');
                }
            }
        }
    }

    /**
     * Apply fill (auto-fill cells)
     */
    private applyFill(
        startRow: number,
        endRow: number,
        startCol: number,
        endCol: number,
        fillRow: number,
        fillCol: number
    ): void {
        const currentData = this.callbacks.getCurrentData();
        if (!currentData) return;

        // Determine fill direction
        const fillDown = fillRow > endRow;
        const fillRight = fillCol > endCol;

        if (fillDown) {
            // Fill down
            for (let r = endRow + 1; r <= fillRow; r++) {
                for (let c = startCol; c <= endCol; c++) {
                    // Copy from the row above (simple fill)
                    const sourceRow = endRow;
                    const sourceCol = c;
                    const sourceCell = this.callbacks.getCellAt(sourceRow, sourceCol);
                    if (sourceCell && r < currentData.rows.length && c < currentData.columns.length) {
                        const colName = currentData.columns[c];
                        const value = currentData.rows[sourceRow][colName];
                        currentData.rows[r][colName] = value;
                    }
                }
            }
        }

        if (fillRight) {
            // Fill right
            for (let c = endCol + 1; c <= fillCol; c++) {
                for (let r = startRow; r <= endRow; r++) {
                    // Copy from the column to the left
                    const sourceRow = r;
                    const sourceCol = endCol;
                    const sourceCell = this.callbacks.getCellAt(sourceRow, sourceCol);
                    if (sourceCell && r < currentData.rows.length && c < currentData.columns.length) {
                        const colName = currentData.columns[c];
                        const sourceColName = currentData.columns[sourceCol];
                        const value = currentData.rows[r][sourceColName];
                        currentData.rows[r][colName] = value;
                    }
                }
            }
        }

        this.callbacks.renderCallback();

        if (this.callbacks.statusBarCallback) {
            this.callbacks.statusBarCallback('Fill completed');
        }
        console.log('[TableFillHandle] Fill applied');
    }
}
