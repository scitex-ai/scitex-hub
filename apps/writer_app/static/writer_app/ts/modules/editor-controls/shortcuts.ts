/**
 * Keyboard Shortcuts Module
 * Handles Ctrl+Wheel and keyboard shortcuts for font size
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/editor-controls/shortcuts.ts loaded",
);

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
   * Setup Ctrl+Mouse wheel for font size adjustment
   */
  public setupFontSizeDrag(getCurrentFontSize: () => number): void {
    const editorContainer = document.querySelector(".latex-panel");
    if (!editorContainer) {
      console.warn(
        "[ShortcutsHandler] Editor container not found for font size control",
      );
      return;
    }

    // Listen on document level with capture to intercept early
    document.addEventListener(
      "wheel",
      (e: Event) => {
        const wheelEvent = e as WheelEvent;

        console.log(
          "[ShortcutsHandler] Wheel event - Ctrl pressed:",
          wheelEvent.ctrlKey,
        );

        // Only handle when Ctrl is pressed
        if (!wheelEvent.ctrlKey) return;

        // Check if we're over the editor panel (not the PDF panel)
        const target = wheelEvent.target as HTMLElement;
        const pdfPanel = document.querySelector(".preview-panel");

        console.log(
          "[ShortcutsHandler] Ctrl+Wheel detected - target:",
          target.className,
          "tagName:",
          target.tagName,
        );
        console.log(
          "[ShortcutsHandler] Is over PDF panel:",
          pdfPanel?.contains(target),
        );
        console.log(
          "[ShortcutsHandler] Is over editor panel:",
          editorContainer.contains(target),
        );

        // If over PDF panel, ignore (let PDF zoom handler take it)
        if (pdfPanel && pdfPanel.contains(target)) {
          console.log(
            "[ShortcutsHandler] Over PDF - skipping font size adjustment",
          );
          return;
        }

        // If not over editor panel, ignore
        if (!editorContainer.contains(target)) {
          console.log("[ShortcutsHandler] Not over editor - skipping");
          return;
        }

        console.log(
          "[ShortcutsHandler] Ctrl+Wheel over editor - adjusting font size",
        );

        // Prevent default zoom behavior and stop propagation
        e.preventDefault();
        e.stopPropagation();

        // Get current font size
        const currentFontSize = getCurrentFontSize();

        // Calculate new font size based on wheel direction
        const delta = wheelEvent.deltaY > 0 ? -1 : 1; // Scroll down = decrease, up = increase
        const newFontSize = Math.max(10, Math.min(20, currentFontSize + delta));

        if (newFontSize !== currentFontSize) {
          this.onFontSizeChange(newFontSize);
          console.log(
            "[ShortcutsHandler] Font size changed via Ctrl+Wheel:",
            currentFontSize,
            "→",
            newFontSize,
          );
        }
      },
      { passive: false, capture: true },
    ); // Use capture phase to intercept very early

    console.log(
      "[ShortcutsHandler] Ctrl+Wheel font size adjustment enabled on editor (document-level listener)",
    );

    // Add keyboard shortcuts for font size - only when cursor is in editor
    // This allows browser zoom (Ctrl+0, Ctrl++, Ctrl+-) to work globally
    document.addEventListener(
      "keydown",
      (e: KeyboardEvent) => {
        if (!e.ctrlKey && !e.metaKey) return;

        // Check if focus is in the editor area
        const activeElement = document.activeElement;
        const isInEditor =
          activeElement === this.latexEditor ||
          activeElement?.closest(".latex-panel") !== null ||
          activeElement?.classList?.contains("CodeMirror") ||
          activeElement?.closest(".CodeMirror") !== null ||
          activeElement?.classList?.contains("monaco-editor") ||
          activeElement?.closest(".monaco-editor") !== null;

        // If not in editor, let browser handle zoom shortcuts
        if (!isInEditor) {
          return;
        }

        const currentFontSize = getCurrentFontSize();
        let newFontSize = currentFontSize;

        // Ctrl+Plus: increase font size
        if (e.key === "+" || e.key === "=") {
          e.preventDefault();
          e.stopPropagation();
          newFontSize = Math.min(20, currentFontSize + 1);
          console.log(
            "[ShortcutsHandler] Ctrl++ font size increase (editor focused)",
          );
        }
        // Ctrl+Minus: decrease font size
        else if (e.key === "-" || e.key === "_") {
          e.preventDefault();
          e.stopPropagation();
          newFontSize = Math.max(10, currentFontSize - 1);
          console.log(
            "[ShortcutsHandler] Ctrl+- font size decrease (editor focused)",
          );
        }
        // Note: Ctrl+0 is reserved for browser zoom - don't intercept it

        if (newFontSize !== currentFontSize) {
          this.onFontSizeChange(newFontSize);
        }
      },
      true,
    ); // Use capture phase to catch events before they reach iframe

    console.log(
      "[ShortcutsHandler] Font size keyboard shortcuts enabled (Ctrl+/-, only when editor is focused; Ctrl+0 reserved for browser zoom)",
    );
  }
}
