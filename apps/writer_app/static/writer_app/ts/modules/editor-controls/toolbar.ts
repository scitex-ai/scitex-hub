/**
 * Toolbar Handling Module
 * Manages toolbar controls for preview and auto-preview
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/modules/editor-controls/toolbar.ts loaded",
);

export class ToolbarHandler {
  private autoPreviewCheckbox: HTMLInputElement | null;
  private autoPreviewCheckboxPanel: HTMLInputElement | null;
  private previewButton: HTMLButtonElement | null;
  private previewButtonPanel: HTMLButtonElement | null;
  private latexEditor: HTMLTextAreaElement | null;
  private pdfPreviewManager: any;
  private autoPreviewTimeout: ReturnType<typeof setTimeout> | null = null;
  private storageAutoPreviewKey: string = "scitex-auto-preview";

  constructor(
    latexEditor: HTMLTextAreaElement | null,
    pdfPreviewManager: any,
  ) {
    this.autoPreviewCheckbox = document.getElementById(
      "auto-preview-checkbox",
    ) as HTMLInputElement;
    this.autoPreviewCheckboxPanel = document.getElementById(
      "auto-preview-checkbox-panel",
    ) as HTMLInputElement;
    this.previewButton = document.getElementById(
      "preview-btn-toolbar",
    ) as HTMLButtonElement;
    this.previewButtonPanel = document.getElementById(
      "preview-btn-panel",
    ) as HTMLButtonElement;
    this.latexEditor = latexEditor;
    this.pdfPreviewManager = pdfPreviewManager;
  }

  /**
   * Initialize toolbar controls
   */
  public initialize(): void {
    // Auto preview control - toolbar checkbox
    if (this.autoPreviewCheckbox) {
      this.loadAutoPreviewPreference();
      this.autoPreviewCheckbox.addEventListener("change", (e) => {
        this.handleAutoPreviewToggle(e);
        // Sync panel checkbox
        if (this.autoPreviewCheckboxPanel) {
          this.autoPreviewCheckboxPanel.checked = (
            e.target as HTMLInputElement
          ).checked;
        }
      });
      console.log(
        "[ToolbarHandler] Auto preview checkbox (toolbar) initialized",
      );
    }

    // Auto preview control - panel checkbox
    if (this.autoPreviewCheckboxPanel) {
      this.loadAutoPreviewPreference(this.autoPreviewCheckboxPanel);
      this.autoPreviewCheckboxPanel.addEventListener("change", (e) => {
        this.handleAutoPreviewToggle(e);
        // Sync toolbar checkbox
        if (this.autoPreviewCheckbox) {
          this.autoPreviewCheckbox.checked = (
            e.target as HTMLInputElement
          ).checked;
        }
      });
      console.log(
        "[ToolbarHandler] Auto preview checkbox (panel) initialized",
      );
    }

    // Preview button - toolbar
    if (this.previewButton) {
      this.previewButton.addEventListener(
        "click",
        this.handlePreviewClick.bind(this),
      );
      console.log("[ToolbarHandler] Preview button (toolbar) initialized");
    }

    // Preview button - panel
    if (this.previewButtonPanel) {
      this.previewButtonPanel.addEventListener(
        "click",
        this.handlePreviewClick.bind(this),
      );
      console.log("[ToolbarHandler] Preview button (panel) initialized");
    }

    // Setup auto-preview trigger on editor changes
    const autoPreviewEnabled =
      (this.autoPreviewCheckbox && this.autoPreviewCheckbox.checked) ||
      (this.autoPreviewCheckboxPanel && this.autoPreviewCheckboxPanel.checked);
    if (this.latexEditor && autoPreviewEnabled) {
      this.setupAutoPreviewTrigger();
    }
  }

  /**
   * Handle auto preview checkbox toggle
   */
  private handleAutoPreviewToggle(event: Event): void {
    const target = event.target as HTMLInputElement;
    const isEnabled = target.checked;

    // Save preference to localStorage
    localStorage.setItem(
      this.storageAutoPreviewKey,
      isEnabled ? "true" : "false",
    );

    if (isEnabled) {
      this.setupAutoPreviewTrigger();
      console.log("[ToolbarHandler] Auto preview enabled");
    } else {
      this.clearAutoPreviewTimeout();
      console.log("[ToolbarHandler] Auto preview disabled");
    }
  }

  /**
   * Load auto-preview preference from localStorage
   */
  private loadAutoPreviewPreference(
    checkbox: HTMLInputElement | null = null,
  ): void {
    const saved = localStorage.getItem(this.storageAutoPreviewKey);
    const isEnabled = saved !== "false"; // Default to true

    if (checkbox) {
      checkbox.checked = isEnabled;
    } else if (this.autoPreviewCheckbox) {
      this.autoPreviewCheckbox.checked = isEnabled;
    }

    // Sync both checkboxes
    if (this.autoPreviewCheckbox) {
      this.autoPreviewCheckbox.checked = isEnabled;
    }
    if (this.autoPreviewCheckboxPanel) {
      this.autoPreviewCheckboxPanel.checked = isEnabled;
    }
  }

  /**
   * Setup auto-preview trigger on editor changes
   */
  private setupAutoPreviewTrigger(): void {
    if (!this.latexEditor) return;

    this.latexEditor.addEventListener("input", () => {
      // Check if auto-preview is enabled (either checkbox)
      const isEnabled =
        (this.autoPreviewCheckbox && this.autoPreviewCheckbox.checked) ||
        (this.autoPreviewCheckboxPanel &&
          this.autoPreviewCheckboxPanel.checked);
      if (!isEnabled) return;

      // Clear existing timeout
      this.clearAutoPreviewTimeout();

      // Schedule auto-compile after 5 seconds of inactivity
      this.autoPreviewTimeout = setTimeout(() => {
        this.triggerPreview();
      }, 5000); // 5 second delay

      console.log("[ToolbarHandler] Auto-preview scheduled for 5s");
    });
  }

  /**
   * Clear auto-preview timeout
   */
  private clearAutoPreviewTimeout(): void {
    if (this.autoPreviewTimeout) {
      clearTimeout(this.autoPreviewTimeout);
      this.autoPreviewTimeout = null;
    }
  }

  /**
   * Handle preview button click
   */
  private handlePreviewClick(event: Event): void {
    event.preventDefault();
    console.log("[ToolbarHandler] Preview button clicked");
    this.triggerPreview();
  }

  /**
   * Trigger PDF preview compilation
   */
  private triggerPreview(): void {
    if (this.pdfPreviewManager && this.latexEditor) {
      const editorContent = this.latexEditor.value;
      if (editorContent.trim()) {
        console.log("[ToolbarHandler] Triggering PDF preview compilation");
        // Use quick compile for live preview (text only)
        this.pdfPreviewManager.compileQuick(editorContent);
      }
    }
  }

  /**
   * Check if auto-preview is enabled
   */
  public isAutoPreviewEnabled(): boolean {
    return this.autoPreviewCheckbox ? this.autoPreviewCheckbox.checked : false;
  }

  /**
   * Set auto-preview enabled state
   */
  public setAutoPreviewEnabled(enabled: boolean): void {
    if (this.autoPreviewCheckbox) {
      this.autoPreviewCheckbox.checked = enabled;
      const event = new Event("change", { bubbles: true });
      this.autoPreviewCheckbox.dispatchEvent(event);
    }
  }

  /**
   * Set PDF preview manager reference (for dynamic initialization)
   */
  public setPDFPreviewManager(pdfPreviewManager: any): void {
    this.pdfPreviewManager = pdfPreviewManager;
  }
}
