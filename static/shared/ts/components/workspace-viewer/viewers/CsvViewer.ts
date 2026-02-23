/**
 * CsvViewer - Fetches CSV content and renders it as an HTML table.
 * Supports a toggle between table view and raw text view.
 * No DataTableManager dependency — simple and self-contained.
 */

import type { Viewer } from "../types.ts";

export class CsvViewer implements Viewer {
  private abortController: AbortController | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const apiUrl = `/console/api/file-content/${filePath}?project_id=${projectId}`;
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
    content.style.cssText = "flex:1; overflow:auto; padding:8px;";
    wrapper.appendChild(content);
    container.appendChild(wrapper);

    content.innerHTML =
      '<div style="color:#888; padding:10px;">Loading...</div>';

    let rawText = "";
    let showRaw = false;

    try {
      const resp = await fetch(apiUrl, { signal: this.abortController.signal });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      rawText = await resp.text();
    } catch (err: any) {
      if (err.name === "AbortError") return;
      content.innerHTML = `<div style="color:#e55; padding:10px;">Failed to load: ${fileName}</div>`;
      return;
    }

    const renderTable = () => {
      content.innerHTML = "";
      const rows = parseCsv(rawText);
      if (rows.length === 0) {
        content.innerHTML =
          '<div style="color:#888; padding:10px;">Empty file</div>';
        return;
      }
      const table = document.createElement("table");
      table.style.cssText =
        "border-collapse:collapse; font-size:0.85em; white-space:nowrap;";

      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");
      for (const cell of rows[0]) {
        const th = document.createElement("th");
        th.textContent = cell;
        th.style.cssText =
          "padding:4px 8px; border:1px solid #444; background:#2a2a2a; font-weight:600; position:sticky; top:0;";
        headerRow.appendChild(th);
      }
      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");
      for (let i = 1; i < rows.length; i++) {
        const tr = document.createElement("tr");
        for (const cell of rows[i]) {
          const td = document.createElement("td");
          td.textContent = cell;
          td.style.cssText = "padding:3px 8px; border:1px solid #333;";
          tr.appendChild(td);
        }
        tbody.appendChild(tr);
      }
      table.appendChild(tbody);
      content.appendChild(table);
    };

    const renderRaw = () => {
      content.innerHTML = "";
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
  }
}

/**
 * Parse CSV text into a 2D array of strings.
 * Handles double-quoted fields containing commas and escaped quotes.
 */
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    if (line.trim() === "") continue;
    rows.push(parseCsvLine(line));
  }
  return rows;
}

function parseCsvLine(line: string): string[] {
  const fields: string[] = [];
  let field = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
    } else {
      if (ch === '"') {
        inQuotes = true;
      } else if (ch === ",") {
        fields.push(field);
        field = "";
      } else {
        field += ch;
      }
    }
  }
  fields.push(field);
  return fields;
}
