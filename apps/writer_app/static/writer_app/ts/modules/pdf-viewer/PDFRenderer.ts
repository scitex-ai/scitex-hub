/**
 * PDF Page Renderer
 * Handles canvas-based rendering of PDF pages with quality settings
 */

console.log("[DEBUG] PDFRenderer.ts loaded");

export class PDFRenderer {
  private renderQuality: number = 4.0; // 4x quality by default for 300 DPI rendering
  private colorMode: "light" | "dark" = "light";
  private currentScale: number = 1.5;

  constructor(quality?: number, colorMode?: "light" | "dark") {
    this.renderQuality = quality ?? 4.0;
    this.colorMode = colorMode ?? "light";
  }

  /**
   * Render all pages to container
   */
  async renderAllPages(
    pdfDoc: any,
    container: HTMLElement,
    scale: number,
    colorMode: "light" | "dark",
  ): Promise<void> {
    this.currentScale = scale;
    this.colorMode = colorMode;

    // Create viewer container
    const viewerHtml = `<div class="pdfjs-viewer" id="pdfjs-viewer" data-theme="${this.colorMode}"></div>`;
    container.innerHTML = viewerHtml;

    const viewer = document.getElementById("pdfjs-viewer");
    if (!viewer) return;

    // Render each page
    for (let pageNum = 1; pageNum <= pdfDoc.numPages; pageNum++) {
      await this.renderPage(pdfDoc, pageNum, viewer);
    }
  }

  /**
   * Render a single page
   */
  async renderPage(
    pdfDoc: any,
    pageNum: number,
    container: HTMLElement,
  ): Promise<void> {
    try {
      const page = await pdfDoc.getPage(pageNum);

      // Get device pixel ratio for high-DPI displays
      const dpr = window.devicePixelRatio || 1;

      // Calculate output scale for high-DPI rendering
      const outputScale = dpr * this.renderQuality;

      console.log(
        "[PDFRenderer] Rendering page", pageNum,
        "| Current scale:", this.currentScale,
        "| DPR:", dpr,
        "| Quality:", this.renderQuality + "x",
        "| Output scale:", outputScale + "x",
        "| Final render scale:", this.currentScale * outputScale,
        "| Effective DPI:", Math.round(72 * outputScale)
      );

      // Create viewport for display size
      const displayViewport = page.getViewport({ scale: this.currentScale });

      // Create viewport for rendering (high resolution)
      const renderViewport = page.getViewport({ scale: this.currentScale * outputScale });

      // Create page container
      const pageContainer = document.createElement("div");
      pageContainer.className = "pdfjs-page-container";
      pageContainer.id = `pdfjs-page-${pageNum}`;
      pageContainer.dataset.pageNum = String(pageNum);
      pageContainer.style.cssText = `
        margin: ${pageNum === 1 ? "0" : "0.5rem 0 0 0"};
        background: ${this.colorMode === "dark" ? "#1e1e1e" : "white"};
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        position: relative;
        width: ${displayViewport.width}px;
        height: ${displayViewport.height}px;
      `;

      // Create canvas
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d", { alpha: false });
      if (!context) return;

      // Set canvas buffer size to high-resolution viewport
      canvas.width = renderViewport.width;
      canvas.height = renderViewport.height;

      // Set canvas CSS size to display viewport
      canvas.style.width = displayViewport.width + "px";
      canvas.style.height = displayViewport.height + "px";
      canvas.style.display = "block";

      // Disable image smoothing for crisp text
      context.imageSmoothingEnabled = false;

      pageContainer.appendChild(canvas);
      container.appendChild(pageContainer);

      // Render PDF page to canvas
      const renderContext = {
        canvasContext: context,
        viewport: renderViewport,
      };

      await page.render(renderContext).promise;

      // Render text layer
      await this.renderTextLayer(page, pageContainer, displayViewport);

      console.log("[PDFRenderer] Rendered page", pageNum, "at", Math.round(72 * outputScale), "DPI");
    } catch (error) {
      console.error(`[PDFRenderer] Error rendering page ${pageNum}:`, error);
    }
  }

  /**
   * Render text layer for text selection
   */
  private async renderTextLayer(
    page: any,
    container: HTMLElement,
    viewport: any,
  ): Promise<void> {
    try {
      const textContent = await page.getTextContent();

      const textLayerDiv = document.createElement("div");
      textLayerDiv.className = "textLayer";

      textLayerDiv.style.cssText = `
        position: absolute;
        left: 0;
        top: 0;
        width: ${viewport.width}px;
        height: ${viewport.height}px;
        overflow: hidden;
        opacity: 1;
        line-height: 1.0;
        --scale-factor: ${viewport.scale};
      `;

      container.appendChild(textLayerDiv);

      if ((window as any).pdfjsLib && (window as any).pdfjsLib.renderTextLayer) {
        const renderTask = (window as any).pdfjsLib.renderTextLayer({
          textContent: textContent,
          container: textLayerDiv,
          viewport: viewport,
          textDivs: [],
          textContentItemsStr: [],
        });

        await renderTask.promise;
        console.log("[PDFRenderer] Text layer rendered for page at scale:", viewport.scale);
      }
    } catch (error) {
      console.error("[PDFRenderer] Error rendering text layer:", error);
    }
  }

  /**
   * Set render quality
   */
  setQuality(quality: number): void {
    if (quality < 0.5 || quality > 5.0) {
      console.warn("[PDFRenderer] Quality must be between 0.5 and 5.0");
      return;
    }
    this.renderQuality = quality;
    console.log("[PDFRenderer] Quality changed to:", quality + "x");
  }

  /**
   * Get current quality
   */
  getQuality(): number {
    return this.renderQuality;
  }

  /**
   * Set color mode
   */
  setColorMode(colorMode: "light" | "dark"): void {
    this.colorMode = colorMode;
  }

  /**
   * Get viewer element
   */
  getViewerElement(): HTMLElement | null {
    return document.getElementById("pdfjs-viewer");
  }
}

// EOF
