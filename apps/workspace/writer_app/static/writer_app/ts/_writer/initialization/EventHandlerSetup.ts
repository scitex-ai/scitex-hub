/**
 * Event Handler Setup Module
 * Handles setup of global event handlers and window functions
 */

import { statusLamp, setLoadingContent } from "../../modules/index";
// Direct import to avoid circular dependency through barrel re-export
import { handleCompileFull } from "../../utils/compilation-handlers";

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

      if (this.pdfPreviewManager) {
        // Use PDFPreviewManager to display via PDFJSViewer, which updates
        // state.currentPdfUrl — prevents SectionLoading from showing it again
        this.pdfPreviewManager.displayPdfFromUrl(url);
        console.log("[EventHandlerSetup] ✓ Existing PDF loaded in preview");
      } else {
        console.warn(
          "[EventHandlerSetup] pdfPreviewManager not available for existing PDF load",
        );
      }
    });
    console.log("[EventHandlerSetup] ✓ Existing PDF loader attached");
  }

  /**
   * Setup PDF color mode toggle button
   */
  private setupPDFColorModeToggle(): void {
    let isTogglingTheme = false;

    // Create toggle function
    const toggleColorMode = () => {
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
        this.pdfScrollZoomHandler.getColorMode() === "dark" ? "light" : "dark";
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
    };

    // Expose globally for onclick handler
    (window as any).togglePdfColorMode = toggleColorMode;

    // Also attach to button directly for redundancy
    const colorModeBtn = document.getElementById("pdf-color-mode-btn");
    if (colorModeBtn) {
      colorModeBtn.addEventListener("click", toggleColorMode);
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
          // Get content from editor object (works with both Monaco and textarea)
          const content = this.editor?.getContent?.();
          if (content && content.trim()) {
            console.log(
              "[EventHandlerSetup] Triggering PDF preview compilation",
            );
            // forceCompile=true: user clicked compile button
            this.pdfPreviewManager.compileQuick(content, undefined, true);
          } else {
            // Fallback: try textarea directly
            const latexEditor = document.getElementById(
              "latex-editor-textarea",
            ) as HTMLTextAreaElement;
            if (latexEditor && latexEditor.value.trim()) {
              console.log(
                "[EventHandlerSetup] Triggering PDF preview compilation (textarea fallback)",
              );
              // forceCompile=true: user clicked compile button
              this.pdfPreviewManager.compileQuick(
                latexEditor.value,
                undefined,
                true,
              );
            } else {
              console.warn(
                "[EventHandlerSetup] No content available for preview compilation",
              );
            }
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
        handleCompileFull(
          this.compilationManager,
          this.state,
          "manuscript",
          false,
        );
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
      // Guard: onDidChangeModelContent is Monaco-only; CodeMirror uses .on("change")
      if (
        this.editor &&
        this.editor.editor &&
        typeof this.editor.editor.onDidChangeModelContent === "function"
      ) {
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
            handleCompileFull(
              this.compilationManager,
              this.state,
              "manuscript",
              false,
            );
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
    console.log("[EventHandlerSetup] Setting up file tree loader");
    console.log(
      "[EventHandlerSetup] Editor type:",
      this.editor?.getEditorType?.(),
    );
    console.log(
      "[EventHandlerSetup] Editor methods:",
      Object.keys(this.editor || {}),
    );

    window.addEventListener("writer:fileContentLoaded", (event: any) => {
      const { path, content } = event.detail;
      console.log(
        `[EventHandlerSetup] Event received: writer:fileContentLoaded`,
      );
      console.log(
        `[EventHandlerSetup] Path: ${path}, Content length: ${content?.length}`,
      );

      if (!this.editor) {
        console.error("[EventHandlerSetup] Editor is not available!");
        return;
      }

      if (content === undefined) {
        console.error("[EventHandlerSetup] Content is undefined!");
        return;
      }

      try {
        // Set content in the editor.
        // Guard with setLoadingContent to prevent Monaco onChange from
        // triggering auto-save/compile during programmatic content loading.
        console.log("[EventHandlerSetup] Calling editor.setContent()...");
        setLoadingContent(true);
        this.editor.setContent(content);
        // Keep flag set briefly to cover synchronous onChange handlers
        setTimeout(() => setLoadingContent(false), 200);
        console.log(
          `[EventHandlerSetup] ✓ File content loaded into editor: ${path}`,
        );

        // Update state
        if (this.state) {
          this.state.currentFile = path;
          console.log("[EventHandlerSetup] ✓ State updated with current file");
        }

        // NOTE: Do NOT call compileQuick here for section .tex files.
        // SectionLoading.ts handles the initial preview via compileQuick()
        // after loadSectionContent() completes. Calling with the file path
        // as sectionId uses wrong sectionName (e.g. "abstract.tex" vs "abstract")
        // causing 404 HEAD check and unnecessary compilation → flash.
      } catch (error) {
        setLoadingContent(false);
        console.error("[EventHandlerSetup] Error loading file content:", error);
      }
    });
    console.log(
      "[EventHandlerSetup] ✓ File tree loader event listener attached",
    );
  }
}
