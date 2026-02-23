/**
 * Type definitions for the shared Workspace Viewer component.
 * Extended from console_app workspace types with audio/video support.
 */

export type FileType =
  | "text"
  | "image"
  | "pdf"
  | "csv"
  | "mermaid"
  | "audio"
  | "video"
  | "binary";

/** Interface for viewer components that render file content */
export interface Viewer {
  render(
    container: HTMLElement,
    filePath: string,
    projectId: string,
  ): Promise<void>;
  destroy(): void;
}

/** Describes a single open tab in the workspace viewer */
export interface TabInfo {
  path: string;
  title: string;
  fileType: FileType;
}

export const LANGUAGE_MAP: { [key: string]: string } = {
  ".py": "python",
  ".js": "javascript",
  ".ts": "typescript",
  ".html": "html",
  ".css": "css",
  ".json": "json",
  ".md": "markdown",
  ".yaml": "yaml",
  ".yml": "yaml",
  ".sh": "shell",
  ".bash": "shell",
  ".r": "r",
  ".R": "r",
  ".tex": "latex",
  ".bib": "bibtex",
  ".txt": "plaintext",
};

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

/** Audio file extensions */
export const AUDIO_EXTENSIONS = new Set([
  ".mp3",
  ".wav",
  ".ogg",
  ".flac",
  ".m4a",
  ".aac",
  ".wma",
]);

/** Video file extensions */
export const VIDEO_EXTENSIONS = new Set([
  ".mp4",
  ".webm",
  ".avi",
  ".mov",
  ".mkv",
  ".ogv",
]);

/**
 * Binary file extensions that cannot be rendered as text or media.
 * Audio and video are intentionally excluded — they have dedicated viewers.
 */
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
 * Detect file type from file path extension.
 * Audio and video are checked before binary to ensure correct routing.
 */
export function detectFileType(filePath: string): FileType {
  const ext = filePath.substring(filePath.lastIndexOf(".")).toLowerCase();

  if (IMAGE_EXTENSIONS.has(ext)) return "image";
  if (PDF_EXTENSIONS.has(ext)) return "pdf";
  if (CSV_EXTENSIONS.has(ext)) return "csv";
  if (MERMAID_EXTENSIONS.has(ext)) return "mermaid";
  if (AUDIO_EXTENSIONS.has(ext)) return "audio";
  if (VIDEO_EXTENSIONS.has(ext)) return "video";
  if (BINARY_EXTENSIONS.has(ext)) return "binary";
  return "text";
}
