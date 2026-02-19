/**
 * PDF Download types for Scholar Search
 */

// PDF status types
export type PDFStatus =
  | "unknown"
  | "checking"
  | "available"
  | "downloading"
  | "downloaded"
  | "unavailable"
  | "error";

// API response interfaces
export interface PDFStatusResponse {
  status: string;
  has_pdf: boolean;
  path?: string;
  filename?: string;
  size_bytes?: number;
  is_open_access?: boolean;
  can_download?: boolean;
}

export interface PDFDownloadResponse {
  status: string;
  downloaded: boolean;
  path?: string;
  filename?: string;
  method?: string;
  size_bytes?: number;
  reason?: string;
  error?: string;
}
