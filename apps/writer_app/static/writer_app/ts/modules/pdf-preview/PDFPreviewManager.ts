/**
 * PDF Preview Manager
 * Main class coordinating PDF preview functionality
 */

import { CompilationManager } from "../compilation.js";
import { LatexWrapper } from "../latex-wrapper.js";
import { PDFViewer } from "./viewer.js";
import { ZoomController } from "./zoom.js";
import { EventHandler } from "./events.js";
import { CompilationHandler } from "./compilation.js";
import { ColorModeManager } from "./color-mode.js";

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
    const renderQuality = options.renderQuality ?? 4.0;

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
   * Compile minimal document for quick preview
   */
  async compileQuick(content: string, sectionId?: string): Promise<void> {
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
      console.log(
        "[PDFPreviewManager] ✓ Found existing PDF for",
        colorMode,
        "theme, showing immediately",
      );
      this.viewer.displayPdf(url);
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
