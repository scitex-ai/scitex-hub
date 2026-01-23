/**
 * Shared Type Definitions
 * Used across the SciTeX application
 */

// ============================================================================
// Configuration Types
// ============================================================================

console.log(
  "[DEBUG] /home/ywatanabe/proj/scitex-cloud/static/ts/types/index.ts loaded",
);
export interface WriterConfig {
  projectId: string | null;
  projectName?: string | null; // Project name for display
  manuscriptId?: number | null; // Manuscript ID for WebSocket connections
  username: string | null;
  visitorUsername?: string | null; // Allocated visitor user (e.g., "visitor-015")
  projectSlug: string | null;
  isDemo: boolean;
  isVisitor: boolean;
  writerInitialized: boolean;
  documentType?: string; // Current document type (manuscript, shared, supplementary, revision)
  csrfToken?: string;
  wordCounts?: Record<string, number>;
}

// ============================================================================
// Document Types
// ============================================================================

export type DocumentType = "manuscript" | "supplementary" | "revision";

export type SectionName =
  | "abstract"
  | "highlights"
  | "introduction"
  | "methods"
  | "results"
  | "discussion"
  | "conclusion"
  | "acknowledgments"
  | "references"
  | "supplementary_methods"
  | "supplementary_results"
  | "revision_introduction"
  | "revision_editor"
  | "revision_reviewer1"
  | "revision_reviewer2"
  | "shared_title"
  | "shared_authors"
  | "shared_keywords"
  | "shared_journal_name";

export interface Section {
  name: SectionName;
  title: string;
  content: string;
  wordCount: number;
  docType: DocumentType;
  isDirty: boolean;
  isSaving: boolean;
  lastSaved?: Date;
}

export interface SectionMetadata {
  name: SectionName;
  title: string;
  placeholder: string;
  category: DocumentType;
}

export interface SectionData {
  [docType: string]: {
    [sectionName: string]: string;
  };
}

export interface ActiveSections {
  [docType: string]: SectionName[];
}

export interface AvailableSections {
  [docType: string]: SectionName[];
}

export interface SectionUI {
  element: HTMLElement;
  section: SectionName;
  docType: DocumentType;
}

// ============================================================================
// Editor Types
// ============================================================================

export interface EditorState {
  content: string;
  cursorPosition?: { line: number; ch: number };
  scrollPosition?: number;
  currentSection?: string;
  currentDocType?: string;
  liveCompilationEnabled?: boolean;
  currentlyCompiling?: boolean;
  unsavedSections?: Set<string>;
  projectId?: number | null;
}

export interface EditorOptions {
  mode: string;
  theme: string;
  lineNumbers: boolean;
  indentUnit: number;
  indentWithTabs: boolean;
  lineWrapping: boolean;
  matchBrackets: boolean;
  autoCloseBrackets: boolean;
  highlightSelectionMatches: boolean;
  styleActiveLine: boolean;
  readOnly: boolean;
  extraKeys?: Record<string, string | ((cm: any) => void)>;
}

export interface PreviewState {
  mode: "latex" | "preview" | "split";
  content: string;
  wordCount: number;
}

export interface EditorTheme {
  name: string;
  label: string;
  isDark: boolean;
}

export interface ThemeConfig {
  dark: EditorTheme;
  light: EditorTheme;
}

// ============================================================================
// Word Count Types
// ============================================================================

export interface WordCounts {
  [key: string]: number;
}

export interface DocumentStats {
  [docType: string]: {
    [sectionName: string]: number;
  };
}

// ============================================================================
// Compilation Types
// ============================================================================

export interface CompilationJob {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress?: number;
  error?: string;
}

// ============================================================================
// History Types
// ============================================================================

export interface HistoryEntry {
  hash: string;
  message: string;
  author: string;
  timestamp: string;
  content?: string;
}

// ============================================================================
// API Response Types
// ============================================================================

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface CompilationResponse extends ApiResponse {
  data?: {
    job_id: string;
    status: string;
    message: string;
  };
}

export interface PdfResponse extends ApiResponse {
  data?: {
    pdf_path: string;
    exists: boolean;
  };
}

export interface SectionResponse extends ApiResponse {
  data?: {
    content: string;
    wordCount: number;
    lastModified: string;
  };
}

export interface HistoryResponse extends ApiResponse {
  data?: {
    entries: HistoryEntry[];
    totalCount: number;
  };
}

export interface TexFile {
  path: string;
  name: string;
  section: string;
  docType: string;
}

export interface TexFilesResponse extends ApiResponse {
  data?: TexFile[];
}

export interface InitializeResponse extends ApiResponse {
  data?: {
    projectId: string;
    sections: SectionData;
    wordCounts: DocumentStats;
  };
}

export interface DiffResponse extends ApiResponse {
  data?: {
    diff: string;
    pdfPath?: string;
  };
}

export interface RequestConfig {
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  url: string;
  data?: any;
  headers?: Record<string, string>;
  timeout?: number;
}
