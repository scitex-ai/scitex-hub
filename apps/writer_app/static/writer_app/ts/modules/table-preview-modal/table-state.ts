/**
 * Table State Management
 * Manages table data and modification state
 */

console.log("[DEBUG] table-preview-modal/table-state.ts loaded");

import { TableData, TableState } from "./types.js";

export class TableStateManager {
  private state: TableState;

  constructor() {
    this.state = {
      projectId: null,
      currentTable: null,
      currentFileHash: null,
      selectedRows: new Set(),
      modifiedCells: new Map(),
      renamedColumns: new Map(),
      deletedColumns: new Set(),
      isModified: false,
    };

    this.initProjectId();
  }

  private initProjectId(): void {
    const writerConfig = (window as any).WRITER_CONFIG;
    if (writerConfig?.projectId) {
      this.state.projectId = String(writerConfig.projectId);
      console.log(
        "[TableStateManager] Initialized with project:",
        this.state.projectId,
      );
    }
  }

  getProjectId(): string | null {
    return this.state.projectId;
  }

  getCurrentTable(): TableData | null {
    return this.state.currentTable;
  }

  setCurrentTable(table: TableData | null): void {
    this.state.currentTable = table;
  }

  getCurrentFileHash(): string | null {
    return this.state.currentFileHash;
  }

  setCurrentFileHash(hash: string | null): void {
    this.state.currentFileHash = hash;
  }

  getSelectedRows(): Set<number> {
    return this.state.selectedRows;
  }

  addSelectedRow(row: number): void {
    this.state.selectedRows.add(row);
  }

  removeSelectedRow(row: number): void {
    this.state.selectedRows.delete(row);
  }

  clearSelectedRows(): void {
    this.state.selectedRows.clear();
  }

  getModifiedCells(): Map<string, any> {
    return this.state.modifiedCells;
  }

  setModifiedCell(key: string, value: any): void {
    this.state.modifiedCells.set(key, value);
    this.state.isModified = true;
  }

  deleteModifiedCell(key: string): void {
    this.state.modifiedCells.delete(key);
    this.updateModifiedStatus();
  }

  clearModifiedCells(): void {
    this.state.modifiedCells.clear();
    this.updateModifiedStatus();
  }

  getRenamedColumns(): Map<string, string> {
    return this.state.renamedColumns;
  }

  setRenamedColumn(oldName: string, newName: string): void {
    this.state.renamedColumns.set(oldName, newName);
    this.state.isModified = true;
  }

  deleteRenamedColumn(oldName: string): void {
    this.state.renamedColumns.delete(oldName);
    this.updateModifiedStatus();
  }

  clearRenamedColumns(): void {
    this.state.renamedColumns.clear();
    this.updateModifiedStatus();
  }

  isModified(): boolean {
    return this.state.isModified;
  }

  setModified(modified: boolean): void {
    this.state.isModified = modified;
  }

  private updateModifiedStatus(): void {
    this.state.isModified =
      this.state.modifiedCells.size > 0 || this.state.renamedColumns.size > 0;
  }

  reset(): void {
    this.state.selectedRows.clear();
    this.state.modifiedCells.clear();
    this.state.renamedColumns.clear();
    this.state.deletedColumns.clear();
    this.state.isModified = false;
  }

  addRow(): void {
    if (!this.state.currentTable) return;

    const newRow: Record<string, any> = {};
    this.state.currentTable.columns.forEach((col) => {
      newRow[col] = "";
    });

    this.state.currentTable.data.push(newRow);
    this.state.currentTable.metadata.rows++;
    this.state.isModified = true;
  }

  deleteRows(rowIndices: number[]): void {
    if (!this.state.currentTable) return;

    // Sort in descending order to delete from end
    const sorted = rowIndices.sort((a, b) => b - a);

    sorted.forEach((rowIndex) => {
      this.state.currentTable!.data.splice(rowIndex, 1);
    });

    this.state.currentTable.metadata.rows = this.state.currentTable.data.length;
    this.state.selectedRows.clear();

    // Clear modified cells for deleted rows
    const keysToDelete: string[] = [];
    this.state.modifiedCells.forEach((value, key) => {
      const [row] = key.split("-").map(Number);
      if (sorted.includes(row)) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach((key) => this.state.modifiedCells.delete(key));

    this.state.isModified = true;
  }

  addColumn(columnName: string): boolean {
    if (!this.state.currentTable) return false;

    // Check if column already exists
    if (this.state.currentTable.columns.includes(columnName)) {
      return false;
    }

    // Add column to table
    this.state.currentTable.columns.push(columnName);
    this.state.currentTable.metadata.cols++;

    // Add empty values for this column in all rows
    this.state.currentTable.data.forEach((row) => {
      row[columnName] = "";
    });

    this.state.isModified = true;
    return true;
  }

  deleteColumn(colIndex: number): void {
    if (!this.state.currentTable) return;

    const columnName = this.state.currentTable.columns[colIndex];
    if (!columnName) return;

    // Remove column from columns array
    this.state.currentTable.columns.splice(colIndex, 1);
    this.state.currentTable.metadata.cols--;

    // Remove column data from all rows
    this.state.currentTable.data.forEach((row) => {
      delete row[columnName];
    });

    // Clean up related tracking
    this.state.renamedColumns.delete(columnName);

    // Clear modified cells for this column
    const keysToDelete: string[] = [];
    this.state.modifiedCells.forEach((value, key) => {
      const [row, col] = key.split("-").map(Number);
      if (col === colIndex) {
        keysToDelete.push(key);
      } else if (col > colIndex) {
        // Shift keys for columns after the deleted one
        const newKey = `${row}-${col - 1}`;
        this.state.modifiedCells.set(newKey, value);
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach((key) => this.state.modifiedCells.delete(key));

    this.state.isModified = true;
  }

  applyModifications(): void {
    if (!this.state.currentTable) return;

    // Apply all cell modifications to data
    this.state.modifiedCells.forEach((value, key) => {
      const [row, col] = key.split("-").map(Number);
      const colName = this.state.currentTable!.columns[col];
      this.state.currentTable!.data[row][colName] = value;
    });

    // Apply column renames
    if (this.state.renamedColumns.size > 0) {
      this.state.renamedColumns.forEach((newName, oldName) => {
        // Update column name in columns array
        const colIndex = this.state.currentTable!.columns.indexOf(oldName);
        if (colIndex !== -1) {
          this.state.currentTable!.columns[colIndex] = newName;
        }

        // Update all row data to use new column name
        this.state.currentTable!.data.forEach((row) => {
          if (oldName in row) {
            row[newName] = row[oldName];
            delete row[oldName];
          }
        });
      });
    }
  }
}
