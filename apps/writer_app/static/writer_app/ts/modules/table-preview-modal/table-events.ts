/**
 * Table Event Handlers
 * Manages table interaction events
 */

console.log("[DEBUG] table-preview-modal/table-events.ts loaded");

import { TableStateManager } from "./table-state.js";
import { TableRenderer } from "./table-renderer.js";

export class TableEventManager {
  constructor(
    private stateManager: TableStateManager,
    private renderer: TableRenderer,
    private onSave: () => Promise<void>,
    private onExport: () => void,
  ) {}

  setupButtonListeners(): void {
    // Add row button
    const addRowBtn = document.getElementById("table-add-row-btn");
    if (addRowBtn) {
      addRowBtn.addEventListener("click", () => this.handleAddRow());
    }

    // Add column button
    const addColumnBtn = document.getElementById("table-add-column-btn");
    if (addColumnBtn) {
      addColumnBtn.addEventListener("click", () => this.handleAddColumn());
    }

    // Delete rows button
    const deleteRowsBtn = document.getElementById("table-delete-rows-btn");
    if (deleteRowsBtn) {
      deleteRowsBtn.addEventListener("click", () => this.handleDeleteRows());
    }

    // Save button
    const saveBtn = document.getElementById("table-save-btn");
    if (saveBtn) {
      saveBtn.addEventListener("click", () => this.onSave());
    }

    // Export button
    const exportBtn = document.getElementById("table-export-btn");
    if (exportBtn) {
      exportBtn.addEventListener("click", () => this.onExport());
    }

    console.log("[TableEventManager] Button listeners setup complete");
  }

  setupModalCloseListener(): void {
    const modal = document.getElementById("tablePreviewModal");
    if (modal) {
      modal.addEventListener("hidden.bs.modal", () => {
        if (this.stateManager.isModified()) {
          const confirm = window.confirm(
            "You have unsaved changes. Are you sure you want to close?",
          );
          if (!confirm) {
            // Re-open modal
            const bsModal = new (window as any).bootstrap.Modal(modal);
            bsModal.show();
          }
        }
      });
    }
  }

  attachTableEventListeners(): void {
    this.attachSelectAllCheckbox();
    this.attachRowCheckboxes();
    this.attachCellInputs();
    this.attachColumnNameInputs();
    this.attachColumnDeleteButtons();
  }

