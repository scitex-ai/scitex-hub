/**
 * Type definitions for Scholar Library
 */

export const API = {
  papers: "/scholar/api/library/papers/",
  collections: "/scholar/api/library/collections/",
  updatePaper: (id: string) => `/scholar/api/library/papers/${id}/update/`,
  removePaper: (id: string) => `/scholar/api/library/papers/${id}/remove/`,
  exportBibtex: "/scholar/api/export/bibtex/",
  importBibtex: "/scholar/api/import/bibtex/",
};

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
