/**
 * ViewerRouter - Routes file types to dedicated viewer instances.
 *
 * Uses a simple factory pattern: one viewer instance per FileType is
 * created lazily and reused for subsequent files of the same type.
 * Text files are handled externally by Monaco; binary files are not viewable.
 */

import { detectFileType, type FileType, type Viewer } from "./types.ts";
import {
  ImageViewer,
  PdfViewer,
  CsvViewer,
  MermaidViewer,
  GraphvizViewer,
  AudioViewer,
  VideoViewer,
} from "./viewers/index.ts";

export class ViewerRouter {
  private viewers: Map<FileType, Viewer> = new Map();

  /**
   * Return the appropriate Viewer for a file path, or null for text/binary.
   * Viewer instances are reused across files of the same type.
   */
  getViewer(filePath: string): Viewer | null {
    const fileType = detectFileType(filePath);

    if (fileType === "text") return null;
    if (fileType === "binary") return null;

    if (!this.viewers.has(fileType)) {
      const viewer = this.createViewer(fileType);
      if (!viewer) return null;
      this.viewers.set(fileType, viewer);
    }

    return this.viewers.get(fileType) ?? null;
  }

  destroyAll(): void {
    this.viewers.forEach((v) => v.destroy());
    this.viewers.clear();
  }

  private createViewer(fileType: FileType): Viewer | null {
    switch (fileType) {
      case "image":
        return new ImageViewer();
      case "pdf":
        return new PdfViewer();
      case "csv":
        return new CsvViewer();
      case "mermaid":
        return new MermaidViewer();
      case "graphviz":
        return new GraphvizViewer();
      case "audio":
        return new AudioViewer();
      case "video":
        return new VideoViewer();
      default:
        return null;
    }
  }
}
