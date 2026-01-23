/**
 * Font Size Formatting Module
 * Handles font size management for all editors
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/editor-controls/formatting.ts loaded",
);

export class FontSizeFormatter {
  private currentFontSize: number = 14;
  private defaultFontSize: number = 14;
  private storageFontSizeKey: string = "scitex-editor-font-size";
  private latexEditor: HTMLTextAreaElement | null;
  private editor: any;
  private pdfPreviewManager: any;

  constructor(
    latexEditor: HTMLTextAreaElement | null,
    editor: any,
    pdfPreviewManager: any,
  ) {
    this.latexEditor = latexEditor;
    this.editor = editor;
    this.pdfPreviewManager = pdfPreviewManager;
  }

  /**
   * Load font size from localStorage
   */
  public loadFontSize(): number {
    const saved = localStorage.getItem(this.storageFontSizeKey);
    let fontSize = saved ? parseInt(saved, 10) : this.defaultFontSize;

    // Ensure minimum font size of 12px for readability
    if (fontSize < 12) {
      console.warn(
        `[FontSizeFormatter] Font size ${fontSize}px is too small, resetting to 12px`,
      );
      fontSize = 12;
      localStorage.setItem(this.storageFontSizeKey, "12");
    }

    this.currentFontSize = fontSize;
    this.applyFontSizeToAllEditors(fontSize);

    console.log(`[FontSizeFormatter] Loaded font size: ${fontSize}px`);
    return fontSize;
  }

  /**
   * Update font size and apply changes
   */
  public updateFontSize(fontSize: number): void {
    this.currentFontSize = fontSize;
    this.applyFontSizeToAllEditors(fontSize);
    localStorage.setItem(this.storageFontSizeKey, fontSize.toString());
    console.log(`[FontSizeFormatter] Font size changed to ${fontSize}px`);
  }

  /**
   * Apply font size to all editors (Monaco, CodeMirror, PDF)
   */
  private applyFontSizeToAllEditors(fontSize: number): void {
    // Update textarea
    if (this.latexEditor) {
      this.latexEditor.style.fontSize = `${fontSize}px`;
    }

    // Update Monaco editor if available
    if (
      this.editor &&
      this.editor.getEditorType &&
      this.editor.getEditorType() === "monaco"
    ) {
      const monacoInstance = this.editor.getInstance();
      if (monacoInstance && monacoInstance.updateOptions) {
        monacoInstance.updateOptions({ fontSize: fontSize });
      }
    }

    // Update CodeMirror if available
    const cmElement = document.querySelector(".CodeMirror") as HTMLElement;
    if (cmElement) {
      cmElement.style.fontSize = `${fontSize}px`;
    }

    // Update PDF compilation font size
    if (this.pdfPreviewManager && this.pdfPreviewManager.setFontSize) {
      this.pdfPreviewManager.setFontSize(fontSize);
    }
  }

  /**
   * Get current font size
   */
  public getFontSize(): number {
    return this.currentFontSize;
  }

  /**
   * Set font size programmatically
   */
  public setFontSize(fontSize: number): void {
    if (fontSize >= 12 && fontSize <= 20) {
      this.updateFontSize(fontSize);
    } else if (fontSize < 12) {
      console.warn(
        `[FontSizeFormatter] Font size ${fontSize}px is too small, using minimum 12px`,
      );
      this.updateFontSize(12);
    }
  }
}
