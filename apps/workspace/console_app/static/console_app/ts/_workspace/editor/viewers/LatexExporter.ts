/**
 * LaTeX Exporter
 * Generates LaTeX table code from CSV content and displays in modal
 */

export class LatexExporter {
  /**
   * Show LaTeX export panel
   */
  show(content: string, filePath: string): void {
    const latexCode = this.generateLatexTable(content, filePath);
    this.showModal(latexCode);
  }

  /**
   * Generate LaTeX table code from CSV content
   * All rows are treated as data (no header detection)
   */
  private generateLatexTable(content: string, filePath: string): string {
    const delimiter = filePath.toLowerCase().endsWith('.tsv') ? '\t' : ',';
    const lines = content.trim().split('\n');
    if (lines.length === 0) return '';

    const firstRow = this.parseCSVLine(lines[0], delimiter);
    const colCount = firstRow.length;

    // Generate column alignment (right-aligned for numbers)
    const colAlign = Array(colCount).fill('r').join('');

    let latex = `\\begin{table}[htbp]\n`;
    latex += `  \\centering\n`;
    latex += `  \\caption{${filePath.split('/').pop()?.replace('.csv', '').replace('.tsv', '') || 'Data'}}\n`;
    latex += `  \\begin{tabular}{${colAlign}}\n`;
    latex += `    \\toprule\n`;

    // All rows are data (no header row)
    for (let i = 0; i < lines.length; i++) {
      const row = this.parseCSVLine(lines[i], delimiter);
      latex += `    ${row.map(v => this.escapeLatex(v.trim())).join(' & ')} \\\\\n`;
    }

    latex += `    \\bottomrule\n`;
    latex += `  \\end{tabular}\n`;
    latex += `\\end{table}`;

    return latex;
  }

  /**
   * Escape special LaTeX characters
   */
  private escapeLatex(text: string): string {
    return text
      .replace(/\\/g, '\\textbackslash{}')
      .replace(/&/g, '\\&')
      .replace(/%/g, '\\%')
      .replace(/\$/g, '\\$')
      .replace(/#/g, '\\#')
      .replace(/_/g, '\\_')
      .replace(/\{/g, '\\{')
      .replace(/\}/g, '\\}')
      .replace(/~/g, '\\textasciitilde{}')
      .replace(/\^/g, '\\textasciicircum{}');
  }

  /**
   * Parse a single CSV line handling quoted fields
   */
  private parseCSVLine(line: string, delimiter: string): string[] {
    const result: string[] = [];
    let currentValue = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      const nextChar = line[i + 1];

      if (inQuotes) {
        if (char === '"' && nextChar === '"') {
          currentValue += '"';
          i++;
        } else if (char === '"') {
          inQuotes = false;
        } else {
          currentValue += char;
        }
      } else {
        if (char === '"') {
          inQuotes = true;
        } else if (char === delimiter) {
          result.push(currentValue);
          currentValue = '';
        } else {
          currentValue += char;
        }
      }
    }
    result.push(currentValue);

    return result;
  }

  /**
   * Escape HTML special characters
   */
  private escapeHtml(text: string): string {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show LaTeX code in a modal with copy functionality
   */
  private showModal(latexCode: string): void {
    // Create modal overlay
    const overlay = document.createElement("div");
    overlay.className = "latex-modal-overlay";
    overlay.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10000;
    `;

    const modal = document.createElement("div");
    modal.className = "latex-modal";
    modal.style.cssText = `
      background: var(--workspace-bg-secondary, #1e2228);
      border: 1px solid var(--color-border-default, #30363d);
      border-radius: 8px;
      padding: 16px;
      width: 600px;
      max-width: 90vw;
      max-height: 80vh;
      display: flex;
      flex-direction: column;
    `;

    modal.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h3 style="margin: 0; font-size: 16px; color: var(--color-fg-default, #c9d1d9);">
          <i class="fas fa-file-code"></i> LaTeX Table
        </h3>
        <button id="latex-modal-close" style="background: transparent; border: none; color: var(--color-fg-muted, #8b949e); cursor: pointer; font-size: 18px;">
          <i class="fas fa-times"></i>
        </button>
      </div>
      <textarea id="latex-code-textarea" style="
        flex: 1;
        min-height: 300px;
        padding: 12px;
        background: var(--workspace-bg-tertiary, #161b22);
        border: 1px solid var(--color-border-default, #30363d);
        border-radius: 4px;
        color: var(--color-fg-default, #c9d1d9);
        font-family: var(--font-mono, 'JetBrains Mono', Monaco, monospace);
        font-size: 12px;
        resize: none;
      ">${this.escapeHtml(latexCode)}</textarea>
      <div style="display: flex; gap: 8px; margin-top: 12px; justify-content: flex-end;">
        <button id="latex-copy-btn" class="csv-control-btn" style="background: var(--color-accent, #238636); border-color: var(--color-accent, #238636); color: #fff;">
          <i class="fas fa-copy"></i> Copy to Clipboard
        </button>
      </div>
    `;

    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // Close button
    document.getElementById("latex-modal-close")?.addEventListener("click", () => {
      overlay.remove();
    });

    // Click outside to close
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.remove();
      }
    });

    // Copy button
    document.getElementById("latex-copy-btn")?.addEventListener("click", async () => {
      const textarea = document.getElementById("latex-code-textarea") as HTMLTextAreaElement;
      try {
        await navigator.clipboard.writeText(textarea.value);
        const btn = document.getElementById("latex-copy-btn");
        if (btn) {
          btn.innerHTML = '<i class="fas fa-check"></i> Copied!';
          setTimeout(() => {
            btn.innerHTML = '<i class="fas fa-copy"></i> Copy to Clipboard';
          }, 2000);
        }
      } catch (err) {
        textarea.select();
        document.execCommand("copy");
      }
    });

    // Escape to close
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        overlay.remove();
        document.removeEventListener("keydown", handleEscape);
      }
    };
    document.addEventListener("keydown", handleEscape);
  }
}
