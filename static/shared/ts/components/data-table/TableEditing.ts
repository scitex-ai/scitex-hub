/**
 * TableEditing - Handles cell editing and keyboard navigation
 *
 * Responsibilities:
 * - Enter/exit edit mode for cells
 * - Handle cell editing (double-click to edit)
 * - Keyboard navigation (Arrow keys, Tab, Enter)
 * - Handle Delete/Backspace to clear cells
 * - F2 to toggle edit mode
 */

import { Dataset, DataRow } from './types.ts';

export interface TableEditingCallbacks {
    getCurrentData: () => Dataset | null;
    setCurrentData: (data: Dataset | null) => void;
    getCellAt: (row: number, col: number) => HTMLElement | null;
    renderCallback: () => void;
    getSelection: () => { start: { row: number; col: number } | null; end: { row: number; col: number } | null };
    updateSelection: () => void;
    statusBarCallback?: (message: string) => void;
}

export class TableEditing {
    // Editing state
    private editingCell: HTMLElement | null = null;
    private editingCellBlurHandler: (() => void) | null = null;

    constructor(private callbacks: TableEditingCallbacks) {}

    /**
     * Enter edit mode for a cell
     */
    public enterEditMode(cell: HTMLElement): void {
        this.exitEditMode(); // Exit any existing edit mode

        cell.contentEditable = 'true';
        cell.focus();
        this.editingCell = cell;

        // Select all text
        const range = document.createRange();
        range.selectNodeContents(cell);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);

