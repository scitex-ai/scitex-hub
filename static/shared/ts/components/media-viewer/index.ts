/**
 * MediaViewer Shared Component
 *
 * A reusable component for displaying non-text files (images, PDFs, binaries)
 * and editing CSV files across multiple SciTeX applications.
 *
 * Note: CSV editing is provided by CsvEditor from media-editor module,
 * but MediaViewer integrates it seamlessly.
 *
 * @module @scitex/media-viewer
 */

export { MediaViewer, detectFileType } from "./MediaViewer.ts";
export type { FileType, ViewerFileType, MediaViewerConfig } from "./types.ts";
export { ImageViewer } from "./ImageViewer.ts";
export { PdfViewer } from "./PdfViewer.ts";
export { MermaidViewer } from "./MermaidViewer.ts";
export { BinaryPlaceholder } from "./BinaryPlaceholder.ts";
export {
  IMAGE_EXTENSIONS,
  PDF_EXTENSIONS,
  CSV_EXTENSIONS,
  MERMAID_EXTENSIONS,
  BINARY_EXTENSIONS,
} from "./types.ts";

// Re-export CsvEditor for direct use
export { CsvEditor } from "../media-editor/CsvEditor.ts";
