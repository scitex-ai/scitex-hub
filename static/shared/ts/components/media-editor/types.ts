/**
 * Type definitions for MediaEditor shared components
 */

export interface MediaEditorConfig {
  /** Container element or ID where the editor will be rendered */
  container: HTMLElement | string;
  /** Function to get file content URL */
  getFileUrl: (filePath: string, raw?: boolean, download?: boolean) => string;
  /** Function to save file content */
  saveFile?: (filePath: string, content: string) => Promise<boolean>;
  /** Optional callback when file is saved */
  onSave?: (filePath: string) => void;
  /** Optional callback when file is downloaded */
  onDownload?: (filePath: string) => void;
  /** Optional callback when data changes */
  onDataChange?: (filePath: string) => void;
}

/** CSV/TSV file extensions */
export const CSV_EXTENSIONS = new Set([".csv", ".tsv"]);

/**
 * Check if a file is a CSV/TSV file
 */
export function isCsvFile(filePath: string): boolean {
  const ext = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
  return CSV_EXTENSIONS.has(ext);
}
