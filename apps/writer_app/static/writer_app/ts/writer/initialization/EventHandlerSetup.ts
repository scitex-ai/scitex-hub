/**
 * Event Handler Setup Module
 * Handles setup of global event handlers and window functions
 */

import { statusLamp } from "../../modules/index.js";
import { handleCompileFull } from "../../utils/index.js";

export class EventHandlerSetup {
  private state: any;
  private editor: any;
  private pdfPreviewManager: any;
  private pdfScrollZoomHandler: any;
  private compilationManager: any;

  constructor(
    state: any,
    editor: any,
    pdfPreviewManager: any,
    pdfScrollZoomHandler: any,
    compilationManager: any,
  ) {
    this.state = state;
    this.editor = editor;
    this.pdfPreviewManager = pdfPreviewManager;
    this.pdfScrollZoomHandler = pdfScrollZoomHandler;
    this.compilationManager = compilationManager;
  }

  /**
   * Setup all event handlers
   */
  setupAll(): void {
    this.setupPDFColorModeToggle();
    this.setupPreviewHandlers();
    this.setupAutoFullCompile();
    this.setupFileTreeLoader();
    this.setupExistingPDFLoader();
  }

  /**
   * Setup handler for loading existing PDF on page start
   */
  private setupExistingPDFLoader(): void {
    window.addEventListener("writer:loadExistingPDF", (event: any) => {
      const { url } = event.detail;
      console.log("[EventHandlerSetup] Loading existing PDF:", url);

      const textPreview = document.getElementById("text-preview");
      if (!textPreview) {
        console.warn("[EventHandlerSetup] text-preview element not found");
        return;
      }

      // Display the PDF using PDF.js canvas (same approach as PDFViewer)
      textPreview.innerHTML = `
        <div class="pdf-preview-container" style="height: 100%; width: 100%;">
          <div class="pdf-preview-viewer" id="pdf-viewer-pane" style="height: 100%; width: 100%;">
            <iframe
              src="${url}#toolbar=0&navpanes=0&scrollbar=1&view=FitW&zoom=page-width"
              type="application/pdf"
              width="100%"
              height="100%"
              title="PDF Preview"
              frameborder="0"
              style="display: block;">
            </iframe>
          </div>
        </div>
      `;
      console.log("[EventHandlerSetup] ✓ Existing PDF loaded in preview");
    });
    console.log("[EventHandlerSetup] ✓ Existing PDF loader attached");
  }

  /**
   * Setup PDF color mode toggle button
   */
  private setupPDFColorModeToggle(): void {
    const colorModeBtn = document.getElementById("pdf-color-mode-btn");
    let isTogglingTheme = false;

    if (colorModeBtn) {
      colorModeBtn.addEventListener("click", () => {
        // Prevent rapid clicking
        if (isTogglingTheme) {
          console.log(
            "[EventHandlerSetup] Theme toggle in progress, ignoring click",
          );
          return;
        }

        isTogglingTheme = true;

        // Toggle color mode
        const newMode =
          this.pdfScrollZoomHandler.getColorMode() === "dark"
            ? "light"
            : "dark";
        console.log("[EventHandlerSetup] PDF color mode switching to:", newMode);

        // Update handler state and button
        this.pdfScrollZoomHandler.setColorMode(newMode);

        // Immediately switch PDF display (pass content for compilation if needed)
        const currentContent = this.editor?.getContent();
        const currentSection = this.state?.currentSection;
        this.pdfPreviewManager.setColorMode(
          newMode,
          currentContent,
          currentSection,
        );

        // Allow next toggle after short delay
        setTimeout(() => {
          isTogglingTheme = false;
        }, 500);
      });
    }
  }

