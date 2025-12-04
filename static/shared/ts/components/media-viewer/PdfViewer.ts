/**
 * PdfViewer - Handles PDF file rendering using PDF.js
 */

import type { MediaViewerConfig } from './types.js';

export class PdfViewer {
  private config: MediaViewerConfig;

  constructor(config: MediaViewerConfig) {
    this.config = config;
  }

  /**
   * Render a PDF file
   */
  render(container: HTMLElement, filePath: string, blobUrl?: string): void {
    const wrapper = document.createElement("div");
    wrapper.className = "media-viewer-pdf-wrapper";

    // Toolbar
    const toolbar = this.createToolbar(filePath);
    wrapper.appendChild(toolbar);

    // PDF viewer container
    const pdfContainer = document.createElement("div");
    pdfContainer.className = "media-viewer-pdf-container";
    pdfContainer.id = "pdf-viewer-container";

    // Canvas for PDF rendering
    const canvas = document.createElement("canvas");
    canvas.id = "pdf-canvas";
    canvas.className = "media-viewer-pdf-canvas";
    pdfContainer.appendChild(canvas);

    wrapper.appendChild(pdfContainer);
    container.appendChild(wrapper);

    // Load PDF
    this.loadPdf(filePath, blobUrl);
  }

  /**
   * Create toolbar for PDF viewer
   */
  private createToolbar(filePath: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.className = "media-viewer-toolbar";

    const fileName = filePath.split("/").pop() || filePath;

    toolbar.innerHTML = `
      <div class="media-viewer-toolbar-left">
        <i class="fas fa-file-pdf media-viewer-icon"></i>
        <span class="media-viewer-filename" title="${filePath}">${fileName}</span>
      </div>
      <div class="media-viewer-toolbar-center">
        <div class="media-viewer-pdf-controls">
          <button class="pdf-control-btn pdf-prev" title="Previous page">
            <i class="fas fa-chevron-left"></i>
          </button>
          <span class="pdf-page-info">
            <input type="number" class="pdf-page-input" min="1" value="1">
            <span> / </span>
            <span class="pdf-total-pages">-</span>
          </span>
          <button class="pdf-control-btn pdf-next" title="Next page">
            <i class="fas fa-chevron-right"></i>
          </button>
          <span class="pdf-control-separator"></span>
          <button class="pdf-control-btn pdf-zoom-out" title="Zoom out">
            <i class="fas fa-search-minus"></i>
          </button>
          <span class="pdf-zoom-level">100%</span>
          <button class="pdf-control-btn pdf-zoom-in" title="Zoom in">
            <i class="fas fa-search-plus"></i>
          </button>
          <button class="pdf-control-btn pdf-fit-width" title="Fit width">
            <i class="fas fa-arrows-alt-h"></i>
          </button>
        </div>
      </div>
      <div class="media-viewer-toolbar-right">
        <button class="media-viewer-btn media-download-btn" title="Download">
          <i class="fas fa-download"></i>
        </button>
        <button class="media-viewer-btn media-open-new-tab" title="Open in new tab">
          <i class="fas fa-external-link-alt"></i>
        </button>
      </div>
    `;

    // Setup button handlers
    const downloadBtn = toolbar.querySelector(".media-download-btn");
    downloadBtn?.addEventListener("click", () => this.downloadFile(filePath));

    const openNewTabBtn = toolbar.querySelector(".media-open-new-tab");
    openNewTabBtn?.addEventListener("click", () => this.openInNewTab(filePath));

    return toolbar;
  }

  /**
   * Load and render PDF using PDF.js
   */
  private async loadPdf(filePath: string, blobUrl?: string): Promise<void> {
    // Load PDF.js if not already loaded
    await this.ensurePdfJsLoaded();

    const lib = (window as any).pdfjsLib;
    if (!lib) {
      console.error("[PdfViewer] PDF.js not available");
      return;
    }

    // Get PDF URL
    const pdfUrl = blobUrl || this.config.getFileUrl(filePath, true, false);

    try {
      const loadingTask = lib.getDocument(pdfUrl);
      const pdf = await loadingTask.promise;

      // Store PDF object for navigation
      (window as any).__currentPdf = pdf;
      (window as any).__currentPdfPage = 1;
      (window as any).__currentPdfScale = 1.0;

      // Update total pages
      const totalPagesEl = document.querySelector(".pdf-total-pages");
      if (totalPagesEl) {
        totalPagesEl.textContent = pdf.numPages.toString();
      }

      // Render first page
      await this.renderPdfPage(pdf, 1, 1.0);

      // Setup navigation controls
      this.setupPdfControls(pdf);
    } catch (error) {
      console.error("[PdfViewer] Error loading PDF:", error);
      const pdfContainer = document.getElementById("pdf-viewer-container");
      if (pdfContainer) {
        pdfContainer.innerHTML = `
          <div class="media-viewer-error">
            <i class="fas fa-exclamation-triangle"></i>
            <p>Failed to load PDF</p>
            <small>${filePath}</small>
          </div>
        `;
      }
    }
  }

