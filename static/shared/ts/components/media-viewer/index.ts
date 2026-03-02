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

export { MediaViewer, detectFileType } from "./_MediaViewer";
export type { FileType, ViewerFileType, MediaViewerConfig } from "./types";
export { ImageViewer } from "./_ImageViewer";
export { PdfViewer } from "./_PdfViewer";
export { MermaidViewer } from "./_MermaidViewer";
export { BinaryPlaceholder } from "./_BinaryPlaceholder";
export {
  IMAGE_EXTENSIONS,
  PDF_EXTENSIONS,
  CSV_EXTENSIONS,
  MERMAID_EXTENSIONS,
  BINARY_EXTENSIONS,
} from "./types";

// Re-export CsvEditor for direct use
export { CsvEditor } from "../media-editor/_CsvEditor";
