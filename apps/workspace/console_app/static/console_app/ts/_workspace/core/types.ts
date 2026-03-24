/**
 * Type definitions for Code Workspace
 * All interfaces, types, and constants used across workspace modules
 */

export interface Project {
  id: number;
  name: string;
  owner: string;
  slug: string;
}

export interface EditorConfig {
  currentProject: Project | null;
  csrfToken: string;
}

export type FileType = "text" | "image" | "pdf" | "csv" | "mermaid" | "binary";

export interface OpenFile {
  path: string;
  content: string;
  language: string;
  /** File type for rendering - 'text' uses Monaco, others use media viewer */
  fileType: FileType;
  /** For media files, stores the blob URL for display */
  blobUrl?: string;
}

export interface GitFileStatus {
  status: string;
  staged: boolean;
}

export interface GitDiff {
  line: number;
  status: string;
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
  if (BINARY_EXTENSIONS.has(ext)) return "binary";
  return "text";
}

export const DEFAULT_SCRATCH_CONTENT = `# Welcome to Code Editor
# This is a scratch buffer for quick notes and code experiments
# Your changes here won't be saved unless you explicitly create a file

# Quick Tips:
# - Press Ctrl+O to open a file
# - Press Ctrl+S to save
# - Press Ctrl+N to create a new file
# - Press Ctrl+K to show all keyboard shortcuts
# - Press F5 to run Python files
# - Right-click in the file tree for more options

# Try some Python console:
def hello(name):
    return f"Hello, {name}!"

print(hello("World"))
`;
