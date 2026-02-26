/**
 * CsvViewer - Uses the shared DataTableManager for rich spreadsheet rendering.
 * Supports table view (with selection, copy/paste, column resize) and raw text toggle.
 */

import type { Viewer } from "../types.ts";
import { getFileUrl } from "../file-loader.ts";
import { DataTableManager } from "../../data-table/DataTableManager.ts";

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

    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "display:flex; flex-direction:column; height:100%; overflow:hidden;";

    const toolbar = document.createElement("div");
    toolbar.style.cssText =
      "display:flex; align-items:center; gap:8px; padding:6px 10px; border-bottom:1px solid #333; flex-shrink:0; font-size:0.85em;";

    const nameSpan = document.createElement("span");
    nameSpan.style.cssText = "color:#888; margin-right:auto;";
    nameSpan.title = filePath;
    nameSpan.textContent = fileName;

    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = "Raw";
    toggleBtn.style.cssText =
      "cursor:pointer; padding:2px 8px; font-size:0.85em;";

    toolbar.appendChild(nameSpan);
    toolbar.appendChild(toggleBtn);
    wrapper.appendChild(toolbar);

    const content = document.createElement("div");
    content.style.cssText = "flex:1; overflow:auto; padding:0;";
    wrapper.appendChild(content);
    container.appendChild(wrapper);

    // Table container needs a unique ID for DataTableManager
    const tableId = "ws-viewer-csv-table";
    const tableContainer = document.createElement("div");
    tableContainer.id = tableId;
    tableContainer.className = "data-table-container";
    tableContainer.style.cssText = "width:100%; height:100%;";
    content.appendChild(tableContainer);

    content.innerHTML =
      '<div style="color:#888; padding:10px;">Loading...</div>';

    let rawText = "";
    let showRaw = false;

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

    const renderTable = () => {
      content.innerHTML = "";
      content.style.padding = "0";
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
    };

    const renderRaw = () => {
      content.innerHTML = "";
      content.style.padding = "8px";
      const pre = document.createElement("pre");
      pre.style.cssText =
        "margin:0; font-size:0.85em; white-space:pre; color:#ccc;";
      pre.textContent = rawText;
      content.appendChild(pre);
    };

    renderTable();

    toggleBtn.addEventListener("click", () => {
      showRaw = !showRaw;
      toggleBtn.textContent = showRaw ? "Table" : "Raw";
      if (showRaw) renderRaw();
      else renderTable();
    });
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