  private attachSelectAllCheckbox(): void {
    const selectAllCheckbox = document.getElementById(
      "select-all-checkbox",
    ) as HTMLInputElement;
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener("change", (e) => {
        const checked = (e.target as HTMLInputElement).checked;
        document
          .querySelectorAll<HTMLInputElement>(".table-row-checkbox")
          .forEach((checkbox) => {
            checkbox.checked = checked;
            const row = parseInt(checkbox.dataset.row || "0");
            if (checked) {
              this.stateManager.addSelectedRow(row);
            } else {
              this.stateManager.removeSelectedRow(row);
            }
          });
        this.renderer.updateSelectedRowsUI();
      });
    }
  }

  private attachRowCheckboxes(): void {
    document
      .querySelectorAll<HTMLInputElement>(".table-row-checkbox")
      .forEach((checkbox) => {
        checkbox.addEventListener("change", (e) => {
          const row = parseInt(
            (e.target as HTMLInputElement).dataset.row || "0",
          );
          if ((e.target as HTMLInputElement).checked) {
            this.stateManager.addSelectedRow(row);
          } else {
            this.stateManager.removeSelectedRow(row);
          }
          this.renderer.updateSelectedRowsUI();
        });
      });
  }

  private attachCellInputs(): void {
    document
      .querySelectorAll<HTMLInputElement>(
        ".table-preview-table td input[type='text']",
      )
      .forEach((input) => {
        input.addEventListener("input", (e) => {
          const target = e.target as HTMLInputElement;
          const row = parseInt(target.dataset.row || "0");
          const col = parseInt(target.dataset.col || "0");
          const original = target.dataset.original || "";
          const newValue = target.value;

          const cellKey = `${row}-${col}`;

          if (newValue !== original) {
            this.stateManager.setModifiedCell(cellKey, newValue);
            target.parentElement?.classList.add("modified");
          } else {
            this.stateManager.deleteModifiedCell(cellKey);
            target.parentElement?.classList.remove("modified");
          }

          this.renderer.updateModifiedBadge();
        });
      });
  }

  private attachColumnNameInputs(): void {
    document
      .querySelectorAll<HTMLInputElement>(".column-name-input")
      .forEach((input) => {
        input.addEventListener("change", (e) => {
          const target = e.target as HTMLInputElement;
          const originalName = target.dataset.originalName || "";
          const newName = target.value.trim();

          if (newName && newName !== originalName) {
            this.stateManager.setRenamedColumn(originalName, newName);
            console.log(
              `[TableEventManager] Column renamed: ${originalName} → ${newName}`,
            );
          } else if (this.stateManager.getRenamedColumns().has(originalName)) {
            this.stateManager.deleteRenamedColumn(originalName);
          }

          this.renderer.updateModifiedBadge();
        });
      });
  }

  private attachColumnDeleteButtons(): void {
    document
      .querySelectorAll<HTMLSpanElement>(".table-column-delete")
      .forEach((btn) => {
        btn.addEventListener("click", (e) => {
          const colIndex = parseInt(
            (e.currentTarget as HTMLElement).dataset.colIndex || "0",
          );
          this.handleDeleteColumn(colIndex);
        });
      });
  }

  private handleAddRow(): void {
    this.stateManager.addRow();
    const container = document.getElementById("table-preview-container");
    if (container) {
      this.renderer.render(container);
      this.attachTableEventListeners();
      this.renderer.updateDimensionsBadge();
      this.renderer.updateModifiedBadge();
    }
    console.log("[TableEventManager] Added new row");
  }

  private handleDeleteRows(): void {
    const selectedRows = this.stateManager.getSelectedRows();
    if (selectedRows.size === 0) return;

    const confirm = window.confirm(
      `Are you sure you want to delete ${selectedRows.size} row(s)?`,
    );
    if (!confirm) return;

    this.stateManager.deleteRows(Array.from(selectedRows));

    const container = document.getElementById("table-preview-container");
    if (container) {
      this.renderer.render(container);
      this.attachTableEventListeners();
      this.renderer.updateDimensionsBadge();
      this.renderer.updateModifiedBadge();
      this.renderer.updateSelectedRowsUI();
    }

    console.log("[TableEventManager] Deleted rows:", Array.from(selectedRows));
  }

  private handleAddColumn(): void {
    // Prompt for column name
    const columnName = window.prompt("Enter new column name:");
    if (!columnName || !columnName.trim()) return;

    const newColName = columnName.trim();

    const success = this.stateManager.addColumn(newColName);
    if (!success) {
      alert(`Column "${newColName}" already exists!`);
      return;
    }

    const container = document.getElementById("table-preview-container");
    if (container) {
      this.renderer.render(container);
      this.attachTableEventListeners();
      this.renderer.updateDimensionsBadge();
      this.renderer.updateModifiedBadge();
    }

    console.log("[TableEventManager] Added new column:", newColName);
  }

  private handleDeleteColumn(colIndex: number): void {
    const table = this.stateManager.getCurrentTable();
    if (!table) return;

    const columnName = table.columns[colIndex];
    if (!columnName) return;

    const confirm = window.confirm(
      `Are you sure you want to delete column "${columnName}"?\nAll data in this column will be lost.`,
    );
    if (!confirm) return;

    this.stateManager.deleteColumn(colIndex);

    const container = document.getElementById("table-preview-container");
    if (container) {
      this.renderer.render(container);
      this.attachTableEventListeners();
      this.renderer.updateDimensionsBadge();
      this.renderer.updateModifiedBadge();
    }

    console.log("[TableEventManager] Deleted column:", columnName);
  }
}
