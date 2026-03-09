/**
 * Types Module
 * Shared type definitions for citations panel
 */

export interface Citation {
  key: string;
  title?: string;
  authors?: string[];
  year?: string;
  journal?: string;
  url?: string;
  publisher?: string;
  citation_count?: number;
  impact_factor?: number;
  abstract?: string;
  doi?: string;
  detail?: string;
  documentation?: string;
}

export interface CitationWithScore {
  citation: Citation;
  score: number;
}
