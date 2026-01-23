/**
 * PDF Viewer
 * Handles PDF file display using PDF.js library
 */

export class PdfViewer {
  private pdfContainer: HTMLElement | null = null;

  /**
   * Display a PDF file
   */
  display(
    wrapper: HTMLElement,
    filePath: string,
    blobUrl?: string,
    createToolbar?: (filePath: string, fileType: string) => HTMLElement
  ): void {
    wrapper.className = "media-viewer-pdf-wrapper";

    // Toolbar
    if (createToolbar) {
      const toolbar = createToolbar(filePath, "pdf");
      this.addPdfControls(toolbar);
      wrapper.appendChild(toolbar);
    }

    // PDF viewer container
    const pdfContainer = document.createElement("div");
    pdfContainer.className = "media-viewer-pdf-container";
    pdfContainer.id = "pdf-viewer-container";
    this.pdfContainer = pdfContainer;

    // Canvas for PDF rendering
    const canvas = document.createElement("canvas");
    canvas.id = "pdf-canvas";
    canvas.className = "media-viewer-pdf-canvas";
    pdfContainer.appendChild(canvas);

    wrapper.appendChild(pdfContainer);

    // Load PDF
    this.loadPdf(filePath, blobUrl);
  }

  /**
   * Add PDF-specific controls to toolbar
   */
  private addPdfControls(toolbar: HTMLElement): void {
    const pdfControls = document.createElement("div");
    pdfControls.className = "media-viewer-pdf-controls";
    pdfControls.innerHTML = `
      <button class="pdf-control-btn" id="pdf-prev" title="Previous page">
        <i class="fas fa-chevron-left"></i>
      </button>
      <span class="pdf-page-info">
        <input type="number" id="pdf-page-input" min="1" value="1" class="pdf-page-input">
        <span> / </span>
        <span id="pdf-total-pages">-</span>
      </span>
      <button class="pdf-control-btn" id="pdf-next" title="Next page">
        <i class="fas fa-chevron-right"></i>
      </button>
      <span class="pdf-control-separator"></span>
      <button class="pdf-control-btn" id="pdf-zoom-out" title="Zoom out">
        <i class="fas fa-search-minus"></i>
      </button>
      <span id="pdf-zoom-level" class="pdf-zoom-level">100%</span>
      <button class="pdf-control-btn" id="pdf-zoom-in" title="Zoom in">
        <i class="fas fa-search-plus"></i>
      </button>
      <button class="pdf-control-btn" id="pdf-fit-width" title="Fit width">
        <i class="fas fa-arrows-alt-h"></i>
      </button>
    `;
    toolbar.appendChild(pdfControls);
  }

  /**
   * Load and render PDF using PDF.js
   */
  private async loadPdf(filePath: string, blobUrl?: string): Promise<void> {
    // Check if PDF.js is loaded
    const pdfjsLib = (window as any).pdfjsLib;
    if (!pdfjsLib) {
      await this.loadPdfJs();
    }

    const lib = (window as any).pdfjsLib;
    if (!lib) {
      console.error("[PdfViewer] PDF.js not available");
      return;
    }

    // Get PDF URL
    let pdfUrl: string;
    if (blobUrl) {
      pdfUrl = blobUrl;
    } else {
      const projectData = document.getElementById("project-data");
      const projectId = projectData?.dataset.projectId || "";
      pdfUrl = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
    }

    try {
      const loadingTask = lib.getDocument(pdfUrl);
      const pdf = await loadingTask.promise;

      // Store PDF object for navigation
      (window as any).__currentPdf = pdf;
      (window as any).__currentPdfPage = 1;
      (window as any).__currentPdfScale = 1.0;

      // Update total pages
      const totalPagesEl = document.getElementById("pdf-total-pages");
      if (totalPagesEl) {
        totalPagesEl.textContent = pdf.numPages.toString();
      }

      // Render first page
      await this.renderPage(pdf, 1, 1.0);

      // Setup navigation controls
      this.setupControls(pdf);
    } catch (error) {
      console.error("[PdfViewer] Error loading PDF:", error);
      if (this.pdfContainer) {
        this.pdfContainer.innerHTML = `
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
   * Load PDF.js library from CDN
   */
  private loadPdfJs(): Promise<void> {
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
  private async renderPage(pdf: any, pageNum: number, scale: number): Promise<void> {
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
    const pageInput = document.getElementById("pdf-page-input") as HTMLInputElement;
    if (pageInput) {
      pageInput.value = pageNum.toString();
    }

    // Update zoom level display
    const zoomLevel = document.getElementById("pdf-zoom-level");
    if (zoomLevel) {
      zoomLevel.textContent = `${Math.round(scale * 100)}%`;
    }
  }

  /**
   * Setup PDF navigation controls
   */
  private setupControls(pdf: any): void {
    const prevBtn = document.getElementById("pdf-prev");
    const nextBtn = document.getElementById("pdf-next");
    const pageInput = document.getElementById("pdf-page-input") as HTMLInputElement;
    const zoomInBtn = document.getElementById("pdf-zoom-in");
    const zoomOutBtn = document.getElementById("pdf-zoom-out");
    const fitWidthBtn = document.getElementById("pdf-fit-width");

    const goToPage = async (pageNum: number) => {
      if (pageNum < 1 || pageNum > pdf.numPages) return;
      (window as any).__currentPdfPage = pageNum;
      await this.renderPage(pdf, pageNum, (window as any).__currentPdfScale);
    };

    const setZoom = async (scale: number) => {
      (window as any).__currentPdfScale = scale;
      await this.renderPage(pdf, (window as any).__currentPdfPage, scale);
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
   * Cleanup PDF resources
   */
  cleanup(): void {
    delete (window as any).__currentPdf;
    delete (window as any).__currentPdfPage;
    delete (window as any).__currentPdfScale;
    this.pdfContainer = null;
  }
}
