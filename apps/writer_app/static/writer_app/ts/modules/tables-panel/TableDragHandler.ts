/**
 * Table Drag Handler
 * Manages drag-and-drop functionality for inserting tables into editor
 */

import { Table } from "./types.js";

export class TableDragHandler {
  /**
   * Handle drag start
   */
  handleDragStart(event: DragEvent, table: Table): void {
    if (!event.dataTransfer) return;

    const tableKey = table.label || table.file_name;
    const figLabel = `fig:${tableKey.replace(/\.[^/.]+$/, "").replace(/[^a-zA-Z0-9_-]/g, "_")}`;

    const latexCode = `\\begin{table}[h]
  \\centering
  \\includegraphics[width=0.8\\textwidth]{${table.file_path}}
  \\caption{${table.caption || "Caption here"}}
  \\label{${figLabel}}
\\end{table}`;

    event.dataTransfer.setData("text/plain", latexCode);
    event.dataTransfer.effectAllowed = "copy";

    const target = event.target as HTMLElement;
    target.classList.add("dragging");

    console.log("[TableDragHandler] Drag started:", tableKey);
  }

  /**
   * Handle drag end
   */
  handleDragEnd(event: DragEvent): void {
    const target = event.target as HTMLElement;
    target.classList.remove("dragging");
  }
}
