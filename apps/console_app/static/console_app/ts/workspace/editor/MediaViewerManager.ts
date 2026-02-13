/**
 * Media Viewer Manager
 * Handles rendering of non-text files (images, PDFs, CSVs) in the editor area
 * Coordinates between specialized viewer components
 */

import type { FileType } from "../core/types";
import type { DataTableManager } from "@/components/data-table/index.js";
import { PdfViewer, ImageViewer, CsvViewer } from "./viewers/index.js";

export class MediaViewerManager {
  private container: HTMLElement | null = null;
  private currentFilePath: string | null = null;

  // Viewer instances
  private pdfViewer: PdfViewer;
  private imageViewer: ImageViewer;
  private csvViewer: CsvViewer;

  constructor() {
    this.pdfViewer = new PdfViewer();
    this.imageViewer = new ImageViewer();
    this.csvViewer = new CsvViewer();
    this.initContainer();
  }

  /**
   * Initialize the media viewer container
   */
  private initContainer(): void {
    this.container = document.getElementById("media-viewer");
    if (this.container) return;

    this.container = document.createElement("div");
    this.container.id = "media-viewer";
    this.container.className = "media-viewer-container";
    this.container.style.display = "none";

    const editorContainer = document.getElementById("editor-container");
    if (editorContainer) {
      editorContainer.appendChild(this.container);
    }
  }

  /**
   * Show media viewer and hide Monaco editor
   */
  show(): void {
    if (this.container) {
      this.container.style.display = "flex";
    }
    const monacoEditor = document.getElementById("monaco-editor");
    if (monacoEditor) {
      monacoEditor.style.display = "none";
    }
    const welcomeScreen = document.getElementById("welcome-screen");
    if (welcomeScreen) {
      welcomeScreen.style.display = "none";
    }
  }

  /**
   * Hide media viewer and show Monaco editor
   */
  hide(): void {
    if (this.container) {
      this.container.style.display = "none";
    }
    const monacoEditor = document.getElementById("monaco-editor");
    if (monacoEditor) {
      monacoEditor.style.display = "block";
    }
  }

  /**
   * Display a file in the media viewer
   */
  displayFile(filePath: string, fileType: FileType, blobUrl?: string): void {
    if (!this.container) {
      this.initContainer();
    }
    if (!this.container) return;

    this.currentFilePath = filePath;
    this.container.innerHTML = "";

    const wrapper = document.createElement("div");

    switch (fileType) {
      case "image":
        this.imageViewer.display(wrapper, filePath, blobUrl, this.createToolbar.bind(this));
        break;
      case "pdf":
        this.pdfViewer.display(wrapper, filePath, blobUrl, this.createToolbar.bind(this));
        break;
      case "csv":
        this.csvViewer.display(wrapper, filePath, this.createToolbar.bind(this));
        break;
      case "binary":
        this.displayBinaryPlaceholder(wrapper, filePath);
        break;
      default:
        this.hide();
        return;
    }

    this.container.appendChild(wrapper);
    this.show();
  }

  /**
   * Display placeholder for binary files
   */
  private displayBinaryPlaceholder(wrapper: HTMLElement, filePath: string): void {
    wrapper.className = "media-viewer-binary-wrapper";

    const fileName = filePath.split("/").pop() || filePath;
    const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

    wrapper.innerHTML = `
      <div class="media-viewer-binary-content">
        <i class="fas fa-file-archive media-viewer-binary-icon"></i>
        <h3>Binary File</h3>
        <p class="media-viewer-binary-filename">${fileName}</p>
        <p class="media-viewer-binary-info">
          This file type (${ext}) cannot be displayed in the editor.
        </p>
        <button class="btn-primary media-viewer-download-btn" id="download-binary-btn">
          <i class="fas fa-download"></i> Download
        </button>
      </div>
    `;

    const downloadBtn = document.getElementById("download-binary-btn");
    downloadBtn?.addEventListener("click", () => {
      this.downloadFile(filePath);
    });
  }

  /**
   * Create toolbar for media viewer
   */
  private createToolbar(filePath: string, fileType: string): HTMLElement {
    const toolbar = document.createElement("div");
    toolbar.className = "media-viewer-toolbar";

    const fileName = filePath.split("/").pop() || filePath;
    const icon = fileType === "image" ? "fa-image" : fileType === "pdf" ? "fa-file-pdf" : "fa-file";

    toolbar.innerHTML = `
      <div class="media-viewer-toolbar-left">
        <i class="fas ${icon} media-viewer-icon"></i>
        <span class="media-viewer-filename" title="${filePath}">${fileName}</span>
      </div>
      <div class="media-viewer-toolbar-right">
        <button class="media-viewer-btn" id="media-download-btn" title="Download">
          <i class="fas fa-download"></i>
        </button>
        <button class="media-viewer-btn" id="media-open-new-tab" title="Open in new tab">
          <i class="fas fa-external-link-alt"></i>
        </button>
      </div>
    `;

    setTimeout(() => {
      const downloadBtn = document.getElementById("media-download-btn");
      downloadBtn?.addEventListener("click", () => this.downloadFile(filePath));

      const openNewTabBtn = document.getElementById("media-open-new-tab");
      openNewTabBtn?.addEventListener("click", () => this.openInNewTab(filePath));
    }, 0);

    return toolbar;
  }

  /**
   * Download the current file
   */
  private downloadFile(filePath: string): void {
    const projectData = document.getElementById("project-data");
    const projectId = projectData?.dataset.projectId || "";
    const url = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true&download=true`;

    const a = document.createElement("a");
    a.href = url;
    a.download = filePath.split("/").pop() || "download";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  /**
   * Open file in new tab
   */
  private openInNewTab(filePath: string): void {
    const projectData = document.getElementById("project-data");
    const projectId = projectData?.dataset.projectId || "";
    const url = `/code/api/file-content/${filePath}?project_id=${projectId}&raw=true`;
    window.open(url, "_blank");
  }

  /**
   * Get the currently displayed file path
   */
  getCurrentFilePath(): string | null {
    return this.currentFilePath;
  }

  /**
   * Get the DataTableManager instance (for external access)
   */
  getDataTableManager(): DataTableManager | null {
    return this.csvViewer.getDataTableManager();
  }

  /**
   * Clean up resources
   */
  cleanup(): void {
    if (this.container) {
      this.container.innerHTML = "";
    }
    this.currentFilePath = null;
    this.pdfViewer.cleanup();
    this.csvViewer.cleanup();
  }
}
