/**
 * Type definitions for MediaViewer shared component
 */

/** File types for viewer (CSV handled by media-editor) */
export type ViewerFileType =
  | "text"
  | "image"
  | "pdf"
  | "binary"
  | "mermaid"
  | "graphviz";

/** All file types including editable ones */
export type FileType = ViewerFileType | "csv";

export interface MediaViewerConfig {
  /** Container element or ID where the viewer will be rendered */
  container: HTMLElement | string;
  /** Function to get file content URL */
  getFileUrl: (filePath: string, raw?: boolean, download?: boolean) => string;
  /** Optional callback when file is downloaded */
  onDownload?: (filePath: string) => void;
  /** Optional callback when viewer is shown/hidden */
  onVisibilityChange?: (visible: boolean) => void;
}

/** Image file extensions */
export const IMAGE_EXTENSIONS = new Set([
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".svg",
  ".bmp",
  ".ico",
]);

/** PDF file extension */
export const PDF_EXTENSIONS = new Set([".pdf"]);

/** CSV/TSV file extensions for table view */
export const CSV_EXTENSIONS = new Set([".csv", ".tsv"]);

/** Mermaid diagram file extensions */
export const MERMAID_EXTENSIONS = new Set([".mmd", ".mermaid"]);

/** Graphviz diagram file extensions */
export const GRAPHVIZ_EXTENSIONS = new Set([".dot", ".gv"]);

/** Binary file extensions that cannot be displayed as text */
export const BINARY_EXTENSIONS = new Set([
  ".zip",
  ".tar",
  ".gz",
  ".rar",
  ".7z",
  ".exe",
  ".dll",
  ".so",
  ".dylib",
  ".mp3",
  ".mp4",
  ".wav",
  ".avi",
  ".mkv",
  ".mov",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".woff",
  ".woff2",
  ".ttf",
  ".eot",
  ".otf",
]);

/**
 * Detect file type from file path extension
 */
export function detectFileType(filePath: string): FileType {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  if (PDF_EXTENSIONS.has(ext)) return "pdf";
  if (CSV_EXTENSIONS.has(ext)) return "csv";
  if (MERMAID_EXTENSIONS.has(ext)) return "mermaid";
  if (GRAPHVIZ_EXTENSIONS.has(ext)) return "graphviz";
  if (BINARY_EXTENSIONS.has(ext)) return "binary";
  return "text";
}
