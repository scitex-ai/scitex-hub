/**
 * Figure Actions Module
 * Handles drag-drop to editor and other figure actions
 */

import type { Figure } from "./figures-list.js";

export class FigureActions {
  constructor() {
    console.log("[FigureActions] Initialized");
  }

  /**
   * Handle drag start - prepare data for editor drop
   */
  handleDragStart(event: DragEvent, figure: Figure): void {
    if (!event.dataTransfer) return;

    const figureKey = figure.label || figure.file_name;
    const figLabel = this.generateFigureLabel(figureKey);
    const latexCode = this.generateLatexCode(figure, figLabel);

    event.dataTransfer.setData("text/plain", latexCode);
    event.dataTransfer.effectAllowed = "copy";

    const target = event.target as HTMLElement;
    target.classList.add("dragging");

    console.log("[FigureActions] Drag started:", figureKey);
  }

  /**
   * Handle drag end - cleanup
   */
  handleDragEnd(event: DragEvent): void {
    const target = event.target as HTMLElement;
    target.classList.remove("dragging");
  }

  /**
   * Generate LaTeX label from figure key
   */
  private generateFigureLabel(figureKey: string): string {
    const cleanKey = figureKey
      .replace(/\.[^/.]+$/, "") // Remove extension
      .replace(/[^a-zA-Z0-9_-]/g, "_"); // Replace special chars with underscore
    return `fig:${cleanKey}`;
  }

  /**
   * Generate LaTeX code for figure
   */
  private generateLatexCode(figure: Figure, figLabel: string): string {
    const caption = figure.caption || "Caption here";
    const width = figure.width ? `${figure.width}\\textwidth` : "0.8\\textwidth";

    return `\\begin{figure}[h]
  \\centering
  \\includegraphics[width=${width}]{${figure.file_path}}
  \\caption{${caption}}
  \\label{${figLabel}}
\\end{figure}`;
  }

  /**
   * Insert figure into editor at cursor
   */
  insertFigureAtCursor(figure: Figure, editor?: any): void {
    const figureKey = figure.label || figure.file_name;
    const figLabel = this.generateFigureLabel(figureKey);
    const latexCode = this.generateLatexCode(figure, figLabel);

    if (editor && typeof editor.insertAtCursor === "function") {
      editor.insertAtCursor(latexCode);
      console.log("[FigureActions] Inserted figure into editor:", figureKey);
    } else {
      console.warn("[FigureActions] No editor available for insertion");
    }
  }

  /**
   * Copy figure LaTeX code to clipboard
   */
  async copyFigureCode(figure: Figure): Promise<boolean> {
    const figureKey = figure.label || figure.file_name;
    const figLabel = this.generateFigureLabel(figureKey);
    const latexCode = this.generateLatexCode(figure, figLabel);

    try {
      await navigator.clipboard.writeText(latexCode);
      console.log("[FigureActions] Copied to clipboard:", figureKey);
      return true;
    } catch (error) {
      console.error("[FigureActions] Failed to copy to clipboard:", error);
      return false;
    }
  }

  /**
   * Generate figure reference code
   */
  generateFigureReference(figure: Figure): string {
    const figureKey = figure.label || figure.file_name;
    const figLabel = this.generateFigureLabel(figureKey);
    return `\\ref{${figLabel}}`;
  }

  /**
   * Copy figure reference to clipboard
   */
  async copyFigureReference(figure: Figure): Promise<boolean> {
    const reference = this.generateFigureReference(figure);

    try {
      await navigator.clipboard.writeText(reference);
      console.log("[FigureActions] Copied reference to clipboard:", reference);
      return true;
    } catch (error) {
      console.error("[FigureActions] Failed to copy reference:", error);
      return false;
    }
  }

  /**
   * Delete figure (placeholder - needs API integration)
   */
  async deleteFigure(
    figure: Figure,
    projectId: string,
  ): Promise<{ success: boolean; error?: string }> {
    // This would need to be implemented with actual API call
    console.log("[FigureActions] Delete figure:", figure.file_name, "Project:", projectId);
    return { success: false, error: "Not implemented" };
  }

  /**
   * Download figure
   */
  downloadFigure(figure: Figure): void {
    const link = document.createElement("a");
    link.href = figure.file_path;
    link.download = figure.file_name;
    link.click();
    console.log("[FigureActions] Downloaded figure:", figure.file_name);
  }
}
