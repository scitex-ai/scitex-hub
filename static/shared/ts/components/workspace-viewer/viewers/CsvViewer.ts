/**
 * CsvViewer - Uses the shared DataTableManager for rich spreadsheet rendering.
 */

import type { Viewer } from "../types";
import { getFileUrl } from "../_file-loader";
import { DataTableManager } from "../../data-table/DataTableManager";

export class CsvViewer implements Viewer {
  private abortController: AbortController | null = null;
  private tableManager: DataTableManager | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const apiUrl = getFileUrl(filePath, projectId, false);
    const fileName = filePath.split("/").pop() || filePath;

    container.innerHTML = "";
    this.abortController = new AbortController();

    const content = document.createElement("div");
    content.style.cssText = "height:100%; overflow:auto; padding:0;";
    content.innerHTML =
      '<div style="color:#888; padding:10px;">Loading...</div>';
    container.appendChild(content);

    let rawText = "";

    try {
      const resp = await fetch(apiUrl, { signal: this.abortController.signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const ct = resp.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        const json = await resp.json();
        rawText = json.content ?? "";
      } else {
        rawText = await resp.text();
      }
    } catch (err: any) {
      if (err.name === "AbortError") return;
      content.innerHTML = `<div style="color:#e55; padding:10px;">Failed to load: ${fileName}</div>`;
      return;
    }

    content.innerHTML = "";
    content.style.padding = "0";
    const tableId = "ws-viewer-csv-table";
    const tc = document.createElement("div");
    tc.id = tableId;
    tc.className = "data-table-container";
    tc.style.cssText = "width:100%; height:100%;";
    content.appendChild(tc);

    try {
      this.tableManager = new DataTableManager({
        container: `#${tableId}`,
        readOnly: true,
      });
      this.tableManager.loadFromCSVContent(rawText, fileName);
      this.tableManager.renderEditableDataTable();
      this.tableManager.setupColumnResizing();
    } catch (err) {
      console.error("[CsvViewer] DataTableManager error:", err);
      content.innerHTML = "";
      renderFallbackTable(content, rawText);
    }
  }

  destroy(): void {
    this.abortController?.abort();
    this.abortController = null;
    this.tableManager = null;
  }
}

/** Simple fallback if DataTableManager fails to render. */
function renderFallbackTable(container: HTMLElement, rawText: string): void {
  const rows = rawText.split(/\r?\n/).filter((l) => l.trim());
  if (rows.length === 0) {
    container.innerHTML =
      '<div style="color:#888; padding:10px;">Empty file</div>';
    return;
  }
  const table = document.createElement("table");
  table.style.cssText =
    "border-collapse:collapse; font-size:0.85em; white-space:nowrap;";
  for (let i = 0; i < rows.length; i++) {
    const tr = document.createElement("tr");
    const cells = rows[i].split(",");
    for (const cell of cells) {
      const el = document.createElement(i === 0 ? "th" : "td");
      el.textContent = cell;
      el.style.cssText =
        "padding:3px 8px; border:1px solid #333;" +
        (i === 0 ? "background:#2a2a2a; font-weight:600;" : "");
      tr.appendChild(el);
    }
    table.appendChild(tr);
  }
  container.appendChild(table);
}
