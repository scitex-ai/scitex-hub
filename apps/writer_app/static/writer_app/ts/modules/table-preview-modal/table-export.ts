/**
 * Table Export
 * Handles table export functionality
 */

console.log("[DEBUG] table-preview-modal/table-export.ts loaded");

import { TableData } from "./types.js";

export class TableExporter {
  exportToCSV(table: TableData): void {
    const { data, columns } = table;

    // Header
    let csv = columns.map((col) => this.escapeCsv(col)).join(",") + "\n";

    // Data rows
    data.forEach((row) => {
      const values = columns.map((col) => {
        const value =
          row[col] !== null && row[col] !== undefined ? row[col] : "";
        return this.escapeCsv(String(value));
      });
      csv += values.join(",") + "\n";
    });

    // Download
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", table.metadata.file_name);
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    console.log("[TableExporter] Exported CSV");
  }

  private escapeCsv(text: string): string {
    if (text.includes(",") || text.includes('"') || text.includes("\n")) {
      return '"' + text.replace(/"/g, '""') + '"';
    }
    return text;
  }
}
