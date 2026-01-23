/**
 * Preview Panel Manager
 * Main manager class that orchestrates all preview panel functionality
 *
 * @version 2.0.0 (TypeScript)
 * @author SciTeX Development Team
 */

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/apps/writer_app/static/writer_app/ts/editor/preview-panel/manager.ts loaded",
);

import type { PreviewPanelConfig } from "./types";
import { LATEX_TEMPLATES } from "./types";
import { PreviewRenderer } from "./rendering";
import { PreviewNavigation } from "./navigation";
import { PreviewSync } from "./sync";

export class PreviewPanelManager {
  private config: PreviewPanelConfig;
  private editor: any; // CodeMirror instance
  private saveTimeout: ReturnType<typeof setTimeout> | null = null;

  // Sub-managers
  private renderer!: PreviewRenderer;
  private navigation!: PreviewNavigation;
  private sync!: PreviewSync;

  // DOM elements
  private compileBtn!: HTMLButtonElement;
  private saveBtn!: HTMLButtonElement;
  private statusIndicator!: HTMLElement;
  private compileStatus!: HTMLElement;
  private previewContent!: HTMLElement;
  private previewPanel!: HTMLElement;
  private togglePreviewBtn!: HTMLButtonElement;
  private templateSelect!: HTMLSelectElement;
  private documentTitle!: HTMLInputElement;

  constructor(config: PreviewPanelConfig) {
    this.config = config;
  }

  /**
   * Initialize the preview panel manager
   */
  initialize(): void {
    console.log("[PreviewPanel] Initializing preview panel manager");

    // Initialize CodeMirror editor
    this.initializeEditor();

    // Get DOM elements
    this.getDOMElements();

    // Initialize sub-managers
    this.initializeSubManagers();

    // Setup event listeners
    this.setupEventListeners();

    console.log("[PreviewPanel] Initialization complete");
  }

  /**
   * Initialize CodeMirror editor
   */
  private initializeEditor(): void {
    const textarea = document.getElementById(
      "latex-editor",
    ) as HTMLTextAreaElement;
    if (!textarea) {
      console.error("[PreviewPanel] LaTeX editor textarea not found");
      return;
    }

    if (!(window as any).CodeMirror) {
      console.error("[PreviewPanel] CodeMirror not loaded");
      return;
    }

    this.editor = (window as any).CodeMirror.fromTextArea(textarea, {
      mode: "stex",
      theme: "github",
      lineNumbers: true,
      autoCloseBrackets: true,
      matchBrackets: true,
      lineWrapping: true,
      indentUnit: 2,
    });

    // Auto-save on content change
    this.editor.on("change", () => {
      this.handleEditorChange();
    });

    console.log("[PreviewPanel] CodeMirror editor initialized");
  }

  /**
   * Get DOM element references
   */
  private getDOMElements(): void {
    this.compileBtn = document.getElementById(
      "compile-btn",
    ) as HTMLButtonElement;
    this.saveBtn = document.getElementById("save-btn") as HTMLButtonElement;
    this.statusIndicator = document.getElementById(
      "status-indicator",
    ) as HTMLElement;
    this.compileStatus = document.getElementById(
      "compile-status",
    ) as HTMLElement;
    this.previewContent = document.getElementById(
      "preview-content",
    ) as HTMLElement;
    this.previewPanel = document.getElementById("preview-panel") as HTMLElement;
    this.togglePreviewBtn = document.getElementById(
      "toggle-preview",
    ) as HTMLButtonElement;
    this.templateSelect = document.getElementById(
      "template-select",
    ) as HTMLSelectElement;
    this.documentTitle = document.getElementById(
      "document-title",
    ) as HTMLInputElement;
  }

  /**
   * Initialize sub-managers
   */
  private initializeSubManagers(): void {
    this.renderer = new PreviewRenderer(
      this.previewContent,
      this.compileStatus,
      this.statusIndicator,
    );

    this.navigation = new PreviewNavigation(
      this.previewPanel,
      this.togglePreviewBtn,
    );

    this.sync = new PreviewSync(this.config, this.renderer, this.compileBtn);
  }

  /**
   * Setup all event listeners
   */
  private setupEventListeners(): void {
    // Template selection
    if (this.templateSelect) {
      this.templateSelect.addEventListener("change", () => {
        this.handleTemplateChange();
      });
    }

    // Save draft
    if (this.saveBtn) {
      this.saveBtn.addEventListener("click", () => {
        this.saveDraft();
      });
    }

    // Compile document
    if (this.compileBtn) {
      this.compileBtn.addEventListener("click", () => {
        this.compileDocument();
      });
    }
  }

  /**
   * Handle template selection change
   */
  private handleTemplateChange(): void {
    const template = this.templateSelect.value;
    if (template && LATEX_TEMPLATES[template]) {
      if (confirm("This will replace your current content. Continue?")) {
        this.editor.setValue(LATEX_TEMPLATES[template]);
        this.documentTitle.value =
          template.charAt(0).toUpperCase() + template.slice(1) + " Document";
      } else {
        this.templateSelect.value = "";
      }
    }
  }

  /**
   * Save draft (auto-save functionality)
   */
  private saveDraft(): void {
    this.renderer.updateStatus("Saving...", "text-warning");
    setTimeout(() => {
      this.renderer.updateStatus("Saved", "text-success");
      setTimeout(() => this.renderer.updateStatus("Ready", "text-success"), 2000);
    }, 500);
  }

  /**
   * Compile LaTeX document to PDF
   */
  private async compileDocument(): Promise<void> {
    const content = this.editor.getValue().trim();
    const title = this.documentTitle.value.trim() || "Quick Document";
    await this.sync.compileDocument(content, title);
  }

  /**
   * Handle editor content change
   */
  private handleEditorChange(): void {
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    this.renderer.updateStatus("Unsaved changes", "text-warning");

    this.saveTimeout = setTimeout(() => {
      this.renderer.updateStatus("Ready", "text-success");
    }, 3000);
  }

  /**
   * Destroy the preview panel manager and cleanup
   */
  destroy(): void {
    if (this.saveTimeout) {
      clearTimeout(this.saveTimeout);
    }

    if (this.sync) {
      this.sync.destroy();
    }

    console.log("[PreviewPanel] Preview panel manager destroyed");
  }
}
