/**
 * Table Renderer
 * Handles table HTML generation and rendering
 */

console.log("[DEBUG] table-preview-modal/table-renderer.ts loaded");

import { TableData } from "./types.js";
import { TableStateManager } from "./table-state.js";

export class TableRenderer {
  constructor(private stateManager: TableStateManager) {}

  render(container: HTMLElement): void {
    const table = this.stateManager.getCurrentTable();
    if (!table) return;

    container.innerHTML = this.generateTableHTML(table);
  }

  private generateTableHTML(table: TableData): string {
    const { data, columns } = table;
    const renamedColumns = this.stateManager.getRenamedColumns();
    const modifiedCells = this.stateManager.getModifiedCells();
    const selectedRows = this.stateManager.getSelectedRows();

    let html = `
      <table class="table-preview-table">
        <thead>
          <tr>
            <th><input type="checkbox" id="select-all-checkbox" title="Select all"></th>
            <th>#</th>
    `;

    // Generate column headers
    columns.forEach((col, colIndex) => {
      const displayName = renamedColumns.get(col) || col;
      html += `
        <th>
          <div class="table-column-header">
            <div class="table-column-name">
              <input type="text"
                     value="${this.escapeHtml(displayName)}"
                     data-col-index="${colIndex}"
                     data-original-name="${this.escapeHtml(col)}"
                     class="column-name-input"
                     title="Click to rename column">
            </div>
            <span class="table-column-delete" data-col-index="${colIndex}" title="Delete column">
              <i class="fas fa-times"></i>
            </span>
          </div>
        </th>
      `;
    });

    html += `
          </tr>
        </thead>
        <tbody>
    `;

    // Generate data rows
    data.forEach((row, rowIndex) => {
      const isSelected = selectedRows.has(rowIndex);
      html += `
        <tr class="${isSelected ? "selected" : ""}" data-row="${rowIndex}">
          <td><input type="checkbox" class="table-row-checkbox" data-row="${rowIndex}" ${isSelected ? "checked" : ""}></td>
          <td class="table-row-number">${rowIndex + 1}</td>
      `;

      columns.forEach((col, colIndex) => {
        const value =
          row[col] !== null && row[col] !== undefined ? row[col] : "";
        const cellKey = `${rowIndex}-${colIndex}`;
        const isModified = modifiedCells.has(cellKey);
        const displayValue = isModified ? modifiedCells.get(cellKey) : value;

        html += `
          <td class="${isModified ? "modified" : ""}">
            <input type="text"
                   value="${this.escapeHtml(String(displayValue))}"
                   data-row="${rowIndex}"
                   data-col="${colIndex}"
                   data-original="${this.escapeHtml(String(value))}">
          </td>
        `;
      });

      html += `</tr>`;
    });

    html += `
        </tbody>
      </table>
    `;

    return html;
  }

  updateDimensionsBadge(): void {
    const table = this.stateManager.getCurrentTable();
    if (!table) return;

    const badge = document.getElementById("table-dimensions-badge");
    if (badge) {
      badge.textContent = `${table.metadata.rows} rows × ${table.metadata.cols} cols`;
    }
  }

  updateModifiedBadge(): void {
    const badge = document.getElementById("table-modified-badge");
    const saveBtn = document.getElementById(
      "table-save-btn",
    ) as HTMLButtonElement;

    if (badge && saveBtn) {
      if (this.stateManager.isModified()) {
        badge.style.display = "inline-block";
        saveBtn.disabled = false;
      } else {
        badge.style.display = "none";
        saveBtn.disabled = true;
      }
    }
  }

  updateSelectedRowsUI(): void {
    // Update row styling
    document
      .querySelectorAll<HTMLTableRowElement>(".table-preview-table tbody tr")
      .forEach((tr) => {
        const row = parseInt(tr.dataset.row || "0");
        if (this.stateManager.getSelectedRows().has(row)) {
          tr.classList.add("selected");
        } else {
          tr.classList.remove("selected");
        }
      });

    // Update delete button
    const deleteBtn = document.getElementById(
      "table-delete-rows-btn",
    ) as HTMLButtonElement;
    if (deleteBtn) {
      deleteBtn.disabled = this.stateManager.getSelectedRows().size === 0;
    }
  }

  showError(message: string): void {
    const errorDiv = document.getElementById("table-preview-error");
    const errorMessage = document.getElementById("table-error-message");

    if (errorDiv && errorMessage) {
      errorMessage.textContent = message;
      errorDiv.style.display = "block";
    }

    console.error("[TableRenderer] Error:", message);
  }

  showLoading(container: HTMLElement): void {
    container.innerHTML = `
      <div class="text-center text-muted py-4">
        <i class="fas fa-spinner fa-spin me-2"></i>Loading table data...
      </div>
    `;
  }

  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }
}
