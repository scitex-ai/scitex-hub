/**
 * MediaViewer - Main component for displaying non-text files
 *
 * This shared component can be used across multiple apps:
 * - /code/ workspace
 * - /project/ Files interface (/blob/ routes)
 * - /writer/ for embedded media
 *
 * Usage:
 * ```typescript
 * const viewer = new MediaViewer({
 *   container: document.getElementById('media-container'),
 *   getFileUrl: (path, raw, download) => {
 *     return `/api/file/${path}?raw=${raw}&download=${download}`;
 *   }
 * });
 *
 * viewer.displayFile('path/to/image.jpg', 'image');
 * ```
 */

import type { MediaViewerConfig, FileType } from "./types.ts";
import { detectFileType } from "./types.ts";
import { ImageViewer } from "./ImageViewer.ts";
import { PdfViewer } from "./PdfViewer.ts";
import { BinaryPlaceholder } from "./BinaryPlaceholder.ts";
import { MermaidViewer } from "./MermaidViewer.ts";
// CsvEditor from media-editor module
import { CsvEditor } from "../media-editor/CsvEditor.ts";

export class MediaViewer {
  private config: MediaViewerConfig;
  private container: HTMLElement | null = null;
  private currentFilePath: string | null = null;
  private imageViewer: ImageViewer;
  private pdfViewer: PdfViewer;
  private csvEditor: CsvEditor;
  private mermaidViewer: MermaidViewer;
  private binaryPlaceholder: BinaryPlaceholder;
  private editorElement: HTMLElement | null = null;

  constructor(config: MediaViewerConfig) {
    this.config = config;
    this.imageViewer = new ImageViewer(config);
    this.pdfViewer = new PdfViewer(config);
    // CsvEditor uses MediaEditorConfig which is compatible with MediaViewerConfig
    this.csvEditor = new CsvEditor(config as any);
    this.mermaidViewer = new MermaidViewer(config);
    this.binaryPlaceholder = new BinaryPlaceholder(config);
    this.initContainer();
  }

  /**
   * Initialize the media viewer container
   */
  private initContainer(): void {
    // Resolve container from ID or element
    if (typeof this.config.container === "string") {
      this.container = document.getElementById(this.config.container);
    } else {
      this.container = this.config.container;
    }

    if (!this.container) {
      console.error("[MediaViewer] Container not found");
      return;
    }

    // Add media viewer class
    this.container.classList.add("media-viewer-container");
    this.container.style.display = "none";
  }

  /**
   * Set the editor element to hide/show when switching views
   * This is optional - only needed when MediaViewer coexists with an editor
   */
  setEditorElement(element: HTMLElement | string): void {
    if (typeof element === "string") {
      this.editorElement = document.getElementById(element);
    } else {
      this.editorElement = element;
    }
  }

  /**
   * Show media viewer and hide editor
   */
  show(): void {
    if (this.container) {
      this.container.style.display = "flex";
    }
    if (this.editorElement) {
      this.editorElement.style.display = "none";
    }
    this.config.onVisibilityChange?.(true);
  }

  /**
   * Hide media viewer and show editor
   */
  hide(): void {
    if (this.container) {
      this.container.style.display = "none";
    }
    if (this.editorElement) {
      this.editorElement.style.display = "block";
    }
    this.config.onVisibilityChange?.(false);
  }

  /**
   * Display a file in the media viewer
   * @param filePath - Path to the file
   * @param fileType - Type of file (auto-detected if not provided)
   * @param blobUrl - Optional blob URL for local files
   */
  async displayFile(
    filePath: string,
    fileType?: FileType,
    blobUrl?: string,
  ): Promise<void> {
    if (!this.container) {
      this.initContainer();
    }
    if (!this.container) return;

    // Auto-detect file type if not provided
    const type = fileType || detectFileType(filePath);

    // Text files should be handled by the editor, not media viewer
    if (type === "text") {
      this.hide();
      return;
    }

    this.currentFilePath = filePath;
    this.container.innerHTML = "";

    switch (type) {
      case "image":
        this.imageViewer.render(this.container, filePath, blobUrl);
        break;
      case "pdf":
        this.pdfViewer.render(this.container, filePath, blobUrl);
        break;
      case "csv":
        await this.csvEditor.render(this.container, filePath);
        break;
      case "mermaid":
        await this.mermaidViewer.render(this.container, filePath);
        break;
      case "binary":
        this.binaryPlaceholder.render(this.container, filePath);
        break;
      default:
        this.hide();
        return;
    }

    this.show();
  }

  /**
   * Check if a file type can be displayed by the media viewer
   */
  canDisplay(filePath: string): boolean {
    const type = detectFileType(filePath);
    return type !== "text";
  }

  /**
   * Get the currently displayed file path
   */
  getCurrentFilePath(): string | null {
    return this.currentFilePath;
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
  }

  /**
   * Check if the viewer is currently visible
   */
  isVisible(): boolean {
    return this.container?.style.display !== "none";
  }
}

// Re-export types and utilities
export { detectFileType } from "./types.ts";
export type { FileType, MediaViewerConfig } from "./types.ts";
