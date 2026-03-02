/**
 * PdfViewer - Canvas-based PDF rendering via PDF.js CDN.
 * State is stored as instance properties (not on window).
 */

import type { Viewer } from "../types";
import { getFileUrl } from "../_file-loader";

const PDFJS_CDN =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
const PDFJS_WORKER =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

export class PdfViewer implements Viewer {
  private pdf: any = null;
  private currentPage = 1;
  private scale = 1.0;
  private canvas: HTMLCanvasElement | null = null;
  private totalPagesEl: HTMLElement | null = null;
  private pageInput: HTMLInputElement | null = null;
  private zoomLevelEl: HTMLElement | null = null;
  private pdfContainer: HTMLElement | null = null;

  async render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void> {
    const rawUrl = getFileUrl(filePath, projectId, true);
    const fileName = filePath.split("/").pop() || filePath;

    container.innerHTML = "";

    const wrapper = document.createElement("div");
    wrapper.style.cssText =
      "display:flex; flex-direction:column; height:100%; overflow:hidden;";

    wrapper.appendChild(this.buildToolbar(fileName));

    this.pdfContainer = document.createElement("div");
    this.pdfContainer.style.cssText =
      "flex:1; overflow:auto; padding:10px; background:#2a2a2a; display:flex; justify-content:center;";

    this.canvas = document.createElement("canvas");
    this.canvas.style.cssText =
      "display:block; box-shadow:0 2px 8px rgba(0,0,0,0.5);";
    this.pdfContainer.appendChild(this.canvas);

    wrapper.appendChild(this.pdfContainer);
    container.appendChild(wrapper);

    await this.loadPdf(rawUrl, fileName);
  }

  private buildToolbar(fileName: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.style.cssText =
      "display:flex; align-items:center; gap:6px; padding:6px 10px; border-bottom:1px solid #333; flex-shrink:0; font-size:0.85em; flex-wrap:wrap;";

    toolbar.innerHTML = `
      <span style="color:#888; margin-right:auto;" title="${fileName}">${fileName}</span>
      <button class="pdf-prev" title="Previous page" style="cursor:pointer;">&#8249;</button>
      <input class="pdf-page-input" type="number" min="1" value="1"
        style="width:3em; text-align:center; background:#1a1a1a; color:#ccc; border:1px solid #444; border-radius:3px; padding:2px;">
      <span> / </span>
      <span class="pdf-total-pages">-</span>
      <button class="pdf-next" title="Next page" style="cursor:pointer;">&#8250;</button>
      <span style="width:8px;"></span>
      <button class="pdf-zoom-out" title="Zoom out" style="cursor:pointer;">&#8722;</button>
      <span class="pdf-zoom-level" style="min-width:3.5em; text-align:center;">100%</span>
      <button class="pdf-zoom-in" title="Zoom in" style="cursor:pointer;">&#43;</button>
      <button class="pdf-fit-width" title="Fit width" style="cursor:pointer; font-size:0.8em;">Fit</button>
    `;

    this.totalPagesEl = toolbar.querySelector(".pdf-total-pages");
    this.pageInput = toolbar.querySelector(".pdf-page-input");
    this.zoomLevelEl = toolbar.querySelector(".pdf-zoom-level");

    toolbar
      .querySelector(".pdf-prev")
      ?.addEventListener("click", () => this.goToPage(this.currentPage - 1));
    toolbar
      .querySelector(".pdf-next")
      ?.addEventListener("click", () => this.goToPage(this.currentPage + 1));
    this.pageInput?.addEventListener("change", () => {
      if (this.pageInput) this.goToPage(parseInt(this.pageInput.value, 10));
    });
    toolbar
      .querySelector(".pdf-zoom-in")
      ?.addEventListener("click", () => this.setZoom(this.scale * 1.25));
    toolbar
      .querySelector(".pdf-zoom-out")
      ?.addEventListener("click", () => this.setZoom(this.scale / 1.25));
    toolbar
      .querySelector(".pdf-fit-width")
      ?.addEventListener("click", () => this.fitWidth());

    return toolbar;
  }

  private async loadPdf(url: string, fileName: string): Promise<void> {
    await this.ensurePdfJs();
    const lib = (window as any).pdfjsLib;
    if (!lib) {
      this.showError(`PDF.js unavailable: ${fileName}`);
      return;
    }
    try {
      this.pdf = await lib.getDocument(url).promise;
      if (this.totalPagesEl)
        this.totalPagesEl.textContent = this.pdf.numPages.toString();
      if (this.pageInput) this.pageInput.max = this.pdf.numPages.toString();
      await this.renderPage(1, 1.0);
    } catch (err) {
      this.showError(`Failed to load PDF: ${fileName}`);
    }
  }

  /**
   * Load PDF.js via fetch+eval to avoid AMD/RequireJS conflict with Monaco.
   * Monaco's RequireJS intercepts <script> tag UMD modules, so we fetch
   * the script as text, temporarily disable AMD globals, execute it, then restore.
   */
  private async ensurePdfJs(): Promise<void> {
    if ((window as any).pdfjsLib) return;

    const resp = await fetch(PDFJS_CDN);
    if (!resp.ok) throw new Error(`Failed to fetch PDF.js: ${resp.status}`);
    const code = await resp.text();

    // Save and disable AMD globals so PDF.js sets window.pdfjsLib directly
    const savedDefine = (window as any).define;
    const savedRequire = (window as any).require;
    (window as any).define = undefined;
    (window as any).require = undefined;

    try {
      new Function(code)();
    } finally {
      // Restore AMD globals for Monaco
      (window as any).define = savedDefine;
      (window as any).require = savedRequire;
    }

    const lib = (window as any).pdfjsLib;
    if (lib) lib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
  }

  private async renderPage(pageNum: number, scale: number): Promise<void> {
    if (!this.pdf || !this.canvas) return;
    const page = await this.pdf.getPage(pageNum);
    const viewport = page.getViewport({ scale });
    this.canvas.width = viewport.width;
    this.canvas.height = viewport.height;
    const ctx = this.canvas.getContext("2d");
    if (!ctx) return;
    await page.render({ canvasContext: ctx, viewport }).promise;
    this.currentPage = pageNum;
    this.scale = scale;
    if (this.pageInput) this.pageInput.value = pageNum.toString();
    if (this.zoomLevelEl)
      this.zoomLevelEl.textContent = `${Math.round(scale * 100)}%`;
  }

  private goToPage(pageNum: number): void {
    if (!this.pdf || pageNum < 1 || pageNum > this.pdf.numPages) return;
    this.renderPage(pageNum, this.scale);
  }

  private setZoom(scale: number): void {
    this.renderPage(this.currentPage, Math.max(0.1, Math.min(5, scale)));
  }

  private async fitWidth(): Promise<void> {
    if (!this.pdf || !this.pdfContainer) return;
    const page = await this.pdf.getPage(this.currentPage);
    const viewport = page.getViewport({ scale: 1 });
    const scale = (this.pdfContainer.clientWidth - 40) / viewport.width;
    this.setZoom(scale);
  }

  private showError(message: string): void {
    if (this.pdfContainer) {
      this.pdfContainer.innerHTML = `<div style="padding:20px; color:#e55; text-align:center;">${message}</div>`;
    }
  }

  destroy(): void {
    if (this.pdf) {
      this.pdf.destroy?.();
      this.pdf = null;
    }
    this.canvas = null;
    this.pdfContainer = null;
  }
}