  /**
   * Setup preview and compilation handlers
   */
  private setupPreviewHandlers(): void {
    // Expose preview functionality globally
    (window as any).handlePreviewClick = (): void => {
      // Check current status
      const currentStatus = statusLamp.getPreviewStatus();

      if (currentStatus === "compiling") {
        // Stop compilation
        console.log("[EventHandlerSetup] Stopping preview compilation");
        if (this.pdfPreviewManager) {
          // Set status to idle/ready
          statusLamp.setPreviewStatus("idle");
        }
      } else {
        // Start compilation
        if (this.pdfPreviewManager) {
          const latexEditor = document.getElementById(
            "latex-editor-textarea",
          ) as HTMLTextAreaElement;
          if (latexEditor && latexEditor.value.trim()) {
            console.log(
              "[EventHandlerSetup] Triggering PDF preview compilation",
            );
            this.pdfPreviewManager.compileQuick(latexEditor.value);
          }
        }
      }
    };

    // Expose full compile functionality globally
    (window as any).handleFullCompileClick = (): void => {
      // Check current status
      const currentStatus = statusLamp.getFullCompileStatus();

      if (currentStatus === "compiling") {
        // Stop compilation
        console.log("[EventHandlerSetup] Stopping full compilation");
        // Set status to idle/ready
        statusLamp.setFullCompileStatus("idle");
      } else {
        // Start compilation
        console.log("[EventHandlerSetup] Full compilation button clicked");
        handleCompileFull(this.compilationManager, this.state, "manuscript", true);
      }
    };
  }

  /**
   * Setup auto-full-compilation feature
   */
  private setupAutoFullCompile(): void {
    let autoFullCompileTimeout: ReturnType<typeof setTimeout> | null = null;
    const autoFullCompileCheckbox = document.getElementById(
      "auto-fullcompile-checkbox",
    ) as HTMLInputElement;

    if (autoFullCompileCheckbox) {
      // Load saved preference
      const savedAutoFull = localStorage.getItem("scitex-auto-fullcompile");
      autoFullCompileCheckbox.checked = savedAutoFull === "true"; // Default off

      // Save preference on change
      autoFullCompileCheckbox.addEventListener("change", () => {
        localStorage.setItem(
          "scitex-auto-fullcompile",
          autoFullCompileCheckbox.checked.toString(),
        );
        console.log(
          "[EventHandlerSetup] Auto-full-compile:",
          autoFullCompileCheckbox.checked,
        );
      });

      // Setup debounced auto-full-compilation on editor changes
      if (this.editor && this.editor.editor) {
        this.editor.editor.onDidChangeModelContent(() => {
          if (!autoFullCompileCheckbox.checked) return;

          // Clear existing timeout
          if (autoFullCompileTimeout) {
            clearTimeout(autoFullCompileTimeout);
          }

          // Schedule full compilation after 15 seconds of inactivity
          autoFullCompileTimeout = setTimeout(() => {
            console.log(
              "[EventHandlerSetup] Auto-full-compile: Triggering compilation after 15s",
            );
            handleCompileFull(this.compilationManager, this.state, "manuscript", false);
          }, 15000); // 15 seconds
        });
      }
    }
  }

  /**
   * Setup file tree content loader
   * Listens for file selection from the file tree and loads content into Monaco editor
   */
  private setupFileTreeLoader(): void {
    console.log('[EventHandlerSetup] Setting up file tree loader');
    console.log('[EventHandlerSetup] Editor type:', this.editor?.getEditorType?.());
    console.log('[EventHandlerSetup] Editor methods:', Object.keys(this.editor || {}));

    window.addEventListener('writer:fileContentLoaded', (event: any) => {
      const { path, content } = event.detail;
      console.log(`[EventHandlerSetup] Event received: writer:fileContentLoaded`);
      console.log(`[EventHandlerSetup] Path: ${path}, Content length: ${content?.length}`);

      if (!this.editor) {
        console.error('[EventHandlerSetup] Editor is not available!');
        return;
      }

      if (content === undefined) {
        console.error('[EventHandlerSetup] Content is undefined!');
        return;
      }

      try {
        // Set content in the editor
        console.log('[EventHandlerSetup] Calling editor.setContent()...');
        this.editor.setContent(content);
        console.log(`[EventHandlerSetup] ✓ File content loaded into editor: ${path}`);

        // Update state
        if (this.state) {
          this.state.currentFile = path;
          console.log('[EventHandlerSetup] ✓ State updated with current file');
        }

        // Trigger quick preview compilation for .tex files
        if (path.endsWith('.tex') && this.pdfPreviewManager) {
          console.log(`[EventHandlerSetup] Triggering preview compilation for: ${path}`);
          setTimeout(() => {
            this.pdfPreviewManager.compileQuick(content, path);
          }, 300);
        }
      } catch (error) {
        console.error('[EventHandlerSetup] Error loading file content:', error);
      }
    });
    console.log('[EventHandlerSetup] ✓ File tree loader event listener attached');
  }
}
