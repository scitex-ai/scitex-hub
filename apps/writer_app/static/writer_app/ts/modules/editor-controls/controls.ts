/**
 * Main Editor Controls Class
 * Coordinates font size management and auto-preview functionality
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/editor-controls/controls.ts loaded",
);

import { FontSizeFormatter } from "./formatting.js";
import { ToolbarHandler } from "./toolbar.js";
import { ShortcutsHandler } from "./shortcuts.js";

export interface EditorControlsOptions {
  pdfPreviewManager?: any;
  compilationManager?: any;
  editor?: any;
}

export class EditorControls {
  private fontSizeSelect: HTMLSelectElement | null;
  private latexEditor: HTMLTextAreaElement | null;
  private fontSizeFormatter: FontSizeFormatter;
  private toolbarHandler: ToolbarHandler;
  private shortcutsHandler: ShortcutsHandler;
  // @ts-ignore - compilation manager available for future use
  private _compilationManager: any;

  constructor(options: EditorControlsOptions = {}) {
    // Get DOM elements
    this.fontSizeSelect = document.getElementById(
      "font-size-select",
    ) as HTMLSelectElement;
    this.latexEditor = document.getElementById(
      "latex-editor-textarea",
    ) as HTMLTextAreaElement;

    // Initialize modules
    this.fontSizeFormatter = new FontSizeFormatter(
      this.latexEditor,
      options.editor,
      options.pdfPreviewManager,
    );

    this.toolbarHandler = new ToolbarHandler(
      this.latexEditor,
      options.pdfPreviewManager,
    );

    this.shortcutsHandler = new ShortcutsHandler(
      this.latexEditor,
      this.setFontSize.bind(this),
    );

    this._compilationManager = options.compilationManager;

    // Initialize if elements exist
    if (this.fontSizeSelect || this.latexEditor) {
      this.initialize();
    }
  }

  /**
   * Initialize editor controls with event listeners
   */
  private initialize(): void {
    // Font size dropdown
    if (this.fontSizeSelect) {
      const loadedFontSize = this.fontSizeFormatter.loadFontSize();
      this.fontSizeSelect.value = loadedFontSize.toString();

      // Listen to dropdown changes
      this.fontSizeSelect.addEventListener("change", () => {
        const newSize = parseInt(this.fontSizeSelect!.value, 10);
        this.setFontSize(newSize);
        console.log(
          `[EditorControls] Font size changed to ${newSize}px via dropdown`,
        );
      });

      console.log("[EditorControls] Font size dropdown initialized");
    }

    // Setup toolbar controls (auto-preview, preview buttons)
    this.toolbarHandler.initialize();

    // Setup keyboard shortcuts (Ctrl+Wheel, Ctrl+/-)
    this.shortcutsHandler.setupFontSizeDrag(() => this.getFontSize());

    console.log("[EditorControls] All controls initialized");
  }

  /**
   * Set PDF preview manager reference (for dynamic initialization)
   */
  public setPDFPreviewManager(pdfPreviewManager: any): void {
    this.toolbarHandler.setPDFPreviewManager(pdfPreviewManager);
  }

  /**
   * Set compilation manager reference (for dynamic initialization)
   */
  public setCompilationManager(compilationManager: any): void {
    this._compilationManager = compilationManager;
  }

  /**
   * Get current font size
   */
  public getFontSize(): number {
    return this.fontSizeFormatter.getFontSize();
  }

  /**
   * Set font size programmatically
   */
  public setFontSize(fontSize: number): void {
    this.fontSizeFormatter.setFontSize(fontSize);

    // Update dropdown if it exists
    if (this.fontSizeSelect) {
      this.fontSizeSelect.value = fontSize.toString();
    }
  }

  /**
   * Check if auto-preview is enabled
   */
  public isAutoPreviewEnabled(): boolean {
    return this.toolbarHandler.isAutoPreviewEnabled();
  }

  /**
   * Set auto-preview enabled state
   */
  public setAutoPreviewEnabled(enabled: boolean): void {
    this.toolbarHandler.setAutoPreviewEnabled(enabled);
  }
}
