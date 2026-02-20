/**
 * PDF Preview Manager
 * Main class coordinating PDF preview functionality
 */

import { CompilationManager } from "../compilation";
import { LatexWrapper } from "../latex-wrapper";
import { PDFViewer } from "./viewer";
import { ZoomController } from "./zoom";
import { EventHandler } from "./events";
import { CompilationHandler } from "./compilation";
import { ColorModeManager } from "./color-mode";

export interface PDFPreviewOptions {
  containerId: string;
  projectId: number;
  manuscriptTitle: string;
  author?: string;
  autoCompile?: boolean;
  compileDelay?: number;
  apiBaseUrl?: string;
  docType?: string;
  renderQuality?: number;
}

export class PDFPreviewManager {
  private viewer: PDFViewer;
  private zoomController: ZoomController;
  private eventHandler: EventHandler;
  private compilationHandler: CompilationHandler;
  private colorModeManager: ColorModeManager;
  private latexWrapper: LatexWrapper;

  constructor(options: PDFPreviewOptions) {
    const projectId = options.projectId;
    const docType = options.docType || "manuscript";
    const autoCompile = options.autoCompile ?? false;
    const compileDelay = options.compileDelay ?? 3000;
    const fontSize = 14;

    // Initialize color mode
    const colorMode = ColorModeManager.initializeColorMode();
    const renderQuality = options.renderQuality ?? 5.0;

    console.log("[PDFPreviewManager] Initialized with color mode:", colorMode);
    console.log("[PDFPreviewManager] Render quality:", renderQuality + "x");

    // Initialize compilation manager and latex wrapper
    const compilationManager = new CompilationManager(options.apiBaseUrl || "");
    this.latexWrapper = new LatexWrapper({
      title: options.manuscriptTitle,
      author: options.author,
    });

    // Initialize viewer
    this.viewer = new PDFViewer(options.containerId, colorMode, renderQuality);
    this.viewer.initialize();

    // Initialize zoom controller
    this.zoomController = new ZoomController(this.viewer.getPdfViewer());
    this.zoomController.setupControls();

    // Initialize event handler
    this.eventHandler = new EventHandler(compilationManager, this.viewer);
    this.eventHandler.setupEventListeners();

    // Initialize compilation handler
    this.compilationHandler = new CompilationHandler(
      compilationManager,
      this.latexWrapper,
      projectId,
      docType,
      fontSize,
      compileDelay,
      autoCompile,
    );

    // Initialize color mode manager
    this.colorModeManager = new ColorModeManager(
      this.viewer,
      this.compilationHandler,
    );
  }

  /**
   * Schedule auto-compilation
   */
  scheduleAutoCompile(sections: { name: string; content: string }[]): void {
    this.compilationHandler.scheduleAutoCompile(sections);
  }

  /**
   * Compile document preview
   */
  async compile(sections: { name: string; content: string }[]): Promise<void> {
    await this.compilationHandler.compile(sections);
  }

  /**
   * Compile minimal document for quick preview.
   * @param forceCompile - When true, always compile even if an existing PDF is shown.
   *   Use true for user-initiated recompiles (auto-save, toolbar button, DPI change).
   *   Default false skips compilation when an existing PDF is already displayed,
   *   preventing flash on initial page load.
   */
  async compileQuick(
    content: string,
    sectionId?: string,
    forceCompile = false,
  ): Promise<void> {
    const sectionName = sectionId ? sectionId.split("/").pop() : "preview";
    const colorMode = this.viewer.getColorMode();

    // Try to show existing PDF immediately
    const exists = await this.compilationHandler.checkExistingPdf(
      sectionName || "preview",
      colorMode,
    );

    if (exists) {
      const url = this.compilationHandler.getExistingPdfUrl(
        sectionName || "preview",
        colorMode,
      );
      const currentUrl = this.viewer.getCurrentPdfUrl();
      if (currentUrl === url) {
        if (!forceCompile) {
          // Already showing this PDF and not a user-triggered compile — skip.
          // Prevents flash from redundant page-load compilation calls.
          console.log(
            "[PDFPreviewManager] ✓ Existing PDF already displayed, skipping (not forced)",
          );
          return;
        }
        // forceCompile=true: fall through to compile (e.g. user edited content)
        console.log(
          "[PDFPreviewManager] Existing PDF displayed but force=true, recompiling",
        );
      } else {
        // Different URL — show cached PDF immediately
        console.log(
          "[PDFPreviewManager] ✓ Found existing PDF for",
          colorMode,
          "theme, showing immediately",
        );
        this.viewer.displayPdf(url);
        if (!forceCompile) {
          // Skip compilation on page load — user edits will trigger recompile
          console.log(
            "[PDFPreviewManager] Skipping compilation — cached PDF shown, user edits will trigger recompile",
          );
          return;
        }
      }
    } else {
      console.log(
        "[PDFPreviewManager] No existing",
        colorMode,
        "PDF found, will compile",
      );
    }

    // Compile with current theme
    await this.compilationHandler.compileQuick(content, sectionId, colorMode);
  }

  /**
   * Set PDF color mode and switch to themed PDF
   */
  async setColorMode(
    colorMode: "light" | "dark",
    content?: string,
    sectionId?: string,
  ): Promise<void> {
    await this.colorModeManager.setColorMode(colorMode, content, sectionId);
  }

  /**
   * Display a PDF from a direct URL (updates state.currentPdfUrl).
   * Used by the existing-PDF loader to show cached PDFs on page start
   * without triggering compilation.
   */
  displayPdfFromUrl(url: string): void {
    this.viewer.displayPdf(url);
  }

  /**
   * Display placeholder
   */
  displayPlaceholder(): void {
    this.viewer.displayPlaceholder();
  }

  /**
   * Get current PDF URL
   */
  getCurrentPdfUrl(): string | null {
    return this.viewer.getCurrentPdfUrl();
  }

  /**
   * Check if currently compiling
   */
  isCompiling(): boolean {
    return this.compilationHandler.isCompiling();
  }

  /**
   * Cancel compilation
   */
  async cancel(jobId: string): Promise<boolean> {
    return this.compilationHandler.cancel(jobId);
  }

  /**
   * Set document type
   */
  setDocType(docType: string): void {
    this.compilationHandler.setDocType(docType);
    console.log("[PDFPreviewManager] Document type changed to:", docType);
  }

  /**
   * Set auto-compile flag
   */
  setAutoCompile(enabled: boolean): void {
    this.compilationHandler.setAutoCompile(enabled);
  }

  /**
   * Set compile delay
   */
  setCompileDelay(delayMs: number): void {
    this.compilationHandler.setCompileDelay(delayMs);
  }

  /**
   * Set manuscript title
   */
  setTitle(title: string): void {
    this.latexWrapper.setTitle(title);
  }

  /**
   * Set manuscript author
   */
  setAuthor(author: string): void {
    this.latexWrapper.setAuthor(author);
  }

  /**
   * Set font size for PDF compilation
   */
  setFontSize(fontSize: number): void {
    this.compilationHandler.setFontSize(fontSize);
    console.log("[PDFPreviewManager] Font size set to:", fontSize);
  }
}
