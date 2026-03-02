/**
 * PDF.js Library and Document Loader
 * Handles PDF.js library loading and PDF document loading
 */

console.log("[DEBUG] PDFLoader.ts loaded");

export class PDFLoader {
  private pdfjsLib: any = null;
  private pdfDoc: any = null;
  private isLoading: boolean = false;

  constructor() {
    this.loadPDFJS();
  }

  /**
   * Load PDF.js from CDN
   */
  private loadPDFJS(): void {
    // Check if already loaded
    if ((window as any).pdfjsLib) {
      this.pdfjsLib = (window as any).pdfjsLib;
      console.log("[PDFLoader] PDF.js already loaded");
      return;
    }

    const PDFJS_VERSION = "3.11.174";
    const PDFJS_CDN = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}`;

    const script = document.createElement("script");
    script.src = `${PDFJS_CDN}/pdf.min.js`;
    script.onload = () => {
      this.pdfjsLib = (window as any).pdfjsLib;
      if (this.pdfjsLib) {
        this.pdfjsLib.GlobalWorkerOptions.workerSrc = `${PDFJS_CDN}/pdf.worker.min.js`;
        console.log("[PDFLoader] PDF.js loaded successfully");
      }
    };
    script.onerror = () => {
      console.error("[PDFLoader] Failed to load PDF.js");
    };
    document.head.appendChild(script);
  }

  /**
   * Load a PDF document
   */
  async loadDocument(pdfUrl: string, container: HTMLElement): Promise<any> {
    if (!this.pdfjsLib) {
      console.warn("[PDFLoader] PDF.js not loaded yet, waiting...");
      await new Promise((resolve) => setTimeout(resolve, 500));
      if (!this.pdfjsLib) {
        throw new Error("PDF.js library not available");
      }
    }

    if (this.isLoading) {
      throw new Error("Already loading a PDF");
    }

    this.isLoading = true;

    // Show loading indicator
    container.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--color-fg-muted);">
        <div style="text-align: center;">
          <i class="fas fa-spinner fa-spin fa-2x mb-2"></i>
          <p>Loading PDF...</p>
        </div>
      </div>
    `;

    try {
      console.log("[PDFLoader] Loading PDF:", pdfUrl);
      const PDFJS_VERSION = "3.11.174";
      const PDFJS_CDN = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${PDFJS_VERSION}`;
      const loadingTask = this.pdfjsLib.getDocument({
        url: pdfUrl,
        cMapUrl: `${PDFJS_CDN}/cmaps/`,
        cMapPacked: true,
        standardFontDataUrl: `${PDFJS_CDN}/standard_fonts/`,
      });
      this.pdfDoc = await loadingTask.promise;
      console.log("[PDFLoader] PDF loaded:", this.pdfDoc.numPages, "pages");
      this.isLoading = false;
      return this.pdfDoc;
    } catch (error) {
      console.error("[PDFLoader] Error loading PDF:", error);
      this.isLoading = false;
      throw error;
    }
  }

  /**
   * Get the loaded PDF document
   */
  getDocument(): any {
    return this.pdfDoc;
  }

  /**
   * Get PDF.js library instance
   */
  getLibrary(): any {
    return this.pdfjsLib;
  }

  /**
   * Check if currently loading
   */
  isLoadingDocument(): boolean {
    return this.isLoading;
  }
}

// EOF
