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

import { Dataset, DataRow } from "./types";

export interface TableEditingCallbacks {
  getCurrentData: () => Dataset | null;
  setCurrentData: (data: Dataset | null) => void;
  getCellAt: (row: number, col: number) => HTMLElement | null;
  renderCallback: () => void;
  getSelection: () => {
    start: { row: number; col: number } | null;
    end: { row: number; col: number } | null;
  };
  updateSelection: () => void;
  selectCellAt: (row: number, col: number) => void;
  setCurrentCell: (row: number, col: number) => void; // Move currentCell within selection
  hasRangeSelection: () => boolean; // Check if multiple cells are selected
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

    cell.contentEditable = "true";
    cell.classList.add("editing");
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
    cell.addEventListener("blur", this.editingCellBlurHandler);
  }

  /**
   * Exit edit mode
   */
  public exitEditMode(): void {
    if (!this.editingCell) return;

    // Remove blur handler
    if (this.editingCellBlurHandler) {
      this.editingCell.removeEventListener("blur", this.editingCellBlurHandler);
      this.editingCellBlurHandler = null;
    }

    this.editingCell.contentEditable = "false";
    this.editingCell.classList.remove("editing");
    this.handleCellEdit(this.editingCell);
    this.editingCell = null;
  }

  /**
   * Handle cell editing
   */
  private handleCellEdit(cell: HTMLElement): void {
    const rowIndex = cell.getAttribute("data-row");
    const colIndex = cell.getAttribute("data-col");
    const value = cell.textContent?.trim() || "";

    const currentData = this.callbacks.getCurrentData();
    if (!currentData) return;

    if (cell.tagName === "TH" && colIndex !== null) {
      // Update column name
      const idx = parseInt(colIndex);
      if (idx < currentData.columns.length) {
        const oldName = currentData.columns[idx];
        const newName = value || this.getColumnLabel(idx);
        currentData.columns[idx] = newName;

        // Update all row data with new column name
        currentData.rows.forEach((row) => {
          if (oldName in row) {
            row[newName] = row[oldName];
            if (oldName !== newName) {
              delete row[oldName];
            }
          }
        });

        console.log("[TableEditing] Column renamed:", oldName, "->", newName);
      }
    } else if (rowIndex !== null && colIndex !== null) {
      // Update cell value
      const rIdx = parseInt(rowIndex);
      const cIdx = parseInt(colIndex);
      if (rIdx < currentData.rows.length && cIdx < currentData.columns.length) {
        const colName = currentData.columns[cIdx];
        const numValue = parseFloat(value);
        currentData.rows[rIdx][colName] =
          isNaN(numValue) || value === "" ? value : numValue;
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
      const rowIndex = parseInt(cell.getAttribute("data-row") || "-1");
      const colIndex = parseInt(cell.getAttribute("data-col") || "-1");

      if (e.key === "Escape") {
        e.preventDefault();
        this.exitEditMode();
        cell.focus();
      } else if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        this.exitEditMode();

        // Calculate next position and enter edit mode there
        const mode = e.key === "Tab" ? "tab" : "enter";
        const nextPos = this.calculateNextPosition(
          rowIndex,
          colIndex,
          mode,
          e.shiftKey,
          currentData,
        );
        const targetCell = this.callbacks.getCellAt(nextPos.row, nextPos.col);

        if (targetCell) {
          // Update currentCell (keeps currentCells if range selected)
          if (this.callbacks.hasRangeSelection()) {
            this.callbacks.setCurrentCell(nextPos.row, nextPos.col);
          } else {
            this.callbacks.selectCellAt(nextPos.row, nextPos.col);
          }
          // Continue editing in next cell
          this.enterEditMode(targetCell);
        }
      } else if (e.key === "F2") {
        // F2 in edit mode - exit edit mode
        e.preventDefault();
        this.exitEditMode();
        cell.focus();
      } else if (
        e.key === "ArrowUp" ||
        e.key === "ArrowDown" ||
        e.key === "ArrowLeft" ||
        e.key === "ArrowRight"
      ) {
        // Arrow keys in edit mode: commit and navigate (Excel behavior)
        e.preventDefault();
        this.exitEditMode();

        let targetCell: HTMLElement | null = null;
        if (e.key === "ArrowUp" && rowIndex > 0) {
          targetCell = this.callbacks.getCellAt(rowIndex - 1, colIndex);
        } else if (
          e.key === "ArrowDown" &&
          rowIndex < currentData.rows.length - 1
        ) {
          targetCell = this.callbacks.getCellAt(rowIndex + 1, colIndex);
        } else if (e.key === "ArrowLeft" && colIndex > 0) {
          targetCell = this.callbacks.getCellAt(rowIndex, colIndex - 1);
        } else if (
          e.key === "ArrowRight" &&
          colIndex < currentData.columns.length - 1
        ) {
          targetCell = this.callbacks.getCellAt(rowIndex, colIndex + 1);
        }

        if (targetCell) {
          this.moveTo(targetCell);
        } else {
          cell.focus();
        }
      }
      return;
    }

    const rowIndex = parseInt(cell.getAttribute("data-row") || "-1");
    const colIndex = parseInt(cell.getAttribute("data-col") || "-1");

    if (rowIndex === -1 || colIndex === -1) return;

    let targetCell: HTMLElement | null = null;

    // Handle Delete/Backspace - clear all cells in currentCells
    if (e.key === "Backspace" || e.key === "Delete") {
      e.preventDefault();
      this.clearSelectedCells();
      return;
    }

    // Check if it's a printable character - enter edit mode on currentCell
    if (e.key.length === 1) {
      // Update currentCell to this cell (keeps currentCells intact)
      this.callbacks.setCurrentCell(rowIndex, colIndex);
      // Enter edit mode and let the character be typed
      this.enterEditMode(cell);
      return;
    }

    switch (e.key) {
      case "ArrowUp":
        e.preventDefault();
        if (rowIndex > 0) {
          targetCell = this.callbacks.getCellAt(rowIndex - 1, colIndex);
        }
        break;

      case "ArrowDown":
        e.preventDefault();
        if (rowIndex < currentData.rows.length - 1) {
          targetCell = this.callbacks.getCellAt(rowIndex + 1, colIndex);
        }
        break;

      case "ArrowLeft":
        e.preventDefault();
        if (colIndex > 0) {
          targetCell = this.callbacks.getCellAt(rowIndex, colIndex - 1);
        }
        break;

      case "ArrowRight":
        e.preventDefault();
        if (colIndex < currentData.columns.length - 1) {
          targetCell = this.callbacks.getCellAt(rowIndex, colIndex + 1);
        }
        break;

      case "Tab":
        e.preventDefault();
        this.handleSelectionNavigation(
          rowIndex,
          colIndex,
          "tab",
          e.shiftKey,
          currentData,
        );
        return; // Don't call moveTo (which collapses selection)

      case "Enter":
        e.preventDefault();
        this.handleSelectionNavigation(
          rowIndex,
          colIndex,
          "enter",
          e.shiftKey,
          currentData,
        );
        return; // Don't call moveTo (which collapses selection)

      case "F2":
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
   * This is a helper method that focuses the target cell and updates selection
   */
  private moveTo(targetCell: HTMLElement): void {
    const rowIndex = parseInt(targetCell.getAttribute("data-row") || "-1");
    const colIndex = parseInt(targetCell.getAttribute("data-col") || "-1");

    if (rowIndex >= 0 && colIndex >= 0) {
      // Update selection state and visual highlight
      this.callbacks.selectCellAt(rowIndex, colIndex);
    }

    // Focus the target cell
    targetCell.focus();
  }

  /**
   * Handle Tab/Enter navigation - keeps rectangular selection if exists
   */
  private handleSelectionNavigation(
    currentRow: number,
    currentCol: number,
    mode: "tab" | "enter",
    reverse: boolean,
    data: Dataset,
  ): void {
    const hasRectSelection = this.callbacks.hasRangeSelection();
    const nextPos = this.calculateNextPosition(
      currentRow,
      currentCol,
      mode,
      reverse,
      data,
    );

    if (hasRectSelection) {
      // Move currentCell within selection (keeps currentCells intact)
      this.callbacks.setCurrentCell(nextPos.row, nextPos.col);
    } else {
      // No rectangular selection - move and select the new cell
      this.callbacks.selectCellAt(nextPos.row, nextPos.col);
      const targetCell = this.callbacks.getCellAt(nextPos.row, nextPos.col);
      if (targetCell) {
        targetCell.focus();
      }
    }
  }

  /**
   * Calculate next cell position within selection bounds
   * Tab: move left-to-right, wrap to next row
   * Enter: move top-to-bottom, wrap to next column
   */
  private calculateNextPosition(
    currentRow: number,
    currentCol: number,
    mode: "tab" | "enter",
    reverse: boolean,
    data: Dataset,
  ): { row: number; col: number } {
    const selection = this.callbacks.getSelection();
    const start = selection.start;
    const end = selection.end;

    // If no selection or single cell selected, use full table bounds
    const hasRectSelection =
      start && end && (start.row !== end.row || start.col !== end.col);

    const minRow = hasRectSelection ? Math.min(start!.row, end!.row) : 0;
    const maxRow = hasRectSelection
      ? Math.max(start!.row, end!.row)
      : data.rows.length - 1;
    const minCol = hasRectSelection ? Math.min(start!.col, end!.col) : 0;
    const maxCol = hasRectSelection
      ? Math.max(start!.col, end!.col)
      : data.columns.length - 1;

    let nextRow = currentRow;
    let nextCol = currentCol;

    if (mode === "tab") {
      // Tab: horizontal movement (left-to-right, wrap to next row)
      if (!reverse) {
        // Tab: move right
        if (currentCol < maxCol) {
          nextCol = currentCol + 1;
        } else {
          // Wrap to next row, first column of selection
          nextCol = minCol;
          nextRow = currentRow < maxRow ? currentRow + 1 : minRow;
        }
      } else {
        // Shift+Tab: move left
        if (currentCol > minCol) {
          nextCol = currentCol - 1;
        } else {
          // Wrap to previous row, last column of selection
          nextCol = maxCol;
          nextRow = currentRow > minRow ? currentRow - 1 : maxRow;
        }
      }
    } else {
      // Enter: vertical movement (top-to-bottom, wrap to next column)
      if (!reverse) {
        // Enter: move down
        if (currentRow < maxRow) {
          nextRow = currentRow + 1;
        } else {
          // Wrap to next column, first row of selection
          nextRow = minRow;
          nextCol = currentCol < maxCol ? currentCol + 1 : minCol;
        }
      } else {
        // Shift+Enter: move up
        if (currentRow > minRow) {
          nextRow = currentRow - 1;
        } else {
          // Wrap to previous column, last row of selection
          nextRow = maxRow;
          nextCol = currentCol > minCol ? currentCol - 1 : maxCol;
        }
      }
    }

    return { row: nextRow, col: nextCol };
  }

  /**
   * Clear all cells in currentCells range
   */
  private clearSelectedCells(): void {
    const currentData = this.callbacks.getCurrentData();
    if (!currentData) return;

    const selection = this.callbacks.getSelection();
    const start = selection.start;
    const end = selection.end;

    if (!start || !end) return;

    const minRow = Math.min(start.row, end.row);
    const maxRow = Math.max(start.row, end.row);
    const minCol = Math.min(start.col, end.col);
    const maxCol = Math.max(start.col, end.col);

    // Clear all cells in the range
    for (let r = minRow; r <= maxRow; r++) {
      for (let c = minCol; c <= maxCol; c++) {
        if (r < currentData.rows.length && c < currentData.columns.length) {
          const colName = currentData.columns[c];
          currentData.rows[r][colName] = "";

          // Update visual
          const cell = this.callbacks.getCellAt(r, c);
          if (cell) {
            cell.textContent = "";
          }
        }
      }
    }

    console.log(
      `[TableEditing] Cleared cells [${minRow}-${maxRow}, ${minCol}-${maxCol}]`,
    );
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