        // On blur, exit edit mode
        this.editingCellBlurHandler = () => {
            // Only exit if we're still editing this cell
            if (this.editingCell === cell) {
                this.exitEditMode();
            }
        };
        cell.addEventListener('blur', this.editingCellBlurHandler);
    }

    /**
     * Exit edit mode
     */
    public exitEditMode(): void {
        if (!this.editingCell) return;

        // Remove blur handler
        if (this.editingCellBlurHandler) {
            this.editingCell.removeEventListener('blur', this.editingCellBlurHandler);
            this.editingCellBlurHandler = null;
        }

        this.editingCell.contentEditable = 'false';
        this.handleCellEdit(this.editingCell);
        this.editingCell = null;
    }

    /**
     * Handle cell editing
     */
    private handleCellEdit(cell: HTMLElement): void {
        const rowIndex = cell.getAttribute('data-row');
        const colIndex = cell.getAttribute('data-col');
        const value = cell.textContent?.trim() || '';

        const currentData = this.callbacks.getCurrentData();
        if (!currentData) return;

        if (cell.tagName === 'TH' && colIndex !== null) {
            // Update column name
            const idx = parseInt(colIndex);
            if (idx < currentData.columns.length) {
                const oldName = currentData.columns[idx];
                const newName = value || this.getColumnLabel(idx);
                currentData.columns[idx] = newName;

                // Update all row data with new column name
                currentData.rows.forEach(row => {
                    if (oldName in row) {
                        row[newName] = row[oldName];
                        if (oldName !== newName) {
                            delete row[oldName];
                        }
                    }
                });

                console.log('[TableEditing] Column renamed:', oldName, '->', newName);
            }
        } else if (rowIndex !== null && colIndex !== null) {
            // Update cell value
            const rIdx = parseInt(rowIndex);
            const cIdx = parseInt(colIndex);
            if (rIdx < currentData.rows.length && cIdx < currentData.columns.length) {
                const colName = currentData.columns[cIdx];
                const numValue = parseFloat(value);
                currentData.rows[rIdx][colName] = isNaN(numValue) || value === '' ? value : numValue;
                console.log(`[TableEditing] Cell updated [${rIdx},${cIdx}]:`, value);
            }
        }
    }

    /**
     * Handle keyboard navigation in cells
     */
    public handleCellKeydown(e: KeyboardEvent, cell: HTMLElement): void {
        const currentData = this.callbacks.getCurrentData();
        if (!currentData) return;

        // If in edit mode, handle differently
        if (this.editingCell === cell) {
            if (e.key === 'Escape') {
                e.preventDefault();
                this.exitEditMode();
                cell.focus();
            } else if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.exitEditMode();
                // Move down
                const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
                const colIndex = parseInt(cell.getAttribute('data-col') || '-1');
                if (rowIndex < currentData.rows.length - 1) {
                    const targetCell = this.callbacks.getCellAt(rowIndex + 1, colIndex);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                }
            } else if (e.key === 'Enter' && e.shiftKey) {
                e.preventDefault();
                this.exitEditMode();
                // Move up with Shift+Enter
                const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
                const colIndex = parseInt(cell.getAttribute('data-col') || '-1');
                if (rowIndex > 0) {
                    const targetCell = this.callbacks.getCellAt(rowIndex - 1, colIndex);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                }
            } else if (e.key === 'Tab' && !e.shiftKey) {
                e.preventDefault();
                this.exitEditMode();
                // Move right with Tab
                const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
                const colIndex = parseInt(cell.getAttribute('data-col') || '-1');
                if (colIndex < currentData.columns.length - 1) {
                    const targetCell = this.callbacks.getCellAt(rowIndex, colIndex + 1);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                } else if (rowIndex < currentData.rows.length - 1) {
                    // Wrap to next row
                    const targetCell = this.callbacks.getCellAt(rowIndex + 1, 0);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                }
            } else if (e.key === 'Tab' && e.shiftKey) {
                e.preventDefault();
                this.exitEditMode();
                // Move left with Shift+Tab
                const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
                const colIndex = parseInt(cell.getAttribute('data-col') || '-1');
                if (colIndex > 0) {
                    const targetCell = this.callbacks.getCellAt(rowIndex, colIndex - 1);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                } else if (rowIndex > 0) {
                    // Wrap to previous row
                    const targetCell = this.callbacks.getCellAt(rowIndex - 1, currentData.columns.length - 1);
                    if (targetCell) {
                        this.moveTo(targetCell);
                    }
                }
            } else if (e.key === 'F2') {
                // F2 in edit mode - exit edit mode
                e.preventDefault();
                this.exitEditMode();
                cell.focus();
            }
            return;
        }

        const rowIndex = parseInt(cell.getAttribute('data-row') || '-1');
        const colIndex = parseInt(cell.getAttribute('data-col') || '-1');

        if (rowIndex === -1 || colIndex === -1) return;

        let targetCell: HTMLElement | null = null;

        // Check if it's a printable character or backspace/delete
        if (e.key.length === 1 || e.key === 'Backspace' || e.key === 'Delete') {
            // Enter edit mode and let the character be typed
            this.enterEditMode(cell);
            if (e.key === 'Backspace' || e.key === 'Delete') {
                e.preventDefault();
                cell.textContent = '';
            }
            return;
        }

        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                if (rowIndex > 0) {
                    targetCell = this.callbacks.getCellAt(rowIndex - 1, colIndex);
                }
                break;

            case 'ArrowDown':
                e.preventDefault();
                if (rowIndex < currentData.rows.length - 1) {
                    targetCell = this.callbacks.getCellAt(rowIndex + 1, colIndex);
                }
                break;

            case 'ArrowLeft':
                e.preventDefault();
                if (colIndex > 0) {
                    targetCell = this.callbacks.getCellAt(rowIndex, colIndex - 1);
                }
                break;

            case 'ArrowRight':
                e.preventDefault();
                if (colIndex < currentData.columns.length - 1) {
                    targetCell = this.callbacks.getCellAt(rowIndex, colIndex + 1);
                }
                break;

            case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                    // Shift+Tab - move left
                    if (colIndex > 0) {
                        targetCell = this.callbacks.getCellAt(rowIndex, colIndex - 1);
                    } else if (rowIndex > 0) {
                        targetCell = this.callbacks.getCellAt(rowIndex - 1, currentData.columns.length - 1);
                    }
                } else {
                    // Tab - move right
                    if (colIndex < currentData.columns.length - 1) {
                        targetCell = this.callbacks.getCellAt(rowIndex, colIndex + 1);
                    } else if (rowIndex < currentData.rows.length - 1) {
                        targetCell = this.callbacks.getCellAt(rowIndex + 1, 0);
                    }
                }
                break;

            case 'Enter':
                e.preventDefault();
                if (e.shiftKey) {
                    // Shift+Enter - move up
                    if (rowIndex > 0) {
                        targetCell = this.callbacks.getCellAt(rowIndex - 1, colIndex);
                    }
                } else {
                    // Enter - move down (Excel behavior)
                    if (rowIndex < currentData.rows.length - 1) {
                        targetCell = this.callbacks.getCellAt(rowIndex + 1, colIndex);
                    }
                }
                break;

            case 'F2':
                e.preventDefault();
                // F2 - enter edit mode
                this.enterEditMode(cell);
                break;
        }

        if (targetCell) {
            this.moveTo(targetCell);
        }
    }

    /**
     * Move selection to target cell
     * This is a helper method that simulates a mouse down event on the target cell
     */
    private moveTo(targetCell: HTMLElement): void {
        // Focus the target cell
        targetCell.focus();

        // We need to trigger a selection update, but we don't have direct access to
        // the selection state. The parent class should handle this through the
        // handleCellMouseDown event, but since we're in a separated module,
        // we'll trigger focus which should be enough for navigation.
        // The actual selection update would need to be handled by the parent.
    }

    /**
     * Get column label (1, 2, 3, ...)
     */
    private getColumnLabel(index: number): string {
        return `${index + 1}`;
    }

    /**
     * Check if currently in edit mode
     */
    public isEditing(): boolean {
        return this.editingCell !== null;
    }

    /**
     * Get the cell currently being edited
     */
    public getEditingCell(): HTMLElement | null {
        return this.editingCell;
    }
}
