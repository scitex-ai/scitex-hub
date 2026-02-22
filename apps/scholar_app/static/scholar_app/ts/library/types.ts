/**
 * Type definitions for Scholar Library
 */

export const API = {
  papers: "/scholar/api/library/papers/",
  collections: "/scholar/api/library/collections/",
  updatePaper: (id: string) => `/scholar/api/library/papers/${id}/update/`,
  removePaper: (id: string) => `/scholar/api/library/papers/${id}/remove/`,
  paperBibtex: (id: string) => `/scholar/api/library/papers/${id}/bibtex/`,
  exportBibtex: "/scholar/api/export/bibtex/",
  exportNamedBib: "/scholar/api/library/export-named-bib/",
  importBibtex: "/scholar/api/import/bibtex/",
  servePdf: (path: string) =>
    `/scholar/api/pdf/serve/?path=${encodeURIComponent(path)}`,
};

export type ViewMode = "card" | "table";

export interface LibraryPaper {
  id: string;
  paper_id: string;
  title: string;
  doi: string | null;
  journal: string | null;
  year: number | null;
  authors: string;
  abstract: string | null;
  reading_status: string;
  importance_rating: number;
  personal_notes: string;
  tags: string[];
  saved_at: string;
  pdf_path: string | null;
  collection_ids: string[];
}

export interface LibraryCollection {
  id: string;
  name: string;
  description: string;
  color: string;
  icon: string;
  paper_count: number;
}

export interface LibraryStats {
  total: number;
  to_read: number;
  reading: number;
  read: number;
  referenced: number;
  favorite: number;
}

export interface UpdatePaperData {
  reading_status: string;
  importance_rating: number;
  tags: string[];
  personal_notes: string;
}