  /**
   * Ensure PDF.js library is loaded
   */
  private ensurePdfJsLoaded(): Promise<void> {
    return new Promise((resolve, reject) => {
      if ((window as any).pdfjsLib) {
        resolve();
        return;
      }

      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.onload = () => {
        const lib = (window as any).pdfjsLib;
        if (lib) {
          lib.GlobalWorkerOptions.workerSrc =
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
        }
        resolve();
      };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  /**
   * Render a specific PDF page
   */
  private async renderPdfPage(pdf: any, pageNum: number, scale: number): Promise<void> {
    const canvas = document.getElementById("pdf-canvas") as HTMLCanvasElement;
    if (!canvas) return;

    const page = await pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale });

    canvas.height = viewport.height;
    canvas.width = viewport.width;

    const context = canvas.getContext("2d");
    if (!context) return;

    await page.render({
      canvasContext: context,
      viewport: viewport,
    }).promise;

    // Update page input
    const pageInput = document.querySelector(".pdf-page-input") as HTMLInputElement;
    if (pageInput) {
      pageInput.value = pageNum.toString();
    }

    // Update zoom level display
    const zoomLevel = document.querySelector(".pdf-zoom-level");
    if (zoomLevel) {
      zoomLevel.textContent = `${Math.round(scale * 100)}%`;
    }
  }

  /**
   * Setup PDF navigation controls
   */
  private setupPdfControls(pdf: any): void {
    const prevBtn = document.querySelector(".pdf-prev");
    const nextBtn = document.querySelector(".pdf-next");
    const pageInput = document.querySelector(".pdf-page-input") as HTMLInputElement;
    const zoomInBtn = document.querySelector(".pdf-zoom-in");
    const zoomOutBtn = document.querySelector(".pdf-zoom-out");
    const fitWidthBtn = document.querySelector(".pdf-fit-width");

    const goToPage = async (pageNum: number) => {
      if (pageNum < 1 || pageNum > pdf.numPages) return;
      (window as any).__currentPdfPage = pageNum;
      await this.renderPdfPage(pdf, pageNum, (window as any).__currentPdfScale);
    };

    const setZoom = async (scale: number) => {
      (window as any).__currentPdfScale = scale;
      await this.renderPdfPage(pdf, (window as any).__currentPdfPage, scale);
    };

    prevBtn?.addEventListener("click", () => {
      goToPage((window as any).__currentPdfPage - 1);
    });

    nextBtn?.addEventListener("click", () => {
      goToPage((window as any).__currentPdfPage + 1);
    });

    pageInput?.addEventListener("change", () => {
      goToPage(parseInt(pageInput.value, 10));
    });

    zoomInBtn?.addEventListener("click", () => {
      setZoom((window as any).__currentPdfScale * 1.25);
    });

    zoomOutBtn?.addEventListener("click", () => {
      setZoom((window as any).__currentPdfScale / 1.25);
    });

    fitWidthBtn?.addEventListener("click", async () => {
      const container = document.getElementById("pdf-viewer-container");
      if (!container) return;
      const page = await pdf.getPage((window as any).__currentPdfPage);
      const viewport = page.getViewport({ scale: 1 });
      const scale = (container.clientWidth - 40) / viewport.width;
      setZoom(scale);
    });
  }

  /**
   * Download the file
   */
  private downloadFile(filePath: string): void {
    const url = this.config.getFileUrl(filePath, true, true);
    const a = document.createElement("a");
    a.href = url;
    a.download = filePath.split("/").pop() || "download";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    this.config.onDownload?.(filePath);
  }

  /**
   * Open file in new tab
   */
  private openInNewTab(filePath: string): void {
    const url = this.config.getFileUrl(filePath, true, false);
    window.open(url, "_blank");
  }

  /**
   * Cleanup PDF.js resources
   */
  cleanup(): void {
    delete (window as any).__currentPdf;
    delete (window as any).__currentPdfPage;
    delete (window as any).__currentPdfScale;
  }
}
