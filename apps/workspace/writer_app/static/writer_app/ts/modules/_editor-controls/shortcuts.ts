/**
 * Keyboard Shortcuts Module
 * Handles Ctrl+Wheel and keyboard shortcuts for font size
 */

export class ShortcutsHandler {
  private latexEditor: HTMLTextAreaElement | null;
  private onFontSizeChange: (newSize: number) => void;

  constructor(
    latexEditor: HTMLTextAreaElement | null,
    onFontSizeChange: (newSize: number) => void,
  ) {
    this.latexEditor = latexEditor;
    this.onFontSizeChange = onFontSizeChange;
  }

  /**
   * Setup Ctrl+Mouse wheel for font size adjustment (editor only)
   * PDF panel has its own Ctrl+wheel handler in PDFEventHandlers
   */
  public setupFontSizeDrag(getCurrentFontSize: () => number): void {
    const editorContainer = document.querySelector(".latex-panel");
    if (!editorContainer) {
      console.warn("[ShortcutsHandler] Editor container not found");
      return;
    }

    // Ctrl+wheel on editor: adjust font size
    document.addEventListener(
      "wheel",
      (e: Event) => {
        const wheelEvent = e as WheelEvent;
        if (!wheelEvent.ctrlKey) return;

        const target = wheelEvent.target as HTMLElement;

        // Skip if over PDF panel (PDFEventHandlers handles it)
        const pdfPanel = document.querySelector(".preview-panel");
        if (pdfPanel && pdfPanel.contains(target)) return;

        // Skip if not over editor panel
        if (!editorContainer.contains(target)) return;

        e.preventDefault();
        e.stopPropagation();

        const currentFontSize = getCurrentFontSize();
        const delta = wheelEvent.deltaY > 0 ? -1 : 1;
        const newFontSize = Math.max(10, Math.min(20, currentFontSize + delta));

        if (newFontSize !== currentFontSize) {
          this.onFontSizeChange(newFontSize);
        }
      },
      { passive: false, capture: true },
    );

    // Keyboard shortcuts: Ctrl+/- for font size, Ctrl+0 to reset
    document.addEventListener(
      "keydown",
      (e: KeyboardEvent) => {
        if (!e.ctrlKey && !e.metaKey) return;

        // Skip if cursor is over PDF panel (PDFEventHandlers handles it)
        const pdfPanel = document.querySelector(".preview-panel");
        if (pdfPanel && pdfPanel.matches(":hover")) return;

        // Only handle when editor is focused
        const activeElement = document.activeElement;
        const isInEditor =
          activeElement === this.latexEditor ||
          activeElement?.closest(".latex-panel") !== null ||
          activeElement?.closest(".CodeMirror") !== null ||
          activeElement?.closest(".monaco-editor") !== null;

        if (!isInEditor) return;

        const currentFontSize = getCurrentFontSize();
        let newFontSize = currentFontSize;

        if (e.key === "+" || e.key === "=") {
          e.preventDefault();
          e.stopPropagation();
          newFontSize = Math.min(20, currentFontSize + 1);
        } else if (e.key === "-" || e.key === "_") {
          e.preventDefault();
          e.stopPropagation();
          newFontSize = Math.max(10, currentFontSize - 1);
        } else if (e.key === "0") {
          e.preventDefault();
          e.stopPropagation();
          newFontSize = 14; // Default font size
        }

        if (newFontSize !== currentFontSize) {
          this.onFontSizeChange(newFontSize);
        }
      },
      true,
    );
  }
}
