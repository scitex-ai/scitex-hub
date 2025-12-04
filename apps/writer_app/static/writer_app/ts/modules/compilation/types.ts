/**
 * Compilation Types
 * Shared type definitions for compilation system
 */

import { CompilationJob } from "@/types";

export interface CompilationOptions {
  projectId: number;
  docType: string;
  content?: string; // Optional: only for preview
  format?: "pdf" | "dvi";
  colorMode?: "light" | "dark";
  sectionName?: string; // For section-specific preview files
  // Full compilation options
  noFigs?: boolean;
  ppt2tif?: boolean;
  cropTif?: boolean;
  quiet?: boolean;
  verbose?: boolean;
  force?: boolean;
}

export interface CompilationResult {
  success: boolean;
  job_id?: string;
  output_pdf?: string;
  pdf_path?: string;
  log?: string;
  log_html?: string;
  error?: string;
  result?: {
    output_pdf?: string;
    pdf_path?: string;
    error?: string;
  };
}

export interface CompilationStatusData {
  status: "pending" | "processing" | "completed" | "failed";
  progress?: number;
  step?: string;
  log?: string;
  log_html?: string;
  result?: CompilationResult;
}

export interface CompilationCallbacks {
  onProgress?: (progress: number, status: string) => void;
  onComplete?: (jobId: string, pdfUrl: string) => void;
  onError?: (error: string) => void;
}

export type { CompilationJob };
