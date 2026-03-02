/**
 * CsvLatexPanel - LaTeX table export panel for CSV data
 *
 * Generates LaTeX table code with booktabs support, caption, and label options.
 * Extracted from CsvEditor.ts for single responsibility.
 */

import type { Dataset, DataRow } from '../../data-table/types';

export interface LatexOptions {
  booktabs?: boolean;
  caption?: boolean;
  label?: boolean;
}

export class CsvLatexPanel {
  private currentFilePath: string | null = null;

  /**
   * Set the current file path (used for default label/filename)
   */
  public setFilePath(filePath: string | null): void {
    this.currentFilePath = filePath;
  }

  /**
   * Render the LaTeX export panel
   */
  public render(panel: HTMLElement, data: Dataset | null): void {
    if (!data || data.rows.length === 0) {
      panel.innerHTML = `
        <div class="csv-latex-empty">
          <i class="fas fa-file-code"></i>
          <p>No data available for LaTeX export</p>
        </div>
      `;
      return;
    }

    const latex = this.generateLatexTable(data.columns, data.rows);

    panel.innerHTML = `
      <div class="csv-latex-panel">
        <h4><i class="fas fa-file-code"></i> LaTeX Table Export</h4>
        <div class="latex-options">
          <label>
            <input type="checkbox" class="latex-opt-booktabs" checked>
            Use booktabs (\\toprule, \\midrule, \\bottomrule)
          </label>
          <label>
            <input type="checkbox" class="latex-opt-caption">
            Include caption
          </label>
          <label>
            <input type="checkbox" class="latex-opt-label">
            Include label
          </label>
        </div>
        <div class="latex-preview-wrapper">
          <textarea class="latex-preview" readonly>${latex}</textarea>
        </div>
        <div class="latex-actions">
          <button class="csv-control-btn latex-copy-btn" title="Copy to clipboard">
            <i class="fas fa-copy"></i> Copy LaTeX
          </button>
          <button class="csv-control-btn latex-download-btn" title="Download as .tex file">
            <i class="fas fa-download"></i> Download .tex
          </button>
        </div>
      </div>
    `;

    // Store data reference for updates
    (panel as any).__latexData = data;

    const updatePreview = () => {
      const booktabs = (panel.querySelector(".latex-opt-booktabs") as HTMLInputElement)?.checked;
      const caption = (panel.querySelector(".latex-opt-caption") as HTMLInputElement)?.checked;
      const label = (panel.querySelector(".latex-opt-label") as HTMLInputElement)?.checked;
      const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
      if (preview) {
        preview.value = this.generateLatexTable(data.columns, data.rows, { booktabs, caption, label });
      }
    };

    // Update preview on option change
    panel.querySelectorAll("input[type=checkbox]").forEach(cb => {
      cb.addEventListener("change", updatePreview);
    });

    // Setup copy button
    const copyBtn = panel.querySelector(".latex-copy-btn");
    copyBtn?.addEventListener("click", () => {
      const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
      if (preview) {
        navigator.clipboard.writeText(preview.value);
        alert('LaTeX table copied to clipboard');
      }
    });

    // Setup download button
    const downloadBtn = panel.querySelector(".latex-download-btn");
    downloadBtn?.addEventListener("click", () => {
      const preview = panel.querySelector(".latex-preview") as HTMLTextAreaElement;
      if (preview) {
        this.downloadTexFile(preview.value);
      }
    });
  }

  /**
   * Generate LaTeX table code from data
   */
  public generateLatexTable(
    columns: string[],
    rows: DataRow[],
    options: LatexOptions = {}
  ): string {
    const { booktabs = true, caption = false, label = false } = options;

    const colSpec = columns.map(() => 'c').join(' ');
    const headerRow = columns.map(c => this.escapeLatex(c)).join(' & ');
    const dataRows = rows.slice(0, 100).map(row =>
      columns.map(col => this.escapeLatex(String(row[col] ?? ''))).join(' & ')
    );

    let latex = '';
    latex += '\\begin{table}[htbp]\n';
    latex += '  \\centering\n';

    if (caption) {
      latex += '  \\caption{Table Caption Here}\n';
    }
    if (label) {
      const baseName = this.getBaseName();
      latex += `  \\label{tab:${baseName}}\n`;
    }

    latex += `  \\begin{tabular}{${colSpec}}\n`;

    if (booktabs) {
      latex += '    \\toprule\n';
      latex += `    ${headerRow} \\\\\n`;
      latex += '    \\midrule\n';
    } else {
      latex += '    \\hline\n';
      latex += `    ${headerRow} \\\\\n`;
      latex += '    \\hline\n';
    }

    for (const row of dataRows) {
      latex += `    ${row} \\\\\n`;
    }

    if (booktabs) {
      latex += '    \\bottomrule\n';
    } else {
      latex += '    \\hline\n';
    }

    latex += '  \\end{tabular}\n';
    latex += '\\end{table}\n';

    if (rows.length > 100) {
      latex += `\n% Note: Table truncated to first 100 rows (original: ${rows.length} rows)\n`;
    }

    return latex;
  }

  /**
   * Download LaTeX content as .tex file
   */
  private downloadTexFile(content: string): void {
    const blob = new Blob([content], { type: 'text/x-latex' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${this.getBaseName()}.tex`;
    a.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Get base name from file path (without extension)
   */
  private getBaseName(): string {
    return this.currentFilePath?.split('/').pop()?.replace(/\.[^.]+$/, '') || 'table';
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
}
