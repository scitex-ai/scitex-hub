/**
 * PDF Preview Compilation Module
 * Handles compilation logic for PDF preview
 */

import { CompilationManager, CompilationOptions } from "../compilation.js";
import { LatexWrapper } from "../latex-wrapper.js";

export class CompilationHandler {
  private compilationManager: CompilationManager;
  private latexWrapper: LatexWrapper;
  private projectId: number;
  private docType: string;
  private fontSize: number;
  private compileTimeout: ReturnType<typeof setTimeout> | null = null;
  private compileDelay: number;
  private autoCompile: boolean;

  constructor(
    compilationManager: CompilationManager,
    latexWrapper: LatexWrapper,
    projectId: number,
    docType: string,
    fontSize: number,
    compileDelay: number,
    autoCompile: boolean,
  ) {
    this.compilationManager = compilationManager;
    this.latexWrapper = latexWrapper;
    this.projectId = projectId;
    this.docType = docType;
    this.fontSize = fontSize;
    this.compileDelay = compileDelay;
    this.autoCompile = autoCompile;
  }

  /**
   * Schedule auto-compilation
   */
  scheduleAutoCompile(sections: { name: string; content: string }[]): void {
    if (!this.autoCompile) return;

    if (this.compileTimeout) {
      clearTimeout(this.compileTimeout);
    }

    this.compileTimeout = setTimeout(() => {
      this.compile(sections);
    }, this.compileDelay);
  }

  /**
   * Compile document preview
   */
  async compile(sections: { name: string; content: string }[]): Promise<void> {
    const latexContent = this.latexWrapper.createDocument(sections);

    const options: CompilationOptions = {
      projectId: this.projectId,
      docType: "manuscript",
      content: latexContent,
      format: "pdf",
    };

    await this.compilationManager.compilePreview(options);
  }

  /**
   * Compile minimal document for quick preview
   */
  async compileQuick(
    content: string,
    sectionId: string | undefined,
    colorMode: "light" | "dark",
  ): Promise<void> {
    const sectionName = sectionId ? sectionId.split("/").pop() : "preview";

    console.log(
      "[CompilationHandler] Quick compile requested for section:",
      sectionName,
      "theme:",
      colorMode,
    );

    // Compile with current theme
    const latexContent = this.latexWrapper.createMinimalDocument(
      content,
      this.fontSize,
    );

    const options: CompilationOptions = {
      projectId: this.projectId,
      docType: this.docType,
      content: latexContent,
      format: "pdf",
      colorMode: colorMode,
      sectionName: sectionName,
    };

    console.log(
      "[CompilationHandler] Compiling with theme:",
      colorMode,
      "(alternate theme will compile in background)",
    );

    await this.compilationManager.compilePreview(options);
  }

  /**
   * Check existing PDF
   */
  async checkExistingPdf(
    sectionName: string,
    colorMode: "light" | "dark",
  ): Promise<boolean> {
    const existingPdfUrl = `/writer/api/project/${this.projectId}/pdf/preview-${sectionName}-${colorMode}.pdf?t=${Date.now()}`;

    try {
      const response = await fetch(existingPdfUrl, { method: "HEAD" });
      return response.ok;
    } catch {
      return false;
    }
  }

  /**
   * Get existing PDF URL
   */
  getExistingPdfUrl(sectionName: string, colorMode: "light" | "dark"): string {
    return `/writer/api/project/${this.projectId}/pdf/preview-${sectionName}-${colorMode}.pdf?t=${Date.now()}`;
  }

  /**
   * Get themed PDF URL
   */
  getThemedPdfUrl(sectionName: string, colorMode: "light" | "dark"): string {
    return `/writer/api/project/${this.projectId}/pdf/preview-${sectionName}-${colorMode}.pdf`;
  }

  /**
   * Check if currently compiling
   */
  isCompiling(): boolean {
    return this.compilationManager.getIsCompiling();
  }

  /**
   * Cancel compilation
   */
  async cancel(jobId: string): Promise<boolean> {
    return this.compilationManager.cancel(jobId);
  }

  /**
   * Set document type
   */
  setDocType(docType: string): void {
    this.docType = docType;
  }

  /**
   * Set font size
   */
  setFontSize(fontSize: number): void {
    this.fontSize = fontSize;
  }

  /**
   * Set auto-compile
   */
  setAutoCompile(enabled: boolean): void {
    this.autoCompile = enabled;
  }

  /**
   * Set compile delay
   */
  setCompileDelay(delayMs: number): void {
    this.compileDelay = delayMs;
  }
}
