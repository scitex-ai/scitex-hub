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

export { MediaViewer, detectFileType } from './MediaViewer.js';
export type { FileType, ViewerFileType, MediaViewerConfig } from './types.js';
export { ImageViewer } from './ImageViewer.js';
export { PdfViewer } from './PdfViewer.js';
export { BinaryPlaceholder } from './BinaryPlaceholder.js';
export {
  IMAGE_EXTENSIONS,
  PDF_EXTENSIONS,
  CSV_EXTENSIONS,
  BINARY_EXTENSIONS
} from './types.js';

// Re-export CsvEditor for direct use
export { CsvEditor } from '../media-editor/CsvEditor.js';
